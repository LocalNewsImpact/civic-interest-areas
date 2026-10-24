"""Predict a small rural county's travel WITHOUT its own data, letting the pull of jobs and retail differ by origin tier.

Held out: the 56 small rural counties (tier 1 of county_class_k4.csv), in 8 folds; each fit uses every other county's
flows, January-September. Score: each held-out county's share of out-of-county visits to each destination, share-
weighted absolute error (points), and the error on its top-3 destinations.

  1 pooled         the adopted doubly constrained model (destination fixed effects learned from other counties)
  2 tier pull      1 + origin tier x {log destination jobs, log destination retail places, log(jobs_j / jobs_i),
                   log(retail_j / retail_i)}: each tier weighs jobs and retail at the destination differently
  3 theory         no destination fixed effects: log population, jobs and retail of the destination, the same ratios,
                   all by origin tier; Fotheringham competing destinations; distance terms by origin tier
  4 county pull    1 + a pull that varies COUNTY BY COUNTY, not by tier: destination jobs and retail (log), each
                   interacted with the origin's own log population, its jobs per resident, and its access to jobs and
                   retail elsewhere (log sum over k != i of jobs_k / miles(i, k), and the same for retail) -- a county
                   with few jobs at home and none near weighs a destination's jobs more
All drivers are public: population ACS 2020-2024; jobs LODES 2023 (workplace county); retail and all establishments
Census County Business Patterns 2022 (analysis/cbp_2022_mo.csv). Tiers: population and LODES commuting outflow.
  5 tier + local   2 and 4 together: a gross pull on destination jobs and retail for each tier, plus each county's
                   own adjustment within its tier (population, jobs per resident, access to jobs and retail elsewhere)
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
exec(open(Path(__file__).resolve().parent / "travel_model_dc_test.py").read().split("models = [")[0])

unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(root / "analysis/county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
cls = pd.Series([tier.get(unit(i), "class 1") for i in pairs.i], index=pairs.index)
T = pd.get_dummies(cls).astype(float)
popd = cov.population.astype(float).to_dict(); jobs = cov.jobs.astype(float).to_dict()
# PUBLIC DATA ONLY: retail = Census County Business Patterns 2022 retail establishments (NAICS 44-45); size (for
# competing destinations) = all CBP establishments. St. Louis city + county pooled.
cbp = pd.read_csv(root / "analysis/cbp_2022_mo.csv", dtype={"fips": str}).set_index("fips")
cbp.index = cbp.index.map(unit)
cbp = cbp.groupby(level=0).sum()
retail = {f: cbp.estab_retail.get(unit(f), 1.0) for f in cov.index}
size = {f: cbp.estab_all.get(unit(f), 1.0) for f in cov.index}
fips = [f for f in FIPS if f in size]
lg = lambda v: math.log(max(v, 1.0))
X0["log_jobs_j"] = [lg(jobs[j]) for j in pairs.j]
X0["log_retail_j"] = [lg(retail[j]) for j in pairs.j]
X0["log_pop_j"] = [lg(popd[j]) for j in pairs.j]
X0["jobs_ratio"] = [lg(jobs[j]) - lg(jobs[i]) for i, j in zip(pairs.i, pairs.j)]
X0["retail_ratio"] = [lg(retail[j]) - lg(retail[i]) for i, j in zip(pairs.i, pairs.j)]
X0["fotheringham"] = [math.log(sum(size[k] / max(miles(j, k), 1.0) for k in fips if k not in (i, j))) for i, j in zip(pairs.i, pairs.j)]
base = pair + ["log_dist_sq", "nonmetro_i_x_log_dist_sq", "log_pop_i_x_log_dist"]
pull = ["log_jobs_j", "log_retail_j", "jobs_ratio", "retail_ratio"]
by_tier = lambda cols: pd.concat({f"{c}__{t}": X0[c] * T[t] for c in cols for t in T.columns}, axis=1)

X1 = pd.concat([X0[base + O], Dd], axis=1)
X2 = pd.concat([X0[base + O], by_tier(pull), Dd], axis=1)
_t_raw = pd.concat([by_tier(base + pull + ["log_pop_j"]), X0[["fotheringham"]]], axis=1)
# 4: county-by-county pull
jpr = {i: jobs[i] / popd[i] for i in fips}
acc_j = {i: math.log(sum(jobs[k] / max(miles(i, k), 1.0) for k in fips if k != i)) for i in fips}
acc_r = {i: math.log(sum(retail[k] / max(miles(i, k), 1.0) for k in fips if k != i)) for i in fips}
oi = pd.DataFrame({"log_pop_i": [lg(popd[i]) for i in pairs.i], "jobs_per_res_i": [jpr[i] for i in pairs.i],
                   "access_jobs_i": [acc_j[i] for i in pairs.i], "access_retail_i": [acc_r[i] for i in pairs.i]}, index=pairs.index)
oi_raw = oi


def standardised(train):
    """Models 3-5 with every standardised column centred and scaled on the training rows only (the held-out counties'
    means and spreads stay out of the fit). 3 is standardised because the no-fixed-effects fit otherwise overflows."""
    _t = (_t_raw - _t_raw[train].mean()) / _t_raw[train].std().replace(0, 1)
    o = (oi_raw - oi_raw[train].mean()) / oi_raw[train].std()
    cp = pd.concat({f"{d}_x_{c}": X0[d] * o[c] for d in ("log_jobs_j", "log_retail_j") for c in o.columns}, axis=1)
    return (pd.concat([_t, X0[O]], axis=1), pd.concat([X0[base + O], cp, Dd], axis=1),
            pd.concat([X0[base + O], by_tier(pull), cp, Dd], axis=1))

small = sorted(tier.index[tier == "class 1"])
rng = np.random.default_rng(7)
folds = np.array_split(rng.permutation(small), 8)
pred = {k: np.zeros(len(pairs)) for k in ("1 pooled", "2 tier pull", "3 theory", "4 county pull", "5 tier + local")}
iu = np.array([unit(i) for i in pairs.i])
for f in folds:
    test = np.isin(iu, f)
    train = ~test
    X3, X4, X5 = standardised(train)
    for label, X in (("1 pooled", X1), ("2 tier pull", X2), ("3 theory", X3), ("4 county pull", X4), ("5 tier + local", X5)):
        cols = X.columns[(X[train] != 0).any()]                       # drop the held-out origins' own fixed effects
        try:
            m = sm.GLM(y9[train], X.loc[train, cols], family=sm.families.Poisson()).fit(maxiter=300)
        except ValueError:
            m = sm.GLM(y9[train], X.loc[train, cols], family=sm.families.Poisson()).fit(method="lbfgs", maxiter=2000)
            print(f"  {label}: IRLS failed, fitted by L-BFGS", flush=True)
        lin = X.loc[test, cols].values @ m.params.values
        pred[label][test] = np.exp(lin - lin.max())                    # origin level is free: shares only
    print("fold done", flush=True)

held = np.isin(iu, small)
a = share(y9)
print("| Model | small rural held out: weighted share error | top-3 destinations: mean error |")
print("|---|---:|---:|")
for label, p in pred.items():
    ps = pd.Series(p).groupby(pairs.i.values).transform(lambda x: x / x.sum()).values
    e = 100 * np.sum(a[held] * np.abs(ps[held] - a[held])) / np.sum(a[held])
    top = held & (pd.Series(a).groupby(pairs.i.values).rank(ascending=False, method="first").values <= 3)
    e3 = 100 * np.mean(np.abs(ps[top] - a[top]))
    print(f"| {label} | {e:.2f} | {e3:.2f} |")
m = sm.GLM(y9, X2, family=sm.families.Poisson()).fit(maxiter=300)
print("tier pull, small rural (all counties):", {k: round(v, 3) for k, v in m.params.items() if "__" in k and "class 1" in k})
X5 = standardised(np.ones(len(pairs), bool))[2]       # all counties, for the reported coefficients
m5 = sm.GLM(y9, X5, family=sm.families.Poisson()).fit(maxiter=300)
print("tier + local (all counties):", {k: round(v, 3) for k, v in m5.params.items() if "_x_" in k or "__" in k})
