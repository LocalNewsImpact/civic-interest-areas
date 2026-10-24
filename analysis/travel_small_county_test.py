"""Small counties: does theory predict them better than fixed effects learned from a thin sample?

Advan's panel is a sample; a small county's residents are few, so the destination and origin effects the doubly
constrained model learns from them are noisy. Models, scored SEPARATELY for small origins (population < 15,000) and
the rest:

  fixed effects  the adopted doubly constrained model (gravity_terms.FACTORS; origin and destination fixed effects)
  theory         origin fixed effects only (each county's total outflow is known), destination draw from MEASURED
                 attributes -- log population, log jobs (LODES 2023), log places (Advan places that week) -- plus
                 Fotheringham's competing destinations log C_ij, C_ij = sum(k != i, j) places_k / d_jk
  shrunk         the fixed-effects model with its destination effects pulled toward the theory model: the theory
                 model's prediction as an offset, destination dummies under an L2 penalty; every alpha tried is shown
                 (none is chosen on the scoring months)

Outcome: the adopted one (calibrated, pass-through discounted). Primary: leave-one-county-out (8 folds, seed 7),
share-weighted absolute error of destination shares (points) with a 95% bootstrap interval over home counties and the
change against the adopted model. Stability check: fit Jan-Jun, score Jul-Sep, beside persistence (Jan-Jun observed
shares); error and R^2 = 1 - SSE/SST of shares.
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

theory = FACTORS + ["log_pop_j", "log_jobs_j", "log_places_j", "fotheringham"]
small = np.array([popd[i] < 15000 for i in pairs.i])
o = pairs.i.values
from gravity_terms import boot, county_stats, loco, poisson_fit, summary  # noqa: E402
import warnings  # noqa: E402
warnings.filterwarnings("ignore")
cs = pd.Series(small, index=o).groupby(level=0).first()
a9, s6, s3 = share(y9), share(y6), share(y3)
Xfe, Xth = Xof(FACTORS), X0[theory + O]
L = {"fixed effects (adopted)": county_stats(a9, loco(y9, Xfe, o), o, y9),
     "theory (measured draw + competing destinations)": county_stats(a9, loco(y9, Xth, o), o, y9)}
fe, th = poisson_fit(y6, Xfe), poisson_fit(y6, Xth)
pth = th.predict(Xth).values
T = {"persistence: Jan-Jun observed shares": county_stats(s3, s6, o, y3),
     "fixed effects (adopted)": county_stats(s3, share(fe.predict(Xfe).values), o, y3),
     "theory (measured draw + competing destinations)": county_stats(s3, share(pth), o, y3)}
off = np.log(pth)
pen = np.array([0.0] * (len(FACTORS) + len(O)) + [1.0] * Dd.shape[1])
for alpha in (1e-4, 1e-3, 1e-2):
    mm = sm.GLM(y6, Xfe, family=sm.families.Poisson(), offset=off).fit_regularized(alpha=alpha * pen, L1_wt=0.0, maxiter=300)
    T[f"shrunk toward theory, alpha {alpha:g}"] = county_stats(s3, share(np.exp(off + Xfe.values @ mm.params.values)), o, y3)
groups = {"small origins (<15k)": cs.reindex(L["fixed effects (adopted)"].index).values,
          "other origins": ~cs.reindex(L["fixed effects (adopted)"].index).values}
ref = L["fixed effects (adopted)"]
print("## LOCO (primary): weighted share error [95%]; change vs adopted [95%]")
print("| Model | " + " | ".join(groups) + " |\n|---|---|---|")
for label, s_ in L.items():
    cells = []
    for mk in groups.values():
        lo, hi = boot(s_, "werr", mask=mk)
        c = f"{s_[mk].werr.mean():.2f} [{lo:.2f}, {hi:.2f}]"
        if s_ is not ref:
            dl, dh = boot(s_, "werr", ref=ref, mask=mk)
            c += f"; {s_[mk].werr.mean() - ref[mk].werr.mean():+.2f} [{dl:+.2f}, {dh:+.2f}]"
        cells.append(c)
    print(f"| {label} | " + " | ".join(cells) + " |")
print("\n## Stability check (not validation): Jul-Sep from Jan-Jun, weighted share error, R^2 (1 - SSE/SST)")
print("| Forecast | " + " | ".join(groups) + " |\n|---|---|---|")
for label, s_ in T.items():
    print(f"| {label} | " + " | ".join(f"{summary(s_[mk])['werr']:.2f}, {summary(s_[mk])['r2']:.3f}" for mk in groups.values()) + " |")
print("theory terms (Jan-Jun fit):", {k: round(v, 3) for k, v in th.params.items() if not k.startswith("o_")})
