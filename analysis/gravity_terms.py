"""The gravity terms shared by the travel model and the coverage model, so both are one model with the same terms.

DOUBLY CONSTRAINED: a fixed effect for every home county (o_*) holds its total, and a fixed effect for every destination
(d_*) measures its overall draw -- a state capital, a university, hospitals, shopping -- from the data itself. What the
pair terms explain is how distance and borders distribute that travel or those stories. For i -> j:
  log_dist                   log miles between 2020 population centres (CenPop2020)
  log_dist_sq                its square: travel falls off more steeply at short range
  nonmetro_i_x_log_dist(_sq) the same two when the home county is nonmetropolitan (USDA RUCC 4-9), else 0
  log_pop_i_x_log_dist       larger home counties travel farther (log population, ACS 2020-2024)
  adjacent                   1 if the counties share a border
  commute_out                log(1 + 1000 x workers living in i who work in j / all workers living in i)  (LODES 2023)
  commute_in                 log(1 + 1000 x workers living in j who work in i / all workers living in j)  (LODES 2023)
                             ADOPTED 2026-10-18 (travel_commute_pair_test.py): each county held out, small rural
                             counties' share error 3.76 -> 3.28, every tier better; commuting ties carry shopping,
                             services and visits with them
Chosen by travel_model_dc_test.py on months the model was not fitted on: doubly constrained with these terms cut
lack of fit 62% from the singly-constrained model (population, stores, distance, border, rural home) and predicts
Jul-Sep shares at 93%. Destination size, stores and jobs are absorbed by the destination effects; candidates() keeps
every term tested so the comparisons can be re-run.
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import shape

root = Path(__file__).resolve().parents[1]
cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str}).set_index("fips")
FIPS = list(cov.index)
FACTORS = ["log_dist", "log_dist_sq", "nonmetro_i_x_log_dist", "nonmetro_i_x_log_dist_sq", "log_pop_i_x_log_dist",
           "adjacent", "commute_out", "commute_in"]


def _lodes():
    """LODES 2023 Missouri main OD: workers by home county -> work county, and workers by home county."""
    import csv
    import gzip
    from collections import defaultdict
    flow, work = defaultdict(float), defaultdict(float)
    with gzip.open(root / "free/od_2023.csv.gz", "rt") as fh:
        for r in csv.DictReader(fh):
            h, w, n = r["h_geocode"][:5], r["w_geocode"][:5], float(r["S000"])
            work[h] += n
            flow[(h, w)] += n
    return flow, work


_FLOW, _WORK = _lodes()

_geo = json.load(open(root / "flows/cousub_29.geojson"))
_shp = {f["id"]: shape(f["geometry"]).buffer(0.002) for f in _geo["counties"]["features"]}   # ~200 m: closes slivers
_adj = {(a, b) for a in FIPS for b in FIPS if a < b and _shp[a].intersects(_shp[b])}


def miles(a, b):
    p1, p2 = math.radians(cov.lat[a]), math.radians(cov.lat[b])
    dl = math.radians(cov.lon[b] - cov.lon[a])
    return 3959 * math.acos(min(1, math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)))


def all_pairs():
    p = pd.DataFrame([(i, j) for i in FIPS for j in FIPS if i != j], columns=["i", "j"])
    p["dist"] = [miles(i, j) for i, j in zip(p.i, p.j)]
    p["adjacent"] = [int((min(i, j), max(i, j)) in _adj) for i, j in zip(p.i, p.j)]
    return p


def candidates(p):
    """Every factor tested, plus the home-county fixed effects."""
    X = pd.DataFrame(index=p.index)
    pop_j = cov.population.reindex(p.j).values
    X["log_pop_j"] = np.log(pop_j)
    X["log_jobs_pc_j"] = np.log(cov.jobs.reindex(p.j).values / pop_j)
    X["log_retail_pc_j"] = np.log((cov.retail.reindex(p.j).values + 1) / pop_j)
    X["metro_j"] = cov.metro.reindex(p.j).values
    X["log_dist"] = np.log(p.dist.values)
    X["nonmetro_i_x_log_dist"] = (1 - cov.metro.reindex(p.i).values) * X["log_dist"]
    X["adjacent"] = p.adjacent.values
    X["log_dist_sq"] = X["log_dist"] ** 2
    X["nonmetro_i_x_log_dist_sq"] = X["nonmetro_i_x_log_dist"] * X["log_dist"]
    X["log_pop_i_x_log_dist"] = np.log(cov.population.reindex(p.i).values) * X["log_dist"]
    X["commute_out"] = [math.log1p(1000 * _FLOW.get((i, j), 0) / max(_WORK.get(i, 0), 1)) for i, j in zip(p.i, p.j)]
    X["commute_in"] = [math.log1p(1000 * _FLOW.get((j, i), 0) / max(_WORK.get(j, 0), 1)) for i, j in zip(p.i, p.j)]
    origin = pd.get_dummies(p.i, prefix="o", drop_first=False).astype(float)
    origin.index = p.index
    dest = pd.get_dummies(p.j, prefix="d", drop_first=True).astype(float)   # one dropped: origins carry the level
    dest.index = p.index
    return pd.concat([X, origin, dest], axis=1)


def design(p):
    """The model's pair terms and both sets of fixed effects."""
    X = candidates(p)
    return X[FACTORS + [c for c in X.columns if c.startswith(("o_", "d_"))]]
