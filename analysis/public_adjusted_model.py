"""The public travel model with Advan-learned adjustments, recomputed from tracts.

Public model: BASE (default the trade area build public_model_pairs_tiers_tac.csv), tract -> county shares.
Adjustments, learned from Advan county -> county out-of-county shares (January-September 2026) on the other counties
(8 folds of home counties) and applied to each held-out county's tracts:
  destination   A: one factor per destination county (Advan inflow / public inflow)
                B: the same factor as a function of public destination measures -- log 2025 taxable sales, log 2020
                   population, nonmetro (RUCC 2023 >= 4), log arts and recreation employment (CBP 2022, NAICS 71) --
                   weighted least squares on the log factor; transferable to any county
                C: no destination factor (segment factors only)
  distance      one factor per distance band (<15, 15-30, 30-50, 50-80, 80-120, 120+ miles) per class of home county,
                applied at the tract's own distance to the destination
  adjacency     one factor for neighbouring counties per class of home county
  groups        COMMUTE=commute_out,commute_in,commute_rank,dest_order,dest_class,...: one factor per class per value
  metro core    CORE=1: one factor per class for the destination that is a central county (OMB 2023) of the home
                county's own metro or micro area, or the nearest central county for a home county in none
Fitted in turn and iterated 5 rounds at county level; applied multiplicatively to tract shares, renormalised per
tract, rolled up to counties by 2020 tract population.

Destination set: every model is scored, and every factor learned, on the public model's destinations (counties within
200 miles of the tract); Advan and the Advan-fitted model are renormalised over that set, and Advan's share outside it
is reported. Scores: share-weighted error and log-ratio error (public_scoring.py).

The structure is a configuration (keys(cfg)); run as a script it is read from the environment (SPLIT3, C5AS,
DIST_BY_RANK, DIST_HUB, CORE, CORE_NEAR, TRANSFER, RC_PF, COMMUTE, POOLED), as before. public_adjusted_nested.py
imports the functions to choose the structure inside an outer cross-validation loop.
Environment (printed at start): BASE, OUTTAG, EXPORT and the structure SPLIT3, C5AS, DIST_BY_RANK, DIST_HUB, CORE,
CORE_NEAR, TRANSFER, RC_PF, COMMUTE, POOLED. public_adjusted_pairs_trnear.csv (the 2026-10-18 structure on the
2026-10-18 base; read by tie_footprint.py, public_activity_space.py, directions_per_tract.py):
  LEGACY=1 CLASS5=_g_40_sales OUTTAG=_c5_g_40_sales python analysis/assemble_public_by_class.py
  BASE=public_model_pairs_tiers_byclass_c5_g_40_sales.csv SPLIT3=1 C5AS="class 2" DIST_BY_RANK=1 CORE= CORE_NEAR=1 \
    TRANSFER=1 RC_PF=1.0 COMMUTE=commute_rank,dest_order,dest_class POOLED= OUTTAG=_trnear python analysis/public_adjusted_model.py
(every command of the chain: scratchpad review_fixes/public_commands.sh, 2026-10-24). Factors learned on all counties
are written for reuse: analysis/public_adjustments.csv (distance and adjacency by class; destination coefficients).
"""
import csv
import gzip
import os
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
from gravity_terms import all_pairs, root  # noqa: E402
from public_scoring import per_county  # noqa: E402

A_ = root / "analysis"
S = pd.read_csv(A_ / "compare_shares.csv", dtype={"i": str, "j": str})
pp = all_pairs()
assert (pp.i.values == S.i.values).all() and (pp.j.values == S.j.values).all()
ADJ = set(zip(pp.i[pp.adjacent == 1], pp.j[pp.adjacent == 1]))
a_raw = S.advan.values
adv_raw = S["Advan-fitted (adopted, counties held out)"].values
BASE = os.environ.get("BASE", "public_model_pairs_tiers_tac.csv")      # the public model the adjustments act on
T = pd.read_csv(A_ / BASE, dtype={"tract": str, "j": str, "home": str})
T = T[(T.j.str[:2] == "29") & (T.home != T.j)].reset_index(drop=True)
_tr = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_TR29.txt", dtype=str, encoding="utf-8-sig")
tpop = dict(zip(_tr.STATEFP + _tr.COUNTYFP + _tr.TRACTCE, _tr.POPULATION.astype(float)))
unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(A_ / "county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
_dl = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str).dropna(subset=["FIPS County Code"])
_bigm = set((_dl["FIPS State Code"] + _dl["FIPS County Code"])[_dl["CBSA Code"].isin(["28140", "41180"])])

