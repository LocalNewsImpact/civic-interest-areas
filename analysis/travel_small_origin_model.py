"""A separate travel model for SMALL origins (population < 15,000) and their flows into LARGER counties.

Large and small counties are not modelled alike: a small county's residents leave for most goods and services, and how
they choose among larger centres need not follow the decay fitted mostly on big counties. Every model is fitted on
January-June pairs from small origins only, scored on July-September: each small origin's share of out-of-county visits
going to each larger county (weighted share error, points; R^2 of shares). The pooled adopted model, scored on the same
pairs, is the reference; the January-June observed shares are the ceiling.

Terms tried for small origins (destination draw is MEASURED, so the model can predict a thin sample):
  distance     log distance and its square; shared border
  draw         log population, log jobs (LODES 2023), log places of the destination
  hub          destination is the largest county within 60 miles of the origin; destination's size rank among the
               counties within 60 miles (1 = largest)
  competition  Fotheringham's log C_ij (sum over k != i, j of places_k / d_jk)
  draw x dist  log population of destination x log distance (bigger centres reach farther for small towns)
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
exec(open(Path(__file__).resolve().parent / "travel_model_dc_test.py").read().split("models = [")[0])

size = cov.places.astype(float).to_dict(); jobs = cov.jobs.astype(float).to_dict(); popd = cov.population.astype(float).to_dict()
fips = [f for f in FIPS if f in size]
P = pairs.copy()
P["small_i"] = [popd[i] < 15000 for i in P.i]
P["larger_j"] = [popd[j] > popd[i] for i, j in zip(P.i, P.j)]
X0["log_pop_j"] = [math.log(popd[j]) for j in P.j]
X0["log_jobs_j"] = [math.log(max(jobs[j], 1)) for j in P.j]
X0["log_places_j"] = [math.log(max(size[j], 1)) for j in P.j]
X0["fotheringham"] = [math.log(sum(size[k] / max(miles(j, k), 1.0) for k in fips if k not in (i, j))) for i, j in zip(P.i, P.j)]
near = {i: sorted([k for k in fips if k != i and miles(i, k) <= 60], key=lambda k: -popd[k]) for i in fips}
X0["hub60"] = [int(bool(near[i]) and near[i][0] == j) for i, j in zip(P.i, P.j)]
X0["rank60"] = [(near[i].index(j) + 1) if j in near[i] else 20 for i, j in zip(P.i, P.j)]
X0["log_rank60"] = np.log(X0["rank60"])
X0["log_pop_j_x_log_dist"] = X0["log_pop_j"] * X0["log_dist"]

# pooled adopted model, all pairs, Jan-Jun
base = pair + ["log_dist_sq", "nonmetro_i_x_log_dist_sq", "log_pop_i_x_log_dist"]
Xfe = pd.concat([X0[base + O], Dd], axis=1)
pfe = sm.GLM(y6, Xfe, family=sm.families.Poisson()).fit(maxiter=300).predict(Xfe)

S = P.small_i.values
sub = np.flatnonzero(S)
Osub = [c for c in O if X0.loc[sub, c].sum() > 0]
tgt = S & P.larger_j.values


def score(pred, mask):
    ps = pd.Series(pred).groupby(P.i.values).transform(lambda x: x / x.sum()).values
    ys_ = share(y3)
    w = ys_[mask]
    return 100 * np.sum(w * np.abs(ps[mask] - ys_[mask])) / np.sum(w), np.corrcoef(ps[mask], ys_[mask])[0, 1] ** 2


s6 = share(y6)
print(f"small origins: {P[S].i.nunique()} counties; their flows into larger counties carry "
      f"{share(y9)[tgt].sum() / P[S].i.nunique():.0%} of their out-of-county visits on average\n")
print("| Model (fitted on small origins only, Jan-Jun) | Into larger counties: weighted share error | R^2 |")
print("|---|---:|---:|")
print(f"| ceiling: Jan-Jun observed shares | {100 * np.sum(share(y3)[tgt] * np.abs(s6[tgt] - share(y3)[tgt])) / np.sum(share(y3)[tgt]):.2f} | {np.corrcoef(s6[tgt], share(y3)[tgt])[0, 1] ** 2:.3f} |")
a, b = score(pfe, tgt); print(f"| pooled adopted model (reference) | {a:.2f} | {b:.3f} |")
specs = {
    "distance + draw": ["log_dist", "log_dist_sq", "adjacent", "log_pop_j", "log_jobs_j", "log_places_j"],
    "+ hub (largest within 60 mi)": ["log_dist", "log_dist_sq", "adjacent", "log_pop_j", "log_jobs_j", "log_places_j", "hub60"],
    "+ size rank within 60 mi": ["log_dist", "log_dist_sq", "adjacent", "log_pop_j", "log_jobs_j", "log_places_j", "log_rank60"],
    "+ competition (Fotheringham)": ["log_dist", "log_dist_sq", "adjacent", "log_pop_j", "log_jobs_j", "log_places_j", "fotheringham"],
    "+ draw x distance": ["log_dist", "log_dist_sq", "adjacent", "log_pop_j", "log_jobs_j", "log_places_j", "log_pop_j_x_log_dist"],
    "all": ["log_dist", "log_dist_sq", "adjacent", "log_pop_j", "log_jobs_j", "log_places_j", "hub60", "log_rank60", "fotheringham", "log_pop_j_x_log_dist"],
}
for label, cols in specs.items():
    X = X0.loc[sub, cols + Osub]
    m = sm.GLM(y6[sub], X, family=sm.families.Poisson()).fit(maxiter=300)
    pred = np.zeros(len(P)); pred[sub] = m.predict(X)
    a, b = score(pred, tgt)
    extra = {c: round(m.params[c], 3) for c in cols if c not in ("log_dist", "log_dist_sq", "adjacent")}
    print(f"| {label} | {a:.2f} | {b:.3f} |   {extra}")
