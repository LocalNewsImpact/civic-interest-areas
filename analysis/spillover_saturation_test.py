"""Saturation and border terms for the spillover model.  Missouri, March 2026.

Base: the adopted model, rate ~ broadcast + crowded_weekly (spillover_outlets.py), fitted on the same 83 well-collected
outlets (Greene County Commonwealth, Mid Rivers Newsmagazine, Three Rivers Publishing left out). Each candidate is
added alone, scored by predicting each county's outlets from all the others (leave one county out), mean and median
absolute miss in percentage points.

Saturation (county, active outlets in src/lookups/mo_outlet_registry.csv; St. Louis city and county one unit):
  log_outlets        log of active local outlets in the county
  outlets_per_10k    active outlets per 10,000 residents
  log_print / log_tv print outlets; TV stations (log of 1 + count)
Border (the outlet's town, from spillover_profile.py):
  log_border_mi      log miles from the town to the nearest edge of its county
  log_hub_mi         log miles to the nearest town of 25,000+ in another county
Each also as a daily-only term (daily x term), so the dailies can move without changing the weeklies.
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
root = Path(__file__).resolve().parents[1]
unit = lambda f: "29189" if f == "29510" else f
d = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
prof = pd.read_csv(root / "analysis/spillover_profile.csv", dtype={"fips": str}).set_index("outlet")
d["log_border_mi"] = np.log(d.outlet.map(prof.border_mi).clip(lower=0.5))
d["log_hub_mi"] = np.log(d.outlet.map(prof.hub_mi).clip(lower=1))

reg = pd.read_csv(Path.home() / "VSCode/NewsCrawler/MizzouNewsCrawler/src/lookups/mo_outlet_registry.csv", dtype=str)
reg = reg[reg.status == "active"].assign(u=lambda x: x.county_fips.fillna("").map(unit))
n = reg.groupby("u").agg(outlets=("outlet", "size"),
                         printn=("type", lambda t: t.str.contains("print|newspaper|digital", na=False).sum()),
                         tv=("type", lambda t: t.str.contains("video", na=False).sum()))
pop = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str})
pop = pop.assign(u=pop.fips.map(unit)).groupby("u").population.sum()
d["log_outlets"] = np.log(d.fips.map(n.outlets).fillna(1))
d["outlets_per_10k"] = 1e4 * d.fips.map(n.outlets).fillna(1) / d.fips.map(pop)
d["log_print"] = np.log1p(d.fips.map(n.printn).fillna(0))
d["log_tv"] = np.log1p(d.fips.map(n.tv).fillna(0))
rows = [l.rstrip("\n").rsplit("|", 1) for l in open(root / "coverage/source_frequency.csv") if "|" in l]
freq = pd.DataFrame(rows, columns=["outlet", "f"]).drop_duplicates("outlet").set_index("outlet").f.str.strip()
d["daily"] = ((d.broadcast == 0) & (d.outlet.map(freq) == "daily")).astype(int)

NOT_FITTED = {"Greene County Commonwealth", "Three Rivers Publishing", "Mid Rivers Newsmagazine"}
g = d[d.good & ~d.outlet.isin(NOT_FITTED)].copy()
BASE = "rate ~ broadcast + crowded_weekly"


def loo(f):
    e = []
    for fp in g.fips.unique():
        tr, te = g[g.fips != fp], g[g.fips == fp]
        e += list((smf.glm(f, tr, family=sm.families.Binomial()).fit().predict(te) - te.rate).abs())
    return 100 * np.mean(e), 100 * np.median(e)


def coef(f, term):
    m = smf.glm(f, g, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(g.fips)[0]})
    return m.params[term], m.pvalues[term]


print(f"{len(g)} outlets, {g.fips.nunique()} counties; dailies {g.daily.sum()}, weeklies "
      f"{(g.outlet.map(freq) == 'weekly').sum()}, broadcasters {g.broadcast.sum()}")
b = loo(BASE)
print(f"\n| Term added | Mean miss | Median miss | Coefficient (p) |\n|---|---:|---:|---|\n| (adopted model) | {b[0]:.2f} | {b[1]:.2f} | |")
for t in ["log_outlets", "outlets_per_10k", "log_print", "log_tv", "log_border_mi", "log_hub_mi"]:
    for lab, term in ((t, t), (f"daily x {t}", f"daily:{t}")):
        f = BASE + f" + {term}"
        e = loo(f); c, p = coef(f, term)
        print(f"| {lab} | {e[0]:.2f} | {e[1]:.2f} | {c:+.2f} ({p:.3f}) |")
for f in [BASE + " + daily", BASE + " + daily + daily:log_outlets", BASE + " + daily + daily:log_border_mi"]:
    e = loo(f); print(f"| {f.replace(BASE + ' + ', '')} | {e[0]:.2f} | {e[1]:.2f} | |")
d.to_csv(root / "analysis/spillover_saturation_terms.csv", index=False)
