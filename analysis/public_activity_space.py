"""Accuracy of activity spaces predicted from public data, against Advan's observed activity spaces (activity_space.py).

Observed: regular tract -> block group visits, January-July 2026 (od_tract_bg_mo_2026_janjul.parquet; >= 4 of 7
months); 3 km hexagons; 80% footprint; lobes (clusters, gap <= 1 hexagon, >= 5% of visits).
Predicted, per tract: P(block group) = county share x within-county share.
  home county share   public: the tract's workers who work in the home county / all its workers (LODES 2023)
  out-of-county share public model by class (combined_share) or + Missouri segment corrections (adjusted_C), each
                      county held out (public_adjusted_pairs_trnear.csv); Missouri destinations
  within a county     SPREAD=jobs: LODES 2023 workplace jobs by block group, half total jobs (C000), half retail,
                      health, arts and accommodation-food jobs (CNS07, CNS16, CNS17, CNS18), each as a share of the
                      county's; SPREAD=osm: OpenStreetMap destinations per block group (flows/reach/destinations_mo.csv);
                      SPREAD=mix: half each; times distance^-BETA from the tract (default 2: Reilly's law; the
                      visitation law's r^-2), renormalised in the county
Diagnostics: Advan's own county shares (home and out) with the public within-county spread -- separates county-share
error from within-county error. Replicability reference: Advan odd vs even months (activity_space_footprints_mo.pkl).
Scores per tract: footprint overlap (Jaccard), same number of lobes, heaviest observed hexagon inside the predicted
footprint, area ratio.
"""
import csv
import gzip
import math
import pickle
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import shapefile
from shapely.geometry import shape

root = Path(__file__).resolve().parents[1]
A = root / "analysis"
monthly = pq.read_table(A / "od_tract_bg_mo_2026_janjul.parquet").to_pandas()
obs = monthly.groupby(["tract", "bg"]).agg(v=("v", "sum"), n=("month", "nunique")).reset_index()
obs = obs[obs.n >= 4]
sf = shapefile.Reader(str(root / "census_dl/bg/cb_2020_29_bg_500k")); fl = [f[0] for f in sf.fields[1:]]
bgpt = {}
for sr in sf.iterShapeRecords():
    p = shape(sr.shape.__geo_interface__).representative_point(); bgpt[sr.record[fl.index("GEOID")]] = (p.x, p.y)
BG = sorted(bgpt); bix = {b: i for i, b in enumerate(BG)}
blon = np.array([bgpt[b][0] for b in BG]); blat = np.array([bgpt[b][1] for b in BG]); bcty = np.array([b[:5] for b in BG])
jobs, cons = defaultdict(float), defaultdict(float)
with gzip.open(root / "free/mo_wac_S000_JT00_2023.csv.gz", "rt") as fh:
    for r in csv.DictReader(fh):
        b = r["w_geocode"][:12]
        jobs[b] += float(r["C000"]); cons[b] += sum(float(r[c]) for c in ("CNS07", "CNS16", "CNS17", "CNS18"))
J = np.array([jobs.get(b, 0) for b in BG]); C = np.array([cons.get(b, 0) for b in BG])
cj = pd.Series(J).groupby(bcty).transform("sum").values; cc = pd.Series(C).groupby(bcty).transform("sum").values
_jobs = 0.5 * np.where(cj > 0, J / np.maximum(cj, 1), 0) + 0.5 * np.where(cc > 0, C / np.maximum(cc, 1), 0)
import os
SPREAD, BETA = os.environ.get("SPREAD", "jobs"), float(os.environ.get("BETA", "2"))   # within-county spread
_osm = pd.read_csv(root / "flows/reach/destinations_mo.csv", dtype={"block_group": str}).block_group.value_counts()
O_ = np.array([_osm.get(b, 0) for b in BG], float)
co_ = pd.Series(O_).groupby(bcty).transform("sum").values
_osm_s = np.where(co_ > 0, O_ / np.maximum(co_, 1), 0)
ATTR = {"jobs": _jobs, "osm": _osm_s, "mix": 0.5 * _jobs + 0.5 * _osm_s}[SPREAD] + 1e-6

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


BHEX = [axial(x, y) for x, y in zip(blon, blat)]
hexdist = lambda a, b: (abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[0] + a[1] - b[0] - b[1])) // 2
NB = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]
CLOSE = int(os.environ.get("CLOSE", "2"))      # market = footprint closed over gaps of up to CLOSE hexagons (~3 km each)