# ---- integer codes for fast group sums ----------------------------------------------------------------------------
homes_S, ii = np.unique(S.i.values, return_inverse=True)
key = list(zip(S.i, S.j))
_kidx = {k: n for n, k in enumerate(key)}
sidx = np.array([_kidx[(h, j)] for h, j in zip(T.home, T.j)])         # T row -> S row
tracts_T, tcode = np.unique(T.tract.values, return_inverse=True)
tw = T.tract.map(tpop).values
NS = len(S)

# ---- common destination set: the public model's support ----------------------------------------------------------
COMMON = np.zeros(NS, bool); COMMON[sidx] = True


def renorm_S(x):
    s = np.bincount(ii, x, minlength=len(homes_S))[ii]
    return np.where(s > 0, x / np.where(s > 0, s, 1), 0.0)


a = renorm_S(a_raw * COMMON)                     # Advan, renormalised over the common set
adv = renorm_S(adv_raw * COMMON)                 # Advan-fitted, the same
outside = pd.Series(a_raw * ~COMMON).groupby(S.i.values).sum()     # Advan share outside the common set, per home


def tract_norm(x, rows=None):
    """Normalise shares to 1 within each tract (over the rows given)."""
    if rows is None:
        s = np.bincount(tcode, x, minlength=len(tracts_T))[tcode]
    else:
        tc = tcode[rows]; s = np.bincount(tc, x, minlength=len(tracts_T))[tc]
    return np.where(s > 0, x / np.where(s > 0, s, 1), 0.0)


def roll(share_T):
    """Tract shares (aligned with T) -> county shares on the S frame, weighted by 2020 tract population."""
    x = np.bincount(sidx, share_T * tw, minlength=NS)
    return renorm_S(x)


base0 = tract_norm(T.combined_share.values.astype(float))
p0 = roll(base0)

# ---- segments (score_segments.py) and folds ------------------------------------------------------------------------
seg = lambda i: {"class 1": "small rural", "class 2": "indep. towns", "class 4": "hubs"}.get(
    tier.get(unit(i), "class 1"), "commuter: major metro" if i in _bigm else "commuter: regional hub")
SEGS = ["small rural", "indep. towns", "commuter: major metro", "commuter: regional hub", "hubs"]
SEG_OF = pd.Series({h: seg(h) for h in homes_S})
iu = np.array([unit(i) for i in S.i])
folds = np.array_split(np.random.default_rng(7).permutation(sorted(set(iu))), 8)
fold_of = {c: k for k, f in enumerate(folds) for c in f}
fold_S = np.array([fold_of[u] for u in iu])
fold_T = np.array([fold_of[unit(h)] for h in T.home])
CUTS = [15, 30, 50, 80, 120]
BAND = ["<15 mi", "15-30", "30-50", "50-80", "80-120", "120+"]

# ---- public destination measures ---------------------------------------------------------------------------------
ts = pd.read_csv(root / "census_dl/mo_dor/cnty/DI60IT15_SLS_CNTY_F_2025.csv", dtype=str, encoding="utf-8-sig")
ts = pd.Series(ts.Total.str.replace(r"[$,\s]", "", regex=True).astype(float).values, index="29" + ts.MOID.str.zfill(3).replace("193", "186"))   # DOR keeps Ste. Genevieve's pre-1979 code
co = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
pop_c = pd.Series(co.POPULATION.astype(float).values, index=co.STATEFP + co.COUNTYFP)
rucc = pd.read_csv(root / "census_dl/ref/rucc2023.csv", dtype=str, encoding="latin-1")
rucc = rucc[rucc.Attribute == "RUCC_2023"]
nonmetro = pd.Series({r.FIPS.zfill(5): float(int(r.Value) >= 4) for r in rucc.itertuples()})
cbp = pd.read_csv(root / "census_dl/cbp/cbp22co.txt", dtype=str, usecols=["fipstate", "fipscty", "naics", "emp", "est"])
arts = cbp[cbp.naics == "71----"].assign(f=lambda d: d.fipstate + d.fipscty).set_index("f").emp.astype(float)
dests = sorted(set(S.j))
dpos = {j: n for n, j in enumerate(dests)}
jS = np.array([dpos[j] for j in S.j]); jT = np.array([dpos[j] for j in T.j])
DX = pd.DataFrame({"const": 1.0, "log_sales": np.log(ts.reindex(dests)), "log_pop": np.log(pop_c.reindex(dests)),
                   "nonmetro": nonmetro.reindex(dests).fillna(0), "log_arts": np.log1p(arts.reindex(dests).fillna(0))},
                  index=dests)

