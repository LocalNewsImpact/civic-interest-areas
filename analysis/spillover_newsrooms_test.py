"""Does the number of newsrooms in a county change how far its coverage reaches?  March 2026, statewide.

Newsroom count = outlets with placed stories in March (The Maneater and CoMoBuzz excluded; St. Louis city + county one
unit), from the same articles spillover_v2.py uses. Spillover as there: share of placed stories touching another
Missouri county or an other-state county within 60 miles.
  1. Spillover by newsroom count (1, 2-3, 4+), within each cohort.
  2. spillover_v2's model (cohort, border, log population, residents' share of visits outside) plus newsroom count
     (as log, and as 1 vs 2+), quasi-binomial.
"""
import json
import subprocess
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

root = Path(__file__).resolve().parents[1]
data = json.load(open(root / "coverage/storymap/statewide_2026_03_articles.json"))
cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str}).set_index("fips")
by_name = {n.lower(): f for f, n in cov.name.items()}
by_name.update({"st. louis": "29189", "st louis": "29189", "st. louis city": "29510"})
fips_of = lambda n: by_name.get((n or "").lower().replace(" county", "").strip())
unit = lambda f: "29189" if f == "29510" else f
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from spillover_common import NOT_LOCAL as EXCLUDE, home_fips  # one outlet set (EXCLUDE + CAMPUS) and HOME_COUNTY for every count

for version, file, keep in (("all outlets", "all", lambda a: True),
                            ("print and digital", "print", lambda a: "broadcast" not in (a["publisher_type"] or ""))):
    outlets = defaultdict(set)
    for a in data["articles"]:
        f = home_fips(a["publisher"], fips_of(a["publisher_county"]))
        if f and a["counties"] and a["publisher"] not in EXCLUDE and keep(a):
            outlets[unit(f)].add(a["publisher"])
    c = pd.read_csv(root / f"analysis/spillover_v2_{file}.csv", dtype={"Unnamed: 0": str}).rename(columns={"Unnamed: 0": "fips"}).set_index("fips")
    c["newsrooms"] = [len(outlets[f]) for f in c.index]
    c["band"] = pd.cut(c.newsrooms, [0, 1, 3, 99], labels=["1", "2-3", "4+"])
    print(f"\n# {version}: {len(c)} newsroom counties; newsrooms per county: " +
          ", ".join(f"{k}: {v}" for k, v in c.band.value_counts().sort_index().items()))
    g = c.groupby(["type", "band"], observed=True).agg(counties=("rate", "size"), median_spill=("rate", "median"),
                                                       median_pop=("population", "median"))
    print("1. spillover by cohort and number of newsrooms:")
    print(g.assign(median_spill=lambda x: (100 * x.median_spill).round(0).astype(int).astype(str) + "%",
                   median_pop=lambda x: x.median_pop.astype(int)).to_string())
    print(f"   correlation of log newsrooms with log population: {np.corrcoef(np.log(c.newsrooms), c.log_pop)[0, 1]:.2f}")
    c["log_newsrooms"] = np.log(c.newsrooms)
    c["one_newsroom"] = (c.newsrooms == 1).astype(int)
    base = "spill + stay ~ C(type, Treatment('Rural')) + border + log_pop + travel_out"
    for label, f in (("without newsroom count", base), ("+ log newsrooms", base + " + log_newsrooms"),
                     ("+ one newsroom only", base + " + one_newsroom")):
        m = smf.glm(f, c, family=sm.families.Binomial()).fit(scale="X2")
        extra = [k for k in ("log_newsrooms", "one_newsroom") if k in m.params]
        est = "; ".join(f"{k} {m.params[k]:+.2f} (se {m.bse[k]:.2f}, p {m.pvalues[k]:.3f})" for k in extra)
        print(f"2. {label}: deviance {m.deviance:,.0f}; log_pop {m.params['log_pop']:+.2f} (p {m.pvalues['log_pop']:.3f}) {est}")
    for n, f in (("Audrain", "29007"), ("Boone", "29019"), ("Osage", "29151")):
        if f in c.index:
            r = c.loc[f]
            print(f"   {n}: {int(r.newsrooms)} newsroom(s), {r.rate:.0%} spillover, {r.type}")
