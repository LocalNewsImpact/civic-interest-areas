"""Revealed media markets by travel pattern: demand (crossover) and supply (spillover both ways) for each county pair.

For each study town and each travel pattern (travel_patterns.py), ranked by the estimated residents who follow it:
  DEMAND  crossover: the town's residents following the pattern x the share of the pattern's travel in county j
  SUPPLY  spillover both ways, March 2026, local outlets (statewide outlets excluded), weighted as the adopted spillover
          measure (centred 1, mention 0.5, Sports half): home county outlets' share of stories about j, and county j's
          outlets' share of stories about the home county
A pattern's market is its counties, each with its demand and its two supply shares.
Writes flows/reach/market_patterns.json.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

here = Path(__file__).parent
# ONE TV MARKET PER RUN (flows/regions.json)
REGION = sys.argv[1] if len(sys.argv) > 1 else "columbia"
CFG = json.load(open(here / "regions.json"))[REGION]
R = here.parent / CFG["out"]
sys.path.insert(0, str(here.parent / "analysis"))
from excluded_outlets import EXCLUDE, HOME_COUNTY, home_fips, registry  # noqa: E402

P = json.load(open(R / "patterns.json"))
cov = pd.read_csv(here.parent / "analysis/county_covariates.csv", dtype={"fips": str}).set_index("fips")
cname = cov.name.to_dict()
by_name = {n.lower(): f for f, n in cname.items()}
by_name.update({"st. louis": "29189", "st louis": "29189", "st. louis city": "29510"})
fips_of = lambda n: by_name.get((n or "").lower().replace(" county", "").strip())
# AN OUTLET'S HOME COUNTY (user, 2026-10-24): the county it is filed under, except the two outlets homed in the county
# they cover (excluded_outlets.HOME_COUNTY: Mid Rivers Newsmagazine -> St. Charles, Greene County Commonwealth -> Greene)
home_of = lambda a: home_fips(a["publisher"], fips_of(a["publisher_county"]))
# ...and their home TOWN, for the incoming tie (outlets based in a hexagon's town): the covered county's seat --
# St. Charles city (2964082; the county's largest town is O'Fallon) and Springfield (2970000, seat and largest)
HOME_TOWN = {o_: g_ for o_, g_ in {"Mid Rivers Newsmagazine": "2964082", "Greene County Commonwealth": "2970000"}.items()
             if o_ in HOME_COUNTY}
assert set(HOME_TOWN) == set(HOME_COUNTY), "a HOME_COUNTY outlet without a home town"
cin = pd.read_csv(here.parent / "coverage/cin_labels_2026_03.csv").set_index("id").primary_label
arts = json.load(open(here.parent / "coverage/storymap/statewide_2026_03_articles.json"))["articles"]
n_stories, about = defaultdict(int), defaultdict(float)
for a in arts:
    i = home_of(a)
    if not i or not a["counties"] or a["publisher"] in EXCLUDE:
        continue
    n_stories[i] += 1
    sw = 0.5 if cin.get(a["id"]) == "Sports" else 1
    for c in set(a["counties"]):
        if c != i:
            about[(i, c)] += sw * (1 if c == a["central"] else 0.5)
spill = lambda i, j: about[(i, j)] / n_stories[i] if n_stories[i] else None

# TOWNS: name -> (home county, 2020 place), from the market's config
TOWNS = {t_: tuple(v_) for t_, v_ in CFG["towns"].items()}
_pe = pd.read_csv(here.parent / "census_dl/ref/sub-est2024_29.csv", dtype=str, encoding="latin-1")
POP = {r_.STATE + r_.PLACE: int(r_.POPESTIMATE2024) for r_ in _pe[_pe.SUMLEV == "162"].itertuples()}
STUDY = {t_: c_ for t_, (c_, _) in TOWNS.items()}
HOME_PLACE = {t_: p_ for t_, (_, p_) in TOWNS.items()}
import numpy as np
hm_ = pd.read_csv(R / "homes.csv", dtype={"home_cbg": str, "place": str}).set_index("home_cbg")
# a town's home block groups: those homes.csv assigns to it (centre in the town, or 10%+ of the town inside)
town_bgs = lambda town: [h for h in hm_.index if hm_.town.get(h) == town or hm_.place.get(h) == HOME_PLACE[town]]
people_a, member_a = np.array(P["people"]), np.array(P["member"])
Wa, Ha, Xa = np.array(P["W"]), np.array(P["H"]), np.array(P["X"])
out = {}
for town, home in STUDY.items():
    hbi = [P["homes"].index(h) for h in town_bgs(town) if h in P["homes"]]
    ppl = (people_a[hbi, None] * member_a[hbi]).sum(0)
    t = {"people": [round(float(x)) for x in ppl], "share": [float(x) for x in ppl / ppl.sum()]}
    # THE TOWN'S OWN TRAVEL IN EACH PATTERN: a pattern is fitted across all 158 block groups, so it carries other
    # places' trips (Osage's pattern takes southern Osage residents to Maries). Each of the town's block groups'
    # observed travel to a place is split across the patterns by the share each explains there (the mixture's
    # responsibilities, W[h,k] H[k,u] / sum_j W[h,j] H[j,u]).
    hb = hbi
    Wm, Xm = Wa[hb], Xa[hb]
    den = np.maximum(Wm @ Ha, 1e-9)
    own = {k: (Xm * (Wm[:, k:k + 1] * Ha[k][None, :] / den)).sum(0) for k in range(P["K"])}
    # each pattern is its own market: Columbia's three share the Boone core and part beyond it (outside Boone their
    # county shares agree at 0.67 or less) -- south toward Jefferson City, east-west along I-70, north toward Moberly
    groups = [[k] for k in sorted(range(P["K"]), key=lambda k: -t["people"][k])]
    out[town] = []
    print(f"\n## {town}")
    # A MARKET needs 10%+ of the town's residents (adopted 2026-10-17) AND, for a secondary or tertiary market, 1,000+
    # residents (adopted 2026-10-18: below 1,000 a market's map spreads thinly -- Mexico's secondary, 729 residents,
    # showed 389 hexagons, 72% of them holding in both halves of the year; analysis/market_stability.py); the primary is
    # always kept
    MIN_SHARE, MIN_RESIDENTS = 0.10, 1000
    groups = [g_ for i_, g_ in enumerate(groups[:3]) if i_ == 0 or (sum(t["share"][k] for k in g_) >= MIN_SHARE
                                                                    and sum(t["people"][k] for k in g_) >= MIN_RESIDENTS)]
    for rank, g_ in enumerate(groups):
        trav = sum(own[k] for k in g_)
        trav = trav / trav.max()
        H = {u: float(x) for u, x in zip(P["units"], trav) if x > 0}
        people = sum(t["people"][k] for k in g_)
        share = sum(t["share"][k] for k in g_)
        by_c = defaultdict(float)
        for u, w in H.items():
            by_c[P["unit_county"][u]] += w
        tot = sum(by_c.values())
        top = [u for u, _ in sorted(H.items(), key=lambda z: -z[1])[:4]]
        rows = []
        for j, w in sorted(by_c.items(), key=lambda z: -z[1]):
            if w / tot < 0.05:
                continue
            rows.append({"county": j, "name": cname.get(j, j), "travel_share": round(w / tot, 3),
                         "crossover_residents": round(people * w / tot),
                         "spill_home_to_j": None if j == home or spill(home, j) is None else round(spill(home, j), 3),
                         "spill_j_to_home": None if j == home or spill(j, home) is None else round(spill(j, home), 3)})
        label = " / ".join(P["unit_name"][u] if not u.startswith("rural:") else "rural " + cname.get(u[6:11], u[6:11]) for u in top)
        # DIRECTION: the pattern's most-travelled towns of 2,500+ (the map's label cut) outside the home county
        ext_towns = sorted(((u, w) for u, w in H.items() if not u.startswith("rural:") and len(u) == 7
                            and P["unit_county"].get(u) != home and POP.get(u, 0) >= 2500), key=lambda z: -z[1])
        # named only if it carries 10%+ of the busiest place's weight: a trace of travel is not a direction
        toward = [P["unit_name"][u] for u, w in ext_towns[:2] if w >= 0.5 * ext_towns[0][1] and w >= 0.10] if ext_towns else []
        out[town].append({"rank": rank + 1, "patterns": g_, "label": label, "toward": toward, "residents": people, "share": round(share, 3),
                          "counties": rows, "travel": H})
        print(f"{['primary', 'secondary', 'tertiary'][rank]}: pattern {g_[0]} toward {' and '.join(toward)} ~{people:,} residents ({share:.0%})")
        for r in rows:
            s1 = "-" if r["spill_home_to_j"] is None else f"{r['spill_home_to_j']:.1%}"
            s2 = "-" if r["spill_j_to_home"] is None else f"{r['spill_j_to_home']:.1%}"
            print(f"   {r['name']:14} travel {r['travel_share']:.0%}  crossover ~{r['crossover_residents']:,}  "
                  f"spillover home->j {s1}  j->home {s2}")
json.dump({t_: [{k: v for k, v in m_.items() if k != "travel"} for m_ in ms] for t_, ms in out.items()}, open(R / "market_patterns.json", "w"), indent=1)

# MAP DATA: a hexagon grid, 3 km across, over the whole market -- the figure is a model, not an observed choropleth.
# Each hexagon takes its centre's unit's weight in the pattern (the town, or the rural block group, it falls in). Drawn:
# hexagons of 5+, with one ring of empty hexagons around them as a border (the figure's code).
import math
from shapely.geometry import Point
from shapely.strtree import STRtree
__file__ = str(here / "build_cousub_shares.py")
exec(open(here / "build_cousub_shares.py").read().split("\ndef cw(")[0])
bgs = read_shp(str(DL / "bg/cb_2020_29_bg_500k"), lambda r: r["GEOID"])
DMA = sorted({b[:5] for b in bgs})       # ALL OF MISSOURI: the frame comes from each town's market, not a TV market
ids = list(bgs)
tree = STRtree([bgs[b][1] for b in ids])
LAT0, SIZE = 38.7, 1.5                                   # circumradius in km: 3 km across
kx, ky = 111.32 * math.cos(math.radians(LAT0)), 110.57
xs = [bgs[b][1].bounds for b in ids]
x0, y0 = min(v[0] for v in xs) * kx, min(v[1] for v in xs) * ky
x1, y1 = max(v[2] for v in xs) * kx, max(v[3] for v in xs) * ky
hexes, unit_at = {}, {}
for r in range(int(y0 / (1.5 * SIZE)) - 1, int(y1 / (1.5 * SIZE)) + 2):
    for q in range(int(x0 / (math.sqrt(3) * SIZE) - r / 2) - 1, int(x1 / (math.sqrt(3) * SIZE) - r / 2) + 2):
        cx, cy = SIZE * math.sqrt(3) * (q + r / 2), SIZE * 1.5 * r
        pt = Point(cx / kx, cy / ky)
        hit = [ids[i] for i in tree.query(pt) if bgs[ids[i]][1].contains(pt)]
        if not hit:
            continue
        k = f"{q},{r}"
        unit_at[k] = P["bg_unit"].get(hit[0])
        hexes[k] = [[round((cx + SIZE * math.cos(math.radians(60 * i - 30))) / kx, 5),
                     round((cy + SIZE * math.sin(math.radians(60 * i - 30))) / ky, 5)] for i in range(7)]
# COVERAGE BY HEXAGON. A story's weight goes where it is located, spread evenly over the hexagons it is relevant to:
#   a precise point (block level)       the hexagon holding it
#   a town (point or named place)       spread over the town's hexagons (those whose centre is in the place; a town
#                                       smaller than a hexagon: the one holding its centre)
#   a county only (point or named)      spread over the county's hexagons
# Central location 1, each other location named 0.5; Sports half; local outlets only (statewide outlets excluded).
#   out(h) = the home county outlets' coverage of h's unit (its town, or its rural block group: the hexagons' credit
#            summed) / their coverage of the home town (cap 1) -- a town compared whole, as travel compares it
#   in(h)  = for the outlets based in h's town (registry city): the share of their coverage in the home county / the
#            same share for the home county's own outlets (cap 1); the home town is 1 both ways
pts = pd.read_csv(here / "reach/march_story_points.csv", dtype={"point_geoid": str})
plc = pd.read_csv(here / "reach/march_story_places.csv", dtype={"geoid": str})
pl_shapes = read_shp(str(DL / "place/cb_2020_29_place_500k"), lambda r: r["GEOID"])
centre = {k: (sum(c[0] for c in v[:6]) / 6, sum(c[1] for c in v[:6]) / 6) for k, v in hexes.items()}
hex_county = {k: (P["unit_county"].get(u) or "") for k, u in unit_at.items()}


def hex_of(lon, lat):
    x, y = lon * kx, lat * ky
    qf, rf = (math.sqrt(3) / 3 * x - y / 3) / SIZE, (2 / 3 * y) / SIZE
    sf = -qf - rf
    rq, rr, rs = round(qf), round(rf), round(sf)
    dq, dr, ds = abs(rq - qf), abs(rr - rf), abs(rs - sf)
    if dq > dr and dq > ds:
        rq = -rr - rs
    elif dr > ds:
        rr = -rq - rs
    k = f"{rq},{rr}"
    return k if k in hexes else None


hex_tree_ids = list(centre)
hex_tree = STRtree([Point(*centre[k]) for k in hex_tree_ids])
_place_hexes = {}


def place_hexes(g_):
    if g_ not in _place_hexes:
        hs = []
        if g_ in pl_shapes:
            geom = pl_shapes[g_][1]
            hs = [hex_tree_ids[i] for i in hex_tree.query(geom) if geom.contains(Point(*centre[hex_tree_ids[i]]))]
            if not hs:
                c_ = geom.representative_point()
                h_ = hex_of(c_.x, c_.y)
                hs = [h_] if h_ else []
        _place_hexes[g_] = hs
    return _place_hexes[g_]


county_hexes = defaultdict(list)
for k, c in hex_county.items():
    county_hexes[c].append(k)


def spread(targets, w, acc):
    if targets:
        for k in targets:
            acc[k] = max(acc.get(k, 0), w / len(targets))


credit = defaultdict(dict)                                  # article -> hexagon -> weight
for r in pts.itertuples():
    acc = credit[r.article_id]
    if r.point_geoid_level == "block" and r.point_lat == r.point_lat:
        spread([hex_of(r.point_lon, r.point_lat)] if hex_of(r.point_lon, r.point_lat) else [], 1.0, acc)
    elif r.point_geoid_level == "place":
        spread(place_hexes(r.point_geoid), 1.0, acc)
    elif r.point_geoid_level == "county":
        spread(county_hexes.get(r.point_geoid, []), 1.0, acc)
central = {a_: dict(v_) for a_, v_ in credit.items()}      # central focus alone (before mentions): the story map's dots
for r in plc.itertuples():
    acc = credit[r.article_id]
    if r.geoid_level == "place":
        spread(place_hexes(r.geoid), 0.5, acc)
    elif r.geoid_level == "county":
        spread(county_hexes.get(r.geoid, []), 0.5, acc)
reg = registry().dropna(subset=["lat", "lon"]).drop_duplicates("outlet").set_index("outlet")   # pinned (data/registry)
# an outlet's town by its registry city (a 3 km cell at a river or a town edge can fall in the next county)
place_by_name = {pl_shapes[g_][0]["NAME"].lower(): g_ for g_ in pl_shapes}
outlet_place = {o: HOME_TOWN.get(o) or place_by_name.get((r.city or "").lower()) for o, r in reg.iterrows()}
by_outlet = defaultdict(list)
for a in arts:
    if a["publisher"] not in EXCLUDE and a["counties"]:
        by_outlet[a["publisher"]].append(a)
# coverage unit of a hexagon: the town whose boundary holds its centre, else its rural block group
hex_place = {}
for g_ in pl_shapes:
    if g_.startswith("29"):
        for k in place_hexes(g_):
            if pl_shapes[g_][1].contains(Point(*centre[k])):
                hex_place[k] = g_
cov_unit = lambda k: hex_place.get(k) or unit_at.get(k)
# DASYMETRIC TRAVEL IN RURAL BLOCK GROUPS: Advan locates travel no finer than a block group, and a rural one can cover
# 30-60 hexagons. Its value is spread by where people go -- OpenStreetMap destinations (build_destinations.py): a
# hexagon's weight is (destinations in it + 0.25) / the block group's mean of the same, so the block group's average is
# kept, farmland falls toward 0.25 / (mean + 0.25) of it and a cluster of destinations rises (travel capped at 1).
# Towns keep one value. A floor of 1 left sparse rural counties (Barton: ~0.2 destinations a hexagon) one flat band.
DFLOOR = 0.25
dest = pd.read_csv(here / "reach/destinations_mo.csv", dtype={"block_group": str})
dest = dest[dest.block_group.str[:5].isin(DMA)]
dcount = defaultdict(int)
for x_, y_ in zip(dest.lon, dest.lat):
    k_ = hex_of(x_, y_)
    if k_:
        dcount[k_] += 1
by_unit = defaultdict(list)
for k_, u_ in unit_at.items():
    if u_ and u_.startswith("rural:"):
        by_unit[u_].append(k_)
DW = {}
for u_, ks in by_unit.items():
    m_ = np.mean([dcount.get(k_, 0) + DFLOOR for k_ in ks])
    for k_ in ks:
        DW[k_] = (dcount.get(k_, 0) + DFLOOR) / m_
# HEADROOM (2026-10-17): the busiest destination is 50, not 100 -- home stays 100, above any place visited, and news ties
# can lift the top destination toward home (Linn's news reaching Jefferson City) instead of finding it already capped
TRAVEL_TOP = 0.5
tr_at = lambda Hk, k, u: min(1.0, TRAVEL_TOP * Hk.get(u, 0) * DW.get(k, 1.0))
COV = {}
for town, home in STUDY.items():
    home_hexes = set(place_hexes(HOME_PLACE[town]))
    dens = defaultdict(float)
    for o, al in by_outlet.items():
        if home_of(al[0]) != home:
            continue
        for a in al:
            sw = 0.5 if cin.get(a["id"]) == "Sports" else 1
            for k, w in credit.get(a["id"], {}).items():
                dens[k] += sw * w
    base = sum(dens.get(k, 0) for k in home_hexes) or float("inf")   # no home outlets (Macon): no outgoing coverage
    unit_tot = defaultdict(float)
    for k, x in dens.items():
        unit_tot[cov_unit(k)] += x
    out_h = {k: min(1.0, unit_tot[cov_unit(k)] / base) for k in hexes if unit_tot.get(cov_unit(k))}
    # incoming: per outlet, its share of coverage in the home county; the outlet's town hexagons take it
    in_num, in_den, self_num, self_den = defaultdict(float), defaultdict(float), 0.0, 0.0
    outlet_town_hexes = {}
    for o, al in by_outlet.items():
        pg = outlet_place.get(o)
        hs = place_hexes(pg) if pg else []
        if not hs:
            continue
        own = home_of(al[0])
        outlet_town_hexes[o] = hs
        for a in al:
            sw = 0.5 if cin.get(a["id"]) == "Sports" else 1
            for k, w in credit.get(a["id"], {}).items():
                hit = sw * w * (hex_county.get(k) == home)
                in_num[o] += hit
                in_den[o] += sw * w
                if own == home:
                    self_num += hit
                    self_den += sw * w
    self_share = self_num / self_den if self_den else 0.6   # no home outlets: a typical home share as the reference
    in_h = {}
    for o, hs in outlet_town_hexes.items():
        if in_den[o] > 0:
            for k in hs:
                in_h[k] = max(in_h.get(k, 0), min(1.0, in_num[o] / in_den[o] / self_share))
    for k in home_hexes:
        out_h[k] = in_h[k] = 1.0
    # HOME COUNTY: home outlets' market is their county -- every hexagon of it carries their outgoing tie (2026-10-17)
    for k, c_ in hex_county.items():
        if c_ == home:
            out_h[k] = 1.0
    COV[town] = {"out": out_h, "in": in_h}
    shown = lambda g_: (np.mean([out_h.get(k, 0) for k in place_hexes(g_)]), np.mean([in_h.get(k, 0) for k in place_hexes(g_)]))
    print(f"{town}: " + ", ".join(f"{n_} {shown(HOME_PLACE[n_])[0]:.2f}/{shown(HOME_PLACE[n_])[1]:.2f}" for n_ in TOWNS if n_ != town))
SUPPLY_EXP = (0, 0.5, 1)
# NETWORK TIE (adopted 2026-10-17): local = where residents travel; coverage AMPLIFIES a travel tie, never makes one.
#   tie(H, X) = travel(H -> X) x (1 + 0.3 out + 0.3 in + 0.7 shared places + 0.7 shared coverage), capped at home
# Travel is worth more than coverage: the coverage weights sum to 2, so coverage at its strongest triples a travel tie
# and never lets a place travelled to a third as often overtake it (at most it ties). Shared places and shared coverage -- two places
# embedded in the same third places (network closure) -- carry most of it; the single direct ties less.
#   shared coverage  overlap coefficient between H's outlets' and X's outlets' coverage, third places only
#   out      H's outlets' coverage located at X / their coverage of home (cap 1)
#   in       X's outlets' share of coverage located in H's county / H's own outlets' share (cap 1)
#   overlap  overlap coefficient sum_Y min(H's travel share at Y, X's outlets' coverage share at Y), third places Y only
#            (not H's home, not X): where H's residents go and X's paper reports (Columbia residents in Centralia, which
#            the Mexico Ledger covers) strengthens the H-X pair, not Y -- Y's own tie is its own travel and coverage
# Equal weights: each coverage tie can at most double the travel tie. Sensitivity: each weight halved and doubled.
outlet_cov = {}
for o, al in by_outlet.items():
    d_ = defaultdict(float)
    for a in al:
        sw = 0.5 if cin.get(a["id"]) == "Sports" else 1
        for k, w in credit.get(a["id"], {}).items():
            u_ = unit_at.get(k)
            if u_:
                d_[u_] += sw * w
    if d_:
        outlet_cov[o] = d_
place_outlets = defaultdict(list)
for o, pg in outlet_place.items():
    if pg and o in outlet_cov and o not in EXCLUDE:
        place_outlets[pg].append(o)


def overlap_of(Hk, home_units, X):
    """Overlap coefficient between H's travel and X's outlets' coverage, over third places."""
    cx = defaultdict(float)
    for o in place_outlets.get(X, []):
        for u_, w in outlet_cov[o].items():
            cx[u_] += w
    drop = set(home_units) | {X}
    tH = {u_: w for u_, w in Hk.items() if u_ not in drop}
    cX = {u_: w for u_, w in cx.items() if u_ not in drop}
    st, sc = sum(tH.values()), sum(cX.values())
    if not st or not sc:
        return 0.0
    return sum(min(tH[u_] / st, cX.get(u_, 0) / sc) for u_ in tH)


