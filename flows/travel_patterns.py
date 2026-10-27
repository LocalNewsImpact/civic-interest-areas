"""Travel patterns: the recurring ways residents of Audrain, Boone and Osage travel, January-July 2026.

Advan counts residents of a home block group seen in each destination block group; it does not link one person's trips,
so cohorts of people are not observed. Instead each home block group's travel is decomposed into a few recurring
patterns (non-negative matrix factorization): travel(h) ~ sum_k weight(h, k) x pattern(k). A pattern is a set of places
travelled to together; a block group's weights give how much of its travel follows each one.
Destinations (all of Missouri) are PLACES, not tracts (tracts split a city into its neighbourhoods, and the patterns then describe travel
across one city): each town of the Columbia-Jefferson City TV market (a block group belongs to the 2020 place holding its
centre), each rural block group (outside towns), and each other Missouri county. Reach is residents seen in the
unit's busiest block group / residents seen at home, mean over the months the block group is observed (50+ residents
seen at home; a missing home-month is missing, not zero, and is masked in every fit). A block group's own town is left
out (masked): patterns describe travel beyond home. Residents: ACS 2020-2024 population of each block group (the
calibrated denominator of crossover, analysis/crossover_bg_month_mo_2026.csv). The masked NMF updates subtract the
masked cells from the full products instead of multiplying by the mask: identical results, about 6x faster.
The number of patterns K (authors, 2026-10-24): the largest K (grid 1-12, extended while its last K passes) at which every
pattern holds 10%+ and 1,000+ of some study town's estimated residents and 10%+ of that town's travel (residents x
reconstructed reach), and has matched cosine 0.9+ across 10 random starts (median) and between fits to odd and to even
months. Per town, not per market: the area rule is per town, and a market's share depends on which counties form it.
The kept fit is the lowest-loss of the 10 starts. Held-out month error (all 105 4 / 2 / 1 month partitions) is printed
as a persistence diagnostic.
Writes <region out>/patterns.json and patterns_halves.json (the odd- and even-month fits).
"""
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

import json as _json
import sys as _sys
here = Path(__file__).parent
# ONE TV MARKET PER RUN (flows/regions.json); each market is fitted on its own residents only
REGION = _sys.argv[1] if len(_sys.argv) > 1 and not _sys.argv[1].startswith("-") else "columbia"
CFG = _json.load(open(here / "regions.json"))[REGION]
R = here.parent / CFG["out"]
exec(open(here / "build_cousub_shares.py").read().split("\ndef read_shp(")[0].split("from shapely")[0])
DMA = ["29007", "29019", "29027", "29041", "29051", "29053", "29089", "29125", "29131", "29135", "29139", "29141",
       "29151", "29175"]
MONTHS = [f"2026-0{m}" for m in range(1, 8)]
f = pd.read_csv(here.parent / CFG["flows"],
                dtype={"dest_cbg": str, "home_cbg": str, "dest_county": str, "home_county": str},
                usecols=["month", "dest_cbg", "dest_county", "home_cbg", "device_home_areas"])
f = f[f.month.isin(MONTHS)]
if "home_counties" in CFG:
    f = f[f.home_cbg.str[:5].isin(CFG["home_counties"])]
own = f[f.dest_cbg == f.home_cbg].set_index(["month", "home_cbg"]).device_home_areas
f = f[f.dest_cbg != f.home_cbg]
# ROAD STOPS COUNT HALF (authors, 2026-10-26; flows/build_stop_weights.py): residents seen in a destination block group are
# weighted by its road-stop share for their home county; STOPS=0 turns it off. Columbia region only (the weights cover
# its three study counties)
_sw = here / "reach/stop_weights.csv"
if os.environ.get("STOPS", "1") != "0" and REGION == "columbia" and _sw.exists():
    _w = pd.read_csv(_sw, dtype={"home_county": str, "dest_cbg": str}).set_index(["home_county", "dest_cbg"]).factor
    _raw = f.device_home_areas.sum()
    f["device_home_areas"] = f.device_home_areas * pd.Series(list(zip(f.home_cbg.str[:5], f.dest_cbg))).map(_w).fillna(1.0).values
    print(f"road stops weighted: residents seen outside home x {f.device_home_areas.sum() / _raw:.3f}", flush=True)
