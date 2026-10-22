"""Primary activity spaces of a place's population, Missouri. Advan Neighborhood Patterns Plus, January-July 2026
(od_tract_bg_mo_2026_janjul.parquet, built by activity_space.py); 3 km hexagons; 80% footprints and lobes as there.

  outbound  the place's residents: tracts whose 2020 centre of population lies inside the place (Census 2020 place
            boundary), pooled; footprint, lobes (each named by the place or county holding most of its visits),
            replicability from odd vs even months
  inbound   the population whose regular travel includes the place: tracts sending >= 10% of their regular visits to
            the place's block groups (block groups whose representative point lies inside it); population, counties
Usage: place_activity_space.py "Columbia" "Mexico" "Jefferson City" "Linn" ...
"""
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import shapefile
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

root = Path(__file__).resolve().parents[1]
A = root / "analysis"
monthly = pq.read_table(A / "od_tract_bg_mo_2026_janjul.parquet").to_pandas()
ALLM = sorted(monthly.month.unique())


def read(path, key):
    sf = shapefile.Reader(str(path)); f = [x[0] for x in sf.fields[1:]]
    return {sr.record[f.index(key)]: (dict(zip(f, sr.record)), shape(sr.shape.__geo_interface__)) for sr in sf.iterShapeRecords()}


places = read(root / "census_dl/place/cb_2020_29_place_500k", "GEOID")
bgs = read(root / "census_dl/bg/cb_2020_29_bg_500k", "GEOID")
bgpt = {k: g.representative_point() for k, (_, g) in bgs.items()}
tr = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_TR29.txt", dtype=str, encoding="utf-8-sig")
tr["t"] = tr.STATEFP + tr.COUNTYFP + tr.TRACTCE
tpt = {t: Point(float(lo), float(la)) for t, la, lo in zip(tr.t, tr.LATITUDE, tr.LONGITUDE)}
tpop = dict(zip(tr.t, tr.POPULATION.astype(float)))
co = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
cname = dict(zip(co.STATEFP + co.COUNTYFP, co.COUNAME))
pids = list(places); ptree = STRtree([places[p][1] for p in pids])


def place_of(pt):
    for i in ptree.query(pt):
        if places[pids[i]][1].contains(pt):
            return pids[i]
    return None


bg_place = {b: place_of(p) for b, p in bgpt.items()}
LAT0, SIZE = 38.7, 1.5
kx, ky = 111.32 * math.cos(math.radians(LAT0)), 110.57
HEX_AREA = 3 * math.sqrt(3) / 2 * SIZE ** 2


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


hexdist = lambda a, b: (abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[0] + a[1] - b[0] - b[1])) // 2
bghex = {b: axial(p.x, p.y) for b, p in bgpt.items()}


def footprint(rows):
    """rows: bg -> visits. Footprint hexes and lobes [(share, name)]"""
    h = defaultdict(float); hb = defaultdict(lambda: defaultdict(float))
    for b, v in rows.items():
        if b in bghex:
            h[bghex[b]] += v
            hb[bghex[b]][bg_place.get(b) or "c" + b[:5]] += v
    h = pd.Series(h).sort_values(ascending=False)
    tot = h.sum()
    foot = list(h.index[: int((h.cumsum() < 0.8 * tot).sum() + 1)])
    left, lobes = set(foot), []
    while left:
        seed = left.pop(); comp = {seed}; stack = [seed]
        while stack:
            c = stack.pop()
            for o in [o for o in left if hexdist(c, o) <= 2]:
                left.discard(o); comp.add(o); stack.append(o)
        who = defaultdict(float)
        for k in comp:
            for n, v in hb[k].items():
                who[n] += v
        top = max(who, key=who.get)
        name = places[top][0]["NAME"] if top in places else cname[top[1:]] + " Co. (rural)"
        lobes.append((h[list(comp)].sum() / tot, name, len(comp)))
    return set(foot), sorted(lobes, reverse=True)