dband0_S = np.digitize(S.dist.values, CUTS)
dband0_T = np.digitize(T.miles.values, CUTS)
adj_S = np.array([(i, j) in ADJ for i, j in zip(S.i, S.j)])
adj_T = np.array([(h, j) in ADJ for h, j in zip(T.home, T.j)])
# metro core: the destination is a central county (OMB 2023) of the home county's own metro or micro area, or, for a
# home county in none, its nearest central county (CORE=1)
dl = _dl[_dl["FIPS State Code"] == "29"].copy()
dl["f"] = dl["FIPS State Code"] + dl["FIPS County Code"]
cbsa = dict(zip(dl.f, dl["CBSA Code"]))
central = set(dl.f[dl["Central/Outlying County"] == "Central"])
dmiles = dict(zip(zip(S.i, S.j), S.dist))
nearest = {i: min((j for j in central if j != i), key=lambda j: dmiles.get((i, j), 1e9)) for i in set(S.i)}
core_of = lambda i, j: (j in central and cbsa.get(i) is not None and cbsa.get(i) == cbsa.get(j)) or (cbsa.get(i) is None and nearest[i] == j)
core_S = np.array([core_of(i, j) for i, j in zip(S.i, S.j)])
core_T = np.array([core_of(h, j) for h, j in zip(T.home, T.j)])
# pair commuting: LODES 2023 primary jobs (JT01), Missouri main + aux OD, as gravity_terms.py (the aux file adds
# out-of-state residents working in Missouri; it changes no Missouri pair)
_flow, _work = defaultdict(float), defaultdict(float)
for _f in ("free/mo_od_main_JT01_2023.csv.gz", "free/mo_od_aux_JT01_2023.csv.gz"):
    with gzip.open(root / _f, "rt") as fh:
        for r in csv.DictReader(fh):
            h, w_, n = r["h_geocode"][:5], r["w_geocode"][:5], float(r["S000"])
            _work[h] += n; _flow[h, w_] += n
CB = [0.005, 0.02, 0.05, 0.15, 0.30]
cband = lambda i, j: int(np.digitize(_flow.get((i, j), 0) / max(_work.get(i, 1), 1), CB))
cinband = lambda i, j: int(np.digitize(_flow.get((j, i), 0) / max(_work.get(j, 1), 1), CB))
# the destination's rank among the home county's out-of-county LODES work destinations (Missouri): 1 dominant,
# 2 secondary, 3 = ranks 3-5, 4 = the rest (commute_rank)
_rank = {}
for _i in set(S.i):
    _r = sorted(((v, w_) for (h, w_), v in _flow.items() if h == _i and w_ != _i and w_[:2] == "29"), reverse=True)
    for n, (_, w_) in enumerate(_r):
        _rank[_i, w_] = 1 if n == 0 else 2 if n == 1 else 3 if n < 5 else 4
crank_of = lambda i, j: _rank.get((i, j), 4)
cout_S = np.array([cband(i, j) for i, j in zip(S.i, S.j)]); cout_T = np.array([cband(h, j) for h, j in zip(T.home, T.j)])
cin_S = np.array([cinband(i, j) for i, j in zip(S.i, S.j)]); cin_T = np.array([cinband(h, j) for h, j in zip(T.home, T.j)])
crank_S = np.array([crank_of(i, j) for i, j in zip(S.i, S.j)]); crank_T = np.array([crank_of(h, j) for h, j in zip(T.home, T.j)])
dist_T = np.array([dmiles.get((h, j), 999) for h, j in zip(T.home, T.j)])