__file__ = str(here / "build_cousub_shares.py")
exec(open(here / "build_cousub_shares.py").read().split("\ndef cw(")[0])
from shapely.strtree import STRtree
bgs = read_shp(str(DL / "bg/cb_2020_29_bg_500k"), lambda r: r["GEOID"])
# DESTINATIONS ARE ALL OF MISSOURI, as towns and rural block groups: no TV-market boundary (a border
# town's travel crosses one). The fit still uses only this market's home counties.
DMA = sorted({b[:5] for b in bgs})
places = read_shp(str(DL / "place/cb_2020_29_place_500k"), lambda r: r["GEOID"])
pids = list(places)
ptree = STRtree([places[q][1] for q in pids])
place_name = {q: places[q][0]["NAME"] for q in pids}
bg_place = {}
for b, (_, geom) in bgs.items():
    if b[:5] in DMA:
        c = geom.representative_point()
        bg_place[b] = next((pids[i] for i in ptree.query(c) if places[pids[i]][1].contains(c)), "")
# outside towns, each rural BLOCK GROUP is its own unit, so a pattern has contours within a county
f["unit"] = np.where(f.dest_county.isin(DMA), f.dest_cbg.map(lambda b: bg_place.get(b) or "rural:" + b), f.dest_county)
p = f.groupby(["month", "home_cbg", "unit"]).device_home_areas.max().rename("people").reset_index()
p["own"] = p.set_index(["month", "home_cbg"]).index.map(own)
p = p[p.own >= 50]
p["reach"] = (p.people / p.own).clip(upper=1)
homes = sorted(p.home_cbg.unique())
units = sorted(p.unit.unique())
cube = np.full((len(MONTHS), len(homes), len(units)), np.nan)
mi, hi, ui = {m: i for i, m in enumerate(MONTHS)}, {h: i for i, h in enumerate(homes)}, {u: i for i, u in enumerate(units)}
# MISSING HOME-MONTHS ARE MISSING, NOT ZERO (2026-10-24): a block group with fewer than 50 residents seen at
# home in a month has no row that month; its travel is unknown, not nil. Observed home-months start at 0 (no visit to a
# destination is a true zero) and take their reach; missing ones stay NaN and are left out of every mean and masked in
# every fit and score.
obs = {(m, h) for m, h in p[["month", "home_cbg"]].drop_duplicates().itertuples(index=False)}
for m, h in obs:
    cube[mi[m], hi[h], :] = 0.0
cube[p.month.map(mi), p.home_cbg.map(hi), p.unit.map(ui)] = p.reach
print(f"home-months observed {len(obs):,} of {len(MONTHS) * len(homes):,}", flush=True)
# destinations this market's residents actually reach: seen from 2+ home block groups, at 0.5%+ of residents
mean_ = np.nanmean(cube, 0)
keep = ((mean_ > 0).sum(0) >= 2) & (mean_.max(0) >= 0.005)
units = [u for u, k_ in zip(units, keep) if k_]
cube = cube[:, :, keep]
ui = {u: i for i, u in enumerate(units)}
print(f"{len(units):,} destinations kept of {len(keep):,}", flush=True)
hm = pd.read_csv(R / "homes.csv", dtype={"home_cbg": str, "place": str}).set_index("home_cbg")
MASK = np.ones((len(homes), len(units)))
for h in homes:
    q = hm.place.get(h)
    if isinstance(q, str) and q in ui:
        MASK[hi[h], ui[q]] = 0


def mean_mask(idx):
    """mean reach over the months idx (missing home-months left out) and the fit mask: the own-town mask, and every
    cell of a block group with no observed month among idx"""
    sub = cube[idx]
    seen = ~np.isnan(sub[:, :, 0])                                    # months x homes
    Xm = np.where(seen.any(0)[:, None], np.nan_to_num(np.nansum(sub, 0)) / np.maximum(seen.sum(0), 1)[:, None], 0.0)
    return Xm, MASK * seen.any(0)[:, None]


