"""Travel patterns: the recurring ways residents of Audrain, Boone and Osage travel, January-July 2026.

Advan counts residents of a home block group seen in each destination block group; it does not link one person's trips,
so cohorts of people are not observed. Instead each home block group's travel is decomposed into a few recurring
patterns (non-negative matrix factorization): travel(h) ~ sum_k weight(h, k) x pattern(k). A pattern is a set of places
travelled to together; a block group's weights give how much of its travel follows each one.
Destinations (all of Missouri) are PLACES, not tracts (tracts split a city into its neighbourhoods, and the patterns then describe travel
across one city): each town of the Columbia-Jefferson City TV market (a block group belongs to the 2020 place holding its
centre), each rural block group (outside towns), and each other Missouri county. Reach is residents seen in the
unit's busiest block group / residents seen at home, mean over months. A block group's own town is left out (masked):
patterns describe travel beyond home.
The number of patterns K (user, 2026-10-24): the largest K (grid 1-12) at which every pattern has (a) 10%+ and 1,000+
of the market's estimated residents, (b) 10%+ of its travel volume (residents x reconstructed reach), and (c) matched
cosine 0.9+ across 10 random starts (median) and between fits to odd and to even months. The kept fit is the lowest-loss
of the 10 starts. Held-out month error (all 105 4 / 2 / 1 month partitions) is printed as a persistence diagnostic.
Writes flows/reach/patterns.json.
"""
import json
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
__file__ = str(here / "build_cousub_shares.py")
exec(open(here / "build_cousub_shares.py").read().split("\ndef cw(")[0])
from shapely.strtree import STRtree
bgs = read_shp(str(DL / "bg/cb_2020_29_bg_500k"), lambda r: r["GEOID"])
# DESTINATIONS ARE ALL OF MISSOURI, as towns and rural block groups: no TV-market boundary (a border city's market --
# St. Joseph toward Kansas City -- crosses one). The fit still uses only this market's home counties.
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
cube = np.zeros((len(MONTHS), len(homes), len(units)))
mi, hi, ui = {m: i for i, m in enumerate(MONTHS)}, {h: i for i, h in enumerate(homes)}, {u: i for i, u in enumerate(units)}
cube[p.month.map(mi), p.home_cbg.map(hi), p.unit.map(ui)] = p.reach
# destinations this market's residents actually reach: seen from 2+ home block groups, at 0.5%+ of residents
mean_ = cube.mean(0)
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


def nmf(X, k, iters=600, seed=0, H=None, M=None):
    """X ~ W @ H, non-negative, Frobenius loss on the cells M marks (M binary), multiplicative updates. H fixed when given.
    The masked products are computed as the full product less the few masked cells (one per home block group at most):
    (M * WH) H' = W (H H') - the masked cells' part, and W' (M * WH) = (W' W) H - the same -- the same updates as
    multiplying by M, about 20 times faster (2026-10-24, for the paired-split K search)."""
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


# ESTIMATED RESIDENTS (as for crossover): devices seen at home / the county-month calibration factor, mean over months.
# Mixed membership: a block group's residents are split across the patterns in proportion to the travel each carries.
cal = pd.read_csv(here.parent / "analysis/calibration_county_month.csv", dtype={"county": str}).set_index(["county", "month"]).factor
o = own.reset_index()
o = o[o.home_cbg.isin(hi) & o.month.isin(MONTHS)]
o["people"] = o.device_home_areas / [cal.get((h[:5], m), np.nan) for h, m in zip(o.home_cbg, o.month)]
people = o.groupby("home_cbg").people.mean().reindex(homes).values
ppl0 = np.nan_to_num(people)
import hashlib
import itertools
import os
from scipy.optimize import linear_sum_assignment

