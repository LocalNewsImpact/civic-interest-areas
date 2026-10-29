"""The civic interest area as the core of an ensemble of plausible drawing settings (authors, 2026-10-24 and
2026-10-25). The adopted drawing moved by more than half under hexagon size, busiest-place scaling and
the dasymetric spread (analysis/area_sensitivity.csv), so each area is drawn under every combination of the settings
below and each published 3 km hexagon is given p = the share of members that draw it -- in published text its
"likelihood" of being part of the area: a probability under equal weighting of the members, conditional on their range.
THE AREA = THE CORE, p >= 0.5 (p >= 0.8 also reported), kept as parts by flows/area_core.py (run after this script:
the home body and every core piece of 3+ hexagons whose nearest hexagon lies within the town's D90; specks of 1-2
hexagons leave the outline). No single-setting map is produced.

Ties: the NETWORK TIE (market_patterns.py idx["net"], the paper's map) and, with the same members, TRAVEL ONLY (no news
term; the supply QA footprint, p_travel). Same K, patterns, data and news weights in every member; only the drawing
changes. FULL FACTORIAL, 6,912 members:
  hexagon size        2, 3, 4 km (the whole grid rebuilt: market_patterns.py HEX_KM)                       3
  TRAVEL_TOP          0.5 (adopted: busiest place 50), 1.0 (busiest place 100)                               2
  dasymetric spread   off, DFLOOR 0.1, 0.25 (adopted), 1 -- rural block groups AND towns of 2+ hexagons       4
  LAMBDA              0, 0.25 (adopted), 0.5 (spatial lag, its rings in km)                                   3
  selectivity         40, 50 (adopted), 60% (share of ties outside home the drawn hexagons hold)              3
  distance rule       on (adopted: the floor rises to 2x over 10.4 km inside the TV market, 5.2 km outside), off 2
  reach               10, 15 (adopted), 25 km: drawn pieces joined to the area's body when within this
                      distance of it (pieces holding home seed the body; grown outward); D90 (authors, 2026-10-25,
                      replaces "none"): every drawn piece whose nearest hexagon lies within the town's
                      regular-travel distance D90 of its centre of population (flows/regular_distance.py)      4
  news weight         x0 (travel only), x0.5, x1 (adopted), x2: all four news weights of the network tie (out 0.3,
                      in 0.3, shared places 0.7, shared coverage 0.7) multiplied together (authors, 2026-10-25) 4
The 1,728 versions of the seven other choices at news weight x1 are reported beside the whole ensemble
(news_weight_levels: each level's core, month-split stability and mean |p_level - p|).
A full factorial weights every level of every factor equally, so the uniform weighting IS the marginal-balanced one;
the script checks that the two give the same p. Held at the adopted values: GAMMA 0.5, the tie cut 1, the floor 5
(never binding), the news weights. Distances are in km on every grid (rings, distance rule, reach).
DISTANT TIES: pieces drawn beyond the reach are not part of the area; they are reported separately (the share of
members drawing each, named by its largest town).
Members are mapped onto the published 3 km grid by FRACTIONAL OVERLAP: a 3 km hexagon takes the fraction of its area
under the member's drawn hexagons (on the km plane, x = lon x 111.32 cos 38.7, y = lat x 110.57); p = the mean
fraction over members. km2 on the ground: 5.85 x cos(latitude) / cos(38.7) per hexagon (the plane is scaled at 38.7 N).
People inside = 2020 population of the hexagons (each block group's population over the hexagons whose centres lie in
it), split by p band, and into the home town, the other towns of 2,500+ the area takes in, and the rest.
MONTH-SPLIT STABILITY (not validity; K was selected on the same odd/even split): the whole network-tie ensemble on each
half of the year, each half on its own fit (W and H refitted on odd or even months on disjoint seeds, matched to the
kept patterns) and its travel: the correlation of p between halves over every hexagon drawn in either and over the
CONTESTED ones (0.1 <= p <= 0.9), the mean |p_odd - p_even|, and the Jaccard of the two cores (home left out).
Home is flagged explicitly (home_hexes_of), never read from a tie of 100 (destinations are capped at 99).
Writes <region out>/probability.json (Columbia: flows/reach/probability_columbia.json).
Usage: area_ensemble.py [columbia] [all]   (default: the built towns Columbia, Mexico, Linn; all = every study town of the market)"""
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
from shapely.geometry import Polygon, mapping
from shapely.ops import unary_union

