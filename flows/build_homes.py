"""Home block groups of the Columbia-Jefferson City TV market's study counties (Audrain, Boone, Osage), for
travel_patterns.py and the scripts after it.

From neighborhood/flows_audrain_boone_osage_2026.csv (Advan Neighborhood Patterns Plus, distinct devices by home block
group, January-July 2026: the months on 2020 block groups). A home block group is one with 50+ residents seen at home in
a month; its town is the study town (Columbia, Mexico or Linn) containing its centre or with 10%+ of the town's area
inside it, and its place the 2020 place by the same rule.

usage: build_homes.py [columbia]. Writes flows/reach/homes.csv: home_cbg, county, town, place, lon, lat, own_mean
(residents seen at home, January-July 2026 mean), months.
"""
from pathlib import Path

import pandas as pd
from shapely.strtree import STRtree

here = Path(__file__).parent
exec(open(here / "build_cousub_shares.py").read().split("\ndef cw(")[0])   # read_shp, DL
OUT = here / "reach"
OUT.mkdir(exist_ok=True)
MONTHS = [f"2026-0{m}" for m in range(1, 8)]
MIN_OWN = 50

f = pd.read_csv(here.parent / "neighborhood/flows_audrain_boone_osage_2026.csv",
                dtype={"dest_cbg": str, "home_cbg": str},
                usecols=["month", "dest_cbg", "home_cbg", "device_home_areas"])
f = f[f.month.isin(MONTHS)]
own = f[f.dest_cbg == f.home_cbg].set_index(["month", "home_cbg"]).device_home_areas
homes = own[own >= MIN_OWN].reset_index().rename(columns={"device_home_areas": "own"})

bgs = read_shp(str(DL / "bg/cb_2020_29_bg_500k"), lambda r: r["GEOID"])
places = read_shp(str(DL / "place/cb_2020_29_place_500k"), lambda r: r["GEOID"])
TOWNS = {"Columbia": "Columbia", "Mexico": "Mexico", "Linn": "Linn"}
town_geom = {t: g for _, (r, g) in places.items() for t in TOWNS if r["NAME"] == t}
# a block group's place contains its centre or has 10%+ of its area inside the block group
pl_ids = list(places)
pl_tree = STRtree([places[p][1] for p in pl_ids])
near_pl = lambda geom: [pl_ids[i] for i in pl_tree.query(geom)]
home_place = lambda geom, c: next((p for p in near_pl(geom) if places[p][1].contains(c)
                                   or geom.intersection(places[p][1]).area >= 0.1 * places[p][1].area), "")
rows = []
for h in sorted(homes.home_cbg.unique()):
    c = bgs[h][1].representative_point()
    # a town smaller than its block group (Linn) holds no block group's centre: then the block groups covering 10%+ of it
    town = next((t for t, g in town_geom.items() if g.contains(c) or bgs[h][1].intersection(g).area >= 0.1 * g.area), "")
    rows.append({"home_cbg": h, "county": h[:5], "town": town, "place": home_place(bgs[h][1], c), "lon": c.x, "lat": c.y,
                 "own_mean": homes[homes.home_cbg == h].own.mean(), "months": (homes.home_cbg == h).sum()})
pd.DataFrame(rows).to_csv(OUT / "homes.csv", index=False)
print(f"homes {len(rows)}: {pd.DataFrame(rows).groupby('town').size().to_dict()}")
