"""Spillover by OUTLET, March 2026, statewide: broadcasting as a factor, not a filter.

Unit: each outlet with 10+ placed stories (EXCLUDE and CAMPUS outlets out: spillover_common.py; St. Louis city + county
one unit; Mid Rivers Newsmagazine and Greene County Commonwealth homed in the county they cover, HOME_COUNTY).
Spillover: weighted share of an outlet's placed stories about another county -- another Missouri county, or an
other-state county within 60 miles -- where "another county" is outside the outlet's HOME set (spillover_common.py:
its county, every county its city lies in, Kansas City, Kansas for Kansas City, Missouri). A story centred in another
county counts 1; a story centred at home (or with no centre) that mentions another county counts MENTION_WEIGHT 0.5; a
home-only story 0. A Sports story (CIN) counts SPORTS_WEIGHT 0.5 of that: a game is between two teams, usually from
different places, so a Sports story reaches another county by its nature. Both weights are DEFINITIONS set by the
authors, not selected; other weights appear only in the sensitivity table, scored scale-free.
Denominator (a definition): every placed story -- one with no central county, and one centred out of state beyond 60
miles, stay in it and count 0 unless they mention another county.
Model: fractional logit, one observation per outlet (a high-volume broadcaster counts once).
ADOPTED: spillover ~ broadcaster + log(1 + print and digital outlets in the county), fitted on well-collected outlets
with 20+ placed stories. Procedure (spillover_common.py, MODEL PROCEDURE): both terms are pre-specified hypothesis
terms, reported with coefficient and drop-one held-out gain whatever the result; exploratory additions pass only
through the nested guard (spillover_rule_selection.py). Primary metric: mean absolute held-out miss on the fitted
outlets (median beside). Inference: CRV3 (cluster jackknife) SEs, t(G-1) p-values; county-cluster bootstrap (1,999
draws) percentile CI. Scored by leaving each county out, on the fitted outlets and on every well-collected outlet with
10+ stories, against intercept-only and broadcaster-only baselines. County expectations are HELD OUT: each county's
outlets predicted by a fit without that county. The terms were first found by a search; its honest error is the
nested search B figure (spillover_nested_selection.py).
Outputs (none under SPILL_DRY=1): analysis/spillover_outlets.csv, analysis/spillover_quoted_rows.csv,
flows/outlet_spillover_2026_03.json (the three counties, for the chart). Printed and quoted figures for single counties
and outlets are those of Audrain, Boone and Osage (STUDY); every other figure is model-level.
"""
import json
import math
import os
import sys
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from spillover_common import (BORDER_FORM, CAMPUS, FINAL, FINAL_ALL_BORDER, FIT_FLOOR, PER_10K, WITH_CROWDED, paired_gain, predict, MENTION_WEIGHT, NOT_FITTED, NOT_LOCAL, SCORE_FLOOR,  # noqa: E402
                              SPORTS_WEIGHT, STUDY, cluster_inference, loo, market, outlet_home, outlet_rows, skill,
                              terms_of, unit)

DRY = bool(os.environ.get("SPILL_DRY"))
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


by_name = {n.lower(): f for f, n in cov.name.items()}
by_name.update({"st. louis": "29189", "st louis": "29189", "st. louis city": "29510"})
fips_of = lambda n: by_name.get((n or "").lower().replace(" county", "").strip())
CIN = pd.read_csv(root / "coverage/cin_labels_2026_03.csv").set_index("id").primary_label

# ---- stories -> outlet counts ---------------------------------------------------------------------------------------
near, homes = {}, {}
o = defaultdict(lambda: {"placed": 0, "touch": 0, "centred": 0, "mention": 0, "centred_s": 0, "mention_s": 0,
                         "no_centre": 0, "far_out_of_state": 0, "moved_home": 0, "moved_home_mention": 0})
