"""Travel-only activity-space markets, every tract of a state: accuracy of the public model against Advan, and Advan's
replicability. Same settings in Missouri and Kansas, so the Kansas run is a transfer test of the method.

Observed   Advan regular tract -> block group visits, January-July 2026 (od_tract_bg_<st>_2026_janjul.parquet;
           >= 4 of 7 months; odd and even months >= 2 of theirs). Frame: Missouri destinations for Missouri homes;
           Kansas and Missouri destinations for Kansas homes.
Public     regular-travel public model by class (public_model_pairs_tiers[_20]_byclass_regular.csv, no corrections),
           out-of-county shares; home-county share = the tract's workers working in their home county (LODES 2023);
           within a county: a third each of jobs (LODES WAC: half total, half retail/health/arts/food), OpenStreetMap
           destinations (destinations_mo/ks.csv) and 2020 block group population, at distance^-0.5; Advan's
           regularity rule (regularity_rule.csv, fitted in Missouri).
Market     80% footprint on 3 km hexagons, closed over gaps of 2 hexagons, holes filled; separate markets = parts of
           5%+ of its area.
Usage: activity_market_score.py 29|20
"""
import csv
import gzip
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import shapefile
from shapely.geometry import shape

root = Path(__file__).resolve().parents[1]
A = root / "analysis"; REF = root / "census_dl/ref"
ST = sys.argv[1] if len(sys.argv) > 1 else "29"
SUF = "" if ST == "29" else "_20"
FRAME = {"29": ["29"], "20": ["20", "29"]}[ST]
monthly = pq.read_table(A / ("od_tract_bg_mo_2026_janjul.parquet" if ST == "29" else "od_tract_bg_ks_2026_janjul.parquet")).to_pandas()
monthly = monthly[monthly.bg.str[:2].isin(FRAME)]
ALLM = sorted(monthly.month.unique())

# block groups of the frame: points, county, attraction
SHP = {"29": root / "census_dl/bg/cb_2020_29_bg_500k", "20": root / "census_dl/bg_ks/cb_2020_20_bg_500k"}
bgpt = {}
for s in FRAME:
    sf = shapefile.Reader(str(SHP[s])); fl = [f[0] for f in sf.fields[1:]]
    for sr in sf.iterShapeRecords():
        p = shape(sr.shape.__geo_interface__).representative_point(); bgpt[sr.record[fl.index("GEOID")]] = (p.x, p.y)
BG = sorted(bgpt); bix = {b: i for i, b in enumerate(BG)}
blon = np.array([bgpt[b][0] for b in BG]); blat = np.array([bgpt[b][1] for b in BG]); bcty = np.array([b[:5] for b in BG])
jobs, cons = defaultdict(float), defaultdict(float)
for f in [root / "free/mo_wac_S000_JT00_2023.csv.gz"] + ([root / "free/ks/ks_wac_S000_JT00_2023.csv.gz"] if "20" in FRAME else []):
    with gzip.open(f, "rt") as fh:
        for r in csv.DictReader(fh):
            b = r["w_geocode"][:12]
            jobs[b] += float(r["C000"]); cons[b] += sum(float(r[c]) for c in ("CNS07", "CNS16", "CNS17", "CNS18"))
osm = pd.concat([pd.read_csv(root / f"flows/reach/destinations_{'mo' if s == '29' else 'ks'}.csv", dtype={"block_group": str}) for s in FRAME]).block_group.value_counts()
bgpop = {}
for s in FRAME:
    x = pd.read_csv(REF / f"CenPop2020_Mean_BG{s}.txt", dtype=str, encoding="utf-8-sig")
    bgpop.update(dict(zip(x.STATEFP + x.COUNTYFP + x.TRACTCE + x.BLKGRPCE, x.POPULATION.astype(float))))
cnt = lambda d: np.array([d.get(b, 0.0) for b in BG], float)
share_in = lambda x: np.where(pd.Series(x).groupby(bcty).transform("sum").values > 0, x / np.maximum(pd.Series(x).groupby(bcty).transform("sum").values, 1e-9), 0)
ATTR = (0.5 * share_in(cnt(jobs)) + 0.5 * share_in(cnt(cons))) / 3 + share_in(np.array([osm.get(b, 0) for b in BG], float)) / 3 + share_in(cnt(bgpop)) / 3 + 1e-6

