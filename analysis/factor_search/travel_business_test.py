"""Business activity as the non-work pull, from public data: does a destination's business relative to the origin's
predict travel beyond distance, borders and commuting?

County Business Patterns 2022 establishments (analysis/cbp_2022_mo_sectors.csv): retail (NAICS 44-45), general
merchandise (452), health care (62), hospitals (622), food and lodging (72), arts and recreation (71). Each enters as
log((destination + 1) / (origin + 1)). FINDING (2026-10-24): the gap is log(destination + 1) - log(origin + 1), a
destination term minus an origin term, so with both sets of fixed effects it is exactly collinear (absorbed): the
design is rank-deficient, every score is unchanged and the coefficients are not identified. The test cannot inform
the adopted model; it is kept to show that. Added to the adopted model (gravity_terms.FACTORS). Outcome: the
adopted one (calibrated, pass-through discounted). Scored: each county held out in 8 folds, seed 7 (primary; share
error by tier with 95% bootstrap intervals over home counties, change vs adopted); Jul-Sep from Jan-Jun (stability
check; R^2 = 1 - SSE/SST, persistence beside it); in-sample actual / expected for two study pairs; gap coefficients
with errors clustered by home and destination county.
"""
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gravity_terms import (MONTHS, all_pairs, boot, county_stats, design, fit_twoway, loco, persistence,  # noqa: E402
                           poisson_fit, root, shares, stop_discount, summary, travel_visits)

warnings.filterwarnings("ignore")
pairs = all_pairs()
DISC = stop_discount(pairs)
X = design(pairs)
biz = pd.read_csv(root / "analysis/cbp_2022_mo_sectors.csv", dtype={"fips": str}).set_index("fips")
SECT = ["retail", "general_merch", "health", "hospitals", "food_lodging", "arts_rec"]
for s_ in SECT:
    X[f"gap_{s_}"] = [math.log((biz[s_].get(j, 0) + 1) / (biz[s_].get(i, 0) + 1)) for i, j in zip(pairs.i, pairs.j)]
y9, y6, y3 = (travel_visits(pairs, m, disc=DISC) for m in (MONTHS, MONTHS[:6], MONTHS[6:]))
o = pairs.i.values
share = lambda x: shares(x, o)
basecols = [c for c in X.columns if not c.startswith("gap_")]
models = {"adopted": basecols,
          "+ retail gap": basecols + ["gap_retail"],
          "+ general merchandise gap": basecols + ["gap_general_merch"],
          "+ health care gap": basecols + ["gap_health"],
          "+ all six business gaps": basecols + [f"gap_{s_}" for s_ in SECT]}
unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(root / "analysis/county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
names = {"class 1": "small rural", "class 2": "indep. towns", "class 3": "commuter", "class 4": "hubs"}
a = share(y9)
idx = {(i, j): k for k, (i, j) in enumerate(zip(pairs.i, pairs.j))}
S, out = {}, []
for label, cols in list(models.items()):
    XX = X[cols]
    if np.linalg.matrix_rank(XX.values) < XX.shape[1]:          # the gap is absorbed by the two sets of fixed effects
        print(f"{label}: design rank {np.linalg.matrix_rank(XX.values)} of {XX.shape[1]} columns -- not identified, not fitted")
        del models[label]
        continue
    S[label] = county_stats(a, loco(y9, XX, o), o, y9)
    r2 = summary(county_stats(share(y3), share(poisson_fit(y6, XX).predict(XX).values), o, y3))["r2"]
    p9 = fit_twoway(y9, XX, pairs).predict(XX).values
    rat = lambda i, j: y9[idx[(i, j)]] / p9[idx[(i, j)]]
    out.append((label, r2, rat("29007", "29127"), rat("29151", "29019")))
    print("done:", label, flush=True)
ref = S["adopted"]
ct = pd.Series({f: tier.get(unit(f), "class 1") for f in ref.index})
print("\nLOCO weighted share error by tier [95%]; change vs adopted [95%]")
print("| Model | Jul-Sep R^2 (stability) | " + " | ".join(names.values()) + " | Audrain->Marion (in-sample) | Osage->Boone (in-sample) |")
print("|---|---:|" + "---|" * 4 + "---:|---:|")
for label, r2, am, ob in out:
    s_, cells = S[label], []
    for c in names:
        mk = (ct == c).values
        lo, hi = boot(s_, "werr", mask=mk)
        cell = f"{s_[mk].werr.mean():.2f} [{lo:.2f}, {hi:.2f}]"
        if s_ is not ref:
            dl, dh = boot(s_, "werr", ref=ref, mask=mk)
            cell += f"; {s_[mk].werr.mean() - ref[mk].werr.mean():+.2f} [{dl:+.2f}, {dh:+.2f}]"
        cells.append(cell)
    print(f"| {label} | {r2:.1%} | " + " | ".join(cells) + f" | {am:.2f} | {ob:.2f} |")
print(persistence(pairs, y6, y3))
XX = X[basecols + [f"gap_{s_}" for s_ in SECT]].values
print(f"design rank with all six gaps: {np.linalg.matrix_rank(XX)} of {XX.shape[1]} columns "
      f"(adopted alone: {np.linalg.matrix_rank(X[basecols].values)} of {len(basecols)}): the gaps are absorbed")