for a in data["articles"]:
    pub = a["publisher"]
    filed = fips_of(a["publisher_county"])
    if not filed or not a["counties"] or pub in NOT_LOCAL:
        continue
    if (pub, filed) not in homes:
        homes[(pub, filed)] = outlet_home(pub, filed)
    i, home = homes[(pub, filed)]
    if i not in near:
        src = [i] + (["29510"] if i == "29189" else [])
        near[i] = {g for g in cen if not g.startswith("29") and any(miles(s, g) <= 60 for s in src)}
    r = o[(pub, i, "broadcast" in (a["publisher_type"] or ""))]
    r["placed"] += 1
    away = lambda c: ((c.startswith("29") and unit(c) not in home) or c in near[i]) and c not in home
    away_unit = lambda c: (c.startswith("29") and unit(c) != i) or c in near[i]   # the outlet's county alone
    touch = any(away(c) for c in a["counties"])
    centred = bool(a["central"]) and away(a["central"])
    r["touch"] += touch
    r["centred"] += centred
    r["mention"] += touch and not centred
    r["no_centre"] += not a["central"]
    r["far_out_of_state"] += bool(a["central"]) and not a["central"].startswith("29") and a["central"] not in near[i]
    # stories the city rule moves home: centred in a home-set county other than the outlet's own
    r["moved_home"] += bool(a["central"]) and away_unit(a["central"]) and not away(a["central"])
    r["moved_home_mention"] += (not centred) and any(away_unit(c) for c in a["counties"]) and not touch
    if CIN.get(a["id"]) == "Sports":
        r["centred_s"] += centred
        r["mention_s"] += touch and not centred
d = pd.DataFrame([{"outlet": k[0], "fips": k[1], "broadcast": int(k[2]), **v} for k, v in o.items()])
hs = {(k[0], v[0]): v[1] for k, v in homes.items()}
d["home_also"] = [";".join(sorted(hs[(x, f)] - {f})) for x, f in zip(d.outlet, d.fips)]
d = d[(d.placed >= SCORE_FLOOR) & d.fips.isin(county.index)].copy().reset_index(drop=True)
d = d.join(county[["type", "border", "log_pop", "travel_out"]], on="fips")
# CROSSOVER = distinct residents seen outside the county in a month, lower bound (crossover_compare.py)
cc = pd.read_csv(root / "analysis/crossover_compare.csv", dtype={"Unnamed: 0": str}).rename(columns={"Unnamed: 0": "fips"}).set_index("fips")
d["travel_out_summed"] = d.travel_out
d["travel_out"] = d.fips.map(cc.dedup_lower)
ua = pd.read_excel(root / "census_dl/urban/2020_UA_COUNTY.xlsx", dtype=str)
ua = ua[ua.STATE == "29"].assign(u=lambda x: ("29" + x.COUNTY).map(unit))
ug = ua.assign(p=ua.POP_COU.astype(float), q=ua.POP_URB.astype(float)).groupby("u")[["p", "q"]].sum()
d["pct_urban"] = d.fips.map(ug.q / ug.p)
tpv = pd.read_csv(root / "analysis/od_predicted.csv", dtype={"i": str, "j": str})
tpv["iu"], tpv["ju"] = tpv.i.map(unit), tpv.j.map(unit)
vv = tpv[tpv.iu != tpv.ju].groupby(["iu", "ju"]).visits.sum()
d["concentration"] = d.fips.map(((vv / vv.groupby(level=0).transform("sum")) ** 2).groupby(level=0).sum())
spill_of = lambda x, mw, sw: (x.centred - x.centred_s) + mw * (x.mention - x.mention_s) + sw * (x.centred_s + mw * x.mention_s)
d["spill"] = spill_of(d, MENTION_WEIGHT, SPORTS_WEIGHT)
d["rate"] = d.spill / d.placed
d["rate_touch"] = d.touch / d.placed

# ---- outlet profile ---------------------------------------------------------------------------------------------------
reg = outlet_rows(d)
pe = pd.read_csv(root / "census_dl/ref/sub-est2024_29.csv", dtype=str, encoding="latin-1")
pl = pe[pe.SUMLEV == "162"].assign(name=lambda x: x.NAME.str.replace(r" (city|town|village|CDP)$", "", regex=True).str.lower(),
                                   n=lambda x: x.POPESTIMATE2024.astype(int))
d["town"] = d.outlet.map(reg.city)
d["town_pop"] = d.town.str.lower().map(pl.groupby("name").n.max()).fillna(500)
d["log_town_pop"] = np.log(d.town_pop)
d["location_basis"] = d.outlet.map(reg.location_basis)