here = Path(__file__).resolve().parent
root = here.parent
region = sys.argv[1] if len(sys.argv) > 1 else "columbia"
ALL = len(sys.argv) > 2 and sys.argv[2] == "all"
# SENSITIVITIES of the constants held fixed in every version; none writes over the adopted ensemble:
#   BUSIEST=hexagon   the busiest hexagon = 50 instead of the busiest place (market_patterns.norm_hex)
#   TIE_W=o,i,p,q     the four news-tie weights (adopted 0.3,0.3,0.7,0.7: out, in, shared places, shared coverage)
#   GAMMA=g           the strength of the direction boost (adopted 0.5)
TIE_W = tuple(float(x) for x in os.environ["TIE_W"].split(",")) if os.environ.get("TIE_W") else None
GAMMA_S = float(os.environ["GAMMA"]) if os.environ.get("GAMMA") else None
SENS = os.environ.get("BUSIEST", "place") == "hexagon" or TIE_W is not None or GAMMA_S is not None
if SENS and (not (os.environ.get("OUT") or os.environ.get("SMOKE")) or Path(os.environ.get("SMOKE") or os.environ["OUT"]).name
             in ("probability_columbia.json", "probability.json")):
    raise SystemExit("a sensitivity: set OUT to a separate file; the adopted ensemble is not overwritten")


def held_constants(G):
    """apply a sensitivity's tie weights and direction strength to a loaded grid's namespace"""
    if TIE_W is not None:
        G["BASE_W"] = TIE_W
    if GAMMA_S is not None:
        G["GAMMA"] = GAMMA_S
    return G
os.environ.pop("HEX_KM", None)
sys.argv = ["confidence_layer.py", region]
C = runpy.run_path(str(root / "analysis/confidence_layer.py"), run_name="confidence_lib")
ns, P, MAPS, HALVES = C["ns"], C["P"], C["MAPS"], C["HALVES"]
G3 = held_constants(ns["tie_map"].__globals__)
BUILT = {"columbia": ("Columbia", "Mexico", "Linn")}     # the Columbia-Jefferson City TV market only
towns = list(MAPS["towns"]) if ALL else list(BUILT.get(region, ()))
if os.environ.get("TOWNS"):                # one process per subset of towns (merged afterwards; the members are the same)
    towns = [t for t in towns if t in os.environ["TOWNS"].split(",")]
AREAS = [(t, m["rank"]) for t in towns for m in MAPS["towns"][t]]
if not AREAS:
    raise SystemExit(f"{region}: no built town (pass 'all' for every study town)")
HEX_KMS, TOPS, DWS, LAMS, SELS, DISTS, REACHES = (2, 3, 4), (0.5, 1.0), (None, 0.1, 0.25, 1.0), (0.0, 0.25, 0.5), \
    (0.4, 0.5, 0.6), ("on", "off"), (10, 15, 25, "D90")
NEWS = (0.0, 0.5, 1.0, 2.0)
if os.environ.get("SMOKE"):                 # a code check on a reduced design; writes to the scratch path given in SMOKE
    HEX_KMS, TOPS, DWS, LAMS, SELS, DISTS, REACHES = (3, 4), (0.5,), (0.25,), (0.25,), (0.5,), ("on",), (15, "D90")
    NEWS = (0.0, 1.0)
LEVELS = {"hexagon_km": HEX_KMS, "TRAVEL_TOP": TOPS, "dasymetric": DWS, "LAMBDA": LAMS, "selectivity": SELS,
          "distance_rule": DISTS, "reach_km": REACHES, "news_weight": NEWS}
MEMBERS = int(np.prod([len(v) for v in LEVELS.values()]))
W_MEMBER = 1.0 / MEMBERS          # marginal-balanced: prod over factors of 1 / levels -- equal for every member here
ADOPTED = (3, 0.5, 0.25, 0.25, 0.5, "on", 15, 1.0)
KXP, KYP = 111.32 * math.cos(math.radians(38.7)), 110.57
SP3 = math.sqrt(3) * 1.5                                   # centre spacing of the 3 km grid, km
NB6 = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]
hexdist = lambda a, b: (abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[0] + a[1] - b[0] - b[1])) // 2
qr = lambda k: tuple(map(int, k.split(",")))

