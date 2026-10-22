"""Business activity as the non-work pull, from public data: does a destination's business relative to the origin's
predict travel beyond distance, borders and commuting?

County Business Patterns 2022 establishments (analysis/cbp_2022_mo_sectors.csv): retail (NAICS 44-45), general
merchandise (452), health care (62), hospitals (622), food and lodging (72), arts and recreation (71). Each enters as
log((destination + 1) / (origin + 1)) -- a destination's business on its own is absorbed by its fixed effect; the GAP
between origin and destination is a pair measure. Added to the adopted model (with commuting). Scored: each county held
out in 8 folds (share error by tier), July-September from January-June, and the study counties' main destinations.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import all_pairs, design, root, cov  # noqa: E402

od = pd.read_csv(root / "analysis/od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
od = od[(od.home_county != "OUT") & (od.home_county != od.dest_county)]
pairs = all_pairs()
X = design(pairs)
biz = pd.read_csv(root / "analysis/cbp_2022_mo_sectors.csv", dtype={"fips": str}).set_index("fips")
SECT = ["retail", "general_merch", "health", "hospitals", "food_lodging", "arts_rec"]
for s in SECT:
    X[f"gap_{s}"] = [math.log((biz[s].get(j, 0) + 1) / (biz[s].get(i, 0) + 1)) for i, j in zip(pairs.i, pairs.j)]
ALL = [f"2026-{m:02d}" for m in range(1, 10)]


def yv(months):
    v = od[od.month.isin(months)].groupby(["home_county", "dest_county"]).visits.sum()
    return np.array([v.get((i, j), 0) for i, j in zip(pairs.i, pairs.j)], float)


y9, y6, y3 = yv(ALL), yv(ALL[:6]), yv(ALL[6:])
share = lambda x: x / pd.Series(x).groupby(pairs.i.values).transform("sum").values
basecols = [c for c in X.columns if not c.startswith("gap_")]
models = {"current (with commuting)": basecols,
          "+ retail gap": basecols + ["gap_retail"],
          "+ general merchandise gap": basecols + ["gap_general_merch"],
          "+ health care gap": basecols + ["gap_health"],
          "+ all six business gaps": basecols + [f"gap_{s}" for s in SECT]}
unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(root / "analysis/county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
cls = np.array([tier.get(unit(i), "class 1") for i in pairs.i])
names = {"class 1": "small rural", "class 2": "indep. towns", "class 3": "commuter", "class 4": "hubs"}
a = share(y9)
folds = np.array_split(np.random.default_rng(7).permutation(sorted(set(pairs.i))), 8)
print("| Model | Jul-Sep R^2 | " + " | ".join(names.values()) + " | Audrain->Marion | Osage->Boone |")
print("|---|---:|" + "---:|" * 6)
idx = {(i, j): k for k, (i, j) in enumerate(zip(pairs.i, pairs.j))}
for label, cols in models.items():
    XX = X[cols]
    m6 = sm.GLM(y6, XX, family=sm.families.Poisson()).fit(maxiter=300)
    r2 = np.corrcoef(share(y3), share(np.asarray(m6.predict(XX))))[0, 1] ** 2
    pred = np.zeros(len(pairs))
    for f in folds:
        test = pairs.i.isin(f).values; train = ~test
        cc = XX.columns[(XX[train] != 0).any()]
        m = sm.GLM(y9[train], XX.loc[train, cc], family=sm.families.Poisson()).fit(maxiter=300)
        lin = XX.loc[test, cc].values @ m.params.values
        pred[test] = np.exp(lin - lin.max())
    ps = pd.Series(pred).groupby(pairs.i.values).transform(lambda x: x / x.sum()).values
    errs = [100 * np.sum(a[cls == c] * np.abs(ps[cls == c] - a[cls == c])) / np.sum(a[cls == c]) for c in names]
    p9 = np.asarray(sm.GLM(y9, XX, family=sm.families.Poisson()).fit(maxiter=300).predict(XX))
    rat = lambda i, j: y9[idx[(i, j)]] / p9[idx[(i, j)]]
    print(f"| {label} | {r2:.1%} | " + " | ".join(f"{e:.2f}" for e in errs) + f" | {rat('29007', '29127'):.2f} | {rat('29151', '29019'):.2f} |", flush=True)
m = sm.GLM(y9, X[models["+ all six business gaps"]], family=sm.families.Poisson()).fit(maxiter=300)
print("gaps:", {s: (round(m.params[f"gap_{s}"], 3), round(m.pvalues[f"gap_{s}"], 3)) for s in SECT})
