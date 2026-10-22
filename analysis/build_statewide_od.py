"""Statewide county-to-county travel, Missouri, Jan-Sep 2026 -> ../analysis/od_mo_2026.csv

From the raw Advan Neighborhood Patterns Plus files (Dewey; one row per Missouri destination block group per month,
DEVICE_HOME_AREAS = home block group -> devices). Summed to home county x destination county x month, for homes in
Missouri; homes outside Missouri are kept as one total per destination county (home_county 'OUT'). Columns carry
the all-day count and the work-hours count.
"""
import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

csv.field_size_limit(sys.maxsize)
root = Path(__file__).resolve().parents[1]
RAW = root / "neighborhood/raw"
cells = defaultdict(lambda: [0, 0])
for f in sorted(RAW.glob("*.csv.gz")):
    month = f.name[:7]
    n = 0
    with gzip.open(f, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            dest = r["AREA"][:5]
            for col, k in (("DEVICE_HOME_AREAS", 0), ("WORK_HOURS_DEVICE_HOME_AREAS", 1)):
                for h, v in json.loads(r[col] or "{}").items():
                    home = h[:5] if h.startswith("29") else "OUT"
                    cells[(month, home, dest)][k] += v
            n += 1
    print(month, n, "destination block groups", flush=True)
with open(root / "analysis/od_mo_2026.csv", "w", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["month", "home_county", "dest_county", "visits", "work_hours_visits"])
    for (m, h, d), (v, wv) in sorted(cells.items()):
        w.writerow([m, h, d, v, wv])
print(len(cells), "cells")
