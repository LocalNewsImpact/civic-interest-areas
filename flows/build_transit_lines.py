"""Transit corridors as roads: the road segments a town's residents use on the way to the places they go.

For each study town and magnification weight, the fastest road route (build_routes.py's graph) from each of the town's
home block groups to each tract shown on its map (interest_towns.json, index 5+) outside the home town. A road segment is
a transit corridor when half or more of the town's block groups route through it, and it lies outside the shown tracts
(through land the map does not shade). Drawn as a line, not a tract: a rural tract can cover half a county.
Writes flows/reach/transit_lines.json: {town: {w: [[[lon, lat], ...], ...]}} (merged runs of segments).
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

here = Path(__file__).parent
exec(open(here / "build_routes.py").read().split("\nrows, mins = [], []")[0])   # graph G, coord, snap, tract_of, homes
interest = json.load(open(R / "interest_towns.json"))
hm = pd.read_csv(R / "homes.csv", dtype={"home_cbg": str}).set_index("home_cbg")
tp = pd.read_csv(R / "tracts.csv", dtype={"tract": str}).fillna({"places": ""}).set_index("tract")
out = {}
for town, r in interest.items():
    hb = hm[hm.town == town]
    home_place = hb.place.dropna().iloc[0]
    out[town] = {}
    paths = {}
    for h_, x, y in zip(hb.index, hb.lon, hb.lat):
        s = snap(x, y)
        _, pred = dijkstra(G, indices=[s], return_predecessors=True)
        paths[h_] = (s, pred[0])
    for w, idx in r["index"].items():
        shown = {t for t, v in idx.items() if v >= 5}
        dest = [t for t in shown if home_place not in tp.places[t].split(";")]
        use = defaultdict(set)
        for h_, (s, pred) in paths.items():
            for t in dest:
                k = t_node[t]
                while k >= 0 and k != s and pred[k] >= 0:
                    use[(pred[k], k)].add(h_)
                    k = pred[k]
        keep = [e for e, hs in use.items() if 2 * len(hs) >= len(hb)]
        keep = [(a, b) for a, b in keep if tract_of(a) not in shown or tract_of(b) not in shown]
        # merge segments into runs
        nxt = defaultdict(list)
        for a, b in keep:
            nxt[a].append(b)
        indeg = defaultdict(int)
        for a, b in keep:
            indeg[b] += 1
        seen, lines = set(), []
        for a, b in keep:
            if (a, b) in seen:
                continue
            start = a
            while indeg[start] == 1 and len([p for p, q in keep if q == start]) == 1:
                prev = next(p for p, q in keep if q == start)
                if (prev, start) in seen or prev == a:
                    break
                start = prev
                if start == a:
                    break
            line, k = [start], start
            while True:
                cand = [q for q in nxt[k] if (k, q) not in seen]
                if not cand:
                    break
                seen.add((k, cand[0]))
                k = cand[0]
                line.append(k)
            if len(line) > 1:
                lines.append([[round(float(coord.x.values[n]), 5), round(float(coord.y.values[n]), 5)] for n in line])
        out[town][w] = lines
        km = sum(np.hypot(np.diff([p[0] for p in l]) * 87, np.diff([p[1] for p in l]) * 111).sum() for l in lines)
        print(f"{town} w={w}: {len(keep)} segments, {len(lines)} runs, {km:.0f} km of road outside shown tracts")
json.dump(out, open(R / "transit_lines.json", "w"))
