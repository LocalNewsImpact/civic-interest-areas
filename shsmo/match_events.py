"""Extracted events matched to known papers, and repeats of one event collapsed into one record.

Matching. A paper is placed in a town first: the town the passage gives, or a Missouri town whose
name the paper's own title carries ("Kahoka Gazette-Herald"). Within that town its title is compared
with the SHSMO catalogue and the outlet registry on the words left after the town and the words
"the", "daily", "weekly" are taken out ("Cameron Daily Vindicator" and "Daily vindicator" both leave
"vindicator"). Equal words, or 90% similar with the spaces taken out, is a match. A paper with no town is matched only on a full
title held by one town alone; when the passage gives another town, that match is marked for review.

Repeats. Overlapping passages state one sentence more than once; that is one mention. Mentions of one
paper, one event type and one new owner (by surname) are one event, unless the years they state are
more than a year apart.

Placing. A bare title with no town ("the Herald") is placed from its passage: the passage's own
fuller name for it, or the nearest town named before the event that holds a paper of that title.
Such a mention says how it was placed, for review. The event's year is the year a mention states; failing that, the issue it is
reported in, marked so.

Writes events.csv (one row per event), mentions.csv (one row per mention, with its page link) and
unmatched_titles.csv (papers no list holds, by how often they are named).
"""

import collections
import csv
import datetime as dt
import difflib
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
LOOK = Path.home() / "VSCode/NewsCrawler/MizzouNewsCrawler/src/lookups"
FILLER = {"the", "daily", "weekly", "semi", "tri", "and", "a", "mo", "missouri"}
WEB = re.compile(r"\b(web ?site|online|internet|e-edition|facebook|web page|digital edition)\b", re.I)


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower().replace("st.", "saint")
                                      .replace("ste.", "sainte"))).strip()


def core(title, town):
    toks = [t for t in norm(title).split() if t not in FILLER]
    tt = norm(town).split()
    for i in range(len(toks) - len(tt) + 1):         # take the town out once, wherever it sits
        if tt and toks[i:i + len(tt)] == tt:
            toks = toks[:i] + toks[i + len(tt):]
            break
    return " ".join(toks)


# known papers, by town
known = collections.defaultdict(list)                 # norm town -> [record]
for r in csv.DictReader(open(LOOK / "newspaper_history/shsmo_missouri_titles.csv")):
    known[norm(r["town"])].append({"list": "shsmo", "title": r["title"], "town": r["town"], "county": r["county"],
                                   "start": r["start_year"], "end": r["end_year"]})
for r in csv.DictReader(open(LOOK / "mo_outlet_registry.csv")):
    if "broadcast" in r["type"]:
        continue
    known[norm(r["city"])].append({"list": "registry", "title": r["outlet"], "town": r["city"], "county": r["county"],
                                   "outlet_id": r["outlet_id"],
                                   "owner": r["owner"], "status": r["status"]})
towns = sorted((t for t in known if t), key=len, reverse=True)
# a two-word town the press runs together ("LaBelle", "DeSoto") is read as the catalogue spells it
JOINED = {t.replace(" ", ""): t for t in towns if " " in t and len(t.replace(" ", "")) >= 6}


def canon(s):
    return " ".join(JOINED.get(w, w) for w in norm(s).split())
by_full = collections.defaultdict(set)                # norm title -> towns that hold it
for t, recs in known.items():
    for k in recs:
        by_full[norm(k["title"])].add(t)


def year_of(s):
    m = re.search(r"\b(18[2-9]\d|19\d\d|20[0-2]\d)\b", s or "")
    return int(m.group(1)) if m else None


MONTHS = {m: i for i, ms in enumerate((("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"),
                                       ("may",), ("jun", "june"), ("jul", "july"), ("aug", "august"),
                                       ("sep", "sept", "september"), ("oct", "october"), ("nov", "november"),
                                       ("dec", "december")), 1) for m in ms}
