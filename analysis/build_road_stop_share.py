"""Share of each county pair's visits that are highway stops, and the pass-through discount -> road_stop_share.csv
Run after build_statewide_od.py (the discount shares are weighted by od_mo_2026.csv visits).

Advan Weekly Patterns Plus, Missouri places, the four full weeks of March 2026 (2026-03-02 .. 03-23). For every place,
VISITOR_HOME_CBGS gives visitors by home block group; summed to home county x place county. Advan codes places in NAICS
2017: gas stations are 447110 / 447190, convenience stores 445120; the 2022 codes (4571xx, 445131) do not occur.
Three definitions of a road stop:
  old        NAICS prefixes 4471, 4571, 445131, 722513 (2026-10-16): gas stations and limited-service restaurants; misses
             every convenience store (445120)
  codes      old + 445120 (convenience stores, NAICS 2017)
  highway    codes, and the place within HWY_KM = 1 km of an Interstate or US highway: OpenStreetMap
             (osm/missouri-latest.osm.pbf), ways tagged highway = motorway / trunk / primary (and their links) whose ref
             names an Interstate (I nn) or US route (US nn); business routes, loops and spurs ("US 63 Business") are
             not highways here. TIGER primary roads are not on disk.
Pass-through discount for a pair with 200+ store-level visitors (others 0): the share of its visits removed,
max(0, road-stop share - expected share). Expected share:
  discount_old                 old share - 0.125 (statewide out-of-county share, old definition; the adopted outcome
                               in gravity_terms.stop_discount reads road_stop_share and 0.125)
  discount_codes               codes share - the statewide out-of-county codes share
  discount_highway_statewide   highway share - the statewide out-of-county highway share
  discount                     highway share - expected_share_dest (ADOPTED definition, review 2026-10-24): the
                               destination's own store mix, as its residents use it (highway share of visits by j's
                               residents to j's places), times the statewide ratio of out-of-county to within-county
                               highway share, so a county with no highway stores expects none
Columns: i, j, visitors, road_stop_visitors, road_stop_share (old definition, unchanged), road_stop_visitors_codes,
road_stop_share_codes, highway_stop_visitors, highway_stop_share, expected_share_dest, discount_old, discount_codes,
discount_highway_statewide, discount.
Switch for the model: gravity_terms.travel_visits(p, months, discounted=False) is the undiscounted outcome (the primary
sensitivity); disc=<array from a discount_* column> applies any definition above.
"""
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import osmium
import pandas as pd
import pyarrow.parquet as pq
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

root = Path(__file__).resolve().parents[1]
A = root / "analysis"
WEEKS = ("2026-03-02", "2026-03-09", "2026-03-16", "2026-03-23")
HWY_KM = 1.0
MIN_VISITORS = 200
OLD_NORM = 0.125
old = lambda n: n.startswith(("4471", "4571", "445131", "722513"))
codes = lambda n: n.startswith(("447", "4571", "445120", "445131", "722513"))
KX, KY = 111.32 * np.cos(np.radians(38.4)), 110.57          # km per degree, Missouri
REF = re.compile(r"^\s*(I|US)\s*[- ]?\d+[A-Z]?\s*$")     # a whole route number: business loops and spurs excluded
HW = {"motorway", "trunk", "primary", "motorway_link", "trunk_link", "primary_link"}

lines = []


class Ways(osmium.SimpleHandler):
    def way(self, w):
        if w.tags.get("highway") in HW and any(REF.match(x) for x in w.tags.get("ref", "").split(";")):
            try:
                pts = [(n.lon * KX, n.lat * KY) for n in w.nodes]
            except osmium.InvalidLocationError:
                return
            if len(pts) > 1:
                lines.append(LineString(pts))


Ways().apply_file(str(root / "osm/missouri-latest.osm.pbf"), locations=True)
tree = STRtree(lines)
print(len(lines), "Interstate / US highway ways (OpenStreetMap)", flush=True)

