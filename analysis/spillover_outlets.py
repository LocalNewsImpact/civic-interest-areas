"""Spillover by OUTLET, March 2026, statewide: broadcasting as a factor, not a filter.

Unit: each outlet with 10+ placed stories (The Maneater and CoMoBuzz excluded; St. Louis city + county one unit).
Spillover (adopted 2026-10-17): weighted share of its placed stories about another county -- another Missouri county
or an other-state county within 60 miles. A story centred in another county counts 1; a story centred at home that
mentions another county counts 0.5 (MENTION_WEIGHT); a story about home only counts 0. A Sports story (CIN) counts
half of that (SPORTS_WEIGHT 0.5, adopted 2026-10-17): 0.5 centred away, 0.25 as a mention. A game is between two
teams, usually from different places, so a Sports story reaches another county by its nature and would inflate an
outlet's spillover through one category (print, undiscounted: ~40% of Sports stories, 23-29% for every other
category). The earlier measure, any story
that touches another county, counted a passing mention the same as a story about that county; it is kept as
rate_touch. County terms from spillover_v2 (cohort, border, log population, residents' share of
visits outside, Jan-Sep 2026).
Model: logistic regression, each outlet weighted equally (spill share as the outcome, one observation per outlet, so a
high-volume broadcaster counts once), standard errors clustered by county.
FINAL MODEL (adopted 2026-10-17): spillover ~ broadcaster + weekly in a county that also has a daily and a TV station
+ log miles to the county edge + log(1 + print outlets in the county).
Fitted on well-collected outlets; each outlet's expectation comes from its own profile, not its county's. Chosen on
held-out error (each county's outlets predicted from all the others): 9.39 points, against 9.79 for broadcaster + the
population of the outlet's town, which it replaces, and 9.45 for both. Frequency alone, distance to the county edge,
distance to a town of 25,000+ in another county and story volume added nothing (spillover_profile.py). A county's
expected spillover is its outlets' expectations weighted by their stories.
Outputs: spillover_outlets.csv; ../flows/outlet_spillover_2026_03.json (the three counties, for the chart).
"""
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

root = Path(__file__).resolve().parents[1]
data = json.load(open(root / "coverage/storymap/statewide_2026_03_articles.json"))
cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str}).set_index("fips")
county = pd.read_csv(root / "analysis/spillover_v2_all.csv", dtype={"Unnamed: 0": str}).rename(columns={"Unnamed: 0": "fips"}).set_index("fips")
cp = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
cen = {r.STATEFP + r.COUNTYFP: (float(r.LATITUDE), float(r.LONGITUDE)) for r in cp.itertuples()}


def miles(a, b):
    (y1, x1), (y2, x2) = cen[a], cen[b]
    p1, p2 = math.radians(y1), math.radians(y2)
    return 3959 * math.acos(min(1, math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(math.radians(x2 - x1))))


