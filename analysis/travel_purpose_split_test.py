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

Outcome: the adopted one -- each count calibrated to population (calibration_county_month.csv, as od_mo_2026.csv) and
pass-through discounted (gravity_terms.stop_discount), work and non-work alike. Scored: each county held out in 8 folds,
seed 7 (primary; share error by tier with 95% bootstrap intervals over home counties, change vs single; a split model's
held-out shares combine the work and non-work forecasts in the held-out county's observed work / non-work proportion);
July-September shares from a January-June fit (stability check, R^2 = 1 - SSE/SST, persistence beside it); the study
counties' main destinations (in-sample actual / expected, all months).
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import (MONTHS, all_pairs, boot, calibration_factor, county_stats, cov, design, loco,  # noqa: E402
                           poisson_fit, r2_oos, root, shares, stop_discount)

warnings.filterwarnings("ignore")
od = pd.read_csv(root / "analysis/od_mo_2026_purpose.csv", dtype={"home_county": str, "dest_county": str})
od = od[od.home_county != od.dest_county]
k = calibration_factor(od.home_county, od.month)
od["all_day"], od["work_behavior"] = od.all_day / k, od.work_behavior / k
od["nonwork"] = (od.all_day - od.work_behavior).clip(lower=0)
pairs = all_pairs()
DISC = stop_discount(pairs)
X = design(pairs)
NOCOM = [c for c in X.columns if c not in ("commute_out", "commute_in")]
ALL = MONTHS
o = pairs.i.values


def y(col, months):
    v = od[od.month.isin(months)].groupby(["home_county", "dest_county"])[col].sum()
    return np.array([v.get((i, j), 0) for i, j in zip(pairs.i, pairs.j)], float) * (1 - DISC)


share = lambda x: shares(x, o)
fit = poisson_fit


def predict(months):
    """single, split A, split B predictions of all-day visits (counts on one scale per origin)."""
    yt, yw, yn = y("all_day", months), y("work_behavior", months), y("nonwork", months)
    mw, mnA, mnB = fit(yw, X), fit(yn, X), fit(yn, X[NOCOM])
    return {"single": fit(yt, X).predict(X).values,
            "split A (non-work with commuting)": mw.predict(X).values + mnA.predict(X).values,
            "split B (non-work without commuting)": mw.predict(X).values + mnB.predict(X[NOCOM]).values}, mw


# 1. each county held out
y9, yw9, yn9 = y("all_day", ALL), y("work_behavior", ALL), y("nonwork", ALL)
a = share(y9)
W = pd.Series(yw9).groupby(o).transform("sum").values
N = pd.Series(yn9).groupby(o).transform("sum").values
sw, snA, snB = loco(yw9, X, o), loco(yn9, X, o), loco(yn9, X[NOCOM], o)
S = {"single": county_stats(a, loco(y9, X, o), o, y9),
     "split A (non-work with commuting)": county_stats(a, (W * sw + N * snA) / (W + N), o, y9),
     "split B (non-work without commuting)": county_stats(a, (W * sw + N * snB) / (W + N), o, y9)}
unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(root / "analysis/county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
names = {"class 1": "small rural", "class 2": "indep. towns", "class 3": "commuter", "class 4": "hubs"}
ref = S["single"]
ct = pd.Series({f: tier.get(unit(f), "class 1") for f in ref.index})
print("| Model | LOCO weighted share error, all [95%] | " + " | ".join(names.values()) + " |\n|---|---|" + "---|" * 4)
for label, s_ in S.items():
    cells = []
    for c in ["all"] + list(names):
        mk = np.ones(len(ct), bool) if c == "all" else (ct == c).values
        lo, hi = boot(s_, "werr", mask=mk)
        cell = f"{s_[mk].werr.mean():.2f} [{lo:.2f}, {hi:.2f}]"
        if s_ is not ref:
            dl, dh = boot(s_, "werr", ref=ref, mask=mk)
            cell += f"; {s_[mk].werr.mean() - ref[mk].werr.mean():+.2f} [{dl:+.2f}, {dh:+.2f}]"
        cells.append(cell)
    print(f"| {label} | " + " | ".join(cells) + " |")

# 2. stability across months
p6, _ = predict(ALL[:6])
y3 = y("all_day", ALL[6:])
print("\n| Forecast | Jul-Sep shares R^2 (1 - SSE/SST), stability check |\n|---|---:|")
for k_, p in p6.items():
    print(f"| {k_} | {r2_oos(share(y3), share(p)):.1%} |")
print(f"| persistence (Jan-Jun observed) | {r2_oos(share(y3), share(y('all_day', ALL[:6]))):.1%} |")

# 3. study-county pairs, all months
p9, mw = predict(ALL)
print("\nwork model commuting:", {k_: round(mw.params[k_], 3) for k_ in ("commute_out", "commute_in")})
idx = pd.MultiIndex.from_arrays([pairs.i, pairs.j])
pos = {kk: n for n, kk in enumerate(zip(pairs.i, pairs.j))}
for i, n in (("29151", "Osage"), ("29007", "Audrain"), ("29019", "Boone")):
    top = pd.Series(y9, index=idx).loc[i].sort_values(ascending=False).head(5).index
    row = []
    for j in top:
        kk = pos[(i, j)]
        row.append(f"{cov.name[j]} " + " / ".join(f"{y9[kk] / p[kk] * p[o == i].sum() / y9[o == i].sum():.2f}" for p in p9.values()))
    print(n, "(single / split A / split B, in-sample):", "; ".join(row))
