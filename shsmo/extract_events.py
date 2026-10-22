"""Newspaper ownership and publication events from candidate Missouri Press News passages.

Each passage in candidates.jsonl goes to DeepSeek V3.2 (via OpenRouter) once, at temperature 0, asking
for the events it states: the paper, its town, the event, seller, buyer, date and an exact quote. An
event is kept only if its quote is found in the passage, the same grounding rule Backfield applies.

Results are appended to extracted.jsonl as they arrive, keyed by passage index, so the run resumes
where it stopped. It stops itself on: spend over the ceiling; more than 5% of the first 200 calls
failing; more than 20% of the first 200 replies not being usable JSON.
"""

import difflib
import json
import os
import re
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
MODEL = "deepseek/deepseek-v3.2"
PRICE_IN, PRICE_OUT = 0.26 / 1e6, 0.80 / 1e6          # USD per token, OpenRouter list price 2026-10-12
CEILING = 8.00
WORKERS = 16
KEY = os.environ["OPENROUTER_API_KEY"]

SYSTEM = ("You extract newspaper ownership and publication events from Missouri Press News, the Missouri "
          "Press Association's trade magazine. Answer with JSON only.")
PROMPT = """Issue: {issue}
Passage:
<<<
{passage}
>>>

List every event in the passage in which a Missouri newspaper changed hands or status:
- ownership_change: sold, bought, acquired
- lease: leased to someone else
- merger: merged or consolidated with another paper
- founded: established, launched, first issue
- closed: suspended or ceased publication
- moved: moved to another town
- renamed: changed its name
Ignore hirings, retirements, deaths, awards, equipment or building purchases, and any paper outside
Missouri (a paper in Kansas, Illinois or any other state is never an event here). Report only events
about a specific, named paper; general remarks about newspapers are not events.

For each event give:
  paper: the newspaper as named in the passage
  town: its town, or null
  event_type: one of the types above
  from: seller or previous owner (people or company), or null
  to: buyer, lessee or new owner, or null
  date: the date as stated in the passage, or null
  quote: an exact span copied from the passage, at most 40 words, that states the event

Return {{"events": [...]}} -- an empty list if the passage states no such event."""

lock = threading.Lock()
spend = [0.0]
stats = {"done": 0, "fail": 0, "badjson": 0, "events": 0, "dropped": 0}


def flat(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()


def grounded(quote, passage):
    """A quote the model joined with an ellipsis is checked piece by piece; pieces under three words are
    skipped. Exact only if every piece is exact."""
    parts = [x for x in re.split(r"\.\.\.|\u2026", quote or "") if len(flat(x).split()) >= 3]
    if len(parts) > 1:
        res = [grounded_one(x, passage) for x in parts]
        if None in res:
            return None
        return "exact" if all(r == "exact" for r in res) else "fuzzy"
    return grounded_one(quote, passage)


def grounded_one(quote, passage):
    """'exact' if the quote is in the passage; 'fuzzy' if some span of the passage matches it word for word
    at 85% or better (OCR noise: "Star-LeaderYas been sold" against the model's "has been sold"); else None."""
    q, p = flat(quote), flat(passage)
    if not q:
        return None
    if q in p:
        return "exact"
    qt, pt = q.split(), p.split()
    n = len(qt)
    best = 0.0
    for size in (n - 2, n - 1, n, n + 1, n + 2):
        if size < 3:
            continue
        for i in range(0, max(1, len(pt) - size + 1)):
            r = difflib.SequenceMatcher(None, qt, pt[i:i + size], autojunk=False).ratio()
            if r > best:
                best = r
    return "fuzzy" if best >= 0.85 else None


def call(cand):
    body = json.dumps({
        "model": MODEL, "temperature": 0, "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": PROMPT.format(issue=cand["issue"], passage=cand["passage"])}],
    }).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body, headers={
        "Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
        "HTTP-Referer": "https://localnewsimpact.org", "X-Title": "Missouri Press News history"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(5 * (attempt + 1))
    return None


def work(idx, cand):
    resp = call(cand)
    rec = {"idx": idx, "issue": cand["issue"], "link": cand["link"], "page": cand["page"]}
    with lock:
        stats["done"] += 1
    if resp is None or "choices" not in resp:
        with lock:
            stats["fail"] += 1
        rec["error"] = "call failed"
        return rec
    u = resp.get("usage", {})
    with lock:
        spend[0] += u.get("prompt_tokens", 0) * PRICE_IN + u.get("completion_tokens", 0) * PRICE_OUT
    try:
        events = json.loads(resp["choices"][0]["message"]["content"]).get("events", [])
        assert isinstance(events, list)
    except Exception:
        with lock:
            stats["badjson"] += 1
        rec["error"] = "unusable JSON"
        return rec
    kept, dropped = [], []
    for e in events:
        if not isinstance(e, dict):
            continue
        how = grounded(e.get("quote"), cand["passage"])
        paper, town = (e.get("paper") or "").strip(), (e.get("town") or "").strip()
        if how is None:
            dropped.append(e | {"why": "quote not found in passage"})
        elif not paper and not town:
            dropped.append(e | {"why": "names neither a paper nor a town"})
        else:
            e["quote_match"] = how
            if not paper or re.fullmatch(r"(the )?(paper|newspaper|weekly|daily|journal|news)", paper.lower()):
                e["review"] = "paper not named in the passage"
            kept.append(e)
    with lock:
        stats["dropped"] += len(dropped)
    with lock:
        stats["events"] += len(kept)
    rec["events"] = kept
    rec["dropped"] = dropped
    return rec


cands = [json.loads(l) for l in open(HERE / "candidates.jsonl")]
SAMPLE = int(os.environ.get("SAMPLE", "0"))       # a test batch: N passages at random, to a separate file
out_path = HERE / ("extracted_test.jsonl" if SAMPLE else "extracted.jsonl")
done = set()
if out_path.exists() and not SAMPLE:
    done = {json.loads(l)["idx"] for l in open(out_path) if '"error"' not in l}
todo = [(i, c) for i, c in enumerate(cands) if i not in done]
if SAMPLE:
    import random
    random.seed(11)
    todo = random.sample(todo, SAMPLE)
    out_path.unlink(missing_ok=True)
print(time.strftime("%H:%M:%S"), f"{len(cands):,} passages; {len(done):,} already done; {len(todo):,} to run", flush=True)

out = open(out_path, "a")
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for n, rec in enumerate(ex.map(lambda ic: work(*ic), todo), 1):
        out.write(json.dumps(rec) + "\n"); out.flush()
        s = dict(stats)
        if n == 200 and (s["fail"] > 10 or s["badjson"] > 40):
            print(time.strftime("%H:%M:%S"), f"STOPPING after 200: {s['fail']} failed, {s['badjson']} unusable JSON", flush=True)
            os._exit(3)
        if spend[0] > CEILING:
            print(time.strftime("%H:%M:%S"), f"STOPPING: spend ${spend[0]:.2f} passed the ${CEILING:.2f} ceiling", flush=True)
            os._exit(4)
        if n % 250 == 0 or n == len(todo):
            print(time.strftime("%H:%M:%S"), f"{n:,}/{len(todo):,}  events kept {s['events']:,}  quotes not found {s['dropped']}  "
                  f"failed {s['fail']}  bad JSON {s['badjson']}  spend ${spend[0]:.2f}", flush=True)
print(time.strftime("%H:%M:%S"), "DONE", flush=True)
