"""Spillover from each outlet's own profile, aggregated to the county.  Missouri, March 2026.

Unit: the 128 outlets of spillover_outlets.py (10+ placed stories; The Maneater and CoMoBuzz excluded; St. Louis city
and county one unit). Two outcomes, each a share of the outlet's placed stories:
  touch    the story's places include another county (Missouri, or another state within 60 miles): the current measure
  centred  the story's central county is another county (Missouri, or another state within 60 miles)
Outlet profile (src/lookups/mo_outlet_registry.csv for the town and its coordinates; sources frequency):
  broadcast        video or audio broadcaster
  weekly           print published weekly or less often (daily and in-between are the reference)
  log_town_pop     log 2024 population of the outlet's town (Census place estimates; 500 if not a Census place)
  town_share       the town's share of its county's population (is it the county's main town)
  border_mi        miles from the town to the nearest edge of its county
  hub_mi           miles from the town to the nearest town of 25,000+ in another county
  log_volume       log of the outlet's local stories in March
County terms of the adopted model (urban share, concentration) are kept as candidates, not assumed.
Each specification is scored by predicting each county's outlets from all the others (leave one county out). A
county's expected spillover is its outlets' expectations weighted by their stories.
"""
import json
import math
import os
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from shapely.geometry import Point, shape
from shapely.ops import unary_union

warnings.filterwarnings("ignore")
root = Path(__file__).resolve().parents[1]
unit = lambda f: "29189" if f == "29510" else f
so = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})

# ---- outcomes: touch and centred, same 60-mile other-state rule as spillover_v2 ----
arts = json.load(open(root / "coverage/storymap/statewide_2026_03_articles.json"))["articles"]
cp0 = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
cen = {r.STATEFP + r.COUNTYFP: (float(r.LATITUDE), float(r.LONGITUDE)) for r in cp0.itertuples()}


def gc_miles(a, b):
    (y1, x1), (y2, x2) = cen[a], cen[b]
    p1, p2, dl = math.radians(y1), math.radians(y2), math.radians(x2 - x1)
    return 3959 * math.acos(min(1, math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)))


home = so.set_index("outlet").fips
near = {}
for h in home.unique():
    src = [h] + (["29510"] if h == "29189" else [])
    near[h] = {g for g in cen if not g.startswith("29") and any(gc_miles(s, g) <= 60 for s in src)}
n = defaultdict(lambda: [0, 0, 0, 0])
for a in arts:
    o = a["publisher"]
    if o not in home.index or not a["counties"]:
        continue
    h = home[o]
    away = lambda c: (c.startswith("29") and unit(c) != h) or c in near[h]
    r = n[o]; r[0] += 1
    r[1] += any(away(c) for c in a["counties"])
    cen_away = bool(a["central"]) and away(a["central"])
    r[2] += cen_away
    r[3] += (not cen_away) and any(away(c) for c in a["counties"])
oc = pd.DataFrame(n, index=["placed_n", "touch_n", "centred_n", "mention_n"]).T
so = so.join(oc, on="outlet")
so["touch"], so["centred"] = so.touch_n / so.placed_n, so.centred_n / so.placed_n
# weighted: a story centred in another county counts 1; a story that only mentions another county counts W
W = float(os.environ.get("MENTION_WEIGHT", "0.5"))
so["weighted"] = (so.centred_n + W * so.mention_n) / so.placed_n

# ---- outlet profile ----
reg = pd.read_csv("/Users/kiesowd/VSCode/NewsCrawler/MizzouNewsCrawler/src/lookups/mo_outlet_registry.csv", dtype=str)
reg["u"] = reg.county_fips.fillna("").map(unit)
reg = reg.drop(columns="fips").merge(so[["outlet", "fips"]], on="outlet")
reg = reg[(reg.u == reg.fips) | ~reg.outlet.duplicated(keep=False)].drop_duplicates("outlet").set_index("outlet")
so["city"] = so.outlet.map(reg.city)
so["lat"], so["lon"] = so.outlet.map(reg.lat).astype(float), so.outlet.map(reg.lon).astype(float)

rows = [l.rstrip("\n").rsplit("|", 1) for l in open(root / "coverage/source_frequency.csv") if "|" in l]
freq = pd.DataFrame(rows, columns=["outlet", "f"]).drop_duplicates("outlet").set_index("outlet").f.str.strip()
so["weekly"] = (so.broadcast.eq(0) & so.outlet.map(freq).isin(["weekly", "monthly"])).astype(int)
so["freq_known"] = so.broadcast.eq(1) | so.outlet.map(freq).fillna("").ne("")

pe = pd.read_csv(root / "census_dl/ref/sub-est2024_29.csv", dtype=str, encoding="latin-1")
pl = pe[pe.SUMLEV == "162"].copy()
pl["name"] = pl.NAME.str.replace(r" (city|town|village|CDP)$", "", regex=True).str.lower()
pl["pop"] = pl.POPESTIMATE2024.astype(int)
town_pop = pl.groupby("name")["pop"].max()
so["town_pop"] = so.city.str.lower().map(town_pop).fillna(500)
cp = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO29.txt", dtype=str, encoding="utf-8-sig")
cp["fips"] = (cp.STATEFP + cp.COUNTYFP).map(unit)
county_pop = cp.assign(p=cp.POPULATION.astype(int)).groupby("fips").p.sum()
so["town_share"] = (so.town_pop / so.fips.map(county_pop)).clip(upper=1)
so["log_town_pop"] = np.log(so.town_pop)