def cov_dist(outlets):
    c_ = defaultdict(float)
    for o in outlets:
        for u_, w in outlet_cov.get(o, {}).items():
            c_[u_] += w
    return c_


def overlap_dists(a, b, drop):
    a = {u_: w for u_, w in a.items() if u_ not in drop}
    b = {u_: w for u_, w in b.items() if u_ not in drop}
    sa, sb = sum(a.values()), sum(b.values())
    if not sa or not sb:
        return 0.0
    return sum(min(w / sa, b.get(u_, 0) / sb) for u_, w in a.items())


# weights: out, in, shared places, shared coverage
BASE_W = (0.3, 0.3, 0.7, 0.7)          # raised from (0.15, 0.15, 0.35, 0.35) 2026-10-17: coverage at its strongest triples a tie
WEIGHTS = {"net": BASE_W}
# SPATIAL NETWORK EFFECT (2026-10-17), on the net tie:
#   adjacency  tie' = tie + 0.25 x (ring-weighted mean of neighbours' ties: ring 1 at 1/2, ring 2 at 1/4, ring 3 at 1/8,
#              rings normalised) -- a hexagon near a strong cluster rises; only where residents travel (tie > 0)
#   direction  x (1 + 0.5 R cos(bearing from home - the market's mean bearing)), R the tie-weighted resultant length
#              (0 = even all round, 1 = all one way): the market's direction strengthens, the opposite side weakens
LAMBDA, GAMMA, RINGS = 0.25, 0.5, ((1, 0.5), (2, 0.25), (3, 0.125))
_DIRS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]