_MON = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?"
_FULL = re.compile(_MON + r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(18[2-9]\d|19\d\d|20[0-2]\d)\b", re.I)
_MDAY = re.compile(r"\b" + _MON + r"\s+(\d{1,2})(?:st|nd|rd|th)?\b(?!,?\s*\d{4})", re.I)
_MYEAR = re.compile(r"\b" + _MON + r",?\s+(?:of\s+)?(18[2-9]\d|19\d\d|20[0-2]\d)\b", re.I)
_MONLY = re.compile(r"^\s*(?:early|late|mid-?|in|on|the end of|the first of)?\s*" + _MON + r"\s*$", re.I)
NUMBER = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
          "a": 1, "twenty": 20, "twenty-five": 25, "thirty": 30, "forty": 40, "fifty": 50}


def _nearest(month, day, issue):
    """A month and day with no year: the year that puts it nearest the issue,
    no more than two months ahead of it (a sale announced for the coming
    month) and otherwise before it -- the press reports what has happened.
    "Jan. 1" in a December issue is the January after; "March" in a November
    issue the March before."""
    iy, im = int(issue[:4]), int(issue[5:7])
    ref = dt.date(iy, im, 15)
    best = None
    for y in (iy - 1, iy, iy + 1):
        try:
            d = dt.date(y, month, day)
        except ValueError:
            return None
        if not -335 <= (d - ref).days <= 62:
            continue
        if best is None or abs((d - ref).days) < abs((best - ref).days):
            best = d
    return best


def date_of(text, issue, whole=True):
    """(date, precision) the text states, read against the issue it is in:
    "Oct. 9" in the December 2002 issue is 2002-10-09, "this month" the
    issue's month, "last year" the year before. `whole` is False for a quote,
    where a month and day or a year is taken but not "this month" or a bare
    month name."""
    t = (text or "").strip()
    if not t:
        return None
    iy, im = int(issue[:4]), int(issue[5:7])
    m = _FULL.search(t)
    if m:
        try:
            return dt.date(int(m.group(3)), MONTHS[m.group(1).lower()[:3]], int(m.group(2))), "day"
        except (KeyError, ValueError):
            pass
    m = _MYEAR.search(t)
    if m:
        return dt.date(int(m.group(2)), MONTHS[m.group(1).lower()[:3]], 1), "month"
    y = year_of(t)
    if y:
        return dt.date(y, 1, 1), "year"
    m = _MDAY.search(t)
    if m:
        d = _nearest(MONTHS[m.group(1).lower()[:3]], int(m.group(2)), issue)
        return (d, "day") if d else None
    if not whole:
        return None
    low = t.lower()
    if re.search(r"\bthis month\b", low):
        return dt.date(iy, im, 1), "month"
    if re.search(r"\blast month\b", low):
        return (dt.date(iy, im - 1, 1) if im > 1 else dt.date(iy - 1, 12, 1)), "month"
    if re.search(r"\b(?:last|a year ago)\b", low) and "year" in low:
        return dt.date(iy - 1, 1, 1), "year"
    m = re.search(r"\b(\d+|[a-z]+(?:[- ][a-z]+)?)(?: and a half)? years? ago\b", low)
    if m:
        n = number(m.group(1))
        if n:
            return dt.date(iy - n, 1, 1), "year"
    m = _MONLY.match(t)
    if m:
        d = _nearest(MONTHS[m.group(1).lower()[:3]], 1, issue)
        return (d, "month") if d else None
    return None


_AGO = re.compile(r"\b(\d+|[a-z]+(?:[- ][a-z]+)?)(?: and a half)? years? ago\b", re.I)
UNITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
         "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}


def number(w):
    """12, "twelve", "twenty-one", "a" -> an integer, or None."""
    w = w.lower().replace(" ", "-")
    if w.isdigit():
        return int(w)
    if w in ("a", "one"):
        return 1
    if w in UNITS:
        return UNITS.index(w)
    head, _, tail = w.partition("-")
    if head in TENS and (not tail or tail in UNITS[1:10]):
        return TENS[head] + (UNITS.index(tail) if tail else 0)
    if tail and number(tail) is not None and head not in TENS:   # "about-ten" -> "ten"
        return number(tail)
    return None
