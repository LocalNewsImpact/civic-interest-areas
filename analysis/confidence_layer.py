"""How certain each approved revealed news market is, hexagon by hexagon: the same network tie as the approved maps
(market_patterns.py idx["net"]), computed from odd months (January, March, May, July 2026) and from even months
(February, April, June) separately, with the same pattern weights (pattern_halves.py). The map (?conf=1) draws a shown
hexagon lighter when it clears the map's floor in only one half. Nothing else on the approved map changes.
Holding in both halves is REPLICABILITY (the same area from either half of the year), not validity: it does not show
the area is the right one. The same pattern weights serve both halves, so the halves test the travel, not the fit.
Corridors (?corridors=1): the road from home to each place the approved map names as its direction, and the hexagons
it crosses (part of the market: travel along it makes crashes, closures, construction, fuel and food there information
residents need).
Writes flows/reach/confidence_<region>.json: {town: {rank: {odd, even, corridors, corridor_hexes}}}.
Usage: confidence_layer.py <region> [town ...]"""
import json
import os
import runpy
import sys
from pathlib import Path

import numpy as np

root = Path(__file__).resolve().parents[1]
region = sys.argv[1] if len(sys.argv) > 1 else "columbia"
os.environ["TIE_LIB"] = "1"
argv, sys.argv = sys.argv, ["tie_footprint.py", region]
ns = runpy.run_path(str(root / "analysis/tie_footprint.py"), run_name="tie_lib")
sys.argv = argv
P = ns["P"]
HALVES = json.load(open(ns["R"] / "patterns_halves.json"))
Wa, Ha = np.array(P["W"]), np.array(P["H"])


def pattern_travel(town, group, X):
    """market_patterns.py's attribution of the town's travel to a pattern group, from travel matrix X"""
    hbi = [P["homes"].index(h) for h in ns["town_bgs"](town) if h in P["homes"]]
    Wm, Xm = Wa[hbi], np.asarray(X)[hbi]
    den = np.maximum(Wm @ Ha, 1e-9)
    trav = sum((Xm * (Wm[:, k:k + 1] * Ha[k][None, :] / den)).sum(0) for k in group)
    trav = trav / trav.max()
    return {u: float(x) for u, x in zip(P["units"], trav) if x > 0}


# CORRIDORS (?corridors=1): the road between home and each place the approved map names as its direction (its "toward"
# towns), the fastest route on the OpenStreetMap road graph (flows/road_graph.py) -- travel there passes along it, and
# crashes, closures, construction, fuel and food on it are information residents need
sys.path.insert(0, str(root / "flows"))
import road_graph  # noqa: E402
MAPS = json.load(open(ns["R"] / "market_pattern_maps.json"))
pl_shapes, hex_place, centre = ns["pl_shapes"], ns["hex_place"], ns["centre"]
name_to_place = {}
for g_, (rec, _) in pl_shapes.items():
    name_to_place.setdefault(rec["NAME"], g_)


NB6 = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]
qr = lambda k: tuple(map(int, k.split(",")))
hexdist = lambda a, b: (abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[0] + a[1] - b[0] - b[1])) // 2


def shown_set(values, in_market, sel=0.5, floor=5, top_mult=2, reach_in=4, reach_out=2):
    """the hexagons the approved map draws (market_pattern_print.html): the 50% selectivity floor, then growth outward
    from home, each hexagon admitted at a floor that rises with its gap from the body (4 hexagons to the top inside the
    TV market, 2 outside)"""
    ext = sorted((v for v in values.values() if v < 100), reverse=True)
    tot, acc, f80 = sum(ext), 0.0, floor
    for v in ext:
        acc += v; f80 = v
        if acc >= sel * tot:
            break
    basef = max(floor, f80); topf = max(10, top_mult * basef) if top_mult > 1 else basef   # top_mult=1: no distance rule
    vals = {k: v for k, v in values.items() if v >= basef}
    on = {k for k, v in vals.items() if v >= 100} or {k for k, v in vals.items() if v >= 80}
    grew = True
    while grew:
        grew = False
        body = [qr(k) for k in on]
        for k, v in vals.items():
            if k in on:
                continue
            c = qr(k)
            d = min(hexdist(c, b) for b in body)
            gap = max(0, d - 1)
            if v >= basef + (topf - basef) * min(1, gap / (reach_in if k in in_market else reach_out)):
                on.add(k); grew = True
    return on, basef