trc = pd.read_csv(REF / f"CenPop2020_Mean_TR{ST}.txt", dtype=str, encoding="utf-8-sig"); trc["t"] = trc.STATEFP + trc.COUNTYFP + trc.TRACTCE
tc = trc.set_index("t")[["LATITUDE", "LONGITUDE", "POPULATION"]].astype(float)
W = pd.read_csv(A / f"public_work_model_pairs{SUF}_v1.csv", dtype={"tract": str, "home": str, "j": str}, usecols=["tract", "home", "j", "y"])
home_lodes = (W[W.home == W.j].groupby("tract").y.sum() / W.groupby("tract").y.sum()).fillna(0.5)
Q = pd.read_csv(A / f"public_model_pairs_tiers{SUF}_byclass_regular.csv", dtype={"tract": str, "home": str, "j": str})
Q = Q[Q.j.str[:2].isin(FRAME)]
qshare = {t: dict(zip(g.j, g.combined_share / g.combined_share.sum())) for t, g in Q.groupby("tract")}
RB = pd.read_csv(A / "regularity_rule.csv", index_col=0).iloc[:, 0].values

LAT0, SIZE = 38.7, 1.5
kx, ky = 111.32 * math.cos(math.radians(LAT0)), 110.57


def axial(lon, lat):
    x, y = lon * kx, lat * ky
    qf, rf = (math.sqrt(3) / 3 * x - y / 3) / SIZE, (2 / 3 * y) / SIZE
    sf_ = -qf - rf
    rq, rr, rs = round(qf), round(rf), round(sf_)
    dq, dr, ds = abs(rq - qf), abs(rr - rf), abs(rs - sf_)
    if dq > dr and dq > ds:
        rq = -rr - rs
    elif dr > ds:
        rr = -rq - rs
    return rq, rr


BHEX = [axial(x, y) for x, y in zip(blon, blat)]
NB = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]
disk = [(q, s_) for q in range(-2, 3) for s_ in range(-2, 3) if abs(q) + abs(s_) + abs(q + s_) <= 4]


def market_of(w):
    h = defaultdict(float)
    for i in np.flatnonzero(w > 0):
        h[BHEX[i]] += w[i]
    if not h:
        return set()
    hs = pd.Series(h).sort_values(ascending=False)
    foot = set(hs.index[: int((hs.cumsum() < 0.8 * hs.sum()).sum() + 1)])
    dil = {(a + dq, b + dr) for a, b in foot for dq, dr in disk}
    clo = {x for x in dil if all((x[0] + dq, x[1] + dr) in dil for dq, dr in disk)} | foot
    qs = [x[0] for x in clo]; rs = [x[1] for x in clo]
    box = {(q, r) for q in range(min(qs) - 1, max(qs) + 2) for r in range(min(rs) - 1, max(rs) + 2)}
    out, stack = set(), [(min(qs) - 1, min(rs) - 1)]
    while stack:
        x = stack.pop()
        if x in out or x in clo or x not in box:
            continue
        out.add(x); stack.extend((x[0] + dq, x[1] + dr) for dq, dr in NB)
    return box - out


def n_markets(reg):
    left, sizes = set(reg), []
    while left:
        stack = [left.pop()]; k = 1
        while stack:
            c = stack.pop()
            for dq, dr in NB:
                o = (c[0] + dq, c[1] + dr)
                if o in left:
                    left.discard(o); stack.append(o); k += 1
        sizes.append(k)
    return sum(k >= 0.05 * len(reg) for k in sizes)


def observed(g, months, min_m):
    g = g[g.month.isin(months)]
    k = g.groupby("bg").agg(v=("v", "sum"), n=("month", "nunique"))
    k = k[(k.n >= min_m) & k.index.isin(bix)]
    w = np.zeros(len(BG)); w[[bix[b] for b in k.index]] = k.v.values
    return w


def predicted(t):
    d = np.hypot((blon - tc.LONGITUDE[t]) * kx, (blat - tc.LATITUDE[t]) * ky)
    w = ATTR * np.maximum(d, 1.0) ** -0.5
    within = w / pd.Series(w).groupby(bcty).transform("sum").values
    hs = home_lodes.get(t, 0.5)
    cs = np.array([qshare[t].get(c, 0.0) for c in bcty]) * (1 - hs)
    cs[bcty == t[:5]] = hs
    pr = within * cs
    return np.where(RB[0] + RB[1] * np.log(np.maximum(pr, 1e-12)) + RB[2] * math.log(max(tc.POPULATION[t], 1)) > 0, pr, 0)


jac = lambda a, b: len(a & b) / len(a | b) if (a | b) else np.nan
# BASELINES -- the conventional definitions of a local market, and a size-only one
county_hexes = defaultdict(set)
for i, c in enumerate(bcty):
    county_hexes[c].add(BHEX[i])
Wo = pd.read_csv(A / f"public_work_model_pairs{SUF}_v1.csv", dtype={"tract": str, "home": str, "j": str}, usecols=["tract", "j", "act_share"])
Wo = Wo[Wo.j.str[:2].isin(FRAME)]
work_share = {t: dict(zip(g.j, g.act_share / max(g.act_share.sum(), 1e-12))) for t, g in Wo.groupby("tract")}
JOBS_ATTR = share_in(cnt(jobs)) + 1e-9