def nmf(X, k, iters=600, seed=0, H=None, M=None):
    """X ~ W @ H, non-negative, Frobenius loss on the cells M marks (M binary), multiplicative updates. H fixed when given.
    The masked products are computed as the full product less the masked cells (the own-town cell of each block group,
    and the rows of block groups with no observed month): (M * WH) H' = W (H H') - the masked cells' part, and
    W' (M * WH) = (W' W) H - the same -- the same updates as multiplying by M (identical to 1e-14), about 6 times faster
    (2026-10-24)."""
    M = MASK if M is None else M
    rng = np.random.default_rng(seed)
    fixed = H is not None
    W = rng.random((X.shape[0], k)) + 0.1
    if not fixed:
        H = rng.random((k, X.shape[1])) + 0.1
    MX = M * X
    rows, cols = np.nonzero(M == 0)

    def masked_part(W, H):
        v = (W[rows] * H[:, cols].T).sum(1)[:, None]          # W H at the masked cells
        cw, ch = np.zeros_like(W), np.zeros_like(H.T)
        np.add.at(cw, rows, v * H[:, cols].T)
        np.add.at(ch, cols, v * W[rows])
        return cw, ch.T
    for _ in range(iters):
        cw, _ = masked_part(W, H)
        W *= (MX @ H.T) / (np.maximum(W @ (H @ H.T) - cw, 0) + 1e-9)
        if not fixed:
            _, ch = masked_part(W, H)
            H *= (W.T @ MX) / (np.maximum((W.T @ W) @ H - ch, 0) + 1e-9)
    return W, H


# RESIDENTS (2026-10-24; replaces devices at home / the county-month factor): each block group's residents
# through the calibrated per-block-group denominator of crossover (analysis/crossover_bg_month_mo_2026.csv,
# build_unique_od.py): people = devices x ACS population / D_h, so a block group's residents are its ACS 2020-2024
# population (B01003), mean over January-July. Mixed membership: a block group's residents are split across the
# patterns in proportion to the travel each carries.
_cb = pd.read_csv(here.parent / "analysis/crossover_bg_month_mo_2026.csv", dtype={"home_bg": str}, usecols=["month", "home_bg", "acs_population"])
_cb = _cb[_cb.month.isin(MONTHS) & _cb.home_bg.isin(hi)]
people = _cb.groupby("home_bg").acs_population.mean().reindex(homes).values
print(f"residents: ACS population for {np.isfinite(people).sum()} of {len(homes)} home block groups, {np.nansum(people):,.0f} in all", flush=True)
ppl0 = np.nan_to_num(people)
import hashlib
import itertools
import os
from scipy.optimize import linear_sum_assignment

# THE K RULE (authors, 2026-10-24: "the patterns need to have a minimum percentage of the population and overall volume -
# AND replicability"; the same day: population and volume per TOWN). K = the LARGEST K at which EVERY
# pattern passes both:
#   (a+b) a town  at least one of the market's towns (the towns the maps are drawn for, flows/regions.json) for which
#                 the pattern holds 10%+ AND 1,000+ of the town's residents AND 10%+ of the town's travel -- the same
#                 town for all three. Residents: ACS population (the calibrated denominator), split by each block
#                 group's membership (as the areas use). Travel: residents x reconstructed reach, sum over the town's
#                 block groups h and destinations u -- the town's own units masked, as the maps mask them
#                 (own_units_of) -- of people(h) W[h,k] H[k,u].
#                 Why per town: the area rule already requires 10% and 1,000 of a town's residents; a share of the
#                 MARKET depends on which home counties form the market (the same number of residents passes in a small
#                 market and fails in a large one). A 5% level is not considered.
#   (c) stability (i) across 10 random starts, the pattern's median matched cosine to the kept solution >= 0.9;
#                 (ii) MONTH-SPLIT STABILITY: refitted on odd months (Jan, Mar, May, Jul) and on even months (Feb, Apr,
#                 Jun) separately (W and H both; best of 5 starts each, the two halves on DISJOINT seeds: odd 0-4, even
#                 100-104); each half's patterns matched to the KEPT patterns (Hungarian, cosine), and
#                 for every kept pattern the cosine between its odd and its even match >= 0.9 (2026-10-24: matched in
#                 the kept order -- before, the odd fit's order was reported as if it were the kept one)
# NOTE: K is selected on this same odd/even split, so the areas' month-split stability (confidence_layer.py,
# area_ensemble.py) is not an independent test of K. Grid 1-12, extended while its last K passes. Replaces the held-out-month one-SE rule (earlier the same day), which on
# paired splits kept adding patterns to the top of the grid; the held-out score is kept as a persistence diagnostic.
KMAX0, KCAP = int(os.environ.get("KMAX", 12)), 20
STARTS, HALF_STARTS, ITERS = 10, 5, 2000
TOWN_MIN, TOWN_ABS, COS_MIN = 0.10, 1000, 0.90
unit_ = lambda A_: A_ / np.maximum(np.linalg.norm(A_, axis=1, keepdims=True), 1e-12)


