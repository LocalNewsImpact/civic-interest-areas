"""Home block groups of the Columbia-Jefferson City TV market's study counties (Audrain, Boone, Osage), for
travel_patterns.py and the scripts after it.

From neighborhood/flows_audrain_boone_osage_2026.csv (Advan Neighborhood Patterns Plus, distinct devices by home block
group, January-July 2026: the months on 2020 block groups). A home block group is one with 50+ residents seen at home in
a month. Its town is the study town (Columbia, Mexico or Linn), and its place the 2020 Census place, in which half or
more of its 2020 Census population lives: block populations (P1_001N, 2020 PL 94-171 redistricting file, Census API,
cached in census_dl/ref/pl2020_blocks_<county>.csv) summed by the place each block lies in (Census block assignment file,
census_dl/BlockAssign_ST29_MO.zip). A block group with no place holding half its people is rural (place ""). No block
group center enters the rule; lon, lat are the block group's 2020 population-weighted center (CenPop2020_Mean_BG29.txt),
for reference only. (Until 2026-11-06 the rule was geometric: the block group's interior point inside the town, or a
tenth of the town's area inside the block group. It left out half of Mexico's residents, whose block groups straddle the
city line.)

usage: build_homes.py [columbia]. Writes flows/reach/homes.csv: home_cbg, county, town, place, lon, lat, own_mean
(residents seen at home, January-July 2026 mean), months; prints each study town's coverage.
"""
import io
import json
import os
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

here = Path(__file__).parent
DL = here.parent / "census_dl"
OUT = here / "reach"
OUT.mkdir(exist_ok=True)
MONTHS = [f"2026-0{m}" for m in range(1, 8)]
MIN_OWN = 50
SHARE = 0.5                                     # of the block group's 2020 population inside the place
TOWNS = {"2915670": "Columbia", "2947648": "Mexico", "2943238": "Linn"}

f = pd.read_csv(here.parent / "neighborhood/flows_audrain_boone_osage_2026.csv",
                dtype={"dest_cbg": str, "home_cbg": str},
                usecols=["month", "dest_cbg", "home_cbg", "device_home_areas"])
f = f[f.month.isin(MONTHS)]
own = f[f.dest_cbg == f.home_cbg].set_index(["month", "home_cbg"]).device_home_areas
homes = own[own >= MIN_OWN].reset_index().rename(columns={"device_home_areas": "own"})
counties = sorted({h[:5] for h in homes.home_cbg})


def block_population(county):
    """2020 Census population of every block in the county (state + county FIPS), cached under census_dl/ref."""
    cache = DL / "ref" / f"pl2020_blocks_{county}.csv"
    if cache.exists():
        return pd.read_csv(cache, dtype={"block": str}).set_index("block")["pop"]
    key = os.environ.get("CENSUS_API_KEY")
    url = (f"https://api.census.gov/data/2020/dec/pl?get=P1_001N&for=block:*&in=state:{county[:2]}%20county:{county[2:]}"
           + (f"&key={key}" if key else ""))
    rows = json.load(urllib.request.urlopen(url))[1:]
    s = pd.DataFrame([(r[1] + r[2] + r[3] + r[4], int(r[0])) for r in rows], columns=["block", "pop"]).set_index("block")["pop"]
    s.to_csv(cache)
    return s


blocks = pd.concat([block_population(c) for c in counties]).to_frame()
with zipfile.ZipFile(DL / "BlockAssign_ST29_MO.zip") as z:
    baf = pd.read_csv(io.BytesIO(z.read(next(n for n in z.namelist() if "INCPLACE" in n))), sep="|", dtype=str)
baf = baf.set_index("BLOCKID")["PLACEFP"].dropna()
blocks["place"] = ("29" + baf).reindex(blocks.index).fillna("")
blocks["bg"] = blocks.index.str[:12]
by_place = blocks[blocks.place != ""].groupby(["bg", "place"])["pop"].sum()
total = blocks.groupby("bg")["pop"].sum()


def place_of(h):
    """The place holding half or more of block group h's 2020 population, else ""."""
    if h not in by_place.index.get_level_values(0) or total.get(h, 0) == 0:
        return ""
    s = by_place.loc[h]
    p = s.idxmax()
    return p if s[p] >= SHARE * total[h] else ""


cen = pd.read_csv(DL / "ref/CenPop2020_Mean_BG29.txt", dtype=str)
cen["bg"] = cen.STATEFP + cen.COUNTYFP + cen.TRACTCE + cen.BLKGRPCE
cen = cen.set_index("bg")
rows = []
for h in sorted(homes.home_cbg.unique()):
    p = place_of(h)
    rows.append({"home_cbg": h, "county": h[:5], "town": TOWNS.get(p, ""), "place": p,
                 "lon": round(float(cen.LONGITUDE.get(h, "nan")), 5), "lat": round(float(cen.LATITUDE.get(h, "nan")), 5),
                 "own_mean": homes[homes.home_cbg == h].own.mean(), "months": (homes.home_cbg == h).sum()})
out = pd.DataFrame(rows)
out.to_csv(OUT / "homes.csv", index=False)
print(f"homes {len(out)}: {out[out.town != ''].groupby('town').size().to_dict()}; rule: {SHARE:.0%}+ of the block group's "
      "2020 population inside the place")
print("| Town | 2020 Census population | Block groups | Their 2020 population | Of whom inside the town | Share of the town's population covered |")
print("|---|---:|---:|---:|---:|---:|")
for p, t in TOWNS.items():
    bgs = set(out[out.town == t].home_cbg)
    city = int(blocks[blocks.place == p]["pop"].sum())
    bgp = int(blocks[blocks.bg.isin(bgs)]["pop"].sum())
    both = int(blocks[blocks.bg.isin(bgs) & (blocks.place == p)]["pop"].sum())
    print(f"| {t} | {city:,} | {len(bgs)} | {bgp:,} | {both:,} ({both / bgp:.0%}) | {both / city:.0%} |")