# the published 3 km grid on the km plane, for mapping other grids onto it
ids3 = list(G3["hexes"])
poly3 = np.array([Polygon([(x * KXP, y * KYP) for x, y in G3["hexes"][k][:6]]) for k in ids3])
area3 = shapely.area(poly3)
tree3 = shapely.STRtree(poly3)
lat3 = {k: sum(c[1] for c in G3["hexes"][k][:6]) / 6 for k in ids3}
HEX_KM2 = MAPS.get("hex_km2", 5.846)
km2_of = lambda hs: sum(HEX_KM2 * math.cos(math.radians(lat3[k])) / math.cos(math.radians(38.7)) for k in hs if k in lat3)

# population by 3 km hexagon (as area_coverage_alignment.py)
bg_hexes = defaultdict(list)
for k, b in G3["hex_bg"].items():
    bg_hexes[b].append(k)
cp = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_BG29.txt", dtype=str, encoding="utf-8-sig")
hex_pop = defaultdict(float)
for r in cp.itertuples():
    g_ = r.STATEFP + r.COUNTYFP + r.TRACTCE + r.BLKGRPCE
    h0 = G3["hex_of"](float(r.LONGITUDE), float(r.LATITUDE))
    hs = bg_hexes.get(g_) or ([h0] if h0 else [])
    for k in hs:
        hex_pop[k] += float(r.POPULATION) / len(hs)


def onto3(drawn, hexes):
    """the fraction of each published 3 km hexagon's area under the drawn hexagons of another grid"""
    if not drawn:
        return {}
    u = unary_union([Polygon([(x * KXP, y * KYP) for x, y in hexes[k][:6]]) for k in drawn if k in hexes]).buffer(1e-6)
    cand = tree3.query(u)
    frac = shapely.area(shapely.intersection(poly3[cand], u)) / area3[cand]
    return {ids3[i]: float(min(1.0, f)) for i, f in zip(cand, frac) if f > 0.001}


def shown_fast(values, in_market, home, sel, top_mult, reach_in, reach_out, floor=5):
    """confidence_layer.shown_set -- the same least fixed point -- with distances to the body by lattice search"""
    ext = sorted((v for k, v in values.items() if k not in home), reverse=True)
    tot, acc_, f80 = sum(ext), 0.0, floor
    for v in ext:
        acc_ += v; f80 = v
        if acc_ >= sel * tot:
            break
    basef = max(floor, f80); topf = max(10, top_mult * basef) if top_mult > 1 else basef
    vals = {k: v for k, v in values.items() if v >= basef}
    on = {k for k in vals if k in home} or {k for k, v in vals.items() if v >= 80}
    if topf <= basef:
        return set(vals), basef              # no distance rule: every hexagon over the floor joins (as shown_set)
    L = int(math.ceil(max(reach_in, reach_out))) + 1
    while True:
        dist = {qr(k): 0 for k in on}
        frontier = list(dist)
        for d in range(1, L + 1):
            nxt = []
            for c in frontier:
                for dq, dr in NB6:
                    o = (c[0] + dq, c[1] + dr)
                    if o not in dist:
                        dist[o] = d; nxt.append(o)
            frontier = nxt
        add = set()
        for k, v in vals.items():
            if k in on:
                continue
            gap = max(0, dist.get(qr(k), L + 1) - 1)
            if v >= basef + (topf - basef) * min(1, gap / (reach_in if k in in_market else reach_out)):
                add.add(k)
        if not add:
            return on, basef
        on |= add


def pieces_of(cells):
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
    return ps


DREG = json.load(open(here / "regular_distance.json"))      # D90 per town, km from its centre of population


def km_from(hexes, lon0, lat0):
    """km from (lon0, lat0) to every hexagon's centre (the mean of its corners), great circle"""
    out_ = {}
    for k, cs in hexes.items():
        lo, la = sum(c[0] for c in cs[:6]) / 6, sum(c[1] for c in cs[:6]) / 6
        a = math.sin(math.radians(la - lat0) / 2) ** 2 + math.cos(math.radians(la)) * math.cos(math.radians(lat0)) * math.sin(math.radians(lo - lon0) / 2) ** 2
        out_[k] = 6371.0 * 2 * math.asin(math.sqrt(a))
    return out_


