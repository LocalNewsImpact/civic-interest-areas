"""Footprints of potential local news interest: the network tie (flows/market_patterns.py, adopted 2026-10-17) of each
study town, from four travel sources, and the accuracy and replicability of the market each defines.

  tie(H, X) = travel(H -> X) x (1 + 0.3 out + 0.3 in + 0.7 shared places + 0.7 shared coverage), the gate on shared
  terms, the spatial lag and direction boost, home 100 -- the maps' own code, run unchanged up to the figure
  (market_patterns.py, through the weights); only the travel input differs.
Travel sources, each the town's home tracts' regular travel (January-July 2026 for Advan) to the maps' units (towns and
rural block groups), scaled so the busiest unit is 1:
  Advan all months; Advan odd months (Jan, Mar, May, Jul); Advan even months (Feb, Apr, Jun);
  public: the public model's tract -> county shares (public_adjusted_pairs_trnear.csv) with the LODES home-county share,
  spread within counties by jobs and OpenStreetMap destinations at distance^-1 (public_activity_space.py, SPREAD=mix
  BETA=1)
Footprint: hexagons with a tie of 5+ (the maps' cut); market: closed over gaps of 2 hexagons, holes filled.
Also the same with travel alone (all coverage weights 0), to show what the network terms add.
Usage: tie_footprint.py <region>   (flows/regions.json; default columbia)

RUN SETTINGS (environment; printed at the start of every run). The adopted tie-market table (MODEL_CHANGES.md, "+
population, all tracts (adopted)") is
  ATTRPOP=1 REGRULE=1 BETA_IN=0.5 PUBCOL=adjusted_C OUTTAG=_pop tie_footprint.py <region>
  PUBFILE   the public model's tract -> county shares (default public_adjusted_pairs_trnear.csv; a path outside
            analysis/ may be given)
  PUBCOL    its share column (default combined_share; adjusted_C: with the Missouri segment corrections)
  BETA_IN   within-county distance exponent (default 1)
  REGRULE   1: Advan's regularity as a rule on the public prediction
  ATTRPOP   1: population a third of the within-county spread; nonmetro; density:<people per km2>
  OUTTAG    suffix of the output file; OUTDIR its folder (default analysis/)
Diagnostics (2026-10-24, to isolate changes since 2026-10-18; defaults are the current method):
  CAMPUS_IN=1     campus papers (excluded_outlets.CAMPUS) counted as local outlets, as before 2026-10-24
  REHOME=0        Mid Rivers Newsmagazine and Greene County Commonwealth homed where they are filed, as before 2026-10-24
  SCORE=2026-10-18  the market without the home county added, scored whole (before the home county was put in every
                  market and the scores taken beyond it)
  MASKHOME=0      the town's own units kept in its travel before scaling (before they were masked as in
                  market_patterns.py): a hub's own city is then its busiest unit and every other tie shrinks
"""
import csv
import gzip
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

root = Path(__file__).resolve().parents[1]
FLOWS = root / "flows"
REGION_ = sys.argv[1] if len(sys.argv) > 1 else "columbia"
sys.argv = ["market_patterns.py", REGION_]
import os as _os
SETTINGS = {k_: _os.environ.get(k_, d_) for k_, d_ in (("PUBFILE", "public_adjusted_pairs_trnear.csv"), ("PUBCOL", "combined_share"),
            ("BETA_IN", "1"), ("REGRULE", "0"), ("ATTRPOP", "0"), ("OUTTAG", ""), ("OUTDIR", "analysis"), ("CAMPUS_IN", "0"),
            ("REHOME", "1"), ("SCORE", "current"), ("MASKHOME", "1"))}
if _os.environ.get("SUMMARY") != "1":
    print("tie_footprint.py", REGION_, " ".join(f"{k_}={v_}" for k_, v_ in SETTINGS.items()), flush=True)