near = {}
by_name = {n.lower(): f for f, n in cov.name.items()}
by_name.update({"st. louis": "29189", "st louis": "29189", "st. louis city": "29510"})
fips_of = lambda n: by_name.get((n or "").lower().replace(" county", "").strip())
unit = lambda f: "29189" if f == "29510" else f
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from excluded_outlets import EXCLUDE  # one list for every county count
import os as _os
MENTION_WEIGHT = float(_os.environ.get("MENTION_WEIGHT", 0.5))
# SPORTS: weight of a Sports story's away credit (CIN primary_label, coverage/cin_labels_2026_03.csv). 1 counts a
# Sports story like any other; 0 keeps it as a story but never as spillover. The story stays in the denominator.
SPORTS_WEIGHT = float(_os.environ.get("SPORTS_WEIGHT", 0.5))
CIN = pd.read_csv(root / "coverage/cin_labels_2026_03.csv").set_index("id").primary_label
# Outlets based in Kansas City, Missouri (registry town), for whom Wyandotte County, Kansas -- Kansas City,
# Kansas -- is home. Decided 2026-10-17.
KC_HOME = frozenset({"20209"})
_kc = pd.read_csv(Path.home() / "VSCode/NewsCrawler/MizzouNewsCrawler/src/lookups/mo_outlet_registry.csv", dtype=str)
KC_OUTLETS = frozenset(_kc[(_kc.city.str.lower() == "kansas city") & (_kc.state == "MO")].outlet)
o = defaultdict(lambda: {"placed": 0, "touch": 0, "centred": 0, "mention": 0, "centred_s": 0, "mention_s": 0})
for a in data["articles"]:
    f = fips_of(a["publisher_county"])
    if not f or not a["counties"] or a["publisher"] in EXCLUDE:
        continue
    i = unit(f)
    if i not in near:
        src = [i] + (["29510"] if i == "29189" else [])
        near[i] = {g for g in cen if not g.startswith("29") and any(miles(s, g) <= 60 for s in src)}
    r = o[(a["publisher"], i, "broadcast" in (a["publisher_type"] or ""))]
    r["placed"] += 1
    # Kansas City, Kansas is the same city as Kansas City, Missouri: a Kansas City outlet's story about KCK
    # (Wyandotte County) is home coverage, not spillover -- as St. Louis city and county are one unit.
    home_also = KC_HOME if a["publisher"] in KC_OUTLETS else frozenset()
    away = lambda c: ((c.startswith("29") and unit(c) != i) or c in near[i]) and c not in home_also
    touch = any(away(c) for c in a["counties"])
    centred = bool(a["central"]) and away(a["central"])
    r["touch"] += touch
    r["centred"] += centred
    r["mention"] += touch and not centred
    if CIN.get(a["id"]) == "Sports":
        r["centred_s"] += centred
        r["mention_s"] += touch and not centred
d = pd.DataFrame([{"outlet": k[0], "fips": k[1], "broadcast": int(k[2]), **v} for k, v in o.items()])
d = d[(d.placed >= 10) & d.fips.isin(county.index)].copy()
d = d.join(county[["type", "border", "log_pop", "travel_out"]], on="fips")
# CROSSOVER = distinct residents seen outside the county in a month, lower bound (crossover_compare.py, from
# build_unique_od.py): people, not summed block-group sightings; it already includes commuters. The summed share it
# replaces is kept as travel_out_summed for comparison.
cc = pd.read_csv(root / "analysis/crossover_compare.csv", dtype={"Unnamed: 0": str}).rename(columns={"Unnamed: 0": "fips"}).set_index("fips")
d["travel_out_summed"] = d.travel_out
d["travel_out"] = d.fips.map(cc.dedup_lower)
# URBAN COUNTY EFFECT: share of the county's population in Census 2020 urban areas (2020_UA_COUNTY.xlsx); St. Louis
# city and county pooled. Outlets in more urban counties cover less outside their county, beyond crossover.
ua = pd.read_excel(root / "census_dl/urban/2020_UA_COUNTY.xlsx", dtype=str)
ua = ua[ua.STATE == "29"].assign(u=lambda x: ("29" + x.COUNTY).map(lambda f: "29189" if f == "29510" else f))
ug = ua.assign(p=ua.POP_COU.astype(float), q=ua.POP_URB.astype(float)).groupby("u")[["p", "q"]].sum()
d["pct_urban"] = d.fips.map(ug.q / ug.p)
# HUB DOMINANCE: concentration of residents' out-of-county travel -- sum over destination counties of squared shares of
# visits (calibrated, pass-through discounted, Jan-Sep 2026; od_predicted.csv). High where one hub takes most of it
# (Webster -> Greene). Adopted 2026-10-16: +1.17 (p 0.12), held-out error 15.0 -> 15.0 (all), 14.3 -> 14.1 (well collected).
tpv = pd.read_csv(root / "analysis/od_predicted.csv", dtype={"i": str, "j": str})
tpv["iu"], tpv["ju"] = tpv.i.map(lambda f: "29189" if f == "29510" else f), tpv.j.map(lambda f: "29189" if f == "29510" else f)
vv = tpv[tpv.iu != tpv.ju].groupby(["iu", "ju"]).visits.sum()
d["concentration"] = d.fips.map(((vv / vv.groupby(level=0).transform("sum")) ** 2).groupby(level=0).sum())
spill_of = lambda x, mw, sw: (x.centred - x.centred_s) + mw * (x.mention - x.mention_s) + sw * (x.centred_s + mw * x.mention_s)
d["spill"] = spill_of(d, MENTION_WEIGHT, SPORTS_WEIGHT)
d["rate"] = d.spill / d.placed
d["rate_touch"] = d.touch / d.placed
# OUTLET'S TOWN: population of the town the outlet is in (registry city -> Census 2024 place estimate)
reg = pd.read_csv(Path.home() / "VSCode/NewsCrawler/MizzouNewsCrawler/src/lookups/mo_outlet_registry.csv", dtype=str)
reg["u"] = reg.county_fips.fillna("").map(unit)
reg = reg.drop(columns="fips").merge(d[["outlet", "fips"]], on="outlet")
reg = reg[(reg.u == reg.fips) | ~reg.outlet.duplicated(keep=False)].drop_duplicates("outlet").set_index("outlet")
pe = pd.read_csv(root / "census_dl/ref/sub-est2024_29.csv", dtype=str, encoding="latin-1")
pl = pe[pe.SUMLEV == "162"].assign(name=lambda x: x.NAME.str.replace(r" (city|town|village|CDP)$", "", regex=True).str.lower(),
                                   n=lambda x: x.POPESTIMATE2024.astype(int))