def body(on, home, reach_hex, dkm=None, dmax=None):
    """the pieces holding home, and every piece within reach_hex of them, grown outward; or, with reach_hex None,
    every piece whose nearest hexagon lies within dmax km of the town's centre (dkm: km by hexagon) -- the D90 level;
    returns (body, distant pieces)"""
    ps = pieces_of({qr(k) for k in on})
    hq = {qr(k) for k in home}
    if reach_hex is None:
        kept, rest = set(), []
        for p_ in ps:
            if p_ & hq or min(dkm.get(f"{a},{b}", 1e9) for a, b in p_) <= dmax:
                kept |= p_
            else:
                rest.append(p_)
        return {f"{a},{b}" for a, b in kept}, [{f"{a},{b}" for a, b in p_} for p_ in rest]
    kept = set().union(*[p_ for p_ in ps if p_ & hq]) if hq else set()
    rest = [p_ for p_ in ps if not (p_ & hq)]
    grew = True
    while grew and kept and rest:
        grew = False
        for p_ in list(rest):
            if min(hexdist(a_, b_) for a_ in p_ for b_ in kept) <= reach_hex:
                kept |= p_; rest.remove(p_); grew = True
    return {f"{a},{b}" for a, b in kept}, [{f"{a},{b}" for a, b in p_} for p_ in rest]


def piece_name(G, piece):
    """a distant piece's name: its largest town of 2,500+, else its county"""
    towns_ = {G["hex_place"][k] for k in piece if G["hex_place"].get(k) and G["POP"].get(G["hex_place"][k], 0) >= 2500}
    if towns_:
        return G["pl_shapes"][max(towns_, key=lambda pl: G["POP"][pl])][0]["NAME"]
    cs = [G["hex_county"].get(k, "") for k in piece]
    c = max(set(cs), key=cs.count)
    return "rural " + G["cname"].get(c, c)


def amps(G, town, Hk):
    """the network tie's amplification by hexagon (network_tie.tie_map's terms, BASE_W), which no drawing setting
    changes -- computed once per grid, town and travel input"""
    cu = G["COV"][town]
    own_u = {G["P"]["bg_unit"].get(h) for h in G["town_bgs"](town)} | {G["HOME_PLACE"][town]}
    OV = {X: G["overlap_of"](Hk, own_u, X) for X in G["place_outlets"] if X not in own_u}
    h_cov = G["cov_dist"]([o for o, al in G["by_outlet"].items() if G["home_of"](al[0]) == G["STUDY"][town] and o not in G["EXCLUDE"]])
    mkt = {u_ for u_, w in Hk.items() if w >= 0.05}
    inm_ = lambda d_: {u_: w for u_, w in d_.items() if u_ in mkt}
    SC = {X: G["overlap_dists"](inm_(h_cov), inm_(G["cov_dist"](G["place_outlets"][X])), own_u | {X})
          for X in G["place_outlets"] if X not in own_u}
    wo, wi, wv, wc = G["BASE_W"]
    out_ = {}
    for k, u in G["unit_at"].items():
        if Hk.get(u, 0) <= 0:
            continue
        xk = G["hex_place"].get(k) or u
        o_, i_ = cu["out"].get(k, 0), cu["in"].get(k, 0)
        gate = 1.0 if (o_ + i_) >= 0.10 else 0.0
        out_[k] = (u, 1 + wo * o_ + wi * i_ + gate * (wv * OV.get(xk, 0) + wc * SC.get(xk, 0)))
    return out_


def tie(G, town, Hk, amp, news, nw=1.0):
    """the tie (network or travel only) under G's current TRAVEL_TOP, DW, LAMBDA: network_tie.tie_map, cached terms;
    nw multiplies all four news weights (the amplification less 1)"""
    top, DW, DC = G["TRAVEL_TOP"], G["DW"], G["DCAP"]
    Hk = G["norm_hex"](Hk)                   # busiest hexagon = 1 under this member's spread
    raw = {}
    for k, (u, a) in amp.items():
        t_ = min(DC, top * Hk[u] * DW.get(k, 1.0))
        if t_ > 0:
            raw[k] = min(DC, t_ * (1 + nw * (a - 1))) if news else t_
    if raw:
        raw = G["spatial"](raw, G["home_hexes_of"][town])
    out_ = {k: round(100 * x, 1) for k, x in raw.items() if 100 * x >= 1}
    for k in G["home_hexes_of"][town]:
        out_[k] = 100.0
    return out_