# MARKET counts (spillover_common.market: active, or closed but publishing in March; not EXCLUDE/CAMPUS)
mk = market()
FREQ = mk.drop_duplicates("outlet").set_index("outlet").freq
CROWDED = set(mk[mk.is_tv].u) & set(mk[mk.is_print & (mk.freq == "daily")].u)
is_print = d.outlet.map(reg.type).str.contains("print|newspaper", na=False)
d["daily"] = ((d.broadcast == 0) & is_print & (d.outlet.map(FREQ) == "daily")).astype(int)
# WEEKLY IN A CROWDED COUNTY (a candidate, not in the adopted model; frequency codes as filled 2026-10-24): a PRINT weekly (registry type print/newspaper; KC Beacon, digital, is not one) in a
# county whose MARKET has a print daily and a TV station.
d["crowded_weekly"] = ((d.broadcast == 0) & is_print & (d.outlet.map(FREQ) == "weekly") & d.fips.isin(CROWDED)).astype(int)
cnt = mk.groupby("u").agg(outlets=("outlet", "size"), printn=("is_print_digital", "sum"), tv=("is_tv", "sum"))
pop = cov.assign(u=cov.index.map(unit)).groupby("u").population.sum()
d["log_print"] = np.log1p(d.fips.map(cnt.printn).fillna(0))
d["log_outlets"] = np.log(d.fips.map(cnt.outlets).fillna(1).clip(lower=1))
d["outlets_per_10k"] = 1e4 * d.fips.map(cnt.outlets).fillna(1) / d.fips.map(pop)
d["log_tv"] = np.log1p(d.fips.map(cnt.tv).fillna(0))

# BORDER: miles from the outlet's registry point to the nearest edge of its home county (2020 county subdivisions
# dissolved; St. Louis city and county one unit), logged, floored at half a mile. The point is the street address
# where the registry has one, else the town centroid (location_basis). An outlet outside its home county (HOME_COUNTY)
# is beyond its edge: distance 0, floored.
from shapely.affinity import scale as _scale  # noqa: E402
from shapely.geometry import Point as _Point  # noqa: E402
from shapely.ops import unary_union as _union  # noqa: E402

_ns = {}
_src = (root / "flows/build_cousub_shares.py").read_text()
exec(_src.split('if "--geo" in sys.argv')[0].replace("Path(__file__).parent", f'Path("{root / "flows"}")'), _ns)
_parts = defaultdict(list)
for _k, (_rec, _geom) in _ns["read_shp"](str(root / "census_dl/cousub/cb_2020_29_cousub_500k"), lambda r: r["GEOID"]).items():
    _parts[unit(_k[:5])].append(_geom)
_shape = {f: _union(g) for f, g in _parts.items()}
_kx = math.cos(math.radians(38.5))   # degrees to miles at Missouri's latitude
_sc = lambda g: _scale(g, xfact=_kx, yfact=1, origin=(0, 0))
_mi = lambda p, geom: 69.0 * _sc(geom).distance(_sc(p))
_lat, _lon = d.outlet.map(reg.lat).astype(float), d.outlet.map(reg.lon).astype(float)
_pts = [_Point(x, y) for x, y in zip(_lon, _lat)]
d["outside_home"] = [not _shape[f].contains(p) for p, f in zip(_pts, d.fips)]
d["border_mi"] = [0.0 if out else _mi(p, _shape[f].boundary) for p, f, out in zip(_pts, d.fips, d.outside_home)]
d["log_border_mi"] = np.log(d.border_mi.clip(lower=0.5))
# ADOPTED form (spillover_common.FINAL): the border term for print and digital outlets only
d["log_border_np"] = d.log_border_mi * (1 - d.broadcast)
# HUB: miles to the nearest town of 25,000+ (2024) in another county (place-shape centroids); a search candidate.
_pp = pl.set_index("PLACE").n
_big = [(g.centroid, next((f for f, s in _shape.items() if s.contains(g.centroid)), None))
        for k, (rec, g) in _ns["read_shp"](str(root / "census_dl/place/cb_2020_29_place_500k"), lambda r: r["PLACEFP"]).items()
        if _pp.get(k, 0) >= 25000]