def ring(r):
    return [(q, s_) for q in range(-r, r + 1) for s_ in range(-r, r + 1) if abs(q) + abs(s_) + abs(q + s_) <= 2 * r]


def market(foot, r=CLOSE):
    """The market a footprint defines: morphological closing on the hexagon grid (dilate r, erode r), holes filled."""
    if not foot:
        return set()
    disk = ring(r)
    dil = {(a + dq, b + dr) for a, b in foot for dq, dr in disk}
    clo = {h for h in dil if all((h[0] + dq, h[1] + dr) in dil for dq, dr in disk)} | set(foot)
    qs = [h[0] for h in clo]; rs = [h[1] for h in clo]
    box = {(q, r_) for q in range(min(qs) - 1, max(qs) + 2) for r_ in range(min(rs) - 1, max(rs) + 2)}
    outside, stack = set(), [(min(qs) - 1, min(rs) - 1)]
    while stack:
        h = stack.pop()
        if h in outside or h in clo or h not in box:
            continue
        outside.add(h); stack.extend((h[0] + dq, h[1] + dr) for dq, dr in NB)
    return box - outside


def lobes_of(region, share=0.05):
    """separate markets: connected parts of the region holding at least `share` of its area"""
    left, sizes = set(region), []
    while left:
        stack = [left.pop()]; k = 1
        while stack:
            c = stack.pop()
            for dq, dr in NB:
                o = (c[0] + dq, c[1] + dr)
                if o in left:
                    left.discard(o); stack.append(o); k += 1
        sizes.append(k)
    return sum(k >= share * len(region) for k in sizes)


def footprint(w):
    """w: weights over BG (array) -> (footprint set, lobes count, heaviest hexagon)"""
    h = defaultdict(float)
    for i in np.flatnonzero(w > 0):
        h[BHEX[i]] += w[i]
    h = pd.Series(h).sort_values(ascending=False); tot = h.sum()
    foot = list(h.index[: int((h.cumsum() < 0.8 * tot).sum() + 1)])
    left, lobes = set(foot), 0
    while left:
        seed = left.pop(); comp = {seed}; stack = [seed]
        while stack:
            c = stack.pop()
            for o in [o for o in left if hexdist(c, o) <= 2]:
                left.discard(o); comp.add(o); stack.append(o)
        lobes += h[list(comp)].sum() / tot >= 0.05
    return set(foot), lobes, h.index[0]


tr = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_TR29.txt", dtype=str, encoding="utf-8-sig"); tr["t"] = tr.STATEFP + tr.COUNTYFP + tr.TRACTCE
tc = tr.set_index("t")[["LATITUDE", "LONGITUDE"]].astype(float)
W = pd.read_csv(A / "public_work_model_pairs_v1.csv", dtype={"tract": str, "j": str, "home": str}, usecols=["tract", "home", "j", "y"])
home_lodes = (W[W.home == W.j].groupby("tract").y.sum() / W.groupby("tract").y.sum()).fillna(0.5)
Q = pd.read_csv(A / "public_adjusted_pairs_trnear.csv", dtype={"tract": str, "j": str, "home": str})
Q = Q[Q.j.str[:2] == "29"]
obs["c"] = obs.bg.str[:5]
oc = obs.groupby(["tract", "c"]).v.sum()
oc = oc / oc.groupby(level=0).transform("sum")
home_adv = pd.Series({t: oc.get((t, t[:5]), 0) for t in oc.index.get_level_values(0).unique()})


def predicted(t, county_out, home_share):
    d = np.hypot((blon - tc.LONGITUDE[t]) * kx, (blat - tc.LATITUDE[t]) * ky)
    w = ATTR * np.maximum(d, 1.0) ** -BETA
    ws = pd.Series(w).groupby(bcty).transform("sum").values
    within = w / ws
    cs = np.array([county_out.get(c, 0.0) for c in bcty]) * (1 - home_share)
    cs[bcty == t[:5]] = home_share
    return within * cs


halves = pickle.load(open(A / "activity_space_footprints_mo.pkl", "rb"))
rows = []
obs_g = {t: g for t, g in obs.groupby("tract")}
qcol = {lab: Q.groupby("tract").apply(lambda g, c=col: dict(zip(g.j, g[c] / g[c].sum())))
        for col, lab in (("combined_share", "public"), ("adjusted_C", "public + corrections"))}