if _os.environ.get("SUMMARY") == "1":       # the figures the log quotes, over the market's output (OUTTAG, OUTDIR)
    import json as _json
    _R = ("columbia",)                                   # the Columbia-Jefferson City TV market only
    # the settings the summarised runs used, as each recorded them (not this call's defaults)
    _st = {r_: _json.load(open(root / SETTINGS["OUTDIR"] / f"tie_footprint_{r_}{SETTINGS['OUTTAG']}.settings.json")) for r_ in _R}
    _keys = ("PUBFILE", "PUBCOL", "BETA_IN", "REGRULE", "ATTRPOP", "CAMPUS_IN", "REHOME", "SCORE", "MASKHOME")
    _set = {_json.dumps({k_: v_.get(k_) for k_ in _keys}, sort_keys=True) for v_ in _st.values()}
    if len(_set) != 1:
        raise SystemExit(f"the summarised runs used different settings: {_set}")
    print("summary of tie_footprint.py runs with", " ".join(f"{k_}={v_}" for k_, v_ in _json.loads(_set.pop()).items()), flush=True)
    _d = pd.concat([pd.read_csv(root / SETTINGS["OUTDIR"] / f"tie_footprint_{r_}{SETTINGS['OUTTAG']}.csv").assign(region=r_) for r_ in _R])
    _n = _d[_d.measure == "network tie"]
    _acc, _rep = "accuracy: public vs Advan overlap", "replicability: odd vs even overlap"
    print(f"{len(_n)} towns: accuracy median {_n[_acc].median():.2f}, mean {_n[_acc].mean():.3f}; month-split stability median "
          f"{_n[_rep].median():.2f}; travel alone accuracy median {_d[_d.measure == 'travel alone'][_acc].median():.2f}")
    print("by market:", _n.groupby("region", sort=False)[_acc].median().round(2).to_dict())
    print(_n[["region", "town", _rep, _acc]].to_string(index=False))
    sys.exit(0)
sys.path.insert(0, str(root / "analysis"))
import excluded_outlets as _eo  # noqa: E402
if SETTINGS["CAMPUS_IN"] == "1":
    _eo.EXCLUDE = _eo.EXCLUDE - _eo.CAMPUS
if SETTINGS["REHOME"] == "0":
    _eo.HOME_COUNTY = {}
_src = open(FLOWS / "market_patterns.py").read()
# read-only: market_patterns.py writes market_patterns.json before the cut; with the diagnostics above it would write
# other numbers over the published file
_src = _src.replace('json.dump(', '(lambda *a, **k: None)(').replace('open(R / "market_patterns.json", "w")', "None")
_cut = _src.index('maps = {"hexes": hexes, "towns": {}}')
assert '"w")' not in _src[:_cut], "market_patterns.py opens a file for writing before the cut; neutralise it here"
__file__ = str(FLOWS / "market_patterns.py")
exec(compile(_src[:_cut], str(FLOWS / "market_patterns.py"), "exec"))
A = root / "analysis"

# --- travel sources -----------------------------------------------------------------------------------------------
monthly = pq.read_table(A / "od_tract_bg_mo_2026_janjul.parquet").to_pandas()
ALLM = sorted(monthly.month.unique())
bg_unit = P["bg_unit"]


def advan_travel(tracts, months, min_months):
    m = monthly[monthly.tract.isin(tracts) & monthly.month.isin(months)]
    g = m.groupby(["bg", "month"]).v.sum().reset_index()
    k = g.groupby("bg").agg(v=("v", "sum"), n=("month", "nunique"))
    return k.v[k.n >= min_months].to_dict()


# public prediction (as public_activity_space.py, SPREAD=mix BETA=1)
import shapefile
from shapely.geometry import shape as _shape
sf_ = shapefile.Reader(str(root / "census_dl/bg/cb_2020_29_bg_500k")); fl_ = [f[0] for f in sf_.fields[1:]]
bgpt = {}
for sr in sf_.iterShapeRecords():
    p_ = _shape(sr.shape.__geo_interface__).representative_point(); bgpt[sr.record[fl_.index("GEOID")]] = (p_.x, p_.y)
