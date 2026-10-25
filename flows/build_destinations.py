"""Destinations: the places people go, from OpenStreetMap, for the market maps' rural shading. ALL OF MISSOURI.

Every node or way in Missouri tagged as a destination -- amenity, shop,
leisure, tourism, office, healthcare, craft, or a commercial, retail, industrial, school, church or civic building, and
village and hamlet centres -- as a point (a way by its first node), with the 2020 block group holding it.
A rural area is shaded only where it has destinations (dasymetric): its weight goes to the land people visit, not to the
whole of a block group that is mostly fields and forest.
Writes flows/reach/destinations_mo.csv: lon, lat, block_group.
"""
import json
from pathlib import Path

import numpy as np
import osmium
import pandas as pd
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

here = Path(__file__).parent
R = here / "reach"
BOX = (-95.8, 35.9, -89.0, 40.7)                       # Missouri
KEYS = ("amenity", "shop", "leisure", "tourism", "office", "healthcare", "craft")
BUILDINGS = {"commercial", "retail", "industrial", "school", "church", "civic", "public", "warehouse", "supermarket",
             "hospital", "college", "university", "kindergarten", "hotel", "office", "sports_centre", "stadium"}
SKIP = {"parking", "parking_space", "bench", "waste_basket", "bicycle_parking", "hunting_stand", "fire_hydrant",
        "post_box", "vending_machine", "toilets", "drinking_water", "waste_disposal", "recycling", "picnic_table", "shelter"}


class Dest(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.pts = []

    def keep(self, tags):
        if any(k in tags and tags[k] not in SKIP for k in KEYS):
            return True
        return tags.get("building") in BUILDINGS or tags.get("place") in ("village", "hamlet")

    def add(self, lon, lat):
        if BOX[0] <= lon <= BOX[2] and BOX[1] <= lat <= BOX[3]:
            self.pts.append((lon, lat))

    def node(self, n):
        if self.keep(n.tags):
            self.add(n.location.lon, n.location.lat)

    def way(self, w):
        if self.keep(w.tags):
            try:
                n = w.nodes[0]
                self.add(n.lon, n.lat)
            except (osmium.InvalidLocationError, IndexError):
                pass


h = Dest()
h.apply_file(str(here.parent / "osm/missouri-latest.osm.pbf"), locations=True)
__file__ = str(here / "build_cousub_shares.py")
exec(open(here / "build_cousub_shares.py").read().split("\ndef cw(")[0])
bgs = read_shp(str(DL / "bg/cb_2020_29_bg_500k"), lambda r: r["GEOID"])
ids = list(bgs)
tree = STRtree([bgs[g][1] for g in ids])
rows = []
for lon, lat in h.pts:
    p = Point(lon, lat)
    hit = [ids[i] for i in tree.query(p) if bgs[ids[i]][1].contains(p)]
    if hit:
        rows.append((round(lon, 5), round(lat, 5), hit[0]))
d = pd.DataFrame(rows, columns=["lon", "lat", "block_group"])
d.to_csv(R / "destinations_mo.csv", index=False)
print(f"{len(h.pts):,} destinations in the box; {len(d):,} in the state's block groups; "
      f"block groups with none: {len(set(ids) - set(d.block_group))} of {len(ids)}")
