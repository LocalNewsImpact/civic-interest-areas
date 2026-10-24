"""Floors on the share of each tract's residents who leave their county -- people, not visits.  -> residents_leaving_tracts.csv

Advan floor (seen outside the county at least once in a month): for each home block group, its busiest outside block
group's people over its residents seen at home; people from different home block groups are distinct, so a tract's
floor is the sum over its block groups of that busiest count over the sum of residents. advan_floor_acs uses the
adopted denominator instead (review 2026-10-24): E_h = ACS population x the statewide units per resident
(home_bg_month_mo_2026.csv), each block group's leavers capped at E_h. Averaged January-July 2026: tracts are 2020
tracts, and August-September home codes are 2010 block groups whose tract codes name different areas.
Commuting floor (regular): LODES 2023 Missouri main file, primary jobs (JT01, free/mo_od_main_JT01_2023.csv.gz),
employed residents of the tract (home block) whose job is in another Missouri county, over tract population (ACS
2020-2024, datadesk census_value) and over employed residents.
Both are lower bounds on real people; the conservative figure per tract is the HIGHER of the two floors, since each is
a valid floor -- reported with which source sets it.
"""
import csv
import gzip
from collections import defaultdict
from pathlib import Path

import pandas as pd

root = Path(__file__).resolve().parents[1]
HOME = {"29007": "Audrain", "29019": "Boone", "29151": "Osage"}
MONTHS = {f"2026-{m:02d}" for m in range(1, 8)}
hb = pd.read_csv(root / "analysis/home_bg_month_mo_2026.csv", dtype={"home_bg": str})
E = hb[hb.month.isin(MONTHS)].set_index(["month", "home_bg"]).expected_units.to_dict()
own, peak = {}, defaultdict(float)
for r in csv.DictReader(open(root / "neighborhood/flows_audrain_boone_osage_2026.csv")):
    if r["month"] not in MONTHS:
        continue
    k = (r["month"], r["home_cbg"])
    v = float(r["device_home_areas"])
    if r["dest_cbg"] == r["home_cbg"]:
        own[k] = v
    elif r["dest_county"] != r["home_county"]:
        peak[k] = max(peak[k], v)
adv = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])   # (month, tract) -> [residents, floor people, expected, floor at E]
for (m, h), n in own.items():
    if n > 0:
        a = adv[(m, h[:11])]
        a[0] += n
        a[1] += min(peak[(m, h)], n)
for (m, h), e in E.items():
    if h[:5] in HOME and e > 0:
        a = adv[(m, h[:11])]
        a[2] += e
        a[3] += min(peak[(m, h)], e)
advan = pd.DataFrame([(m, t, f / n if n else float("nan"), fe / e if e else float("nan")) for (m, t), (n, f, e, fe) in adv.items()],
                     columns=["month", "tract", "advan_floor", "advan_floor_acs"])
advan_acs = advan.groupby("tract").advan_floor_acs.mean()
advan = advan.groupby("tract").advan_floor.mean()

emp, out = defaultdict(int), defaultdict(int)
with gzip.open(root / "free/mo_od_main_JT01_2023.csv.gz", "rt") as fh:
    for r in csv.DictReader(fh):
        h = r["h_geocode"]
        if h[:5] in HOME:
            n = int(r["S000"])
            emp[h[:11]] += n
            out[h[:11]] += n * (r["w_geocode"][:5] != h[:5])
pop = pd.read_csv(root / "free/tract_population_3counties.csv", dtype={"tract": str}).set_index("tract").population
t = pd.DataFrame({"population": pop})
t["employed_residents"] = pd.Series(emp)
t["commuters_out"] = pd.Series(out)
t["commute_floor_pop"] = t.commuters_out / t.population
t["commute_share_employed"] = t.commuters_out / t.employed_residents
t["advan_floor_seen_at_home"] = advan
t["advan_floor"] = advan_acs                    # adopted denominator (column name kept for readers)
t["conservative"] = t[["advan_floor", "commute_floor_pop"]].max(axis=1)
t["set_by"] = (t.advan_floor >= t.commute_floor_pop).map({True: "Advan", False: "commuting"})
t["county"] = t.index.str[:5].map(HOME)
t.index.name = "tract"
t.to_csv(root / "analysis/residents_leaving_tracts.csv")
print("| County | Tracts | Advan floor (seen outside, monthly), / ACS x statewide rate | / seen at home | Commuters out / population | "
      "Commuters out / employed | Conservative (higher floor), population-weighted | Set by Advan / commuting |")
print("|---|---:|---:|---:|---:|---:|---:|---|")
for c, g in t.groupby("county"):
    w = lambda col: (g[col] * g.population).sum() / g.population.sum()
    print(f"| {c} | {len(g)} | {w('advan_floor'):.0%} | {w('advan_floor_seen_at_home'):.0%} | {w('commute_floor_pop'):.0%} | "
          f"{g.commuters_out.sum() / g.employed_residents.sum():.0%} | {w('conservative'):.0%} | "
          f"{(g.set_by == 'Advan').sum()} / {(g.set_by == 'commuting').sum()} |")
print("\nrange across tracts (conservative):", {c: f"{g.conservative.min():.0%}-{g.conservative.max():.0%}" for c, g in t.groupby('county')})
