"""Distinct people, de-duplicated: statewide, Missouri, Jan-Sep 2026.

From the raw Advan Neighborhood Patterns Plus files. For each month, home block group h and destination county j:
  unique_lower(h, j) = people from h seen in j's single busiest block group     (all distinct people)
People from different home block groups are distinct, so a home COUNTY's figure is the sum over its block groups.
  od_unique_mo_2026.csv     month, home_county, dest_county, people_lower, people_summed  (summed = current measure)
  leaving_unique_mo_2026.csv  month, county, residents_seen_at_home, left_lower
      left_lower: per home block group, people seen in its single busiest block group OUTSIDE the home county
Each home block group's figures are capped at its residents seen at home (no more people can leave than live there).
Calibration: divide both by the county-month factor (calibration_county_month.csv) for people; shares are unaffected.
"""
import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

csv.field_size_limit(sys.maxsize)
root = Path(__file__).resolve().parents[1]
cal = {(r["county"], r["month"]): float(r["factor"]) for r in csv.DictReader(open(root / "analysis/calibration_county_month.csv"))}
low, summed = defaultdict(float), defaultdict(float)
home_seen, left = defaultdict(float), defaultdict(float)
for f in sorted((root / "neighborhood/raw").glob("*.csv.gz")):
    month = f.name[:7]
    best = defaultdict(float)            # (h, j) -> busiest block group count
    best_out = defaultdict(float)        # h -> busiest outside block group count
    own = {}                             # h -> residents of h seen in h
    with gzip.open(f, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            a, j = r["AREA"], r["AREA"][:5]
            for h, v in json.loads(r["DEVICE_HOME_AREAS"] or "{}").items():
                if not h.startswith("29"):
                    continue
                v = float(v)
                if h == a:
                    home_seen[(month, h[:5])] += v
                    own[h] = v
                    continue
                k = (h, j)
                if v > best[k]:
                    best[k] = v
                summed[(month, h[:5], j)] += v
                if j != h[:5] and v > best_out[h]:
                    best_out[h] = v
    for (h, j), v in best.items():
        low[(month, h[:5], j)] += min(v, own.get(h, 0.0))
    for h, v in best_out.items():
        left[(month, h[:5])] += min(v, own.get(h, 0.0))
    print(month, len(best), flush=True)
with open(root / "analysis/od_unique_mo_2026.csv", "w", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["month", "home_county", "dest_county", "people_lower", "people_summed"])
    for (m, i, j), v in sorted(summed.items()):
        k = cal.get((i, m), 1.0)
        w.writerow([m, i, j, round(low[(m, i, j)] / k, 2), round(v / k, 2)])
with open(root / "analysis/leaving_unique_mo_2026.csv", "w", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["month", "county", "residents_seen_at_home", "left_lower", "share_left_lower"])
    for (m, c), n in sorted(home_seen.items()):
        w.writerow([m, c, round(n, 1), round(left[(m, c)], 1), round(left[(m, c)] / n, 4) if n else ""])
print("done")
