"""Outlets required: for a resident of a civic interest area, how many news outlets must they follow for news to reach
across their area? For k = 1..K, the largest share of the area's hexagons (the footprint, every hexagon the same) that
the best k outlets together bring to regular coverage (2+ stories a month) and to frequent coverage (9+), and which
outlets those are -- the exact best set, every combination of the candidate outlets checked (candidates: outlets
reaching the tier in at least one hexagon of the area alone or that hold 1%+ of the area's coverage weight).
Coverage per outlet and hexagon from area_coverage_alignment.py (coverage density: scope areas, central 1, mention 0.5,
Sports half, towns by the square root of size, counties and regions counted once by population; statewide stories out).
Writes analysis/outlets_required.csv."""
import itertools
import json
import os
import runpy
import sys
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
os.environ["COV_LIB"] = "1"
sys.argv = ["area_coverage_alignment.py"]
A = runpy.run_path(str(root / "analysis/area_coverage_alignment.py"), run_name="cov_lib")
cov, layer = A["cov"]["all"], A["layer"]
K, TIERS = 5, {"regular": 2.0, "frequent": 9.0}
rows = []
for town, rank in A["AREAS"]:
    area = list(layer[town][rank]["all"])
    outlets = [o for o in cov if any(cov[o].get(k, 0) for k in area)]
    M = np.array([[cov[o].get(k, 0.0) for k in area] for o in outlets])          # outlets x hexagons
    tot = M.sum(0)
    for tier, floor in TIERS.items():
        reach_all = float((tot >= floor).mean())
        cand = [i for i in range(len(outlets)) if (M[i] >= floor).any() or M[i].sum() >= 0.01 * M.sum()]
        cand = sorted(cand, key=lambda i: -M[i].sum())[:24]                      # exact search over the 24 largest
        for k in range(1, K + 1):
            best, best_set = -1.0, ()
            for combo in itertools.combinations(cand, k):
                share = float((M[list(combo)].sum(0) >= floor).mean())
                if share > best:
                    best, best_set = share, combo
            rows.append({"area": f"{town} {'I' * rank}", "tier": tier, "outlets_followed": k, "share_reached": round(best, 3),
                         "all_outlets_reach": round(reach_all, 3), "outlets": "; ".join(outlets[i] for i in best_set)})
            print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(root / "analysis/outlets_required.csv", index=False)