# destination order (central place hierarchy), public: 2025 taxable sales and pull factor (DOR), CBP 2022 marinas
# (713930) + RV parks and recreational camps (7212) establishments per resident (resort)
_pf = (ts / pop_c.reindex(ts.index)) / (ts.sum() / pop_c.reindex(ts.index).sum())
_acc = cbp[cbp.naics.isin(["713930", "7212//"])].assign(f=lambda d: d.fipstate + d.fipscty, e=lambda d: d.est.astype(float)).groupby("f").e.sum()
_resort = (_acc.reindex(ts.index).fillna(0) / pop_c.reindex(ts.index) * 1e4)   # marinas + RV parks and camps per 10,000
_ORD = {False: {"core": set(ts.sort_values(ascending=False).index[:3]),
                "big_metro": {f for f, c in cbsa.items() if c in ("28140", "41180")},
                "rcut": _resort.quantile(0.9)}}
# TRANSFER=1: the same orders in terms that mean the same in any state --
#   metro core = central county of a metro area of 1,000,000+ (OMB 2023, Census 2024 CBSA population); rest of such a
#   metro = its outlying counties; regional centre = pull factor >= 1 and trade-area customers (sales / the state's
#   per-capita sales) >= 60,000; resort = marinas + RV parks and camps per resident in the top tenth of all U.S. counties
_cpop = pd.read_csv(root / "census_dl/ref/cbsa-est2024-alldata.csv", encoding="latin-1", dtype=str)
_cpop = _cpop[_cpop.LSAD.str.endswith("Statistical Area")].set_index("CBSA").POPESTIMATE2024.astype(float)
_big = {f for f, c in cbsa.items() if _cpop.get(c, 0) >= 1e6}
_ORD[True] = {"core": _big & central, "big_metro": _big - (_big & central),
              "rcut": (_acc.reindex(pop_c.index).fillna(0) / pop_c * 1e4).quantile(0.9)}
_cust = ts / (ts.sum() / pop_c.reindex(ts.index).sum())


def env_cfg():
    """The structure from the environment (the script's historical interface)."""
    g = lambda k, d=None: os.environ.get(k, d)
    return {"SPLIT3": g("SPLIT3") == "1", "C5AS": g("C5AS", "class 5"), "DIST_BY_RANK": g("DIST_BY_RANK") == "1",
            "DIST_HUB": g("DIST_HUB") == "1", "CORE": g("CORE") == "1", "CORE_NEAR": g("CORE_NEAR") == "1",
            "TRANSFER": g("TRANSFER") == "1", "RC_PF": float(g("RC_PF", "1.0")),
            "COMMUTE": tuple(x for x in g("COMMUTE", "").split(",") if x), "POOLED": tuple(x for x in g("POOLED", "").split(",") if x)}


