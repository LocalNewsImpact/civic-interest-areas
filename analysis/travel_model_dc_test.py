"""Doubly-constrained gravity: a fixed effect for every destination as well as every origin, so each county's own
overall draw (state capital, university, hospitals, shopping) is measured from the data rather than proxied by
population and stores. What remains to explain is how distance and pair ties distribute the travel.

Scored as before: deviance; Jul-Sep shares predicted by a Jan-Jun fit; each county's #1 destination (median actual /
predicted, middle half); and pairs carrying >= 5% of an origin's visits outside the county (share within 0.8-1.25x).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import FACTORS, FIPS, all_pairs, candidates, cov, miles, root  # noqa: E402

od = pd.read_csv(root / "analysis/od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
od = od[(od.home_county != "OUT") & (od.home_county != od.dest_county)]
pairs = all_pairs()
d = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str)
d = d[d["FIPS State Code"] == "29"]
cbsa = {"29" + r[11]: r[1] for r in d.itertuples()}
central = {"29" + r[11] for r in d.itertuples() if r[12] == "Central"}
X0 = candidates(pairs)
X0["log_dist_sq"] = X0["log_dist"] ** 2
X0["dest_centre"] = [int(j in central) for j in pairs.j]
X0["same_area"] = [int(i in cbsa and cbsa.get(i) == cbsa.get(j)) for i, j in zip(pairs.i, pairs.j)]
X0["nonmetro_i_x_log_dist_sq"] = X0["nonmetro_i_x_log_dist"] * X0["log_dist"]
nearest = {i: min((j for j in central if j != i), key=lambda j: miles(i, j)) for i in FIPS}
X0["nearest_centre"] = [int(nearest[i] == j) for i, j in zip(pairs.i, pairs.j)]
X0["adjacent_centre"] = X0["adjacent"] * X0["dest_centre"]
X0["log_pop_j_x_log_dist"] = X0["log_pop_j"] * X0["log_dist"]                     # big destinations reach farther
X0["log_pop_i_x_log_dist"] = np.log(cov.population.reindex(pairs.i).values) * X0["log_dist"]   # big origins travel farther
O = [c for c in X0.columns if c.startswith("o_")]
Dd = pd.get_dummies(pairs.j, prefix="d").astype(float); Dd.index = pairs.index
Dd = Dd.drop(columns=Dd.columns[0])            # one destination dropped: the origin effects carry the level
ALL = [f"2026-{m:02d}" for m in range(1, 10)]


def y_for(months):
    v = od[od.month.isin(months)].groupby(["home_county", "dest_county"]).visits.sum()
    return np.array([v.get((i, j), 0) for i, j in zip(pairs.i, pairs.j)], float)


y9, y6, y3 = y_for(ALL), y_for(ALL[:6]), y_for(ALL[6:])
share = lambda x: x / pd.Series(x).groupby(pairs.i.values).transform("sum").values
ys = share(y9)
rank1 = pd.Series(y9).groupby(pairs.i.values).transform("max").values == y9
big = ys >= 0.05
pair = ["log_dist", "nonmetro_i_x_log_dist", "adjacent"]
models = [
    ("singly constrained (current)", FACTORS, False),
    ("singly + area centre + curved distance", FACTORS + ["dest_centre", "log_dist_sq"], False),
    ("doubly constrained: distance, rural x distance, border", pair, True),
    ("doubly + curved distance", pair + ["log_dist_sq", "nonmetro_i_x_log_dist_sq"], True),
    ("doubly + curved distance + same metro/micro area", pair + ["log_dist_sq", "nonmetro_i_x_log_dist_sq", "same_area"], True),
    ("doubly + curved + destination size x distance", pair + ["log_dist_sq", "nonmetro_i_x_log_dist_sq", "log_pop_j_x_log_dist"], True),
    ("doubly + curved + origin size x distance", pair + ["log_dist_sq", "nonmetro_i_x_log_dist_sq", "log_pop_i_x_log_dist"], True),
    ("doubly + curved + both sizes x distance", pair + ["log_dist_sq", "nonmetro_i_x_log_dist_sq", "log_pop_j_x_log_dist", "log_pop_i_x_log_dist"], True),
    ("doubly + curved + both sizes x distance + adjacent centre + nearest centre",
     pair + ["log_dist_sq", "nonmetro_i_x_log_dist_sq", "log_pop_j_x_log_dist", "log_pop_i_x_log_dist", "adjacent_centre", "nearest_centre"], True),
]
print("| Model | Deviance | Predicts Jul-Sep | #1 destination actual/predicted | Big pairs within 0.8-1.25x | Big pairs off by 1.5x+ either way |")
print("|---|---:|---:|---|---:|---:|")
for label, cols, dc in models:
    X = pd.concat([X0[cols + O]] + ([Dd] if dc else []), axis=1)
    m9 = sm.GLM(y9, X, family=sm.families.Poisson()).fit(maxiter=300)
    m6 = sm.GLM(y6, X, family=sm.families.Poisson()).fit(maxiter=300)
    p9 = m9.predict(X)
    r = y9 / p9
    oos = np.corrcoef(share(y3), share(m6.predict(X)))[0, 1] ** 2
    rb = r[big]
    print(f"| {label} | {m9.deviance / 1e6:,.0f}M | {oos:.1%} | {np.median(r[rank1]):.2f}x ({np.quantile(r[rank1], .25):.2f}-"
          f"{np.quantile(r[rank1], .75):.2f}) | {np.mean((rb >= .8) & (rb <= 1.25)):.0%} | {np.mean((rb >= 1.5) | (rb <= 1 / 1.5)):.0%} |")
    best = (m9, p9)   # the last model listed
m9, p9 = best
print("\nbest model's estimates:", {k: round(v, 3) for k, v in m9.params.items() if not k.startswith(("o_", "d_"))})
pr = pairs.assign(visits=y9, pred=p9, ratio=y9 / p9)
for f, n in (("29151", "Osage"), ("29007", "Audrain"), ("29019", "Boone")):
    x = pr[pr.i == f].sort_values("visits", ascending=False).head(4)
    print(n, [(cov.name[j], f"{rt:.2f}x") for j, rt in zip(x.j, x.ratio)])