def corridors_for(town, rank):
    """road corridors joining every separate part of the shown market (3+ hexagons) to home: the hexagons the fastest
    route from home to the part's strongest hexagon crosses outside the shown market"""
    m = next(x for x in MAPS["towns"][town] if x["rank"] == rank)
    net, home = m["index"]["net"], MAPS["home"][town]
    on, _ = shown_set(net, set(MAPS.get("in_market", [])))
    left, parts = set(on), []
    while left:
        stack = [left.pop()]; comp = {stack[0]}
        while stack:
            c = qr(stack.pop())
            for dq, dr in NB6:
                o = f"{c[0] + dq},{c[1] + dr}"
                if o in left:
                    left.discard(o); stack.append(o); comp.add(o)
        parts.append(comp)
    homes_ = {k for k in on if net.get(k, 0) >= 100}
    lines, hexes = [], set()
    for p_ in parts:
        if p_ & homes_ or len(p_) < 3:
            continue
        tgt = max(p_, key=lambda k: net.get(k, 0))
        if tgt not in centre:
            continue
        pts = road_graph.route(home["lon"], home["lat"], *centre[tgt])
        cells = [ns["hex_of"](x, y) for x, y in pts]
        new = {c for c in cells if c and c not in on}
        if pts:
            name = next((pl_shapes[hex_place[k]][0]["NAME"] for k in sorted(p_, key=lambda k: -net.get(k, 0)) if hex_place.get(k) in pl_shapes), "")
            lines.append({"toward": name, "hexes": len(new)})
            hexes |= new
    return lines, sorted(hexes), len(on)


# OUTLINE (?outline=1): the market as one connected, confident shape -- the shown hexagons that hold in both halves of
# the year (and home), joined across gaps by morphological closing at the smallest radius (2 to 8 hexagons) that makes
# them one piece, holes filled; drawn as a line around it. Every confident cell is included.
from shapely.geometry import Polygon, mapping
from shapely.ops import unary_union


def close_fill(cells, r):
    dsk = [(q, s_) for q in range(-r, r + 1) for s_ in range(-r, r + 1) if abs(q) + abs(s_) + abs(q + s_) <= 2 * r]
    dil = {(a + dq, b + dr) for a, b in cells for dq, dr in dsk}
    clo = {h for h in dil if all((h[0] + dq, h[1] + dr) in dil for dq, dr in dsk)} | set(cells)
    qs = [h[0] for h in clo]; rs = [h[1] for h in clo]
    box = {(q, r_) for q in range(min(qs) - 1, max(qs) + 2) for r_ in range(min(rs) - 1, max(rs) + 2)}
    outside, stack = set(), [(min(qs) - 1, min(rs) - 1)]
    while stack:
        h = stack.pop()
        if h in outside or h in clo or h not in box:
            continue
        outside.add(h); stack.extend((h[0] + dq, h[1] + dr) for dq, dr in NB6)
    return box - outside


def pieces(cells):
    left, out_ = set(cells), []
    while left:
        stack = [left.pop()]; comp = {stack[0]}
        while stack:
            c = stack.pop()
            for dq, dr in NB6:
                o = (c[0] + dq, c[1] + dr)
                if o in left:
                    left.discard(o); stack.append(o); comp.add(o)
        out_.append(comp)
    return out_