def keys(cfg):
    """Every grouping key the structure needs, on the county frame (S) and the tract frame (T)."""
    K = SimpleNamespace(cfg=cfg)
    split, c5as = cfg["SPLIT3"], cfg["C5AS"]

    def klass(h):
        c = tier.get(unit(h), "class 1")
        if split and c == "class 3" and h not in _bigm:
            return c5as                        # C5AS="class 2": learn and apply independent-town factors for them
        return c
    K.klass = klass
    K.LABEL = {"class 1": "small rural", "class 2": "indep. towns", "class 3": "commuter", "class 4": "hubs"}
    if split:
        K.LABEL = {"class 1": "small rural", "class 2": "indep. towns", "class 3": "commuter: major metro",
                   "class 5": "commuter: regional hub", "class 4": "hubs"}
    kc = {h: klass(h) for h in set(S.i) | set(S.j)}
    K.cls_S = np.array([kc[i] for i in S.i]); K.cls_T = np.array([kc[h] for h in T.home])
    O = _ORD[cfg["TRANSFER"]]

    def dest_order(j):
        if j in O["core"]: return 1                                         # metro core
        if j in O["big_metro"]: return 6                                    # rest of the large metros
        if _resort.get(j, 0) >= O["rcut"]: return 5                         # resort / recreation
        big_enough = _cust.get(j, 0) >= 60000 if cfg["TRANSFER"] else ts.get(j, 0) > 1e9
        if _pf.get(j, 0) >= cfg["RC_PF"] and big_enough: return 2            # regional centre
        if _pf.get(j, 0) >= 1.0: return 3                                   # sub-regional town
        return 4                                                            # local
    K.dest_order = dest_order
    # CORE_NEAR: a metro core (1) or the rest of a big metro (6) within 50 miles of home is its own order (7, 8)
    near = lambda o, d: (7 if o == 1 else 8 if o == 6 else o) if (cfg["CORE_NEAR"] and d < 50 and o in (1, 6)) else o
    do = {j: dest_order(j) for j in dests}
    dord_S = np.array([near(do[j], d) for j, d in zip(S.j, S.dist.values)])
    dord_T = np.array([near(do[j], d) for j, d in zip(T.j, dist_T)])
    hub_S = (crank_S == 1) & np.isin(dord_S, [1, 2, 7]); hub_T = (crank_T == 1) & np.isin(dord_T, [1, 2, 7])
    K.dband_S, K.band_T = dband0_S.copy(), dband0_T.copy()
    if cfg["DIST_BY_RANK"]:      # distance factors learned apart for the dominant/secondary county
        hubw = 20 if cfg["DIST_HUB"] else 10
        K.dband_S = K.dband_S + 10 * ((crank_S <= 2) & ~hub_S) + hubw * hub_S
        K.band_T = K.band_T + 10 * ((crank_T <= 2) & ~hub_T) + hubw * hub_T
    dcls_S = np.array([int(kc[j][-1]) for j in S.j]); dcls_T = np.array([int(kc[j][-1]) for j in T.j])
    allg_S = {"commute_out": cout_S, "commute_in": cin_S, "dest_class": dcls_S, "dest_class_band": dcls_S * 10 + K.dband_S,
              "dest_order": dord_S, "dest_order_band": dord_S * 10 + K.dband_S, "commute_rank": crank_S, "rank_order": crank_S * 10 + dord_S}
    allg_T = {"commute_out": cout_T, "commute_in": cin_T, "dest_class": dcls_T, "dest_class_band": dcls_T * 10 + K.band_T,
              "dest_order": dord_T, "dest_order_band": dord_T * 10 + K.band_T, "commute_rank": crank_T, "rank_order": crank_T * 10 + dord_T}
    K.groups = list(cfg["COMMUTE"])
    K.g_S = {g: allg_S[g] for g in K.groups}; K.g_T = {g: allg_T[g] for g in K.groups}
    pooled_S = {"hub": hub_S.astype(int), "hub_band": hub_S * (1 + np.digitize(S.dist.values, [15, 30, 50]))}
    pooled_T = {"hub": hub_T.astype(int), "hub_band": hub_T * (1 + np.digitize(T.miles.values, [15, 30, 50]))}
    K.pooled = list(cfg["POOLED"])
    K.p_S = {g: pooled_S[g] for g in K.pooled}; K.p_T = {g: pooled_T[g] for g in K.pooled}
    K.core = cfg["CORE"]
    K.dord_S, K.hub_S = dord_S, hub_S
    # masks by class: band, adjacency, each group, metro core
    K.blocks = {}
    for c in K.LABEL:
        mc = K.cls_S == c
        K.blocks[c] = {"band": [(b, mc & (K.dband_S == b)) for b in np.unique(K.dband_S)],
                       "adj": [(v, mc & (adj_S == v)) for v in (True, False)],
                       "groups": [(g, [(v, mc & (K.g_S[g] == v)) for v in np.unique(K.g_S[g])]) for g in K.groups],
                       "core": [(v, mc & (core_S == v)) for v in (True, False)]}
    K.pblocks = [(g, [(v, K.p_S[g] == v) for v in np.unique(K.p_S[g])]) for g in K.pooled]
    return K