def matched(Ha, Hb):
    """cosine of each pattern of Ha to its Hungarian match in Hb (in Ha's order)"""
    C_ = unit_(Ha) @ unit_(Hb).T
    r_, c_ = linear_sum_assignment(-C_)
    out_ = np.zeros(len(Ha))
    out_[r_] = C_[r_, c_]
    return out_


def kept_order(Hk, Hh):
    """for each kept pattern, the index of its Hungarian match among the half fit's patterns"""
    C_ = unit_(Hk) @ unit_(Hh).T
    r_, c_ = linear_sum_assignment(-C_)
    o_ = np.zeros(len(Hk), int)
    o_[r_] = c_
    return o_


def best_of(Xm, k, n, seed0=0, M=None):
    M = MASK if M is None else M
    fs = []
    for sd in range(seed0, seed0 + n):
        W_, H_ = nmf(Xm, k, iters=ITERS, seed=sd, M=M)
        fs.append(((M * (W_ @ H_ - Xm) ** 2).sum(), sd, W_, H_))
    return sorted(fs, key=lambda z: z[0])


X, MX_ = mean_mask(list(range(len(MONTHS))))
odd = [i for i, m in enumerate(MONTHS) if int(m[-2:]) % 2 == 1]
even = [i for i, m in enumerate(MONTHS) if int(m[-2:]) % 2 == 0]
(Xo, Mo), (Xe, Me) = mean_mask(odd), mean_mask(even)
TOWN_IDX = {t_: [hi[h] for h in hm[(hm.town == t_) | (hm.place == CFG["towns"][t_][1])].index if h in hi] for t_ in CFG["towns"]}
# the town's own units (market_patterns.own_units_of): its block groups' towns and rural block groups and the town itself
_bgu = lambda b: bg_place.get(b) or "rural:" + b
OWN_MASK = {t_: np.array([u not in ({_bgu(homes[i]) for i in ix} | {"rural:" + homes[i] for i in ix} | {CFG["towns"][t_][1]})
                          for u in units], float) for t_, ix in TOWN_IDX.items()}
crit, fitk = {}, {}


def town_tests(W, H):
    """per town and pattern: share and count of the town's residents, share of the town's travel"""
    mass = W * H.sum(1)[None, :]
    member_ = mass / np.maximum(mass.sum(1, keepdims=True), 1e-12)
    out_ = {}
    for t_, ix in TOWN_IDX.items():
        r_ = (ppl0[ix, None] * member_[ix]).sum(0)
        Mt = MASK[ix] * OWN_MASK[t_][None, :]
        v_ = np.array([(ppl0[ix, None] * Mt * (W[ix][:, [j]] @ H[[j]])).sum() for j in range(W.shape[1])])
        out_[t_] = {"res": r_, "res_share": r_ / max(r_.sum(), 1e-9), "travel_share": v_ / max(v_.sum(), 1e-9)}
    return out_


def carrier(c_, j, tmin=TOWN_MIN):
    """the town carrying pattern j (all three tests), the one where it holds most of the residents; else None"""
    ok = [(c_["towns"][t_]["res_share"][j], t_) for t_ in c_["towns"]
          if c_["towns"][t_]["res_share"][j] >= tmin and c_["towns"][t_]["res"][j] >= TOWN_ABS
          and c_["towns"][t_]["travel_share"][j] >= tmin]
    return max(ok)[1] if ok else None


