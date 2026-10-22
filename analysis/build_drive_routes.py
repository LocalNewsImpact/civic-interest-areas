"""Driving routes between the main towns of every pair of Missouri counties -> drive_od.csv

Road network: OpenStreetMap, Geofabrik Missouri extract (osm/missouri-latest.osm.pbf), roads of class motorway down to
unclassified (residential streets left out -- county-to-county routing does not need them). Speed: the way's maxspeed
where tagged in mph, else a typical speed for its class. Ways are treated as two-way.
Each county is represented by its main town -- the incorporated place with the largest 2024 population inside the
county (Census sub-county estimates, sub-est2024_29.csv; "balance of county" remainders excluded) -- at a point inside
the part of the town that lies in the county (Census 2020 place boundaries). Mexico to Columbia, not Audrain to Boone.
Each town point is snapped to the nearest network node; the fastest route by time is found for every ordered pair
(Dijkstra, scipy). Per pair: the two towns, driving minutes, driving miles, and the counties the route passes through
on the way (route nodes located in county polygons; the two end counties excluded).
"""
import json
import math
import re
from pathlib import Path

import numpy as np
import osmium
import pandas as pd
import shapely
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree
from shapely.geometry import shape

root = Path(__file__).resolve().parents[1]
SPEED = {"motorway": 65, "motorway_link": 45, "trunk": 55, "trunk_link": 40, "primary": 50, "primary_link": 35,
         "secondary": 45, "secondary_link": 30, "tertiary": 40, "tertiary_link": 30, "unclassified": 35}


class Roads(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.ids, self.lon, self.lat, self.u, self.v, self.mi, self.mins = {}, [], [], [], [], [], []

    def node_index(self, n):
        k = self.ids.get(n.ref)
        if k is None:
            k = self.ids[n.ref] = len(self.lon)
            self.lon.append(n.lon); self.lat.append(n.lat)
        return k

    def way(self, w):
        hw = w.tags.get("highway")
        if hw not in SPEED:
            return
        mph = SPEED[hw]
        m = re.match(r"(\d+)\s*mph", w.tags.get("maxspeed", ""))
        if m and 10 <= int(m.group(1)) <= 85:
            mph = int(m.group(1))
        prev = None
        for n in w.nodes:
            if not n.location.valid():
                prev = None
                continue
            k = self.node_index(n)
            if prev is not None:
                (x1, y1), (x2, y2) = (self.lon[prev], self.lat[prev]), (self.lon[k], self.lat[k])
                p1, p2 = math.radians(y1), math.radians(y2)
                d = 3959 * 2 * math.asin(math.sqrt(math.sin((p2 - p1) / 2) ** 2 +
                                                   math.cos(p1) * math.cos(p2) * math.sin(math.radians(x2 - x1) / 2) ** 2))
                self.u.append(prev); self.v.append(k); self.mi.append(d); self.mins.append(60 * d / mph)
            prev = k


r = Roads()
r.apply_file(str(root / "osm/missouri-latest.osm.pbf"), locations=True)
N = len(r.lon)
lon, lat = np.array(r.lon), np.array(r.lat)
u, v = np.array(r.u), np.array(r.v)
T = coo_matrix((np.r_[r.mins, r.mins], (np.r_[u, v], np.r_[v, u])), shape=(N, N)).tocsr()
L = coo_matrix((np.r_[r.mi, r.mi], (np.r_[u, v], np.r_[v, u])), shape=(N, N)).tocsr()
_, comp = connected_components(T, directed=False)
main = np.bincount(comp).argmax()
print(f"network: {N:,} nodes, {len(u):,} road segments; largest connected part {np.mean(comp == main):.1%} of nodes", flush=True)

cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str}).set_index("fips")
fips = list(cov.index)
geo = json.load(open(root / "flows/cousub_29.geojson"))
polys = {f["id"]: shape(f["geometry"]) for f in geo["counties"]["features"]}
est = pd.read_csv(root / "census_dl/ref/sub-est2024_29.csv", dtype=str, encoding="latin-1")
est = est[(est.SUMLEV == "157") & (est.PLACE != "99990")].assign(pop=lambda x: x.POPESTIMATE2024.astype(int),
                                                                fips=lambda x: "29" + x.COUNTY)
town = est.sort_values("pop", ascending=False).groupby("fips").head(1).set_index("fips")
ns = {}
src_code = (root / "flows/build_cousub_shares.py").read_text()
exec(src_code.split('if "--geo" in sys.argv')[0].replace("Path(__file__).parent", f'Path("{root / "flows"}")'), ns)
places = ns["read_shp"](str(root / "census_dl/place/cb_2020_29_place_500k"), lambda r: r["GEOID"])
tlon, tlat, tname = [], [], []
for f in fips:
    t = town.loc[f]
    g = places["29" + t.PLACE][1].intersection(polys[f])
    pt = (g if not g.is_empty else places["29" + t.PLACE][1]).representative_point()
    tlon.append(pt.x); tlat.append(pt.y); tname.append(t.NAME.replace(" city", "").replace(" town", "").replace(" village", "").replace(" (pt.)", ""))
print("towns:", ", ".join(f"{cov.name[f]}: {n}" for f, n in list(zip(fips, tname)) if f in ("29007", "29019", "29151", "29027", "29051")), flush=True)
keep = np.where(comp == main)[0]
scale = math.cos(math.radians(38.5))
tree = cKDTree(np.c_[lon[keep] * scale, lat[keep]])
dsnap, idx = tree.query(np.c_[np.array(tlon) * scale, np.array(tlat)])
src = keep[idx]
print(f"towns snapped to the network: median {np.median(dsnap) * 69:.2f} mi, max {dsnap.max() * 69:.2f} mi", flush=True)

ids = list(polys)
stree = shapely.STRtree([polys[k] for k in ids])
pts = shapely.points(lon, lat)
pi, gi = stree.query(pts, predicate="within")
node_county = np.full(N, -1)
node_county[pi] = gi
county_code = np.array(ids)

rows = []
for b in range(0, len(fips), 5):
    batch = list(range(b, min(b + 5, len(fips))))
    dist, pred = dijkstra(T, directed=False, indices=src[batch], return_predecessors=True)
    for bi, a in enumerate(batch):
        for c in range(len(fips)):
            if c == a:
                continue
            t = src[c]
            path, k = [], t
            while k != src[a] and k >= 0:
                path.append(k); k = pred[bi, k]
            path.append(src[a])
            path = np.array(path[::-1])
            miles = float(np.asarray(L[path[:-1], path[1:]]).ravel().sum())
            cs = node_county[path]
            through = [county_code[x] for x in dict.fromkeys(cs[cs >= 0]) if county_code[x] not in (fips[a], fips[c])]
            rows.append((fips[a], fips[c], tname[a], tname[c], round(dist[bi, t], 1), round(miles, 1), ";".join(through)))
    print(f"routed {min(b + 5, len(fips))} of {len(fips)} origins", flush=True)
out = pd.DataFrame(rows, columns=["i", "j", "town_i", "town_j", "drive_minutes", "drive_miles", "through"])
out.to_csv(root / "analysis/drive_od.csv", index=False)
print(out.describe().round(1).to_string())
