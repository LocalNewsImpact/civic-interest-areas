"""How much evidence each hexagon on an information needs map rests on. For every market of a region: the hexagons
drawn (the approved selection, then the stability filter -- inside the connected area that holds in both halves of
the year), and for each the residents' worth of travel behind it: the market's residents x the share of the market's
travel going to the hexagon's unit (a town, or a rural block group), divided evenly over the unit's hexagons.
Usage: market_evidence.py <region>"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import Point, shape

root = Path(__file__).resolve().parents[1]
region = sys.argv[1] if len(sys.argv) > 1 else "columbia"
os.environ["TIE_LIB"] = "1"
sys.argv = ["confidence_layer.py", region]
g = {"__file__": str(root / "analysis/confidence_layer.py"), "__name__": "lib"}
src = open(root / "analysis/confidence_layer.py").read()
exec(compile(src[:src.index("out = {}\nfor town in")], "confidence_layer.py", "exec"), g)
ns, MAPS, P = g["ns"], g["MAPS"], g["P"]
C = json.load(open(root / ("flows/reach/confidence_columbia.json" if region == "columbia" else f"flows/reach/{region}/confidence.json")))
Wa, Ha = np.array(P["W"]), np.array(P["H"])
unit_at, centre = ns["unit_at"], ns["centre"]
unit_hexes = defaultdict(list)
for k, u in unit_at.items():
    unit_hexes[u].append(k)
rows = []
for town, ms in MAPS["towns"].items():
    for m in ms:
        pt = next(p for p in ns["out"][town] if p["rank"] == m["rank"])
        hbi = [P["homes"].index(h) for h in ns["town_bgs"](town) if h in P["homes"]]
        Wm, Xm = Wa[hbi], np.asarray(P["X"])[hbi]
        den = np.maximum(Wm @ Ha, 1e-9)
        trav = sum((Xm * (Wm[:, k:k + 1] * Ha[k][None, :] / den)).sum(0) for k in pt["patterns"])
        drop = ns["own_units"](town)
        tv = {u: x for u, x in zip(P["units"], trav) if x > 0 and u not in drop}
        tot = sum(tv.values())
        res_u = {u: m["residents"] * x / tot for u, x in tv.items()}
        net = m["index"]["net"]
        on, basef = g["shown_set"](net, set(MAPS.get("in_market", [])))
        area = shape(C[town][str(m["rank"])]["outline"])
        drawn = [k for k in on if net[k] < 100 and k in centre and area.contains(Point(*centre[k]))]
        for k in drawn:
            u = unit_at.get(k)
            rows.append({"town": town, "rank": m["rank"], "residents": m["residents"], "hex": k,
                         "residents_worth": res_u.get(u, 0) / max(len(unit_hexes.get(u, [1])), 1),
                         "unit_residents_worth": res_u.get(u, 0), "town_unit": not (u or "").startswith("rural:")})
D = pd.DataFrame(rows)
D.to_csv(root / f"analysis/market_evidence_{region}.csv", index=False)
bands = [0, 5, 25, 100, 1e9]; lab = ["under 5", "5-25", "25-100", "100+"]
D["band"] = pd.cut(D.unit_residents_worth, bands, labels=lab, right=False)
t = D.groupby(["town", "rank", "residents"]).band.value_counts(normalize=True).unstack().reindex(columns=lab).fillna(0).mul(100).round(0)
t["hexagons drawn"] = D.groupby(["town", "rank", "residents"]).size()
print("Share of drawn hexagons (beyond home) by residents' worth of travel to their town or rural block group, %:")
print(t.to_string())