d["town"] = d.outlet.map(reg.city)
d["town_pop"] = d.town.str.lower().map(pl.groupby("name").n.max()).fillna(500)
d["log_town_pop"] = np.log(d.town_pop)
print(f"{len(d)} outlets with 10+ placed stories in {d.fips.nunique()} counties; broadcasters: {d.broadcast.sum()}")
print("median spillover: broadcasters", f"{d[d.broadcast == 1].rate.median():.0%},", "print and digital", f"{d[d.broadcast == 0].rate.median():.0%}")
f = "rate ~ broadcast + C(type, Treatment('Rural')) + border + log_pop + travel_out"
for label, w in (("each outlet counts once", None), ("weighted by stories", d.placed)):
    m = smf.glm(f, d, family=sm.families.Binomial(), freq_weights=w).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.fips)[0]})
    d["pred_" + ("outlet" if w is None else "stories")] = m.predict(d)
    print(f"\n## {label}")
    print(pd.DataFrame({"coef": m.params, "se": m.bse, "p": m.pvalues}).round(3).to_string())
print("\n## the three counties' outlets (model: each outlet counts once)")
print("| County | Outlet | Broadcaster | Stories | Spillover | Model |\n|---|---|---|---:|---:|---:|")
for n, fp in (("Audrain", "29007"), ("Boone", "29019"), ("Osage", "29151")):
    for r in d[d.fips == fp].sort_values("placed", ascending=False).itertuples():
        print(f"| {n} | {r.outlet} | {'yes' if r.broadcast else 'no'} | {r.placed} | {r.rate:.0%} | {r.pred_outlet:.0%} |")
d.to_csv(root / "analysis/spillover_outlets.csv", index=False)


# ---- choosing the model: leave one county out, predict its outlets from the rest -------------------------------------
CANDIDATES = {
    "broadcaster only": "rate ~ broadcast",
    "broadcaster + town population": "rate ~ broadcast + log_town_pop",
    "broadcaster + county urban share + concentration (previous)": "rate ~ broadcast + pct_urban + concentration",
    "broadcaster + residents' travel out": "rate ~ broadcast + travel_out",
    "broadcaster + travel out + population": "rate ~ broadcast + travel_out + log_pop",
    "full (cohort, border, population, travel out)": f,
}
print("\n## leave-one-county-out prediction error (outlet spillover, each outlet counts once)")
print("| Model | Mean absolute error (points) |\n|---|---:|")
errs = {}
for label, formula in CANDIDATES.items():
    e = []
    for fp in d.fips.unique():
        train, test = d[d.fips != fp], d[d.fips == fp]
        mm = smf.glm(formula, train, family=sm.families.Binomial()).fit()
        e += list((mm.predict(test) - test.rate).abs())
    errs[label] = 100 * np.mean(e)
    print(f"| {label} | {errs[label]:.1f} |")


