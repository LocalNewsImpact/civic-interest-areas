"""County classes from size and job dependence, and a travel model whose pair terms differ by the ORIGIN's class.

Classes: k-means (k = 2, 3, 4) on standardised log population (ACS 2020-2024) and commuting outflow (LODES 2023
Missouri main file: employed residents working in another county / employed residents; St. Louis city + county one
unit, as in crossover_compare.py). k-means is run from 50 seeds and the lowest within-class spread kept.

Model: the adopted doubly constrained travel model (gravity_terms.FACTORS), with every pair term interacted with the
origin's class, so each class gets its own distance decay, border and commuting effect; destination fixed effects
shared. Outcome: the adopted one (calibrated, pass-through discounted). Scored per origin class: leave-one-county-out
(8 folds, seed 7; primary) share-weighted absolute error of destination shares (points) with a 95% bootstrap interval
over home counties and the change against the pooled model; and the Jan-Jun -> Jul-Sep stability check (error; R^2 =
1 - SSE/SST) beside persistence (Jan-Jun observed shares).
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
exec(open(Path(__file__).resolve().parent / "travel_model_dc_test.py").read().split("models = [")[0])
from gravity_terms import poisson_fit  # noqa: E402

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


from gravity_terms import boot, county_stats, loco, summary  # noqa: E402
warnings.filterwarnings("ignore")
o = pairs.i.values
a9, s6, s3 = share(y9), share(y6), share(y3)
Xfe = Xof(FACTORS)
pooled_loco = county_stats(a9, loco(y9, Xfe, o), o, y9)
pooled_split = county_stats(s3, share(poisson_fit(y6, Xfe).predict(Xfe).values), o, y3)
persist = county_stats(s3, s6, o, y3)


def cell(s, mk, ref=None):
    lo, hi = boot(s, "werr", mask=mk)
    t = f"{s[mk].werr.mean():.2f} [{lo:.2f}, {hi:.2f}]"
    if ref is not None:
        dl, dh = boot(s, "werr", ref=ref, mask=mk)
        t += f"; {s[mk].werr.mean() - ref[mk].werr.mean():+.2f} [{dl:+.2f}, {dh:+.2f}]"
    return t


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
    inter = pd.concat({f"{t}__{c}": X0[t] * D[c] for t in FACTORS for c in D.columns}, axis=1)
    Xc = pd.concat([inter, X0[O], Dd], axis=1)
    cl_loco = county_stats(a9, loco(y9, Xc, o), o, y9)
    cl_split = county_stats(s3, share(poisson_fit(y6, Xc).predict(Xc).values), o, y3)
    ccls = pd.Series(cls.values, index=o).groupby(level=0).first().reindex(pooled_loco.index)
    print("  | Origin class | LOCO: pooled | LOCO: class-specific (change vs pooled) | Jul-Sep: persistence | "
          "Jul-Sep: pooled | Jul-Sep: class-specific |")
    print("  |---|---|---|---|---|---|")
    for c in sorted(set(names.values())) + ["all origins"]:
        mk = np.ones(len(ccls), bool) if c == "all origins" else (ccls == c).values
        sp = [summary(x[mk]) for x in (persist, pooled_split, cl_split)]
        print(f"  | {c} | {cell(pooled_loco, mk)} | {cell(cl_loco, mk, pooled_loco)} | "
              + " | ".join(f"{r['werr']:.2f}, R^2 {r['r2']:.3f}" for r in sp) + " |", flush=True)
    lab.map(names).rename("class").to_csv(root / f"analysis/county_class_k{k}.csv")
