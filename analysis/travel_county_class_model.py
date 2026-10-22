"""County classes from size and job dependence, and a travel model whose pair terms differ by the ORIGIN's class.

Classes: k-means (k = 2, 3, 4) on standardised log population (ACS 2020-2024) and commuting outflow (LODES 2023
Missouri main file: employed residents working in another county / employed residents; St. Louis city + county one
unit, as in crossover_compare.py). k-means is run from 50 seeds and the lowest within-class spread kept.

Model: the adopted doubly constrained travel model, with every pair term (log distance and its square, shared border,
rural x distance and its square, origin size x distance) interacted with the origin's class, so each class gets its
own distance decay and border effect; destination fixed effects shared. Fitted on January-June, scored on
July-September per origin class: share-weighted absolute error of destination shares (points), R^2. Reference: the
pooled adopted model scored on the same classes; ceiling: the January-June observed shares.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
exec(open(Path(__file__).resolve().parent / "travel_model_dc_test.py").read().split("models = [")[0])

cc = pd.read_csv(root / "analysis/crossover_compare.csv", dtype={"Unnamed: 0": str}).rename(columns={"Unnamed: 0": "fips"}).set_index("fips")
unit = lambda f: "29189" if f == "29510" else f
feat = pd.DataFrame({"log_pop": np.log(cc.population), "out": cc.commute_emp}).dropna()
Z = (feat - feat.mean()) / feat.std()


def kmeans(Z, k, seeds=50):
    best = None
    for s in range(seeds):
        rng = np.random.default_rng(s)
        c = Z.values[rng.choice(len(Z), k, replace=False)]
        for _ in range(100):
            lab = np.argmin(((Z.values[:, None, :] - c[None]) ** 2).sum(2), 1)
            nc = np.array([Z.values[lab == j].mean(0) if (lab == j).any() else c[j] for j in range(k)])
            if np.allclose(nc, c):
                break
            c = nc
        sse = ((Z.values - c[lab]) ** 2).sum()
        if best is None or sse < best[0]:
            best = (sse, lab, c)
    return best[1]


base = pair + ["log_dist_sq", "nonmetro_i_x_log_dist_sq", "log_pop_i_x_log_dist"]
Xfe = pd.concat([X0[base + O], Dd], axis=1)
pooled = sm.GLM(y6, Xfe, family=sm.families.Poisson()).fit(maxiter=300).predict(Xfe)
s6, s3 = share(y6), share(y3)


def score(pred, mask):
    ps = share(pred)
    w = s3[mask]
    return 100 * np.sum(w * np.abs(ps[mask] - s3[mask])) / np.sum(w), np.corrcoef(ps[mask], s3[mask])[0, 1] ** 2


for k in (2, 3, 4):
    lab = pd.Series(kmeans(Z, k), index=Z.index)
    # name classes by mean population, smallest first
    order = feat.log_pop.groupby(lab).mean().sort_values().index
    names = {c: f"class {i + 1}" for i, c in enumerate(order)}
    cls = pd.Series([names[lab[unit(i)]] if unit(i) in lab.index else "class 1" for i in pairs.i], index=pairs.index)
    print(f"\n## k = {k}")
    for c in sorted(set(names.values())):
        m = lab.map(names) == c
        print(f"  {c}: {m.sum()} counties; median population {int(np.exp(feat.log_pop[m].median())):,}; "
              f"median commuting out {feat.out[m].median():.0%}; e.g. {', '.join(cc.name[m.index[m]].head(5))}")
    D = pd.get_dummies(cls).astype(float)
    inter = pd.concat({f"{t}__{c}": X0[t] * D[c] for t in base for c in D.columns}, axis=1)
    Xc = pd.concat([inter, X0[O], Dd], axis=1)
    pc = sm.GLM(y6, Xc, family=sm.families.Poisson()).fit(maxiter=300).predict(Xc)
    print("  | Origin class | ceiling | pooled model | class-specific model |")
    print("  |---|---|---|---|")
    for c in sorted(set(names.values())):
        mk = (cls == c).values
        ce = (100 * np.sum(s3[mk] * np.abs(s6[mk] - s3[mk])) / np.sum(s3[mk]), np.corrcoef(s6[mk], s3[mk])[0, 1] ** 2)
        a, b = score(pooled, mk), score(pc, mk)
        print(f"  | {c} | {ce[0]:.2f}, {ce[1]:.3f} | {a[0]:.2f}, {a[1]:.3f} | {b[0]:.2f}, {b[1]:.3f} |")
    a, b = score(pooled, np.ones(len(pairs), bool)), score(pc, np.ones(len(pairs), bool))
    print(f"  | all origins | | {a[0]:.2f}, {a[1]:.3f} | {b[0]:.2f}, {b[1]:.3f} |")
    lab.map(names).rename("class").to_csv(root / f"analysis/county_class_k{k}.csv")
