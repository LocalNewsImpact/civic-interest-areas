"""Discount pass-through stops instead of modelling routes.

The Neighborhood Patterns county counts cannot separate a gas stop from any other stop. The store-level data can: for
each county pair, road_stop_share.csv gives the share of March visits at gas stations, convenience stores and fast
food. Buying gas where you shop is normal, so only the EXCESS over the statewide out-of-county share (12.5%) is treated
as pass-through:  adjusted visits_ij = visits_ij x (1 - max(0, road_stop_share_ij - 0.125)), for pairs with 200+
store-level visitors (others unadjusted). Same adopted model (gravity_terms.design), refitted. Each row is scored
against its own outcome, as travel_model.py scores (gravity_terms.HEAD; no change column: the outcomes differ).
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import HEAD, MONTHS, all_pairs, cov, design, evaluate, persistence, row, shares, stop_discount, travel_visits  # noqa: E402

warnings.filterwarnings("ignore")
pairs = all_pairs()
X = design(pairs)
excess = stop_discount(pairs)
raw = travel_visits(pairs, MONTHS, discounted=False)
print(f"pairs discounted: {np.sum(excess > 0):,}; visits removed: {np.sum(raw * excess) / raw.sum():.1%} of out-of-county visits")
EV, out = {}, []
for label, adj in (("as recorded (calibrated)", np.zeros(len(pairs))), ("excess highway stops discounted (adopted)", excess)):
    y9, y6, y3 = (travel_visits(pairs, m, disc=adj) for m in (MONTHS, MONTHS[:6], MONTHS[6:]))
    EV[label] = evaluate(X, pairs, y9, y6, y3)
    out.append(persistence(pairs, y6, y3))
    r = y9 / EV[label]["m"].predict(X).values
    pr = pairs.assign(ratio=r, v=y9, ex=adj)
    for f, n in (("29007", "Audrain"), ("29151", "Osage"), ("29019", "Boone")):
        x = pr[pr.i == f].sort_values("v", ascending=False).head(4)
        out.append(f"    {label}, {n} (in-sample actual / predicted, discount): "
                   + ", ".join(f"{cov.name[j]} {rt:.2f}x (-{e:.0%})" for j, rt, e in zip(x.j, x.ratio, x.ex)))
print("\n" + HEAD)
for label in EV:
    print(row(label, EV[label]))
print("\n".join(out))
