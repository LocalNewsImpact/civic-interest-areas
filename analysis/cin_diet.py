"""The balanced diet of civic information in each
civic interest area (the hexagons the maps draw; authors, 2026-10-20, area 2026-10-26): the ten CIN categories of the
codebook (the eight critical information needs of Friedland et al. 2012, plus Civic Life and Sports); a hexagon has a
balanced diet when ANY 8 of the 10 reach the floor of 1 story a month each, by coverage density (scope areas, central 1,
mention 0.5, Sports half, towns by the square root of size, counties and regions counted once by population; statewide
stories out). March 2026.

Per area: the share of the footprint with a balanced diet, the mean number of categories met, how often each category
is met; and the outlets required -- for k = 1..5, the best k outlets (every combination of the 24 outlets with the most
coverage in the area checked) and the share of the footprint they bring to a balanced diet, against all outlets.
Writes analysis/cin_diet.csv and analysis/cin_diet_outlets.csv; flows/reach/diet_<region>.json for the map. Env REGION (default columbia)."""
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
COVCAT, layer = A["COVCAT"], A["layer"]
CATS = ["Emergencies and Public Safety", "Civic information", "Political life", "Education", "Environment and Planning",
        "Health", "Transportation Systems", "Economic Development", "Civic Life", "Sports"]
FLOOR, NEED, K = 1.0, 8, int(os.environ.get("DIET_K", 5))   # DIET_K=0: map data only, no outlet search
rows, orows, mapdata = [], [], {}
for town, rank in A["AREAS"]:
    area = list(layer[town][rank]["all"])
    outlets = sorted({o for c in CATS for o in COVCAT[c] if any(COVCAT[c][o].get(k, 0) for k in area)})
    T = np.array([[[COVCAT[c][o].get(k, 0.0) for k in area] for c in CATS] for o in outlets])   # outlets x cats x hexes
    full = T.sum(0)                                                                              # cats x hexes
    met = (full >= FLOOR)
    n_met = met.sum(0)
    diet = n_met >= NEED
    label = f"{town} {'I' * rank}"
    rows.append({"area": label, "hexagons": len(area), "balanced_diet": round(float(diet.mean()), 3),
                 "mean_categories_met": round(float(n_met.mean()), 2),
                 **{f"met: {c}": round(float(met[i].mean()), 3) for i, c in enumerate(CATS)}})
    print(rows[-1], flush=True)
    cand = sorted(range(len(outlets)), key=lambda i: -T[i].sum())[:24]
    for k in range(1, K + 1):
        best, best_set = -1.0, ()
        for combo in itertools.combinations(cand, k):
            share = float(((T[list(combo)].sum(0) >= FLOOR).sum(0) >= NEED).mean())
            if share > best:
                best, best_set = share, combo
        orows.append({"area": label, "outlets_followed": k, "balanced_diet_share": round(best, 3),
                      "all_outlets": round(float(diet.mean()), 3), "outlets": "; ".join(outlets[i] for i in best_set)})
        print(orows[-1], flush=True)
    mapdata.setdefault(town, {})[rank] = {k: int(n_met[j]) for j, k in enumerate(area)}
    # the map's display hexagons (area_coverage_alignment.py "display": the area map's 10%+ hexagons) carry their breadth
    # too, so a hexagon is drawn at the same size on every map; the shares above stay on the measured area
    show = [k for k in layer[town][rank].get("display", {}) if k not in mapdata[town][rank]]
    for k in show:
        mapdata[town][rank][k] = int(sum(sum(COVCAT[c][o].get(k, 0.0) for o in COVCAT[c]) >= FLOOR for c in CATS))
pd.DataFrame(rows).to_csv(root / f"analysis/cin_diet{A['SUFFIX']}.csv", index=False)
pd.DataFrame(orows).to_csv(root / f"analysis/cin_diet_outlets{A['SUFFIX']}.csv", index=False)
json.dump(mapdata, open(root / f"flows/reach/diet_{A['REGION']}.json", "w"))
