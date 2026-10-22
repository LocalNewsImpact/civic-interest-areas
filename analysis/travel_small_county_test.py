"""Small counties: does theory predict them better than fixed effects learned from a thin sample?

Advan's panel is a sample; a small county's residents are few, so the destination and origin effects the doubly
constrained model learns from them are noisy. Three models, each fitted on January-June and scored on July-September,
scored SEPARATELY for small origins (population < 15,000) and the rest:

  fixed effects  the adopted doubly constrained model (origin and destination fixed effects; curved distance;
                 rural x distance; border; larger origins travel farther)
  theory         origin fixed effects only (each county's total outflow is known), destination draw from MEASURED
                 attributes -- log population, log jobs (LODES 2023), log places (Advan places that week) -- plus
                 Fotheringham's competing destinations log C_ij, C_ij = sum(k != i, j) places_k / d_jk
  shrunk         the fixed-effects model with its destination effects pulled toward the theory model: the theory
                 model's prediction as an offset, destination dummies under an L2 penalty (alpha chosen on held-out months)

Ceiling: the correlation of each small origin's January-June and July-September shares (sampling noise alone).
Score: share-weighted mean absolute error of destination shares (points), and R^2 of shares, per group.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
exec(open(Path(__file__).resolve().parent / "travel_model_dc_test.py").read().split("models = [")[0])

size = cov.places.astype(float).to_dict()
jobs = cov.jobs.astype(float).to_dict()
popd = cov.population.astype(float).to_dict()
fips = [f for f in FIPS if f in size]
X0["log_pop_j"] = [math.log(popd[j]) for j in pairs.j]
X0["log_jobs_j"] = [math.log(max(jobs[j], 1)) for j in pairs.j]
X0["log_places_j"] = [math.log(max(size[j], 1)) for j in pairs.j]
X0["fotheringham"] = [math.log(sum(size[k] / max(miles(j, k), 1.0) for k in fips if k not in (i, j))) for i, j in zip(pairs.i, pairs.j)]

base = pair + ["log_dist_sq", "nonmetro_i_x_log_dist_sq", "log_pop_i_x_log_dist"]
theory = base + ["log_pop_j", "log_jobs_j", "log_places_j", "fotheringham"]
small = np.array([popd[i] < 15000 for i in pairs.i])
groups = {"small origins (<15k)": small, "other origins": ~small}


def score(pred_counts, actual_counts, mask):
    ps, ys_ = share(pred_counts), share(actual_counts)
    w = ys_[mask]
    return 100 * np.sum(w * np.abs(ps[mask] - ys_[mask])) / np.sum(w), np.corrcoef(ps[mask], ys_[mask])[0, 1] ** 2


print("| Model | " + " | ".join(f"{g}: weighted share error, R^2" for g in groups) + " |")
print("|---|" + "---|" * len(groups))
s6, s3 = share(y6), share(y3)
print("| ceiling: Jan-Jun shares as the forecast | " + " | ".join(
    f"{100 * np.sum(s3[m] * np.abs(s6[m] - s3[m])) / np.sum(s3[m]):.2f}, {np.corrcoef(s6[m], s3[m])[0, 1] ** 2:.3f}" for m in groups.values()) + " |")
Xfe = pd.concat([X0[base + O], Dd], axis=1)
fe = sm.GLM(y6, Xfe, family=sm.families.Poisson()).fit(maxiter=300)
pfe = fe.predict(Xfe)
Xth = X0[theory + O]
th = sm.GLM(y6, Xth, family=sm.families.Poisson()).fit(maxiter=300)
pth = th.predict(Xth)
print("| fixed effects (adopted) | " + " | ".join(f"{a:.2f}, {b:.3f}" for a, b in (score(pfe, y3, m) for m in groups.values())) + " |")
print("| theory (measured draw + competing destinations) | " + " | ".join(f"{a:.2f}, {b:.3f}" for a, b in (score(pth, y3, m) for m in groups.values())) + " |")
print("  theory terms:", {k: round(v, 3) for k, v in th.params.items() if not k.startswith("o_")})
# shrunk: offset = theory linear predictor; free base terms + origin effects; destination dummies penalised
off = np.log(pth)
Xs = pd.concat([X0[base + O], Dd], axis=1)
pen = np.array([0.0] * (len(base) + len(O)) + [1.0] * Dd.shape[1])
for alpha in (1e-4, 1e-3, 1e-2):
    m = sm.GLM(y6, Xs, family=sm.families.Poisson(), offset=off).fit_regularized(alpha=alpha * pen, L1_wt=0.0, maxiter=300)
    ps = np.exp(off + Xs.values @ m.params.values)
    print(f"| shrunk toward theory, alpha {alpha:g} | " + " | ".join(f"{a:.2f}, {b:.3f}" for a, b in (score(ps, y3, mm) for mm in groups.values())) + " |")