# travel inputs: the full fit and each half's own fit (grid-independent)
travel_in = {}
for town, rank in AREAS:
    g_ = next(x for x in ns["out"][town] if x["rank"] == rank)["patterns"]
    travel_in[(town, rank)] = {"all": C["pattern_travel"](town, g_, P["X"]),
                               **{s: C["pattern_travel"](town, g_, HALVES[f"X_{s}"], HALVES[f"W_{s}"], HALVES[f"H_{s}"]) for s in ("odd", "even")}}
RUNS = [("net", "all"), ("net", "odd"), ("net", "even"), ("travel", "all")]
acc = {a: {r_: defaultdict(float) for r_ in RUNS} for a in AREAS}
accw = {a: {(s, nw): defaultdict(float) for s in ("all", "odd", "even") for nw in NEWS} for a in AREAS}   # by news weight
wacc = {a: defaultdict(float) for a in AREAS}                 # marginal-balanced weighting, network tie, all months
distant = {a: defaultdict(float) for a in AREAS}
drawn_any = {a: defaultdict(float) for a in AREAS}            # share of members drawing a town anywhere (area or apart)
drawn_body = {a: defaultdict(float) for a in AREAS}           # ... inside the member's area
drawn_half = {a: {s: defaultdict(float) for s in ("odd", "even")} for a in AREAS}   # ... by half year, for the area's month split
adopted = {}
for hk in HEX_KMS:
    if hk == 3:
        G = G3
    else:
        os.environ["HEX_KM"] = str(hk)
        sys.argv = ["network_tie.py", region]
        G = held_constants(runpy.run_path(str(root / "analysis/network_tie.py"), run_name="tie_lib")["tie_map"].__globals__)
        os.environ.pop("HEX_KM", None)
    sp = math.sqrt(3) * hk / 2                                # this grid's centre spacing, km
    r_in, r_out = 4 * SP3 / sp, 2 * SP3 / sp                  # the distance rule in km
    in_market = {k for k, c in G["hex_county"].items() if c in G["CFG"]["dma_counties"]}
    # the towns of 2,500+ (and the study towns) by hexagon on this grid, for where each member draws
    TOWN_OF = {k: G["pl_shapes"][pl][0]["NAME"] for k, pl in G["hex_place"].items()
               if pl in G["pl_shapes"] and (G["POP"].get(pl, 0) >= 2500 or pl in G["HOME_PLACE"].values())}
    AMP = {(a, s): amps(G, a[0], travel_in[a][s]) for a in AREAS for s in ("all", "odd", "even")}
    DKM = {t_: km_from(G["hexes"], *DREG[t_]["centre"]) for t_ in {a[0] for a in AREAS}}
    DW0, saved = dict(G["DW"]), {k: G[k] for k in ("TRAVEL_TOP", "LAMBDA")}
    for top, dw, lam in itertools.product(TOPS, DWS, LAMS):
        G["TRAVEL_TOP"], G["LAMBDA"] = top, lam
        G["DW"].clear(); G["DW"].update(G["dasymetric"](dw))
        for a in AREAS:
            home = G["home_hexes_of"][a[0]]
            for kind, s in RUNS:
              for nw in (NEWS if kind == "net" else (0.0,)):
                t = tie(G, a[0], travel_in[a][s], AMP[(a, s)], kind == "net", nw)
                for sel, dist in itertools.product(SELS, DISTS):
                    on, _ = shown_fast(t, in_market, home, sel, 2 if dist == "on" else 1, r_in, r_out)
                    for reach in REACHES:
                        b, far = (body(on, home, None, DKM[a[0]], DREG[a[0]]["D90"]) if reach == "D90"
                                  else body(on, home, reach / sp))
                        fr = {k: 1.0 for k in b} if hk == 3 else onto3(b, G["hexes"])
                        for k, f in fr.items():
                            acc[a][(kind, s)][k] += f
                        if kind == "net":
                            for k, f in fr.items():
                                accw[a][(s, nw)][k] += f
                            if s != "all":                                            # the town rule, by half year
                                for n_ in {TOWN_OF[k] for k in b if k in TOWN_OF}:
                                    drawn_half[a][s][n_] += 1.0 / MEMBERS
                        if (kind, s) == ("net", "all"):
                            for k, f in fr.items():
                                wacc[a][k] += W_MEMBER * f
                            for n_ in {piece_name(G, p_) for p_ in far if len(p_) >= 2}:   # once per member
                                distant[a][n_] += 1.0 / MEMBERS
                            for n_ in {TOWN_OF[k] for k in on if k in TOWN_OF}:            # drawn anywhere
                                drawn_any[a][n_] += 1.0 / MEMBERS
                            for n_ in {TOWN_OF[k] for k in b if k in TOWN_OF}:             # inside the area
                                drawn_body[a][n_] += 1.0 / MEMBERS
                            if (hk, top, dw, lam, sel, dist, reach, nw) == ADOPTED:
                                adopted[a] = b
        print(f"hexagon {hk} km, TRAVEL_TOP {top}, dasymetric {dw}, LAMBDA {lam}: done", flush=True)
    G.update(saved); G["DW"].clear(); G["DW"].update(DW0)

