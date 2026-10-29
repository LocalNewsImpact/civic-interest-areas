"""Competing destinations: does a destination draw more when the origin has no comparable alternative in another direction?

The adopted travel model (gravity_terms.FACTORS, doubly constrained) measures each destination's overall draw and each
origin's overall outflow as fixed effects. What it does not see is the CHOICE SET from a given home: Jefferson City
pulls Osage residents harder if the next comparable centre is far away in every other direction. Terms tested, each
added to the adopted model:

  alt_ratio      log(distance from home to the nearest comparable alternative / distance to this destination);
                 comparable = a destination with at least as many places (Advan places that week, a draw measure) as this
                 one, other than home and this destination. Large when this destination has no near rival.
  alt_ratio_dir  the same, alternatives counted only in OTHER DIRECTIONS (bearing from home 60+ degrees away from this
                 destination's)
  fotheringham   log C_ij, C_ij = sum over k != i, j of places_k / miles(j, k) (Haynes & Fotheringham 1985, the
                 competing-destinations term: a centre ringed by others competes with them)

Outcome: the adopted one (calibrated, pass-through discounted). Scored as travel_model.py (gravity_terms.HEAD):
leave-one-county-out primary (big pairs = forecast at 5%+, held out); Jan-Jun -> Jul-Sep stability check beside
persistence; added terms with errors clustered by home and destination county.
"""
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
src = open(Path(__file__).resolve().parents[1] / "travel_model_dc_test.py").read().split("models = [")[0]
exec(src)                                          # pairs, X0, O, Dd, y9, y6, y3, share, cov, miles, Xof
warnings.filterwarnings("ignore")

cp = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO29.txt", dtype=str, encoding="utf-8-sig")
cen = {r.STATEFP + r.COUNTYFP: (float(r.LATITUDE), float(r.LONGITUDE)) for r in cp.itertuples()}
size = cov.places.astype(float).to_dict()


def bearing(a, b):
    (y1, x1), (y2, x2) = cen[a], cen[b]
    return math.atan2(y2 - y1, (x2 - x1) * math.cos(math.radians((y1 + y2) / 2)))


alt, alt_dir, acc = [], [], []
fips = [f for f in FIPS if f in cen and f in size]
for i, j in zip(pairs.i, pairs.j):
    dij = max(miles(i, j), 1.0)
    rivals = [k for k in fips if k not in (i, j) and size[k] >= size.get(j, 0)]
    dk = min((miles(i, k) for k in rivals), default=400.0)
    bj = bearing(i, j)
    rivals_dir = [k for k in rivals if abs((bearing(i, k) - bj + math.pi) % (2 * math.pi) - math.pi) >= math.radians(60)]
    dkd = min((miles(i, k) for k in rivals_dir), default=400.0)
    alt.append(math.log(max(dk, 1.0) / dij))
    alt_dir.append(math.log(max(dkd, 1.0) / dij))
    # C_ij excludes the ORIGIN as well, which is what makes it vary by pair and not only by destination
    acc.append(math.log(sum(size[k] / max(miles(j, k), 1.0) for k in fips if k not in (i, j))))
X0["alt_ratio"], X0["alt_ratio_dir"], X0["fotheringham"] = alt, alt_dir, acc

tests = (("adopted", []), ("+ nearest comparable alternative", ["alt_ratio"]),
         ("+ nearest comparable alternative in another direction", ["alt_ratio_dir"]),
         ("+ Fotheringham competing destinations (k != i, j)", ["fotheringham"]))
EV, ph = {}, {}
for label, extra in tests:
    EV[label] = evaluate(Xof(FACTORS + extra), pairs, y9, y6, y3, extra=extra)
    print("done:", label, flush=True)
print("\n" + HEAD)
for label, _ in tests:
    print(row(label, EV[label], EV["adopted"]))
print(persistence(pairs, y6, y3))
from gravity_terms import loco  # noqa: E402
a = share(y9)
for label, extra in (tests[0], tests[3]):
    X = Xof(FACTORS + extra)
    ps, hold = share(EV[label]["m"].predict(X).values), loco(y9, X, pairs.i.values)
    print(f"\n{label}: main destinations, actual / expected share (in-sample, held out)")
    for f, n in (("29151", "Osage"), ("29007", "Audrain"), ("29019", "Boone")):
        k = np.flatnonzero(pairs.i.values == f)
        k = k[np.argsort(-a[k])][:4]
        print(" ", n, [(cov.name[pairs.j[x]], f"{a[x] / ps[x]:.2f}", f"{a[x] / hold[x]:.2f}") for x in k])