# ---- the final model, and the three counties for the chart --------------------------------------------------------
# WEEKLY IN A CROWDED COUNTY: a print weekly in a county that also has an active daily and an active TV station
# (src/lookups/mo_outlet_registry.csv, status active; frequency from the sources registry). Nine counties: Adair, Boone,
# Buchanan, Callaway, Cape Girardeau, Greene, Jackson, Jasper, St. Louis. Their weeklies' median spillover is 11%,
# against 24% for the other weeklies.
_all = pd.read_csv(Path.home() / "VSCode/NewsCrawler/MizzouNewsCrawler/src/lookups/mo_outlet_registry.csv", dtype=str)
# The market as it stood in MARCH: active now, or closed since but publishing then. The Barry County Advertiser
# closed in July; counted as closed, Barry looked like a one-paper county. Statuses that say what an entry IS
# (duplicate, replica, not local news) stay out whatever they published.
_all["_march"] = pd.to_numeric(_all.march_articles, errors="coerce").fillna(0)
_all = _all[(_all.status == "active") | ((_all.status == "closed") & (_all._march > 0))].assign(
    u=lambda x: x.county_fips.fillna("").map(unit))
_rows = [l.rstrip("\n").rsplit("|", 1) for l in open(root / "coverage/source_frequency.csv") if "|" in l]
_freq = pd.DataFrame(_rows, columns=["outlet", "f"]).drop_duplicates("outlet").set_index("outlet").f.str.strip()
_all["freq"] = _all.outlet.map(_freq).fillna("")
CROWDED = (set(_all[_all.type.str.contains("video", na=False)].u)
           & set(_all[_all.type.str.contains("print|newspaper", na=False) & (_all.freq == "daily")].u))
d["crowded_weekly"] = ((d.broadcast == 0) & (d.outlet.map(_freq) == "weekly") & d.fips.isin(CROWDED)).astype(int)
# BORDER: miles from the outlet's town (registry coordinates) to the nearest edge of its county; county shapes from the
# 2020 county subdivisions, St. Louis city and county one unit. Logged, floored at half a mile.
from shapely.affinity import scale as _scale
from shapely.geometry import Point as _Point
from shapely.ops import unary_union as _union

_ns = {}
_src = (root / "flows/build_cousub_shares.py").read_text()
exec(_src.split('if "--geo" in sys.argv')[0].replace("Path(__file__).parent", f'Path("{root / "flows"}")'), _ns)
_parts = defaultdict(list)
for _k, (_rec, _geom) in _ns["read_shp"](str(root / "census_dl/cousub/cb_2020_29_cousub_500k"), lambda r: r["GEOID"]).items():
    _parts[unit(_k[:5])].append(_geom)
_edge = {f: _union(g).boundary for f, g in _parts.items()}
_kx = math.cos(math.radians(38.5))   # degrees to miles at Missouri's latitude: 69 miles a degree, longitude scaled
_mi = lambda p, geom: 69.0 * _scale(geom, xfact=_kx, yfact=1, origin=(0, 0)).distance(_scale(p, xfact=_kx, yfact=1, origin=(0, 0)))
_lat, _lon = d.outlet.map(reg.lat).astype(float), d.outlet.map(reg.lon).astype(float)
d["border_mi"] = [_mi(_Point(x, y), _edge[f]) for x, y, f in zip(_lon, _lat, d.fips)]
d["log_border_mi"] = np.log(d.border_mi.clip(lower=0.5))
# SATURATION: print and digital outlets active in the county (registry), log of 1 + count.
d["log_print"] = np.log1p(d.fips.map(_all[_all.type.str.contains("print|newspaper|digital", na=False)].groupby("u").size()).fillna(0))
# Adopted 2026-10-17 on held-out error (each county's outlets predicted from the others, fitted outlets; mean / median
# miss in points): + border + print saturation 8.62 / 7.20; with the terms chosen inside each fold without the held-out
# county (nested, the honest figure for having searched) 9.18 / 7.81, border + print saturation chosen in 38 of 43
# folds; broadcaster + crowded weekly alone 9.39 / 7.05; broadcaster + town population 9.79 / 8.64. Saturation and
# border terms tested one at a time and as daily-only terms in spillover_saturation_test.py.
FINAL = "rate ~ broadcast + crowded_weekly + log_border_mi + log_print"
# WELL COLLECTED: the model is fitted on these outlets only, then predicts every outlet. March local news with body text
# >= 95%, full length (600+ characters) >= 80%, placed by enrichment >= 60%. Ciphertext is NOT a criterion: six
# TownNews/BLOX outlets store 28-56% of `text` as ROT47 (coverage/cipher_share_2026_03.csv), but place enrichment read
# the decoded capture (`raw`) -- their stories' places include names found only in the encoded paragraphs.
q = pd.read_csv(root / "coverage/source_quality_2026_03.csv").groupby("canonical_name").agg(
    ln=("local_news", "max"), tu=("text_unavailable", "max"), shrt=("short_texts", "max"))
