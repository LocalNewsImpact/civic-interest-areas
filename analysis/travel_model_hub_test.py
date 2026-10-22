"""Does a regional-centre factor remove the model's bias toward under-predicting each county's main destination?

Candidates, all from the OMB 2023 core-based statistical area delineation (built from commuting data, independent of
the Advan travel data):
  same_area        destination is in the same metro or micropolitan area as the home county
  dest_centre      destination is a central county of a metro or micropolitan area
  nearest_centre   destination is the central county nearest the home county (2020 population centres)
  log_intervening  log of the population living closer to the home county than the destination is
  log_dist_sq      squared log distance: lets travel fall off more steeply (or less) at short range
Each is added to the current model (gravity_terms.FACTORS). Scored on: deviance; Jul-Sep shares predicted by a
Jan-Jun fit; and the bias on each county's #1 destination (median actual / predicted -- 1.00 is unbiased).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import FACTORS, FIPS, all_pairs, candidates, miles, root  # noqa: E402

od = pd.read_csv(root / "analysis/od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
od = od[(od.home_county != "OUT") & (od.home_county != od.dest_county)]
pairs = all_pairs()
d = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str)
d = d[d["FIPS State Code"] == "29"]
cbsa = {"29" + r[11]: r[1] for r in d.itertuples()}
central = {"29" + r[11] for r in d.itertuples() if r[12] == "Central"}
nearest = {i: min((j for j in central if j != i), key=lambda j: miles(i, j)) for i in FIPS}
X0 = candidates(pairs)
X0["same_area"] = [int(i in cbsa and cbsa.get(i) == cbsa.get(j)) for i, j in zip(pairs.i, pairs.j)]
X0["dest_centre"] = [int(j in central) for j in pairs.j]
X0["nearest_centre"] = [int(nearest[i] == j) for i, j in zip(pairs.i, pairs.j)]
# intervening opportunities: people living closer to the home county than the destination is (Stouffer; Fotheringham's
# competing destinations) -- log(1 + population of counties k != i, j with d_ik < d_ij)
from gravity_terms import cov  # noqa: E402
D = {(i, j): miles(i, j) for i in FIPS for j in FIPS if i != j}
X0["log_intervening"] = [np.log1p(sum(cov.population[k] for k in FIPS if k not in (i, j) and D[(i, k)] < D[(i, j)]))
                         for i, j in zip(pairs.i, pairs.j)]
X0["log_dist_sq"] = X0["log_dist"] ** 2
origin = [c for c in X0.columns if c.startswith("o_")]
ALL = [f"2026-{m:02d}" for m in range(1, 10)]


def y_for(months):
    v = od[od.month.isin(months)].groupby(["home_county", "dest_county"]).visits.sum()
    return np.array([v.get((i, j), 0) for i, j in zip(pairs.i, pairs.j)], float)


y9, y6, y3 = y_for(ALL), y_for(ALL[:6]), y_for(ALL[6:])
share = lambda x: x / pd.Series(x).groupby(pairs.i.values).transform("sum").values
rank1 = pd.Series(y9).groupby(pairs.i.values).transform("max").values == y9
print("| Model | Deviance | Predicts Jul-Sep | #1 destination: actual / predicted (median, middle half) | Added factor (p) |")
print("|---|---:|---:|---|---|")
for label, extra in (("current", []), ("+ same area", ["same_area"]), ("+ area centre", ["dest_centre"]),
                     ("+ nearest centre", ["nearest_centre"]), ("+ same area + nearest centre", ["same_area", "nearest_centre"]),
                     ("+ area centre + intervening opportunities", ["dest_centre", "log_intervening"]),
                     ("+ area centre + curved distance", ["dest_centre", "log_dist_sq"]),
                     ("+ area centre + intervening + curved distance", ["dest_centre", "log_intervening", "log_dist_sq"])):
    X = X0[FACTORS + extra + origin]
    m9 = sm.GLM(y9, X, family=sm.families.Poisson()).fit(cov_type="HC1", maxiter=200)
    m6 = sm.GLM(y6, X, family=sm.families.Poisson()).fit(maxiter=200)
    r = (y9 / m9.predict(X))[rank1]
    oos = np.corrcoef(share(y3), share(m6.predict(X)))[0, 1] ** 2
    est = "; ".join(f"{e} {m9.params[e]:+.2f} ({m9.pvalues[e]:.3f})" for e in extra)
    print(f"| {label} | {m9.deviance / 1e6:,.0f}M | {oos:.1%} | {np.median(r):.2f}x ({np.quantile(r, .25):.2f}-{np.quantile(r, .75):.2f}) | {est} |")