for t, g in obs_g.items():
    if t not in tc.index or t not in qcol["public"].index:
        continue
    ow = np.zeros(len(BG)); ix = [bix[b] for b in g.bg if b in bix]; ow[ix] = g.v[g.bg.isin(bix)].values
    fo, lo, ho = footprint(ow)
    mo = market(fo)
    out_adv = {c: v for (tt, c), v in oc.loc[[t]].items() if c != t[:5]}
    sa = sum(out_adv.values()); out_adv = {c: v / sa for c, v in out_adv.items()} if sa else {}
    variants = {"public": (qcol["public"][t], home_lodes.get(t, 0.5)),
                "public + corrections": (qcol["public + corrections"][t], home_lodes.get(t, 0.5)),
                "Advan county shares, public within-county spread": (out_adv, home_adv.get(t, 0.5)),
                "Advan out-of-county shares, LODES home share": (out_adv, home_lodes.get(t, 0.5))}
    rec = {"tract": t}
    for lab, (co_, hs) in variants.items():
        fp, lp, _ = footprint(predicted(t, co_, hs))
        rec[lab, "jaccard"] = len(fp & fo) / len(fp | fo); rec[lab, "lobes"] = lp == lo
        rec[lab, "top"] = ho in fp; rec[lab, "area"] = len(fp) / len(fo)
        mp = market(fp)
        rec[lab, "market"] = len(mp & mo) / len(mp | mo); rec[lab, "market_lobes"] = lobes_of(mp) == lobes_of(mo)
        rec[lab, "market_area"] = len(mp) / len(mo)
    if t in halves["odd"] and t in halves["even"]:
        a_, b_ = set(map(tuple, halves["odd"][t])), set(map(tuple, halves["even"][t]))
        rec["Advan odd vs even months", "jaccard"] = len(a_ & b_) / len(a_ | b_)
        ma, mb = market(a_), market(b_)
        rec["Advan odd vs even months", "market"] = len(ma & mb) / len(ma | mb)
        rec["Advan odd vs even months", "market_lobes"] = lobes_of(ma) == lobes_of(mb)
        rec["Advan odd vs even months", "market_area"] = len(ma) / len(mb)
    rows.append(rec)
R = pd.DataFrame(rows).set_index("tract")
unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(A / "county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
L = {"class 1": "small rural", "class 2": "indep. towns", "class 3": "commuter", "class 4": "hubs"}
cls = pd.Series([L[tier.get(unit(t[:5]), "class 1")] for t in R.index], index=R.index)
labs = ["Advan odd vs even months", "public", "public + corrections", "Advan county shares, public within-county spread", "Advan out-of-county shares, LODES home share"]
print("| Activity space, Missouri tracts | footprint overlap (median Jaccard) | " + " | ".join(L.values()) + " | same number of lobes | heaviest observed hexagon inside | area ratio (median) |")
print("|---|---:|" + "---:|" * len(L) + "---:|---:|---:|")
for lab in labs:
    j = R[(lab, "jaccard")]
    line = f"| {lab} | {j.median():.2f} | " + " | ".join(f"{j[cls == c].median():.2f}" for c in L.values())
    if (lab, "lobes") in R:
        line += f" | {100 * R[(lab, 'lobes')].mean():.0f}% | {100 * R[(lab, 'top')].mean():.0f}% | {R[(lab, 'area')].median():.2f} |"
    else:
        line += " | 85% (activity_space.py) | — | — |"
    print(line)
print("\n| Market (footprint closed over gaps of " + str(CLOSE) + " hexagons, holes filled) | market overlap (median Jaccard) | " + " | ".join(L.values()) + " | same number of markets | area ratio (median) |")
print("|---|---:|" + "---:|" * len(L) + "---:|---:|")
for lab in labs:
    j = R[(lab, "market")]
    print(f"| {lab} | {j.median():.2f} | " + " | ".join(f"{j[cls == c].median():.2f}" for c in L.values())
          + f" | {100 * R[(lab, 'market_lobes')].mean():.0f}% | {R[(lab, 'market_area')].median():.2f} |")
R.to_csv(A / f"public_activity_space_scores_{SPREAD}_{BETA:g}.csv")
