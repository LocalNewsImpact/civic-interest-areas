"""Discount pass-through stops instead of modelling routes.

The Neighborhood Patterns county counts cannot separate a gas stop from any other stop. The store-level data can: for
each county pair, road_stop_share.csv gives the share of March visits at gas stations, convenience stores and fast
food. Buying gas where you shop is normal, so only the EXCESS over the statewide out-of-county share (12.5%) is treated
as pass-through:  adjusted visits_ij = visits_ij x (1 - max(0, road_stop_share_ij - 0.125)), for pairs with 200+
store-level visitors (others unadjusted). Same doubly-constrained straight-line model (gravity_terms.py), refitted.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import all_pairs, cov, design, root  # noqa: E402

od = pd.read_csv(root / "analysis/od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
od = od[(od.home_county != "OUT") & (od.home_county != od.dest_county)]
stops = pd.read_csv(root / "analysis/road_stop_share.csv", dtype={"i": str, "j": str}).set_index(["i", "j"])
BASE = 0.125
pairs = all_pairs()
key = list(zip(pairs.i, pairs.j))
X = design(pairs)
ALL = [f"2026-{m:02d}" for m in range(1, 10)]
excess = np.array([max(0.0, stops.road_stop_share[k] - BASE) if k in stops.index and stops.visitors[k] >= 200 else 0.0
                   for k in key])


def y_for(months):
    v = od[od.month.isin(months)].groupby(["home_county", "dest_county"]).visits.sum()
    return np.array([v.get(k, 0) for k in key], float)


share = lambda x: x / pd.Series(x).groupby(pairs.i.values).transform("sum").values
print(f"pairs discounted: {np.sum(excess > 0):,}; visits removed: {np.sum(y_for(ALL) * excess) / y_for(ALL).sum():.1%} of all")
print("| Visits | Deviance | Predicts Jul-Sep | #1 destination actual/predicted | Big pairs within 0.8-1.25x | Big pairs off 1.5x+ |")
print("|---|---:|---:|---|---:|---:|")
for label, adj in (("as recorded", np.zeros(len(key))), ("excess highway stops discounted", excess)):
    y9, y6, y3 = (y_for(m) * (1 - adj) for m in (ALL, ALL[:6], ALL[6:]))
    m9 = sm.GLM(y9, X, family=sm.families.Poisson()).fit(maxiter=300)
    m6 = sm.GLM(y6, X, family=sm.families.Poisson()).fit(maxiter=300)
    r = y9 / m9.predict(X)
    rank1 = pd.Series(y9).groupby(pairs.i.values).transform("max").values == y9
    big = share(y9) >= 0.05
    rb = r[big]
    print(f"| {label} | {m9.deviance / 1e6:,.0f}M | {np.corrcoef(share(y3), share(m6.predict(X)))[0, 1] ** 2:.1%} | "
          f"{np.median(r[rank1]):.2f}x | {np.mean((rb >= .8) & (rb <= 1.25)):.0%} | {np.mean((rb >= 1.5) | (rb <= 1 / 1.5)):.0%} |")
    pr = pairs.assign(ratio=r, v=y9, ex=adj)
    for f, n in (("29007", "Audrain"), ("29151", "Osage"), ("29019", "Boone")):
        x = pr[pr.i == f].sort_values("v", ascending=False).head(4)
        print(f"    {n}: " + ", ".join(f"{cov.name[j]} {rt:.2f}x (-{e:.0%})" for j, rt, e in zip(x.j, x.ratio, x.ex)))
