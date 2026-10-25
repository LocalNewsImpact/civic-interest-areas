"""Does adding stores, jobs, borders and rural origins improve the SINGLY-constrained gravity model (origin fixed
effects only; destination draw from measured attributes)? The historical first steps toward the adopted model, last row.

Outcome: the adopted one (calibrated, pass-through discounted). Scored as travel_model.py (gravity_terms.HEAD):
leave-one-county-out (8 folds, seed 7) primary; Jan-Jun -> Jul-Sep stability check beside persistence; in-sample
deviance labelled as such; the added term's coefficient with errors clustered by home and destination county.
"""
import sys
import warnings
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import FACTORS, HEAD, MONTHS, all_pairs, candidates, evaluate, persistence, row, stop_discount, travel_visits  # noqa: E402

warnings.filterwarnings("ignore")
pairs = all_pairs()
DISC = stop_discount(pairs)
X_all = candidates(pairs)
origin = [c for c in X_all.columns if c.startswith("o_")]
dest = [c for c in X_all.columns if c.startswith("d_")]
y9, y6, y3 = (travel_visits(pairs, m, disc=DISC) for m in (MONTHS, MONTHS[:6], MONTHS[6:]))
steps = [
    ("plain gravity: population + distance", ["log_pop_j", "log_dist"]),
    ("+ shared border", ["log_pop_j", "log_dist", "adjacent"]),
    ("+ rural home county x distance", ["log_pop_j", "log_dist", "adjacent", "rural_i_x_log_dist"]),
    ("+ metro destination", ["log_pop_j", "log_dist", "adjacent", "rural_i_x_log_dist", "metro_j"]),
    ("+ stores per resident", ["log_pop_j", "log_dist", "adjacent", "rural_i_x_log_dist", "metro_j", "log_retail_pc_j"]),
    ("+ jobs per resident", ["log_pop_j", "log_dist", "adjacent", "rural_i_x_log_dist", "metro_j", "log_retail_pc_j", "log_jobs_pc_j"]),
    ("previous row without stores", ["log_pop_j", "log_dist", "adjacent", "rural_i_x_log_dist", "metro_j", "log_jobs_pc_j"]),
]
EV = {}
prev = []
for label, cols in steps:
    extra = [c for c in cols if c not in prev] if not label.startswith(("plain", "previous")) else []
    if label.startswith("previous"):
        extra = []
    EV[label] = evaluate(X_all[cols + origin], pairs, y9, y6, y3, extra=extra)
    prev = cols
    print("done:", label, flush=True)
ref = evaluate(X_all[FACTORS + origin + dest], pairs, y9, y6, y3)
print("\n" + HEAD)
for label, _ in steps:
    print(row(label, EV[label], ref))
print(row("ADOPTED: doubly constrained (gravity_terms.FACTORS)", ref, ref))
print(persistence(pairs, y6, y3))
