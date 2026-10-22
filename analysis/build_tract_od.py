"""Tract-to-county travel, Missouri, Jan-Sep 2026 -> analysis/od_tract_mo_2026.csv

Origins below county level: a county's residents do not travel as one -- north Audrain leans toward Hannibal (and
Illinois), south Audrain toward Columbia. From the raw Advan Neighborhood Patterns Plus files (Missouri destinations),
home block group -> destination county, summed to home TRACT (2020; August-September home codes are 2010 block groups,
whose tract codes are kept as given) x destination county x month: all-day and work-behaviour devices.
"""
import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

csv.field_size_limit(sys.maxsize)
root = Path(__file__).resolve().parents[1]
cells = defaultdict(lambda: [0, 0])
for f in sorted((root / "neighborhood/raw").glob("*.csv.gz")):
    month = f.name[:7]
    with gzip.open(f, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            dest = r["AREA"][:5]
            for k, col in enumerate(("DEVICE_HOME_AREAS", "WORK_BEHAVIOR_DEVICE_HOME_AREAS")):
                for h, v in json.loads(r[col] or "{}").items():
                    if h.startswith("29"):
                        cells[(month, h[:11], dest)][k] += v
    print(month, flush=True)
with open(root / "analysis/od_tract_mo_2026.csv", "w", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["month", "home_tract", "dest_county", "all_day", "work_behavior"])
    for (m, t, d), v in sorted(cells.items()):
        w.writerow([m, t, d, *v])
print(len(cells), "cells")