_ANNIV = re.compile(r"\b(\d+)(?:st|nd|rd|th)\s+(?:anniversary|birthday|year of (?:publication|service))\b", re.I)


def ago(quote, issue, event_type):
    """A year the quote gives relative to its issue: "125 years ago" is the
    issue's year less 125; a founding "marks its 75th anniversary" the
    issue's year less 75."""
    q, iy = quote or "", int(issue[:4])
    m = _AGO.search(q)
    if m:
        n = number(m.group(1))
        if n:
            return dt.date(iy - n, 1, 1), "year"
    m = _ANNIV.search(q)
    if m and event_type == "founded":
        return dt.date(iy - int(m.group(1)), 1, 1), "year"
    return None


def match(paper, town):
    """Best known paper for (paper, town): (record or None, how)."""
    p, town = canon(paper), canon(town)
    paper = p
    cand_towns = []
    if town in known:
        cand_towns.append(town)
    for t in towns:                                   # a town the title itself carries
        if f" {t} " in f" {p} " and t not in cand_towns:
            cand_towns.append(t)
    best, how = None, None
    for t in cand_towns:
        pc = core(paper, t)
        for k in known[t]:
            kc = core(k["title"], t)
            if not pc or not kc:
                if norm(k["title"]) == p:
                    return k, "title"
                continue
            if pc.replace(" ", "") == kc.replace(" ", ""):
                score = 1.0
            else:                                     # 90% on the words run together: OCR and hyphens, not
                score = difflib.SequenceMatcher(None, pc.replace(" ", ""), kc.replace(" ", "")).ratio()
                if score < 0.9:                       # "Republican" against "Republic" (0.89)
                    continue
            yr = event_year[0]
            if yr and k.get("start", "").isdigit() and k.get("end", "").isdigit():
                score += 0.01 if int(k["start"]) <= yr <= int(k["end"]) else 0
            if k["list"] == "registry":
                score += 0.005
            if best is None or score > best[0]:
                best = (score, k)
    if best:
        return best[1], "exact" if best[0] >= 1 else "close"
    held = by_full.get(p, set())                      # no town: a full title one town alone holds
    if len(held) == 1 and len(p.split()) >= 2:
        t = next(iter(held))
        k = next(k for k in known[t] if norm(k["title"]) == p)
        return k, "title" if not town or town == t else "title held elsewhere"
    return None, None


def place(paper, quote, passage):
    """A paper the passage names by a bare title ("the Herald"): its town, read from the passage.

    The passage's own fuller name for it first ("Osage Beach Lake Sun" for "Lake Sun"); failing that,
    the towns the passage names before the event, nearest first. A town is taken only if a paper of
    that title is known there, so a town named in passing never places a paper it does not hold.
    Returns (record, basis) or (None, None)."""
    flat = canon(passage)
    t = canon(paper)
    t = t[4:] if t.startswith("the ") else t
    if not t:
        return None, None
    for town in towns:                                # 1. "<town> <title>" in the passage
        if f" {town} {t} " in f" {flat} ":
            k, _ = match(paper, town)
            if k:
                return k, "full name in the passage"
    at = flat.find(canon(quote)[:40]) if quote else -1
    before = flat[:at] if at > 0 else flat
    seen_at = sorted(((before.rfind(f" {town} "), town) for town in towns if f" {town} " in f" {before} "), reverse=True)
    for _, town in seen_at:                           # 2. the nearest town named before the event
        k, _ = match(paper, town)
        if k:
            return k, "town read from the passage"
    return None, None


