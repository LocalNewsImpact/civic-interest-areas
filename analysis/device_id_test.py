"""Are device IDs stable across weeks within a month?  One-directional, cross-product comparison, March 2026, Missouri.

For block groups where one business takes >= 80% of the weekly visitors to businesses there:
  monthly   = Neighborhood Patterns Plus DEVICE_COUNTS: distinct devices seen in the block group in March (Mar 1-31)
  weekly    = that business's VISITOR_COUNTS (Weekly Patterns Plus) summed over the four full weeks Mar 2-29
A business is one PERSISTENT_ID_STORE (one place). PERSISTENT_ID is not a place key: it is shared by unrelated places
(2,225 values for 100,596 places in a week, e.g. "A1_NAICS-561622"), so the 2026-10-16 run merged different places.
monthly >= the business's own monthly distinct visitors. So monthly < weekly sum would mean the same devices were
recognised in more than one week -- IF both products carried the same scale. They need not: both are "normalized
against panel size and country population", each by its own factor. same_scale = monthly >= the business's busiest
single week (the least a consistent scale requires).
Result reading (review 2026-10-24): this comparison cannot establish stable IDs, because the scales of the two
products are not known to match; a within-product test is not possible -- no Advan product on disk reports distinct
devices over more than one week for one place (Weekly Patterns is one week; Neighborhood Patterns is one month, no
weeks). The claim "IDs are stable week to week" is withdrawn.
"""
import csv
import glob
import gzip
import sys
from collections import defaultdict

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

csv.field_size_limit(sys.maxsize)
root = "/Users/kiesowd/VSCode/advan"
WEEKS = ("2026-03-02", "2026-03-09", "2026-03-16", "2026-03-23")
vis = defaultdict(lambda: defaultdict(float))        # cbg -> place -> summed weekly visitors
peak = defaultdict(float)                            # (cbg, place) -> busiest single week
for f in sorted(glob.glob(root + "/weekly/raw/*.parquet")):
    wk = f.split("/")[-1][:10]
    if wk not in WEEKS:
        continue
    t = pq.read_table(f, columns=["PERSISTENT_ID_STORE", "POI_CBG", "VISITOR_COUNTS", "LOCATION_NAME", "TOP_CATEGORY"]).to_pandas()
    t = t[t.POI_CBG.notna()]
    t["v"] = t.VISITOR_COUNTS.astype(float)
    for r in t.itertuples():
        k = (r.PERSISTENT_ID_STORE, r.LOCATION_NAME, (r.TOP_CATEGORY or "").strip())
        vis[r.POI_CBG][k] += r.v
        peak[(r.POI_CBG, k)] = max(peak[(r.POI_CBG, k)], r.v)
dev = {}
with gzip.open(glob.glob(root + "/neighborhood/raw/2026-03-01--*.csv.gz")[0], "rt") as fh:
    for r in csv.DictReader(fh):
        dev[r["AREA"]] = float(r["DEVICE_COUNTS"] or 0)
rows = []
for cbg, places in vis.items():
    if cbg not in dev or dev[cbg] <= 0:
        continue
    tot = sum(places.values())
    k, top = max(places.items(), key=lambda kv: kv[1])
    if tot > 0 and top / tot >= 0.8 and top >= 500:
        rows.append((cbg, k[0], k[1], k[2], dev[cbg], top, peak[(cbg, k)], dev[cbg] / top, int(dev[cbg] >= peak[(cbg, k)])))
d = pd.DataFrame(rows, columns=["cbg", "place_id", "business", "category", "monthly_devices", "weekly_visitors_summed",
                                "weekly_visitors_peak", "ratio", "same_scale"])
print(f"{len(d)} block groups dominated by one business (>= 80% of visitors, >= 500 summed weekly visitors)")
print(f"monthly distinct devices / summed weekly visitors of the one business: median {d.ratio.median():.2f}, "
      f"middle half {d.ratio.quantile(.25):.2f}-{d.ratio.quantile(.75):.2f}")
print(f"monthly < weekly sum: {(d.ratio < 1).sum()} ({np.mean(d.ratio < 1):.0%}); of these, monthly >= busiest week (same-scale "
      f"check): {((d.ratio < 1) & (d.same_scale == 1)).sum()}; monthly below busiest week (scales differ): "
      f"{(d.same_scale == 0).sum()} of all {len(d)}")
print("by category (10+ block groups):")
for cat, g in d.groupby("category"):
    if len(g) >= 10:
        print(f"  {cat}: {len(g)}, median ratio {g.ratio.median():.2f}, below 1: {np.mean(g.ratio < 1):.0%}")
print("Reading: a cross-product comparison with unknown relative scales; no within-product test exists on disk. "
      "The claim of week-to-week stable IDs is withdrawn.")
d.to_csv(root + "/analysis/device_id_test.csv", index=False)