BG = sorted(bgpt); blon = np.array([bgpt[b][0] for b in BG]); blat = np.array([bgpt[b][1] for b in BG]); bcty = np.array([b[:5] for b in BG])
jobs, cons = defaultdict(float), defaultdict(float)
with gzip.open(root / "free/mo_wac_S000_JT00_2023.csv.gz", "rt") as fh:
    for r in csv.DictReader(fh):
        b = r["w_geocode"][:12]
        jobs[b] += float(r["C000"]); cons[b] += sum(float(r[c]) for c in ("CNS07", "CNS16", "CNS17", "CNS18"))
J = np.array([jobs.get(b, 0) for b in BG]); C = np.array([cons.get(b, 0) for b in BG])
import os as _os
osm = pd.read_csv(FLOWS / "reach/destinations_mo.csv", dtype={"block_group": str}).block_group.value_counts()
O_ = np.array([osm.get(b, 0) for b in BG], float)
share_in = lambda x: np.where(pd.Series(x).groupby(bcty).transform("sum").values > 0, x / np.maximum(pd.Series(x).groupby(bcty).transform("sum").values, 1e-9), 0)
_bgp = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_BG29.txt", dtype=str, encoding="utf-8-sig")
_bgp = dict(zip(_bgp.STATEFP + _bgp.COUNTYFP + _bgp.TRACTCE + _bgp.BLKGRPCE, _bgp.POPULATION.astype(float)))
POPB = np.array([_bgp.get(b, 0.0) for b in BG])
# ATTRPOP=1: where people live is a third of the within-county spread (visits to family, friends, churches, schools)
ATTR_POP = (0.5 * share_in(J) + 0.5 * share_in(C)) / 3 + share_in(O_) / 3 + share_in(POPB) / 3 + 1e-6
ATTR_DEST = 0.5 * (0.5 * share_in(J) + 0.5 * share_in(C)) + 0.5 * share_in(O_) + 1e-6
ATTRPOP = _os.environ.get("ATTRPOP", "0")      # 1: every tract; nonmetro: tracts in nonmetro counties (RUCC 2023 >= 4)
_ru = pd.read_csv(root / "census_dl/ref/rucc2023.csv", dtype=str, encoding="latin-1")
_ru = _ru[_ru.Attribute == "RUCC_2023"]
NONMETRO = {r_.FIPS.zfill(5) for r_ in _ru.itertuples() if int(r_.Value) >= 4}
# ATTRPOP=density:<people per km2>: population in the spread for home tracts below that density (2020 population /
# land area of the tract's block groups, Census 2020 cartographic boundaries ALAND)
_al = defaultdict(float)
for _sr in shapefile.Reader(str(root / "census_dl/bg/cb_2020_29_bg_500k")).iterRecords():
    _al[_sr["GEOID"][:11]] += float(_sr["ALAND"]) / 1e6
DENS = {}


def attr_for(t):
    if ATTRPOP == "1" or (ATTRPOP == "nonmetro" and t[:5] in NONMETRO):
        return ATTR_POP
    if ATTRPOP.startswith("density:"):
        if not DENS:
            DENS.update({t_: tc.POPULATION.get(t_, 0) / max(_al.get(t_, 0), 1e-6) for t_ in tc.index})
    if ATTRPOP.startswith("density:") and DENS.get(t, 1e9) < float(ATTRPOP.split(":")[1]):
        return ATTR_POP
    return ATTR_DEST
