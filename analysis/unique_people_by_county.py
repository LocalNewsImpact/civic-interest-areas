"""De-duplicated people: residents of home county i seen in destination county j in a month, as a share of residents.

Per home block group h and destination county j (block groups c in j), p_hc = people from h seen in c / residents of h
seen in h (calibration cancels: both sides carry the same factor). People from different home block groups are distinct,
so county figures sum over h, weighted by residents. Residents seen at home are inflated where Advan over-detects homes
(build_calibration.py), so lower_acs repeats the lower bound over E_h = ACS population x the statewide units per
resident (home_bg_month_mo_2026.csv; b = 1 sensitivity), and lower_cal over the adopted calibrated denominator
D_h = own_h^(1-b) E_h^b (crossover_bg_month_mo_2026.csv).
  lower     max_c p_hc                    the busiest block group's people are all distinct
  estimate  1 - prod_c (1 - p_hc)         union of overlapping groups assuming independence (leans high: people seen in
                                          one part of a town are more likely to be seen in another)
  upper     min(1, sum_c p_hc)            no one seen in two block groups
Usage: unique_people_by_county.py [month]   (default 2026-03)
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
MONTH = sys.argv[1] if len(sys.argv) > 1 else "2026-03"
HOME = {"29007": "Audrain", "29019": "Boone", "29151": "Osage"}
NAMES = {r["fips"]: r["name"] for r in csv.DictReader(open(root / "analysis/county_covariates.csv"))}
hb = pd.read_csv(root / "analysis/home_bg_month_mo_2026.csv", dtype={"home_bg": str}).query("month == @MONTH")
E = hb.set_index("home_bg").expected_units.to_dict()
cb = pd.read_csv(root / "analysis/crossover_bg_month_mo_2026.csv", dtype={"home_bg": str}).query("month == @MONTH")
Dc = cb.set_index("home_bg").denominator_calibrated.to_dict()
own, seen = {}, defaultdict(lambda: defaultdict(list))
for r in csv.DictReader(open(root / "neighborhood/flows_audrain_boone_osage_2026.csv")):
    if r["month"] != MONTH:
        continue
    v = float(r["device_home_areas"])
    if r["dest_cbg"] == r["home_cbg"]:
        own[r["home_cbg"]] = v
    elif r["dest_county"] != r["home_county"] and v > 0:
        seen[r["home_cbg"]][r["dest_county"]].append(v)
rows = []
for h, n in own.items():
    if n <= 0:
        continue
    for j, vals in seen[h].items():
        p = np.minimum(np.array(vals) / n, 1.0)
        e, dc = E.get(h, 0.0), Dc.get(h, 0.0)
        rows.append((h[:5], j, n, p.max(), 1 - np.prod(1 - p), min(1.0, p.sum()), len(p), e, min(1.0, max(vals) / e) if e > 0 else 0.0,
                     dc, min(1.0, max(vals) / dc) if dc > 0 else 0.0))
d = pd.DataFrame(rows, columns=["home", "dest", "residents", "lower", "estimate", "upper", "block_groups", "expected", "lower_acs",
                                "calibrated", "lower_cal"])
res = {c: sum(n for h, n in own.items() if h.startswith(c) and n > 0) for c in HOME}
res_e = {c: sum(e for h, e in E.items() if h.startswith(c)) for c in HOME}
res_d = {c: sum(e for h, e in Dc.items() if h.startswith(c)) for c in HOME}
out = []
for (c, j), g in d.groupby(["home", "dest"]):
    w = lambda col: (g[col] * g.residents).sum() / res[c]
    out.append((HOME[c], NAMES.get(j, j), w("lower"), w("estimate"), w("upper"), g.block_groups.median(),
                (g.lower_acs * g.expected).sum() / res_e[c], (g.lower_cal * g.calibrated).sum() / res_d[c]))
t = pd.DataFrame(out, columns=["home", "destination", "lower", "estimate", "upper", "block_groups_seen", "lower_acs", "lower_cal"])
t = t.sort_values(["home", "estimate"], ascending=[True, False])
print(f"Residents seen in each destination county, {MONTH}, as a share of the home county's residents")
print("| Home | Destination | Lower bound, / calibrated D (adopted) | / seen at home | / ACS x statewide rate | Estimate | Upper bound | Block groups seen in (median) |\n|---|---|---:|---:|---:|---:|---:|---:|")
for home, g in t.groupby("home", sort=False):
    for r in g.head(6).itertuples():
        print(f"| {r.home} | {r.destination} | {r.lower_cal:.1%} | {r.lower:.1%} | {r.lower_acs:.1%} | {r.estimate:.1%} | {r.upper:.1%} | {r.block_groups_seen:.0f} |")
t.to_csv(root / f"analysis/unique_people_by_county_{MONTH.replace('-', '_')}.csv", index=False)
