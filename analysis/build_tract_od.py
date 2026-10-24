"""Tract-to-county travel, Missouri, January-July 2026 -> analysis/od_tract_mo_2026.csv

Origins below county level: a county's residents do not travel as one -- north Audrain leans toward Hannibal (and
Illinois), south Audrain toward Columbia. From the raw Advan Neighborhood Patterns Plus files (Missouri destinations),
home block group -> destination county, summed to home TRACT (2020) x destination county x month: all-day and
work-behaviour devices. January-July only (2020 block groups, as activity_space.py): August-September home codes are
2010 block groups, whose tract codes name different areas (a 2010 tract code is not the 2020 tract of that number), so
those months cannot be added to 2020 tracts. Uncalibrated device counts (consumers use shares within a tract).
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
MONTHS = [f"2026-{m:02d}" for m in range(1, 8)]
for f in sorted((root / "neighborhood/raw").glob("*.csv.gz")):
    month = f.name[:7]
    if month not in MONTHS:
        continue
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
