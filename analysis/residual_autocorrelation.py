"""Spatial autocorrelation of the travel and coverage models' residuals: Moran's I on Missouri counties.

Weights: queen contiguity (counties sharing any boundary point, gravity_terms adjacency: polygons buffered ~200 m),
row-standardised; counties without a neighbour in the set are left out. Moran's I = (n / S0) z'Wz / z'z, expected
-1 / (n - 1); p from 999 random permutations of the values over counties (two-sided: share of |I_perm - E| >= |I - E|).

Residuals (with both sets of fixed effects, raw residuals sum to zero for every home and every destination county, so
signed in-sample sums carry nothing; the measures are chosen to avoid that):
  travel, home county    held-out share-weighted absolute share error per home county (points; each home county
                         held out, 8 folds, seed 7, gravity_terms.loco) -- where the model misses most
  travel, destination    held-out signed residual per destination county: sum over held-out home counties of observed
                         minus forecast share (points) -- where the model under- (+) or over-predicts (-) a draw
  coverage, newsroom     per newsroom county, mean absolute share error (points) of coverage_model.py's fitted
                         stories (coverage_predicted_<version>.csv, pred_travel) on the destinations holding 1%+ of the
                         county's visits -- in-sample: coverage_model.py writes no held-out predictions
Printed: I, E[I], p, n for each; values for Audrain, Boone and Osage.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import FACTORS, MONTHS, all_pairs, county_stats, cov, design, loco, root, shares, travel_visits  # noqa: E402

warnings.filterwarnings("ignore")
STUDY = {"29007": "Audrain", "29019": "Boone", "29151": "Osage"}
pairs = all_pairs()
NBR = {f: set(pairs.j[(pairs.i == f) & (pairs.adjacent == 1)]) for f in cov.index}


def moran(v, draws=999, seed=7):
    """v: Series indexed by county. Queen contiguity within v's counties, row-standardised."""
    v = v.dropna()
    keep = [f for f in v.index if NBR[f] & set(v.index)]
    v = v.loc[keep]
    idx = {f: k for k, f in enumerate(v.index)}
    n = len(v)
    W = np.zeros((n, n))
    for f in v.index:
        nb = [idx[g] for g in NBR[f] if g in idx]
        W[idx[f], nb] = 1 / len(nb)
    z = v.values - v.values.mean()
    I = lambda zz: (n / W.sum()) * (zz @ W @ zz) / (zz @ zz)
    i0, e = I(z), -1 / (n - 1)
    rng = np.random.default_rng(seed)
    perm = np.array([I(rng.permutation(z)) for _ in range(draws)])
    p = (np.sum(np.abs(perm - e) >= abs(i0 - e)) + 1) / (draws + 1)
    return i0, e, p, n


o = pairs.i.values
y = travel_visits(pairs, MONTHS)
a = shares(y, o)
X = design(pairs)
ps = loco(y, X, o)
R = {"travel, held-out error by home county": county_stats(a, ps, o, y).werr,
     "travel, held-out signed residual by destination": pd.Series(100 * (a - ps)).groupby(pairs.j.values).sum()}
for version in ("all", "no_broadcast"):
    cp = pd.read_csv(root / f"analysis/coverage_predicted_{version}.csv", dtype={"i": str, "j": str})
    cp = cp[cp.groupby("i").stories.transform("sum") > 0]
    sy, sp, sv = (shares(cp[c].values, cp.i.values) for c in ("stories", "pred_travel", "visits"))
    m = sv >= 0.01
    R[f"coverage ({version}), in-sample error by newsroom county"] = pd.Series(100 * np.abs(sp - sy)[m]).groupby(cp.i.values[m]).mean()

print("| Residual | n counties | Moran's I | E[I] | p (999 permutations) | Audrain | Boone | Osage |")
print("|---|---:|---:|---:|---:|---:|---:|---:|")
for label, v in R.items():
    i0, e, p, n = moran(v)
    st = " | ".join(f"{v.get(f, np.nan):.2f}" for f in STUDY)
    print(f"| {label} | {n} | {i0:+.3f} | {e:+.3f} | {p:.3f} | {st} |")
