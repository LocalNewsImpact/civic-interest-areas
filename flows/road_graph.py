"""Statewide road graph for market corridors, cached: OpenStreetMap (osm/missouri-latest.osm.pbf), motorway to tertiary
and their links, edge cost = length / class speed (mph: motorway 65, trunk 55, primary 50, secondary 45, tertiary 35,
links 30) -- build_routes.py's graph, for all of Missouri. Long edges carry points every 0.5 km so a route can be read
as the 3 km hexagons it crosses. Cached at flows/reach/road_graph_mo.npz.

route(lon0, lat0, lon1, lat1) -> [(lon, lat), ...] along the fastest route.
"""
import math
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

here = Path(__file__).parent
CACHE = here / "reach/road_graph_mo.npz"
SPEED = {"motorway": 65, "trunk": 55, "primary": 50, "secondary": 45, "tertiary": 35}
COSLAT = math.cos(math.radians(38.5))

if not CACHE.exists():
    import osmium

    class Roads(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.a, self.b, self.m, self.xa, self.ya, self.xb, self.yb = [], [], [], [], [], [], []

        def way(self, w):
            hw = w.tags.get("highway", "")
            base = hw.replace("_link", "")
            if base not in SPEED:
                return
            mph = 30 if hw.endswith("_link") else SPEED[base]
            try:
                pts = [(n.ref, n.lon, n.lat) for n in w.nodes]
            except osmium.InvalidLocationError:
                return
            oneway = w.tags.get("oneway") == "yes" or base == "motorway"
            for (a, xa, ya), (b, xb, yb) in zip(pts, pts[1:]):
                km = 6371 * 2 * math.asin(math.sqrt(math.sin(math.radians(yb - ya) / 2) ** 2 + math.cos(math.radians(ya))
                                                    * math.cos(math.radians(yb)) * math.sin(math.radians(xb - xa) / 2) ** 2))
                mins = km / (mph * 1.609) * 60
                for (u, v, x1, y1, x2, y2) in ((a, b, xa, ya, xb, yb),) + (() if oneway else ((b, a, xb, yb, xa, ya),)):
                    self.a.append(u); self.b.append(v); self.m.append(mins)
                    self.xa.append(x1); self.ya.append(y1); self.xb.append(x2); self.yb.append(y2)

    h = Roads()
    h.apply_file(str(here.parent / "osm/missouri-latest.osm.pbf"), locations=True)
    np.savez_compressed(CACHE, a=np.array(h.a), b=np.array(h.b), m=np.array(h.m), xa=np.array(h.xa), ya=np.array(h.ya),
                        xb=np.array(h.xb), yb=np.array(h.yb))
Z = np.load(CACHE)
ids, inv = np.unique(np.concatenate([Z["a"], Z["b"]]), return_inverse=True)
ia, ib = inv[: len(Z["a"])], inv[len(Z["a"]):]
X = np.zeros(len(ids)); Y = np.zeros(len(ids))
X[ia], Y[ia] = Z["xa"], Z["ya"]; X[ib], Y[ib] = Z["xb"], Z["yb"]
G = csr_matrix((Z["m"], (ia, ib)), shape=(len(ids), len(ids)))
_kd = cKDTree(np.c_[X * COSLAT, Y])
snap = lambda lon, lat: int(_kd.query([lon * COSLAT, lat])[1])


def route(lon0, lat0, lon1, lat1):
    s, t = snap(lon0, lat0), snap(lon1, lat1)
    _, pred = dijkstra(G, indices=s, return_predecessors=True)
    if pred[t] < 0 and s != t:
        return []
    path = [t]
    while path[-1] != s:
        path.append(pred[path[-1]])
    pts = []
    for u, v in zip(path[::-1], path[::-1][1:]):
        km = math.hypot((X[v] - X[u]) * 111.32 * COSLAT, (Y[v] - Y[u]) * 110.57)
        n = max(1, int(km / 0.5))
        pts += [(X[u] + (X[v] - X[u]) * k / n, Y[u] + (Y[v] - Y[u]) * k / n) for k in range(n)]
    return pts + [(X[path[0]], Y[path[0]])]


if __name__ == "__main__":
    print(f"road graph: {len(ids):,} nodes, {G.nnz:,} edges")
    print(len(route(-92.33, 38.95, -92.17, 38.57)), "points Columbia -> Jefferson City")
