"""Unique device-county pairs: each person counted once for each outside county they are seen in (per month).

Advan counts distinct people from a home block group h in each destination block group c. People from h seen in a
destination COUNTY j are bounded: low = busiest block group of j (max_c), high = all block groups of j (sum_c, capped at
residents). Summed over outside counties -> unique person-county pairs out of the county. Residents = people from h seen
in h. Reported per county of residence (sum over its block groups), averaged Jan-Sep 2026, as pairs per resident and
as the outside share of all person-county pairs (home county = one pair per resident).
Privacy floor: Advan reports 2-4 devices as 4 and scales; a home block group appears at that floor in many counties.
Floor entries are approximated as the smallest value reported for that destination block group and month in this
extract; the "floor removed" columns drop them.
"""
import csv
from collections import defaultdict
from pathlib import Path

import pandas as pd

root = Path(__file__).resolve().parents[1]
HOME = {"29007": "Audrain", "29019": "Boone", "29151": "Osage"}
rows = list(csv.DictReader(open(root / "neighborhood/flows_audrain_boone_osage_2026.csv")))
floor = defaultdict(lambda: float("inf"))
for r in rows:
    v = float(r["device_home_areas"])
    if v > 0:
        floor[(r["month"], r["dest_cbg"])] = min(floor[(r["month"], r["dest_cbg"])], v)
own = {}
lo, hi = defaultdict(lambda: defaultdict(float)), defaultdict(lambda: defaultdict(float))
lo_nf, hi_nf = defaultdict(lambda: defaultdict(float)), defaultdict(lambda: defaultdict(float))
for r in rows:
    k, v = (r["month"], r["home_cbg"]), float(r["device_home_areas"])
    if r["dest_cbg"] == r["home_cbg"]:
        own[k] = v
    elif r["dest_county"] != r["home_county"] and v > 0:
        j = r["dest_county"]
        lo[k][j] = max(lo[k][j], v); hi[k][j] += v
        if v > floor[(r["month"], r["dest_cbg"])]:
            lo_nf[k][j] = max(lo_nf[k][j], v); hi_nf[k][j] += v
acc = defaultdict(lambda: defaultdict(float))
for k, n in own.items():
    if n <= 0:
        continue
    a = acc[(k[0], k[1][:5])]
    a["residents"] += n
    for name, d in (("low", lo), ("high", hi), ("low_nf", lo_nf), ("high_nf", hi_nf)):
        a[name] += sum(min(v, n) for v in d[k].values())
        a["counties_" + name] += len(d[k])
df = pd.DataFrame([{"month": m, "county": c, **v} for (m, c), v in acc.items()])
g = df.groupby("county").mean(numeric_only=True)
print("| County | Outside pairs per resident (low-high) | Outside share of all pairs (low-high) | "
      "Floor removed: pairs per resident | Floor removed: outside share |")
print("|---|---|---|---|---|")
for c, r in g.iterrows():
    sh = lambda x: x / (x + r.residents)
    print(f"| {HOME[c]} | {r.low / r.residents:.2f}-{r.high / r.residents:.2f} | {sh(r.low):.0%}-{sh(r.high):.0%} | "
          f"{r.low_nf / r.residents:.2f}-{r.high_nf / r.residents:.2f} | {sh(r.low_nf):.0%}-{sh(r.high_nf):.0%} |")
g.to_csv(root / "analysis/device_county_pairs_three_counties.csv")
