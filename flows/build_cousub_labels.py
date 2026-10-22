"""cousub_labels.json: a reader's name for each Missouri county subdivision -- the largest city lying mostly inside
it, the larger when two qualify ("Jefferson City", not Taos), with a direction on every part of a split city
except one holding 60% of it ("Columbia (west)", "Jefferson City (east)").
A subdivision holding no city keeps its own Census name.
Census 2020 cartographic files in ../census_dl; read_shp from build_cousub_shares.py.
"""
import json
from collections import defaultdict
from pathlib import Path

here = Path(__file__).parent
ns = {}
src = (here / "build_cousub_shares.py").read_text()
exec(src.split('if "--geo" in sys.argv')[0].replace("Path(__file__).parent", f'Path("{here}")'), ns)
DL = here.parent / "census_dl"
cous = ns["read_shp"](str(DL / "cousub/cb_2020_29_cousub_500k"), lambda r: r["GEOID"])
places = ns["read_shp"](str(DL / "place/cb_2020_29_place_500k"), lambda r: r["GEOID"])
parts = defaultdict(dict)    # place -> {cousub: overlap area}
best = {}
for c, (crec, cg) in cous.items():
    hits = []
    for p, (prec, pg) in places.items():
        if prec["LSAD"] != "25" or not pg.intersects(cg):     # 25 = city; CDPs are not what a reader names
            continue
        a = pg.intersection(cg).area
        if a > 0:
            hits.append((a, p))
            parts[p][c] = a
    # the city's own share, not only how much of the subdivision it covers: Mexico is 4.5% of Salt River township
    # 40% of Mexico lies in Salt River township, 47% of Fulton in West Fulton
    hits = [h for h in hits if h[0] / places[h[1]][1].area >= 0.25 or h[0] / cg.area >= 0.05]
    # the LARGER city names the area: Liberty township holds all of Taos (900 people) and Jefferson City's east side
    best[c] = max(hits, key=lambda h: places[h[1]][1].area)[1] if hits else None
labels = {}
for c, p in best.items():
    if p is None:
        labels[c] = cous[c][0]["NAME"]
        continue
    name = places[p][0]["NAME"]
    pg = places[p][1]
    # a city's part keeps the plain name only when it holds most of the city; every other part says which side
    share = parts[p][c] / pg.area
    if share < 0.6 and any(k != c and a / pg.area >= 0.1 for k, a in parts[p].items()):
        here_c, whole = pg.intersection(cous[c][1]).centroid, pg.centroid
        dx, dy = here_c.x - whole.x, here_c.y - whole.y
        name += " (" + (("east" if dx > 0 else "west") if abs(dx) >= abs(dy) else ("north" if dy > 0 else "south")) + ")"
    labels[c] = name
json.dump(labels, open(here / "cousub_labels.json", "w"), indent=0)
print({k: labels[k] for k in ("2901915688", "2901948944", "2905136764", "2907770009", "2901912916")})