def learn(K, p_base, train, parametric, aa=None):
    """Destination, distance, adjacency and group factors from the training home counties (boolean mask on S)."""
    aa = a if aa is None else aa
    p = p_base.copy()
    fd = pd.Series(1.0, index=dests); fb = {}; fa = {}; fc = {}; fx = {}
    a_tr = np.where(train, aa, 0.0)

    def ratio(m):
        mt = train & m
        return a_tr[mt].sum() / max(p[mt].sum(), 1e-12) if mt.any() else 1.0
    for _ in range(5):
        if parametric is not None:
            ain = np.bincount(jS, a_tr, minlength=len(dests)); pin = np.bincount(jS, np.where(train, p, 0.0), minlength=len(dests))
            r = pd.Series(np.where(pin > 0, ain / np.where(pin > 0, pin, 1), np.nan), index=dests)
            if parametric:
                w = ain + 1e-4
                y = np.log(r.clip(0.05, 20).fillna(1.0))
                beta = np.linalg.lstsq(DX.values * np.sqrt(w)[:, None], y.values * np.sqrt(w), rcond=None)[0]
                step = pd.Series(np.exp(DX.values @ beta), index=dests)
            else:
                step = r.clip(0.05, 20).fillna(1.0)
            fd *= step
            p = renorm_S(p * step.values[jS])
        for c in K.LABEL:
            B = K.blocks[c]
            for b, m in B["band"]:
                f = ratio(m); fb[c, b] = fb.get((c, b), 1.0) * f; p[m] *= f
            p = renorm_S(p)
            for v, m in B["adj"]:
                f = ratio(m); fa[c, v] = fa.get((c, v), 1.0) * f; p[m] *= f
            p = renorm_S(p)
            for g, lst in B["groups"]:
                for v, m in lst:
                    f = ratio(m); fx[g, c, v] = fx.get((g, c, v), 1.0) * f; p[m] *= f
                p = renorm_S(p)
        for g, lst in K.pblocks:                                    # learned across all classes
            for v, m in lst:
                f = ratio(m); fx[g, "all", v] = fx.get((g, "all", v), 1.0) * f; p[m] *= f
            p = renorm_S(p)
        if K.core:
            for c in K.LABEL:
                for v, m in K.blocks[c]["core"]:
                    f = ratio(m); fc[c, v] = fc.get((c, v), 1.0) * f; p[m] *= f
                p = renorm_S(p)
    coef = None
    if parametric:
        w = np.bincount(jS, a_tr, minlength=len(dests)) + 1e-4
        coef = np.linalg.lstsq(DX.values * np.sqrt(w)[:, None], np.log(fd.values) * np.sqrt(w), rcond=None)[0]
        fd = pd.Series(np.exp(DX.values @ coef), index=dests)
    return SimpleNamespace(fd=fd, fb=fb, fa=fa, fc=fc, fx=fx, coef=coef)


def _lut(cls_arr, val_arr, table, gname=None):
    """Factor per row from a dict keyed (class, value) or (group, class, value); 1.0 where absent."""
    codes, inv = np.unique(np.char.add(np.char.add(cls_arr.astype(str), "|"), val_arr.astype(int).astype(str)), return_inverse=True)
    vals = []
    for cd in codes:
        c, v = cd.split("|"); v = int(v)
        vals.append(table.get((gname, c, v) if gname else (c, v), 1.0))
    return np.asarray(vals)[inv]


def apply(K, base_T, rows, F):
    """Adjusted tract shares for the T rows given (boolean mask), renormalised per tract."""
    cl = K.cls_T[rows]
    f = F.fd.values[jT[rows]] * _lut(cl, K.band_T[rows], F.fb) * _lut(cl, adj_T[rows], F.fa)
    if K.core:
        f = f * _lut(cl, core_T[rows], F.fc)
    for g in K.groups:
        f = f * _lut(cl, K.g_T[g][rows], F.fx, g)
    for g in K.pooled:
        f = f * _lut(np.full(rows.sum(), "all"), K.p_T[g][rows], F.fx, g)
    return tract_norm(base_T[rows] * f, rows)


MODES = {"A": False, "B": True, "C": None}
MODE_LABEL = {"A": "A: destination factor per county", "B": "B: destination factor from public measures",
              "C": "C: segment factors only (no per-destination factor)"}


