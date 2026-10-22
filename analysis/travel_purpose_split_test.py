"""Work and non-work travel modelled separately, then summed.

Advan counts each destination's visitors with work behaviour there (WORK_BEHAVIOR_DEVICE_HOME_AREAS); non-work
travel = all-day - work behaviour (od_mo_2026_purpose.csv, build_statewide_od_purpose.py). A single model on all
travel ties every trip to commuting once commuting is a term: Audrain -> Hannibal, shopping and services with almost
no commuting, was pushed from 1.83x to 2.40x of expectation.

  single      the adopted model (shared gravity terms incl. commuting) on all-day visits
  split       work model (all terms, incl. commuting) on work-behaviour visits + non-work model on non-work visits:
                non-work A  same terms incl. commuting
                non-work B  same terms WITHOUT commuting
              predicted all-day = work prediction + non-work prediction

Scored: July-September shares from a January-June fit (R^2, statewide), each county held out in 8 folds (share error
by tier), and the study counties' main destinations (actual / expected, all months).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import FACTORS, all_pairs, design, root, cov  # noqa: E402

od = pd.read_csv(root / "analysis/od_mo_2026_purpose.csv", dtype={"home_county": str, "dest_county": str})
od = od[od.home_county != od.dest_county]
od["nonwork"] = (od.all_day - od.work_behavior).clip(lower=0)
pairs = all_pairs()
X = design(pairs)
NOCOM = [c for c in X.columns if c not in ("commute_out", "commute_in")]
ALL = [f"2026-{m:02d}" for m in range(1, 10)]


def y(col, months):
    v = od[od.month.isin(months)].groupby(["home_county", "dest_county"])[col].sum()
    return np.array([v.get((i, j), 0) for i, j in zip(pairs.i, pairs.j)], float)


share = lambda x: x / pd.Series(x).groupby(pairs.i.values).transform("sum").values
fit = lambda yy, XX: sm.GLM(yy, XX, family=sm.families.Poisson()).fit(maxiter=300)


def predict(months, Xw, Xn, rows=None):
    """single, split A, split B predictions of all-day visits (counts on one scale per origin)."""
    tr = slice(None) if rows is None else rows
    yt, yw, yn = y("all_day", months), y("work_behavior", months), y("nonwork", months)
    out = {}
    m = fit(yt[tr], X.loc[tr] if rows is not None else X); out["single"] = m.predict(X)
    mw = fit(yw[tr], X.loc[tr] if rows is not None else X)
    mnA = fit(yn[tr], X.loc[tr] if rows is not None else X)
    mnB = fit(yn[tr], X.loc[tr, NOCOM] if rows is not None else X[NOCOM])
    out["split A (non-work with commuting)"] = mw.predict(X) + mnA.predict(X)
    out["split B (non-work without commuting)"] = mw.predict(X) + mnB.predict(X[NOCOM])
    return out, (mw, mnB)


# 1. out of time
p6, _ = predict(ALL[:6], X, X)
y3 = y("all_day", ALL[6:])
print("| Model | Jul-Sep shares R^2 (from Jan-Jun) |\n|---|---:|")
for k, p in p6.items():
    print(f"| {k} | {np.corrcoef(share(y3), share(np.asarray(p)))[0, 1] ** 2:.1%} |")
print(f"| persistence (Jan-Jun observed) | {np.corrcoef(share(y3), share(y('all_day', ALL[:6])))[0, 1] ** 2:.1%} |")

# 2. study-county pairs, all months
p9, (mw, mn) = predict(ALL, X, X)
y9 = y("all_day", ALL)
print("\nwork model commuting:", {k: round(mw.params[k], 3) for k in ("commute_out", "commute_in")})
idx = pd.MultiIndex.from_arrays([pairs.i, pairs.j])
for i, n in (("29151", "Osage"), ("29007", "Audrain"), ("29019", "Boone")):
    top = pd.Series(y9, index=idx).loc[i].sort_values(ascending=False).head(5).index
    row = []
    for j in top:
        k = list(zip(pairs.i, pairs.j)).index((i, j))
        row.append(f"{cov.name[j]} " + " / ".join(f"{y9[k] / np.asarray(p)[k] * np.asarray(p)[pairs.i.values == i].sum() / y9[pairs.i.values == i].sum():.2f}" for p in p9.values()))
    print(n, "(single / split A / split B):", "; ".join(row))
