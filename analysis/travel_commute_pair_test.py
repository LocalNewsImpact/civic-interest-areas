"""Pair-level commuting as a predictor of travel: does the LODES flow between two specific counties predict visits?

Public data: LODES 2023 Missouri main origin-destination file (od_2023.csv.gz), jobs S000, home county -> work county.
  commute_out   log(1 + 1000 x workers living in i who work in j / all workers living in i)
  commute_in    log(1 + 1000 x workers living in j who work in i / all workers living in j)
Added to the adopted pooled model (destination fixed effects; centre-of-population distance). Scored as before: the 56
small rural counties held out in 8 folds, each predicted from all other counties (its commuting flows are public data
about it, so they are used for it; its travel is not), share-weighted absolute error of destination shares and the
top-3 error. Also scored for every tier with all counties held out in 8 folds.
"""
import csv
import gzip
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
exec(open(Path(__file__).resolve().parent / "travel_model_dc_test.py").read().split("models = [")[0])

unit = lambda f: "29189" if f == "29510" else f
flow, work = defaultdict(float), defaultdict(float)
with gzip.open(root / "free/od_2023.csv.gz", "rt") as fh:
    for r in csv.DictReader(fh):
        h, w = unit(r["h_geocode"][:5]), unit(r["w_geocode"][:5])
        n = float(r["S000"])
        work[h] += n
        flow[(h, w)] += n
X0["commute_out"] = [math.log1p(1000 * flow.get((unit(i), unit(j)), 0) / max(work[unit(i)], 1)) for i, j in zip(pairs.i, pairs.j)]
X0["commute_in"] = [math.log1p(1000 * flow.get((unit(j), unit(i)), 0) / max(work[unit(j)], 1)) for i, j in zip(pairs.i, pairs.j)]
base = pair + ["log_dist_sq", "nonmetro_i_x_log_dist_sq", "log_pop_i_x_log_dist"]
models = {"pooled (current)": base, "+ commuting out": base + ["commute_out"], "+ commuting out and in": base + ["commute_out", "commute_in"]}
tier = pd.read_csv(root / "analysis/county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
names = {"class 1": "small rural", "class 2": "independent towns", "class 3": "commuter counties", "class 4": "hubs"}
iu = np.array([unit(i) for i in pairs.i])
cls = np.array([tier.get(u, "class 1") for u in iu])
a = share(y9)


def cv(X, held_counties):
    folds = np.array_split(np.random.default_rng(7).permutation(held_counties), 8)
    pred = np.zeros(len(pairs))
    for f in folds:
        test = np.isin(iu, f); train = ~test
        cc = X.columns[(X[train] != 0).any()]
        m = sm.GLM(y9[train], X.loc[train, cc], family=sm.families.Poisson()).fit(maxiter=300)
        lin = X.loc[test, cc].values @ m.params.values
        pred[test] = np.exp(lin - lin.max())
    return pd.Series(pred).groupby(pairs.i.values).transform(lambda x: x / x.sum()).values


def err(ps, mask):
    return 100 * np.sum(a[mask] * np.abs(ps[mask] - a[mask])) / np.sum(a[mask])


print("| Model | " + " | ".join(names.values()) + " | small rural top-3 |")
print("|---|" + "---:|" * 5)
allc = sorted(set(iu))
for label, cols in models.items():
    X = pd.concat([X0[cols + O], Dd], axis=1)
    ps = cv(X, allc)
    top = (cls == "class 1") & (pd.Series(a).groupby(pairs.i.values).rank(ascending=False, method="first").values <= 3)
    print(f"| {label} | " + " | ".join(f"{err(ps, cls == c):.2f}" for c in names) + f" | {100 * np.mean(np.abs(ps[top] - a[top])):.2f} |", flush=True)
m = sm.GLM(y9, pd.concat([X0[models['+ commuting out and in'] + O], Dd], axis=1), family=sm.families.Poisson()).fit(maxiter=300)
print("coefficients:", {k: round(m.params[k], 3) for k in ("commute_out", "commute_in", "log_dist", "adjacent")})
