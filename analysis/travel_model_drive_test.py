"""Driving time and the "on the way" factor.

1. Replace straight-line distance with driving time (drive_od.csv: fastest route between 2020 population centres on
   OpenStreetMap roads) in every distance term of the doubly-constrained model.
2. Add an "on the way" factor -- county j lies on the driving route from home county i to somewhere bigger:
     on_way_centre   j is on the route from i to a metro or micropolitan central county k (OMB 2023) larger than j
                     and within 90 minutes of i
     on_way_weight   log(1 + sum over destinations k whose route from i passes through j of population_k /
                     minutes_ik^2 / 1000) -- every route, weighted by how big and near its destination is
Scored on deviance, Jul-Sep shares from a Jan-Jun fit, the #1-destination bias, big pairs (>= 5% of an origin's
visits) within 0.8-1.25x, and the check against the store data: the correlation, across county pairs with 200+
visitors, between the model's log(actual / predicted) and the pair's share of visits at highway stops
(road_stop_share.csv). If the model is missing pass-through, that correlation is positive; the on-the-way factor
should shrink it.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import FACTORS, FIPS, all_pairs, candidates, cov, root  # noqa: E402

od = pd.read_csv(root / "analysis/od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
od = od[(od.home_county != "OUT") & (od.home_county != od.dest_county)]
drive = pd.read_csv(root / "analysis/drive_od.csv", dtype={"i": str, "j": str}).set_index(["i", "j"])
drive["through"] = drive.through.fillna("").map(lambda s: set(s.split(";")) if s else set())
stops = pd.read_csv(root / "analysis/road_stop_share.csv", dtype={"i": str, "j": str}).set_index(["i", "j"])
d = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str)
d = d[d["FIPS State Code"] == "29"]
central = {"29" + r[11] for r in d.itertuples() if r[12] == "Central"}
pairs = all_pairs()
key = list(zip(pairs.i, pairs.j))
minutes = np.array([drive.drive_minutes[k] for k in key])
pop = cov.population

on_centre, on_weight = [], []
for i, j in key:
    big = [k for k in central if k not in (i, j) and pop[k] > pop[j] and drive.drive_minutes[(i, k)] <= 90]
    on_centre.append(int(any(j in drive.through[(i, k)] for k in big)))
    on_weight.append(np.log1p(sum(pop[k] / drive.drive_minutes[(i, k)] ** 2 / 1000
                                  for k in FIPS if k not in (i, j) and j in drive.through[(i, k)])))

base = candidates(pairs)
FE = [c for c in base.columns if c.startswith(("o_", "d_"))]


def distance_terms(logd):
    X = pd.DataFrame(index=pairs.index)
    nonmetro = 1 - cov.metro.reindex(pairs.i).values
    X["log_dist"], X["log_dist_sq"] = logd, logd ** 2
    X["nonmetro_i_x_log_dist"], X["nonmetro_i_x_log_dist_sq"] = nonmetro * logd, nonmetro * logd ** 2
    X["log_pop_i_x_log_dist"] = np.log(pop.reindex(pairs.i).values) * logd
    X["adjacent"] = pairs.adjacent.values
    return X


straight = distance_terms(np.log(pairs.dist.values))
driving = distance_terms(np.log(minutes))
ALL = [f"2026-{m:02d}" for m in range(1, 10)]


def y_for(months):
    v = od[od.month.isin(months)].groupby(["home_county", "dest_county"]).visits.sum()
    return np.array([v.get(k, 0) for k in key], float)


y9, y6, y3 = y_for(ALL), y_for(ALL[:6]), y_for(ALL[6:])
share = lambda x: x / pd.Series(x).groupby(pairs.i.values).transform("sum").values
ys = share(y9)
rank1 = pd.Series(y9).groupby(pairs.i.values).transform("max").values == y9
big = ys >= 0.05
st = np.array([stops.road_stop_share.get(k, np.nan) for k in key])
stn = np.array([stops.visitors.get(k, 0) for k in key])
chk = (stn >= 200) & ~np.isnan(st)
print(f"on the way to a bigger centre: {sum(on_centre):,} of {len(key):,} pairs")
print("| Model | Deviance | Predicts Jul-Sep | #1 destination actual/predicted | Big pairs within 0.8-1.25x | "
      "Under-prediction vs highway-stop share (corr.) | On-the-way estimate (p) |")
print("|---|---:|---:|---|---:|---:|---|")
models = [("straight-line distance (current)", straight, []), ("driving time", driving, []),
          ("driving time + on the way to a bigger centre", driving.assign(on_way_centre=on_centre), ["on_way_centre"]),
          ("driving time + on the way, weighted", driving.assign(on_way_weight=on_weight), ["on_way_weight"])]
for label, X, extra in models:
    Xm = pd.concat([X, base[FE]], axis=1)
    m9 = sm.GLM(y9, Xm, family=sm.families.Poisson()).fit(cov_type="HC1", maxiter=300)
    m6 = sm.GLM(y6, Xm, family=sm.families.Poisson()).fit(maxiter=300)
    p9 = m9.predict(Xm)
    r = y9 / p9
    oos = np.corrcoef(share(y3), share(m6.predict(Xm)))[0, 1] ** 2
    rb = r[big]
    c = np.corrcoef(np.log(r[chk] + 1e-9), st[chk])[0, 1]
    est = "; ".join(f"{e} {m9.params[e]:+.2f} ({m9.pvalues[e]:.3f})" for e in extra)
    print(f"| {label} | {m9.deviance / 1e6:,.0f}M | {oos:.1%} | {np.median(r[rank1]):.2f}x | "
          f"{np.mean((rb >= .8) & (rb <= 1.25)):.0%} | {c:+.2f} | {est} |")
    if label == models[-1][0] or label == models[-2][0]:
        pr = pairs.assign(ratio=r)
        for f, n in (("29007", "Audrain"), ("29151", "Osage"), ("29019", "Boone")):
            x = pr.assign(v=y9)[pr.i == f].sort_values("v", ascending=False).head(4)
            print(f"    {n}: " + ", ".join(f"{cov.name[j]} {rt:.2f}x" for j, rt in zip(x.j, x.ratio)))
