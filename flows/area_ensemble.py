"""The civic interest area as a PROBABILITY SURFACE over plausible drawing settings (user, 2026-10-24, option A): the
outline moved by more than half under hexagon size, busiest-place scaling and the dasymetric spread
(analysis/area_sensitivity.csv), so each area is drawn under every combination of the settings below and each published
3 km hexagon is given p = the share of members that draw it.

The area is the PUBLISHED, NETWORK-TIE map (market_patterns.py idx["net"]: travel strengthened by news ties). Same K,
patterns, data and news weights in every member; only the drawing changes. FULL FACTORIAL, 432 members:
  hexagon size        2, 3, 4 km (the whole grid rebuilt: market_patterns.py HEX_KM)                       3
  TRAVEL_TOP          0.5 (adopted: busiest place 50), 1.0 (busiest place 100)                               2
  dasymetric spread   off (a rural block group one value), DFLOOR 0.1, 0.25 (adopted), 1                      4
  LAMBDA              0, 0.25 (adopted), 0.5 (spatial lag)                                                    3
  selectivity         40, 50 (adopted), 60% (share of ties outside home the drawn hexagons hold)              3
  distance rule       on (adopted: 2x at 4 hexagons inside the TV market, 2 outside), off                     2
Held at the adopted values: GAMMA 0.5, the tie cut 1, the floor 5 (never binding: every area's selectivity threshold is
above it), the news weights. Distances in the distance rule are in hexagons of the member's grid.
A member draws the area as the published map does: its shown hexagons, joined into the area's body -- the pieces
holding home, and every piece within 15 km (5 hexagons of 3 km) of the body, grown outward; distant clusters are left
off, as the published outline leaves them (confidence_layer.outline_for). Without it, a large city that is one travel
unit (Kansas City, Springfield) is drawn whole far from home in every member without the distance rule.
The member's drawn hexagons are mapped onto the published 3 km grid: a 3 km hexagon counts as drawn when 50%+ of its
area lies under the member's drawn hexagons (on the km plane, x = lon x 111.32 cos 38.7, y = lat x 110.57).
CORE = hexagons with p >= 0.5 (the area as stated; p >= 0.8 also reported); km2 = hexagons x 5.85; people inside = the
2020 population of those hexagons (each block group's population over the hexagons whose centres lie in it).
REPLICABILITY: the whole ensemble repeated on each half of the year -- each half's own fit (W and H refitted on odd or
even months, matched to the kept patterns) and its travel: the correlation of p between halves over hexagons drawn in
either, and the Jaccard of the two cores (home hexagons excluded).
Writes <region out>/probability.json (Columbia: flows/reach/probability_columbia.json).
Usage: area_ensemble.py <region> [all]   (default: the built towns of flows/export_figures.py; all = every study town)"""
import itertools
import json
import math
import os
import runpy
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Polygon
from shapely.ops import unary_union

here = Path(__file__).resolve().parent
root = here.parent
region = sys.argv[1] if len(sys.argv) > 1 else "columbia"
ALL = len(sys.argv) > 2 and sys.argv[2] == "all"
os.environ.pop("HEX_KM", None)
sys.argv = ["confidence_layer.py", region]
C = runpy.run_path(str(root / "analysis/confidence_layer.py"), run_name="confidence_lib")
ns, P, MAPS, HALVES = C["ns"], C["P"], C["MAPS"], C["HALVES"]
G3 = ns["tie_map"].__globals__
BUILT = {"columbia": ("Columbia", "Mexico", "Linn"), "springfield": ("Springfield",), "joplin": ("Joplin",),
         "kirksville": ("Kirksville",)}
towns = list(MAPS["towns"]) if ALL else list(BUILT.get(region, ()))
AREAS = [(t, m["rank"]) for t in towns for m in MAPS["towns"][t]]
if not AREAS:
    raise SystemExit(f"{region}: no built town (pass 'all' for every study town)")
HEX_KMS, TOPS, DWS, LAMS, SELS, DISTS = (2, 3, 4), (0.5, 1.0), ("off", 0.1, 0.25, 1.0), (0.0, 0.25, 0.5), (0.4, 0.5, 0.6), ("on", "off")
MEMBERS = len(HEX_KMS) * len(TOPS) * len(DWS) * len(LAMS) * len(SELS) * len(DISTS)
KXP, KYP = 111.32 * math.cos(math.radians(38.7)), 110.57
HEX_KM2 = MAPS.get("hex_km2", 5.846)

# the published 3 km grid on the km plane, for mapping other grids onto it
ids3 = list(G3["hexes"])
poly3 = np.array([Polygon([(x * KXP, y * KYP) for x, y in G3["hexes"][k][:6]]) for k in ids3])
area3 = shapely.area(poly3)
tree3 = shapely.STRtree(poly3)