# county shapes from county subdivisions (St. Louis city and county one unit)
ns = {}
src = (root / "flows/build_cousub_shares.py").read_text()
exec(src.split('if "--geo" in sys.argv')[0].replace("Path(__file__).parent", f'Path("{root / "flows"}")'), ns)
parts = defaultdict(list)
for k, (rec, g) in ns["read_shp"](str(root / "census_dl/cousub/cb_2020_29_cousub_500k"), lambda r: r["GEOID"]).items():
    parts[unit(k[:5])].append(g)
county = {f: unary_union(g) for f, g in parts.items()}
MI = 69.0
def miles(p, geom):
    # degrees to miles at Missouri's latitude: scale longitude by cos(38.5)
    k = math.cos(math.radians(38.5))
    from shapely.affinity import scale
    return scale(geom, xfact=k, yfact=1, origin=(0, 0)).distance(scale(p, xfact=k, yfact=1, origin=(0, 0))) * MI
so["border_mi"] = [miles(Point(x, y), county[f].boundary) for x, y, f in zip(so.lon, so.lat, so.fips)]
# towns of 25,000+: their location from the place shapes
big = []
place_pop = pl.set_index("PLACE")["pop"]
for k, (rec, g) in ns["read_shp"](str(root / "census_dl/place/cb_2020_29_place_500k"), lambda r: r["PLACEFP"]).items():
    pop = place_pop.get(k)
    if pop and pop >= 25000:
        c = g.centroid
        f = next((k for k, g in county.items() if g.contains(c)), None)
        big.append((rec["NAME"], c, f))
so["hub_mi"] = [min(miles(Point(x, y), c) for _, c, cf in big if cf != f) for x, y, f in zip(so.lon, so.lat, so.fips)]
so["hub_mi"] = so.hub_mi.clip(lower=1)
so["log_hub_mi"] = np.log(so.hub_mi)
q = pd.read_csv(root / "coverage/source_quality_2026_03.csv").groupby("canonical_name").local_news.max()
so["log_volume"] = np.log(so.outlet.map(q).fillna(so.placed))

# ---- models ----
fit = lambda f, d, y: smf.glm(f.replace("rate", y), d, family=sm.families.Binomial(), var_weights=None).fit()


def loo(f, d, y):
    e = []
    for fp in d.fips.unique():
        tr, te = d[d.fips != fp], d[d.fips == fp]
        e += list(np.abs(fit(f, tr, y).predict(te) - te[y]))
    return 100 * np.mean(e)


PROFILE = "rate ~ broadcast + weekly + log_town_pop + town_share + border_mi + log_hub_mi + log_volume"
SPECS = {
    "adopted (broadcaster + county urban share + concentration)": "rate ~ broadcast + pct_urban + concentration",
    "broadcaster only": "rate ~ broadcast",
    "broadcaster + town population": "rate ~ broadcast + log_town_pop",
    "outlet profile": PROFILE,
    "outlet profile + county urban share + concentration": PROFILE + " + pct_urban + concentration",
}
d = so[so.freq_known].copy()
print(f"{len(d)} outlets with frequency known ({len(so) - len(d)} print outlets without it left out), {d.fips.nunique()} counties")
print(d.groupby("broadcast")[["touch", "centred"]].median().round(2).rename(index={0: "print median", 1: "broadcast median"}))
fits = {}
for y in ("touch", "centred", "weighted"):
    print(f"\n## {y}: leave-one-county-out error (points)")
    for name, f in SPECS.items():
        print(f"  {loo(f, d, y):5.1f}  {name}")
    m = smf.glm("rate ~ broadcast + log_town_pop".replace("rate", y), d, family=sm.families.Binomial()).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(d.fips)[0]})
    fits[y] = m
    print(pd.DataFrame({"coef": m.params, "p": m.pvalues}).round(3).to_string())

# ---- the three counties: each outlet's profile and expectation ----
show = d[d.fips.isin(["29007", "29019", "29151"])].copy()
for y, m in fits.items():
    show[f"exp_{y}"] = m.predict(show)
cols = ["outlet", "fips", "broadcast", "weekly", "town_pop", "border_mi", "hub_mi", "placed", "touch", "exp_touch", "centred", "exp_centred", "weighted", "exp_weighted"]
pd.set_option("display.width", 220)
print("\n" + show[cols].round(2).sort_values(["fips", "broadcast"]).to_string(index=False))
for f, g in show.groupby("fips"):
    w = g.placed
    print(f"{f}: touch actual {np.average(g.touch, weights=w):.0%} expected {np.average(g.exp_touch, weights=w):.0%}; "
          f"centred actual {np.average(g.centred, weights=w):.0%} expected {np.average(g.exp_centred, weights=w):.0%}; "
          f"weighted actual {np.average(g.weighted, weights=w):.0%} expected {np.average(g.exp_weighted, weights=w):.0%}")
so.to_csv(root / "analysis/spillover_profile.csv", index=False)