k = 1
while True:
    fs = best_of(X, k, STARTS, M=MX_)
    loss, seed_kept, W, H = fs[0]
    m_ = np.array([matched(H, H_) for *_, H_ in fs[1:]])               # starts x patterns
    cos_starts = np.median(m_, 0) if len(m_) else np.ones(k)
    _, _, Wo, Ho = best_of(Xo, k, HALF_STARTS, M=Mo)[0]
    _, _, We, He = best_of(Xe, k, HALF_STARTS, seed0=100, M=Me)[0]      # seeds disjoint from the odd half's
    po, pe = kept_order(H, Ho), kept_order(H, He)                      # half patterns in the kept order
    Ho, Wo, He, We = Ho[po], Wo[:, po], He[pe], We[:, pe]
    cos_oe = (unit_(Ho) * unit_(He)).sum(1)
    crit[k] = {"towns": town_tests(W, H), "cos_starts": cos_starts, "cos_halves": cos_oe,
               "cos_kept_odd": (unit_(H) * unit_(Ho)).sum(1), "cos_kept_even": (unit_(H) * unit_(He)).sum(1), "loss": float(loss)}
    fitk[k] = (W, H, seed_kept, [float(z[0]) for z in fs], m_, (Wo, Ho, We, He))
    c_ = crit[k]
    car = [carrier(c_, j) for j in range(k)]
    best_town = [max(c_["towns"], key=lambda t_: min(c_["towns"][t_]["res_share"][j], c_["towns"][t_]["travel_share"][j]))
                 for j in range(k)]
    print(f"K={k:2d}: patterns carried by " + ", ".join(
        f"{j}:{car[j]}" if car[j] else f"{j}:none (best {best_town[j]} {c_['towns'][best_town[j]]['res_share'][j]:.0%} of residents "
        f"/{c_['towns'][best_town[j]]['res'][j]:,.0f} / {c_['towns'][best_town[j]]['travel_share'][j]:.0%} of travel)"
        for j in range(k)) + f"; starts cosine min {c_['cos_starts'].min():.3f}; odd/even cosine min {c_['cos_halves'].min():.3f}",
          flush=True)
    if k >= KMAX0 and not (all(car) and (c_["cos_starts"] >= COS_MIN).all() and (c_["cos_halves"] >= COS_MIN).all()
                           and k < KCAP):
        break
    k += 1
KGRID = range(1, k + 1)


def passes(k, tmin=TOWN_MIN, cos=COS_MIN):
    c_ = crit[k]
    return bool(all(carrier(c_, j, tmin) for j in range(k)) and (c_["cos_starts"] >= cos).all()
                and (c_["cos_halves"] >= cos).all())


def pick(strict=False, **kw):
    ok = [k for k in crit if passes(k, **kw)]
    if not ok and strict:
        raise SystemExit(f"{REGION}: no K passes the rule ({kw or 'adopted thresholds'})")
    return max(ok) if ok else 0          # 0 in the sensitivity table: nothing passes


K = pick(strict=True)
binding = {}
for k in crit:
    c_ = crit[k]
    binding[k] = [n_ for n_, bad in (("no town", not all(carrier(c_, j) for j in range(k))),
                                     ("starts", (c_["cos_starts"] < COS_MIN).any()),
                                     ("halves", (c_["cos_halves"] < COS_MIN).any())) if bad]
print(f"chosen K={K}: the largest K in 1-{max(crit)} at which every pattern holds 10%+ and 1,000+ of some study town's "
      f"residents and 10%+ of that town's travel, with matched cosine 0.9+ across starts and between odd and even months. "
      f"Fails by K: " + "; ".join(f"{k} {','.join(v) or 'pass'}" for k, v in binding.items()))
