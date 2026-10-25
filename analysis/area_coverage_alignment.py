"""QA DIAGNOSTIC (2026-10-24: supply figures belong to the next paper, not this one). How well news coverage lines up
with where residents travel, in each civic interest area's travel-only footprint
(Columbia I and II, Mexico, Linn), and how many newsrooms it takes to supply that coverage.

AREA: the published area -- the footprint: the hexagons whose centres lie inside its outline
  (flows/reach/confidence_columbia.json), drawn from the TRAVEL-ONLY civic interest area (user, 2026-10-24, option A:
  supply is measured on where residents go, not on an area news ties already enlarged). Every hexagon counts the same.
  Area = hexagons x 5.85 km2. "people inside" = the 2020 population of those hexagons (block-group population over the
  hexagons whose centres lie in it), beside the residents allocated to the area's travel pattern.
STORIES, March 2026, local outlets statewide (statewide and campus outlets excluded): each story's geolocated central
  point, standing for an area set by its geographic scope (the enrichment's scope classification,
  coverage/storymap/statewide_2026_03_scope.csv):
    neighborhood_community        3 km around the point
    city_municipality             the town (its 2020 place) and 3 km around it; a point outside any town, 5 km
    elsewhere_to_local, local_to_elsewhere, unclassified   as a town story
    regional                      40 km around the point (about the distance to the next county's centre)
    statewide, national, international, other            no local area
  A story whose point is only a county stands for the county (any local scope). Statewide, national and international
  stories add nothing, their mentions included.
  Weights (user, 2026-10-19): central focus 1, each place or county it mentions 0.5 -- a named town stands for the town
  and 3 km around it, a named county for the county. Sports stories count half (user, 2026-10-20), as in spillover.
  ATTRIBUTION (user, 2026-10-20: city, county and region mentions apply to the whole region, the larger the region the
  less weight): weight per hexagon = story weight x (A0 / A) ^ alpha, A = the region's hexagons, A0 = 7 (a hexagon and
  its ring: a neighbourhood or a town the size of Linn; smaller regions take full weight). Towns and neighbourhoods:
  alpha = 0.5 (env ALPHA). Counties and regions: alpha = 1 (env ALPHA_REGION), each story counted once -- the square
  root overvalued county-wide stories and county mentions (user, 2026-10-20) -- spread by where people live: each block
  group's 2020 population over the hexagons whose centres lie in it. A hexagon takes a story's strongest claim.
  "local" = the same without county-level points and county mentions.
  A hexagon's coverage = the weighted stories in the month whose area includes it. Tiers (user, 2026-10-19; renamed 2026-10-20):
  regular = 2+ a month (2-3 a month as the floor); frequent = 9+ a month (2-3 a week: 2 x 31/7); sporadic = under 2.
  "None" cannot occur in an area: every hexagon lies in a county, and every county in an area has county-level stories
  or mentions, which reach all of its hexagons (by population); the tier is reported for completeness.

Per area, with and without the home town: the share of the footprint's hexagons with any and with regular coverage;
the same from town- and point-scope stories alone (without whole-county stories); and the fewest outlets that together
give regular coverage (greedy: each step adds the outlet that brings the most hexagons closest to 4 stories) to 80% and
to all of the regularly covered hexagons.
Writes analysis/area_coverage_alignment.csv.
"""
import csv
import os
import json
import sys
from collections import defaultdict
from pathlib import Path

from shapely.geometry import Point, shape