def ring(q, r, n):
    out_, (cq, cr) = [], (q - n, r + n)
    for dq, dr in _DIRS:
        for _ in range(n):
            out_.append(f"{cq},{cr}"); cq += dq; cr += dr
    return out_


def spatial(raw, home):
    qr_ = {k: tuple(map(int, k.split(","))) for k in raw}
    boosted = {}
    for k, v in raw.items():
        q, r = qr_[k]
        lag = sum(w * np.mean([raw.get(n_, 0) for n_ in ring(q, r, d)]) for d, w in RINGS) / sum(w for _, w in RINGS)
        boosted[k] = v + LAMBDA * lag
    hc = [centre[k] for k in home if k in centre] or [centre[max(raw, key=raw.get)]]
    hx, hy = np.mean([c[0] for c in hc]), np.mean([c[1] for c in hc])
    ang = {k: math.atan2(centre[k][1] - hy, (centre[k][0] - hx) * math.cos(math.radians(LAT0))) for k in boosted if k in centre}
    wsum = sum(boosted[k] for k in ang if k not in home)
    cx = sum(boosted[k] * math.cos(a) for k, a in ang.items() if k not in home) / (wsum or 1)
    cy = sum(boosted[k] * math.sin(a) for k, a in ang.items() if k not in home) / (wsum or 1)
    R_, mean_ = math.hypot(cx, cy), math.atan2(cy, cx)
    return {k: min(1.0, v * (1 + GAMMA * R_ * math.cos(ang[k] - mean_)) if k in ang else v) for k, v in boosted.items()}
