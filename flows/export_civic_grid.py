"""The statewide 3 km hexagon grid for the datadesk builder's coverage density (2026-10-22).

Public Census geography only -- no Advan data -- so it ships inside datadesk beside its boundary files:

  grid     the hexagon plane: 1.5 km circumradius, x = lon * 111.32 * cos(38.7 deg), y = lat * 110.57 (km),
           pointy-top axial (q, r); distances for story reach use cos(38.6 deg), as the coverage rules did
  hexes    "q,r": [county FIPS, town GEOID (the 2020 place holding the hexagon's centre) or "", 2020 population]
           -- the county of the block group holding the centre; population is each block group's 2020 count over
           the hexagons whose centres lie in it
  places   GEOID: [name, lon, lat, 2024 population estimate, [hexagons a story about the town reaches]]
           -- the town's 2020 boundary and 3 km around it (analysis/area_coverage_alignment.town_area)
  counties FIPS: [name, geometry] for Missouri and the counties of the eight bordering states within 1.5 degrees
           of it (cb_2020_us_county_500k, simplified to 0.003 degrees): a map at a state line shows the
           neighbouring state's county borders for context (user, 2026-10-22)
  markets  region: [TV market name, outline] (flows/reach/**/market_pattern_maps.json)
  landmarks  [name, lon, lat] from flows/regions.json, for naming an unlabelled cluster
  areas_p  "region|town|area": {"p": {hexagon: p}, "area": {hexagon: part}}: each hexagon's likelihood of being
           part of the area (the ensemble's 1,728 versions weighted equally), and the multi-part area (flows/area_core.py)
           (flows/area_ensemble.py; derived from Advan travel at the hexagon level -- check the licence before shipping)

Every number is the one today's coverage maps were computed from (analysis/area_coverage_alignment.py), so the
builder's coverage density can be checked against them.

Usage: export_civic_grid.py <out.json> <cb_2020_us_county_500k dir>     (datadesk: visuals/data/civic_grid_29.json)"""
import json
import os
import runpy
import sys
from pathlib import Path

import pandas as pd

root = Path(__file__).resolve().parents[1]
out, COUNTY_DIR = Path(sys.argv[1]), sys.argv[2]
os.environ["COV_LIB"] = "1"
sys.argv = ["area_coverage_alignment.py"]
A = runpy.run_path(str(root / "analysis/area_coverage_alignment.py"), run_name="cov_lib")
ns, hexes, hex_pop, pl_shapes = A["ns"], A["hexes"], A["hex_pop"], A["pl_shapes"]
county_of = {k: b_[:5] for k, b_ in A["hex_bg"].items()}
_units = {k: c for c, hs in ns["county_hexes"].items() for k in hs}
print("hexagons whose travel-unit county differs from their block group's:",
      sum(1 for k in county_of if _units.get(k) and _units[k] != county_of[k]), flush=True)
hex_place = ns["hex_place"]

pe = pd.read_csv(root / "census_dl/ref/sub-est2024_29.csv", dtype=str, encoding="latin-1")
pe = pe[pe.SUMLEV == "162"]
pop24 = {"29" + r.PLACE: int(r.POPESTIMATE2024) for r in pe.itertuples()}

grid = {"size_km": 1.5, "lat0": 38.7, "ky": 110.57, "reach_lat": 38.6, "state": "29"}
hexes_out = {k: [county_of.get(k, ""), hex_place.get(k, ""), round(hex_pop.get(k, 0))]
             for k in hexes if county_of.get(k, "").startswith("29")}
places_out = {}
for g_ in pl_shapes:
    if not g_.startswith("29"):
        continue
    rec, geom = pl_shapes[g_]
    c = geom.representative_point()
    reach = sorted(k for k in A["town_area"](g_) if k in hexes_out)
    places_out[g_] = [rec["NAME"], round(c.x, 5), round(c.y, 5), pop24.get(g_, 0), reach]
from shapely.geometry import box, mapping  # noqa: E402

rnd = lambda c: [] if not len(c) else [rnd(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], 4), round(c[1], 4)]
NEAR = {"05", "17", "19", "20", "21", "31", "40", "47"}
reach_box = box(-95.77 - 1.5, 35.99 - 1.5, -89.10 + 1.5, 40.61 + 1.5)
us = ns["read_shp"](COUNTY_DIR + "/cb_2020_us_county_500k", lambda r: r["GEOID"])
counties_out = {}
for fips, (rec, geom) in us.items():
    if fips[:2] == "29" or (fips[:2] in NEAR and geom.intersects(reach_box)):
        gj = mapping(geom.simplify(0.003))
        counties_out[fips] = [rec["NAME"], {"type": gj["type"], "coordinates": rnd(gj["coordinates"])}]
regions = json.load(open(root / "flows/regions.json"))
markets_out = {}
for reg, cfg in regions.items():
    f = root / cfg["out"] / "market_pattern_maps.json"
    if f.exists():
        mk = json.load(open(f))["market"]
        markets_out[reg] = [mk["name"], {"type": mk["outline"]["type"], "coordinates": rnd(mk["outline"]["coordinates"])}]
landmarks_out = [[l["name"], l["lon"], l["lat"]] for cfg in regions.values() for l in cfg.get("landmarks", [])]
# AREA PROBABILITY (2026-10-24, flows/area_ensemble.py): per built area, each hexagon's share of the settings ensemble's
# members that draw it -- "region|town|area": {hexagon: p}
areas_p = {}
for reg, cfg in regions.items():
    f = root / ("flows/reach/probability_columbia.json" if reg == "columbia" else f"{cfg['out']}/probability.json")
    if f.exists():
        for t_, ranks in json.load(open(f)).items():
            for r_, rec in ranks.items():
                areas_p[f"{reg}|{t_}|{r_}"] = {"p": rec["p"], "area": rec.get("core50_part_hexes", {})}
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"grid": grid, "hexes": hexes_out, "places": places_out, "counties": counties_out,
                               "markets": markets_out, "landmarks": landmarks_out, "areas_p": areas_p}, separators=(",", ":")))
print(f"{out}: {len(hexes_out):,} hexagons, {len(places_out):,} towns, {len(counties_out)} counties, {len(markets_out)} markets, {out.stat().st_size // 1024} KB")