d["hub_mi"] = [min(_mi(p, c) for c, cf in _big if cf != f) for p, f in zip(_pts, d.fips)]
d["log_hub_mi"] = np.log(d.hub_mi.clip(lower=1))

# WELL COLLECTED: March local news with body text >= 95%, full length (600+ characters) >= 80%, placed by enrichment
# >= 60%. Ciphertext is not a criterion: enrichment read the decoded capture (coverage/cipher_share_2026_03.csv).
q = pd.read_csv(root / "coverage/source_quality_2026_03.csv").groupby("canonical_name").agg(
    ln=("local_news", "max"), tu=("text_unavailable", "max"), shrt=("short_texts", "max"))
d = d.join(q, on="outlet")
d["cipher_share"] = d.outlet.map(pd.read_csv(root / "coverage/cipher_share_2026_03.csv").set_index("outlet").cipher_share).fillna(0)
d["good"] = ((d.ln / (d.ln + d.tu) >= .95) & (1 - d.shrt / d.ln >= .8) & (d.placed / d.ln >= .6))
d["fitted"] = d.good & ~d.outlet.isin(NOT_FITTED) & (d.placed >= FIT_FLOOR)
d["scored"] = d.good & ~d.outlet.isin(NOT_FITTED) & (d.placed >= SCORE_FLOOR)

# ---- definitions, as counted -------------------------------------------------------------------------------------------
print(f"{len(d)} outlets with {SCORE_FLOOR}+ placed stories in {d.fips.nunique()} counties; broadcasters {d.broadcast.sum()}; "
      f"{int(d.placed.sum())} stories")
print(f"left out as not local news: EXCLUDE + CAMPUS ({', '.join(sorted(CAMPUS))})")
print(f"DENOMINATOR (a definition): {int(d.no_centre.sum())} stories with no central county and "
      f"{int(d.far_out_of_state.sum())} centred out of state beyond 60 miles stay in the denominator "
      f"({(d.no_centre.sum() + d.far_out_of_state.sum()) / d.placed.sum():.1%} of stories); they count only as mentions")
THREE = {fp for _, fp in STUDY}
mv = d[d.home_also != ""]
print(f"HOME rule (city counties + Kansas City, Kansas): {len(mv)} outlets have extra home counties; "
      f"{int(d.moved_home.sum())} stories centred in them move from away to home, and {int(d.moved_home_mention.sum())} "
      "mention-only stories lose their mention credit")
mt = mv[mv.fips.isin(THREE)]
if len(mt):
    print(mt.assign(m=mt.moved_home, mm=mt.moved_home_mention)[["outlet", "fips", "home_also", "placed", "m", "mm"]]
          .sort_values("m", ascending=False).to_string(index=False))

# ---- earlier candidates, all outlets (kept for the record; not the adopted model) -------------------------------------
f_full = "rate ~ broadcast + C(type, Treatment('Rural')) + border + log_pop + travel_out"
for col, w in (("pred_outlet", None), ("pred_stories", d.placed)):
    d[col] = smf.glm(f_full, d, family=sm.families.Binomial(), freq_weights=w).fit().predict(d)
print("\n## earlier candidates, all outlets, leave one county out (mean miss, points)")
for label, formula in {"broadcaster only": "rate ~ broadcast", "broadcaster + town population": "rate ~ broadcast + log_town_pop",
                       "broadcaster + county urban share + concentration": "rate ~ broadcast + pct_urban + concentration",
                       "broadcaster + residents' travel out": "rate ~ broadcast + travel_out"}.items():
    print(f"  {label}: {100 * np.abs(loo(terms_of(formula), d)).mean():.1f}")