root = Path(__file__).resolve().parents[1]
flows = root / "flows"
REGION = os.environ.get("REGION", "columbia")          # any region of flows/regions.json
sys.argv = ["market_patterns.py", REGION]
src = (flows / "market_patterns.py").read_text().split("# DASYMETRIC TRAVEL")[0]
# read-only: write nothing. Neutralise the open(..., "w") as well as the dump -- opening for writing empties the file
# even when nothing is written (it emptied market_patterns.json, 2026-10-20/21)
src = src.replace("json.dump(", "(lambda *a, **k: None)(").replace('open(R / "market_patterns.json", "w")', "None")
assert '"w")' not in src, "market_patterns.py opens another file for writing before the cut; neutralise it here"
ns = {"__file__": str(flows / "market_patterns.py"), "__name__": "coverage_lib"}
exec(compile(src, "market_patterns.py", "exec"), ns)
pts, plc, place_hexes, county_hexes, hex_of = ns["pts"], ns["plc"], ns["place_hexes"], ns["county_hexes"], ns["hex_of"]
by_outlet, cov_unit, CIN = ns["by_outlet"], ns["cov_unit"], ns["cin"]
TIERS = {"regular": 2.0, "frequent": 9.0}   # never "weekly"/"daily": those name publications (user, 2026-10-20)
qr = lambda k: tuple(map(int, k.split(",")))
NB = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]
ring = lambda hs: set(hs) | {f"{a + dq},{b + dr}" for a, b in map(qr, hs) for dq, dr in NB}

art_out = {a["id"]: o for o, arts in by_outlet.items() for a in arts}
# outlet -> hexagon -> weighted stories; "local" = town- and point-scope stories only
cov = {"all": defaultdict(lambda: defaultdict(float)), "local": defaultdict(lambda: defaultdict(float))}


def credit(o, hs, w, local):
    for k in hs:
        cov["all"][o][k] += w
        if local:
            cov["local"][o][k] += w


import math  # noqa: E402

import pandas as pd  # noqa: E402

SCOPE = pd.read_csv(root / "coverage/storymap/statewide_2026_03_scope.csv").set_index("article_id").scope.fillna("")
KM = {"neighborhood_community": 3.0, "regional": 40.0}
TOWN = {"city_municipality", "elsewhere_to_local", "local_to_elsewhere", ""}
hexes, pl_shapes = ns["hexes"], ns["pl_shapes"]
hc = {k: (sum(c[0] for c in v[:6]) / 6, sum(c[1] for c in v[:6]) / 6) for k, v in hexes.items()}
KX = 111.32 * math.cos(math.radians(38.6))
from shapely.strtree import STRtree  # noqa: E402
_ids = list(hc)
_tree = STRtree([Point(*hc[k]) for k in _ids])
_mo_places = [g_ for g_ in pl_shapes if g_.startswith("29")]
_ptree = STRtree([pl_shapes[g_][1] for g_ in _mo_places])


def within_km(lon, lat, km):
    box = Point(lon, lat).buffer(km / 110.57 * 1.6)
    return [_ids[i] for i in _tree.query(box)
            if math.hypot((hc[_ids[i]][0] - lon) * KX, (hc[_ids[i]][1] - lat) * 110.57) <= km]


from functools import lru_cache  # noqa: E402

from shapely.ops import transform as _tf  # noqa: E402

_KXP, _KYP = 111.32 * math.cos(math.radians(38.7)), 110.57      # the hexagon plane, km


@lru_cache(maxsize=None)
def town_area(g_):
    """the town and 3 km around it -- buffered on the km plane (isotropic; 2026-10-24: was 3/110.57 degrees, 2.4 km
    east-west), as a set of hexagons"""
    gk = _tf(lambda x, y, z=None: (x * _KXP, y * _KYP), pl_shapes[g_][1]).buffer(3.0)
    geom = _tf(lambda x, y, z=None: (x / _KXP, y / _KYP), gk)
    return frozenset([_ids[i] for i in _tree.query(geom) if geom.contains(Point(*hc[_ids[i]]))]) | set(place_hexes(g_))


def town_at(lon, lat):
    pt_ = Point(lon, lat)
    return next((_mo_places[i] for i in _ptree.query(pt_) if pl_shapes[_mo_places[i]][1].contains(pt_)), None)