def cv(K, base_T, p_base, mode, train_S=None, fold_ids=range(8)):
    """Tract shares with each fold of home counties predicted from the other folds (restricted to train_S)."""
    out = np.zeros(len(T))
    train_S = np.ones(NS, bool) if train_S is None else train_S
    for k in fold_ids:
        F = learn(K, p_base, train_S & (fold_S != k), MODES[mode])
        rows = fold_T == k
        out[rows] = apply(K, base_T, rows, F)
    return out


def export(K, p_base, name):
    """Segment corrections (mode C) learned on every Missouri county, for transfer_adjustments.py."""
    import pickle
    F = learn(K, p_base, np.ones(NS, bool), None)
    c = K.cfg
    env = {"DIST_BY_RANK": "1" if c["DIST_BY_RANK"] else None, "DIST_HUB": "1" if c["DIST_HUB"] else None,
           "SPLIT3": "1" if c["SPLIT3"] else None, "C5AS": c["C5AS"], "TRANSFER": "1" if c["TRANSFER"] else None,
           "CORE_NEAR": "1" if c["CORE_NEAR"] else None, "RC_PF": str(c["RC_PF"]), "CORE": "1" if c["CORE"] else None}
    pickle.dump({"fb": dict(F.fb), "fa": dict(F.fa), "fc": dict(F.fc), "fx": dict(F.fx), "groups": list(K.groups), "pooled": list(K.pooled),
                 "label": K.LABEL, "env": env, "cfg": dict(c)}, open(A_ / name, "wb"))
    print("exported segment corrections to", name)