for i_, nm in enumerate(("out", "in", "shared places", "shared coverage")):
    for f_ in (0.5, 2):
        w_ = list(BASE_W); w_[i_] *= f_
        WEIGHTS[f"{nm} x{f_}"] = tuple(w_)
# HOME: the town's hexagons and every hexagon of its residents' own block groups (masked from their own travel -- nobody
# travels to home -- so they would read 0: Linn's block group around the town, Columbia's fringe block groups)
home_hexes_of = {}
for town in STUDY:
    own_units = {P["bg_unit"].get(h) for h in town_bgs(town)} | {"rural:" + h for h in town_bgs(town)}
    home_hexes_of[town] = set(place_hexes(HOME_PLACE[town])) | {k for k, u in unit_at.items() if u in own_units}
maps = {"hexes": hexes, "towns": {}}
for town, pats in out.items():
    maps["towns"][town] = []
    cu = COV[town]
    for pt in pats:
        Hk = pt["travel"]                                    # the town's own travel in this market
        v = {k: round(100 * tr_at(Hk, k, u), 1) for k, u in unit_at.items() if 100 * tr_at(Hk, k, u) >= 1}
        # LOCAL INDEX: travel x [(1 + out + in) / 3] ^ s, by hexagon; s = 1 adopted 2026-10-17 (demand and supply equal)
        idx = {}
        for sx in SUPPLY_EXP:
            raw = {k: tr_at(Hk, k, u) * ((1 + cu["out"].get(k, 0) + cu["in"].get(k, 0)) / 3) ** sx
                   for k, u in unit_at.items() if Hk.get(u, 0) > 0}
            idx[str(sx)] = {k: round(100 * x, 1) for k, x in raw.items() if 100 * x >= 1}
            for k in home_hexes_of[town]:                     # home is 100 by definition
                idx[str(sx)][k] = 100.0
        own_u = {P["bg_unit"].get(h) for h in town_bgs(town)} | {HOME_PLACE[town]}
        OV = {X: overlap_of(Hk, own_u, X) for X in place_outlets if X not in own_u}
        h_cov = cov_dist([o for o, al in by_outlet.items() if home_of(al[0]) == STUDY[town] and o not in EXCLUDE])
        # shared coverage counts only places in this town's own market (travel 0.05+ of the busiest): two newsrooms both
        # reporting statewide news (the capital, the university) is not a local tie
        mkt = {u_ for u_, w in Hk.items() if w >= 0.05}
        inm_ = lambda d_: {u_: w for u_, w in d_.items() if u_ in mkt}
        SC = {X: overlap_dists(inm_(h_cov), inm_(cov_dist(place_outlets[X])), own_u | {X}) for X in place_outlets if X not in own_u}
        for name_, (wo, wi, wv, wc) in WEIGHTS.items():
            raw = {}
            for k, u in unit_at.items():
                t_ = tr_at(Hk, k, u)
                if t_ <= 0:
                    continue
                xk = hex_place.get(k) or u
                # GATE: shared places and shared coverage count only for a pair that already covers each other (out + in
                # 0.10+ of home): both covering the capital is not a tie between Linn and Columbia (2026-10-17)
                o_, i_ = cu["out"].get(k, 0), cu["in"].get(k, 0)
                gate = 1.0 if (o_ + i_) >= 0.10 else 0.0
                amp = 1 + wo * o_ + wi * i_ + gate * (wv * OV.get(xk, 0) + wc * SC.get(xk, 0))
                raw[k] = min(1.0, t_ * amp)
            if name_ == "net":
                idx["cov"] = {k: round(100 * x, 1) for k, x in raw.items() if 100 * x >= 1}   # news ties only, for the dots
                # PROTOTYPE "netcov" (2026-10-18, not adopted): the coverage areas of the market's OWN newsrooms create
                # interest where residents do not travel. A newsroom's location matters only for membership: outlets based
                # in places inside the market's travel footprint (tie 5+), plus the home town's, belong to it; KRCG belongs to
                # a Callaway market, not to Columbia's. Interest = max(travel tie, 0.3 x max over the market's newsrooms of
                # residents' tie to the newsroom's town x the share of its coverage at the place, its top place = 1); and spillover
                # from every other newsroom into the market (below)
                news_w = {HOME_PLACE[town]: 1.0}
                for X_ in place_outlets:
                    hs_ = place_hexes(X_)
                    if X_ != HOME_PLACE[town] and hs_:
                        w_ = float(np.mean([raw.get(k_, 0) for k_ in hs_]))
                        if w_ >= 0.05:
                            news_w[X_] = w_
                ccell = defaultdict(float)
                for X_, w_ in news_w.items():
                    cd_ = cov_dist(place_outlets.get(X_, []))
                    if not cd_:
                        continue
                    mx_ = max(cd_.values())
                    for k_, u_ in unit_at.items():
                        if cd_.get(u_, 0) > 0:
                            ccell[k_] = max(ccell[k_], w_ * cd_[u_] / mx_)
                rawc = dict(raw)
                for k_, c_ in ccell.items():
                    rawc[k_] = max(rawc.get(k_, 0), 0.3 * c_)
                # SPILLOVER INTO THE MARKET: every other newsroom's coverage that lands inside the residents' travel
                # footprint is news about their area (KRCG and the Mexico Ledger reporting in Boone, for Columbia) -- it
                # raises the places it covers there by 0.3 x its share of that newsroom's coverage (top place = 1); what
                # outside newsrooms cover elsewhere does not count
                spill_in = defaultdict(float)
                for X_, outs_ in place_outlets.items():
                    if X_ in news_w:
                        continue
                    cd_ = cov_dist(outs_)
                    if not cd_:
                        continue
                    mx_ = max(cd_.values())
                    for k_, u_ in unit_at.items():
                        if raw.get(k_, 0) > 0 and cd_.get(u_, 0) > 0:
                            spill_in[k_] = max(spill_in[k_], cd_[u_] / mx_)
                for k_, c_ in spill_in.items():
                    rawc[k_] = min(1.0, rawc[k_] * (1 + 0.3 * c_))
                rawc = spatial(rawc, home_hexes_of[town])
                idx["netcov"] = {k_: round(100 * x_, 1) for k_, x_ in rawc.items() if 100 * x_ >= 1}
                for k_ in home_hexes_of[town]:
                    idx["netcov"][k_] = 100.0
                pt["newsrooms"] = {(pl_shapes[X_][0]["NAME"] if X_ in pl_shapes else X_): round(w_, 2) for X_, w_ in news_w.items()}
                raw = spatial(raw, home_hexes_of[town])
            idx[name_] = {k: round(100 * x, 1) for k, x in raw.items() if 100 * x >= 1}
            for k in home_hexes_of[town]:
                idx[name_][k] = 100.0
        if pt["rank"] == 1:
            nm_ = lambda X: P["unit_name"].get(X) or (pl_shapes[X][0]["NAME"] if X in pl_shapes else X)
            top_ov = sorted(((nm_(X), round(OV.get(X, 0), 2), round(SC.get(X, 0), 2)) for X in OV), key=lambda z: -(z[1] + z[2]))[:5]
            from scipy.stats import spearmanr
            base = idx["net"]
            ks_ = [k for k in base if base[k] >= 5 and base[k] < 100]
            sens = []
            for name_ in WEIGHTS:
                if name_ == "net":
                    continue
                alt = idx[name_]
                rho = spearmanr([base[k] for k in ks_], [alt.get(k, 0) for k in ks_]).statistic if len(ks_) > 2 else float("nan")
                bands = sum(np.digitize(base[k], [5, 10, 20, 40, 80]) != np.digitize(alt.get(k, 0), [5, 10, 20, 40, 80]) for k in ks_)
                sens.append(f"{name_} rho {rho:.3f} bands {bands}/{len(ks_)}")
            print(f"  NET {town}: (place, shared places, shared coverage) {top_ov}\n    " + "; ".join(sens))
        # DIRECTION FROM THE FINAL TIES (2026-10-17): the towns of 2,500+ outside the home county with the strongest
        # network tie (mean of their 3 strongest hexagons); the second named only if half the first. Travel alone named places the map
        # does not show (Kansas City for Columbia).
        tv = defaultdict(list)
        for k, v_ in idx["net"].items():
            pk = hex_place.get(k)
            if pk and POP.get(pk, 0) >= 2500 and hex_county.get(k) != STUDY[town] and v_ >= 5:
                tv[pk].append(v_)
        # a town's mean over its 3 strongest hexagons (missing count as 0): neither size nor one stray cell decides
        tsum = {pk: sum(sorted(vs, reverse=True)[:3]) / 3 for pk, vs in tv.items()}
        ranked = sorted(tsum.items(), key=lambda z: -z[1])
        pt["toward"] = [pl_shapes[pk][0]["NAME"] for pk, w in ranked[:2] if w >= 0.5 * ranked[0][1]] if ranked else []
        maps["towns"][town].append({**{k: pt[k] for k in ("rank", "label", "toward", "residents", "share", "counties")},
                                    "value": v, "index": {k_: v_ for k_, v_ in idx.items() if k_ in ("0", "1", "net", "cov", "netcov")},
                                    "newsrooms": pt.get("newsrooms", {})})
