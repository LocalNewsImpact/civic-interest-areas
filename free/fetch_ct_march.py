"""March 2021 weekly tract-to-tract flows for residents of Audrain, Boone and Osage.

Each GeoDS week is 20 CSVs. The files are not sorted by origin -- a file's first and last
rows do not bound what is inside it -- so every file is read to the end and rows are kept
when the origin tract is in one of the three counties. Five files are read at a time.
"""

import csv
import io
import sys
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = ("https://raw.githubusercontent.com/GeoDS/COVID19USFlows-WeeklyFlows-Ct2021/"
        "master/weekly_flows/ct2ct/{w}/weekly_ct2ct_{w}_{i}.csv")
WEEKS = ["2021_03_01", "2021_03_08", "2021_03_15", "2021_03_22", "2021_03_29"]
KEEP = {"29007", "29019", "29151"}
OUT = sys.argv[1]
lock = threading.Lock()
HEAD = ["geoid_o", "geoid_d", "lng_o", "lat_o", "lng_d", "lat_d", "date_range", "visitor_flows", "pop_flows"]


def one(job):
    week, i = job
    kept = []
    for attempt in range(3):
        try:
            with urllib.request.urlopen(BASE.format(w=week, i=i), timeout=900) as r:
                rd = csv.reader(io.TextIOWrapper(r, encoding="utf-8"))
                assert next(rd) == HEAD
                kept = [row for row in rd if row[0][:5] in KEEP]
            break
        except Exception as e:                      # a dropped connection retries the whole file
            print(f"  retry {week} file {i}: {e}", flush=True)
    with lock:
        with open(OUT, "a", newline="") as fh:
            csv.writer(fh).writerows(kept)
        print(f"  {week} file {i:2d}: {len(kept):,} rows", flush=True)
    return len(kept)


with open(OUT, "w", newline="") as fh:
    csv.writer(fh).writerow(HEAD)
jobs = [(w, i) for w in WEEKS for i in range(20)]
with ThreadPoolExecutor(max_workers=5) as ex:
    total = sum(ex.map(one, jobs))
print(f"DONE {total:,} rows from {len(jobs)} files -> {OUT}", flush=True)
