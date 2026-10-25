"""THE AREA IS MULTI-PART (user, 2026-10-25; replaces the held "one connected area" rule): the core of the settings
ensemble (p >= 0.5, flows/area_ensemble.py) is kept as
  - the home body: the core piece(s) holding home;
  - every other core piece of 3 or more hexagons, wherever it lies -- a separate part of the area, outlined on its own
    and labelled by its largest town (Columbia is Mexico's dominant destination, a part some 45 km from Mexico);
  - core specks of 1-2 hexagons leave the outline (their p shading stays on the map).
Writes into <region out>/probability.json, per area: core50_outline (the parts; the plain union of every core hexagon is
kept as core50_outline_unconnected), core50_parts [{name, hexagons, km2, people, km_from_home_body, home}],
core50_specks [...], and core50_kept {hexagons, km2, people} beside the unconnected figures. km2 on the ground
(5.85 x cos(latitude) / cos(38.7) per hexagon); people = 2020 population of the hexagons (each block group's population
over the hexagons of the statewide 3 km grid whose centres lie in it; a block group holding no centre goes to the
hexagon of its population centre); a part's name is the largest town of 2,500+ (or a configured study town) within one
hexagon of it, else "rural <county>".
Usage: area_core.py <region> [<region> ...]"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import shapefile
from shapely.geometry import Point, Polygon, mapping, shape
from shapely.ops import unary_union
from shapely.strtree import STRtree

here = Path(__file__).resolve().parent
root = here.parent
REACH_KM, SP3 = 15, math.sqrt(3) * 1.5
CNAME = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str}).set_index("fips").name.to_dict()
REACH_HEX = REACH_KM / SP3
NB6 = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]
hexdist = lambda a, b: (abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[0] + a[1] - b[0] - b[1])) // 2
qr = lambda k: tuple(map(int, k.split(",")))
key = lambda c: f"{c[0]},{c[1]}"
LAT0, SIZE = 38.7, 1.5
kx, ky = 111.32 * math.cos(math.radians(LAT0)), 110.57


def centre_of(c):
    q, r = c
    return SIZE * math.sqrt(3) * (q + r / 2) / kx, SIZE * 1.5 * r / ky


def corners(c):
    q, r = c
    cx, cy = SIZE * math.sqrt(3) * (q + r / 2), SIZE * 1.5 * r
    return [((cx + SIZE * math.cos(math.radians(60 * i - 30))) / kx, (cy + SIZE * math.sin(math.radians(60 * i - 30))) / ky) for i in range(7)]


km2 = lambda cells: sum(3 * math.sqrt(3) / 2 * SIZE ** 2 * math.cos(math.radians(centre_of(c)[1])) / math.cos(math.radians(LAT0)) for c in cells)

def qr_ll(lon, lat):
    x, y = lon * kx, lat * ky
    qf, rf = (math.sqrt(3) / 3 * x - y / 3) / SIZE, (2 / 3 * y) / SIZE
    sf_ = -qf - rf
    rq, rr_, rs = round(qf), round(rf), round(sf_)
    dq, dr, ds = abs(rq - qf), abs(rr_ - rf), abs(rs - sf_)
    if dq > dr and dq > ds:
        rq = -rr_ - rs
    elif dr > ds:
        rr_ = -rq - rs
    return rq, rr_



# population by hexagon on the statewide 3 km grid (market_patterns.py's grid and rule)
sf = shapefile.Reader(str(root / "census_dl/bg/cb_2020_29_bg_500k"))
fl = [f[0] for f in sf.fields[1:]]
bgs = {sr.record[fl.index("GEOID")]: shape(sr.shape.__geo_interface__) for sr in sf.iterShapeRecords()}
ids = list(bgs)
tree = STRtree([bgs[b] for b in ids])
xs = [g.bounds for g in bgs.values()]
x0, y0 = min(v[0] for v in xs) * kx, min(v[1] for v in xs) * ky
x1, y1 = max(v[2] for v in xs) * kx, max(v[3] for v in xs) * ky
hex_bg = {}
for r in range(int(y0 / (1.5 * SIZE)) - 1, int(y1 / (1.5 * SIZE)) + 2):
    for q in range(int(x0 / (math.sqrt(3) * SIZE) - r / 2) - 1, int(x1 / (math.sqrt(3) * SIZE) - r / 2) + 2):
        pt = Point(*centre_of((q, r)))
        hit = [ids[i] for i in tree.query(pt) if bgs[ids[i]].contains(pt)]
        if hit:
            hex_bg[(q, r)] = hit[0]
bg_hexes = defaultdict(list)
for c, b in hex_bg.items():
    bg_hexes[b].append(c)
cp = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_BG29.txt", dtype=str, encoding="utf-8-sig")
hex_pop = defaultdict(float)
for rr in cp.itertuples():
    # a block group holding no hexagon centre (small urban ones) goes to the hexagon of its population centre
    hs = bg_hexes.get(rr.STATEFP + rr.COUNTYFP + rr.TRACTCE + rr.BLKGRPCE) or [qr_ll(float(rr.LONGITUDE), float(rr.LATITUDE))]
    for c in hs:
        hex_pop[c] += float(rr.POPULATION) / len(hs)


def pieces(cells):
    left, out = set(cells), []
    while left:
        st = [left.pop()]; comp = {st[0]}
        while st:
            c = st.pop()
            for dq, dr in NB6:
                o = (c[0] + dq, c[1] + dr)
                if o in left:
                    left.discard(o); st.append(o); comp.add(o)
        out.append(comp)
    return out


def band(a, b):
    """the hexagons along the straight line between hexagons a and b"""
    n = hexdist(a, b)
    out = set()
    for t in range(n + 1):
        fq, fr = a[0] + (b[0] - a[0]) * t / max(n, 1), a[1] + (b[1] - a[1]) * t / max(n, 1)
        fs = -fq - fr
        rq, rr_, rs = round(fq), round(fr), round(fs)
        dq, dr, ds = abs(rq - fq), abs(rr_ - fr), abs(rs - fs)
        if dq > dr and dq > ds:
            rq = -rr_ - rs
        elif dr > ds:
            rr_ = -rq - rs
        out.add((rq, rr_))
    return out


def name_of(piece, M):
    places = defaultdict(int)
    for c in piece:
        places[M.get("hex_county", {}).get(key(c), "")] += 1
    big = [l_ for l_ in M["market"]["labels"] if any(hexdist(qr_ll(l_["lon"], l_["lat"]), c) <= 1 for c in piece)]
    if big:
        return max(big, key=lambda l_: l_["pop"])["name"]
    c_ = max(places, key=places.get)
    return f"rural {CNAME.get(c_, c_)}"


for region in sys.argv[1:] or ["columbia"]:
    cfg = json.load(open(here / "regions.json"))[region]
    R = root / cfg["out"]
    pf = here / "reach/probability_columbia.json" if region == "columbia" else R / "probability.json"
    M = json.load(open(R / "market_pattern_maps.json"))
    PR = json.load(open(pf))
    for town, ranks in PR.items():
        home = {qr(k) for k in M["home"][town]["hexes"]}
        for rank, rec in ranks.items():
            # the core from the ensemble's unrounded p (core50_hexes); p in the file is rounded
            core = {qr(k) for k in rec["core50_hexes"]} if "core50_hexes" in rec else {qr(k) for k, v in rec["p"].items() if v >= 0.5}
            ps = pieces(core)
            body = set().union(*[p_ for p_ in ps if p_ & home]) if any(p_ & home for p_ in ps) else set()
            others = [p_ for p_ in ps if not (p_ & home)]
            parts = [p_ for p_ in others if len(p_) >= 3]
            specks = [p_ for p_ in others if len(p_) <= 2]
            kept = body.union(*parts) if parts else set(body)
            dist_ = lambda p_: round(min(hexdist(x, y) for x in p_ for y in body) * SP3, 1) if body else None
            desc = lambda p_, h=False: {"name": town if h else name_of(p_, M), "home": h, "hexagons": len(p_), "km2": round(km2(p_)),
                                        "people": round(sum(hex_pop.get(c, 0) for c in p_)), "km_from_home_body": 0.0 if h else dist_(p_)}
            rec["core50_outline_unconnected"] = mapping(unary_union([Polygon(corners(c)).buffer(1e-7) for c in core]).simplify(0.0003))
            rec["core50_outline"] = mapping(unary_union([Polygon(corners(c)).buffer(1e-7) for c in kept]).simplify(0.0003))
            rec["core50_parts"] = ([desc(body, True)] if body else []) + sorted([desc(p_) for p_ in parts], key=lambda d: -d["hexagons"])
            rec["core50_part_hexes"] = {key(c): town for c in body}
            for p_ in parts:
                nm_ = name_of(p_, M)
                rec["core50_part_hexes"].update({key(c): nm_ for c in p_})
            rec["core50_specks"] = sorted([desc(p_) for p_ in specks], key=lambda d: d["km_from_home_body"] or 0)
            rec["core50_kept"] = {"hexagons": len(kept), "km2": round(km2(kept)), "people": round(sum(hex_pop.get(c, 0) for c in kept)),
                                  "unconnected_hexagons": len(core), "unconnected_km2": round(km2(core)),
                                  "unconnected_people": round(sum(hex_pop.get(c, 0) for c in core)),
                                  "rule": "the home body and every core piece of 3+ hexagons, wherever it lies; specks of 1-2 hexagons leave the outline"}
            rec.pop("core50_connected", None); rec.pop("core50_pieces", None)
            # THE TRAVEL-ONLY QA CORE, the same multi-part rule (parts of 3+ hexagons and the home body; specks out)
            core_t = {qr(k) for k in rec.get("core50_travel_hexes", [k for k, v in rec.get("p_travel", {}).items() if v >= 0.5])}
            pt_ = pieces(core_t)
            kept_t = set().union(*[p_ for p_ in pt_ if p_ & home or len(p_) >= 3]) if pt_ else set()
            rec["core50_travel_part_hexes"] = sorted(key(c) for c in kept_t)
            rec["core50_travel_kept"] = {"hexagons": len(kept_t), "km2": round(km2(kept_t)),
                                         "people": round(sum(hex_pop.get(c, 0) for c in kept_t)),
                                         "specks_dropped": sum(1 for p_ in pt_ if not (p_ & home) and len(p_) <= 2)}
            k_ = rec["core50_kept"]
            print(f"{region} {town} {rank}: kept {k_['km2']:,} km2, {k_['people']:,} people ({k_['hexagons']} hexagons) | all core "
                  f"{k_['unconnected_km2']:,} km2, {k_['unconnected_people']:,} people ({k_['unconnected_hexagons']}) | parts "
                  f"{[(d['name'], d['hexagons'], d['km2'], d['km_from_home_body'], d['people']) for d in rec['core50_parts']]} | specks "
                  f"{[(d['name'], d['hexagons'], d['km_from_home_body']) for d in rec['core50_specks']]}", flush=True)
    json.dump(PR, open(pf, "w"))
    print("wrote", pf)