# ---- the adopted model ---------------------------------------------------------------------------------------------------
g = d[d.fitted].copy()
s10 = d[d.scored].copy()
pb = stats.pointbiserialr(d.good, d.rate)
print(f"\n## QUALITY SELECTION: well collected {int(d.good.sum())} of {len(d)} outlets ({int(d.scored.sum())} scored = well "
      f"collected minus NOT_FITTED: {', '.join(sorted(d[d.good & ~d.scored].outlet))}); mean spillover "
      f"{d[d.good].rate.mean():.1%} well collected vs {d[~d.good].rate.mean():.1%} others "
      f"(point-biserial r {pb[0]:+.2f}, p {pb[1]:.3f}); print/digital {d[d.good & (d.broadcast == 0)].rate.mean():.1%} vs "
      f"{d[~d.good & (d.broadcast == 0)].rate.mean():.1%}. The fit and its errors describe well-collected outlets.")
m, inf, G = cluster_inference(g, FINAL)
d["expected_full_fit"] = m.predict(d)
# HELD-OUT EXPECTATION: each county's outlets predicted by the adopted model fitted without that county's outlets.
# Used for every county and outlet figure and the chart (`expected`).


def heldout_expected(frame, fitset):
    """Each county's outlets in `frame` predicted by the adopted model fitted on `fitset` without that county. The one
    computation behind every outlet and county expectation printed, charted or quoted."""
    e = pd.Series(np.nan, index=frame.index)
    for c in frame.fips.unique():
        e[frame.fips == c] = predict(fitset[fitset.fips != c], frame[frame.fips == c], terms_of(FINAL))
    return e


def county_figure(x, col="expected", rate="rate"):
    """Stories-weighted actual and expected spillover of a set of outlets (one formula for every county figure)."""
    w = x.placed
    return {"stories": int(w.sum()), "actual": round(float((x[rate] * w).sum() / w.sum()), 3),
            "expected": round(float((x[col] * w).sum() / w.sum()), 3)}


d["expected"] = heldout_expected(d, g)
print(f"\n## adopted model: fitted on {len(g)} well-collected outlets with {FIT_FLOOR}+ stories in {G} counties (of {len(d)}), "
      f"{int(g.broadcast.sum())} broadcasters; "
      f"crowded weeklies {int(g.crowded_weekly.sum())} in {g[g.crowded_weekly == 1].fips.nunique()} counties "
      f"(in the three counties: {', '.join(sorted(g[(g.crowded_weekly == 1) & g.fips.isin(THREE)].outlet)) or 'none'}); "
      f"crowded counties {len(CROWDED)}")
print("coefficients: CRV3 (cluster jackknife) SE, p from t with G-1 df (CRV1 beside for comparison); county-cluster "
      "bootstrap, 1,999 draws, percentile 95% CI")
print(inf.round(3).to_string())
print(f"border point: {(g.location_basis == 'town centroid').sum()} of {len(g)} fitted outlets located at a town centroid, "
      f"{(g.location_basis == 'address').sum()} at a street address; {int(g.outside_home.sum())} outside their home county "
      f"(border 0; in the three counties: {', '.join(g[g.outside_home & g.fips.isin(THREE)].outlet) or 'none'})")

print("\n## held-out error (each county's outlets predicted by a fit without that county): mean / median miss, points; "
      "skill = 1 - MAE / MAE(intercept only); R2 = out-of-sample, against intercept only")
print("| Model | Scored on | n | Mean | Median | Skill | OOS R2 |\n|---|---|---:|---:|---:|---:|---:|")
heldout = {}
for label, formula in (("adopted", FINAL), ("+ outlets per 10,000", PER_10K),
                       ("+ border (print and digital)", BORDER_FORM),
                       ("+ border (print and digital) + crowded weekly", WITH_CROWDED),
                       ("2026-10-17 form (crowded weekly, border term for every outlet)", FINAL_ALL_BORDER),
                       ("intercept only", "rate ~ 1"), ("broadcaster only", "rate ~ broadcast"),
                       ("broadcaster + crowded weekly", "rate ~ broadcast + crowded_weekly"),
                       ("broadcaster + town population", "rate ~ broadcast + log_town_pop")):
    for sl, sc in ((f"fitted ({FIT_FLOOR}+)", None), (f"all well collected {SCORE_FLOOR}+", s10)):
        k = skill(terms_of(formula), g, sc)
        heldout[(label, sl)] = k
        print(f"| {label} | {sl} | {k['n']} | {k['mean']:.2f} | {k['median']:.2f} | {k['skill']:+.3f} | {k['r2']:+.3f} |")
