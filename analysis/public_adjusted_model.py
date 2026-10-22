"""The public travel model with Advan-learned adjustments, recomputed from tracts.

Public model: trade area capture, Huff on sales, survey decay (public_travel_tiers.py RETAIL=tac DRAWMODE=cap
REC_CODES=71----; public_model_pairs_tiers_tac.csv), tract -> county shares.
Adjustments, learned from Advan county -> county out-of-county shares (January-September 2026) on the other counties
(8 folds of home counties) and applied to each held-out county's tracts:
  destination   A: one factor per destination county (Advan inflow / public inflow)
                B: the same factor as a function of public destination measures -- log 2025 taxable sales, log 2020
                   population, nonmetro (RUCC 2023 >= 4), log arts and recreation employment (CBP 2022, NAICS 71) --
                   weighted least squares on the log factor; transferable to any county
  distance      one factor per distance band (<15, 15-30, 30-50, 50-80, 80-120, 120+ miles) per class of home county,
                applied at the tract's own distance to the destination
  adjacency     one factor for neighbouring counties per class of home county
  commuting     COMMUTE=commute_out,commute_in: one factor per class per band of LODES 2023 pair commuting -- the
                share of the home county's workers working in the destination (out), of the destination's workers
                living in the home county (in); bands <0.5%, 0.5-2, 2-5, 5-15, 15-30, 30%+
  metro core    CORE=1: one factor per class for the destination that is a central county (OMB 2023) of the home
                county's own metro or micro area, or the nearest central county for a home county in none
Fitted in turn and iterated 5 rounds at county level; applied multiplicatively to tract shares, renormalised per
tract, rolled up to counties by 2020 tract population. Factors learned on all counties are written for reuse:
analysis/public_adjustments.csv (distance and adjacency by class; destination coefficients).
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
from gravity_terms import all_pairs, root  # noqa: E402

A_ = root / "analysis"
S = pd.read_csv(A_ / "compare_shares.csv", dtype={"i": str, "j": str})
pp = all_pairs()
assert (pp.i.values == S.i.values).all() and (pp.j.values == S.j.values).all()
ADJ = set(zip(pp.i[pp.adjacent == 1], pp.j[pp.adjacent == 1]))
a = S.advan.values
BASE = os.environ.get("BASE", "public_model_pairs_tiers_tac.csv")      # the public model the adjustments act on
T = pd.read_csv(A_ / BASE, dtype={"tract": str, "j": str, "home": str})
T = T[(T.j.str[:2] == "29") & (T.home != T.j)].copy()
_tr = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_TR29.txt", dtype=str, encoding="utf-8-sig")
_tp = dict(zip(_tr.STATEFP + _tr.COUNTYFP + _tr.TRACTCE, _tr.POPULATION.astype(float)))
_w = T.combined_share / T.groupby("tract").combined_share.transform("sum") * T.tract.map(_tp)
_g = _w.groupby([T.home, T.j]).sum()
_x = np.array([_g.get(k, 0.0) for k in zip(S.i, S.j)])
p0 = _x / pd.Series(_x).groupby(S.i.values).transform("sum").values
adv = S["Advan-fitted (adopted, counties held out)"].values
unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(A_ / "county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
# SPLIT3=1: commuter counties in the Kansas City or St. Louis metro (OMB 2023) stay class 3; the rest -- rings of
# regional hubs (Springfield, Joplin, Jefferson City) and the two outside any metro -- become class 5
SPLIT3 = os.environ.get("SPLIT3") == "1"
_dl = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str).dropna(subset=["FIPS County Code"])
_bigm = set((_dl["FIPS State Code"] + _dl["FIPS County Code"])[_dl["CBSA Code"].isin(["28140", "41180"])])


def klass(h):
    c = tier.get(unit(h), "class 1")
    if SPLIT3 and c == "class 3" and h not in _bigm:
        return os.environ.get("C5AS", "class 5")     # C5AS="class 1": learn and apply small rural weights for them
    return c


cls = np.array([klass(i) for i in S.i])
LABEL = {"class 1": "small rural", "class 2": "indep. towns", "class 3": "commuter", "class 4": "hubs"}
if SPLIT3:
    LABEL = {"class 1": "small rural", "class 2": "indep. towns", "class 3": "commuter: major metro", "class 5": "commuter: regional hub",
             "class 4": "hubs"}
CUTS = [15, 30, 50, 80, 120]
BAND = ["<15 mi", "15-30", "30-50", "50-80", "80-120", "120+"]
iu = np.array([unit(i) for i in S.i])
folds = np.array_split(np.random.default_rng(7).permutation(sorted(set(iu))), 8)
err = lambda p, m: 100 * np.sum(a[m] * np.abs(p[m] - a[m])) / np.sum(a[m])

# public destination measures
ts = pd.read_csv(root / "census_dl/mo_dor/cnty/DI60IT15_SLS_CNTY_F_2025.csv", dtype=str, encoding="utf-8-sig")
ts = pd.Series(ts.Total.str.replace(r"[$,\s]", "", regex=True).astype(float).values, index="29" + ts.MOID.str.zfill(3).replace("193", "186"))   # DOR keeps Ste. Genevieve's pre-1979 code
co = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
pop_c = pd.Series(co.POPULATION.astype(float).values, index=co.STATEFP + co.COUNTYFP)
rucc = pd.read_csv(root / "census_dl/ref/rucc2023.csv", dtype=str, encoding="latin-1")
rucc = rucc[rucc.Attribute == "RUCC_2023"]
nonmetro = pd.Series({r.FIPS.zfill(5): float(int(r.Value) >= 4) for r in rucc.itertuples()})
cbp = pd.read_csv(root / "census_dl/cbp/cbp22co.txt", dtype=str, usecols=["fipstate", "fipscty", "naics", "emp"])
arts = cbp[cbp.naics == "71----"].assign(f=lambda d: d.fipstate + d.fipscty).set_index("f").emp.astype(float)
dests = sorted(set(S.j))
DX = pd.DataFrame({"const": 1.0, "log_sales": np.log(ts.reindex(dests)), "log_pop": np.log(pop_c.reindex(dests)),
                   "nonmetro": nonmetro.reindex(dests).fillna(0), "log_arts": np.log1p(arts.reindex(dests).fillna(0))},
                  index=dests)

# county-level grouping keys for the frame
dband = np.digitize(S.dist.values, CUTS)
adj = np.array([(i, j) in ADJ for i, j in zip(S.i, S.j)])
# metro core: the destination is a central county (OMB 2023) of the home county's own metro or micro area, or, for a
# home county in none, its nearest central county -- one factor per class (CORE=1)
import os
CORE = os.environ.get("CORE") == "1"
dl = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str).dropna(subset=["FIPS County Code"])
dl = dl[dl["FIPS State Code"] == "29"]
dl["f"] = dl["FIPS State Code"] + dl["FIPS County Code"]
cbsa = dict(zip(dl.f, dl["CBSA Code"]))
central = set(dl.f[dl["Central/Outlying County"] == "Central"])
dmiles = dict(zip(zip(S.i, S.j), S.dist))
nearest = {i: min((j for j in central if j != i), key=lambda j: dmiles.get((i, j), 1e9)) for i in set(S.i)}
core_of = lambda i, j: (j in central and cbsa.get(i) is not None and cbsa.get(i) == cbsa.get(j)) or (cbsa.get(i) is None and nearest[i] == j)
core = np.array([core_of(i, j) for i, j in zip(S.i, S.j)])
# pair commuting (LODES 2023, Missouri main OD): share of the home county's workers who work in the destination
# (out), and of the destination's workers who live in the home county (in); one factor per class per band (COMMUTE=1)
COMMUTE = os.environ.get("COMMUTE", "")
import csv, gzip
from collections import defaultdict
_flow, _work = defaultdict(float), defaultdict(float)
with gzip.open(root / "free/od_2023.csv.gz", "rt") as fh:
    for r in csv.DictReader(fh):
        h, w_, n = r["h_geocode"][:5], r["w_geocode"][:5], float(r["S000"])
        _work[h] += n; _flow[h, w_] += n
CB = [0.005, 0.02, 0.05, 0.15, 0.30]
cband = lambda i, j: int(np.digitize(_flow.get((i, j), 0) / max(_work.get(i, 1), 1), CB))
cinband = lambda i, j: int(np.digitize(_flow.get((j, i), 0) / max(_work.get(j, 1), 1), CB))
cout = np.array([cband(i, j) for i, j in zip(S.i, S.j)])
# the destination's rank among the home county's out-of-county LODES work destinations (Missouri): 1 dominant,
# 2 secondary, 3 = ranks 3-5, 4 = the rest (commute_rank)
_rank = {}
for _i in set(S.i):
    _r = sorted(((v, w_) for (h, w_), v in _flow.items() if h == _i and w_ != _i and w_[:2] == "29"), reverse=True)
    for n, (_, w_) in enumerate(_r):
        _rank[_i, w_] = 1 if n == 0 else 2 if n == 1 else 3 if n < 5 else 4
crank_of = lambda i, j: _rank.get((i, j), 4)
crank = np.array([crank_of(i, j) for i, j in zip(S.i, S.j)])
cin = np.array([cinband(i, j) for i, j in zip(S.i, S.j)])


fx = {}
dcls = np.array([int(klass(j)[-1]) for j in S.j])                  # destination's class, 1-4
# destination order (central place hierarchy), public: 2025 taxable sales and pull factor (DOR), CBP 2022
# marinas (713930) + RV parks and recreational camps (7212) establishments per resident (resort)
_pf = (ts / pop_c.reindex(ts.index)) / (ts.sum() / pop_c.reindex(ts.index).sum())
_cbe = pd.read_csv(root / "census_dl/cbp/cbp22co.txt", dtype=str, usecols=["fipstate", "fipscty", "naics", "est"])
_acc = _cbe[_cbe.naics.isin(["713930", "7212//"])].assign(f=lambda d: d.fipstate + d.fipscty, e=lambda d: d.est.astype(float)).groupby("f").e.sum()
_resort = (_acc.reindex(ts.index).fillna(0) / pop_c.reindex(ts.index) * 1e4)   # marinas + RV parks and camps per 10,000
_rcut = _resort.quantile(0.9)
_score = ts.sort_values(ascending=False)
_core = set(_score.index[:3])
_big_metro = {f for f, c in cbsa.items() if c in ("28140", "41180")}   # Kansas City, St. Louis metro areas (OMB 2023)
# TRANSFER=1: the same orders in terms that mean the same in any state --
#   metro core = central county of a metro area of 1,000,000+ (OMB 2023, Census 2024 CBSA population); rest of such a
#   metro = its outlying counties; regional centre = pull factor >= 1 and trade-area customers (sales / the state's
#   per-capita sales) >= 60,000; resort = marinas + RV parks and camps per resident in the top tenth of all U.S. counties
TRANSFER = os.environ.get("TRANSFER") == "1"
if TRANSFER:
    _cpop = pd.read_csv(root / "census_dl/ref/cbsa-est2024-alldata.csv", encoding="latin-1", dtype=str)
    _cpop = _cpop[_cpop.LSAD.str.endswith("Statistical Area")].set_index("CBSA").POPESTIMATE2024.astype(float)
    _big = {f for f, c in cbsa.items() if _cpop.get(c, 0) >= 1e6}
    _central = set(dl.f[dl["Central/Outlying County"] == "Central"])
    _core = _big & _central
    _big_metro = _big - _core
    _cust = ts / (ts.sum() / pop_c.reindex(ts.index).sum())
    _us = _cbe[_cbe.naics.isin(["713930", "7212//"])].assign(f=lambda d: d.fipstate + d.fipscty, e=lambda d: d.est.astype(float)).groupby("f").e.sum()
    _usp = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
    _usp = pd.Series(_usp.POPULATION.astype(float).values, index=_usp.STATEFP + _usp.COUNTYFP)
    _rcut = (_us.reindex(_usp.index).fillna(0) / _usp * 1e4).quantile(0.9)
def dest_order(j):
    if j in _core: return 1                                         # metro core
    if j in _big_metro: return 6                                    # rest of the large metros
    if _resort.get(j, 0) >= _rcut: return 5                         # resort / recreation
    big_enough = _cust.get(j, 0) >= 60000 if TRANSFER else ts.get(j, 0) > 1e9
    if _pf.get(j, 0) >= float(os.environ.get("RC_PF", "1.0")) and big_enough: return 2   # regional centre
    if _pf.get(j, 0) >= 1.0: return 3                               # sub-regional town
    return 4                                                        # local
dord = np.array([dest_order(j) for j in S.j])
# CORE_NEAR=1: a metro core (order 1) or the rest of a big metro (order 6) within 50 miles of home is its own order
# (7, 8): the cores pull their ring and are overstated for distant homes
NEAR = os.environ.get("CORE_NEAR") == "1"
near_key = lambda o, d: (7 if o == 1 else 8 if o == 6 else o) if (NEAR and d < 50 and o in (1, 6)) else o
dord = np.array([near_key(o, d) for o, d in zip(dord, S.dist.values)])
print("destination order counts:", pd.Series([dest_order(j) for j in dests]).value_counts().sort_index().to_dict(),
      "| core:", sorted(_core), "| resort:", sorted(_resort.index[_resort >= _rcut]))
# hub relation: the destination is the home county's dominant LODES work county AND a regional centre (order 2) or
# metro core (order 1) -- the tie a hub's ring has to its hub; POOLED=hub learns its factor from every county in that
# relation, any class; DIST_HUB=1 gives those pairs their own distance bands
hub = (crank == 1) & np.isin(dord, [1, 2, 7])
if os.environ.get("DIST_BY_RANK") == "1":      # distance factors learned apart for the dominant/secondary county
    dband = dband + 10 * ((crank <= 2) & ~hub) + (20 * hub if os.environ.get("DIST_HUB") == "1" else 10 * hub)
POOLED = {g: {"hub": hub.astype(int), "hub_band": hub * (1 + np.digitize(S.dist.values, [15, 30, 50]))}[g]
          for g in os.environ.get("POOLED", "").split(",") if g}
print("hub pairs:", int(hub.sum()), "home counties whose dominant work county is a regional centre or metro core")
dcls_band = dcls * 10 + dband
EXTRA_GROUPS = {g: {"commute_out": cout, "commute_in": cin, "dest_class": dcls, "dest_class_band": dcls_band, "dest_order": dord,
                    "dest_order_band": dord * 10 + dband, "commute_rank": crank,
                    "rank_order": crank * 10 + dord}[g]
                for g in COMMUTE.split(",") if g}


def learn(train, parametric):
    """Destination, distance and adjacency factors from the training home counties."""
    p = p0.copy()
    fd = pd.Series(1.0, index=dests); fb = {}; fa = {}; fc = {}; fx.clear()
    for _ in range(5):
        r = pd.Series(a[train]).groupby(S.j.values[train]).sum() / pd.Series(p[train]).groupby(S.j.values[train]).sum()
        if parametric is None:
            step = pd.Series(1.0, index=dests)
        elif parametric:
            w = pd.Series(a[train]).groupby(S.j.values[train]).sum().reindex(dests).fillna(0) + 1e-4
            y = np.log(r.reindex(dests).clip(0.05, 20).fillna(1.0))
            Xm = DX.values * np.sqrt(w.values)[:, None]
            beta = np.linalg.lstsq(Xm, y.values * np.sqrt(w.values), rcond=None)[0]
            step = pd.Series(np.exp(DX.values @ beta), index=dests)
        else:
            step = r.reindex(dests).clip(0.05, 20).fillna(1.0)
        fd *= step
        p = p * S.j.map(step).values; p = p / pd.Series(p).groupby(S.i.values).transform("sum").values
        for c in LABEL:
            for b in np.unique(dband):
                m = train & (cls == c) & (dband == b)
                f = a[m].sum() / max(p[m].sum(), 1e-12) if m.any() else 1.0
                fb[c, b] = fb.get((c, b), 1.0) * f
                p[(cls == c) & (dband == b)] *= f
            p = p / pd.Series(p).groupby(S.i.values).transform("sum").values
            for v in (True, False):
                m = train & (cls == c) & (adj == v)
                f = a[m].sum() / max(p[m].sum(), 1e-12) if m.any() else 1.0
                fa[c, v] = fa.get((c, v), 1.0) * f
                p[(cls == c) & (adj == v)] *= f
            p = p / pd.Series(p).groupby(S.i.values).transform("sum").values
            for gname, garr in EXTRA_GROUPS.items():
                for v in np.unique(garr):
                    m = train & (cls == c) & (garr == v)
                    f = a[m].sum() / max(p[m].sum(), 1e-12) if m.any() else 1.0
                    fx[gname, c, v] = fx.get((gname, c, v), 1.0) * f
                    p[(cls == c) & (garr == v)] *= f
                p = p / pd.Series(p).groupby(S.i.values).transform("sum").values
            pass
        for gname, garr in POOLED.items():                          # learned across all classes
            for v in np.unique(garr):
                m = train & (garr == v)
                f = a[m].sum() / max(p[m].sum(), 1e-12) if m.any() else 1.0
                fx[gname, "all", v] = fx.get((gname, "all", v), 1.0) * f
                p[garr == v] *= f
            p = p / pd.Series(p).groupby(S.i.values).transform("sum").values
        for c in LABEL:
            if CORE:
                for v in (True, False):
                    m = train & (cls == c) & (core == v)
                    f = a[m].sum() / max(p[m].sum(), 1e-12) if m.any() else 1.0
                    fc[c, v] = fc.get((c, v), 1.0) * f
                    p[(cls == c) & (core == v)] *= f
                p = p / pd.Series(p).groupby(S.i.values).transform("sum").values
    coef = None
    if parametric:   # (None and False skip this)
        y = np.log(fd)
        w = pd.Series(a[train]).groupby(S.j.values[train]).sum().reindex(dests).fillna(0) + 1e-4
        coef = np.linalg.lstsq(DX.values * np.sqrt(w.values)[:, None], y.values * np.sqrt(w.values), rcond=None)[0]
        fd = pd.Series(np.exp(DX.values @ coef), index=dests)
    return fd, fb, fa, fc, coef


tr = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_TR29.txt", dtype=str, encoding="utf-8-sig")
tpop = dict(zip(tr.STATEFP + tr.COUNTYFP + tr.TRACTCE, tr.POPULATION.astype(float)))
T["cls"] = T.home.map(klass)
T["band"] = np.digitize(T.miles.values, CUTS)
T["adj"] = [(h, j) in ADJ for h, j in zip(T.home, T.j)]
T["core"] = [core_of(h, j) for h, j in zip(T.home, T.j)]
T["commute_out"] = [cband(h, j) for h, j in zip(T.home, T.j)]
T["commute_in"] = [cinband(h, j) for h, j in zip(T.home, T.j)]
T["dest_class"] = [int(klass(j)[-1]) for j in T.j]
T["dest_class_band"] = T.dest_class * 10 + T.band
_cd = dict(zip(zip(S.i, S.j), S.dist))
T["dest_order"] = [near_key(dest_order(j), _cd.get((h, j), 999)) for h, j in zip(T.home, T.j)]
T["commute_rank"] = [crank_of(h, j) for h, j in zip(T.home, T.j)]
T["rank_order"] = T.commute_rank * 10 + T.dest_order
T["hub"] = ((T.commute_rank == 1) & T.dest_order.isin([1, 2, 7])).astype(int)
T["hub_band"] = T.hub * (1 + np.digitize(T.miles.values, [15, 30, 50]))
if os.environ.get("DIST_BY_RANK") == "1":
    T["band"] = np.digitize(T.miles.values, CUTS) + 10 * ((T.commute_rank <= 2) & (T.hub == 0)) + (20 * T.hub if os.environ.get("DIST_HUB") == "1" else 10 * T.hub)
T["dest_order_band"] = T.dest_order * 10 + T.band
T["unit"] = T.home.map(unit)
key = list(zip(S.i, S.j))


def apply(Tf, fd, fb, fa, fc):
    f = Tf.j.map(fd).fillna(1.0).values * np.array([fb[c, b] for c, b in zip(Tf.cls, Tf.band)]) \
        * np.array([fa[c, v] for c, v in zip(Tf.cls, Tf.adj)])
    if CORE:
        f = f * np.array([fc[c, v] for c, v in zip(Tf.cls, Tf.core)])
    for gname in EXTRA_GROUPS:
        f = f * np.array([fx.get((gname, c, v), 1.0) for c, v in zip(Tf.cls, Tf[gname])])
    for gname in POOLED:
        f = f * np.array([fx.get((gname, "all", v), 1.0) for v in Tf[gname]])
    s = Tf.combined_share.values * f
    return s / pd.Series(s, index=Tf.index).groupby(Tf.tract).transform("sum").values


def roll(Tf, col):
    w = Tf[col] * Tf.tract.map(tpop)
    g = w.groupby([Tf.home, Tf.j]).sum()
    x = np.array([g.get(k, 0.0) for k in key])
    s = pd.Series(x).groupby(S.i.values).transform("sum").values
    return np.where(s > 0, x / np.where(s > 0, s, 1), 0)


results = {}
MODES = {"A: destination factor per county": False, "B: destination factor from public measures": True,
         "C: segment factors only (no per-destination factor)": None}
for lab, par in MODES.items():
    T[lab] = 0.0
    for f in folds:
        train = ~np.isin(iu, f)
        fd, fb, fa, fc, _ = learn(train, par)
        m = T.unit.isin(f).values
        T.loc[m, lab] = apply(T[m], fd, fb, fa, fc)
    results[lab] = roll(T, lab)

rows = {"Advan-fitted": adv, "public reference": p0, **{f"public + adjustments, {k}": v for k, v in results.items()}}
allm = np.ones(len(a), bool)
gap = err(p0, allm) - err(adv, allm)
print("| Model | " + " | ".join(LABEL.values()) + " | all | gap closed |\n|---|" + "---:|" * 6)
for lab, p in rows.items():
    e = err(p, allm)
    print(f"| {lab} | " + " | ".join(f"{err(p, cls == c):.2f}" for c in LABEL) + f" | {e:.2f} | {100 * (err(p0, allm) - e) / gap:.0f}% |")
k = {kk: n for n, kk in enumerate(key)}
print("\n| Pair | Advan | Advan-fitted | public | public + A | public + B | public + C |\n|---|---:|---:|---:|---:|---:|---:|")
for i, j, n in (("29151", "29051", "Osage -> Cole"), ("29151", "29019", "Osage -> Boone"), ("29007", "29019", "Audrain -> Boone"),
                ("29007", "29127", "Audrain -> Marion"), ("29019", "29051", "Boone -> Cole"), ("29019", "29189", "Boone -> St. Louis County"),
                ("29077", "29043", "Greene -> Christian"), ("29077", "29213", "Greene -> Taney")):
    q = k[(i, j)]
    print(f"| {n} | {100 * a[q]:.1f}% | {100 * adv[q]:.1f}% | {100 * p0[q]:.1f}% | " + " | ".join(f"{100 * v[q]:.1f}%" for v in results.values()) + " |")

# Audrain's tracts, north to south: Marion and Boone
lat = dict(zip(tr.STATEFP + tr.COUNTYFP + tr.TRACTCE, tr.LATITUDE.astype(float)))
od = pd.read_csv(A_ / "od_tract_mo_2026.csv", dtype={"home_tract": str, "dest_county": str}).groupby(["home_tract", "dest_county"]).all_day.sum()
print("\nAudrain tracts (out-of-county Missouri shares, %): Marion actual / public / public + B; Boone the same")
for t, g in T[T.home == "29007"].groupby("tract"):
    adv_t = pd.Series({j: od.get((t, j), 0) for j in g.j}); adv_t = adv_t / adv_t.sum()
    gi = g.set_index("j")
    base = gi.combined_share / gi.combined_share.sum()
    b = gi["B: destination factor from public measures"]
    print(f"  {t[5:]} (lat {lat[t]:.2f}): Marion {100 * adv_t.get('29127', 0):.1f} / {100 * base.get('29127', 0):.1f} / {100 * b.get('29127', 0):.1f};"
          f"  Boone {100 * adv_t.get('29019', 0):.1f} / {100 * base.get('29019', 0):.1f} / {100 * b.get('29019', 0):.1f}")

if os.environ.get("EXPORT"):        # segment corrections learned on every Missouri county, for transfer_adjustments.py
    import pickle
    _fd, _fb, _fa, _fc, _ = learn(np.ones(len(a), bool), None)
    pickle.dump({"fb": dict(_fb), "fa": dict(_fa), "fc": dict(_fc), "fx": dict(fx), "groups": list(EXTRA_GROUPS), "pooled": list(POOLED),
                 "label": LABEL, "env": {k: os.environ.get(k) for k in ("DIST_BY_RANK", "DIST_HUB", "SPLIT3", "C5AS", "TRANSFER", "CORE_NEAR", "RC_PF")}},
                open(A_ / os.environ["EXPORT"], "wb"))
    print("exported segment corrections to", os.environ["EXPORT"])
fd, fb, fa, fc, coef = learn(np.ones(len(a), bool), True)
for gname in POOLED:
    print(gname, "factors (all classes):", {v: round(fx.get((gname, "all", v), np.nan), 2) for v in np.unique(POOLED[gname])})
for gname in EXTRA_GROUPS:
    print(gname, "factors by class, band 0..5:", {LABEL[c]: [round(fx.get((gname, c, v), np.nan), 2) for v in range(6)] for c in LABEL})
if CORE:
    print("Metro core (core / other):", {LABEL[c]: f"{fc[c, True]:.2f} / {fc[c, False]:.2f}" for c in LABEL})
out = [{"kind": "distance", "class": LABEL[c], "key": (BAND[b % 10] + (" (dominant/secondary)" if b >= 10 else "")), "factor": fb.get((c, b), np.nan)} for c in LABEL for b in np.unique(dband)]
out += [{"kind": "adjacency", "class": LABEL[c], "key": "neighbour" if v else "other", "factor": fa[c, v]} for c in LABEL for v in (True, False)]
out += [{"kind": "destination coefficient", "class": "all", "key": n, "factor": v} for n, v in zip(DX.columns, coef)]
pd.DataFrame(out).to_csv(A_ / "public_adjustments.csv", index=False)
print("\nDestination factor = exp(" + " + ".join(f"{v:+.3f} {n}" for n, v in zip(DX.columns, coef)) + ")")
print("Distance factors by class:\n" + pd.DataFrame({LABEL[c]: [fb.get((c, b), np.nan) for b in np.unique(dband)] for c in LABEL}, index=[BAND[b % 10] + (" hub" if b >= 20 else " dom/sec" if b >= 10 else "") for b in np.unique(dband)]).round(2).to_string())
print("Adjacency (neighbour / other):", {LABEL[c]: f"{fa[c, True]:.2f} / {fa[c, False]:.2f}" for c in LABEL})
T[["tract", "home", "j", "miles", "combined_share"] + list(MODES)].rename(
    columns={"A: destination factor per county": "adjusted_A", "B: destination factor from public measures": "adjusted_B",
             "C: segment factors only (no per-destination factor)": "adjusted_C"}).to_csv(A_ / f"public_adjusted_pairs{os.environ.get('OUTTAG', '')}.csv", index=False)