passages = [json.loads(l)["passage"] for l in open(HERE / "candidates.jsonl")]
event_year = [None]
mentions, seen = [], set()
for line in open(HERE / "extracted.jsonl"):
    r = json.loads(line)
    for e in r.get("events", []):
        quote = norm(e.get("quote"))
        if (r["link"], quote) in seen:                # overlapping passages: one sentence, one mention
            continue
        seen.add((r["link"], quote))
        # the model's date for this event, read against the issue; the quote only for "N years ago" or
        # an "Nth anniversary" -- a year in the quote is usually someone else's ("owned by the Dorsey
        # family since 1919", "the Rays, who bought the paper in 1996, sold it to Touchdown")
        when = date_of(e.get("date"), r["issue"]) or ago(e.get("quote"), r["issue"], e.get("event_type"))
        stated = when[0].year if when else None
        misread = None
        if stated and stated > int(r["issue"][:4]) + 1:   # no sale is announced decades ahead: a misread
            misread, stated, when = stated, None, None
        event_year[0] = stated or int(r["issue"][:4])
        k, how = match(e.get("paper"), e.get("town"))
        flags = []
        if not k and not (e.get("town") or "").strip() and e.get("paper"):
            k, basis = place(e.get("paper"), e.get("quote"), passages[r["idx"]])
            if k:
                how = "placed"
                flags.append(f"placed: {basis}")
        if e.get("review"):
            flags.append(e["review"])
        if e.get("event_type") == "founded" and WEB.search(e.get("quote") or ""):
            flags.append("a website, not a paper")
        if not k and not (e.get("town") or "").strip():
            flags.append("paper not placed in a town")
        if how == "title held elsewhere":
            flags.append(f"title known only in {k['town']}")
        if stated and stated > int(r["issue"][:4]):    # a sale announced for the coming January
            flags.append(f"year {stated} is after the issue")
        if misread:
            flags.append(f"year {misread} misread: after the issue, so dated by the issue")
        if e.get("quote_match") == "fuzzy":
            flags.append("quote matched through OCR noise")
        mentions.append({
            "issue": r["issue"], "page": r["page"], "link": r["link"],
            "paper": (e.get("paper") or "").strip(), "town": (e.get("town") or "").strip() or (k or {}).get("town", ""),
            "press_town": (e.get("town") or "").strip(),
            "event_type": {"sold": "ownership_change", "bought": "ownership_change"}.get(e.get("event_type"), e.get("event_type")),
            "from": e.get("from") or "", "to": e.get("to") or "", "date_stated": e.get("date") or "",
            "year": event_year[0], "year_basis": "stated" if stated else "issue",
            "date": when[0].isoformat() if when else "", "date_precision": when[1] if when else "",
            "known_title": (k or {}).get("title", ""), "known_town": (k or {}).get("town", ""),
            "county": (k or {}).get("county", ""), "list": (k or {}).get("list", ""), "match": how or "none",
            "outlet_id": (k or {}).get("outlet_id", ""),
            "flags": "; ".join(flags), "quote": e.get("quote") or "", "passage": passages[r["idx"]],
        })


def surname(s):
    words = re.findall(r"[A-Z][a-z]+", s or "")
    words = [w for w in words if w not in {"Mr", "Mrs", "Inc", "Co", "Company", "Corp", "And", "The", "Publishing",
                                           "Publications", "Publishers", "Newspapers", "Newspaper", "Media",
                                           "Communications", "Group", "Enterprises", "Holdings", "Partners",
                                           "Associates", "Jr", "Sr"}]
    return words[-1].lower() if words else ""


# one event: one paper, one type, one new owner; years more than one apart are separate events
groups = collections.defaultdict(list)
for m in mentions:
    paper_key = (norm(m["known_title"]), norm(m["known_town"])) if m["known_title"] else (norm(m["paper"]), norm(m["town"]))
    m["paper_key"] = paper_key
    groups[(paper_key, m["event_type"], surname(m["to"]))].append(m)
RANK = {"day": 0, "month": 1, "year": 2}


def _best_date(st):
    if not st:
        return {"date": "", "date_precision": "", "date_stated": ""}
    year = collections.Counter(m["year"] for m in st).most_common(1)[0][0]
    pick = min((m for m in st if m["year"] == year), key=lambda m: (RANK[m["date_precision"]], m["issue"]))
    return {"date": pick["date"], "date_precision": pick["date_precision"], "date_stated": pick["date_stated"]}