def commute_shed(t):
    """where the tract's workers work: LODES observed county shares, within the county by jobs"""
    cs = np.array([work_share.get(t, {}).get(c, 0.0) for c in bcty])
    return JOBS_ATTR * cs


def circle(t, km2):
    r_hex = math.sqrt(km2 / 5.85 / math.pi)
    c0 = axial(tc.LONGITUDE[t], tc.LATITUDE[t])
    R_ = int(math.ceil(r_hex))
    return {(c0[0] + q, c0[1] + s_) for q in range(-R_, R_ + 1) for s_ in range(-R_, R_ + 1)
            if (abs(q) + abs(s_) + abs(q + s_)) / 2 <= r_hex}


rows = []
for t, g in monthly.groupby("tract"):
    if t not in tc.index or t not in qshare or tc.POPULATION[t] < 100:
        continue
    mo, mp = market_of(observed(g, ALLM, 4)), market_of(predicted(t))
    m1, m2 = market_of(observed(g, ALLM[0::2], 2)), market_of(observed(g, ALLM[1::2], 2))
    if not mo:
        continue
    mc, mw = county_hexes[t[:5]], market_of(commute_shed(t))
    rec = {"tract": t, "accuracy": jac(mp, mo), "replicability": jac(m1, m2), "markets_obs": n_markets(mo),
           "markets_pub": n_markets(mp), "area_ratio": len(mp) / len(mo), "km2": len(mo) * 5.85,
           "recall": len(mp & mo) / len(mo), "precision": len(mp & mo) / max(len(mp), 1),
           "county": jac(mc, mo), "county_recall": len(mc & mo) / len(mo), "county_precision": len(mc & mo) / len(mc),
           "shed": jac(mw, mo), "shed_recall": len(mw & mo) / len(mo), "shed_precision": len(mw & mo) / max(len(mw), 1),
           "_obs": mo}
    rows.append(rec)
R = pd.DataFrame(rows).set_index("tract")
obs_sets = R.pop("_obs")
tier = pd.read_csv(A / f"county_class_k4{SUF}.csv", dtype={"fips": str}).set_index("fips")["class"]
unit = lambda f: "29189" if f == "29510" else f
L = {"class 1": "small rural", "class 2": "indep. towns", "class 3": "commuter", "class 4": "hubs"}
R["cls"] = [L[tier.get(unit(t[:5]), "class 1")] for t in R.index]
med_km2 = R.groupby("cls").km2.median()
circ = {t: circle(t, med_km2[R.cls[t]]) for t in R.index}
R["circle"] = [jac(circ[t], obs_sets[t]) for t in R.index]
R["circle_recall"] = [len(circ[t] & obs_sets[t]) / len(obs_sets[t]) for t in R.index]
R["circle_precision"] = [len(circ[t] & obs_sets[t]) / len(circ[t]) for t in R.index]
R.to_csv(A / f"activity_market_score_{ST}.csv")
print(f"\n| {ST} -- definition of the market | Overlap with Advan's (median Jaccard) | Recall: observed market covered | Precision: of it, observed |")
print("|---|---:|---:|---:|")
for lab, k in (("Advan itself, odd vs even months (ceiling)", None), ("public model (travel)", ""), ("home county", "county"),
               ("commuting shed (LODES only)", "shed"), ("circle of the class's median observed area (size from Advan)", "circle")):
    if k is None:
        print(f"| {lab} | {R.replicability.median():.2f} | -- | -- |"); continue
    j = R["accuracy" if k == "" else k]; rc = R["recall" if k == "" else k + "_recall"]; pr = R["precision" if k == "" else k + "_precision"]
    print(f"| {lab} | {j.median():.2f} | {100 * rc.median():.0f}% | {100 * pr.median():.0f}% |")
name = {"29": "Missouri", "20": "Kansas"}[ST]
print(f"| {name} ({len(R)} tracts) | Replicability (Advan, odd vs even) | Accuracy (public vs Advan) | Same number of markets | Within one | Area ratio |")
print("|---|---:|---:|---:|---:|---:|")
for c in list(L.values()) + ["all"]:
    x = R if c == "all" else R[R.cls == c]
    if len(x):
        print(f"| {c} ({len(x)}) | {x.replicability.median():.2f} | {x.accuracy.median():.2f} | {100 * (x.markets_obs == x.markets_pub).mean():.0f}% | "
              f"{100 * ((x.markets_obs - x.markets_pub).abs() <= 1).mean():.0f}% | {x.area_ratio.median():.2f} |")
