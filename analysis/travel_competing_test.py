"""Competing destinations: does a destination draw more when the origin has no comparable alternative in another direction?

The adopted travel model (doubly constrained; curved distance; rural x distance; border; larger home counties travel
farther) measures each destination's overall draw and each origin's overall outflow as fixed effects. What it does not
see is the CHOICE SET from a given home: Jefferson City pulls Osage residents harder if the next comparable centre is far
away in every other direction. Terms tested, each added to the adopted model:

  alt_ratio      log(distance from home to the nearest comparable alternative / distance to this destination);
                 comparable = a destination with at least as many places (Advan places that week, a draw measure) as this
                 one, other than home and this destination. Large when this destination has no near rival.
  alt_ratio_dir  the same, alternatives counted only in OTHER DIRECTIONS (bearing from home 60+ degrees away from this
                 destination's) -- the user's "similar opportunities in other directions"
  fotheringham   log C_ij, C_ij = sum over k != i, j of places_k / miles(j, k) (Haynes & Fotheringham 1985, the
                 competing-destinations term: a centre ringed by others competes with them)

Scored as the travel model is: deviance; July-September shares predicted by a January-June fit; large pairs (5%+ of an
origin's outside visits) within 0.8-1.25x and median miss; each study county's main destinations.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
src = open(Path(__file__).resolve().parent / "travel_model_dc_test.py").read().split("models = [")[0]
exec(src)                                          # od, pairs, X0, O, Dd, y9, y6, y3, share, big, cov, miles

cp = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO29.txt", dtype=str, encoding="utf-8-sig")
cen = {r.STATEFP + r.COUNTYFP: (float(r.LATITUDE), float(r.LONGITUDE)) for r in cp.itertuples()}
size = cov.places.astype(float).to_dict()


def bearing(a, b):
    (y1, x1), (y2, x2) = cen[a], cen[b]
    return math.atan2(y2 - y1, (x2 - x1) * math.cos(math.radians((y1 + y2) / 2)))


alt, alt_dir, acc = [], [], []
fips = [f for f in FIPS if f in cen and f in size]
for i, j in zip(pairs.i, pairs.j):
    dij = max(miles(i, j), 1.0)
    rivals = [k for k in fips if k not in (i, j) and size[k] >= size.get(j, 0)]
    dk = min((miles(i, k) for k in rivals), default=400.0)
    bj = bearing(i, j)
    rivals_dir = [k for k in rivals if abs((bearing(i, k) - bj + math.pi) % (2 * math.pi) - math.pi) >= math.radians(60)]
    dkd = min((miles(i, k) for k in rivals_dir), default=400.0)
    alt.append(math.log(max(dk, 1.0) / dij))
    alt_dir.append(math.log(max(dkd, 1.0) / dij))
    # Fotheringham (Haynes & Fotheringham 1985): C_ij = sum over k != i, j of W_k / d_jk -- excluding the ORIGIN as
    # well, which is what makes it vary by pair and not only by destination
    acc.append(math.log(sum(size[k] / max(miles(j, k), 1.0) for k in fips if k not in (i, j))))
X0["alt_ratio"], X0["alt_ratio_dir"], X0["fotheringham"] = alt, alt_dir, acc

base = pair + ["log_dist_sq", "nonmetro_i_x_log_dist_sq", "log_pop_i_x_log_dist"]
models = [("adopted", base), ("+ Fotheringham competing destinations (k != i, j)", base + ["fotheringham"])]
print("| Model | Deviance | Predicts Jul-Sep | Big pairs within 0.8-1.25x | Big pairs median miss | term (p) |")
print("|---|---:|---:|---:|---:|---|")
keep = {}
for label, cols in models:
    X = pd.concat([X0[cols + O], Dd], axis=1)
    m9 = sm.GLM(y9, X, family=sm.families.Poisson()).fit(maxiter=300)
    m6 = sm.GLM(y6, X, family=sm.families.Poisson()).fit(maxiter=300)
    p9 = m9.predict(X)
    r = (y9 / p9)[big]
    oos = np.corrcoef(share(y3), share(m6.predict(X)))[0, 1] ** 2
    miss = np.median(np.exp(np.abs(np.log(r))) - 1)
    new = [c for c in cols if c not in base]
    terms = "; ".join(f"{c} {m9.params[c]:+.3f} (p {m9.pvalues[c]:.3f})" for c in new)
    print(f"| {label} | {m9.deviance / 1e6:,.1f}M | {oos:.1%} | {np.mean((r >= .8) & (r <= 1.25)):.0%} | {miss:.0%} | {terms} |")
    keep[label] = pairs.assign(visits=y9, pred=p9, ratio=y9 / p9)
for label in ("adopted", "+ Fotheringham competing destinations (k != i, j)"):
    pr = keep[label]
    print(f"\n{label}:")
    for f, n in (("29151", "Osage"), ("29007", "Audrain"), ("29019", "Boone")):
        x = pr[pr.i == f].sort_values("visits", ascending=False).head(4)
        print(" ", n, [(cov.name[j], f"{rt:.2f}x") for j, rt in zip(x.j, x.ratio)])
