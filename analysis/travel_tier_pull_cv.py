"""Does the pull of destination jobs and retail differ by origin tier, or county by county, beyond the adopted model?

Baseline: the adopted travel model (gravity_terms.FACTORS, the eight terms: five distance terms, adjacency, commuting
out and in; origin and destination fixed effects) on the adopted outcome (visits_statewide, pass-through discounted;
travel_model_dc_test.py preamble). Candidates, each added to the baseline:
  + tier pull      origin tier x {log destination jobs, log destination retail places}, hubs the reference tier (the
                   destination effects absorb the hubs' slope; the ratios log(x_j / x_i) of the 2026-10-18 version are
                   the same terms once origin and destination effects are in, so they are dropped)
  + county pull    destination jobs and retail (log), each x the origin's own log population, jobs per resident and
                   access to jobs and retail elsewhere (log sum over k != i of x_k / miles(i, k)), the origin measures
                   standardised on the training counties only
  + tier + local   both
  theory           no destination effects: the eight terms, origin tier x {log destination population, jobs, retail},
                   Fotheringham competing destinations; standardised on the training counties only
Public drivers: population ACS 2020-2024; jobs LODES 2023 (workplace county); retail and all establishments CBP 2022
(analysis/cbp_2022_mo.csv). Tiers: county_class_k4.csv.

Scored as the travel model: every home county held out (8 folds, seed 7), share-weighted absolute share error over all
Missouri destinations (primary), and top-3 error = mean absolute share error of each county's three largest FORECAST
destinations (selection on the observed share is biased upward). Both for all counties and the 56 small rural ones.
Decision through the nested guard (gravity_terms.py SELECTION): in each of the 8 outer training sets every candidate is
scored by 7-fold leave-county-out inside it and the lowest inner error chosen; the chosen model's held-out error is
compared with the adopted model's on the same folds, county-paired 95% interval (1,000 draws); an addition is adopted
only if that interval excludes zero.
Fits: Poisson GLM by IRLS from the full-data fit's coefficients (start values); every fit's convergence is checked and
a fit that does not converge is redone from zero by L-BFGS (counted in the output).
"""
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
exec(open(Path(__file__).resolve().parent / "travel_model_dc_test.py").read().split("models = [")[0])
import gravity_terms as gt  # noqa: E402
warnings.filterwarnings("ignore")

unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(root / "analysis/county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
o = pairs.i.values
cls = pd.Series([tier.get(unit(i), "class 1") for i in o], index=pairs.index)
TT = pd.get_dummies(cls).astype(float)
popd = cov.population.astype(float).to_dict(); jobs = cov.jobs.astype(float).to_dict()
cbp = pd.read_csv(root / "analysis/cbp_2022_mo.csv", dtype={"fips": str}).set_index("fips")
cbp.index = cbp.index.map(unit)
cbp = cbp.groupby(level=0).sum()
retail = {f: cbp.estab_retail.get(unit(f), 1.0) for f in cov.index}
size = {f: cbp.estab_all.get(unit(f), 1.0) for f in cov.index}
fips = [f for f in FIPS if f in size]
lg = lambda v: math.log(max(v, 1.0))
Z = pd.DataFrame(index=pairs.index)
Z["log_jobs_j"] = [lg(jobs[j]) for j in pairs.j]
Z["log_retail_j"] = [lg(retail[j]) for j in pairs.j]
Z["log_pop_j"] = [lg(popd[j]) for j in pairs.j]
Z["fotheringham"] = [math.log(sum(size[k] / max(miles(j, k), 1.0) for k in fips if k not in (i, j))) for i, j in zip(pairs.i, pairs.j)]
by_tier = lambda cols, tiers: pd.concat({f"{c}__{t}": Z[c] * TT[t] for c in cols for t in tiers}, axis=1)
TIER_PULL = by_tier(["log_jobs_j", "log_retail_j"], ["class 1", "class 2", "class 3"])
THEORY_RAW = pd.concat([by_tier(["log_pop_j", "log_jobs_j", "log_retail_j"], list(TT.columns)), Z[["fotheringham"]]], axis=1)
jpr = {i: jobs[i] / popd[i] for i in fips}
acc_j = {i: math.log(sum(jobs[k] / max(miles(i, k), 1.0) for k in fips if k != i)) for i in fips}
acc_r = {i: math.log(sum(retail[k] / max(miles(i, k), 1.0) for k in fips if k != i)) for i in fips}
OI_RAW = pd.DataFrame({"log_pop_i": [lg(popd[i]) for i in o], "jobs_per_res_i": [jpr[i] for i in o],
                       "access_jobs_i": [acc_j[i] for i in o], "access_retail_i": [acc_r[i] for i in o]}, index=pairs.index)
BASE = pd.concat([X0[FACTORS + O], Dd], axis=1)


def design(name, train):
    """Design matrix of a candidate; standardised columns use the training rows' means and spreads only."""
    if name == "adopted":
        return BASE
    if name == "+ tier pull":
        return pd.concat([BASE, TIER_PULL], axis=1)
    oi = (OI_RAW - OI_RAW[train].mean()) / OI_RAW[train].std()
    cp = pd.concat({f"{d}_x_{c}": Z[d] * oi[c] for d in ("log_jobs_j", "log_retail_j") for c in oi.columns}, axis=1)
    if name == "+ county pull":
        return pd.concat([BASE, cp], axis=1)
    if name == "+ tier + local":
        return pd.concat([BASE, TIER_PULL, cp], axis=1)
    th = (THEORY_RAW - THEORY_RAW[train].mean()) / THEORY_RAW[train].std().replace(0, 1)
    return pd.concat([X0[FACTORS + O], th], axis=1)              # theory: no destination effects


CANDS = ["adopted", "+ tier pull", "+ county pull", "+ tier + local", "theory (no destination effects)"]
ALL = np.ones(len(pairs), bool)
START = {n: pd.Series(np.asarray(gt.poisson_fit(y9, design(n, ALL)).params), index=design(n, ALL).columns) for n in CANDS}
FALLBACK = {"n": 0, "fits": 0}


def fit(name, yy, XX):
    FALLBACK["fits"] += 1
    try:
        m = sm.GLM(yy, XX, family=sm.families.Poisson()).fit(maxiter=300, start_params=START[name].reindex(XX.columns).fillna(0).values)
        if m.converged and np.all(np.isfinite(m.params)):
            return np.asarray(m.params)
    except (ValueError, np.linalg.LinAlgError):
        pass
    FALLBACK["n"] += 1
    return np.asarray(sm.GLM(yy, XX, family=sm.families.Poisson()).fit(method="lbfgs", maxiter=3000).params)


def held_out(name, rows, counties, folds, seed=7):
    """Shares for the home counties in `counties` (within `rows`), each fold predicted from the rest of `rows`."""
    pred = np.full(len(pairs), np.nan)
    for f in np.array_split(np.random.default_rng(seed).permutation(sorted(counties)), folds):
        test = rows & np.isin(o, f); train = rows & ~test
        X = design(name, train)
        cc = X.columns[(X[train] != 0).any()]
        lin = X.loc[test, cc].values @ fit(name, y9[train], X.loc[train, cc])
        lin = lin - pd.Series(lin).groupby(o[test]).transform("max").values      # each origin's own maximum
        pred[test] = gt.shares(np.exp(lin), o[test])
    return pred


a = share(y9)
counties = sorted(set(o))
small = sorted({i for i in counties if tier.get(unit(i), "class 1") == "class 1"})


def top3(ps, m):
    rk = pd.Series(ps).groupby(o).rank(ascending=False, method="first").values
    t = m & (rk <= 3)
    return 100 * np.mean(np.abs(ps[t] - a[t]))


# one at a time (reference only)
P = {n: held_out(n, ALL, counties, 8) for n in CANDS}
ST = {n: gt.county_stats(a, P[n], o, y9) for n in CANDS}
sm_mask = np.isin(o, small)
print("Held out (8 folds), share-weighted error over all Missouri destinations; top-3 by forecast share:")
print("| Model | all counties (115) | small rural (56) | top-3, small rural | gain vs adopted, all [95%] |\n|---|---:|---:|---:|---:|")
for n in CANDS:
    s = ST[n]; sr = s.index.isin(small)
    gain = "" if n == "adopted" else "{:+.3f} [{:+.3f}, {:+.3f}]".format(ST["adopted"].werr.mean() - s.werr.mean(), *gt.boot(ST["adopted"], "werr", ref=s))
    print(f"| {n} (one at a time, not nested) | {s.werr.mean():.3f} | {s.werr[sr].mean():.3f} | {top3(P[n], sm_mask):.2f} | {gain} |", flush=True)

# nested guard
outer = np.full(len(pairs), np.nan); ref = np.full(len(pairs), np.nan)
for k, f in enumerate(np.array_split(np.random.default_rng(7).permutation(counties), 8)):
    test = np.isin(o, f); train = ~test
    inner = {n: gt.county_stats(a[train], held_out(n, train, set(o[train]), 7)[train], o[train]).werr.mean() for n in CANDS}
    best = min(inner, key=inner.get)
    outer[test] = P[best][test]          # the same 8 folds (seed 7) as the one-at-a-time fits: fitted on this training set
    ref[test] = P["adopted"][test]
    print(f"  outer fold {k + 1}: lowest inner error {best} ({inner[best]:.3f}; adopted {inner['adopted']:.3f})", flush=True)
sr_, sa_ = gt.county_stats(a, ref, o, y9), gt.county_stats(a, outer, o, y9)
lo, hi = gt.boot(sr_, "werr", ref=sa_)
lo_s, hi_s = gt.boot(sr_, "werr", ref=sa_, mask=sr_.index.isin(small))
print(f"| nested (lowest inner error) | {sa_.werr.mean():.3f} | {sa_.werr[sa_.index.isin(small)].mean():.3f} | {top3(outer, sm_mask):.2f} | "
      f"{sr_.werr.mean() - sa_.werr.mean():+.3f} [{lo:+.3f}, {hi:+.3f}] |")
print(f"nested gain, small rural: {sr_.werr[sr_.index.isin(small)].mean() - sa_.werr[sa_.index.isin(small)].mean():+.3f} [{lo_s:+.3f}, {hi_s:+.3f}]")
print("DECISION (adopt only if the nested gain's interval excludes zero): " + ("adopt the nested choice" if lo > 0 else "no addition adopted"))
print(f"fits: {FALLBACK['fits']}, not converged by IRLS from the full-data start and refitted by L-BFGS: {FALLBACK['n']}")
m = gt.poisson_fit(y9, design("+ tier pull", ALL))
print("tier pull (all counties), log destination jobs / retail by tier, hubs = reference:",
      {k: round(v, 3) for k, v in m.params.items() if "__" in k})