# population by 3 km hexagon (as area_coverage_alignment.py)
hex_bg = G3["hex_bg"]
bg_hexes = defaultdict(list)
for k, b in hex_bg.items():
    bg_hexes[b].append(k)
cp = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_BG29.txt", dtype=str, encoding="utf-8-sig")
hex_pop = defaultdict(float)
for r in cp.itertuples():
    g_ = r.STATEFP + r.COUNTYFP + r.TRACTCE + r.BLKGRPCE
    hs = bg_hexes.get(g_) or ([G3["hex_of"](float(r.LONGITUDE), float(r.LATITUDE))] if G3["hex_of"](float(r.LONGITUDE), float(r.LATITUDE)) else [])
    for k in hs:
        hex_pop[k] += float(r.POPULATION) / len(hs)


def onto3(drawn, hexes):
    """the published 3 km hexagons with 50%+ of their area under the drawn hexagons of another grid"""
    if not drawn:
        return set()
    u = unary_union([Polygon([(x * KXP, y * KYP) for x, y in hexes[k][:6]]) for k in drawn if k in hexes]).buffer(1e-6)
    cand = tree3.query(u)
    frac = shapely.area(shapely.intersection(poly3[cand], u)) / area3[cand]
    return {ids3[i] for i, f in zip(cand, frac) if f >= 0.5}


NB6 = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]
hexdist = lambda a, b: (abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[0] + a[1] - b[0] - b[1])) // 2


def body(on, values, hk):
    """the pieces holding home and every piece within 15 km of them, grown outward (the published outline's rule)"""
    cells = {tuple(map(int, k.split(","))) for k in on}
    home = {tuple(map(int, k.split(","))) for k in on if values.get(k, 0) >= 100}
    left, ps = set(cells), []
    while left:
        st = [left.pop()]; comp = {st[0]}
        while st:
            c = st.pop()
            for dq, dr in NB6:
                o = (c[0] + dq, c[1] + dr)
                if o in left:
                    left.discard(o); st.append(o); comp.add(o)
        ps.append(comp)
    kept = set().union(*[p_ for p_ in ps if p_ & home]) if home else set()
    reach = max(1, round(15 / hk))
    grew = True
    while grew and kept:
        grew = False
        for p_ in ps:
            if p_ <= kept:
                continue
            if min(hexdist(a_, b_) for a_ in p_ for b_ in kept) <= reach:
                kept |= p_; grew = True
    return {f"{a},{b}" for a, b in kept}


def dw_for(G, fl):
    if fl == "off":
        return {}
    out_ = {}
    for u_, ks in G["by_unit"].items():
        m_ = np.mean([G["dcount"].get(k_, 0) + fl for k_ in ks])
        for k_ in ks:
            out_[k_] = (G["dcount"].get(k_, 0) + fl) / m_
    return out_


# travel inputs: the full fit and each half's own fit (grid-independent)
SOURCES = ("all", "odd", "even")
travel_in = {}
for town, rank in AREAS:
    pt = next(x for x in ns["out"][town] if x["rank"] == rank)
    g_ = pt["patterns"]
    travel_in[(town, rank)] = {"all": C["pattern_travel"](town, g_, P["X"]),
                               **{s: C["pattern_travel"](town, g_, HALVES[f"X_{s}"], HALVES[f"W_{s}"], HALVES[f"H_{s}"]) for s in ("odd", "even")}}
counts = {a: {s: defaultdict(int) for s in SOURCES} for a in AREAS}
adopted = {}
for hk in HEX_KMS:
    if hk == 3:
        G = G3
    else:
        os.environ["HEX_KM"], os.environ["TIE_LIB"] = str(hk), "1"
        sys.argv = ["tie_footprint.py", region]
        G = runpy.run_path(str(root / "analysis/tie_footprint.py"), run_name="tie_lib")["tie_map"].__globals__
        os.environ.pop("HEX_KM", None)
    in_market = {k for k, c in G["hex_county"].items() if c in G["CFG"]["dma_counties"]}
    DW0 = dict(G["DW"])
    saved = {k: G[k] for k in ("TRAVEL_TOP", "LAMBDA")}
    for top, dw, lam in itertools.product(TOPS, DWS, LAMS):
        G["TRAVEL_TOP"], G["LAMBDA"] = top, lam
        G["DW"].clear(); G["DW"].update(dw_for(G, dw) if dw != 0.25 else DW0)
        for a in AREAS:
            for s in SOURCES:
                t = {k: round(v, 1) for k, v in G["tie_map"](a[0], travel_in[a][s]).items() if v >= 1}
                for sel, dist in itertools.product(SELS, DISTS):
                    on, _ = C["shown_set"](t, in_market, sel=sel, top_mult=2 if dist == "on" else 1)
                    on = body(on, t, hk)
                    drawn = on if hk == 3 else onto3(on, G["hexes"])
                    for k in drawn:
                        counts[a][s][k] += 1
                    if (hk, top, dw, lam, sel, dist, s) == (3, 0.5, 0.25, 0.25, 0.5, "on", "all"):
                        adopted[a] = set(on)
        print(f"hexagon {hk} km, TRAVEL_TOP {top}, dasymetric {dw}, LAMBDA {lam}: done", flush=True)
    G.update(saved); G["DW"].clear(); G["DW"].update(DW0)