def outline_for(town, rank, half, **sel_kw):
    m = next(x for x in MAPS["towns"][town] if x["rank"] == rank)
    net = m["index"]["net"]
    on, basef = shown_set(net, set(MAPS.get("in_market", [])), **sel_kw)
    core = {qr(k) for k in on if net[k] >= 100 or (half["odd"].get(k, 0) >= basef and half["even"].get(k, 0) >= basef)}
    home_ = {qr(k) for k in on if net[k] >= 100}
    # small clusters count when they lie near the market: rural travel spreads over the land where destinations are and
    # rarely forms solid clusters (Mexico's north-Callaway cells: 14 of 15 hold in both halves, in pieces of 1-6). A piece
    # under 3 hexagons more than 5 hexagons from the rest is a lone far cell and is left out (it drew spikes)
    ps0 = pieces(core)
    keep_ = [p_ for p_ in ps0 if p_ & home_ or len(p_) >= 3]
    kept = set().union(*keep_) if keep_ else set()
    grew_ = True
    while grew_:
        grew_ = False
        for p_ in ps0:
            if p_ <= kept:
                continue
            if min(hexdist(a_, b_) for a_ in p_ for b_ in kept) <= 5:
                kept |= p_; grew_ = True
    core = kept
    for r in range(2, 9):
        shape_ = close_fill(core, r)
        if len(pieces(shape_)) == 1:
            break
    ps = pieces(shape_)
    if len(ps) > 1:      # still apart at 8: join each piece to the home piece by a band between their nearest hexagons
        main = max(ps, key=lambda p_: (bool(p_ & home_), len(p_)))
        for p_ in ps:
            if p_ is main or len(p_ & core) < 3:          # only pieces of 3+ confident hexagons get a band
                continue
            a_, b_ = min(((x, y) for x in p_ for y in main), key=lambda z: hexdist(*z))
            n = hexdist(a_, b_)
            for t in range(n + 1):
                q, r_ = a_[0] + (b_[0] - a_[0]) * t / max(n, 1), a_[1] + (b_[1] - a_[1]) * t / max(n, 1)
                shape_.add((round(q), round(r_)))
        shape_ = close_fill(shape_, 1)
    # a leftover piece with fewer than 3 confident cells is not part of the market: one area only
    ps = pieces(shape_)
    if len(ps) > 1:
        main = max(ps, key=lambda p_: (bool(p_ & home_), len(p_ & core)))
        shape_ = set(main)
    polys = [Polygon(MAPS["hexes"][f"{a},{b}"][:6]) for a, b in shape_ if f"{a},{b}" in MAPS["hexes"]]
    # SMOOTHED (user, 2026-10-18: the hexagon-edge outline "looks dumb"): grown about 3 km and pulled back about 2 km --
    # corners round off and one-hexagon arms become bands, so the line reads as a market area, not a network of threads
    # smoothed further (user: "it does not need to trace the bump of every hexagon"): grown about 5 km, pulled back
    # about 4.5 km, simplified at about 300 m -- the market's shape, not its cells
    geom = unary_union([p_.buffer(1e-6) for p_ in polys]).buffer(0.05, quad_segs=24).buffer(-0.045, quad_segs=24).simplify(0.003)
    return mapping(geom), r, round(len(shape_) * 5.85), len(pieces(shape_))




if __name__ == "__main__":   # imported by selection_sensitivity.py for its functions only
    out = {}
    for town in (argv[2:] or list(ns["STUDY"])):
        out[town] = {}
        for pt in ns["out"][town]:
            g_ = pt["patterns"]
            check = pattern_travel(town, g_, P["X"])
            assert max(abs(check.get(u, 0) - v) for u, v in pt["travel"].items()) < 1e-6, "attribution differs from the map's"
            half = {s: {k: round(v, 1) for k, v in ns["tie_map"](town, pattern_travel(town, g_, HALVES[f"X_{s}"])).items() if v >= 1}
                    for s in ("odd", "even")}
            lines, chex, n_on = corridors_for(town, pt["rank"])
            geom, r_used, km2, n_pieces = outline_for(town, pt["rank"], half)
            out[town][pt["rank"]] = {**half, "corridors": lines, "corridor_hexes": chex, "outline": geom,
                                     "outline_stats": {"closing_hexagons": r_used, "km2": km2, "pieces": n_pieces}}
            print(f"   outline: closed over {r_used} hexagons, {km2:,} km2, {n_pieces} piece(s)")
            print(f"{town} market {pt['rank']} toward {' and '.join(pt['toward']) or '-'}: "
                  f"{sum(v >= 5 for v in half['odd'].values())} / {sum(v >= 5 for v in half['even'].values())} hexagons of 5+ (odd / even); "
                  f"shown {n_on} hexagons; corridors to {[c['toward'] for c in lines]}, {len(chex)} hexagons added")
    dest = ns["R"] / "confidence.json" if region != "columbia" else root / "flows/reach/confidence_columbia.json"
    json.dump(out, open(dest, "w"))
    print("wrote", dest)