d = d.drop(columns=[c for c in ("ln", "tu", "shrt", "cipher_share", "good") if c in d]).join(q, on="outlet")
d["cipher_share"] = d.outlet.map(pd.read_csv(root / "coverage/cipher_share_2026_03.csv").set_index("outlet").cipher_share).fillna(0)
d["good"] = ((d.ln / (d.ln + d.tu) >= .95) & (1 - d.shrt / d.ln >= .8) & (d.placed / d.ln >= .6))
# NOT FITTED (2026-10-17, the authors' call): the Greene County Commonwealth is published in Mount Vernon (Lawrence
# County) and covers Greene County -- 20 of 23 stories centred there, so its home county is its office, not its market;
# Three Rivers Publishing (Cuba) carries three newspapers' stories under one name; the Mid Rivers Newsmagazine is
# published in Chesterfield (St. Louis County) and covers St. Charles County -- 19 of 26 stories centred there. All
# three still get an expectation.
NOT_FITTED = {"Greene County Commonwealth", "Three Rivers Publishing", "Mid Rivers Newsmagazine"}
# VOLUME FLOOR (2026-10-17): fitted on outlets with 20+ placed stories. Scored on the same outlets (every well-
# collected outlet with 10+), each county predicted from the others: floor 20 8.22 points mean, 6.62 median;
# floor 10 8.26 / 7.36 (analysis/rerun_report.py). Every outlet with 10+ still gets an expectation.
FIT_FLOOR = 20
g = d[d.good & ~d.outlet.isin(NOT_FITTED) & (d.placed >= FIT_FLOOR)]
m = smf.glm(FINAL, g, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(g.fips)[0]})
d["expected"] = m.predict(d)
e = []
for fp in g.fips.unique():
    tr, te = g[g.fips != fp], g[g.fips == fp]
    e += list((smf.glm(FINAL, tr, family=sm.families.Binomial()).fit().predict(te) - te.rate).abs())
print(f"\nfitted on {len(g)} well-collected outlets in {g.fips.nunique()} counties (of {len(d)}); "
      f"held-out error {100 * np.mean(e):.1f} points")
print("\n## final model")
print(pd.DataFrame({"coef": m.params, "se": m.bse, "p": m.pvalues}).round(3).to_string())
types = {}
for a in data["articles"]:
    types[a["publisher"]] = a["publisher_type"] or ""
kind = lambda o: "TV" if "video" in types.get(o, "") else "radio" if "audio" in types.get(o, "") else "print/digital"
out = {}
for n, fp in (("Audrain", "29007"), ("Boone", "29019"), ("Osage", "29151")):
    x = d[d.fips == fp].sort_values("placed", ascending=False)
    tot = lambda y: {"stories": int(y.placed.sum()), "actual": round(y.spill.sum() / y.placed.sum(), 3),
                     "expected": round((y.placed * y.expected).sum() / y.placed.sum(), 3)}
    out[n] = {"all": tot(x), "print": tot(x[x.broadcast == 0]) if (x.broadcast == 0).any() else None,
              "outlets": [{"name": r.outlet, "kind": kind(r.outlet), "stories": int(r.placed), "actual": round(r.rate, 3),
                           "expected": round(r.expected, 3)} for r in x.itertuples()]}
    t = out[n]["all"]
    print(f"{n}: county {t['actual']:.0%} actual vs {t['expected']:.0%} expected ({t['stories']} stories)" +
          (f"; print/digital {out[n]['print']['actual']:.0%} vs {out[n]['print']['expected']:.0%}" if out[n]["print"] and len(x) > (x.broadcast == 0).sum() else ""))
if not _os.environ.get("SPILL_DRY"):
    json.dump(out, open(root / "flows/outlet_spillover_2026_03.json", "w"), indent=1)

