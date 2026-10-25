"""Do county demographic variables improve the crossover, spillover or travel models?  Missouri, 2026.

Variables: ACS 2020-2024 5-year, county, from datadesk's Census store (mo_county_acs_2024.csv): percents where the
measure is a share, logs for dollar values, as published otherwise. St. Louis city and county one unit (population-
weighted). Plus LODES 2023 commuting share (employed residents working in another county / population).
  1 CROSSOVER  county share of residents seen outside it in a month (distinct people, lower bound; crossover_compare.csv)
               ~ log population + nonmetro + commuting share [+ one ACS variable]; ordinary least squares on the logit;
               leave one county out; then forward selection by that error.
  2 SPILLOVER  outlet model (broadcaster + crossover) + one county ACS variable; leave one county out.
  3 TRAVEL     the adopted travel model + (home-county variable x centred log distance): does a county's makeup change
               how far its residents travel? Outcome: the adopted one (calibrated, pass-through discounted). Primary:
               leave one home county out (8 folds, seed 7), share-weighted error and big flows (FORECAST at 5%+) with
               95% bootstrap intervals over counties and the change vs adopted; stability check: fit Jan-Jun, score
               Jul-Sep (R^2 = 1 - SSE/SST), beside persistence. Coefficient p-values: errors clustered by home and
               destination county. Crossover p-values: HC1; spillover: clustered by county.
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
    m = smf.ols(BASE + f" + {v}", c).fit(cov_type="HC1")
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
import gravity_terms as gt  # noqa: E402
pairs = gt.all_pairs()
DISC = gt.stop_discount(pairs)
y9, y6, y3 = (gt.travel_visits(pairs, m, disc=DISC) for m in (gt.MONTHS, gt.MONTHS[:6], gt.MONTHS[6:]))
o = pairs.i.values
Xd = gt.design(pairs)
ld = Xd["log_dist"].values                         # centred at 25 miles
Xi = X.copy(); Xi.loc["29510"] = Xi.loc["29189"]
for v in VARS:
    Xi[v] = (Xi[v] - Xi[v].mean()) / Xi[v].std()
ev0 = gt.evaluate(Xd, pairs, y9, y6, y3, full=False)
r0 = gt.summary(ev0["loco"])
print(f"\n## 3 TRAVEL: adopted, leave one county out: weighted share error {r0['werr']:.2f}, big-flow error {r0['big']:.2f}; "
      f"Jul-Sep from Jan-Jun R^2 {gt.summary(ev0['split'])['r2']:.1%} (stability check; {gt.persistence(pairs, y6, y3)})")
print("| home-county variable x log distance | LOCO weighted error, change vs adopted [95%] | LOCO big-flow error, change [95%] | Jul-Sep R^2 | coef (2-way p) |")
print("|---|---:|---:|---:|---|")
for v in ("median_household_income", "per_capita_income", "median_age", "age_65_and_over", "households_with_broadband",
          "mean_travel_time", "below_poverty", "bachelors_or_higher", "unemployment_rate", "in_labor_force", "owner_occupied"):
    if v not in Xi:
        continue
    t = f"{v}_x_log_dist"
    if Xi[v].reindex(pairs.i).isna().any():
        print(f"| {v} | missing for some counties: not tested | | | |")
        continue
    try:
        ev = gt.evaluate(Xd.assign(**{t: Xi[v].reindex(pairs.i).values * ld}), pairs, y9, y6, y3, extra=[t])
    except np.linalg.LinAlgError:
        print(f"| {v} | singular design: not identified | | | |")
        continue
    r = gt.summary(ev["loco"])
    cw = gt.boot(ev["loco"], "werr", ref=ev0["loco"]); cb = gt.boot(ev["loco"], "big", ref=ev0["loco"])
    print(f"| {v} | {r['werr']:.2f}, {r['werr'] - r0['werr']:+.2f} [{cw[0]:+.2f}, {cw[1]:+.2f}] | {r['big']:.2f}, "
          f"{r['big'] - r0['big']:+.2f} [{cb[0]:+.2f}, {cb[1]:+.2f}] | {gt.summary(ev['split'])['r2']:.1%} | "
          f"{ev['m'].params[t]:+.3f} ({ev['m'].pvalues[t]:.3f}) |", flush=True)
