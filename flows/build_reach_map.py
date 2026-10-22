"""Consensus reach for Columbia, Mexico and Linn: the map's data.

The selected model (reach_models.py: M2, the observed reach pulled toward the logistic model with the selected terms,
strength a) is fitted on all seven months, January-July 2026, and gives every home block group's reach to every tract
of the Columbia-Jefferson City TV market. A town's consensus is the median over its home block groups, per tract:
no single neighbourhood sets it. Its own block groups' tracts are included: the home town is the most relevant place.
Usage: build_reach_map.py "<terms name>" <a>
Writes flows/reach/reach_towns.json: {town: {tract: reach}}, plus labels for the towns on the map.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

here = Path(__file__).parent
src = open(here / "reach_models.py").read().split("\nm2 = lambda")[0]
exec(src)                                        # data, matrices, SPECS, fit_predict
name, a = sys.argv[1], float(sys.argv[2])
terms = SPECS[name]
out, glm = fit_predict(g, g.drop_duplicates(["hi", "ti"]), terms)
out["m2"] = (out.people + a * out.m1) / (out.own + a)
out["town"] = out.home_cbg.map(homes.town).fillna("")
res, nbg = {}, {}
for town in ("Columbia", "Mexico", "Linn"):
    x = out[out.town == town].groupby("tract").m2.median()
    res[town] = {t: round(float(v), 4) for t, v in x.items()}
    nbg[town] = int(out[out.town == town].home_cbg.nunique())
    print(f"{town}: {(out.town == town).sum() // len(T)} block groups; tracts >= 5%: {(x >= .05).sum()}, >= 20%: {(x >= .2).sum()}; "
          f"max outside home county {x[~x.index.str.startswith(homes[homes.town == town].county.iloc[0])].max():.1%}")
print(pd.Series(glm.params).round(3).to_string())

# labels: towns of 2,500+ in the market (Census 2024 estimates), and the three study towns
exec(open(here / "build_cousub_shares.py").read().split("\ndef cw(")[0])
places = read_shp(str(DL / "place/cb_2020_29_place_500k"), lambda r: r["GEOID"])
pe = pd.read_csv(here.parent / "census_dl/ref/sub-est2024_29.csv", dtype=str, encoding="latin-1")
pop = {r.STATE + r.PLACE: int(r.POPESTIMATE2024) for r in pe[pe.SUMLEV == "162"].itertuples()}
tg = json.load(open(R / "tracts_dma.geojson"))
from shapely.geometry import shape
from shapely.ops import unary_union
dma = unary_union([shape(f["geometry"]) for f in tg["features"]])
labels = []
for gid, (r, geom) in places.items():
    if (pop.get(gid, 0) >= 2500 or r["NAME"] in ("Columbia", "Mexico", "Linn")) and dma.contains(geom.representative_point()):
        c = geom.representative_point()
        labels.append({"name": r["NAME"], "pop": pop.get(gid, 0), "lon": round(c.x, 4), "lat": round(c.y, 4)})
json.dump({"reach": res, "block_groups": nbg, "labels": sorted(labels, key=lambda l: -l["pop"]), "terms": name, "a": a},
          open(R / "reach_towns.json", "w"), indent=0)
print(f"labels: {[l['name'] for l in labels]}")
