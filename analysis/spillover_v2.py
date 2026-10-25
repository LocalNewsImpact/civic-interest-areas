"""Spillover, revised (March 2026 coverage; Jan-Sep 2026 travel).

Changes from spillover_hub_test.py, all for this measure only:
  1. St. Louis city and St. Louis County are one metro core: every St. Louis outlet is recorded in the county, so a
     story about the city counted as "another county". Merged on both sides -- newsroom county and county covered --
     and in residents' travel.
  2. Four cohorts:
       Top 50 metro    central county of Kansas City (31st US metro) or St. Louis (23rd), 2024 Census estimates
       Regional hub    central county of any other metro or micro area that draws at least as many visits from other
                       Missouri counties as its residents make elsewhere (visitors in / residents out >= 1, Jan-Sep)
       Metro suburban  every other county in a metro area: outlying counties, every non-core county of the Kansas
                       City and St. Louis metros, and central counties that send more than they draw (Christian)
       Rural           everything else (OMB 2023 delineation for metro / micro / central / outlying)
  3. A story spills over if it touches another Missouri county OR a county in another state within 60 miles (2020
     population centres) of the newsroom's county -- a border region is a region on both sides of the line. A newsroom
     county is "border" if any other-state county lies within 60 miles.
Model: quasi-binomial GLM across newsroom counties with 10+ placed stories, spill ~ cohort + border + log population
+ residents' share of visits outside.
"""
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

root = Path(__file__).resolve().parents[1]
MERGE = {"29510": "29189"}                       # St. Louis city -> the St. Louis metro core
unit = lambda f: MERGE.get(f, f)
cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str}).set_index("fips")
cp = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
cen = {r.STATEFP + r.COUNTYFP: (float(r.LATITUDE), float(r.LONGITUDE)) for r in cp.itertuples()}


def miles(a, b):
    (y1, x1), (y2, x2) = cen[a], cen[b]
    p1, p2, dl = math.radians(y1), math.radians(y2), math.radians(x2 - x1)
    return 3959 * math.acos(min(1, math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)))


other_state = [f for f in cen if not f.startswith("29")]
near_oos = {f: {g for g in other_state if miles(f, g) <= 60} for f in cov.index}

# county attributes on merged units
c0 = cov.copy()
c0.index = [unit(f) for f in c0.index]
units = c0.groupby(level=0).agg(population=("population", "sum"), name=("name", "first"))
units.loc["29189", "name"] = "St. Louis (city + county)"
d = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str)
d = d[d["FIPS State Code"] == "29"]
omb = {"29" + r[11]: (r[5].startswith("Metropolitan"), r[12] == "Central", r[4]) for r in d.itertuples()}
od = pd.read_csv(root / "analysis/od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
od = od[od.home_county != "OUT"].assign(h=lambda x: x.home_county.map(unit), d=lambda x: x.dest_county.map(unit))
away = od[od.h != od.d]
units["travel_out"] = away.groupby("h").visits.sum() / od.groupby("h").visits.sum()
units["draw"] = away.groupby("d").visits.sum() / away.groupby("h").visits.sum()
units["border"] = [int(bool(near_oos[f] | (near_oos.get("29510", set()) if f == "29189" else set()))) for f in units.index]


def kind(f):
    if f in ("29095", "29189"):
        return "Top 50 metro"
    if f not in omb:
        return "Rural"
    metro, central, cbsa = omb[f]
    # a county of the Kansas City or St. Louis metro is part of that metro, never a hub of its own
    if cbsa.startswith(("Kansas City", "St. Louis")):
        return "Metro suburban"
    if central and units.draw[f] >= 1:
        return "Regional hub"
    return "Metro suburban" if metro else "Rural"


units["type"] = [kind(f) for f in units.index]
print("cohorts (all 114 units):", units.type.value_counts().to_dict())
print("the three:", {n: units.type[f] for n, f in {"Audrain": "29007", "Boone": "29019", "Osage": "29151"}.items()},
      "| Audrain draw", round(units.draw["29007"], 2))

data = json.load(open(root / "coverage/storymap/statewide_2026_03_articles.json"))
by_name = {n.lower(): f for f, n in cov.name.items()}
by_name.update({"st. louis": "29189", "st louis": "29189", "st. louis city": "29510"})
fips_of = lambda n: by_name.get((n or "").lower().replace(" county", "").strip())
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from spillover_common import NOT_LOCAL, home_fips, home_set, registry  # one outlet set and one home rule for every count
HOME = {"Audrain": "29007", "Boone": "29019", "Osage": "29151"}
_reg = registry()
_city = {(o, unit(c or "")): (t, s) for o, c, t, s in zip(_reg.outlet, _reg.county_fips, _reg.city, _reg.state)}

for version, keep in (("all outlets", lambda a: True), ("print and digital", lambda a: "broadcast" not in (a["publisher_type"] or ""))):
    n = defaultdict(lambda: [0, 0, 0])            # placed, spill (MO or near other-state), MO only
    for a in data["articles"]:
        f = fips_of(a["publisher_county"])
        if a["publisher"] in NOT_LOCAL or not f or not a["counties"] or not keep(a):
            continue
        f = home_fips(a["publisher"], f)
        i = unit(f)
        near = near_oos[f] | (near_oos["29510"] if i == "29189" else set())
        # HOME rule (spillover_common.home_set): counties of the outlet's city, and Kansas City, Kansas for Kansas City
        hs = home_set(a["publisher"], i, *_city.get((a["publisher"], i), ("", "MO")))
        near = near - hs
        mo = any(c.startswith("29") and unit(c) not in hs for c in a["counties"])
        oos = any(c in near for c in a["counties"])
        r = n[i]; r[0] += 1; r[1] += mo or oos; r[2] += mo
    c = units.join(pd.DataFrame(n, index=["placed", "spill", "spill_mo"]).T, how="inner")
    c = c[c.placed >= 10].copy()
    c["stay"], c["rate"], c["rate_mo"], c["log_pop"] = c.placed - c.spill, c.spill / c.placed, c.spill_mo / c.placed, np.log(c.population)
    m = smf.glm("spill + stay ~ C(type, Treatment('Rural')) + border + log_pop + travel_out", c,
                family=sm.families.Binomial()).fit(scale="X2")
    c["pred"] = m.predict(c)
    print(f"\n# {version}: {len(c)} newsroom units with 10+ placed stories; dispersion {m.scale:.2f}")
    print(pd.DataFrame({"coef": m.params, "se": m.bse, "p": m.pvalues}).round(3).to_string())
    print("| County | Type | Border | Stories | Spill (MO only) | Spill (MO + near other state) | Predicted |")
    print("|---|---|---|---:|---:|---:|---:|")
    show = c[c.type.isin(["Top 50 metro", "Regional hub"]) & c.index.isin(HOME.values())].sort_values("population", ascending=False)
    for f, r in show.iterrows():
        print(f"| {r['name']} | {r.type} | {'yes' if r.border else 'no'} | {int(r.placed)} | {r.rate_mo:.0%} | {r.rate:.0%} | {r.pred:.0%} |")
    for name, f in HOME.items():
        if f in c.index:
            r = c.loc[f]
            print(f"{name} ({r.type}, border {'yes' if r.border else 'no'}): {r.rate:.0%} of {int(r.placed)} stories spill over; predicted {r.pred:.0%}")
    c.to_csv(root / f"analysis/spillover_v2_{version.split()[0]}.csv")
