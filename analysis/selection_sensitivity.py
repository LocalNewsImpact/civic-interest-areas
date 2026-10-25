"""Sensitivity of the TRAVEL-ONLY civic interest areas (the supply footprint; the published network-tie map's sensitivity
is the settings ensemble, flows/area_ensemble.py) to the map's selection rule
and to the travel tie's settings. Areas: every published area of Columbia, Mexico and Linn.

Table 1, the selection rule (market_pattern_print.html, mirrored by confidence_layer.shown_set): the share of ties outside
home the drawn hexagons hold (selectivity, adopted 0.5), the distance rule (a hexagon apart from the area's body needs a
tie rising to top_mult x the base threshold at reach_in hexagons inside the TV market, reach_out outside; adopted 2x, 4,
2) and the floor (adopted 5). Home hexagons (value 100) are left out of every count and overlap (as in
market_stability.py: home is in every draw and would inflate the overlap):
  shown                  hexagons drawn beyond home
  shown_odd, shown_even  the same from odd months and from even months, each half on its OWN fit (W and H refitted on
                         its months, matched to the kept patterns; travel_patterns.py)
  replicability          Jaccard of those two sets: whether the rule draws the same area from either half of the year.
                         REPLICABILITY, not validity: it says the area repeats, not that it is the right area
  stable                 share of shown hexagons whose tie clears the threshold in both halves
  jaccard_published      Jaccard of the shown hexagons beyond home with the published (adopted) ones
  km2, iou               the published area (stability filter, connected, smoothed; hexagons inside x 5.85 km2) and
                         its overlap with the adopted rule's area
Table 2, the tie's settings, one at a time (jaccard_published as above): TRAVEL_TOP (busiest place 50 -> 100), the
dasymetric spread of rural travel (off: every hexagon of a rural block group the same), DFLOOR (0.25 -> 0.1, 1), the
spatial lag LAMBDA (0.25 -> 0, 0.5), the direction GAMMA (0.5 -> 0, 1), the cut below which a tie is dropped (1 ->
0.5, 2), the floor (5 -> 3, 8) and the hexagon (3 km -> 2, 4 km; compared as areas: overlap of the shown hexagons'
footprints, IoU). The news weights do not enter the travel-only area.
Writes analysis/selection_sensitivity.csv and analysis/area_sensitivity.csv. Usage: selection_sensitivity.py [region]
(HEXSIZE=0 skips the 2 and 4 km grids)."""
import csv
import math
import os
import runpy
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon, shape
from shapely.ops import unary_union

root = Path(__file__).resolve().parents[1]
region = sys.argv[1] if len(sys.argv) > 1 else "columbia"
sys.argv = ["confidence_layer.py", region]
C = runpy.run_path(str(root / "analysis/confidence_layer.py"), run_name="confidence_lib")
ns, P, MAPS = C["ns"], C["P"], C["MAPS"]
G = ns["tie_map"].__globals__                      # the tie's module namespace (tie_footprint.py + market_patterns.py)
AREAS = [(t, m["rank"]) for t in ("Columbia", "Mexico", "Linn") for m in MAPS["towns"][t]]
VARIANTS = {
    "adopted (50%, 2x at 4 hexagons, floor 5)": {},
    "selectivity 40%": {"sel": 0.4},
    "selectivity 60%": {"sel": 0.6},
    "no distance rule": {"top_mult": 1},
    "distance 1.5x": {"top_mult": 1.5},
    "distance 3x": {"top_mult": 3},
    "distance reach 2 hexagons": {"reach_in": 2, "reach_out": 1},
    "distance reach 6 hexagons": {"reach_in": 6, "reach_out": 3},
    "floor 3": {"floor": 3},
    "floor 8": {"floor": 8},
}
in_market = set(MAPS.get("in_market", []))
jac = lambda a, b: len(a & b) / max(1, len(a | b))
beyond = lambda on, v: {k for k in on if v[k] < 100}
KXP, KYP = 111.32 * math.cos(math.radians(38.7)), 110.57


def footprint(hexset, hexes):
    return unary_union([Polygon([(x * KXP, y * KYP) for x, y in hexes[k][:6]]).buffer(1e-6) for k in hexset if k in hexes])


