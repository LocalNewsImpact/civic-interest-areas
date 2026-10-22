"""Do county demographic variables improve the crossover, spillover or travel models?  Missouri, 2026.

Variables: ACS 2020-2024 5-year, county, from datadesk's Census store (mo_county_acs_2024.csv): percents where the
measure is a share, logs for dollar values, as published otherwise. St. Louis city and county one unit (population-
weighted). Plus LODES 2023 commuting share (employed residents working in another county / population).
  1 CROSSOVER  county share of residents seen outside it in a month (distinct people, lower bound; crossover_compare.csv)
               ~ log population + nonmetro + commuting share [+ one ACS variable]; ordinary least squares on the logit;
               leave one county out; then forward selection by that error.
  2 SPILLOVER  outlet model (broadcaster + crossover) + one county ACS variable; leave one county out.
  3 TRAVEL     the adopted travel model + (home-county variable x log distance): does a county's makeup change how far
               its residents travel? Fit Jan-Jun, score Jul-Sep shares.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
here = Path(__file__).resolve().parent
root = here.parent
unit = lambda f: "29189" if f == "29510" else f
acs = pd.read_csv(root / "free/mo_county_acs_2024.csv", dtype={"fips": str})
wide = acs.pivot(index="fips", columns="variable", values="percent").add_suffix("_pct")
est = acs.pivot(index="fips", columns="variable", values="estimate")
LEVEL = ["median_household_income", "per_capita_income", "median_home_value", "median_gross_rent", "median_age",
         "mean_travel_time", "unemployment_rate"]
X = pd.DataFrame(index=est.index)
for v in LEVEL:
    X[v] = np.log(est[v]) if v.startswith(("median_h", "per_c", "median_g")) else est[v]
for v in wide.columns:
    if wide[v].notna().mean() > 0.9 and v.replace("_pct", "") not in LEVEL:
        X[v.replace("_pct", "")] = wide[v]
X = X.drop(columns=[c for c in ("total_population", "households", "housing_units") if c in X])
pop = est.total_population
w = pop.reindex(X.index)
u = X.index.map(unit)
X = X.mul(w, axis=0).groupby(u).sum().div(w.groupby(u).sum(), axis=0)   # population-weighted where units merge
VARS = list(X.columns)
cc = pd.read_csv(root / "analysis/crossover_compare.csv", dtype={"Unnamed: 0": str}).rename(columns={"Unnamed: 0": "fips"}).set_index("fips")
cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str})
cov["u"] = cov.fips.map(unit)
c = cc[["dedup_lower", "commute_pop", "population"]].join(cov.groupby("u").metro.max()).join(X)
c["y"] = np.log(c.dedup_lower / (1 - c.dedup_lower))
c["log_pop"] = np.log(c.population)
c["nonmetro"] = 1 - c.metro
VARS = [v for v in VARS if c[v].notna().all() and c[v].std() > 0]   # measures missing for any county are left out
print("variables tested:", len(VARS), VARS)
for v in VARS:
    c[v] = (c[v] - c[v].mean()) / c[v].std()


def loo(formula, d, target, inv):
    e = []
    for f in d.index:
        m = smf.ols(formula, d.drop(index=f)).fit()
        e.append(abs(inv(m.predict(d.loc[[f]]).iloc[0]) - d.loc[f, target]))
    return 100 * np.mean(e)


inv = lambda z: 1 / (1 + np.exp(-z))
BASE = "y ~ log_pop + nonmetro + commute_pop"
b0 = loo(BASE, c, "dedup_lower", inv)
print(f"## 1 CROSSOVER ({len(c)} counties): baseline (population, nonmetro, commuting) error {b0:.1f} points")
res = []
for v in VARS:
    e = loo(BASE + f" + {v}", c, "dedup_lower", inv)
    m = smf.ols(BASE + f" + {v}", c).fit()
    res.append((v, e, m.params[v], m.pvalues[v]))
r = pd.DataFrame(res, columns=["variable", "error", "coef", "p"]).sort_values("error")
print(r.head(10).round(3).to_string(index=False))
chosen, best = [], b0
while True:
    trial = [(loo(BASE + " + " + " + ".join(chosen + [v]), c, "dedup_lower", inv), v) for v in VARS if v not in chosen]
    e, v = min(trial)
    if e >= best - 0.05:
        break
    chosen.append(v); best = e
print(f"forward selection: {chosen} -> error {best:.1f} points (baseline {b0:.1f}); "
      f"crossover range across counties {100 * c.dedup_lower.min():.0f}-{100 * c.dedup_lower.max():.0f}%")

so = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str}).join(X, on="fips")
for v in VARS:
    so[v] = (so[v] - so[v].mean()) / so[v].std()


def loo_out(f):
    e = []
    for fp in so.fips.unique():
        tr, te = so[so.fips != fp], so[so.fips == fp]
        e += list(np.abs(smf.glm(f, tr, family=sm.families.Binomial()).fit().predict(te) - te.rate))
    return 100 * np.mean(e)


s0 = loo_out("rate ~ broadcast + travel_out")
res = []
for v in VARS:
    f = f"rate ~ broadcast + travel_out + {v}"
    m = smf.glm(f, so, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(so.fips)[0]})
    res.append((v, loo_out(f), m.params[v], m.pvalues[v]))
r = pd.DataFrame(res, columns=["variable", "error", "coef", "p"]).sort_values("error")
print(f"\n## 2 SPILLOVER ({len(so)} outlets): adopted error {s0:.1f} points")
print(r.head(8).round(3).to_string(index=False))

sys.path.insert(0, str(here))
from gravity_terms import FACTORS, all_pairs, design  # noqa: E402
pairs = all_pairs()
od = pd.read_csv(root / "analysis/od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
od = od[(od.home_county != "OUT") & (od.home_county != od.dest_county)]
key = list(zip(pairs.i, pairs.j))
yf = lambda ms: (lambda v: np.array([v.get(k, 0) for k in key], float))(od[od.month.isin(ms)].groupby(["home_county", "dest_county"]).visits.sum())
ALL = [f"2026-{m:02d}" for m in range(1, 10)]
y6, y3 = yf(ALL[:6]), yf(ALL[6:])
share = lambda x: x / pd.Series(x).groupby(pairs.i.values).transform("sum").values
s3 = share(y3)
Xd = design(pairs)
ld = np.log(pairs.dist.values)
Xi = X.copy(); Xi.loc["29510"] = Xi.loc["29189"]
for v in VARS:
    Xi[v] = (Xi[v] - Xi[v].mean()) / Xi[v].std()


def oos(Xm):
    m = sm.GLM(y6, Xm, family=sm.families.Poisson()).fit(maxiter=300)
    p3 = share(m.predict(Xm))
    big = s3 >= 0.05
    return np.corrcoef(s3, p3)[0, 1] ** 2, 100 * np.mean(np.abs(s3 - p3)[big]), m
r2, e0, _ = oos(Xd)
print(f"\n## 3 TRAVEL: adopted Jul-Sep shares explained {r2:.2%}, big-flow error {e0:.2f} points")
res = []
for v in ("median_household_income", "per_capita_income", "median_age", "age_65_and_over", "households_with_broadband",
          "mean_travel_time", "below_poverty", "bachelors_or_higher", "unemployment_rate", "in_labor_force", "owner_occupied"):
    if v not in Xi:
        continue
    Xm = Xd.assign(**{f"{v}_x_log_dist": Xi[v].reindex(pairs.i).values * ld})
    r2v, ev, m = oos(Xm)
    res.append((v, r2v, ev, m.params[f"{v}_x_log_dist"]))
print(pd.DataFrame(res, columns=["home-county variable x log distance", "Jul-Sep explained", "big-flow error", "coef"])
      .sort_values("big-flow error").round(4).to_string(index=False))
