"""Kansas county-to-county travel, January-September 2026 -> analysis/od_ks_2026.csv (the Kansas counterpart of
build_statewide_od.py). Advan Neighborhood Patterns Plus (Dewey): Kansas destination block groups from
neighborhood/raw_ks/*.parquet; Missouri destination block groups from neighborhood/raw/*.csv.gz (Kansans' visits to
Missouri). DEVICE_HOME_AREAS = home block group -> devices; summed to home county x destination county x month for
homes in Kansas. Columns: visits (all day), work_hours_visits."""
import csv
import glob
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

csv.field_size_limit(sys.maxsize)
root = Path(__file__).resolve().parents[1]
cells = defaultdict(lambda: [0, 0])
types = defaultdict(int)


def add(month, dest, home_json, work_json):
    for col, k in ((home_json, 0), (work_json, 1)):
        for h, v in json.loads(col or "{}").items():
            if h.startswith("20"):
                cells[(month, h[:5], dest)][k] += v


for f in sorted(glob.glob(str(root / "neighborhood/raw_ks/*.parquet"))):
    t = pq.read_table(f, columns=["AREA", "AREA_TYPE", "DATE_RANGE_START", "DEVICE_HOME_AREAS", "WORK_HOURS_DEVICE_HOME_AREAS"]).to_pylist()
    for r in t:
        types[r["AREA_TYPE"]] += 1
        add(str(r["DATE_RANGE_START"])[:7], r["AREA"][:5], r["DEVICE_HOME_AREAS"], r["WORK_HOURS_DEVICE_HOME_AREAS"])
    print("KS", Path(f).name[:10], len(t), "destination areas", flush=True)
for f in sorted(glob.glob(str(root / "neighborhood/raw/*.csv.gz"))):
    n = 0
    with gzip.open(f, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            if '"20' in (r["DEVICE_HOME_AREAS"] or ""):
                add(r["DATE_RANGE_START"][:7], r["AREA"][:5], r["DEVICE_HOME_AREAS"], r["WORK_HOURS_DEVICE_HOME_AREAS"])
            n += 1
    print("MO", Path(f).name[:10], n, "destination areas", flush=True)
print("area types:", dict(types))
with open(root / "analysis/od_ks_2026.csv", "w", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["month", "home_county", "dest_county", "visits", "work_hours_visits"])
    for (m, h, d), (v, wv) in sorted(cells.items()):
        w.writerow([m, h, d, v, wv])
print(len(cells), "cells")