trc = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_TR29.txt", dtype=str, encoding="utf-8-sig"); trc["t"] = trc.STATEFP + trc.COUNTYFP + trc.TRACTCE
tc = trc.set_index("t")[["LATITUDE", "LONGITUDE", "POPULATION"]].astype(float)
Wl = pd.read_csv(A / "public_work_model_pairs_v1.csv", dtype={"tract": str, "j": str, "home": str}, usecols=["tract", "home", "j", "y"])
home_lodes = (Wl[Wl.home == Wl.j].groupby("tract").y.sum() / Wl.groupby("tract").y.sum()).fillna(0.5)
import os as _os
PUBFILE = _os.environ.get("PUBFILE", "public_adjusted_pairs_trnear.csv")     # the public model's tract -> county shares
BETA_IN = float(_os.environ.get("BETA_IN", "1"))                              # within-county distance exponent
Qp = pd.read_csv(A / PUBFILE, dtype={"tract": str, "j": str, "home": str})
Qp = Qp[Qp.j.str[:2] == "29"]
REGRULE = _os.environ.get("REGRULE") == "1"
# regularity_rule.csv: logit P(block group visited in 4+ of 7 months) = const + a log(share of the tract's visits) +
# b log(tract population), fitted on Advan (85.7% agreement); a predicted block group counts if P >= 0.5
RB = pd.read_csv(A / "regularity_rule.csv", index_col=0).iloc[:, 0].values
PUBCOL = _os.environ.get("PUBCOL", "combined_share")      # adjusted_C: with the Missouri segment corrections
qshare = {t: dict(zip(g.j, g[PUBCOL] / g[PUBCOL].sum())) for t, g in Qp.groupby("tract")}
KXp, KYp = 111.32 * math.cos(math.radians(38.7)), 110.57


def public_travel(tracts):
    tot = np.zeros(len(BG))
    for t in tracts:
        if t not in qshare or t not in tc.index:
            continue
        d = np.hypot((blon - tc.LONGITUDE[t]) * KXp, (blat - tc.LATITUDE[t]) * KYp)
        w = attr_for(t) * np.maximum(d, 1.0) ** -BETA_IN
        within = w / pd.Series(w).groupby(bcty).transform("sum").values
        hs = home_lodes.get(t, 0.5)
        cs = np.array([qshare[t].get(c, 0.0) for c in bcty]) * (1 - hs)
        cs[bcty == t[:5]] = hs
        pr = within * cs
        if REGRULE:      # Advan's regularity, as a rule: keep block groups whose predicted share would be regular
            pr = np.where(RB[0] + RB[1] * np.log(np.maximum(pr, 1e-12)) + RB[2] * math.log(max(tc.POPULATION[t], 1)) > 0, pr, 0)
        tot += tc.POPULATION[t] * pr
    return {b: v for b, v in zip(BG, tot) if v > 0}


def own_units(town):
    return {P["bg_unit"].get(h) for h in town_bgs(town)} | {"rural:" + h for h in town_bgs(town)} | {HOME_PLACE[town]}


def to_units(bgv, town=None):
    """travel to the maps' units, scaled so the busiest unit is 1; the town's own units are masked first, as in
    market_patterns.py (nobody travels to home -- home is 100 by definition)"""
    drop = own_units(town) if town and SETTINGS["MASKHOME"] == "1" else set()
    u = defaultdict(float)
    for b, v in bgv.items():
        if bg_unit.get(b) and bg_unit[b] not in drop:
            u[bg_unit[b]] += v
    mx = max(u.values()) if u else 1
    return {k: v / mx for k, v in u.items() if v > 0}


