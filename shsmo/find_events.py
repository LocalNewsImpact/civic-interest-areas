"""Candidate publisher-history passages in Missouri Press News.

A passage is a paragraph read with the one before and after it (headlines come through as their own
paragraphs). It is a candidate when it uses transaction language. Each candidate is matched to known
titles: the SHSMO Missouri title catalogue and the outlet registry. A title counts only if it contains
its own town's name or is three or more words long, so "Free Press" alone never matches.
Writes candidates.jsonl -- one line per candidate, with the page link and issue date.
"""

import collections
import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
LOOK = Path.home() / "VSCode/NewsCrawler/MizzouNewsCrawler/src/lookups"

TRANSACTION = re.compile(
    r"\b(has sold|have sold|sold (?:the|his|her|their|its)|sale of|purchased|has bought|have bought|bought the|"
    r"acquired|new owners?|new publishers?|took over|taken over|assumed (?:ownership|control|management)|"
    r"leased|consolidated|merged|merger|combined with|suspended publication|ceased publication|"
    r"discontinued publication|last issue|first issue|established a|founded|launched|"
    r"started (?:a|the) (?:new )?(?:paper|newspaper|weekly))\b", re.I)


def norm(s):
    s = re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()
    return re.sub(r"^the ", "", s)


# known titles, keyed by their first word for a single pass over each passage
titles = collections.defaultdict(list)
n_titles = 0
with open(LOOK / "newspaper_history/shsmo_missouri_titles.csv") as fh:
    for r in csv.DictReader(fh):
        t, town = norm(r["title"]), norm(r["town"])
        if not t:
            continue
        if not ((town and town in t) or len(t.split()) >= 3):
            continue
        titles[t.split()[0]].append((t, {"title": r["title"], "town": r["town"], "county": r["county"],
                                         "years": f"{r['start_year']}-{r['end_year']}", "from": "shsmo"}))
        n_titles += 1
with open(LOOK / "mo_outlet_registry.csv") as fh:
    for r in csv.DictReader(fh):
        t, town = norm(r["outlet"]), norm(r["city"])
        if t and ((town and town in t) or len(t.split()) >= 3):
            titles[t.split()[0]].append((t, {"title": r["outlet"], "town": r["city"], "county": r["county"],
                                             "owner": r["owner"], "from": "registry"}))
            n_titles += 1


# one-word titles ("Ozark", "Republic") match the region or the plain word, not the paper: dropped
for k in list(titles):
    titles[k] = [(t, m) for t, m in titles[k] if len(t.split()) >= 2]
# a title held by several towns ("Tri-County News" in five) is placed only if its town is in the passage
towns_of = collections.defaultdict(set)
for k in titles:
    for t, m in titles[k]:
        towns_of[t].add(norm(m["town"]))


def find_titles(text):
    flat = norm(text)
    toks = flat.split()
    hits = {}
    for i, tok in enumerate(toks):
        for t, meta in titles.get(tok, ()):
            n = len(t.split())
            if " ".join(toks[i:i + n]) != t:
                continue
            town = norm(meta["town"])
            if len(towns_of[t]) > 1 and not (town and f" {town} " in f" {flat} "):
                continue
            hits[(t, town)] = meta                      # one entry per title and town, whichever list it came from
    return list(hits.values())


rows = [json.loads(l) for l in open(HERE / "pages_dated.jsonl")]
rows = [r for r in rows if r["publication"] == "Missouri Press News"]
cands = []
for r in rows:
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", r["text"])]
    paras = [p for p in paras if p]
    for i, p in enumerate(paras):
        terms = sorted({m.group(1).lower() for m in TRANSACTION.finditer(p)})
        if not terms:
            continue
        window = " ".join(paras[max(0, i - 1):i + 2])
        cands.append({
            "issue": f"{r['issue_year']}-{r['issue_month']:02d}", "volume": r["volume_title"],
            "page": r["page_title"], "link": r["link"], "terms": terms,
            "titles": find_titles(window), "passage": window,
        })
with open(HERE / "candidates.jsonl", "w") as out:
    for c in cands:
        out.write(json.dumps(c) + "\n")

matched = [c for c in cands if c["titles"]]
print(f"known titles in the matcher: {n_titles:,}")
print(f"passages with transaction language: {len(cands):,}; naming at least one known title: {len(matched):,}")
dec = collections.Counter(c["issue"][:3] + "0s" for c in cands)
dm = collections.Counter(c["issue"][:3] + "0s" for c in matched)
print("by decade (all / with a known title):", ", ".join(f"{d} {dec[d]:,}/{dm[d]:,}" for d in sorted(dec)))
top = collections.Counter(f"{t['title']} ({t['town']})" for c in matched for t in c["titles"])
print("most-named titles:", top.most_common(12))
print("most common terms:", collections.Counter(t for c in cands for t in c["terms"]).most_common(10))