R = root / json.load(open(here / "regions.json"))[region]["out"]
out_path = here / "reach/probability_columbia.json" if region == "columbia" else R / "probability.json"
out = json.load(open(out_path)) if out_path.exists() else {}
jac = lambda a, b: len(a & b) / max(1, len(a | b))
CONF_ = json.load(open(here / "reach/confidence_columbia.json" if region == "columbia" else R / "confidence.json"))
from shapely.geometry import Point, shape  # noqa: E402


def inside(geom):
    """km2 (hexagons whose centres lie inside x 5.85) and 2020 people of an outline"""
    g = shape(geom)
    hs = [k for k in MAPS["hexes"] if g.contains(Point(*G3["centre"][k]))]
    return round(len(hs) * HEX_KM2), round(sum(hex_pop.get(k, 0) for k in hs))
for (town, rank) in AREAS:
    p = {s: {k: n / MEMBERS for k, n in counts[(town, rank)][s].items()} for s in SOURCES}
    home = {k for k, v in next(x for x in MAPS["towns"][town] if x["rank"] == rank)["index"]["net"].items() if v >= 100}
    core = {c: {k for k, v in p["all"].items() if v >= c} for c in (0.5, 0.8)}
    halves = {s: {c: {k for k, v in p[s].items() if v >= c} - home for c in (0.5, 0.8)} for s in ("odd", "even")}
    keys = sorted((set(p["odd"]) | set(p["even"])) - home)
    r_ = float(np.corrcoef([p["odd"].get(k, 0) for k in keys], [p["even"].get(k, 0) for k in keys])[0, 1]) if len(keys) > 2 else float("nan")
    ad = adopted[(town, rank)]
    _net = next(x for x in MAPS["towns"][town] if x["rank"] == rank)["index"]["net"]
    pub = body(C["shown_set"](_net, set(MAPS.get("in_market", [])))[0], _net, 3)
    assert len(ad ^ pub) <= 0.02 * max(1, len(pub)), f"{town} {rank}: the adopted member differs from the published map"
    rec = {"members": MEMBERS,
           "design": {"hexagon_km": list(HEX_KMS), "TRAVEL_TOP": list(TOPS), "dasymetric": [str(d) for d in DWS],
                      "LAMBDA": list(LAMS), "selectivity": list(SELS), "distance_rule": list(DISTS), "factorial": True},
           "p": {k: round(v, 3) for k, v in sorted(p["all"].items())},
           "p_odd": {k: round(v, 3) for k, v in sorted(p["odd"].items())},
           "p_even": {k: round(v, 3) for k, v in sorted(p["even"].items())},
           "core50_km2": round(len(core[0.5]) * HEX_KM2), "core80_km2": round(len(core[0.8]) * HEX_KM2),
           "core50_hexagons": len(core[0.5]), "core80_hexagons": len(core[0.8]),
           "people50": round(sum(hex_pop.get(k, 0) for k in core[0.5])), "people80": round(sum(hex_pop.get(k, 0) for k in core[0.8])),
           "adopted_km2": round(len(ad) * HEX_KM2), "adopted_in_core50": round(len(ad & core[0.5]) / max(1, len(ad)), 3),
           "adopted_people": round(sum(hex_pop.get(k, 0) for k in ad)),
           **{f"{key}_{m_}": v_ for key in ("outline", "outline_travel") for m_, v_ in zip(("km2", "people"), inside(CONF_[town][str(rank)][key]))},
           "core50_in_adopted": round(len(ad & core[0.5]) / max(1, len(core[0.5])), 3),
           "replicability": {"pearson_p_odd_even": round(r_, 3), "jaccard_core50": round(jac(halves["odd"][0.5], halves["even"][0.5]), 3),
                             "jaccard_core80": round(jac(halves["odd"][0.8], halves["even"][0.8]), 3),
                             "core50_odd_even": [len(halves["odd"][0.5]), len(halves["even"][0.5])]}}
    out.setdefault(town, {})[str(rank)] = rec
    print(f"{town} {rank}: {MEMBERS} members; core p>=0.5 {rec['core50_km2']:,} km2, {rec['people50']:,} people; "
          f"p>=0.8 {rec['core80_km2']:,} km2, {rec['people80']:,} people; adopted map {rec['adopted_km2']:,} km2, "
          f"{rec['adopted_in_core50']:.0%} of it in the core; replicability {rec['replicability']}", flush=True)
json.dump(out, open(out_path, "w"))
print("wrote", out_path)