story_area = {}                       # article -> (hexagons, local: not a county-only point)
for r in pts.itertuples():
    if r.article_id not in art_out:
        continue
    sc = SCOPE.get(r.article_id, "")
    lvl, has_pt = r.point_geoid_level, r.point_lat == r.point_lat
    if lvl == "county":
        if sc in KM or sc in TOWN:
            story_area[r.article_id] = (set(county_hexes.get(r.point_geoid, [])), False, True)
        continue
    if lvl not in ("block", "place"):
        continue
    if sc in KM and has_pt:
        story_area[r.article_id] = (set(within_km(r.point_lon, r.point_lat, KM[sc])), True, sc == "regional")
    elif sc in TOWN:
        g_ = r.point_geoid if lvl == "place" else (town_at(r.point_lon, r.point_lat) if has_pt else None)
        if g_ in pl_shapes:
            story_area[r.article_id] = (town_area(g_), True, False)
        elif has_pt:
            story_area[r.article_id] = (set(within_km(r.point_lon, r.point_lat, 5.0)), True, False)
import os  # noqa: E402

ALPHA, A0 = float(os.environ.get("ALPHA", 0.5)), 7
# counties and regions are counted once (user, 2026-10-20: the square root "overvalues mentions and county-wide coverage")
ALPHA_REGION = float(os.environ.get("ALPHA_REGION", 1.0))
# population by hexagon: each block group's 2020 population over the hexagons whose centres lie in it (the block
# group's population centre's hexagon when none does)
bgs = ns["bgs"]
_bg_ids = list(bgs)
_bg_tree = STRtree([bgs[b][1] for b in _bg_ids])
hex_bg = {}
for k, (x_, y_) in hc.items():
    pt_ = Point(x_, y_)
    hit = [_bg_ids[i] for i in _bg_tree.query(pt_) if bgs[_bg_ids[i]][1].contains(pt_)]
    if hit:
        hex_bg[k] = hit[0]
bg_hexes = defaultdict(list)
for k, b_ in hex_bg.items():
    bg_hexes[b_].append(k)
cp_bg = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_BG29.txt", dtype=str, encoding="utf-8-sig")
hex_pop = defaultdict(float)
for r in cp_bg.itertuples():
    g_ = r.STATEFP + r.COUNTYFP + r.TRACTCE + r.BLKGRPCE
    hs_ = bg_hexes.get(g_) or ([hex_of(float(r.LONGITUDE), float(r.LATITUDE))] if hex_of(float(r.LONGITUDE), float(r.LATITUDE)) else [])
    for k in hs_:
        hex_pop[k] += float(r.POPULATION) / len(hs_)


def attribute(hs, w, by_pop):
    """per-hexagon weight of a story's claim on region hs: w x (A0/A)^ALPHA, spread by population when by_pop"""
    hs = list(hs)
    if not hs:
        return {}
    per = w * min(1.0, (A0 / len(hs)) ** (ALPHA_REGION if by_pop else ALPHA))
    if not by_pop:
        return {k: per for k in hs}
    tot_pop = sum(hex_pop.get(k, 0) for k in hs)
    if tot_pop <= 0:
        return {k: per for k in hs}
    # spread by population, CAPPED at the story's weight w per hexagon (2026-10-24, peer review): a county story spread
    # by population put up to several stories' weight on one dense hexagon (a county seat's centre)
    return {k: min(w, per * len(hs) * hex_pop.get(k, 0) / tot_pop) for k in hs}


story_hexes = defaultdict(dict)                 # article -> hexagon -> (weight, local), the strongest claim kept


def claim(aid, wts, local):
    for k, w in wts.items():
        if story_hexes[aid].get(k, (0, False))[0] < w:
            story_hexes[aid][k] = (w, local)


for aid, (hs, local, by_pop) in story_area.items():
    claim(aid, attribute(hs, 1.0, by_pop), local)