maps["home"] = {t_: {"county": c_, "lon": round(pl_shapes[p_][1].representative_point().x, 4),
                     "lat": round(pl_shapes[p_][1].representative_point().y, 4)} for t_, (c_, p_) in TOWNS.items()}
# FOR THE FIGURE (and the visual builder): the market, its counties and outline, town labels (2,500+ and the
# configured towns), each town's block-group count
from shapely.geometry import mapping
from shapely.ops import unary_union
dma_geom = unary_union([bgs[b][1] for b in bgs if b[:5] in CFG["dma_counties"]]).simplify(0.002)
pe_ = pd.read_csv(here.parent / "census_dl/ref/sub-est2024_29.csv", dtype=str, encoding="latin-1")
pop_ = {r_.STATE + r_.PLACE: int(r_.POPESTIMATE2024) for r_ in pe_[pe_.SUMLEV == "162"].itertuples()}
labels = []
for g_, (r_, geom) in pl_shapes.items():
    if (pop_.get(g_, 0) >= 2500 or g_ in HOME_PLACE.values()) and g_.startswith("29"):
        c_ = geom.representative_point()
        labels.append({"name": r_["NAME"], "pop": pop_.get(g_, 0), "lon": round(c_.x, 4), "lat": round(c_.y, 4)})
