"""Distance measured to where the jobs are, from where the people are -- not centroid to centroid.

Public data only:
  job hub of a county   the job-weighted median location (median latitude, median longitude) of its 2020 block groups,
                        jobs = LODES 2023 workplace counts (od_2023.csv.gz, S000, by w_geocode block group)
  people of a county    LODES 2023 workers by home block group (h_geocode), a public stand-in for where residents live
  block groups          Census 2020 cartographic boundaries, centre = representative point; county shapes the same

Distance variants from origin county i to destination county j's job hub:
  centroid      current: Census 2020 mean centre of population to mean centre of population
  pop_mean      worker-weighted mean distance from i's block groups to j's hub
  pop_median    worker-weighted median of the same
  near_border   distance from i's nearest county edge to j's hub
  far_border    distance from i's farthest county edge to j's hub
Each replaces log distance in every distance term of the adopted model (log distance, its square, rural x distance and
its square, origin size x distance). Scored as travel_tier_pull_cv.py: the 56 small rural counties held out in 8 folds,
each predicted from all other counties; share-weighted absolute error of destination shares, and the top-3 error.
"""
import csv
import gzip
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
exec(open(Path(__file__).resolve().parent / "travel_model_dc_test.py").read().split("models = [")[0])
__file__ = str(root / "flows/build_cousub_shares.py")
exec(open(root / "flows/build_cousub_shares.py").read().split("\ndef cw(")[0])          # read_shp, DL
from shapely.geometry import Point, shape

unit = lambda f: "29189" if f == "29510" else f
bgs = read_shp(str(DL / "bg/cb_2020_29_bg_500k"), lambda r: r["GEOID"])
bgc = {b: g.representative_point() for b, (_, g) in bgs.items()}
jobs_bg, work_bg = defaultdict(float), defaultdict(float)
with gzip.open(root / "free/od_2023.csv.gz", "rt") as fh:
    for r in csv.DictReader(fh):
        n = float(r["S000"])
        jobs_bg[r["w_geocode"][:12]] += n
        work_bg[r["h_geocode"][:12]] += n
by_cty = defaultdict(list)
for b in bgc:
    by_cty[unit(b[:5])].append(b)
geo = __import__("json").load(open(root / "flows/cousub_29.geojson"))
cshape = {}
for f in geo["counties"]["features"]:
    u = unit(f["id"])
    cshape[u] = cshape[u].union(shape(f["geometry"])) if u in cshape else shape(f["geometry"])

KX, KY = 111.32 * math.cos(math.radians(38.5)), 110.57          # km per degree near Missouri's middle
km = lambda ax, ay, bx, by: math.hypot((ax - bx) * KX, (ay - by) * KY) / 1.609   # miles


def wmedian(v, w):
    o = np.argsort(v); c = np.cumsum(np.array(w)[o]); return float(np.array(v)[o][np.searchsorted(c, c[-1] / 2)])


hub = {}
for c, bl in by_cty.items():
    w = [jobs_bg.get(b, 0) for b in bl]
    if sum(w) == 0:
        w = [1] * len(bl)
    hub[c] = (wmedian([bgc[b].x for b in bl], w), wmedian([bgc[b].y for b in bl], w))

cols = {"pop_mean": [], "pop_median": [], "near_border": [], "far_border": []}
cache = {}
for i, j in zip(pairs.i, pairs.j):
    ui, uj = unit(i), unit(j)
    key = (ui, uj)
    if key not in cache:
        hx, hy = hub[uj]
        bl = by_cty[ui]
        d = [km(bgc[b].x, bgc[b].y, hx, hy) for b in bl]
        w = [work_bg.get(b, 0) + 1e-9 for b in bl]
        poly = cshape[ui]
        parts = [poly] if poly.geom_type == "Polygon" else list(poly.geoms)
        ring = np.array([p for g in parts for p in g.exterior.coords])        # outer edges only
        bd = [km(x, y, hx, hy) for x, y in ring[:: max(1, len(ring) // 400)]]
        near = 0.0 if poly.contains(Point(hx, hy)) else min(bd)
        cache[key] = (np.average(d, weights=w), wmedian(d, w), max(near, 1.0), max(bd))
    for k, v in zip(cols, cache[key]):
        cols[k].append(max(v, 1.0))

base_terms = pair + ["log_dist_sq", "nonmetro_i_x_log_dist_sq", "log_pop_i_x_log_dist"]


def with_distance(miles_series):
    X = X0.copy()
    ld = np.log(np.asarray(miles_series, float))
    X["log_dist"] = ld
    X["log_dist_sq"] = ld ** 2
    X["nonmetro_i_x_log_dist"] = (1 - cov.metro.reindex(pairs.i).values) * ld
    X["nonmetro_i_x_log_dist_sq"] = X["nonmetro_i_x_log_dist"] * ld
    X["log_pop_i_x_log_dist"] = np.log(cov.population.reindex(pairs.i).values) * ld
    return pd.concat([X[base_terms + O], Dd], axis=1)


variants = {"centroid (current)": None, **{k: v for k, v in cols.items()}}
tier = pd.read_csv(root / "analysis/county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
small = sorted(tier.index[tier == "class 1"])
folds = np.array_split(np.random.default_rng(7).permutation(small), 8)
iu = np.array([unit(i) for i in pairs.i])
held = np.isin(iu, small)
a = share(y9)
print("| Distance | small rural held out: weighted share error | top-3 destinations |")
print("|---|---:|---:|")
for label, dist in variants.items():
    X = pd.concat([X0[base_terms + O], Dd], axis=1) if dist is None else with_distance(dist)
    pred = np.zeros(len(pairs))
    for f in folds:
        test = np.isin(iu, f); train = ~test
        cc = X.columns[(X[train] != 0).any()]
        m = sm.GLM(y9[train], X.loc[train, cc], family=sm.families.Poisson()).fit(maxiter=300)
        lin = X.loc[test, cc].values @ m.params.values
        pred[test] = np.exp(lin - lin.max())
    ps = pd.Series(pred).groupby(pairs.i.values).transform(lambda x: x / x.sum()).values
    e = 100 * np.sum(a[held] * np.abs(ps[held] - a[held])) / np.sum(a[held])
    top = held & (pd.Series(a).groupby(pairs.i.values).rank(ascending=False, method="first").values <= 3)
    print(f"| {label} | {e:.2f} | {100 * np.mean(np.abs(ps[top] - a[top])):.2f} |", flush=True)
pd.DataFrame({"i": pairs.i, "j": pairs.j, **cols}).to_csv(root / "analysis/pair_distances_jobhub.csv", index=False)
