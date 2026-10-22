"""Reach: the share of a home block group's residents seen in each tract of the Columbia-Jefferson City TV market.

From neighborhood/flows_audrain_boone_osage_2026.csv (Advan Neighborhood Patterns Plus, distinct devices by home block
group, January-July 2026: the months on 2020 block groups). For month m, home block group h and destination tract t:
  people(m, h, t) = people from h seen in t's single busiest block group, h's own block group left out
                    (distinct people, the lower bound of build_unique_od.py)
  own(m, h)       = residents of h seen in h
  reach(m, h, t)  = min(1, people / own)
Every (m, h, t) on the grid is written, unseen as 0, for the home block groups with 50+ residents seen at home that
month. Calibration does not enter: reach is a share of the same panel.

Also writes the geometry the models and the map use: tract polygons (block groups dissolved), tract and home block
group centroids, and the town each home block group is in (2020 place containing its centre, or 10%+ of the place's area inside it).
Writes flows/reach/: reach_2026_jan_jul.csv, homes.csv, tracts.csv, tracts_dma.geojson
"""
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd
from shapely.geometry import mapping
from shapely.ops import unary_union

here = Path(__file__).parent
exec(open(here / "build_cousub_shares.py").read().split("\ndef cw(")[0])   # read_shp, DL, DMA
OUT = here / "reach"
OUT.mkdir(exist_ok=True)
MONTHS = [f"2026-0{m}" for m in range(1, 8)]
MIN_OWN = 50

f = pd.read_csv(here.parent / "neighborhood/flows_audrain_boone_osage_2026.csv",
                dtype={"dest_cbg": str, "home_cbg": str, "dest_county": str, "home_county": str},
                usecols=["month", "dest_cbg", "dest_county", "home_cbg", "home_county", "device_home_areas"])
f = f[f.month.isin(MONTHS)]
own = f[f.dest_cbg == f.home_cbg].set_index(["month", "home_cbg"]).device_home_areas
f = f[(f.dest_cbg != f.home_cbg) & f.dest_county.isin(DMA)]
f["tract"] = f.dest_cbg.str[:11]
p = f.groupby(["month", "home_cbg", "tract"]).device_home_areas.max().rename("people")

bgs = read_shp(str(DL / "bg/cb_2020_29_bg_500k"), lambda r: r["GEOID"])
by_tract = defaultdict(list)
for g, (_, geom) in bgs.items():
    if g[:5] in DMA:
        by_tract[g[:11]].append(geom)
tract_geom = {t: unary_union(gs) for t, gs in by_tract.items()}
tracts = sorted(tract_geom)

homes = own[own >= MIN_OWN].reset_index().rename(columns={"device_home_areas": "own"})
grid = homes.merge(pd.DataFrame({"tract": tracts}), how="cross")
grid = grid.merge(p.reset_index(), on=["month", "home_cbg", "tract"], how="left").fillna({"people": 0})
grid["reach"] = (grid.people / grid.own).clip(upper=1)
grid.to_csv(OUT / "reach_2026_jan_jul.csv", index=False)

places = read_shp(str(DL / "place/cb_2020_29_place_500k"), lambda r: r["GEOID"])
TOWNS = {"Columbia": "Columbia", "Mexico": "Mexico", "Linn": "Linn"}
town_geom = {t: g for _, (r, g) in places.items() for t in TOWNS if r["NAME"] == t}
# EVERY TOWN, for the home-town term: a block group's town contains its centre or has 10%+ of its area inside the block
# group; a tract is in a town when half or more of its block groups have their centre in the town (a fringe tract of
# mostly rural land still holds the town's people: Mexico's 950500), 25%+ of the tract is inside it, or 50%+ of the
# town is inside the tract (Linn).
from shapely.strtree import STRtree
pl_ids = list(places)
pl_tree = STRtree([places[p][1] for p in pl_ids])
near_pl = lambda geom: [pl_ids[i] for i in pl_tree.query(geom)]
home_place = lambda geom, c: next((p for p in near_pl(geom) if places[p][1].contains(c)
                                   or geom.intersection(places[p][1]).area >= 0.1 * places[p][1].area), "")
tract_bgs = defaultdict(list)
for b, (_, bg) in bgs.items():
    tract_bgs[b[:11]].append(bg.representative_point())
tract_place = lambda t, geom: ";".join(p for p in near_pl(geom) if (lambda a: a >= 0.25 * geom.area
                                       or a >= 0.5 * places[p][1].area
                                       or 2 * sum(places[p][1].contains(c) for c in tract_bgs[t]) >= len(tract_bgs[t])
                                       )(geom.intersection(places[p][1]).area))
rows = []
for h in sorted(homes.home_cbg.unique()):
    c = bgs[h][1].representative_point()
    # a town smaller than its block group (Linn) holds no block group's centre: then the block groups covering 10%+ of it
    town = next((t for t, g in town_geom.items() if g.contains(c) or bgs[h][1].intersection(g).area >= 0.1 * g.area), "")
    rows.append({"home_cbg": h, "county": h[:5], "town": town, "place": home_place(bgs[h][1], c), "lon": c.x, "lat": c.y,
                 "own_mean": homes[homes.home_cbg == h].own.mean(), "months": (homes.home_cbg == h).sum()})
pd.DataFrame(rows).to_csv(OUT / "homes.csv", index=False)
pd.DataFrame([{"tract": t, "county": t[:5], "places": tract_place(t, g), "lon": g.representative_point().x, "lat": g.representative_point().y,
               "area_km2": g.area * 111 * 111 * 0.78} for t, g in tract_geom.items()]).to_csv(OUT / "tracts.csv", index=False)
json.dump({"type": "FeatureCollection", "features": [
    {"type": "Feature", "id": t, "properties": {"county": t[:5]}, "geometry": mapping(g.simplify(0.0008))}
    for t, g in tract_geom.items()]}, open(OUT / "tracts_dma.geojson", "w"))
h = pd.DataFrame(rows)
print(f"grid {len(grid):,} rows; homes {h.home_cbg.nunique()} ({h.groupby('town').size().to_dict()}); tracts {len(tracts)}")
print(grid.groupby("month").agg(homes=("home_cbg", "nunique"), seen=("people", lambda x: (x > 0).mean())))
