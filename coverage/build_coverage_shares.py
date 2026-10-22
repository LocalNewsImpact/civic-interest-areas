"""Coverage on the travel maps' terms: for each home county's newsrooms, the share of their articles that name a
place outside the county which name each travel-map place (a city's Census subdivisions, as cousub_labels.json
groups them). Two versions: all newsrooms, and without broadcasters (KOMU, ABC 17 KMIZ, KBIA).

A named city (Census place code) is assigned to the subdivision holding most of its area, then to that
subdivision's place group. A place named without a code is matched by city name. A county named on its own is
counted as naming outside the home county but is not assigned to a place.
Output: ../flows/coverage_shares_2026_03.json
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

here = Path(__file__).parent
flows = here.parent / "flows"
ns = {}
src = (flows / "build_cousub_shares.py").read_text()
exec(src.split('if "--geo" in sys.argv')[0].replace("Path(__file__).parent", f'Path("{flows}")'), ns)
DL = here.parent / "census_dl"
cous = ns["read_shp"](str(DL / "cousub/cb_2020_29_cousub_500k"), lambda r: r["GEOID"])
places = ns["read_shp"](str(DL / "place/cb_2020_29_place_500k"), lambda r: r["GEOID"])
labels = json.load(open(flows / "cousub_labels.json"))
group = {c: re.sub(r" \((east|west|north|south)\)$", "", l) for c, l in labels.items()}

county_fips = {crec["NAMELSADCO"].lower(): c[:5] for c, (crec, _) in cous.items()}   # "boone county" -> 29019
place_group, by_name = {}, {}
for p, (prec, pg) in places.items():
    best = max(((pg.intersection(cg).area, c) for c, (_, cg) in cous.items() if pg.intersects(cg)), default=None)
    if best and best[0] > 0:
        place_group[p] = (best[1][:5], group[best[1]])
        by_name.setdefault((prec["NAME"].lower(), best[1][:5]), place_group[p])
print(f"{len(place_group)} Census places assigned to a travel-map place")

HOME = {"Audrain": "29007", "Boone": "29019", "Osage": "29151"}
arts = defaultdict(lambda: {"groups": set(), "counties": set(), "row": None})
unplaced = 0
for r in csv.DictReader(open(here / "coverage_places_2026_03.csv")):
    a = arts[r["article_id"]]
    a["row"] = r
    if not r["full_name"] or (r["state"] and r["state"] != "MO"):
        continue
    g = r["geoid"] or ""
    hit = None
    if r["geoid_level"] == "place" and g.startswith("29") and g in place_group:
        hit = place_group[g]
    elif r["geoid_level"] == "county" and g.startswith("29"):
        a["counties"].add(g[:5])
        continue
    if hit is None and r["city"]:
        # a city named without a code: matched by name inside its own county; a name without a county is used only
        # when one Missouri city carries it
        cf = county_fips.get((r["county"] or "").lower())
        if cf:
            hit = by_name.get((r["city"].lower(), cf))
        else:
            same = [v for (nm, _), v in by_name.items() if nm == r["city"].lower()]
            hit = same[0] if len(same) == 1 else None
    if hit:
        a["counties"].add(hit[0])
        a["groups"].add(hit)
    else:
        unplaced += 1
print("place rows not assigned:", unplaced)

out = {}
for version, keep in (("all", lambda r: True), ("no_broadcast", lambda r: r["broadcast"] != "True")):
    out[version] = {}
    for name, fips in HOME.items():
        mine = [a for a in arts.values() if a["row"]["publisher_county"] == name and keep(a["row"])]
        outside = [a for a in mine if any(c != fips for c in a["counties"])]
        counts = defaultdict(int)
        for a in outside:
            for cf, gname in {g for g in a["groups"] if g[0] != fips}:
                counts[f"{cf}|{gname}"] += 1
        out[version][name] = {"articles": len(mine), "outside": len(outside),
                              "places": {k: {"articles": v, "share": round(100 * v / max(1, len(outside)), 1)}
                                         for k, v in sorted(counts.items(), key=lambda kv: -kv[1])}}
        top = list(out[version][name]["places"].items())[:6]
        print(f"{version:12} {name:8} articles {len(mine):4}  naming outside {len(outside):4}  top {[(k.split('|')[1], v['share']) for k, v in top]}")
json.dump(out, open(flows / "coverage_shares_2026_03.json", "w"), indent=1)
