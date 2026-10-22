"""Home block groups of one TV market's fitted counties (flows/regions.json), for travel_patterns.py.

usage: build_homes.py <region>.  Writes <out>/homes.csv: home_cbg, county, town (a configured town: its centre in the
town, or 10%+ of the town's area inside the block group), place (any 2020 place by the same rule), lon, lat, own_mean
(residents seen at home, January-July 2026 mean), months. Block groups with 50+ residents seen at home in a month.
(The Columbia-Jefferson City market's homes.csv comes from build_reach.py.)
"""
import json
import sys
from pathlib import Path

import pandas as pd

here = Path(__file__).parent
REGION = sys.argv[1]
cfg = json.load(open(here / "regions.json"))[REGION]
OUT = here.parent / cfg["out"]
OUT.mkdir(parents=True, exist_ok=True)
__file__ = str(here / "build_cousub_shares.py")
exec(open(here / "build_cousub_shares.py").read().split("\ndef cw(")[0])     # read_shp, DL (and Columbia's DMA)
from shapely.strtree import STRtree
MONTHS = [f"2026-0{m}" for m in range(1, 8)]
f = pd.read_csv(here.parent / cfg["flows"], dtype={"dest_cbg": str, "home_cbg": str, "home_county": str},
                usecols=["month", "dest_cbg", "home_cbg", "home_county", "device_home_areas"])
f = f[f.month.isin(MONTHS) & f.home_county.isin(cfg["home_counties"]) & (f.dest_cbg == f.home_cbg)]
own = f[f.device_home_areas >= 50]
bgs = read_shp(str(DL / "bg/cb_2020_29_bg_500k"), lambda r: r["GEOID"])
places = read_shp(str(DL / "place/cb_2020_29_place_500k"), lambda r: r["GEOID"])
pids = list(places)
tree = STRtree([places[p][1] for p in pids])
town_of = {p: t for t, (_, p) in cfg["towns"].items()}
rows = []
for h, g in own.groupby("home_cbg"):
    if h not in bgs:
        continue
    geom = bgs[h][1]
    c = geom.representative_point()
    hit = [pids[i] for i in tree.query(geom) if places[pids[i]][1].contains(c)
           or geom.intersection(places[pids[i]][1]).area >= 0.1 * places[pids[i]][1].area]
    place = next((p for p in hit if p in town_of), hit[0] if hit else "")
    rows.append({"home_cbg": h, "county": h[:5], "town": town_of.get(place, ""), "place": place, "lon": c.x, "lat": c.y,
                 "own_mean": g.device_home_areas.mean(), "months": len(g)})
d = pd.DataFrame(rows)
d.to_csv(OUT / "homes.csv", index=False)
print(REGION, len(d), "home block groups;", d[d.town != ""].groupby("town").size().to_dict())
