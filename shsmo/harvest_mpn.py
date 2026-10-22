"""Polite collection of Missouri Press News (SHSMO CONTENTdm collection `lhs`).

One request a minute, single-threaded, with a contact address in the user-agent. Every
response is written to cache/ before the next request, and a cached response is never
fetched again, so the run can be stopped and resumed at no cost to SHSMO.

Two limits of the API shape the plan:
  * a search pages through only its first ~10,000 results, and ignores a requested sort;
  * page titles are "Page N" with N restarting at every ISSUE, so one number matches ~450 pages.

  1. the 75 volume records (one request)
  2. the 75 volume page lists: every page's record number and title, the authoritative set
  3. title searches by page number, sliced from the real title counts so each slice stays
     under 9,000 results, 1,024 pages per request with OCR text and record number
  4. pages whose title carries no number (covers and the like), fetched singly -- stops if
     there are more than 400
  5. five pages fetched singly to confirm the bulk text is not truncated
On a failed request it waits five minutes and tries once more; a second failure stops the run.
"""

import collections
import glob
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://digital.shsmo.org/digital/bl/dmwebservices/index.php?q="
UA = "Mizzou Journalism Researcher (dkiesow@missouri.edu)"
PACE = 60                                    # seconds between requests
SLICE_MAX = 9000                             # under the ~10,000 result window, with margin
HERE = Path(__file__).parent
CACHE = HERE / "cache"
CACHE.mkdir(exist_ok=True)
_last = [0.0]
n_requests = [0]


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def get(name, query):
    """Cached, paced GET of one API query; returns parsed JSON."""
    path = CACHE / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    for attempt in (1, 2):
        wait = PACE - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        n_requests[0] += 1
        try:
            req = urllib.request.Request(API + query, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read().decode("utf-8")
            data = json.loads(body)
            path.write_text(body)
            return data
        except Exception as e:
            log(f"  request failed ({name}, attempt {attempt}): {e}")
            if attempt == 2:
                log("STOPPING: second failure. Rerun to resume from the cache.")
                sys.exit(1)
            time.sleep(300)


def text(r, key):
    v = r.get(key)
    return v if isinstance(v, str) else ""


# 1. volumes
vols = get("volumes", "dmQuery/lhs/0/title!dmrecord/title/100/1/1/0/0/0/0/0/json")["records"]
log(f"volumes: {len(vols)}")

# 2. the volume page lists
listed = {}
for v in vols:
    info = get(f"volume_{v['pointer']}", f"dmGetCompoundObjectInfo/lhs/{v['pointer']}/json")
    pages_v = []

    def walk(node):                          # pages may sit flat or inside nested nodes
        if isinstance(node, list):
            for x in node:
                walk(x)
        elif isinstance(node, dict):
            if "pageptr" in node:
                pages_v.append(node)
            for k in ("page", "node"):
                if k in node:
                    walk(node[k])
    walk(info)
    for order, p in enumerate(pages_v, 1):
        listed[int(p["pageptr"])] = {"volume": v["pointer"], "order": order, "title": p.get("pagetitle", "")}
    log(f"  volume {v['pointer']}: {len(pages_v)} pages")
log(f"pages listed by the volumes: {len(listed):,}")
vt0 = {v["pointer"]: v["title"] for v in vols}
mpn = {p for p, m in listed.items() if vt0[m["volume"]].startswith("Missouri Press News")}
MPN_MAX = max((int(n) for p in mpn for n in re.findall(r"\b\d+\b", listed[p]["title"])), default=0)
log(f"Missouri Press News pages: {len(mpn):,} in {len({listed[p]['volume'] for p in mpn})} volumes; "
    f"highest page number {MPN_MAX} (the other {len(listed) - len(mpn):,} pages are two society newsletters)")

# pages already held from the first run's search batches
got = {}
for f in glob.glob(str(CACHE / "pages_*.json")) + glob.glob(str(CACHE / "slice_*.json")):
    for r in json.loads(Path(f).read_text())["records"]:
        got[int(r["pointer"])] = r
log(f"pages already cached with text: {len(got):,}")

# 3. number slices sized from the real titles. The Grand River newsletter is left out here: its
# pages are indexed under zero-padded titles ("0001") although its page list says "Page 1", so a
# search for "1" never finds them. They get their own search in 3c.
gr_vol = next(v["pointer"] for v in vols if v["title"].startswith("Newsletter of the Grand River"))
gr = {p for p, m in listed.items() if m["volume"] == gr_vol}
by_num = collections.defaultdict(set)
no_number = []
for ptr, m in listed.items():
    nums = re.findall(r"\b\d+\b", m["title"])
    if not nums:
        no_number.append(ptr)
    for n in nums:
        by_num[int(n)].add(ptr)
slices, cur, cur_set = [], [], set()
for n in sorted(by_num):
    if cur and (len(cur_set | by_num[n]) > SLICE_MAX or len(cur) >= 120):
        slices.append((cur, cur_set)); cur, cur_set = [], set()
    cur.append(n); cur_set |= by_num[n]
if cur:
    slices.append((cur, cur_set))
# Slices are computed exactly as before, Grand River pages included, so every query -- and the cache
# file it is stored under -- is unchanged. Slices that start above the highest page number outside
# Grand River held only Grand River pages, which a "Page N" search cannot find, so they are dropped.
top = max((int(n) for p, m in listed.items() if p not in gr for n in re.findall(r"\b\d+\b", m["title"])), default=0)
slices = [s for s in slices if s[0][0] <= top]
log(f"Grand River newsletter: {len(gr)} pages searched separately; highest page number elsewhere: {top}")
log(f"{len(slices)} number slices: " + ", ".join(f"{s[0][0]}-{s[0][-1]} ({len(s[1]):,})" for s in slices))
for k, (nums, expect) in enumerate(slices):
    q = urllib.parse.quote(" ".join(map(str, nums)))
    base = f"dmQuery/lhs/title^{q}^any^and/title!transc!identi!dmrecord/nosort/1024"
    first = get(f"slice_{k:02d}_00001", f"{base}/1/0/0/0/0/0/0/json")
    total = first["pager"]["total"]
    for r in first["records"]:
        got[int(r["pointer"])] = r
    if total >= 10000:
        log(f"STOPPING: slice {nums[0]}-{nums[-1]} returned {total:,} results, past the 10,000 window.")
        sys.exit(3)
    seen = {int(r["pointer"]) for r in first["records"]}
    log(f"  slice {nums[0]}-{nums[-1]} batch at 1: {len(first['records'])} pages")
    for start in range(1025, total + 1, 1024):
        recs = get(f"slice_{k:02d}_{start:05d}", f"{base}/{start}/0/0/0/0/0/0/json")["records"]
        fresh = {int(r["pointer"]) for r in recs} - seen
        for r in recs:
            got[int(r["pointer"])] = r
        seen |= fresh
        log(f"  slice {nums[0]}-{nums[-1]} batch at {start}: {len(recs)} pages, {len(fresh)} new to this slice")
        # fail fast: a batch whose pages all came in earlier batches of this slice means the search
        # is repeating itself. Compared within the slice, so batches read back from the cache count.
        if not fresh:
            log(f"STOPPING: slice {nums[0]}-{nums[-1]} batch at {start} repeated earlier batches.")
            sys.exit(4)
    # A few pages are simply absent from the search index (pages 1-10 of the Grand River newsletter);
    # those are fetched singly in step 4. Only a shortfall big enough to mean the search itself failed
    # stops the run.
    expect = expect - gr                         # Grand River is searched separately in 3c
    held = len(expect & set(got))
    short = len(expect) - held
    log(f"  slice {nums[0]}-{nums[-1]}: search total {total:,}; expected {len(expect):,}, held {held:,}, short {short}")
    if short > max(25, 0.02 * len(expect)):
        log(f"STOPPING: slice {nums[0]}-{nums[-1]} is short by {short:,} pages.")
        sys.exit(5)

# 3b. covers carry no page number; one title search returns all of them
cov = get("covers_00001", "dmQuery/lhs/title^cover^all^and/title!transc!identi!dmrecord/nosort/1024/1/0/0/0/0/0/0/json")
if cov["pager"]["total"] > 1024:
    log(f"STOPPING: cover search returned {cov['pager']['total']:,}, more than one batch."); sys.exit(6)
for r in cov["records"]:
    got[int(r["pointer"])] = r
log(f"covers by title search: {cov['pager']['total']}")

# 3c. the Grand River newsletter by its zero-padded titles, 100 numbers to a request
for lo in range(1, len(gr) + 1, 100):
    toks = " ".join(f"{n:04d}" for n in range(lo, min(lo + 99, len(gr)) + 1))
    res = get(f"grandriver_{lo:04d}",
              f"dmQuery/lhs/title^{urllib.parse.quote(toks)}^any^and/title!transc!identi!dmrecord/nosort/1024/1/0/0/0/0/0/0/json")
    ptrs = {int(r["pointer"]) for r in res["records"]}
    for r in res["records"]:
        got[int(r["pointer"])] = r
    log(f"  Grand River {lo:04d}-{min(lo + 99, len(gr)):04d}: {len(ptrs)} pages, {len(ptrs & gr)} in the newsletter")
    if not ptrs & gr:
        log("STOPPING: zero-padded title search found no Grand River pages."); sys.exit(7)

# 4. any page still missing, fetched singly
missing = sorted(set(listed) - set(got))
log(f"still missing after the slices: {len(missing)} (titles without a number: {len(no_number)})")
if len(missing) > 400:
    log(f"STOPPING: {len(missing)} pages is too many to fetch singly. Cache is kept.")
    sys.exit(2)
for ptr in missing:
    got[ptr] = get(f"page_{ptr}", f"dmGetItemInfo/lhs/{ptr}/json") | {"pointer": ptr}

# 5. truncation check
for ptr in sorted(listed)[:: max(1, len(listed) // 5)][:5]:
    single = get(f"check_{ptr}", f"dmGetItemInfo/lhs/{ptr}/json")
    a, b = text(got.get(ptr, {}), "transc"), text(single, "transc")
    log(f"  truncation check {ptr}: bulk {len(a)} chars, single {len(b)} chars {'OK' if a == b else 'DIFFERS'}")

# assemble: one line per page, in volume and page order, with its link
vt = {v["pointer"]: v["title"] for v in vols}
with open(HERE / "pages.jsonl", "w") as out:
    for ptr, m in sorted(listed.items(), key=lambda kv: (vt.get(kv[1]["volume"], ""), kv[1]["order"])):
        r = got.get(ptr, {})
        out.write(json.dumps({
            "volume_pointer": m["volume"], "volume_title": vt.get(m["volume"]),
            "page_pointer": ptr, "page_title": m["title"], "page_order": m["order"],
            "identifier": text(r, "identi"),
            "link": f"https://digital.shsmo.org/digital/collection/lhs/id/{ptr}",
            "text": text(r, "transc"),
        }) + "\n")
empty = sum(1 for p in listed if not text(got.get(p, {}), "transc"))
log(f"DONE: {len(listed):,} pages written to pages.jsonl ({empty} with no OCR text); "
    f"{n_requests[0]} requests made this run")
