"""Does adding stores, jobs, borders and rural origins improve the gravity model?  Each version is fitted on all nine
months (in-sample fit) and on Jan-Jun only, then scored on Jul-Sep (out-of-sample: months the model has not seen).
Same data and method as travel_model.py (PPML, origin fixed effects)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import all_pairs, candidates, root  # noqa: E402

od = pd.read_csv(root / "analysis/od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
od = od[(od.home_county != "OUT") & (od.home_county != od.dest_county)]
pairs = all_pairs()
X_all = candidates(pairs)
origin = [c for c in X_all.columns if c.startswith("o_")]
ALL = [f"2026-{m:02d}" for m in range(1, 10)]


def y_for(months):
    v = od[od.month.isin(months)].groupby(["home_county", "dest_county"]).visits.sum()
    return np.array([v.get((i, j), 0) for i, j in zip(pairs.i, pairs.j)], float)


y9, y6, y3 = y_for(ALL), y_for(ALL[:6]), y_for(ALL[6:])
share = lambda x: x / pd.Series(x).groupby(pairs.i.values).transform("sum").values
steps = [
    ("plain gravity: population + distance", ["log_pop_j", "log_dist"]),
    ("+ shared border", ["log_pop_j", "log_dist", "adjacent"]),
    ("+ rural home county x distance", ["log_pop_j", "log_dist", "adjacent", "nonmetro_i_x_log_dist"]),
    ("+ metro destination", ["log_pop_j", "log_dist", "adjacent", "nonmetro_i_x_log_dist", "metro_j"]),
    ("+ stores per resident", ["log_pop_j", "log_dist", "adjacent", "nonmetro_i_x_log_dist", "metro_j", "log_retail_pc_j"]),
    ("+ jobs per resident (full model)", ["log_pop_j", "log_dist", "adjacent", "nonmetro_i_x_log_dist", "metro_j", "log_retail_pc_j", "log_jobs_pc_j"]),
    ("full model without stores", ["log_pop_j", "log_dist", "adjacent", "nonmetro_i_x_log_dist", "metro_j", "log_jobs_pc_j"]),
]
print("| Version | Accounts for (9 months) | Log scale | Predicts Jul-Sep from Jan-Jun | Deviance | Added factor's estimate (p) |")
print("|---|---:|---:|---:|---:|---|")
for label, cols in steps:
    X = X_all[cols + origin]
    m9 = sm.GLM(y9, X, family=sm.families.Poisson()).fit(cov_type="HC1", maxiter=200)
    m6 = sm.GLM(y6, X, family=sm.families.Poisson()).fit(maxiter=200)
    p9, p3 = m9.predict(X), m6.predict(X)
    r2 = np.corrcoef(y9, p9)[0, 1] ** 2
    r2l = np.corrcoef(np.log1p(y9), np.log1p(p9))[0, 1] ** 2
    oos = np.corrcoef(share(y3), share(p3))[0, 1] ** 2
    last = cols[-1]
    est = f"{m9.params[last]:+.2f} ({m9.pvalues[last]:.3f})" if not label.startswith("plain") else ""
    print(f"| {label} | {r2:.1%} | {r2l:.1%} | {oos:.1%} | {m9.deviance / 1e6:,.1f}M | {est} |")