near = {}
tot, stop_o, stop_c, stop_h = (defaultdict(float) for _ in range(4))
naics = defaultdict(int)
for f in sorted((root / "weekly/raw").glob("*.parquet")):
    if f.name[:10] not in WEEKS:
        continue
    t = pq.read_table(f, columns=["PERSISTENT_ID_STORE", "NAICS_CODE", "POI_CBG", "VISITOR_HOME_CBGS", "LATITUDE", "LONGITUDE"]).to_pylist()
    for r in t:
        if not r["POI_CBG"] or not r["VISITOR_HOME_CBGS"]:
            continue
        n = r["NAICS_CODE"] or ""
        is_o, is_c = old(n), codes(n)
        if is_c:
            naics[n[:6]] += 1
            k = r["PERSISTENT_ID_STORE"]
            if k not in near:
                p = Point(r["LONGITUDE"] * KX, r["LATITUDE"] * KY)
                near[k] = len(tree.query(p, predicate="dwithin", distance=HWY_KM)) > 0
        is_h = is_c and near[r["PERSISTENT_ID_STORE"]]
        j = r["POI_CBG"][:5]
        for h, v in json.loads(r["VISITOR_HOME_CBGS"]).items():
            if h.startswith("29"):
                key = (h[:5], j)
                tot[key] += v
                stop_o[key] += v * is_o
                stop_c[key] += v * is_c
                stop_h[key] += v * is_h
    print(f.name[:10], len(tot), "pairs so far", flush=True)
print("road-stop place-weeks by NAICS:", dict(sorted(naics.items())))
print(f"road-stop stores within {HWY_KM:g} km of an Interstate or US highway: {np.mean(list(near.values())):.1%} of {len(near):,}")

d = pd.DataFrame([(i, j, v, stop_o[(i, j)], stop_c[(i, j)], stop_h[(i, j)]) for (i, j), v in tot.items()],
                 columns=["i", "j", "visitors", "road_stop_visitors", "road_stop_visitors_codes", "highway_stop_visitors"])
d["road_stop_share"] = d.road_stop_visitors / d.visitors
d["road_stop_share_codes"] = d.road_stop_visitors_codes / d.visitors
d["highway_stop_share"] = d.highway_stop_visitors / d.visitors
x, w = d[d.i != d.j], d[d.i == d.j]
S = {c: x[c].sum() / x.visitors.sum() for c in ("road_stop_visitors", "road_stop_visitors_codes", "highway_stop_visitors")}
S_local = w.highway_stop_visitors.sum() / w.visitors.sum()
local = (w.set_index("j").highway_stop_share).to_dict()
d["expected_share_dest"] = d.j.map(local).fillna(S_local) * S["highway_stop_visitors"] / S_local
big = d.visitors >= MIN_VISITORS
d["discount_old"] = np.where(big, np.maximum(0, d.road_stop_share - OLD_NORM), 0.0)
d["discount_codes"] = np.where(big, np.maximum(0, d.road_stop_share_codes - S["road_stop_visitors_codes"]), 0.0)
d["discount_highway_statewide"] = np.where(big, np.maximum(0, d.highway_stop_share - S["highway_stop_visitors"]), 0.0)
d["discount"] = np.where(big, np.maximum(0, d.highway_stop_share - d.expected_share_dest), 0.0)
d.loc[d.i == d.j, ["discount_old", "discount_codes", "discount_highway_statewide", "discount"]] = 0.0
d[["i", "j", "visitors", "road_stop_visitors", "road_stop_share", "road_stop_visitors_codes", "road_stop_share_codes",
   "highway_stop_visitors", "highway_stop_share", "expected_share_dest", "discount_old", "discount_codes",
   "discount_highway_statewide", "discount"]].to_csv(A / "road_stop_share.csv", index=False)

print(f"{len(x):,} out-of-county pairs. Out-of-county share, visitor-weighted: old {S['road_stop_visitors']:.1%}, codes "
      f"{S['road_stop_visitors_codes']:.1%}, highway {S['highway_stop_visitors']:.1%}; within the home county: old "
      f"{w.road_stop_visitors.sum() / w.visitors.sum():.1%}, codes {w.road_stop_visitors_codes.sum() / w.visitors.sum():.1%}, "
      f"highway {S_local:.1%}")
od = pd.read_csv(A / "od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
assert {"visits", "visits_recorded"} <= set(od.columns), "od_mo_2026.csv not built by build_statewide_od.py"
od = od[(od.home_county != "OUT") & (od.home_county != od.dest_county)].groupby(["home_county", "dest_county"]).visits.sum()
m = d.set_index(["i", "j"]).reindex(od.index).fillna(0.0)
print("Pass-through discount, share of out-of-county calibrated visits removed (Jan-Sep):")
for c, lab in (("discount_old", "old codes, statewide 12.5%"), ("discount_codes", "codes fixed (+445120), statewide"),
               ("discount_highway_statewide", f"highway stops within {HWY_KM:g} km, statewide"),
               ("discount", f"highway stops within {HWY_KM:g} km, destination's own store mix (adopted)")):
    print(f"  {lab}: {(od * m[c]).sum() / od.sum():.2%} ({(m[c] > 0).sum():,} pairs; largest {m[c].max():.0%})")
