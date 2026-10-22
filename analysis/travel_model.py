"""Statewide travel model, Missouri, Jan-Sep 2026: where each county's residents go.

Visits by residents of county i to county j (i != j), Advan Neighborhood Patterns Plus, summed over the months used
(od_mo_2026.csv). A doubly-constrained gravity model -- fixed effects for every home county and every destination, and
the pair terms in gravity_terms.py -- estimated by Poisson pseudo-maximum likelihood (PPML, the standard gravity
estimator) with robust (HC1) errors. Fit on Jan-Sep (the model) and on Jan-Jun alone, scored on Jul-Sep.

PASS-THROUGH DISCOUNT. A device is counted wherever it stops, so a gas stop on the way to somewhere else counts as a
visit. The county counts cannot separate those stops; the store-level data can (road_stop_share.csv: each county
pair's share of March visits at gas stations, convenience stores and fast food). Buying gas where you shop is normal,
so only the excess over the statewide out-of-county share (12.5%) is removed:
  visits_ij x (1 - max(0, road_stop_share_ij - 0.125)), for pairs with 200+ store-level visitors.
It removes 3.0% of out-of-county visits (travel_model_stop_discount_test.py). Driving time and an on-the-way route
factor were tested and added little statewide (travel_model_drive_test.py).
Output: od_predicted.csv -- every pair's recorded and discounted visits, predicted visits, and shares of the
origin's outflow.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import FACTORS, all_pairs, candidates, design, root  # noqa: E402  the shared gravity terms

od = pd.read_csv(root / "analysis/od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
od = od[(od.home_county != "OUT") & (od.home_county != od.dest_county)]
pairs = all_pairs()
stops = pd.read_csv(root / "analysis/road_stop_share.csv", dtype={"i": str, "j": str}).set_index(["i", "j"])
STOP_NORM = 0.125
pairs["stop_discount"] = [max(0.0, stops.road_stop_share[k] - STOP_NORM)
                          if k in stops.index and stops.visitors[k] >= 200 else 0.0 for k in zip(pairs.i, pairs.j)]


def visits(months, discounted=True):
    v = od[od.month.isin(months)].groupby(["home_county", "dest_county"]).visits.sum()
    y = pd.Series([v.get((i, j), 0) for i, j in zip(pairs.i, pairs.j)], index=pairs.index, dtype=float)
    return y * (1 - pairs.stop_discount) if discounted else y


def fit(months):
    y = visits(months)
    X = design(pairs)
    m = sm.GLM(y, X, family=sm.families.Poisson()).fit(cov_type="HC1", maxiter=200)
    return y, m


ALL = [f"2026-{m:02d}" for m in range(1, 10)]
y, m = fit(ALL)
pairs["visits_recorded"] = visits(ALL, discounted=False).values
pairs["visits"], pairs["predicted"] = y.values, m.predict(design(pairs)).values
for col in ("visits", "predicted"):
    pairs[col + "_share"] = pairs[col] / pairs.groupby("i")[col].transform("sum")
pairs["ratio"] = pairs.visits / pairs.predicted
r2 = np.corrcoef(pairs.visits, pairs.predicted)[0, 1] ** 2
r2_log = np.corrcoef(np.log1p(pairs.visits), np.log1p(pairs.predicted))[0, 1] ** 2
print(f"pass-through discount: {1 - y.sum() / pairs.visits_recorded.sum():.1%} of out-of-county visits removed")
print(f"Jan-Sep fit: {len(pairs):,} county pairs, {int(y.sum()):,} visits; "
      f"explains {r2:.0%} of visits, {r2_log:.0%} on a log scale")
coef = pd.DataFrame({"coef": m.params, "se": m.bse, "p": m.pvalues}).loc[[c for c in m.params.index if not c.startswith(("o_", "d_"))]]
print(coef.round(3).to_string())

# out of sample: fit Jan-Jun, score Jul-Sep
_, m6 = fit(ALL[:6])
y3 = visits(ALL[6:]).values
p3 = m6.predict(design(pairs)).values
share = lambda x: x / pd.Series(x).groupby(pairs.i.values).transform("sum").values
print(f"Jan-Jun model scored on Jul-Sep shares: explains {np.corrcoef(share(y3), share(p3))[0, 1] ** 2:.0%} "
      f"(log scale {np.corrcoef(np.log1p(y3), np.log1p(p3 * y3.sum() / p3.sum()))[0, 1] ** 2:.0%})")
pairs.to_csv(root / "analysis/od_predicted.csv", index=False)