# ---- measure sensitivity: mention weight x sports weight ------------------------------------------------------------
# The outcome changes with the weights, so held-out error does not compare them; this shows what each choice does to
# the fit and to the three study counties. Same outlets, same terms.
print("\n## measure sensitivity (mention weight, sports weight): coefficients; county actual/expected")
for mw in (0.25, 0.5):
    for sw in (1, 0.5, 0):
        y = d.assign(rate=spill_of(d, mw, sw) / d.placed)
        gy = y.loc[g.index]
        my = smf.glm(FINAL, gy, family=sm.families.Binomial()).fit()
        y["expected"] = my.predict(y)
        ey = []
        for fp in gy.fips.unique():
            tr, te = gy[gy.fips != fp], gy[gy.fips == fp]
            ey += list((smf.glm(FINAL, tr, family=sm.families.Binomial()).fit().predict(te) - te.rate).abs())
        cty = []
        for n, fp in (("Audrain", "29007"), ("Boone", "29019"), ("Osage", "29151")):
            x = y[y.fips == fp]
            cty.append(f"{n} {(x.rate * x.placed).sum() / x.placed.sum():.0%}/{(x.expected * x.placed).sum() / x.placed.sum():.0%}")
        print(f"  mention {mw}, sports {sw}: mean rate {gy.rate.mean():.1%}; held-out {100 * np.mean(ey):.1f}; "
              + " ".join(f"{k} {v:+.3f}" for k, v in my.params.items()) + "; " + ", ".join(cty))

# ---- Springfield region, held out ----------------------------------------------------------------------------------
# Greene (Springfield), Webster (Springfield metro) and Barry (rural), the comparison set of springfield_vs_columbia.py.
# The model is refitted WITHOUT any of the three counties' outlets and then predicts them: a test on a region the fit
# never saw, and the expectations the Springfield chart shows. The previous models are scored the same way.
REGION = {"Greene": "29077", "Webster": "29225", "Barry": "29009"}
held = d.fips.isin(REGION.values())
gr = g[~g.fips.isin(REGION.values())]
print(f"\n## Springfield region held out: fitted on {len(gr)} outlets outside it; region outlets {held.sum()} "
      f"({(held & d.good).sum()} well collected)")
miss = {}
for label, formula in (("adopted", FINAL), ("broadcaster + crowded weekly", "rate ~ broadcast + crowded_weekly"),
                       ("broadcaster + town population", "rate ~ broadcast + log_town_pop")):
    pr = smf.glm(formula, gr, family=sm.families.Binomial()).fit().predict(d[held])
    w = d[held].placed
    miss[label] = (100 * (pr - d[held].rate).abs().mean(), 100 * (pr - d[held].rate).abs()[d[held].good].mean(),
                   np.average(pr, weights=w), np.average(d[held].rate, weights=w))
    if label == "adopted":
        d.loc[held, "expected_heldout"] = pr
for label, (m_all, m_good, e, a_) in miss.items():
    print(f"  {label}: mean miss {m_all:.1f} points (well collected {m_good:.1f}); region {a_:.0%} actual vs {e:.0%} expected")
out_sgf = {}
for n, fp in REGION.items():
    x = d[d.fips == fp].sort_values("placed", ascending=False).assign(expected=lambda y: y.expected_heldout)
    if x.empty:
        continue
    tot = lambda y: {"stories": int(y.placed.sum()), "actual": round(y.spill.sum() / y.placed.sum(), 3),
                     "expected": round((y.placed * y.expected).sum() / y.placed.sum(), 3)}
    out_sgf[n] = {"all": tot(x), "print": tot(x[x.broadcast == 0]) if (x.broadcast == 0).any() else None,
                  "outlets": [{"name": r.outlet, "kind": kind(r.outlet), "stories": int(r.placed),
                               "actual": round(r.rate, 3), "expected": round(r.expected, 3)} for r in x.itertuples()]}
    print(f"  {n}: {out_sgf[n]['all']['actual']:.0%} actual vs {out_sgf[n]['all']['expected']:.0%} expected; "
          + "; ".join(f"{o['name']} {o['actual']:.0%}/{o['expected']:.0%}" for o in out_sgf[n]["outlets"]))
if not _os.environ.get("SPILL_DRY"):
    json.dump(out_sgf, open(root / "flows/outlet_spillover_springfield_2026_03.json", "w"), indent=1)
    d.to_csv(root / "analysis/spillover_outlets.csv", index=False)
