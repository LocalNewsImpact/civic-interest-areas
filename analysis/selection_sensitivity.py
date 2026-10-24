"""Sensitivity of the civic interest areas to the map's selection rule (market_pattern_print.html, mirrored by
confidence_layer.shown_set): the share of ties outside home the drawn hexagons hold (selectivity, adopted 0.5) and the
distance rule (a hexagon apart from the area's body needs a tie rising to top_mult x the base threshold at reach_in
hexagons inside the TV market, reach_out outside; adopted 2x, 4, 2).

For each variant and area (home hexagons, value 100, left out of every count and overlap, as in market_stability.py:
home is in every area by definition and would inflate the overlap):
  shown                  hexagons drawn beyond home (before the stability filter)
  shown_odd, shown_even  hexagons beyond home the same rule draws from odd months and from even months
  replicability          Jaccard of those two sets -- whether the rule picks out the same area from either half of the
                         year. REPLICABILITY, not validity: it says the area repeats, not that it is the right area
  stable                 share of shown hexagons whose tie clears the threshold in both halves
  km2, iou    the published area (stability filter, connected, smoothed) and its overlap with the adopted rule's area
Writes analysis/selection_sensitivity.csv. Usage: selection_sensitivity.py [region]"""
import csv
import runpy
import sys
from pathlib import Path

from shapely.geometry import shape

root = Path(__file__).resolve().parents[1]
region = sys.argv[1] if len(sys.argv) > 1 else "columbia"
sys.argv = ["confidence_layer.py", region]
C = runpy.run_path(str(root / "analysis/confidence_layer.py"), run_name="confidence_lib")
ns, P, MAPS = C["ns"], C["P"], C["MAPS"]
# the published areas: every area of Columbia, Mexico and Linn (market_patterns.py decides how many each has)
AREAS = [(t, m["rank"]) for t in ("Columbia", "Mexico", "Linn") for m in MAPS["towns"][t]]
VARIANTS = {
    "adopted (50%, 2x at 4 hexagons)": {},
    "selectivity 40%": {"sel": 0.4},
    "selectivity 60%": {"sel": 0.6},
    "no distance rule": {"top_mult": 1},
    "distance 1.5x": {"top_mult": 1.5},
    "distance 3x": {"top_mult": 3},
    "distance reach 2 hexagons": {"reach_in": 2, "reach_out": 1},
    "distance reach 6 hexagons": {"reach_in": 6, "reach_out": 3},
}
in_market = set(MAPS.get("in_market", []))
jac = lambda a, b: len(a & b) / max(1, len(a | b))

rows = []
for town, rank in AREAS:
    pt = next(x for x in ns["out"][town] if x["rank"] == rank)
    g_ = pt["patterns"]
    half = {s: {k: round(v, 1) for k, v in ns["tie_map"](town, C["pattern_travel"](town, g_, C["HALVES"][f"X_{s}"])).items() if v >= 1}
            for s in ("odd", "even")}
    net = next(x for x in MAPS["towns"][town] if x["rank"] == rank)["index"]["net"]
    base_geom = None
    for name, kw in VARIANTS.items():
        on, basef = C["shown_set"](net, in_market, **kw)
        on_odd, _ = C["shown_set"](half["odd"], in_market, **kw)
        on_even, _ = C["shown_set"](half["even"], in_market, **kw)
        # beyond home only (home is 100 in every map, all months and both halves)
        on = {k for k in on if net[k] < 100}
        on_odd = {k for k in on_odd if half["odd"][k] < 100}
        on_even = {k for k in on_even if half["even"][k] < 100}
        stable = sum(1 for k in on if half["odd"].get(k, 0) >= basef and half["even"].get(k, 0) >= basef)
        geom, _, km2, _ = C["outline_for"](town, rank, half, **kw)
        g = shape(geom)
        base_geom = base_geom or g
        rows.append({"area": f"{town} {'I' * rank}", "variant": name, "threshold": round(basef, 1), "shown": len(on),
                     "shown_odd": len(on_odd), "shown_even": len(on_even),
                     "replicability": round(jac(on_odd, on_even), 3), "stable": round(stable / max(1, len(on)), 3),
                     "km2": km2, "iou": round(g.intersection(base_geom).area / g.union(base_geom).area, 3)})
        print(rows[-1])
out = root / "analysis/selection_sensitivity.csv"
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
print("wrote", out)