def indicators(rows, homes):
    """Yuan & Xu (2022) external and internal indicators, visit-weighted, from the home area's centre of population:
    radius of gyration (km), standard deviational ellipse (axes km, elongation, orientation), convex hull of the 80%
    footprint (km2), entropy of visits over hexagons (bits)"""
    from shapely.geometry import MultiPoint
    b = [k for k in rows if k in bgpt]
    w = np.array([rows[k] for k in b], float); w = w / w.sum()
    hx = np.mean([tpt[t].x for t in homes]); hy = np.mean([tpt[t].y for t in homes])
    x = np.array([(bgpt[k].x - hx) * kx for k in b]); y = np.array([(bgpt[k].y - hy) * ky for k in b])
    rog = math.sqrt(np.sum(w * ((x - np.sum(w * x)) ** 2 + (y - np.sum(w * y)) ** 2)))
    cov = np.cov(np.vstack([x, y]), aweights=w); ev, evec = np.linalg.eigh(cov)
    hw = defaultdict(float)
    for k, wi in zip(b, w):
        hw[bghex[k]] += wi
    hs = pd.Series(hw).sort_values(ascending=False)
    foot = hs.index[: int((hs.cumsum() < 0.8).sum() + 1)]
    pts = [(bgpt[k].x * kx, bgpt[k].y * ky) for k in b if bghex[k] in set(foot)]
    hull = MultiPoint(pts).convex_hull.area if len(pts) >= 3 else 0.0
    ent = -np.sum(hs.values * np.log2(hs.values))
    return {"radius of gyration km": round(rog, 1), "ellipse axes km": f"{2 * math.sqrt(ev[1]):.0f} x {2 * math.sqrt(ev[0]):.0f}",
            "elongation": round(math.sqrt(ev[1] / ev[0]), 2), "orientation deg": round((math.degrees(math.atan2(evec[0, 1], evec[1, 1])) + 180) % 180),
            "convex hull km2": round(hull), "entropy bits": round(ent, 2)}


def pooled(tracts, months, min_months):
    m = monthly[monthly.tract.isin(tracts) & monthly.month.isin(months)]
    g = m.groupby(["bg", "month"]).v.sum().reset_index()
    k = g.groupby("bg").agg(v=("v", "sum"), n=("month", "nunique"))
    return k.v[k.n >= min_months].to_dict()


regular_tract = monthly.groupby(["tract", "bg"]).agg(v=("v", "sum"), n=("month", "nunique")).reset_index()
regular_tract = regular_tract[regular_tract.n >= 4]
for name in sys.argv[1:]:
    pid = next(p for p, (r, _) in places.items() if r["NAME"] == name)
    poly = places[pid][1]
    homes = [t for t, p in tpt.items() if poly.contains(p)]
    if not homes:      # a town smaller than any tract: the tract whose centre of population is nearest the town
        c = poly.representative_point()
        homes = [min(tpt, key=lambda t: tpt[t].distance(c))]
    foot, lobes = footprint(pooled(homes, ALLM, 4))
    fo, _ = footprint(pooled(homes, ALLM[0::2], 2)); fe, _ = footprint(pooled(homes, ALLM[1::2], 2))
    ind = indicators(pooled(homes, ALLM, 4), homes)
    print(f"\n{name}: {len(homes)} tracts, {sum(tpop[t] for t in homes):,.0f} residents | footprint {len(foot) * HEX_AREA:,.0f} km2 "
          f"| odd/even-month overlap {len(fo & fe) / max(len(fo | fe), 1):.2f}")
    print("  indicators: " + ", ".join(f"{k} {v}" for k, v in ind.items()))
    print("  OUTBOUND lobes (share of regular visits, hexagons): " + "; ".join(f"{n} {100 * s:.0f}% ({k})" for s, n, k in lobes if s >= 0.02))
    pbg = {b for b, p in bg_place.items() if p == pid}
    rt = regular_tract.assign(inp=regular_tract.bg.isin(pbg))
    sh = rt.groupby("tract").apply(lambda g: g.v[g.inp].sum() / g.v.sum())
    inbound = sh[(sh >= 0.10) & ~sh.index.isin(homes)]
    by_c = pd.Series({t: tpop.get(t, 0) for t in inbound.index}).groupby(lambda t: cname[t[:5]]).sum().sort_values(ascending=False)
    print(f"  INBOUND: {len(inbound)} tracts outside {name} send >= 10% of regular visits there, {by_c.sum():,.0f} residents; by county: "
          + ", ".join(f"{c} {v:,.0f}" for c, v in by_c.head(10).items()))
    for cut in (0.2, 0.3):
        x = sh[(sh >= cut) & ~sh.index.isin(homes)]
        print(f"    at >= {int(100 * cut)}%: {len(x)} tracts, {sum(tpop.get(t, 0) for t in x.index):,.0f} residents")