print(f"   carriers at K={K}: " + ", ".join(f"pattern {j} {carrier(crit[K], j)}" for j in range(K)))
SENS = {}
print("sensitivity (K picked; town threshold for residents and travel x cosine threshold):")
for tv in (0.10, 0.15, 0.20):
    row = {cs: pick(tmin=tv, cos=cs) for cs in (0.85, 0.90, 0.95)}
    SENS[f"{tv:.2f}"] = {f"{cs:.2f}": v for cs, v in row.items()}
    print(f"   town {tv:.0%}: " + ", ".join(f"cosine {cs:.2f} -> K={v}" for cs, v in row.items()))
W, H, seed_kept, losses, m_, HALF_FIT = fitk[K]
stability = {"starts": STARTS, "seed_kept": seed_kept, "loss": [round(z, 4) for z in losses],
             "matched_cosine_median_by_pattern": np.round(crit[K]["cos_starts"], 3).tolist(),
             "matched_cosine_min_by_pattern": np.round(m_.min(0) if len(m_) else np.ones(K), 3).tolist(),
             "odd_even_cosine_by_pattern": np.round(crit[K]["cos_halves"], 3).tolist(),
             "kept_odd_cosine_by_pattern": np.round(crit[K]["cos_kept_odd"], 3).tolist(),
             "kept_even_cosine_by_pattern": np.round(crit[K]["cos_kept_even"], 3).tolist(),
             "matched_cosine_mean": round(float(m_.mean()) if len(m_) else 1.0, 3),
             "carrier_town_by_pattern": [carrier(crit[K], j) for j in range(K)]}
criteria = {str(k): {"towns": {t_: {n_: np.round(v, 4).tolist() for n_, v in tt.items()} for t_, tt in c_["towns"].items()},
                     "cos_starts": np.round(c_["cos_starts"], 4).tolist(), "cos_halves": np.round(c_["cos_halves"], 4).tolist(),
                     "cos_kept_odd": np.round(c_["cos_kept_odd"], 4).tolist(), "cos_kept_even": np.round(c_["cos_kept_even"], 4).tolist(),
                     "carriers": [carrier(c_, j) for j in range(k)], "fails": binding[k]} for k, c_ in crit.items()}

# PERSISTENCE DIAGNOSTIC (not the K rule): held-out months, every K on the same splits -- all 105 distinct 4 / 2 / 1
# partitions of the seven months (35 training sets; block-group weights refitted on two held-out months, scored on the
# third). Cached by the travel cube's checksum (flows/reach/**/persistence.json): the data and seeds fix the result.
TRAIN = [list(c) for c in itertools.combinations(range(len(MONTHS)), 4)]
TESTS = lambda tr: [([a, b], c) for c in [m for m in range(len(MONTHS)) if m not in tr]
                    for a, b in [[m for m in range(len(MONTHS)) if m not in tr and m != c]]]
key = hashlib.sha256(cube.tobytes() + MASK.tobytes()).hexdigest()
pf = R / "persistence.json"
cache = json.load(open(pf)) if pf.exists() else {}
cache = cache if cache.get("key") == key else {"key": key, "errors": {}}
if not cache["errors"] and (R / "patterns.json").exists() and len(obs) == len(MONTHS) * len(homes):
    # seeded from the previous fit's errors when its block groups and destinations match (same data and seeds: the
    # same numbers, rounded to 5 decimals)
    _prev = json.load(open(R / "patterns.json"))
    if _prev.get("homes") == homes and _prev.get("units") == units:
        cache["errors"] = {str(k_): v_ for k_, v_ in _prev.get("errors_by_training_set", {}).items()}


def score_k(k):
    per = []
    for rep, tr in enumerate(TRAIN):
        Xt, Mt = mean_mask(tr)
        _, Hs = nmf(Xt, k, seed=rep, M=Mt)
        e = []
        for wm, sm in TESTS(tr):
            Xw, Mw = mean_mask(wm)
            Xs, Ms = mean_mask([sm])
            Ws, _ = nmf(Xw, k, H=Hs, seed=rep, M=Mw)
            Ms = Ms * Mw                                                  # scored where both are observed
            e.append((np.abs(Ws @ Hs - Xs) * Ms).sum() / Ms.sum() * 100)
        per.append(np.mean(e))
    return per


if os.environ.get("PERSIST", "1") == "1":
    for k in KGRID:
        if str(k) not in cache["errors"]:
            cache["errors"][str(k)] = score_k(k)
    json.dump(cache, open(pf, "w"))