# hexagons inside the TV market, for the page's frame rule (the market unless 10%+ of a town's index is outside it)
maps["in_market"] = sorted(k for k in maps["hexes"] if hex_county.get(k) in CFG["dma_counties"])
# every Missouri place, for labelling an unlabelled cluster by its largest town (the page picks)
# STORY-MAP LAYER (prototype, 2026-10-17): the home county's local outlets' March stories on the same hexagons -- value =
# stories located there (central focus 1, each other named place or county 0.5; a town spread over its hexagons, a county
# over the county's); central = central-focus stories alone (the dots). Statewide outlets excluded.
maps["story"] = {}
for town, (c_, _) in TOWNS.items():
    val, cen = defaultdict(float), defaultdict(float)
    for o, al in by_outlet.items():
        if home_of(al[0]) != c_:
            continue
        for a in al:
            for k, w in credit.get(a["id"], {}).items():
                val[k] += w
            for k, w in central.get(a["id"], {}).items():
                cen[k] += w
    # CENTRAL FOCUS ON ITS FOOTPRINT, at full strength: a neighbourhood (block point) story shades its hexagon, a city
    # (place) story every hexagon of the city, a county story every hexagon of the county; each hexagon counts the stories
    # centred on it. MENTIONS likewise, kept apart -- the weaker signal, drawn faint. State-level focus has no footprint.
    ids_ = {a["id"] for o, al in by_outlet.items() if home_of(al[0]) == c_ for a in al}
    cfp, mfp = defaultdict(set), defaultdict(set)
    for r in pts[pts.article_id.isin(ids_)].itertuples():
        if r.point_geoid_level == "block" and r.point_lat == r.point_lat and hex_of(r.point_lon, r.point_lat):
            cfp[r.article_id].add(hex_of(r.point_lon, r.point_lat))
        elif r.point_geoid_level == "place":
            cfp[r.article_id].update(place_hexes(r.point_geoid))
        elif r.point_geoid_level == "county":
            cfp[r.article_id].update(county_hexes.get(r.point_geoid, []))
    for r in plc[plc.article_id.isin(ids_)].itertuples():
        if r.geoid_level == "place":
            mfp[r.article_id].update(place_hexes(r.geoid))
        elif r.geoid_level == "county":
            mfp[r.article_id].update(county_hexes.get(r.geoid, []))
    # mentions: only those naming a town are drawn on hexagons; county-wide stories and mentions are kept per county
    mfp_place = defaultdict(set)
    for r in plc[plc.article_id.isin(ids_) & (plc.geoid_level == "place")].itertuples():
        mfp_place[r.article_id].update(place_hexes(r.geoid))
    cty_stories = pts[pts.article_id.isin(ids_) & (pts.point_geoid_level == "county")].point_geoid.value_counts().to_dict()
    cen_n, men_n, cty_n = defaultdict(int), defaultdict(int), defaultdict(int)
    county_level = set(pts[pts.article_id.isin(ids_) & (pts.point_geoid_level == "county")].article_id)
    for a_, ks in cfp.items():
        for k in ks:
            if a_ in county_level:
                cty_n[k] += 1          # centred on a whole county: drawn as the county treatment, not the fill
            else:
                cen_n[k] += 1
    for a_, ks in mfp_place.items():
        for k in ks - cfp.get(a_, set()):
            men_n[k] += 1
    # MENTIONS BY COUNTY: stories naming a county (or a place in it) without being centred there -- the county shade
    cm = defaultdict(int)
    for o, al in by_outlet.items():
        if home_of(al[0]) != c_:
            continue
        for a in al:
            for cc in set(a["counties"]) - {a["central"]}:
                cm[cc] += 1
    # ANCHORS for the volume (waffle) view: stories centred on a place counted at the place's centre hexagon, a
    # neighbourhood (block) story at its own hexagon; county-wide stories go to the county shade
    anc = defaultdict(int); anc_name = {}
    for r in pts[pts.article_id.isin(ids_)].itertuples():
        if r.point_geoid_level == "place" and r.point_geoid in pl_shapes:
            q_ = pl_shapes[r.point_geoid][1].representative_point(); k = hex_of(q_.x, q_.y); nm = pl_shapes[r.point_geoid][0]["NAME"]
        elif r.point_geoid_level == "block" and r.point_lat == r.point_lat:
            k = hex_of(r.point_lon, r.point_lat); nm = ""
        else:
            continue
        if k:
            anc[k] += 1; anc_name.setdefault(k, nm)
    # BUILDER STORY MAP points (corpus.run_story_map): one circle per central location -- a place at its centre, a
    # neighbourhood (block) at its point -- with its precision level
    sp = defaultdict(lambda: {"n": 0})
    for r in pts[pts.article_id.isin(ids_)].itertuples():
        if r.point_geoid_level in ("place", "block") and r.point_lat == r.point_lat:
            if r.point_geoid_level == "place" and r.point_geoid in pl_shapes:
                q_ = pl_shapes[r.point_geoid][1].representative_point(); lon_, lat_ = q_.x, q_.y; key = r.point_geoid
            else:
                lon_, lat_ = r.point_lon, r.point_lat; key = f"{round(lon_, 3)},{round(lat_, 3)}"
            e = sp[key]; e["n"] += 1; e.update(lon=round(lon_, 4), lat=round(lat_, 4), level=r.point_geoid_level)
    maps["story"][town] = {"central": dict(cen_n), "mention": dict(men_n), "value": dict(cen_n), "county": {},
                           "points": sorted(sp.values(), key=lambda e: -e["n"]),
                           "anchors": [{"hex": k, "n": n, "name": anc_name.get(k, "")} for k, n in sorted(anc.items(), key=lambda z: -z[1])],
                           "county_mentions": dict(cm),
                           "county_stories": {str(k): int(v_) for k, v_ in cty_stories.items()},
                           "stories": len(ids_), "centred": len(cfp)}
