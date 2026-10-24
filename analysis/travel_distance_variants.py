"""Distance measured to where the jobs are, from where the people are -- not centroid to centroid.

Public data only:
  job hub of a county   the job-weighted median location (median latitude, median longitude) of its 2020 block groups,
                        jobs = LODES 2023 primary jobs (JT01 main, S000, by w_geocode block group)
  people of a county    LODES 2023 workers by home block group (h_geocode), a public stand-in for where residents live
  block groups          Census 2020 cartographic boundaries, centre = representative point; county shapes the same

Distance variants from origin county i to destination county j's job hub:
  centroid      current: Census 2020 mean centre of population to mean centre of population
  pop_mean      worker-weighted mean distance from i's block groups to j's hub
  pop_median    worker-weighted median of the same
  near_border   distance from i's nearest county edge to j's hub
  far_border    distance from i's farthest county edge to j's hub
Each replaces log distance in every distance term of the adopted model (gravity_terms.FACTORS: log distance, its
square, rural x distance and its square, origin size x distance; centred at 25 miles). Outcome: the adopted one
(calibrated, pass-through discounted). Scored as travel_tier_pull_cv.py: the 56 small rural counties held out in 8
folds (seed 7), each predicted from all other counties; share-weighted absolute error of destination shares with a 95%
bootstrap interval over the held-out counties and the change against the centroid distance, and the top-3 error (each
county's three largest FORECAST destinations).
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
with gzip.open(root / "free/mo_od_main_JT01_2023.csv.gz", "rt") as fh:
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

from gravity_terms import boot, county_stats, distance_terms, loco  # noqa: E402
import warnings  # noqa: E402
warnings.filterwarnings("ignore")


def with_distance(miles_series):
    X = X0.copy()
    D = distance_terms(np.log(np.asarray(miles_series, float)), pairs.i.values)
    for c in D.columns:
        X[c] = D[c].values
    return pd.concat([X[FACTORS + O], Dd], axis=1)


variants = {"centroid (adopted)": None, **{k: v for k, v in cols.items()}}
tier = pd.read_csv(root / "analysis/county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
small = sorted(tier.index[tier == "class 1"])
iu = np.array([unit(i) for i in pairs.i])
held = np.isin(iu, small)
o = pairs.i.values
a = share(y9)
print("| Distance | small rural held out: weighted share error [95%] | change vs centroid [95%] | top-3 destinations |")
print("|---|---:|---:|---:|")
ref = None
for label, dist in variants.items():
    X = Xof(FACTORS) if dist is None else with_distance(dist)
    ps = loco(y9, X, o, counties=sorted(set(o[held])))
    st = county_stats(a, ps, o, y9)
    lo, hi = boot(st, "werr")
    diff = ""
    if ref is None:
        ref = st
    else:
        dl, dh = boot(st, "werr", ref=ref)
        diff = f"{st.werr.mean() - ref.werr.mean():+.2f} [{dl:+.2f}, {dh:+.2f}]"
    rk = pd.Series(np.nan_to_num(ps, nan=-1)).groupby(o).rank(ascending=False, method="first").values
    top = held & (rk <= 3)
    print(f"| {label} | {st.werr.mean():.2f} [{lo:.2f}, {hi:.2f}] | {diff} | {100 * np.mean(np.abs(ps[top] - a[top])):.2f} |", flush=True)
pd.DataFrame({"i": pairs.i, "j": pairs.j, **cols}).to_csv(root / "analysis/pair_distances_jobhub.csv", index=False)