rows, rows2, published = [], [], {}
for town, rank in AREAS:
    pt = next(x for x in ns["out"][town] if x["rank"] == rank)
    g_ = pt["patterns"]
    half = C["half_ties"](town, g_, C["TRAVEL_W"])
    tv = next(x for x in MAPS["towns"][town] if x["rank"] == rank)["index"]["travel"]
    base_on = beyond(C["shown_set"](tv, in_market)[0], tv)
    published[(town, rank)] = base_on
    base_geom = None
    for name, kw in VARIANTS.items():
        on, basef = C["shown_set"](tv, in_market, **kw)
        on_odd, _ = C["shown_set"](half["odd"], in_market, **kw)
        on_even, _ = C["shown_set"](half["even"], in_market, **kw)
        on, on_odd, on_even = beyond(on, tv), beyond(on_odd, half["odd"]), beyond(on_even, half["even"])
        stable = sum(1 for k in on if half["odd"].get(k, 0) >= basef and half["even"].get(k, 0) >= basef)
        geom, _, km2, _ = C["outline_for"](town, rank, half, index="travel", **kw)
        g = shape(geom)
        base_geom = base_geom or g
        rows.append({"area": f"{town} {'I' * rank}", "variant": name, "threshold": round(basef, 1), "shown": len(on),
                     "shown_odd": len(on_odd), "shown_even": len(on_even), "replicability": round(jac(on_odd, on_even), 3),
                     "stable": round(stable / max(1, len(on)), 3), "jaccard_published": round(jac(on, base_on), 3),
                     "km2": km2, "iou": round(g.intersection(base_geom).area / g.union(base_geom).area, 3)})
        print(rows[-1], flush=True)

    # TABLE 2: the tie's settings, one at a time, on the same grid
    Hk = C["pattern_travel"](town, g_, P["X"])
    DW0 = dict(G["DW"])

    def dw_for(fl):
        out_ = {}
        for u_, ks in G["by_unit"].items():
            m_ = np.mean([G["dcount"].get(k_, 0) + fl for k_ in ks])
            for k_ in ks:
                out_[k_] = (G["dcount"].get(k_, 0) + fl) / m_
        return out_
    SETTINGS = {"TRAVEL_TOP 1.0 (busiest place 100)": {"TRAVEL_TOP": 1.0}, "no dasymetric spread": {"DW": {}},
                "DFLOOR 0.1": {"DW": dw_for(0.1)}, "DFLOOR 1": {"DW": dw_for(1.0)}, "LAMBDA 0 (no spatial lag)": {"LAMBDA": 0.0},
                "LAMBDA 0.5": {"LAMBDA": 0.5}, "GAMMA 0 (no direction)": {"GAMMA": 0.0}, "GAMMA 1": {"GAMMA": 1.0},
                "cut 0.5": {"cut": 0.5}, "cut 2": {"cut": 2.0}, "floor 3": {"floor": 3}, "floor 8": {"floor": 8}}
    for name, kw in SETTINGS.items():
        saved = {k: G[k] for k in ("TRAVEL_TOP", "LAMBDA", "GAMMA")}
        for k in ("TRAVEL_TOP", "LAMBDA", "GAMMA"):
            if k in kw:
                G[k] = kw[k]
        if "DW" in kw:
            G["DW"].clear(); G["DW"].update(kw["DW"])
        t = {k: round(v, 1) for k, v in G["tie_map"](town, Hk, C["TRAVEL_W"]).items() if v >= kw.get("cut", 1)}
        on, bf = C["shown_set"](t, in_market, **({"floor": kw["floor"]} if "floor" in kw else {}))
        on = beyond(on, t)
        rows2.append({"area": f"{town} {'I' * rank}", "setting": name, "shown": len(on), "threshold": round(bf, 1),
                      "jaccard_published": round(jac(on, base_on), 3), "published_shown": len(base_on)})
        print(rows2[-1], flush=True)
        G.update(saved); G["DW"].clear(); G["DW"].update(DW0)

# HEXAGON SIZE: the whole grid rebuilt at 2 and 4 km (market_patterns.py HEX_KM), the same travel; compared as areas
if os.environ.get("HEXSIZE", "1") == "1":
    for hk in ("2", "4"):
        os.environ["HEX_KM"], os.environ["TIE_LIB"] = hk, "1"
        sys.argv = ["tie_footprint.py", region]
        N = runpy.run_path(str(root / "analysis/tie_footprint.py"), run_name="tie_lib")
        im = {k for k, c in N["hex_county"].items() if c in N["CFG"]["dma_counties"]}
        for town, rank in AREAS:
            pt = next(x for x in ns["out"][town] if x["rank"] == rank)
            t = {k: round(v, 1) for k, v in N["tie_map"](town, C["pattern_travel"](town, pt["patterns"], P["X"]), C["TRAVEL_W"]).items() if v >= 1}
            on = beyond(C["shown_set"](t, im)[0], t)
            a, b = footprint(on, N["hexes"]), footprint(published[(town, rank)], MAPS["hexes"])
            rows2.append({"area": f"{town} {'I' * rank}", "setting": f"hexagon {hk} km (area IoU)", "shown": len(on), "threshold": "",
                          "jaccard_published": round(a.intersection(b).area / a.union(b).area, 3),
                          "published_shown": len(published[(town, rank)])})
            print(rows2[-1], flush=True)
    os.environ.pop("HEX_KM", None)
for path_, rs in ((root / "analysis/selection_sensitivity.csv", rows), (root / "analysis/area_sensitivity.csv", rows2)):
    with open(path_, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rs[0]))
        w.writeheader(); w.writerows(rs)
    print("wrote", path_)
