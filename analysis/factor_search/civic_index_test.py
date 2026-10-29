"""Do Civic Information Index indicators improve the crossover or spillover models?  Missouri, 2026.

Civic Information Index 2026 (Internews Listening Post Collective and Brown University Information Futures Lab;
county data from the index's published Google Sheet, census_dl/civic_index/cii_2026.csv): 27 indicators and five
pillar scores. Raw values (not percentiles), standardized; St. Louis city and county one unit, population-weighted.
  CROSSOVER  share of residents seen outside the county (distinct people, lower bound) ~ log population + rural +
             commuting share + one indicator; OLS on the logit; leave one county out; then forward selection.
  SPILLOVER  the adopted outlet model (spillover_common.FINAL) + one county indicator, adopted outlets and held-out
             scheme (spillover_common.heldout_error); then forward selection.
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from spillover_common import FINAL, adopted_split, heldout_error, rural_by_unit  # noqa: E402  the adopted spillover model
root = Path(__file__).resolve().parents[2]
unit = lambda f: "29189" if f == "29510" else f
cii = pd.read_csv(root / "census_dl/civic_index/cii_2026.csv", dtype={"FIPS": str})
cii["FIPS"] = cii.FIPS.str.zfill(5)
cii = cii[cii.FIPS.str.startswith("29")].set_index("FIPS")
cols = [c for c in cii.columns if c not in ("Name", "County", "State", "Abbr", "Population") and "percentile" not in c.lower()]
X = cii[cols].apply(pd.to_numeric, errors="coerce")
w = pd.to_numeric(cii.Population, errors="coerce")
u = X.index.map(unit)
X = X.mul(w, axis=0).groupby(u).sum(min_count=1).div(w.groupby(u).sum(), axis=0)
short = {c: "v_" + "".join(ch if ch.isalnum() else "_" for ch in c.lower())[:40].strip("_") for c in cols}
X = X.rename(columns=short)
raw = cii[cols].apply(pd.to_numeric, errors="coerce").rename(columns=short)
# an indicator must vary across Missouri's counties (the volunteer rate is one state figure for every county)
VARS = [v for v in X.columns if X[v].notna().all() and raw[v].nunique() >= 3]
label = {v: c for c, v in short.items()}
print(f"{len(VARS)} indicators with complete Missouri data; missing: {[label[v] for v in X.columns if v not in VARS]}")
Xs = (X[VARS] - X[VARS].mean()) / X[VARS].std()

cc = pd.read_csv(root / "analysis/crossover_compare.csv", dtype={"Unnamed: 0": str}).rename(columns={"Unnamed: 0": "fips"}).set_index("fips")
cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str})
cov["u"] = cov.fips.map(unit)
c = cc[["dedup_lower", "commute_pop", "population"]].join(rural_by_unit()).join(Xs)
c["y"] = np.log(c.dedup_lower / (1 - c.dedup_lower)); c["log_pop"] = np.log(c.population)
inv = lambda z: 1 / (1 + np.exp(-z))
loo_c = lambda f: 100 * np.mean([abs(inv(smf.ols(f, c.drop(index=k)).fit().predict(c.loc[[k]]).iloc[0]) - c.loc[k, "dedup_lower"]) for k in c.index])
B = "y ~ log_pop + rural + commute_pop"


def screen(base, loo, fit):
    b0 = loo(base)
    r = []
    for v in VARS:
        m = fit(base + f" + {v}")
        r.append((label[v], loo(base + f" + {v}"), m.params[v], m.pvalues[v], v))
    r = pd.DataFrame(r, columns=["indicator", "error", "coef", "p", "v"]).sort_values("error")
    chosen, best = [], b0
    while True:
        trial = [(loo(base + " + " + " + ".join(chosen + [v])), v) for v in r.v.head(10) if v not in chosen]
        if not trial:
            break
        e, v = min(trial)
        if e >= best - 0.05:
            break
        chosen.append(v); best = e
    return b0, r, chosen, best


b0, r, chosen, best = screen(B, loo_c, lambda f: smf.ols(f, c).fit())
print(f"\n## CROSSOVER ({len(c)} counties): baseline error {b0:.1f} points")
print(r.drop(columns="v").head(8).round(3).to_string(index=False))
print(f"forward selection: {[label[v] for v in chosen]} -> {best:.1f} points")

so = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str}).join(Xs, on="fips")


def loo_o(f):
    return heldout_error(f, so)



so_fit = adopted_split(so)[0]
fit_o = lambda f: smf.glm(f, so_fit, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(so_fit.fips)[0]})
import sys
if "--crossover-only" in sys.argv:
    raise SystemExit
b0, r, chosen, best = screen(FINAL, loo_o, fit_o)
print(f"\n## SPILLOVER ({FINAL}; fitted {len(so_fit)}, scored {int(so.scored.sum())} outlets): adopted error {b0:.2f} points")
print(r.drop(columns="v").head(8).round(3).to_string(index=False))
print(f"forward selection: {[label[v] for v in chosen]} -> {best:.1f} points")