maps["places"] = [{"name": r_["NAME"], "pop": pop_.get(g_, 0), "lon": round(geom.representative_point().x, 4),
                   "lat": round(geom.representative_point().y, 4)} for g_, (r_, geom) in pl_shapes.items() if g_.startswith("29")]
maps["landmarks"] = CFG.get("landmarks", [])
maps["market"] = {"region": REGION, "name": CFG["market"], "home_counties": sorted({c_ for c_, _ in TOWNS.values()}),
                  "counties": CFG["dma_counties"], "outline": mapping(dma_geom),
                  "labels": sorted(labels, key=lambda l: -l["pop"]),
                  "block_groups": {t_: len(town_bgs(t_)) for t_ in TOWNS}}
# keep only the hexagons some town uses, and their neighbours (the empty border ring)
used = set()
for ms in maps["towns"].values():
    for m_ in ms:
        used |= set(m_["value"]) | {k for ix in m_["index"].values() for k in ix}
for st_ in maps.get("story", {}).values():
    used |= set(st_["central"]) | set(st_["mention"]) | set(st_["county"])
ring = set()
for k in used:
    q_, r_ = map(int, k.split(","))
    ring |= {f"{q_ + a},{r_ + b}" for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))}
maps["hexes"] = {k: v for k, v in maps["hexes"].items() if k in used | ring}
maps["in_market"] = [k for k in maps["in_market"] if k in maps["hexes"]]
maps["hex_county"] = {k: hex_county.get(k, "") for k in maps["hexes"]}
json.dump(maps, open(R / "market_pattern_maps.json", "w"))
print(f"{len(hexes):,} hexagons in the market")
