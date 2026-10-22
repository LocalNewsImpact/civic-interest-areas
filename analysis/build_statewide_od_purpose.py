"""Statewide county-to-county travel BY PURPOSE, Missouri, Jan-Sep 2026 -> analysis/od_mo_2026_purpose.csv

From the raw Advan Neighborhood Patterns Plus files, as build_statewide_od.py, keeping four counts per home county x
destination county x month: all-day devices (DEVICE_HOME_AREAS), devices showing work behaviour at the destination
(WORK_BEHAVIOR_DEVICE_HOME_AREAS), weekday and weekend devices. Non-work travel = all-day - work behaviour.
Uncalibrated counts: the models use each origin's shares (origin fixed effects absorb the panel's size).
"""
import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

csv.field_size_limit(sys.maxsize)
root = Path(__file__).resolve().parents[1]
COLS = ("DEVICE_HOME_AREAS", "WORK_BEHAVIOR_DEVICE_HOME_AREAS", "WEEKDAY_DEVICE_HOME_AREAS", "WEEKEND_DEVICE_HOME_AREAS")
cells = defaultdict(lambda: [0, 0, 0, 0])
for f in sorted((root / "neighborhood/raw").glob("*.csv.gz")):
    month = f.name[:7]
    with gzip.open(f, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            dest = r["AREA"][:5]
            for k, col in enumerate(COLS):
                for h, v in json.loads(r[col] or "{}").items():
                    if h.startswith("29"):
                        cells[(month, h[:5], dest)][k] += v
    print(month, flush=True)
with open(root / "analysis/od_mo_2026_purpose.csv", "w", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["month", "home_county", "dest_county", "all_day", "work_behavior", "weekday", "weekend"])
    for (m, h, d), v in sorted(cells.items()):
        w.writerow([m, h, d, *v])
print(len(cells), "cells")