err = {int(k): np.array(v) for k, v in cache["errors"].items()}
scores = {k: float(v.mean()) for k, v in sorted(err.items())}
if scores:
    print("persistence diagnostic (held-out month error, points; not the K rule): "
          + ", ".join(f"K={k} {v:.4f}" for k, v in scores.items()))
# scale so each pattern's peak place is 1; weights then read as reach to that peak
peak = H.max(1, keepdims=True)
H, W = H / peak, W * peak.T
name = lambda u: place_name.get(u, u)
out = {"K": K, "k_rule": "largest K at which every pattern holds 10%+ and 1,000+ of some study town's residents and 10%+ "
                         "of that town's travel (residents x reach), matched cosine 0.9+ across 10 starts and odd vs even months",
       "criteria": criteria, "sensitivity": SENS, "stability": stability,
       "persistence_scores": scores, "errors_by_training_set": {j: np.round(v, 5).tolist() for j, v in err.items()},
       "units": units, "patterns": [], "towns": {}}
for k in range(K):
    top = np.argsort(-H[k])[:8]
    out["patterns"].append({"weights_by_unit": {units[j]: round(float(H[k, j]), 4) for j in np.flatnonzero(H[k] > 0.01)},
                            "top": [[units[j], round(float(H[k, j]), 3)] for j in top]})
    print(f"pattern {k}: " + ", ".join(f"{name(units[j])} {H[k, j]:.2f}" for j in top))
mass = W * (H * 1).sum(1)[None, :]
member = mass / mass.sum(1, keepdims=True)
county_of = {}
for b, q in bg_place.items():
    if q:
        county_of.setdefault(q, []).append(b[:5])
unit_county = {u: (u[6:11] if u.startswith("rural:") else u if len(u) == 5 else max(set(county_of[u]), key=county_of[u].count))
               for u in units}
out["unit_county"] = unit_county
out["bg_unit"] = {b: (q or "rural:" + b) for b, q in bg_place.items()}
out["unit_name"] = {u: name(u) for u in units}
out["W"] = W.round(5).tolist()
out["H"] = H.round(5).tolist()
out["X"] = X.round(4).tolist()          # observed mean reach, home block group x unit (for each town's own attribution)
out["homes"] = homes
out["people"] = np.round(people, 1).tolist()
out["member"] = member.round(4).tolist()
for town in CFG["towns"]:
    idx = [hi[h] for h in hm[(hm.town == town) | (hm.place == CFG["towns"][town][1])].index if h in hi]
    ppl = (people[idx, None] * member[idx]).sum(0)
    out["towns"][town] = {"people": [round(float(x)) for x in ppl], "share": [round(float(x), 3) for x in ppl / ppl.sum()],
                          "block_groups": len(idx)}
    print(f"{town} ({len(idx)} block groups, ~{ppl.sum():,.0f} residents): "
          + ", ".join(f"pattern {k} {x / ppl.sum():.0%} (~{x:,.0f})" for k, x in sorted(enumerate(ppl), key=lambda z: -z[1])))
json.dump(out, open(R / "patterns.json", "w"))
# THE HALVES, FITTED INDEPENDENTLY (2026-10-24): W and H refitted on odd months and on even months, each
# half's patterns in the kept order, with each half's mean reach (missing home-months left out) -- for the
# replicability of the areas (analysis/confidence_layer.py). Before, both halves used the full fit's W and H.
Wo, Ho, We, He = HALF_FIT
json.dump({"X_odd": Xo.round(4).tolist(), "X_even": Xe.round(4).tolist(),
           "W_odd": Wo.round(6).tolist(), "H_odd": Ho.round(6).tolist(), "W_even": We.round(6).tolist(), "H_even": He.round(6).tolist(),
           "seen_odd": Mo.any(1).astype(int).tolist(), "seen_even": Me.any(1).astype(int).tolist(),
           "months_odd": [MONTHS[i] for i in odd], "months_even": [MONTHS[i] for i in even], "homes": homes, "units": units},
          open(R / "patterns_halves.json", "w"))