R = root / json.load(open(here / "regions.json"))[region]["out"]
out_path = here / "reach/probability_columbia.json" if region == "columbia" else R / "probability.json"
if os.environ.get("SMOKE") or os.environ.get("OUT"):
    out_path = Path(os.environ.get("SMOKE") or os.environ["OUT"])
out = {}
jac = lambda a, b: len(a & b) / max(1, len(a | b))
POP = G3["POP"]
TOWN_HEX3 = defaultdict(list)                                 # the 3 km hexagons of each town
for k, pl in G3["hex_place"].items():
    if pl in G3["pl_shapes"]:
        TOWN_HEX3[G3["pl_shapes"][pl][0]["NAME"]].append(k)


def outline_of(hs):
    if not hs:
        return None
    return mapping(unary_union([Polygon(G3["hexes"][k][:6]).buffer(1e-7) for k in hs]).simplify(0.0005))


def people_split(hs, town):
    home = G3["home_hexes_of"][town]
    by_town, home_p, rest = defaultdict(float), 0.0, 0.0
    for k in hs:
        pl = G3["hex_place"].get(k)
        if k in home:
            home_p += hex_pop.get(k, 0)
        elif pl and POP.get(pl, 0) >= 2500:
            by_town[G3["pl_shapes"][pl][0]["NAME"]] += hex_pop.get(k, 0)
        else:
            rest += hex_pop.get(k, 0)
    return {"home_town": round(home_p), "other_towns": {t_: round(v) for t_, v in sorted(by_town.items(), key=lambda z: -z[1]) if v >= 1},
            "rest": round(rest)}