# --- the tie map (the loop body of market_patterns.py, one travel input) ----------------------------------------------
def tie_map(town, Hk, weights=BASE_W):
    Hk_u, Hk = Hk, norm_hex(Hk)             # busiest hexagon = 1 (market_patterns.norm_hex); Hk_u: busiest place = 1
    cu = COV[town]
    own_u = {P["bg_unit"].get(h) for h in town_bgs(town)} | {HOME_PLACE[town]}
    OV = {X: overlap_of(Hk, own_u, X) for X in place_outlets if X not in own_u}
    h_cov = cov_dist([o for o, al in by_outlet.items() if home_of(al[0]) == STUDY[town] and o not in EXCLUDE])
    mkt = {u_ for u_, w in Hk_u.items() if w >= 0.05}
    inm_ = lambda d_: {u_: w for u_, w in d_.items() if u_ in mkt}
    SC = {X: overlap_dists(inm_(h_cov), inm_(cov_dist(place_outlets[X])), own_u | {X}) for X in place_outlets if X not in own_u}
    wo, wi, wv, wc = weights
    raw = {}
    for k, u in unit_at.items():
        t_ = tr_at(Hk, k, u)
        if t_ <= 0:
            continue
        xk = hex_place.get(k) or u
        o_, i_ = cu["out"].get(k, 0), cu["in"].get(k, 0)
        gate = 1.0 if (o_ + i_) >= 0.10 else 0.0
        raw[k] = min(DCAP, t_ * (1 + wo * o_ + wi * i_ + gate * (wv * OV.get(xk, 0) + wc * SC.get(xk, 0))))
    if raw:
        raw = spatial(raw, home_hexes_of[town])
    out_ = {k: 100 * x for k, x in raw.items()}
    for k in home_hexes_of[town]:
        out_[k] = 100.0
    return out_


# --- markets --------------------------------------------------------------------------------------------------------
NB = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]
disk = lambda r: [(q, s_) for q in range(-r, r + 1) for s_ in range(-r, r + 1) if abs(q) + abs(s_) + abs(q + s_) <= 2 * r]


def market(foot, r=2):
    foot = {tuple(map(int, k.split(","))) for k in foot}
    if not foot:
        return set()
    dsk = disk(r)
    dil = {(a + dq, b + dr) for a, b in foot for dq, dr in dsk}
    clo = {h for h in dil if all((h[0] + dq, h[1] + dr) in dil for dq, dr in dsk)} | foot
    qs = [h[0] for h in clo]; rs = [h[1] for h in clo]
    box = {(q, r_) for q in range(min(qs) - 1, max(qs) + 2) for r_ in range(min(rs) - 1, max(rs) + 2)}
    outside, stack = set(), [(min(qs) - 1, min(rs) - 1)]
    while stack:
        h = stack.pop()
        if h in outside or h in clo or h not in box:
            continue
        outside.add(h); stack.extend((h[0] + dq, h[1] + dr) for dq, dr in NB)
    return box - outside


def n_markets(region, share=0.05):
    left, sizes = set(region), []
    while left:
        stack = [left.pop()]; k = 1
        while stack:
            c = stack.pop()
            for dq, dr in NB:
                o = (c[0] + dq, c[1] + dr)
                if o in left:
                    left.discard(o); stack.append(o); k += 1
        sizes.append(k)
    return sum(k >= share * len(region) for k in sizes)


jac = lambda a, b: len(a & b) / len(a | b) if (a | b) else float("nan")
CUT = 5
# THE HOME COUNTY IS IN EVERY MARKET by definition: residents have an inherent interest in its news (county government,
# schools, courts, taxes) whether or not they travel to all of it. Scores compare the travel-defined part beyond it.
home_county_hexes = lambda town: ({tuple(map(int, k.split(","))) for k, c_ in hex_county.items() if c_ == STUDY[town]}
                                   if SETTINGS["SCORE"] != "2026-10-18" else set())
