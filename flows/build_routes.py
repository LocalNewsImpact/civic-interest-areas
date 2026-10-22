"""Road routes from each home block group to each tract of the Columbia-Jefferson City TV market.

Road graph: OpenStreetMap (osm/missouri-latest.osm.pbf), motorway to tertiary and their links, inside the market's
bounding box plus 0.3 degrees; edge cost = length / class speed (mph: motorway 65, trunk 55, primary 50, secondary 45,
tertiary 35, links 30). Each home block group centre and each tract centre is snapped to its nearest graph node; the
fastest route from home to tract is walked and every tract it passes through is recorded.
Writes flows/reach/routes.csv: home_cbg, dest_tract, via_tract (one row per tract on the route, the end tracts included)
and flows/reach/route_minutes.csv: home_cbg, tract, minutes.
"""
import json
import math
from pathlib import Path

import numpy as np
import osmium
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

here = Path(__file__).parent
R = here / "reach"
geo = json.load(open(R / "tracts_dma.geojson"))
tgeom = {f["id"]: shape(f["geometry"]) for f in geo["features"]}
x0, y0, x1, y1 = np.array([g.bounds for g in tgeom.values()]).T
BOX = (x0.min() - 0.3, y0.min() - 0.3, x1.max() + 0.3, y1.max() + 0.3)
SPEED = {"motorway": 65, "trunk": 55, "primary": 50, "secondary": 45, "tertiary": 35}


class Roads(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.edges = []

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
        if not any(BOX[0] <= x <= BOX[2] and BOX[1] <= y <= BOX[3] for _, x, y in pts):
            return
        oneway = w.tags.get("oneway") == "yes" or base == "motorway"
        for (a, xa, ya), (b, xb, yb) in zip(pts, pts[1:]):
            km = 6371 * 2 * math.asin(math.sqrt(math.sin(math.radians(yb - ya) / 2) ** 2 + math.cos(math.radians(ya))
                                                * math.cos(math.radians(yb)) * math.sin(math.radians(xb - xa) / 2) ** 2))
            mins = km / (mph * 1.609) * 60
            self.edges.append((a, b, mins, xa, ya, xb, yb))
            if not oneway:
                self.edges.append((b, a, mins, xb, yb, xa, ya))


h = Roads()
h.apply_file(str(here.parent / "osm/missouri-latest.osm.pbf"), locations=True)
e = pd.DataFrame(h.edges, columns=["a", "b", "mins", "xa", "ya", "xb", "yb"])
ids = pd.Index(pd.unique(np.concatenate([e.a.values, e.b.values])))
coord = pd.concat([e[["a", "xa", "ya"]].set_axis(["n", "x", "y"], axis=1), e[["b", "xb", "yb"]].set_axis(["n", "x", "y"], axis=1)]
                  ).drop_duplicates("n").set_index("n").loc[ids]
G = csr_matrix((e.mins.values, (ids.get_indexer(e.a), ids.get_indexer(e.b))), shape=(len(ids), len(ids)))
print(f"road graph: {len(ids):,} nodes, {len(e):,} edges")

# largest strongly-reachable set: snap only to nodes reachable from the market's centre
kd = cKDTree(np.c_[coord.x.values * math.cos(math.radians(38.7)), coord.y.values])
snap = lambda lon, lat: kd.query([lon * math.cos(math.radians(38.7)), lat])[1]
centre = snap(-92.2, 38.75)
reach_ok = np.isfinite(dijkstra(G, indices=[centre], limit=600)[0])
kd = cKDTree(np.c_[coord.x.values[reach_ok] * math.cos(math.radians(38.7)), coord.y.values[reach_ok]])
ok_idx = np.flatnonzero(reach_ok)
snap = lambda lon, lat: ok_idx[kd.query([lon * math.cos(math.radians(38.7)), lat])[1]]

homes = pd.read_csv(R / "homes.csv", dtype={"home_cbg": str})
tracts = pd.read_csv(R / "tracts.csv", dtype={"tract": str})
t_node = {t: snap(x, y) for t, x, y in zip(tracts.tract, tracts.lon, tracts.lat)}
# node -> tract, for the nodes routes pass through
names = list(tgeom)
tree = STRtree([tgeom[t] for t in names])
node_tract = {}


def tract_of(n):
    if n not in node_tract:
        p = Point(coord.x.values[n], coord.y.values[n])
        hit = [names[i] for i in tree.query(p) if tgeom[names[i]].contains(p)]
        node_tract[n] = hit[0] if hit else None
    return node_tract[n]


rows, mins = [], []
for hcbg, x, y in zip(homes.home_cbg, homes.lon, homes.lat):
    s = snap(x, y)
    dist, pred = dijkstra(G, indices=[s], return_predecessors=True)
    dist, pred = dist[0], pred[0]
    for t, n in t_node.items():
        mins.append((hcbg, t, dist[n]))
        seen, k = [], n
        while k >= 0 and k != s:
            tt = tract_of(k)
            if tt and (not seen or seen[-1] != tt):
                seen.append(tt)
            k = pred[k]
        for v in dict.fromkeys(seen + [t]):
            rows.append((hcbg, t, v))
pd.DataFrame(rows, columns=["home_cbg", "dest_tract", "via_tract"]).to_csv(R / "routes.csv", index=False)
pd.DataFrame(mins, columns=["home_cbg", "tract", "minutes"]).to_csv(R / "route_minutes.csv", index=False)
m = pd.DataFrame(mins, columns=["home_cbg", "tract", "minutes"])
print(f"routes: {len(rows):,} route-tract rows; minutes median {m.minutes.median():.0f}, unreachable {np.isinf(m.minutes).sum()}")
