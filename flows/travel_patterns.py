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
The number of patterns K is chosen on held-out months: fitted on four months, the patterns score the other three by
reconstruction error with each block group's weights refitted on two of them and scored on the third; 10 random splits;
the fewest patterns within one standard error of the best.
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
    """X ~ W @ H, non-negative, Frobenius loss on the cells M marks, multiplicative updates. H fixed when given."""
    M = MASK if M is None else M
    rng = np.random.default_rng(seed)
    fixed = H is not None
    W = rng.random((X.shape[0], k)) + 0.1
    if not fixed:
        H = rng.random((k, X.shape[1])) + 0.1
    MX = M * X
    for _ in range(iters):
        W *= (MX @ H.T) / ((M * (W @ H)) @ H.T + 1e-9)
        if not fixed:
            H *= (W.T @ MX) / (W.T @ (M * (W @ H)) + 1e-9)
    return W, H


rng = np.random.default_rng(1)
scores = {}
ses = {}
for k in range(1, 9):
    err = []
    for rep in range(10):
        order = rng.permutation(len(MONTHS))
        tr, te = order[:4], order[4:]
        _, H = nmf(cube[tr].mean(0), k, seed=rep)
        # weights from two held-out months, scored on the third
        W, _ = nmf(cube[te[:2]].mean(0), k, H=H, seed=rep)
        err.append((np.abs(W @ H - cube[te[2]]) * MASK).sum() / MASK.sum() * 100)
    scores[k], ses[k] = np.mean(err), np.std(err) / np.sqrt(len(err))
    print(f"K={k}: held-out error {scores[k]:.3f} points (se {ses[k]:.3f})", flush=True)
best = min(scores, key=scores.get)
K = min(k for k in scores if scores[k] <= scores[best] + ses[best])   # fewest patterns within one standard error
print(f"chosen K={K} (best {best})")
X = cube.mean(0)
W, H = nmf(X, K, iters=2000)
# scale so each pattern's peak place is 1; weights then read as reach to that peak
peak = H.max(1, keepdims=True)
H, W = H / peak, W * peak.T
name = lambda u: place_name.get(u, u)
out = {"K": K, "scores": scores, "units": units, "patterns": [], "towns": {}}
for k in range(K):
    top = np.argsort(-H[k])[:8]
    out["patterns"].append({"weights_by_unit": {units[j]: round(float(H[k, j]), 4) for j in np.flatnonzero(H[k] > 0.01)},
                            "top": [[units[j], round(float(H[k, j]), 3)] for j in top]})
    print(f"pattern {k}: " + ", ".join(f"{name(units[j])} {H[k, j]:.2f}" for j in top))
# ESTIMATED RESIDENTS (as for crossover): devices seen at home / the county-month calibration factor, mean over months.
# Mixed membership: a block group's residents are split across the patterns in proportion to the travel each carries.
cal = pd.read_csv(here.parent / "analysis/calibration_county_month.csv", dtype={"county": str}).set_index(["county", "month"]).factor
o = own.reset_index()
o = o[o.home_cbg.isin(hi) & o.month.isin(MONTHS)]
o["people"] = o.device_home_areas / [cal.get((h[:5], m), np.nan) for h, m in zip(o.home_cbg, o.month)]
people = o.groupby("home_cbg").people.mean().reindex(homes).values
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