events = []
for key, ms in groups.items():
    stated = sorted({m["year"] for m in ms if m["year_basis"] == "stated"})
    clusters = []                                     # stated years split the group; unstated join the nearest
    for y in stated:
        if clusters and y - clusters[-1][-1] <= 1:
            clusters[-1].append(y)
        else:
            clusters.append([y])
    buckets = [[] for _ in clusters]
    undated = []                                      # reports with no year and no dated event before them
    for m in ms:
        if m["year_basis"] == "stated":
            buckets[next(i for i, c in enumerate(clusters) if m["year"] in c)].append(m)
            continue
        # reported in an issue: the event is on or before it, so it is never a later dated event
        prior = [i for i, c in enumerate(clusters) if c[0] <= m["year"]]
        if prior:
            buckets[prior[-1]].append(m)
        else:
            undated.append(m)
    buckets.append(undated)
    for b in buckets:
        if not b:
            continue
        b.sort(key=lambda m: m["issue"])
        st = [m for m in b if m["year_basis"] == "stated"]
        first = b[0]
        events.append({
            "paper": collections.Counter(m["paper"] for m in b if m["paper"]).most_common(1)[0][0]
            if any(m["paper"] for m in b) else first["known_title"],
            "known_title": first["known_title"], "outlet_id": first["outlet_id"],
            # the town the press gave, where it gave one; the matched title's town otherwise
            "town": collections.Counter(m["press_town"] for m in b if m["press_town"]).most_common(1)[0][0]
            if any(m["press_town"] for m in b) else (first["known_town"] or first["town"]),
            "known_town": first["known_town"],
            "county": first["county"], "event_type": first["event_type"],
            "year": collections.Counter(m["year"] for m in st).most_common(1)[0][0] if st else int(first["issue"][:4]),
            "year_basis": "stated" if st else "first report",
            # the most exact date the reports state, the earliest report's first
            **_best_date(st),
            "from": max((m["from"] for m in b), key=len), "to": max((m["to"] for m in b), key=len),
            "matched_to": first["list"] or "none", "match": first["match"],
            "names_in_press": "; ".join(sorted({m["paper"] for m in b})),
            "mentions": len(b), "first_reported": first["issue"], "last_reported": b[-1]["issue"],
            "link": first["link"], "page": first["page"], "quote": first["quote"], "passage": first["passage"],
            "flags": "; ".join(sorted({f for m in b for f in m["flags"].split("; ") if f})),
            "all_links": " ".join(dict.fromkeys(m["link"] for m in b)),
        })
events.sort(key=lambda e: (e["town"], e["paper"], e["year"]))

with open(HERE / "mentions.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(mentions[0]))
    w.writeheader(); w.writerows(mentions)
with open(HERE / "events.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(events[0]))
    w.writeheader(); w.writerows(events)
un = collections.Counter((m["paper"], m["town"]) for m in mentions if m["match"] == "none" and m["paper"])
with open(HERE / "unmatched_titles.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["paper", "town", "mentions"])
    for (p, t), n in un.most_common():
        w.writerow([p, t, n])

c = collections.Counter
print(f"mentions after overlap removed: {len(mentions):,}; events: {len(events):,}")
print("mentions matched:", dict(c(m["match"] for m in mentions)), "by list:", dict(c(m["list"] or "none" for m in mentions)))
print("events matched:", dict(c(e["matched_to"] for e in events)))
print("events by type:", dict(c(e["event_type"] for e in events).most_common()))
print("events by year basis:", dict(c(e["year_basis"] for e in events)))
print("events by decade:", dict(sorted(c(f"{e['year'] // 10 * 10}s" for e in events).items())))
print("events flagged:", dict(c(f for e in events for f in e["flags"].split("; ") if f)))
print("distinct papers in events:", len({(norm(e['paper']), norm(e['town'])) for e in events}),
      "of which matched:", len({(norm(e['paper']), norm(e['town'])) for e in events if e['matched_to'] != 'none'}))
print("most-named unmatched:", un.most_common(15))