k10 = skill(terms_of(FINAL), s10, s10)
print(f"| adopted, fitted at {SCORE_FLOOR}+ | all well collected {SCORE_FLOOR}+ | {k10['n']} | {k10['mean']:.2f} | "
      f"{k10['median']:.2f} | {k10['skill']:+.3f} | {k10['r2']:+.3f} |")
print("honest error of the search that found the hypothesis terms: nested search B, spillover_nested_selection.py; "
      "exploratory guard: spillover_rule_selection.py")

# HYPOTHESIS TERMS (pre-specified): coefficient (above) and drop-one held-out gain -- mean miss of the adopted model
# GAIN = held-out mean miss without the term minus with it (positive: the term helps) -- with a county-paired bootstrap 95% interval, reported
# whatever the result; the block (both terms) against intercept only. LOCO folds are the counties, so the folds have no
# seed; the only randomness is the county bootstrap, shown over five seeds.
print("\nGAIN (this output and spillover_rule_selection.py): held-out mean miss WITHOUT the term(s) minus WITH them, "
      "points; positive = the term helps; county-paired bootstrap 95% interval")
print("\n## hypothesis terms: drop-one held-out gain, county-paired bootstrap 95% "
      "interval over 5 seeds (1,999 draws each); median with / without")
print("| Term | Against | Gain | 95% interval (5 seeds: lowest lo - highest hi) | Median with / without |\n|---|---|---:|---|---|")
base = terms_of(FINAL)
for lab, to in (("broadcaster", [t for t in base if t != "broadcast"]), ("print outlets", [t for t in base if t != "log_print"]),
                ("block: broadcaster + print outlets", [])):
    rs = [paired_gain(base, to, g, seed=sd) for sd in range(1, 6)]
    print(f"| {lab} | {' + '.join(to) or 'intercept only'} | {rs[0]['gain']:+.2f} | "
          + "; ".join(f"{r['lo']:+.2f} to {r['hi']:+.2f}" for r in rs) + f" | {rs[0]['median_with']:.2f} / {rs[0]['median_without']:.2f} |")
# EXPLORATORY candidates, one at a time against the adopted model: descriptive only. Adoption needs the nested guard
# (spillover_rule_selection.py), not these intervals.
print("\n## exploratory candidates, one at a time against the adopted model (descriptive; adoption by the nested guard "
      "only): gain, county-paired 95% interval, median with / without")
for lab, t in (("outlets per 10,000", "outlets_per_10k"), ("border, print and digital", "log_border_np"),
               ("border, every outlet", "log_border_mi"), ("crowded weekly", "crowded_weekly"), ("all outlets", "log_outlets"),
               ("miles to a town of 25,000+", "log_hub_mi"), ("TV stations", "log_tv")):
    r = paired_gain(base + [t], base, g)
    ci = cluster_inference(g, FINAL + f" + {t}", B=999)[1].loc[t]
    print(f"  {lab}: gain {r['gain']:+.2f} ({r['lo']:+.2f} to {r['hi']:+.2f}); median {r['median_with']:.2f} / "
          f"{r['median_without']:.2f}; coefficient {ci.coef:+.3f} (CRV3 p {ci.p_cluster_t:.3f}; CI {ci.ci_lo:+.3f} to {ci.ci_hi:+.3f})")
# BORDER DISTANCE 0 for an outlet outside its home county (Mid Rivers Newsmagazine, Greene County Commonwealth): it is
# beyond its home county's edge. Kept by the authors' decision (2026-10-24); the border term is a candidate, not adopted.

