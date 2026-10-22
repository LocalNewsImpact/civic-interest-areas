"""Blend each county's observed travel pattern with the gravity model, weighted by its sample size (empirical Bayes).

predicted share(i -> j) = w_i * observed share (January-June) + (1 - w_i) * model share,  w_i = n_i / (n_i + k)
n_i = residents of county i Advan saw at home, January-June mean per month (calibration_county_month.csv, seen_at_home).
Models: the pooled adopted model, and the same with HUB-specific distance decay (tier 4 of county_class_k4.csv: its own
log distance, square, border, rural x distance and origin size x distance terms). k chosen on a split inside January-June
(fit January-April, score May-June), then applied: fit January-June, score July-September per tier (share-weighted
absolute error of destination shares, points).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
exec(open(Path(__file__).resolve().parent / "travel_model_dc_test.py").read().split("models = [")[0])

unit = lambda f: "29189" if f == "29510" else f
cal = pd.read_csv(root / "analysis/calibration_county_month.csv", dtype={"county": str})
cal["u"] = cal.county.map(unit)
n6 = cal[cal.month.isin(ALL[:6])].groupby(["u", "month"]).seen_at_home.sum().groupby("u").mean()
n4 = cal[cal.month.isin(ALL[:4])].groupby(["u", "month"]).seen_at_home.sum().groupby("u").mean()
tier = pd.read_csv(root / "analysis/county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
cls = np.array([tier.get(unit(i), "class 1") for i in pairs.i])
names = {"class 1": "small rural", "class 2": "independent towns", "class 3": "commuter counties", "class 4": "hubs"}
base = pair + ["log_dist_sq", "nonmetro_i_x_log_dist_sq", "log_pop_i_x_log_dist"]
hub = pd.Series((cls == "class 4").astype(float), index=pairs.index)
Xp = pd.concat([X0[base + O], Dd], axis=1)
Xh = pd.concat([X0[base], X0[base].mul(hub, axis=0).add_suffix("__hub"), X0[O], Dd], axis=1)
y4, y56 = y_for(ALL[:4]), y_for(ALL[4:6])


def fitpred(X, y):
    return sm.GLM(y, X, family=sm.families.Poisson()).fit(maxiter=300).predict(X)


def blend(obs_counts, model_counts, n, k):
    w = np.array([n.get(unit(i), 0) for i in pairs.i]) / (np.array([n.get(unit(i), 0) for i in pairs.i]) + k)
    return w * share(obs_counts) + (1 - w) * share(model_counts)


def err(ps, actual, mask):
    a = share(actual)
    return 100 * np.sum(a[mask] * np.abs(ps[mask] - a[mask])) / np.sum(a[mask])


allm = np.ones(len(pairs), bool)
rows = []
for label, X in (("pooled", Xp), ("hub decay", Xh)):
    # choose k on Jan-Apr -> May-Jun
    m4 = fitpred(X, y4)
    ks = [0, 100, 300, 1000, 3000, 10000, 30000, 100000]
    kbest = min(ks, key=lambda k: err(blend(y4, m4, n4, k), y56, allm))
    m6 = fitpred(X, y6)
    for name_, ps in ((f"{label} model alone", share(m6)), (f"{label} model + blend (k = {kbest:,})", blend(y6, m6, n6, kbest))):
        rows.append([name_] + [err(ps, y3, cls == c) for c in names] + [err(ps, y3, allm)])
rows.append(["persistence (observed Jan-Jun alone)"] + [err(share(y6), y3, cls == c) for c in names] + [err(share(y6), y3, allm)])
print("| Prediction of July-September | " + " | ".join(names.values()) + " | all |")
print("|---|" + "---:|" * 5)
for r in rows:
    print(f"| {r[0]} | " + " | ".join(f"{v:.2f}" for v in r[1:]) + " |")
print("\nsample size n (residents seen at home per month, Jan-Jun), median by tier:",
      {names[c]: int(np.median([n6.get(f, 0) for f in tier.index[tier == c]])) for c in names})