def main():
    cfg = env_cfg()
    print("environment:", {"BASE": BASE, "OUTTAG": os.environ.get("OUTTAG", ""), "EXPORT": os.environ.get("EXPORT", ""), **cfg}, flush=True)
    K = keys(cfg)
    LABEL = K.LABEL
    print("destination order counts:", pd.Series([K.dest_order(j) for j in dests]).value_counts().sort_index().to_dict(),
          "| core:", sorted(_ORD[cfg["TRANSFER"]]["core"]))
    print("hub pairs:", int(K.hub_S.sum()), "home counties whose dominant work county is a regional centre or metro core")
    print(f"common destination set: {int((~COMMON).sum())} pairs outside (public = 0) hold {100 * outside.mean():.2f}% of Advan "
          f"share on average (max {100 * outside.max():.1f}%); every model renormalised over the set")
    results = {}
    for mk in MODES:
        T[MODE_LABEL[mk]] = cv(K, base0, p0, mk)
        results[MODE_LABEL[mk]] = roll(T[MODE_LABEL[mk]].values)
    rows = {"Advan-fitted": adv, "public reference": p0, **{f"public + adjustments, {k}": v for k, v in results.items()}}
    cls_h = pd.Series(dict(zip(S.i, K.cls_S)))
    print("| Model | " + " | ".join(LABEL.values()) + " | all |\n|---|" + "---:|" * (len(LABEL) + 1))
    for lab, p in rows.items():
        e = per_county(S.i.values, a, p)
        cell = lambda d: f"{d.sw.mean():.2f} / {d.lr.mean():.2f}"
        print(f"| {lab} | " + " | ".join(cell(e[cls_h.reindex(e.index) == c]) for c in LABEL) + f" | {cell(e)} |")
    print("(share-weighted error / log-ratio error, county mean, by learning class)")
    kk = {kx: n for n, kx in enumerate(key)}
    print("\n| Pair | Advan | Advan-fitted | public | public + A | public + B | public + C |\n|---|---:|---:|---:|---:|---:|---:|")
    for i, j, n in (("29151", "29051", "Osage -> Cole"), ("29151", "29019", "Osage -> Boone"), ("29007", "29019", "Audrain -> Boone"),
                    ("29007", "29127", "Audrain -> Marion"), ("29019", "29051", "Boone -> Cole"), ("29019", "29189", "Boone -> St. Louis County"),
                    ("29077", "29043", "Greene -> Christian"), ("29077", "29213", "Greene -> Taney")):
        q = kk[(i, j)]
        print(f"| {n} | {100 * a[q]:.1f}% | {100 * adv[q]:.1f}% | {100 * p0[q]:.1f}% | " + " | ".join(f"{100 * v[q]:.1f}%" for v in results.values()) + " |")

    # Audrain's tracts, north to south: Marion and Boone
    lat = dict(zip(_tr.STATEFP + _tr.COUNTYFP + _tr.TRACTCE, _tr.LATITUDE.astype(float)))
    od = pd.read_csv(A_ / "od_tract_mo_2026.csv", dtype={"home_tract": str, "dest_county": str}).groupby(["home_tract", "dest_county"]).all_day.sum()
    print("\nAudrain tracts (out-of-county Missouri shares, %; od_tract_mo_2026.csv, January-July): Marion actual / public / public + B; Boone the same")
    for t, g in T[T.home == "29007"].groupby("tract"):
        adv_t = pd.Series({j: od.get((t, j), 0) for j in g.j}); adv_t = adv_t / adv_t.sum()
        gi = g.set_index("j")
        base = gi.combined_share / gi.combined_share.sum()
        b = gi[MODE_LABEL["B"]]
        print(f"  {t[5:]} (lat {lat[t]:.2f}): Marion {100 * adv_t.get('29127', 0):.1f} / {100 * base.get('29127', 0):.1f} / {100 * b.get('29127', 0):.1f};"
              f"  Boone {100 * adv_t.get('29019', 0):.1f} / {100 * base.get('29019', 0):.1f} / {100 * b.get('29019', 0):.1f}")

    if os.environ.get("EXPORT"):        # segment corrections learned on every Missouri county, for transfer_adjustments.py
        export(K, p0, os.environ["EXPORT"])
    F = learn(K, p0, np.ones(NS, bool), True)
    for g in K.pooled:
        print(g, "factors (all classes):", {int(v): round(F.fx.get((g, "all", v), np.nan), 2) for v in np.unique(K.p_S[g])})
    for g in K.groups:
        print(g, "factors by class:", {LABEL[c]: {int(v): round(F.fx.get((g, c, v), np.nan), 2) for v in np.unique(K.g_S[g])} for c in LABEL})
    if K.core:
        print("Metro core (core / other):", {LABEL[c]: f"{F.fc[c, True]:.2f} / {F.fc[c, False]:.2f}" for c in LABEL})
    ub = np.unique(K.dband_S)
    out = [{"kind": "distance", "class": LABEL[c], "key": (BAND[b % 10] + (" (dominant/secondary)" if b >= 10 else "")), "factor": F.fb.get((c, b), np.nan)} for c in LABEL for b in ub]
    out += [{"kind": "adjacency", "class": LABEL[c], "key": "neighbour" if v else "other", "factor": F.fa[c, v]} for c in LABEL for v in (True, False)]
    out += [{"kind": "destination coefficient", "class": "all", "key": n, "factor": v} for n, v in zip(DX.columns, F.coef)]
    pd.DataFrame(out).to_csv(A_ / "public_adjustments.csv", index=False)
    print("\nDestination factor = exp(" + " + ".join(f"{v:+.3f} {n}" for n, v in zip(DX.columns, F.coef)) + ")")
    print("Distance factors by class:\n" + pd.DataFrame({LABEL[c]: [F.fb.get((c, b), np.nan) for b in ub] for c in LABEL}, index=[BAND[b % 10] + (" hub" if b >= 20 else " dom/sec" if b >= 10 else "") for b in ub]).round(2).to_string())
    print("Adjacency (neighbour / other):", {LABEL[c]: f"{F.fa[c, True]:.2f} / {F.fa[c, False]:.2f}" for c in LABEL})
    T[["tract", "home", "j", "miles", "combined_share"] + list(MODE_LABEL.values())].rename(
        columns={MODE_LABEL["A"]: "adjusted_A", MODE_LABEL["B"]: "adjusted_B", MODE_LABEL["C"]: "adjusted_C"}).to_csv(
        A_ / f"public_adjusted_pairs{os.environ.get('OUTTAG', '')}.csv", index=False)


if __name__ == "__main__":
    main()
