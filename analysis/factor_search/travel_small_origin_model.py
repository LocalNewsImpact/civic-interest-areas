"""A separate travel model for SMALL origins (population < 15,000) and their flows into LARGER counties.

Large and small counties are not modelled alike: a small county's residents leave for most goods and services, and how
they choose among larger centres need not follow the decay fitted mostly on big counties. Every model is fitted on
pairs from small origins only. Outcome: the adopted one (calibrated, pass-through discounted). Scored on each small
origin's share of out-of-county visits going to each larger county (weighted share error, points, with a 95% bootstrap
interval over home counties; R^2 = 1 - SSE/SST of those shares): primary, leave-one-county-out among small origins (8
folds, seed 7), Jan-Sep; stability check, fit Jan-Jun and score Jul-Sep, beside persistence (Jan-Jun observed shares).
The pooled adopted model (gravity_terms.FACTORS; LOCO over all counties), scored on the same pairs, is the reference.

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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
exec(open(Path(__file__).resolve().parents[1] / "travel_model_dc_test.py").read().split("models = [")[0])

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

from gravity_terms import loco, poisson_fit, r2_oos  # noqa: E402
import warnings  # noqa: E402
warnings.filterwarnings("ignore")
S = P.small_i.values
sub = np.flatnonzero(S)
Osub = [c for c in O if X0.loc[sub, c].sum() > 0]
tgt = S & P.larger_j.values
o = P.i.values
a9, s3, s6 = share(y9), share(y3), share(y6)


def score(ps, a, mask, draws=1000):
    """weighted share error (points) on mask pairs, 95% bootstrap over home counties, R^2 (1 - SSE/SST)."""
    d = pd.DataFrame({"o": o[mask], "n": a[mask] * np.abs(ps[mask] - a[mask]), "w": a[mask]}).groupby("o").sum()
    rng = np.random.default_rng(7)
    bs = [(lambda b: 100 * b.n.sum() / b.w.sum())(d.loc[rng.choice(d.index, len(d))]) for _ in range(draws)]
    lo, hi = np.quantile(bs, [.025, .975])
    return f"{100 * d.n.sum() / d.w.sum():.2f} [{lo:.2f}, {hi:.2f}] | {r2_oos(a[mask], ps[mask]):.3f}"


Xfe = Xof(FACTORS)
print(f"small origins: {P[S].i.nunique()} counties; their flows into larger counties carry "
      f"{a9[tgt].sum() / P[S].i.nunique():.0%} of their out-of-county visits on average\n")
print("| Model (fitted on small origins only) | LOCO: weighted share error [95%] | LOCO R^2 | Jul-Sep from Jan-Jun: error [95%] | R^2 |")
print("|---|---:|---:|---:|---:|")
print(f"| persistence: Jan-Jun observed shares | | | {score(s6, s3, tgt)} |")
print(f"| pooled adopted model (reference) | {score(loco(y9, Xfe, o), a9, tgt)} | "
      f"{score(share(poisson_fit(y6, Xfe).predict(Xfe).values), s3, tgt)} |", flush=True)
specs = {
    "distance + draw": ["log_dist", "log_dist_sq", "adjacent", "log_pop_j", "log_jobs_j", "log_places_j"],
    "+ hub (largest within 60 mi)": ["log_dist", "log_dist_sq", "adjacent", "log_pop_j", "log_jobs_j", "log_places_j", "hub60"],
    "+ size rank within 60 mi": ["log_dist", "log_dist_sq", "adjacent", "log_pop_j", "log_jobs_j", "log_places_j", "log_rank60"],
    "+ competition (Fotheringham)": ["log_dist", "log_dist_sq", "adjacent", "log_pop_j", "log_jobs_j", "log_places_j", "fotheringham"],
    "+ draw x distance": ["log_dist", "log_dist_sq", "adjacent", "log_pop_j", "log_jobs_j", "log_places_j", "log_pop_j_x_log_dist"],
    "all": ["log_dist", "log_dist_sq", "adjacent", "log_pop_j", "log_jobs_j", "log_places_j", "hub60", "log_rank60", "fotheringham", "log_pop_j_x_log_dist"],
}
for label, cols in specs.items():
    X = X0.loc[sub, cols + Osub].reset_index(drop=True)
    ph = np.full(len(P), np.nan); ph[sub] = loco(y9[sub], X, o[sub])
    m = poisson_fit(y6[sub], X)
    pt = np.zeros(len(P)); pt[sub] = m.predict(X)
    print(f"| {label} | {score(ph, a9, tgt)} | {score(share(pt), s3, tgt)} |", flush=True)