# THE K RULE (user, 2026-10-24: "the patterns need to have a minimum percentage of the population and overall volume -
# AND replicability"). K = the LARGEST K in the grid at which EVERY pattern meets all three:
#   (a) population  residents allocated to the pattern (devices at home / calibration factor, split by each block
#                   group's membership, as for the areas) >= 10% of the market's residents AND >= 1,000 residents
#   (b) volume      the pattern's share of the market's travel volume >= 10%: volume = residents x reconstructed
#                   reach, sum over home block groups h and destinations u (masked) of people(h) W[h,k] H[k,u] -- the
#                   estimated residents' trips the pattern carries (not the unweighted W.H reconstruction)
#   (c) replicability (i) across 10 random starts, the pattern's median matched cosine to the kept solution >= 0.9;
#                   (ii) refitted on odd months (Jan, Mar, May, Jul) and on even months (Feb, Apr, Jun) separately
#                   (best of 5 starts each), the odd and even patterns matched (Hungarian, cosine): every pair >= 0.9
# Replaces the held-out-month one-SE rule (2026-10-24, earlier the same day), which on paired splits kept adding
# patterns to the top of the grid. The held-out month score is kept as a persistence diagnostic only.
KGRID = range(1, int(os.environ.get("KMAX", 12)) + 1)
STARTS, HALF_STARTS, ITERS = 10, 5, 2000
POP_MIN, POP_ABS, VOL_MIN, COS_MIN = 0.10, 1000, 0.10, 0.90
unit_ = lambda A_: A_ / np.maximum(np.linalg.norm(A_, axis=1, keepdims=True), 1e-12)


def matched(Ha, Hb):
    """cosine of each pattern of Ha to its Hungarian match in Hb (in Ha's order)"""
    C_ = unit_(Ha) @ unit_(Hb).T
    r_, c_ = linear_sum_assignment(-C_)
    out_ = np.zeros(len(Ha))
    out_[r_] = C_[r_, c_]
    return out_


def best_of(Xm, k, n, seed0=0):
    fs = []
    for sd in range(seed0, seed0 + n):
        W_, H_ = nmf(Xm, k, iters=ITERS, seed=sd)
        fs.append(((MASK * (W_ @ H_ - Xm) ** 2).sum(), sd, W_, H_))
    return sorted(fs, key=lambda z: z[0])


X = cube.mean(0)
odd = [i for i, m in enumerate(MONTHS) if int(m[-2:]) % 2 == 1]
even = [i for i, m in enumerate(MONTHS) if int(m[-2:]) % 2 == 0]
Xo, Xe = cube[odd].mean(0), cube[even].mean(0)
total_res = ppl0.sum()
crit, fitk = {}, {}
for k in KGRID:
    fs = best_of(X, k, STARTS)
    loss, seed_kept, W, H = fs[0]
    m_ = np.array([matched(H, H_) for *_, H_ in fs[1:]])               # starts x patterns
    cos_starts = np.median(m_, 0) if len(m_) else np.ones(k)
    Ho, He = best_of(Xo, k, HALF_STARTS)[0][3], best_of(Xe, k, HALF_STARTS)[0][3]
    cos_half = matched(Ho, He)
    mass = W * H.sum(1)[None, :]
    member_ = mass / np.maximum(mass.sum(1, keepdims=True), 1e-12)
    res = (ppl0[:, None] * member_).sum(0)
    vol = np.array([(ppl0[:, None] * MASK * (W[:, [j]] @ H[[j]])).sum() for j in range(k)])
    crit[k] = {"pop_share": res / total_res, "pop": res, "vol_share": vol / vol.sum(), "cos_starts": cos_starts,
               "cos_halves": cos_half, "loss": float(loss)}
    fitk[k] = (W, H, seed_kept, [float(z[0]) for z in fs], m_)
    c_ = crit[k]
    print(f"K={k:2d}: min over patterns -- (a) residents {c_['pop_share'].min():.1%} ({c_['pop'].min():,.0f}); "
          f"(b) volume {c_['vol_share'].min():.1%}; (c-i) starts cosine {c_['cos_starts'].min():.3f}; "
          f"(c-ii) odd/even cosine {c_['cos_halves'].min():.3f}", flush=True)