beyond = lambda M_, town: M_ - home_county_hexes(town)
if not _os.environ.get("TIE_LIB"):          # TIE_LIB=1: load the functions only (confidence_layer.py)
    rows = []
    for town in STUDY:
        tracts = sorted({h[:11] for h in town_bgs(town)})
        src = {"all": to_units(advan_travel(tracts, ALLM, 4), town), "odd": to_units(advan_travel(tracts, ALLM[0::2], 2), town),
               "even": to_units(advan_travel(tracts, ALLM[1::2], 2), town), "public": to_units(public_travel(tracts), town)}
        for lab, w in (("network tie", BASE_W), ("travel alone", (0, 0, 0, 0))):
            M = {s: market({k for k, v in tie_map(town, Hk, w).items() if v >= CUT}) | home_county_hexes(town) for s, Hk in src.items()}
            B = {s: beyond(m_, town) for s, m_ in M.items()}            # the travel-defined part, scored
            rows.append({"town": town, "measure": lab, "km2 (all months)": round(len(M["all"]) * 5.85),
                         "km2 beyond the home county": round(len(B["all"]) * 5.85),
                         "markets (all months)": n_markets(M["all"]),
                         "replicability: odd vs even overlap": round(jac(B["odd"], B["even"]), 2),
                         "accuracy: public vs Advan overlap": round(jac(B["public"], B["all"]), 2),
                         "public area / Advan area": round(len(B["public"]) / max(len(B["all"]), 1), 2),
                         "markets public / Advan": f"{n_markets(M['public'])} / {n_markets(M['all'])}"})
    R_ = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    print(R_.to_string(index=False))
    print("\nmedian over towns:")
    print(R_.groupby("measure")[["replicability: odd vs even overlap", "accuracy: public vs Advan overlap", "public area / Advan area"]].median().to_string())
    _od = root / SETTINGS["OUTDIR"]
    _od.mkdir(parents=True, exist_ok=True)
    R_.to_csv(_od / f"tie_footprint_{REGION_}{SETTINGS['OUTTAG']}.csv", index=False)
    import json as _json
    _json.dump(SETTINGS, open(_od / f"tie_footprint_{REGION_}{SETTINGS['OUTTAG']}.settings.json", "w"), indent=1)   # read by SUMMARY=1


    # DETAIL=town,town: each market (lobe) of the public and the Advan tie footprints, named, with what Advan observes in it
    import os
    for town in [t for t in os.environ.get("DETAIL", "").split(",") if t]:
        tracts = sorted({h[:11] for h in town_bgs(town)})
        T_all = tie_map(town, to_units(advan_travel(tracts, ALLM, 4), town))
        T_pub = tie_map(town, to_units(public_travel(tracts), town))
        H_all = to_units(advan_travel(tracts, ALLM, 4), town)
        adv_travel_hex = {k: tr_at(H_all, k, u) for k, u in unit_at.items()}
        tot_tr = sum(adv_travel_hex.values())
        for lab, T in (("Advan", T_all), ("public", T_pub)):
            reg = market({k for k, v in T.items() if v >= CUT})
            left, parts = set(reg), []
            while left:
                stack = [left.pop()]; comp = {stack[0]}
                while stack:
                    c = stack.pop()
                    for dq, dr in NB:
                        o = (c[0] + dq, c[1] + dr)
                        if o in left:
                            left.discard(o); stack.append(o); comp.add(o)
                parts.append(comp)
            parts = [p for p in parts if len(p) >= 0.05 * len(reg)]
            print(f"\n{town} -- {lab} tie market: {len(parts)} markets, {len(reg) * 5.85:,.0f} km2")
            for p in sorted(parts, key=len, reverse=True):
                ks = [f"{a},{b}" for a, b in p]
                names = defaultdict(float)
                for k in ks:
                    pl = hex_place.get(k)
                    nm = (pl_shapes[pl][0]["NAME"] if pl in pl_shapes else pl) if pl else ("rural " + cname.get((unit_at.get(k) or "rural:00000")[6:11], "?"))
                    names[nm] += T.get(k, 0)
                top = sorted(names.items(), key=lambda z: -z[1])[:3]
                adv_in = np.mean([T_all.get(k, 0) for k in ks]); trav_in = sum(adv_travel_hex.get(k, 0) for k in ks) / tot_tr
                print(f"  {len(p) * 5.85:7,.0f} km2  {', '.join(n for n, _ in top):45s}  Advan tie inside (mean) {adv_in:5.1f}  "
                      f"Advan travel inside {100 * trav_in:4.1f}%  inside the Advan market {100 * len(p & market({k for k, v in T_all.items() if v >= CUT})) / len(p):3.0f}%")
