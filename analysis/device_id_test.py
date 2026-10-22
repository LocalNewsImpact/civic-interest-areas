"""Are device IDs stable across weeks within a month?  One-directional test, March 2026, Missouri.

For block groups where one business takes >= 80% of the weekly visitors to businesses there:
  monthly   = Neighborhood Patterns Plus DEVICE_COUNTS: distinct devices seen in the block group in March (Mar 1-31)
  weekly    = that business's VISITOR_COUNTS (Weekly Patterns Plus) summed over the four full weeks Mar 2-29
monthly >= the business's own monthly distinct visitors. So monthly < weekly sum means the same devices were recognised
in more than one week: stable IDs. monthly >= weekly sum is inconclusive. Both products are normalized to population
(Advan, "normalized against panel size and country population"), possibly with different factors: read the spread,
not a single block group.
"""
import csv
import gzip
import glob
import sys
from collections import defaultdict

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

csv.field_size_limit(sys.maxsize)
root = "/Users/kiesowd/VSCode/advan"
WEEKS = ("2026-03-02", "2026-03-09", "2026-03-16", "2026-03-23")
vis = defaultdict(lambda: defaultdict(float))       # cbg -> place -> summed weekly visitors
weekly_tot = defaultdict(lambda: defaultdict(float))  # cbg -> week -> all businesses' visitors
for f in sorted(glob.glob(root + "/weekly/raw/*.parquet")):
    wk = f.split("/")[-1][:10]
    if wk not in WEEKS:
        continue
    t = pq.read_table(f, columns=["PERSISTENT_ID", "POI_CBG", "VISITOR_COUNTS", "LOCATION_NAME", "TOP_CATEGORY"]).to_pandas()
    t = t[t.POI_CBG.notna()]
    t["v"] = t.VISITOR_COUNTS.astype(float)
    for r in t.itertuples():
        vis[r.POI_CBG][(r.PERSISTENT_ID, r.LOCATION_NAME, (r.TOP_CATEGORY or "").strip())] += r.v
        weekly_tot[r.POI_CBG][wk] += r.v
dev = {}
with gzip.open(glob.glob(root + "/neighborhood/raw/2026-03-01--*.csv.gz")[0], "rt") as fh:
    for r in csv.DictReader(fh):
        dev[r["AREA"]] = float(r["DEVICE_COUNTS"] or 0)
rows = []
for cbg, places in vis.items():
    if cbg not in dev or dev[cbg] <= 0:
        continue
    tot = sum(places.values())
    (pid, name, cat), top = max(places.items(), key=lambda kv: kv[1])
    if tot > 0 and top / tot >= 0.8 and top >= 500:
        rows.append((cbg, name, cat, dev[cbg], top, dev[cbg] / top))
d = pd.DataFrame(rows, columns=["cbg", "business", "category", "monthly_devices", "weekly_visitors_summed", "ratio"])
print(f"{len(d)} block groups dominated by one business (>= 80% of visitors, >= 500 summed weekly visitors)")
print(f"monthly distinct devices / summed weekly visitors of the one business: median {d.ratio.median():.2f}, "
      f"middle half {d.ratio.quantile(.25):.2f}-{d.ratio.quantile(.75):.2f}")
print(f"share of block groups where monthly < weekly sum (stable-ID evidence): {np.mean(d.ratio < 1):.0%}; below 0.5: {np.mean(d.ratio < .5):.0%}")
print("by category (10+ block groups):")
for cat, g in d.groupby("category"):
    if len(g) >= 10:
        print(f"  {cat}: {len(g)}, median ratio {g.ratio.median():.2f}, below 1: {np.mean(g.ratio < 1):.0%}")
d.to_csv(root + "/analysis/device_id_test.csv", index=False)
