"""Spillover by county type: the share of a newsroom county's stories (March 2026) that touch another Missouri county,
modelled with the county's TYPE, because regional centres, suburbs and small rural counties behave differently and
one statewide average mixes them.

type   OMB 2023 delineation (Census list1_2023.xlsx): metro central, metro outlying, micropolitan (central or
       outlying), rural (in no metro or micro area)
model  binomial GLM (quasi-, scale from Pearson X2), weighted by stories, across newsroom counties with 10+ placed
       stories:  touch-another-county ~ type + log population + residents' share of visits outside the county
Then each of Audrain, Boone and Osage against the model and against its own type, by population.
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import statsmodels.api as sm

root = Path(__file__).resolve().parents[1]
cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str}).set_index("fips")
d = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str)
d = d[d["FIPS State Code"] == "29"]
kind = {}
for r in d.itertuples():
    f = "29" + r[11]
    metro = r[5].startswith("Metropolitan")
    kind[f] = ("metro central" if r[12] == "Central" else "metro outlying") if metro else "micropolitan"
cov["type"] = [kind.get(f, "rural") for f in cov.index]
od = pd.read_csv(root / "analysis/od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
od = od[od.home_county != "OUT"]
cov["travel_out"] = (od[od.home_county != od.dest_county].groupby("home_county").visits.sum()
                     / od.groupby("home_county").visits.sum())
data = json.load(open(root / "coverage/storymap/statewide_2026_03_articles.json"))
by_name = {n.lower(): f for f, n in cov.name.items()}
by_name.update({"st. louis": "29189", "st louis": "29189", "st. louis city": "29510"})
fips_of = lambda n: by_name.get((n or "").lower().replace(" county", "").strip())
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from spillover_common import NOT_LOCAL as EXCLUDE, home_fips  # one outlet set (EXCLUDE + CAMPUS) and HOME_COUNTY for every count
HOME = {"Audrain": "29007", "Boone": "29019", "Osage": "29151"}
print("types:", cov.type.value_counts().to_dict(), "| the three:", {n: cov.type[f] for n, f in HOME.items()})

for version, keep in (("all outlets", lambda a: True), ("print and digital", lambda a: "broadcast" not in (a["publisher_type"] or ""))):
    n = defaultdict(lambda: [0, 0])
    for a in data["articles"]:
        i = home_fips(a["publisher"], fips_of(a["publisher_county"]))
        if a["publisher"] in EXCLUDE or not i or not a["counties"] or not keep(a):
            continue
        n[i][0] += 1
        n[i][1] += any(c.startswith("29") and c != i for c in a["counties"])
    c = cov.join(pd.DataFrame(n, index=["placed", "spill"]).T, how="inner")
    c = c[c.placed >= 10].copy()
    c["stay"], c["rate"], c["log_pop"] = c.placed - c.spill, c.spill / c.placed, np.log(c.population)
    m = smf.glm("spill + stay ~ C(type, Treatment('rural')) + log_pop + travel_out", c,
                family=sm.families.Binomial()).fit(scale="X2")
    c["pred"] = m.predict(c)
    print(f"\n# {version}: {len(c)} newsroom counties with 10+ placed stories")
    print(pd.DataFrame({"coef": m.params, "se": m.bse, "p": m.pvalues}).round(3).to_string())
    print("by type:", c.groupby("type").apply(lambda g: f"{len(g)} counties, median {g.rate.median():.0%}").to_dict())
    for name, f in HOME.items():
        if f not in c.index:
            continue
        r = c.loc[f]
        peers = c[c.type == r.type].sort_values("population", ascending=False)
        print(f"\n## {name} ({r.type}, {int(r.population):,} people): {r.rate:.0%} of {int(r.placed)} stories touch another "
              f"county; the model predicts {r.pred:.0%}")
        print("| County | Population | Residents' visits outside | Stories | Touch another county | Model predicts |")
        print("|---|---:|---:|---:|---:|---:|")
        near = peers[(peers.population >= r.population / 2.5) & (peers.population <= r.population * 2.5)]
        for p in near.itertuples():
            mark = "**" if p.Index == f else ""
            print(f"| {mark}{p.name}{mark} | {int(p.population):,} | {p.travel_out:.0%} | {int(p.placed)} | {mark}{p.rate:.0%}{mark} | {p.pred:.0%} |")
c.to_csv(root / "analysis/spillover_by_type.csv")