for (town, rank) in AREAS:
    a = (town, rank)
    M7 = MEMBERS // len(NEWS)                     # the versions of the seven other choices (1,728)
    p = {r_: {k: v / (MEMBERS if r_[0] == "net" else M7) for k, v in acc[a][r_].items()} for r_ in RUNS}
    pl_ = {key_: {k: v / M7 for k, v in d_.items()} for key_, d_ in accw[a].items()}
    pw = dict(wacc[a])
    assert max(abs(pw.get(k, 0) - p[("net", "all")].get(k, 0)) for k in set(pw) | set(p[("net", "all")])) < 1e-9, \
        "the marginal-balanced weighting differs from the uniform one"
    home = G3["home_hexes_of"][town]
    pa, pt_ = p[("net", "all")], p[("travel", "all")]
    core = {c: {k for k, v in pa.items() if v >= c} for c in (0.5, 0.8)}
    core_t = {k for k, v in pt_.items() if v >= 0.5}
    band = {"0.5-0.8": core[0.5] - core[0.8], ">=0.8": core[0.8]}
    halves = {s: {k for k, v in p[("net", s)].items() if v >= 0.5} - home for s in ("odd", "even")}
    keys = sorted((set(p[("net", "odd")]) | set(p[("net", "even")])) - home)
    po = np.array([p[("net", "odd")].get(k, 0) for k in keys]); pe = np.array([p[("net", "even")].get(k, 0) for k in keys])
    contested = [i for i, k in enumerate(keys) if 0.1 <= pa.get(k, 0) <= 0.9]
    r_all = float(np.corrcoef(po, pe)[0, 1]) if len(keys) > 2 else float("nan")
    r_con = float(np.corrcoef(po[contested], pe[contested])[0, 1]) if len(contested) > 2 else float("nan")
    ad = adopted[a]
    _net = next(x for x in MAPS["towns"][town] if x["rank"] == rank)["index"]["net"]
    pub, _ = shown_fast(_net, set(MAPS.get("in_market", [])), home, 0.5, 2, 4, 2)
    pub, _ = body(pub, home, 15 / SP3)
    print(f"{town} {rank}: adopted member vs the published map, Jaccard {jac(ad, pub):.3f}")
    # the published map is drawn with the busiest place = 50; under BUSIEST=hexagon the adopted member differs by design
    assert os.environ.get("SMOKE") or SENS or jac(ad, pub) >= 0.98, f"{town} {rank}: the adopted member differs from the published map"
    hc = G3["hex_county"]
    rec = {"members": MEMBERS, "design": {**{k: [str(x) for x in v] for k, v in LEVELS.items()}, "factorial": True,
                                          "adopted": [str(x) for x in ADOPTED]},
           "p": {k: round(v, 4) for k, v in sorted(pa.items()) if v >= 0.0001},
           "core50_hexes": sorted(core[0.5]), "core80_hexes": sorted(core[0.8]), "core50_travel_hexes": sorted(core_t),
           "towns_drawn": {n_: {"any": round(v, 3), "in_area": round(drawn_body[a].get(n_, 0), 3),
                                "max_p": round(max((pa.get(k, 0) for k in TOWN_HEX3.get(n_, [])), default=0), 3)}
                           for n_, v in sorted(drawn_any[a].items(), key=lambda z: -z[1]) if v >= 0.2},
           # DRAWN OFTEN, NOT IN THE AREA: towns drawn in half or more of the versions with no hexagon at p >= 0.5. A town
           # counts toward p only where it falls inside a version's area (within that version's reach of the body), and
           # versions draw different hexagons of it (grid size, spread), so its hexagons can each stay under 0.5
           "drawn_often_outside_area": sorted(n_ for n_, v in drawn_any[a].items()
                                              if v >= 0.5 and max((pa.get(k, 0) for k in TOWN_HEX3.get(n_, [])), default=0) < 0.5),
           "towns_in_area_halves": {s: {n_: round(v, 3) for n_, v in drawn_half[a][s].items() if v >= 0.2} for s in ("odd", "even")},
           "p_odd": {k: round(v, 4) for k, v in sorted(p[("net", "odd")].items()) if v >= 0.001},
           "p_even": {k: round(v, 4) for k, v in sorted(p[("net", "even")].items()) if v >= 0.001},
           "p_travel": {k: round(v, 4) for k, v in sorted(pt_.items()) if v >= 0.0001},
           "core50_hexagons": len(core[0.5]), "core80_hexagons": len(core[0.8]),
           "core50_km2": round(km2_of(core[0.5])), "core80_km2": round(km2_of(core[0.8])),
           "people_by_band": {b_: round(sum(hex_pop.get(k, 0) for k in hs)) for b_, hs in band.items()},
           "people50": round(sum(hex_pop.get(k, 0) for k in core[0.5])),
           "people50_split": people_split(core[0.5], town),
           "core50_outline": outline_of(core[0.5]), "core50_travel_outline": outline_of(core_t),
           "core50_travel_hexagons": len(core_t), "core50_travel_km2": round(km2_of(core_t)),
           "net_vs_travel_core": {"net_only": len(core[0.5] - core_t), "travel_only": len(core_t - core[0.5]),
                                  "both": len(core[0.5] & core_t), "jaccard": round(jac(core[0.5], core_t), 3)},
           "adopted_hexagons": len(ad), "adopted_in_core50": round(len(ad & core[0.5]) / max(1, len(ad)), 3),
           "distant_ties": {n_: round(v, 3) for n_, v in sorted(distant[a].items(), key=lambda z: -z[1]) if v >= 0.02},
           "boone_hexagons": {"p>=0.2": sum(1 for k, v in pa.items() if v >= 0.2 and hc.get(k) == "29019"),
                              "p>=0.5": sum(1 for k in core[0.5] if hc.get(k) == "29019"),
                              "p>=0.8": sum(1 for k in core[0.8] if hc.get(k) == "29019"),
                              "adopted": sum(1 for k in ad if hc.get(k) == "29019")},
           "month_split_stability": {"r_all": round(r_all, 3), "r_contested": round(r_con, 3), "contested_hexagons": len(contested),
                                     "mean_abs_diff": round(float(np.mean(np.abs(po - pe))), 3) if keys else None,
                                     "jaccard_core50": round(jac(halves["odd"], halves["even"]), 3),
                                     "core50_odd_even": [len(halves["odd"]), len(halves["even"])],
                                     "note": "K was selected on the same odd/even split; not an independent test"}}
    # THE NEWS-WEIGHT FACTOR ALONE: each level's p over the 1,728 versions of the other choices, its core (p >= 0.5),
    # its month-split stability, and mean |p_level - p| over the hexagons either draws (home left out)
    def split_(po_, pe_):
        ks = sorted((set(po_) | set(pe_)) - home)
        a_, b_ = np.array([po_.get(k, 0) for k in ks]), np.array([pe_.get(k, 0) for k in ks])
        con = [i for i, k in enumerate(ks) if 0.1 <= pa.get(k, 0) <= 0.9]
        ho, he = {k for k, v in po_.items() if v >= 0.5} - home, {k for k, v in pe_.items() if v >= 0.5} - home
        return {"r_all": round(float(np.corrcoef(a_, b_)[0, 1]), 3), "r_contested": round(float(np.corrcoef(a_[con], b_[con])[0, 1]), 3),
                "mean_abs_diff": round(float(np.mean(np.abs(a_ - b_))), 3), "jaccard_core50": round(jac(ho, he), 3)}
    rec["news_weight_levels"] = {}
    for nw in NEWS:
        pn = pl_[("all", nw)]
        ks = sorted((set(pn) | set(pa)) - home)
        c50 = {k for k, v in pn.items() if v >= 0.5}
        rec["news_weight_levels"][str(nw)] = {
            "versions": M7, "core50_hexes": sorted(c50), "core50_km2": round(km2_of(c50)),
            "people50": round(sum(hex_pop.get(k, 0) for k in c50)),
            "mean_abs_diff_vs_all": round(float(np.mean([abs(pn.get(k, 0) - pa.get(k, 0)) for k in ks])), 4),
            "max_abs_diff_vs_all": round(float(max(abs(pn.get(k, 0) - pa.get(k, 0)) for k in ks)), 3),
            "jaccard_core50_vs_all": round(jac(c50 - home, core[0.5] - home), 3),
            "month_split_stability": split_(pl_[("odd", nw)], pl_[("even", nw)])}
    out.setdefault(town, {})[str(rank)] = rec
    print(f"{town} {rank}: news-weight levels " + "; ".join(
        f"x{k_}: core {v_['core50_km2']:,} km2, mean |dp| {v_['mean_abs_diff_vs_all']}, core Jaccard vs all {v_['jaccard_core50_vs_all']}, "
        f"month split {v_['month_split_stability']}" for k_, v_ in rec["news_weight_levels"].items()), flush=True)
    print(f"{town} {rank}: {MEMBERS} members (full factorial); core p>=0.5 {rec['core50_km2']:,} km2, {rec['people50']:,} people "
          f"(by band {rec['people_by_band']}; {rec['people50_split']}); p>=0.8 {rec['core80_km2']:,} km2; travel-only core "
          f"{rec['core50_travel_km2']:,} km2, vs network {rec['net_vs_travel_core']}; adopted drawing {len(ad)} hexagons, "
          f"{rec['adopted_in_core50']:.0%} in the core; distant ties {rec['distant_ties']}; drawn often but outside the area "
          f"{rec['drawn_often_outside_area']}; Boone hexagons {rec['boone_hexagons']}; "
          f"month-split stability {rec['month_split_stability']}", flush=True)
json.dump(out, open(out_path, "w"))
print("wrote", out_path)