def passes(k, pop=POP_MIN, vol=VOL_MIN, cos=COS_MIN):
    c_ = crit[k]
    return bool((c_["pop_share"] >= pop).all() and (c_["pop"] >= POP_ABS).all() and (c_["vol_share"] >= vol).all()
                and (c_["cos_starts"] >= cos).all() and (c_["cos_halves"] >= cos).all())


def pick(**kw):
    ok = [k for k in crit if passes(k, **kw)]
    return max(ok) if ok else 1


K = pick()
binding = {}
for k in crit:
    c_ = crit[k]
    fails = [n_ for n_, bad in (("population", (c_["pop_share"] < POP_MIN).any() or (c_["pop"] < POP_ABS).any()),
                                ("volume", (c_["vol_share"] < VOL_MIN).any()), ("starts", (c_["cos_starts"] < COS_MIN).any()),
                                ("halves", (c_["cos_halves"] < COS_MIN).any())) if bad]
    binding[k] = fails
print(f"chosen K={K}: the largest K in {KGRID.start}-{KGRID.stop - 1} at which every pattern has 10%+ and 1,000+ of the "
      f"market's residents, 10%+ of its travel volume, and matched cosine 0.9+ across starts and between odd and even "
      f"months. Fails by K: " + "; ".join(f"{k} {','.join(v) or 'pass'}" for k, v in binding.items()))
SENS = {}
print("sensitivity (K picked; population and volume threshold x cosine threshold):")
for pv in (0.05, 0.10, 0.15):
    row = {cs: pick(pop=pv, vol=pv, cos=cs) for cs in (0.85, 0.90, 0.95)}
    SENS[f"{pv:.2f}"] = {f"{cs:.2f}": v for cs, v in row.items()}
    print(f"   population and volume {pv:.0%}: " + ", ".join(f"cosine {cs:.2f} -> K={v}" for cs, v in row.items()))
if pick(pop=0.05, vol=0.05, cos=0.85) == max(KGRID):
    print(f"   (the loosest setting passes at the grid's top, K={max(KGRID)}: KMAX caps it)")
W, H, seed_kept, losses, m_ = fitk[K]
stability = {"starts": STARTS, "seed_kept": seed_kept, "loss": [round(z, 4) for z in losses],
             "matched_cosine_median_by_pattern": np.round(crit[K]["cos_starts"], 3).tolist(),
             "matched_cosine_min_by_pattern": np.round(m_.min(0) if len(m_) else np.ones(K), 3).tolist(),
             "odd_even_cosine_by_pattern": np.round(crit[K]["cos_halves"], 3).tolist(),
             "matched_cosine_mean": round(float(m_.mean()) if len(m_) else 1.0, 3)}
criteria = {str(k): {n_: np.round(v, 4).tolist() for n_, v in c_.items() if n_ != "loss"} | {"fails": binding[k]}
            for k, c_ in crit.items()}

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
if not cache["errors"] and (R / "patterns.json").exists():
    # seeded from the previous fit's errors when its block groups and destinations match (same data and seeds: the
    # same numbers, rounded to 5 decimals)
    _prev = json.load(open(R / "patterns.json"))
    if _prev.get("homes") == homes and _prev.get("units") == units:
        cache["errors"] = {str(k_): v_ for k_, v_ in _prev.get("errors_by_training_set", {}).items()}


def score_k(k):
    per = []
    for rep, tr in enumerate(TRAIN):
        _, Hs = nmf(cube[tr].mean(0), k, seed=rep)
        e = []
        for wm, sm in TESTS(tr):
            Ws, _ = nmf(cube[wm].mean(0), k, H=Hs, seed=rep)
            e.append((np.abs(Ws @ Hs - cube[sm]) * MASK).sum() / MASK.sum() * 100)
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
out = {"K": K, "k_rule": "largest K at which every pattern has 10%+ and 1,000+ of the market's residents, 10%+ of its "
                         "travel volume (residents x reach), matched cosine 0.9+ across 10 starts and odd vs even months",
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