for r in plc.itertuples():
    # a statewide, national or international story's mentions are not local coverage of the places it names (Pemiscot
    # Press, Sikeston, KCTV5 read as regular sources for Columbia through them)
    if r.article_id not in art_out or SCOPE.get(r.article_id, "") in {"statewide", "national", "international", "other"}:
        continue
    if r.geoid_level == "place" and r.geoid in pl_shapes:
        claim(r.article_id, attribute(town_area(r.geoid), 0.5, False), True)
    elif r.geoid_level == "county":
        claim(r.article_id, attribute(county_hexes.get(r.geoid, []), 0.5, True), False)
SPORTS_W = 0.5   # Sports stories count half (user, 2026-10-20), as in spillover: a game involves two places by nature
COVCAT = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))   # CIN category -> outlet -> hexagon -> weight
for aid, hs in story_hexes.items():
    sw = SPORTS_W if CIN.get(aid) == "Sports" else 1.0
    cat = CIN.get(aid)
    for k, (w, local) in hs.items():
        credit(art_out[aid], [k], w * sw, local)
        if isinstance(cat, str):
            COVCAT[cat][art_out[aid]][k] += w * sw
print("stories with a local area:", len(story_area), "of", sum(1 for a in art_out), flush=True)

RDIR = flows / "reach" if REGION == "columbia" else flows / "reach" / REGION
MAPS = json.load(open(RDIR / "market_pattern_maps.json"))
CONF = json.load(open(RDIR / ("confidence_columbia.json" if REGION == "columbia" else "confidence.json")))
# the study's three towns in the Columbia region; every town's areas elsewhere
AREAS = ([(t, m["rank"]) for t in ("Columbia", "Mexico", "Linn") for m in MAPS["towns"][t]] if REGION == "columbia"
         else [(t, m["rank"]) for t, ms in MAPS["towns"].items() for m in ms if str(m["rank"]) in CONF.get(t, {})])
SUFFIX = "" if REGION == "columbia" else f"_{REGION}"
rows = []
for town, rank in ([] if os.environ.get("COV_LIB") == "1" else AREAS):
    m = next(x for x in MAPS["towns"][town] if x["rank"] == rank)
    outline = shape(CONF[town][str(rank)]["outline_travel"])
    area = [k for k, v in MAPS["hexes"].items()
            if outline.contains(Point(sum(c[0] for c in v[:6]) / 6, sum(c[1] for c in v[:6]) / 6))]
    home = {k for k in area if m["index"]["travel"].get(k, 0) >= 100}
    for scope in ("with home town", "outside home town"):
        hs = [k for k in area if scope == "with home town" or k not in home]
        mass = {k: 1.0 for k in hs}
        tot = len(hs)
        row = {"area": f"{town} {'I' * rank}", "scope": scope, "hexagons": len(hs), "km2": round(len(hs) * ns["HEX_KM2"]),
               "people_inside": round(sum(hex_pop.get(k, 0) for k in hs)), "residents_allocated": m["residents"]}
        for kind in ("all", "local"):
            cv = {k: sum(cov[kind][o].get(k, 0) for o in cov[kind]) for k in hs}
            row[f"{kind}: any"] = round(sum(1 for k in hs if cv[k] > 0) / tot, 2)
            row[f"{kind}: none"] = round(sum(1 for k in hs if cv[k] == 0) / tot, 2)
            row[f"{kind}: sporadic"] = round(sum(1 for k in hs if 0 < cv[k] < TIERS["regular"]) / tot, 2)
            row[f"{kind}: outlets any"] = sum(1 for o in cov[kind] if any(cov[kind][o].get(k, 0) for k in hs))
            for tier, REG in TIERS.items():
                reg = [k for k in hs if cv[k] >= REG]
                row[f"{kind}: {tier}"] = round(len(reg) / tot, 2)
                c, chosen, steps = defaultdict(float), [], {}
                cand = [o for o in cov[kind] if any(cov[kind][o].get(k, 0) for k in reg)]
                while reg and len(chosen) < len(cand):
                    def gain(o):
                        return sum(min(REG, c[k] + cov[kind][o].get(k, 0)) - min(REG, c[k]) for k in reg)
                    o = max((o for o in cand if o not in chosen), key=gain)
                    if gain(o) <= 0:
                        break
                    chosen.append(o)
                    for k in reg:
                        c[k] += cov[kind][o].get(k, 0)
                    done = sum(1 for k in reg if c[k] >= REG) / len(reg)
                    for q in (0.8, 1.0):
                        if q not in steps and done >= q - 1e-9:
                            steps[q] = len(chosen)
                row[f"{kind}: {tier} outlets 80%/all"] = f"{steps.get(0.8)}/{steps.get(1.0)}"
                row[f"{kind}: {tier} outlets"] = "; ".join(chosen[:steps.get(1.0, len(chosen))])
        rows.append(row)
        print(row)
