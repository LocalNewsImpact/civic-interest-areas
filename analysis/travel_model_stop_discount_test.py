"""Discount pass-through stops instead of modelling routes.

The Neighborhood Patterns county counts cannot separate a gas stop from any other stop. The store-level data can
(road_stop_share.csv, build_road_stop_share.py; pairs with 200+ store-level visitors): adjusted visits_ij = visits_ij x
(1 - discount_ij) under each definition --
  discount_old                2026-10-16: gas, fast food (old codes) share above the statewide 12.5%
  discount_codes              codes fixed (+ convenience stores 445120), above the statewide share
  discount_highway_statewide  road stops within 1 km of an Interstate or US highway, above the statewide share
  discount_unshrunk           highway stops above the share expected from the destination's own residents' store mix
  discount (ADOPTED)          the same, shrunk toward zero by empirical Bayes for the pair's store-level sample Same adopted model (gravity_terms.design), refitted. Each row is scored
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
raw = travel_visits(pairs, MONTHS, discounted=False)
VARIANTS = [("undiscounted", np.zeros(len(pairs)))] + [(c, stop_discount(pairs, c)) for c in
                                                      ("discount_old", "discount_codes", "discount_highway_statewide", "discount_unshrunk")] + [
    ("discount (adopted)", stop_discount(pairs))]
for label, adj in VARIANTS[1:]:
    print(f"{label}: pairs discounted {np.sum(adj > 0):,}; visits removed {np.sum(raw * adj) / raw.sum():.2%} of out-of-county visits")
EV, out = {}, []
for label, adj in VARIANTS:
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
