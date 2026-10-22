"""Three crossover measures per Missouri county (St. Louis city and county one unit), January-September 2026.

current      share of residents' summed block-group counts that are outside the county (od_mo_2026.csv, calibrated)
dedup_lower  distinct residents seen in at least one outside block group in a month / residents seen at home, averaged
             over months (leaving_unique_mo_2026.csv) -- at least this share of people left that month
commute      LODES 2023 Missouri main file: employed residents working in another Missouri county / population
             (ACS 2020-2024) -- at least this share leave regularly for work; also over employed residents
conservative the higher of the two lower bounds
"""
import csv
import gzip
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
unit = lambda f: "29189" if f == "29510" else f
cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str})
cov["u"] = cov.fips.map(unit)
pop = cov.groupby("u").population.sum()
name = cov.groupby("u").name.first()
name.loc["29189"] = "St. Louis (city + county)"
od = pd.read_csv(root / "analysis/od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
od = od[od.home_county != "OUT"].assign(h=lambda x: x.home_county.map(unit), d=lambda x: x.dest_county.map(unit))
current = od[od.h != od.d].groupby("h").visits.sum() / od.groupby("h").visits.sum()
lv = pd.read_csv(root / "analysis/leaving_unique_mo_2026.csv", dtype={"county": str})
lv["u"] = lv.county.map(unit)
g = lv.groupby(["u", "month"])[["residents_seen_at_home", "left_lower"]].sum()
dedup = (g.left_lower / g.residents_seen_at_home).groupby("u").mean()
emp, out = Counter(), Counter()
with gzip.open(root / "free/od_2023.csv.gz", "rt") as fh:
    for r in csv.DictReader(fh):
        h, w = unit(r["h_geocode"][:5]), unit(r["w_geocode"][:5])
        n = int(r["S000"]); emp[h] += n; out[h] += n * (w != h)
t = pd.DataFrame({"name": name, "population": pop, "current": current, "dedup_lower": dedup,
                  "commute_pop": pd.Series(out) / pop, "commute_emp": pd.Series(out) / pd.Series(emp)})
t["conservative"] = t[["dedup_lower", "commute_pop"]].max(axis=1)
t["set_by"] = np.where(t.dedup_lower >= t.commute_pop, "phone data", "commuting")
t.to_csv(root / "analysis/crossover_compare.csv")
print("| County | Current crossover (summed counts) | Distinct people seen outside, monthly (lower bound) | "
      "Commuting out / population | Commuting out / employed | Conservative | Set by |")
print("|---|---:|---:|---:|---:|---:|---|")
for f in ("29007", "29019", "29151", "29051", "29027", "29077", "29095", "29189"):
    r = t.loc[f]
    print(f"| {r['name']} | {r.current:.0%} | {r.dedup_lower:.0%} | {r.commute_pop:.0%} | {r.commute_emp:.0%} | {r.conservative:.0%} | {r.set_by} |")
print(f"\nall {len(t)} counties: correlation of current crossover with the conservative lower bound "
      f"{np.corrcoef(t.current, t.conservative)[0, 1]:.2f}; conservative set by phone data in {(t.set_by == 'phone data').sum()}, "
      f"by commuting in {(t.set_by == 'commuting').sum()}")
print("medians:", {c: f"{t[c].median():.0%}" for c in ("current", "dedup_lower", "commute_pop", "commute_emp", "conservative")})
