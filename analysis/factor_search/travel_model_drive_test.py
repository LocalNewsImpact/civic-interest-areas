"""Driving time and the "on the way" factor.

1. Replace straight-line distance with driving time (drive_od.csv: fastest route between 2020 population centres on
   OpenStreetMap roads) in every distance term of the adopted doubly-constrained model (centred at 30 minutes).
2. Add an "on the way" factor -- county j lies on the driving route from home county i to somewhere bigger:
     on_way_centre   j is on the route from i to a metro or micropolitan central county k (OMB 2023) larger than j
                     and within 90 minutes of i
     on_way_weight   log(1 + sum over destinations k whose route from i passes through j of population_k /
                     minutes_ik^2 / 1000) -- every route, weighted by how big and near its destination is
Outcome: the adopted one (calibrated, pass-through discounted). Scored as travel_model.py (gravity_terms.HEAD):
leave-one-county-out primary; Jan-Jun -> Jul-Sep stability check beside persistence; added terms with errors clustered
by home and destination county. Check against the store data (IN-SAMPLE, Jan-Sep fit): the correlation, across county
pairs with 200+ visitors, between log(actual / predicted) and the pair's share of visits at highway stops
(road_stop_share.csv); positive = pass-through the model is missing.
"""
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gravity_terms import (FACTORS, FIPS, HEAD, MONTHS, all_pairs, candidates, cov, distance_terms, evaluate,  # noqa: E402
                           persistence, root, row, stop_discount, travel_visits)

warnings.filterwarnings("ignore")
drive = pd.read_csv(root / "analysis/drive_od.csv", dtype={"i": str, "j": str}).set_index(["i", "j"])
drive["through"] = drive.through.fillna("").map(lambda s: set(s.split(";")) if s else set())
stops = pd.read_csv(root / "analysis/road_stop_share.csv", dtype={"i": str, "j": str}).set_index(["i", "j"])
d = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str)
d = d[d["FIPS State Code"] == "29"]
central = {"29" + r[11] for r in d.itertuples() if r[12] == "Central"}
pairs = all_pairs()
DISC = stop_discount(pairs)
key = list(zip(pairs.i, pairs.j))
minutes = np.array([drive.drive_minutes[k] for k in key])
pop = cov.population

on_centre, on_weight = [], []
for i, j in key:
    big = [k for k in central if k not in (i, j) and pop[k] > pop[j] and drive.drive_minutes[(i, k)] <= 90]
    on_centre.append(int(any(j in drive.through[(i, k)] for k in big)))
    on_weight.append(np.log1p(sum(pop[k] / drive.drive_minutes[(i, k)] ** 2 / 1000
                                  for k in FIPS if k not in (i, j) and j in drive.through[(i, k)])))

base = candidates(pairs)
FE = [c for c in base.columns if c.startswith(("o_", "d_"))]
straight = base[FACTORS]
driving = pd.concat([distance_terms(np.log(minutes), pairs.i.values, ref=math.log(30)).set_index(pairs.index),
                     base[["adjacent", "commute_out", "commute_in"]]], axis=1)
y9, y6, y3 = (travel_visits(pairs, m, disc=DISC) for m in (MONTHS, MONTHS[:6], MONTHS[6:]))
st = np.array([stops.road_stop_share.get(k, np.nan) for k in key])
stn = np.array([stops.visitors.get(k, 0) for k in key])
chk = (stn >= 200) & ~np.isnan(st)
print(f"on the way to a bigger centre: {sum(on_centre):,} of {len(key):,} pairs")
models = [("straight-line distance (adopted)", straight, []), ("driving time", driving, []),
          ("driving time + on the way to a bigger centre", driving.assign(on_way_centre=on_centre), ["on_way_centre"]),
          ("driving time + on the way, weighted", driving.assign(on_way_weight=on_weight), ["on_way_weight"])]
EV, corr = {}, {}
for label, X, extra in models:
    Xm = pd.concat([X, base[FE]], axis=1)
    EV[label] = evaluate(Xm, pairs, y9, y6, y3, extra=extra)
    r = y9 / EV[label]["m"].predict(Xm).values
    corr[label] = np.corrcoef(np.log(r[chk] + 1e-9), st[chk])[0, 1]
    print("done:", label, flush=True)
print("\n" + HEAD)
for label, *_ in models:
    print(row(label, EV[label], EV[models[0][0]]))
print(persistence(pairs, y6, y3))
print("\nin-sample log(actual / predicted) vs highway-stop share, correlation:", {k: round(v, 3) for k, v in corr.items()})