if rows:
    with open(root / f"analysis/area_coverage_alignment{SUFFIX}{'' if ALPHA == 0.5 else f'_alpha{ALPHA:g}'}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

# MAP LAYER (market_pattern_print.html ?measure=coverage): each footprint hexagon's stories a month, all and local
layer = {}
CIRCLE_MIN_HEX, CIRCLE_Q = 3, 0.5
# each outlet's story locations: (lon, lat, weight) -- central location 1, each mention 0.5; statewide and wider scopes out
_cp = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
CO_LL = {r.STATEFP + r.COUNTYFP: (float(r.LONGITUDE), float(r.LATITUDE)) for r in _cp.itertuples()}
WIDE = {"statewide", "national", "international", "other"}


def _ll(level, geoid, lon, lat):
    if level == "block" and lat == lat:
        return float(lon), float(lat)
    if level == "place" and geoid in pl_shapes:
        c_ = pl_shapes[geoid][1].representative_point(); return c_.x, c_.y
    if level == "county" and geoid in CO_LL:
        return CO_LL[geoid]
    return None


STORY_PTS = defaultdict(list)
for r in pts.itertuples():
    o = art_out.get(r.article_id)
    if o and SCOPE.get(r.article_id, "") not in WIDE:
        ll = _ll(r.point_geoid_level, r.point_geoid, r.point_lon, r.point_lat)
        if ll:
            STORY_PTS[o].append((*ll, 1.0 * (0.5 if CIN.get(r.article_id) == "Sports" else 1.0)))
for r in plc.drop_duplicates(["article_id", "geoid"]).itertuples():
    o = art_out.get(r.article_id)
    if o and SCOPE.get(r.article_id, "") not in WIDE:
        ll = _ll(r.geoid_level, r.geoid, None, float("nan"))
        if ll:
            STORY_PTS[o].append((*ll, 0.5 * (0.5 if CIN.get(r.article_id) == "Sports" else 1.0)))
sys.path.insert(0, str(root / "analysis"))
from excluded_outlets import registry  # noqa: E402

_reg = registry()                      # pinned (data/registry)
_reg = _reg[_reg.state == "MO"].dropna(subset=["lat", "lon"]).drop_duplicates("outlet")
REG_LL = {r.outlet: (float(r.lon), float(r.lat)) for r in _reg.itertuples()}
# an outlet homed in the county it covers (excluded_outlets.HOME_COUNTY) is centred on that county's seat
# (market_patterns.HOME_TOWN: St. Charles city, Springfield), not on its office in another county
for o_, g_ in ns["HOME_TOWN"].items():
    if g_ in pl_shapes:
        c_ = pl_shapes[g_][1].representative_point()
        REG_LL[o_] = (c_.x, c_.y)
for town, rank in AREAS:
    outline = shape(CONF[town][str(rank)]["outline_travel"])
    area = [k for k, v in MAPS["hexes"].items()
            if outline.contains(Point(sum(c[0] for c in v[:6]) / 6, sum(c[1] for c in v[:6]) / 6))]
    layer.setdefault(town, {})[rank] = {kind: {k: round(sum(cov[kind][o].get(k, 0) for o in cov[kind]), 2) for k in area}
                                        for kind in ("all", "local")}
    layer[town][rank]["pop"] = {k: round(hex_pop.get(k, 0)) for k in area}
    # OUTLET CIRCLES (user, 2026-10-20: sources are pinned to a place, so a circle for the statistical bounds of each one's
    # contribution): centred on the newsroom (registry office); radius = the distance from it holding half the outlet's
    # story weight, story by story (central location 1, each place or county mentioned 0.5; a county at its population
    # centre; statewide and wider stories left out). Drawn for the outlets that alone give regular coverage (2+ a month)
    # to 3+ hexagons of the area
    # revised (13 overlapping circles were unreadable): the outlets that are the largest single source for 3+ hexagons of
    # the area, and a radius holding half the outlet's story weight -- the core-area convention the areas use
    lead = defaultdict(int)
    for k in area:
        best = max(((hw.get(k, 0), o) for o, hw in cov["all"].items()), default=(0, None))
        if best[0] > 0:
            lead[best[1]] += 1
    circles = []
    for o, hw in cov["all"].items():
        n_reg = lead.get(o, 0)
        if n_reg < CIRCLE_MIN_HEX or o not in REG_LL or o not in STORY_PTS:
            continue
        lon0, lat0 = REG_LL[o]
        d = sorted((math.hypot((x - lon0) * KX, (y - lat0) * 110.57), w) for x, y, w in STORY_PTS[o])
        tw, acc, r80 = sum(w for _, w in d), 0.0, 0.0
        for dist, w in d:
            acc += w; r80 = dist
            if acc >= CIRCLE_Q * tw:
                break
        circles.append({"outlet": o, "lon": lon0, "lat": lat0, "r_km": round(max(r80, 1.5), 1), "share": n_reg / len(area)})
    layer[town][rank]["outlets"] = sorted(circles, key=lambda c: -c["share"])
json.dump(layer, open(flows / f"reach/coverage_{REGION}{'' if ALPHA == 0.5 else f'_alpha{ALPHA:g}'}.json", "w"))


# SYNDICATION CHECK: the stories that make distant outlets regular sources for an area (env SYNDCHECK=1)
if os.environ.get("SYNDCHECK") == "1":
    SUSPECT = {"Pemiscot Press", "KCTV5", "Springfield Daily Citizen", "KQTV", "St. Louis Post-Dispatch", "St. Louis American",
               "Sikeston Standard Democrat", "Springfield News-Leader", "KZRG", "KMOV CBS", "KPLR11/Fox 2 Now", "KFVS 12", "KSPR/KY3",
               "STL Public Radio", "The Kansas City Star", "KC Magazine", "KMBC News 9", "KHQA 7", "KTVO CBS", "North West Missourian"}
    allarea = set()
    for town, rank in AREAS:
        outline = shape(CONF[town][str(rank)]["outline_travel"])
        allarea |= {k for k, v in MAPS["hexes"].items()
                    if outline.contains(Point(sum(c[0] for c in v[:6]) / 6, sum(c[1] for c in v[:6]) / 6))}
    out_rows = []
    for aid, hs in story_hexes.items():
        o = art_out[aid]
        if o in SUSPECT:
            w_in = sum(w for k, (w, _) in hs.items() if k in allarea)
            if w_in > 0:
                out_rows.append({"article_id": aid, "outlet": o, "scope": SCOPE.get(aid, ""), "weight_in_areas": round(w_in, 2)})
    pd.DataFrame(out_rows).sort_values(["outlet", "weight_in_areas"], ascending=[True, False]).to_csv(
        root / "analysis/syndication_check_areas.csv", index=False)
    print("syndication check:", len(out_rows), "stories")