# ---- counties -------------------------------------------------------------------------------------------------------------
types = {a["publisher"]: a["publisher_type"] or "" for a in data["articles"]}
kind = lambda o_: "TV" if "video" in types.get(o_, "") else "radio" if "audio" in types.get(o_, "") else "print/digital"
tot = county_figure
print("\n## counties: actual / HELD-OUT expected spillover (fit without the county), stories weighted")
out = {}
for n, fp in STUDY:
    x = d[d.fips == fp].sort_values("placed", ascending=False)
    t = tot(x)
    pr = tot(x[x.broadcast == 0]) if (x.broadcast == 0).any() else None
    if n in ("Audrain", "Boone", "Osage"):
        out[n] = {"all": t, "print": pr,
                  "outlets": [{"name": r.outlet, "kind": kind(r.outlet), "stories": int(r.placed), "actual": round(r.rate, 3),
                               "expected": round(r.expected, 3)} for r in x.itertuples()]}
    print(f"  {n}: {t['actual']:.0%} actual vs {t['expected']:.0%} expected ({t['stories']} stories)"
          + (f"; print/digital {pr['actual']:.0%} vs {pr['expected']:.0%}" if pr and len(x) > (x.broadcast == 0).sum() else "")
          + "; " + "; ".join(f"{r.outlet} {r.rate:.0%}/{r.expected:.0%}" for r in x.itertuples()))

# ---- measure sensitivity: mention weight x sports weight (the adopted 0.5 / 0.5 are definitions) ----------------------
print("\n## measure sensitivity: same outlets, same terms; each row a different outcome, so compare skill and OOS R2, "
      "not the miss in points. County columns actual / held-out expected.")
print("| Mention | Sports | Mean rate | Held-out mean | Intercept-only mean | Skill | OOS R2 | "
      + " | ".join(n for n, _ in STUDY[:3]) + " |\n|---:|---:|---:|---:|---:|---:|---:|" + "---|" * 3)
for mw in (0.25, 0.5, 1.0):
    for sw in (1, 0.5, 0):
        adopted_weights = (mw, sw) == (MENTION_WEIGHT, SPORTS_WEIGHT)
        y = d.copy() if adopted_weights else d.assign(rate=spill_of(d, mw, sw) / d.placed)
        gy = y[y.fitted]
        if not adopted_weights:              # the adopted row reuses d.expected: the same numbers as the county section
            y["expected"] = heldout_expected(y, gy)
        k, k0 = skill(terms_of(FINAL), gy), skill([], gy)
        cty = []
        for n, fp in STUDY[:3]:
            t = county_figure(y[y.fips == fp])
            cty.append(f"{t['actual']:.0%} / {t['expected']:.0%}")
        mark = "**" if (mw, sw) == (MENTION_WEIGHT, SPORTS_WEIGHT) else ""
        print(f"| {mark}{mw}{mark} | {mark}{sw}{mark} | {gy.rate.mean():.1%} | {k['mean']:.2f} | {k0['mean']:.2f} | "
              f"{k['skill']:+.3f} | {k['r2']:+.3f} | " + " | ".join(cty) + " |")

# ---- outputs: written once, after every column exists ---------------------------------------------------------------------
# QUOTED ROWS: the three counties' county and outlet actual / expected figures that MODEL_CHANGES.md quotes, from
# d.expected (held out).
QUOTED = ["Vandalia Leader", "Boone County Journal", "Centralia Fireside Guard", "The Mexico Ledger", "Columbia Missourian",
          "Columbia Daily Tribune"]
qrows = [{"level": "county", "name": n, "subset": sub, **county_figure(x)}
         for n, fp in STUDY for sub, x in (("all", d[d.fips == fp]), ("print and digital", d[(d.fips == fp) & (d.broadcast == 0)]))
         if len(x)]
qrows += [{"level": "outlet", "name": r.outlet, "subset": r.fips, "stories": int(r.placed), "actual": round(r.rate, 3),
           "expected": round(r.expected, 3)} for r in d[d.outlet.isin(QUOTED) & d.fips.isin(THREE)].itertuples()]
quoted = pd.DataFrame(qrows)
print("\n## quoted rows (actual / held-out expected): analysis/spillover_quoted_rows.csv")
print(quoted.to_string(index=False))
if DRY:
    print("\nSPILL_DRY: nothing written")
else:
    d.to_csv(root / "analysis/spillover_outlets.csv", index=False)
    quoted.to_csv(root / "analysis/spillover_quoted_rows.csv", index=False)
    json.dump(out, open(root / "flows/outlet_spillover_2026_03.json", "w"), indent=1)
    print("\nwrote analysis/spillover_outlets.csv, analysis/spillover_quoted_rows.csv, flows/outlet_spillover_2026_03.json")
