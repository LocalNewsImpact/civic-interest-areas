"""The gravity terms shared by the travel model and the coverage model, so both are one model with the same terms; and
the travel outcome, validation and inference every travel script uses.

DOUBLY CONSTRAINED: a fixed effect for every home county (o_*) holds its total, and a fixed effect for every destination
(d_*) measures its overall draw -- a state capital, a university, hospitals, shopping -- from the data itself. What the
pair terms explain is how distance and borders distribute that travel or those stories. For i -> j:
  log_dist                   log miles between 2020 population centres (CenPop2020), CENTRED: log(miles / 25)
  log_dist_sq                its square: the distance elasticity changes with distance
  nonmetro_i_x_log_dist(_sq) the same two when the home county is nonmetropolitan (USDA RUCC 4-9), else 0
  log_pop_i_x_log_dist       larger home counties travel farther: (log population - its mean over the 115 counties,
                             ACS 2020-2024; geometric mean 21,980) x centred log distance
  adjacent                   1 if the counties share a border
  commute_out                log(1 + 1000 x workers living in i who work in j / all workers living in i)  (LODES 2023)
  commute_in                 log(1 + 1000 x workers living in j who work in i / all workers living in j)  (LODES 2023)
CENTRING. Distance is measured from 25 miles (REF_MILES; the visit-weighted geometric mean distance of out-of-county
trips is 26 miles) and home-county population from its mean, so the log_dist coefficient is the distance elasticity of
travel at 25 miles for a metropolitan home county of mean size, and log_dist + nonmetro_i_x_log_dist the same for a
nonmetropolitan one. The constants are absorbed by the fixed effects: predictions and fit are unchanged by centring.

Validation (travel_model.py): leave-one-county-out (LOCO) -- each home county's out-of-county shares predicted from a
model fitted without any of its travel (8 folds, seed 7). The Jan-Jun -> Jul-Sep split is a stability check, scored
beside persistence (Jan-Jun observed shares as the forecast). candidates() keeps every term tested so the comparisons
can be re-run.
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import shape

root = Path(__file__).resolve().parents[1]
cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str}).set_index("fips")
FIPS = list(cov.index)
FACTORS = ["log_dist", "log_dist_sq", "nonmetro_i_x_log_dist", "nonmetro_i_x_log_dist_sq", "log_pop_i_x_log_dist",
           "adjacent", "commute_out", "commute_in"]
# SELECTION RULE (2026-10-24; travel_model_dc_test.py selection): the set must beat origin + destination effects alone
# held out (each home county left out; county-paired bootstrap, 1,000 draws; 95% interval excluding zero) -- 16.76 ->
# 3.26, gain +13.50 [+11.69, +15.14]; every coefficient's 2-way clustered 95% interval excludes zero (all eight do);
# a candidate is added only if its paired held-out gain excludes zero, and the choice survives the nested test
# (combined_marginal_test.py travel_nested_all, 24 candidates): none does -- the nearest comparable alternative passes
# one at a time (+0.051 [+0.002, +0.100]) and fails nested (+0.041 [-0.112, +0.173]). Drop-one gains, reported, not used
# to drop: log_dist +0.17 [-0.09, +0.45], log_dist_sq +0.28 [+0.01, +0.55], nonmetro x log_dist +0.13 [-0.01, +0.28],
# nonmetro x log_dist_sq +0.18 [+0.04, +0.33], log_pop_i x log_dist +0.15 [-0.08, +0.39], adjacent +0.19
# [-0.06, +0.42], commute_out +0.38 [+0.20, +0.55], commute_in +0.06 [-0.10, +0.20].
DIST_TERMS = FACTORS[:5]
REF_MILES = 25.0                                   # centring point of every distance term
LOG_D0 = math.log(REF_MILES)
LOG_POP0 = float(np.log(cov.population).mean())    # centring point of home-county log population
# the singly-constrained model the doubly-constrained one replaced: origin effects + measured destination draw
SINGLY = ["log_pop_j", "log_retail_pc_j", "log_dist", "adjacent", "nonmetro_i_x_log_dist"]


def _lodes():
    """LODES 2023 Missouri main OD: workers by home county -> work county, and workers by home county."""
    import csv
    import gzip
    from collections import defaultdict
    flow, work = defaultdict(float), defaultdict(float)
    with gzip.open(root / "free/od_2023.csv.gz", "rt") as fh:
        for r in csv.DictReader(fh):
            h, w, n = r["h_geocode"][:5], r["w_geocode"][:5], float(r["S000"])
            work[h] += n
            flow[(h, w)] += n
    return flow, work


_FLOW, _WORK = _lodes()

_geo = json.load(open(root / "flows/cousub_29.geojson"))
_shp = {f["id"]: shape(f["geometry"]).buffer(0.002) for f in _geo["counties"]["features"]}   # ~200 m: closes slivers
_adj = {(a, b) for a in FIPS for b in FIPS if a < b and _shp[a].intersects(_shp[b])}


def miles(a, b):
    p1, p2 = math.radians(cov.lat[a]), math.radians(cov.lat[b])
    dl = math.radians(cov.lon[b] - cov.lon[a])
    return 3959 * math.acos(min(1, math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)))


def all_pairs():
    p = pd.DataFrame([(i, j) for i in FIPS for j in FIPS if i != j], columns=["i", "j"])
    p["dist"] = [miles(i, j) for i, j in zip(p.i, p.j)]
    p["adjacent"] = [int((min(i, j), max(i, j)) in _adj) for i, j in zip(p.i, p.j)]
    return p


def distance_terms(logd, origins, ref=LOG_D0):
    """The five distance terms from any log distance (miles, driving minutes), centred at `ref` and at mean log
    home-county population."""
    l = np.asarray(logd, float) - ref
    nonmetro = 1 - cov.metro.reindex(origins).values
    return pd.DataFrame({"log_dist": l, "log_dist_sq": l ** 2, "nonmetro_i_x_log_dist": nonmetro * l,
                         "nonmetro_i_x_log_dist_sq": nonmetro * l ** 2,
                         "log_pop_i_x_log_dist": (np.log(cov.population.reindex(origins).values) - LOG_POP0) * l})


def candidates(p):
    """Every factor tested, plus the home-county fixed effects."""
    X = pd.DataFrame(index=p.index)
    pop_j = cov.population.reindex(p.j).values
    X["log_pop_j"] = np.log(pop_j)
    X["log_jobs_pc_j"] = np.log(cov.jobs.reindex(p.j).values / pop_j)
    X["log_retail_pc_j"] = np.log((cov.retail.reindex(p.j).values + 1) / pop_j)
    X["metro_j"] = cov.metro.reindex(p.j).values
    D = distance_terms(np.log(p.dist.values), p.i.values)
    for c in D.columns:
        X[c] = D[c].values
    X["adjacent"] = p.adjacent.values
    X["commute_out"] = [math.log1p(1000 * _FLOW.get((i, j), 0) / max(_WORK.get(i, 0), 1)) for i, j in zip(p.i, p.j)]
    X["commute_in"] = [math.log1p(1000 * _FLOW.get((j, i), 0) / max(_WORK.get(j, 0), 1)) for i, j in zip(p.i, p.j)]
    origin = pd.get_dummies(p.i, prefix="o", drop_first=False).astype(float)
    origin.index = p.index
    dest = pd.get_dummies(p.j, prefix="d", drop_first=True).astype(float)   # one dropped: origins carry the level
    dest.index = p.index
    return pd.concat([X, origin, dest], axis=1)


def design(p):
    """The model's pair terms and both sets of fixed effects."""
    X = candidates(p)
    return X[FACTORS + [c for c in X.columns if c.startswith(("o_", "d_"))]]


# ---- the travel outcome ----------------------------------------------------------------------------------------------
# Visits by residents of county i to county j (i != j), Advan Neighborhood Patterns Plus, calibrated to population
# (build_calibration.py), minus the pass-through excess: visits x (1 - max(0, road_stop_share - 0.125)) for pairs with
# 200+ store-level visitors (travel_model_stop_discount_test.py). Every travel script scores this outcome.
MONTHS = [f"2026-{m:02d}" for m in range(1, 10)]
STOP_NORM = 0.125
_OD = {}


def stop_discount(p):
    s = pd.read_csv(root / "analysis/road_stop_share.csv", dtype={"i": str, "j": str}).set_index(["i", "j"])
    return np.array([max(0.0, s.road_stop_share[k] - STOP_NORM) if k in s.index and s.visitors[k] >= 200 else 0.0
                     for k in zip(p.i, p.j)])


def _od():
    if "mo" not in _OD:
        od = pd.read_csv(root / "analysis/od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
        _OD["mo"] = od[(od.home_county != "OUT") & (od.home_county != od.dest_county)]
    return _OD["mo"]


def travel_visits(p, months, discounted=True, col="visits", disc=None):
    """The adopted outcome for pairs p over `months`: calibrated, pass-through discounted (discounted=False: not).
    col="visits_recorded" gives the uncalibrated counts."""
    v = _od()[lambda d: d.month.isin(months)].groupby(["home_county", "dest_county"])[col].sum()
    y = np.array([v.get(k, 0) for k in zip(p.i, p.j)], float)
    if not discounted:
        return y
    return y * (1 - (stop_discount(p) if disc is None else disc))


def calibration_factor(home, month):
    """Population calibration factor (build_calibration.py) for each (home county, month) row."""
    cal = pd.read_csv(root / "analysis/calibration_county_month.csv", dtype={"county": str}).set_index(["county", "month"]).factor
    return np.array([cal.get((h, m), np.nan) for h, m in zip(home, month)])


# ---- scoring ---------------------------------------------------------------------------------------------------------
def shares(x, origins):
    x = np.asarray(x, float)
    t = pd.Series(x).groupby(np.asarray(origins)).transform("sum").values
    return np.divide(x, t, out=np.zeros_like(x), where=t > 0)


def r2_oos(a, p):
    """Out-of-sample R^2 = 1 - SSE/SST of shares (not a squared correlation)."""
    a, p = np.asarray(a), np.asarray(p)
    return 1 - np.sum((a - p) ** 2) / np.sum((a - a.mean()) ** 2)


def poisson_fit(y, X, maxiter=300):
    import statsmodels.api as sm
    return sm.GLM(y, X, family=sm.families.Poisson()).fit(maxiter=maxiter)


def loco(y, X, origins, counties=None, folds=8, seed=7, fit=None):
    """Leave-one-county-out (in `folds` folds): each held-out home county's destination shares predicted from a model
    fitted on every other home county's travel (its own origin effect dropped; shares need none). Returns shares for
    held-out origins, NaN elsewhere. counties: the home counties to hold out (default all)."""
    origins = np.asarray(origins)
    counties = sorted(set(origins)) if counties is None else sorted(counties)
    fit = fit or (lambda yy, XX: np.asarray(poisson_fit(yy, XX).params))
    pred = np.full(len(origins), np.nan)
    for f in np.array_split(np.random.default_rng(seed).permutation(counties), folds):
        test = np.isin(origins, f)
        train = ~test
        cc = X.columns[(X[train] != 0).any()]
        lin = X.loc[test, cc].values @ fit(y[train], X.loc[train, cc])
        lin = lin - pd.Series(lin).groupby(origins[test]).transform("max").values
        pred[test] = shares(np.exp(lin), origins[test])
    return pred


def county_stats(a, ps, origins, y=None, big=0.05):
    """Per-home-county pieces of every score, so scores can be bootstrapped over home counties. a: observed shares;
    ps: forecast shares (NaN = not scored); y: observed counts, for held-out deviance. Big flows and each county's top
    destination are selected by the FORECAST share (selection on the observed share, *_obs, is biased upward)."""
    ok = np.isfinite(ps)
    d = pd.DataFrame({"o": np.asarray(origins)[ok], "a": np.asarray(a)[ok], "p": np.asarray(ps)[ok]})
    n_per = d.groupby("o").a.transform("size")
    d["sse"] = (d.a - d.p) ** 2
    d["sst"] = (d.a - 1 / n_per) ** 2                         # shares average 1/(destinations) within every origin
    d["wabs"] = 100 * d.a * (d.p - d.a).abs()
    d["err"] = 100 * (d.p - d.a).abs()
    d["bigp"], d["bigo"] = d.p >= big, d.a >= big
    r = d.a / d.p.where(d.p > 0)
    d["within"] = d.bigp & (r >= 0.8) & (r <= 1.25)
    d["off15"] = d.bigp & ((r >= 1.5) | (r <= 1 / 1.5))
    g = d.groupby("o")
    tp, to = d.loc[g.p.idxmax()].set_index("o"), d.loc[g.a.idxmax()].set_index("o")
    out = pd.DataFrame({"sse": g.sse.sum(), "sst": g.sst.sum(), "werr": g.wabs.sum(),
                        "big_abs": d.err.where(d.bigp, 0).groupby(d.o).sum(), "big_n": g.bigp.sum(),
                        "bigo_abs": d.err.where(d.bigo, 0).groupby(d.o).sum(), "bigo_n": g.bigo.sum(),
                        "within": g.within.sum(), "off15": g.off15.sum(),
                        "top_pred": tp.a / tp.p, "top_obs": to.a / to.p})
    if y is not None:
        yy = np.asarray(y, float)[ok]
        mu = d.p.values * pd.Series(yy).groupby(d.o.values).transform("sum").values
        ll = np.where(yy > 0, yy * np.log(np.where(yy > 0, yy, 1) / np.where(mu > 0, mu, 1e-300)), 0)
        out["dev"] = pd.Series(2 * (ll - (yy - mu))).groupby(d.o.values).sum()
    return out


def summary(s):
    """Scores from county_stats rows (any subset or bootstrap resample of home counties):
    r2 = 1 - SSE/SST of shares; werr = share-weighted absolute share error (points; each county weighted equally);
    big = mean absolute share error (points) of pairs forecast at 5%+ (big_obs: pairs observed at 5%+);
    within / off15 = share of those pairs within 0.8-1.25x / off by 1.5x+; top = median observed / forecast for each
    county's top forecast destination (top_obs: top observed destination); dev = held-out Poisson deviance."""
    r = {"r2": 1 - s.sse.sum() / s.sst.sum(), "werr": s.werr.mean(),
         "big": s.big_abs.sum() / max(s.big_n.sum(), 1), "big_obs": s.bigo_abs.sum() / max(s.bigo_n.sum(), 1),
         "within": s.within.sum() / max(s.big_n.sum(), 1), "off15": s.off15.sum() / max(s.big_n.sum(), 1),
         "top": s.top_pred.median(), "top_q1": s.top_pred.quantile(.25), "top_q3": s.top_pred.quantile(.75),
         "top_obs": s.top_obs.median(), "n_big": int(s.big_n.sum())}
    if "dev" in s:
        r["dev"] = s.dev.sum()
    return r


def boot(s, key, ref=None, draws=1000, seed=7, mask=None):
    """95% interval over home counties (resampled with replacement; predictions held fixed) for summary()[key], or for
    its difference from `ref` (county_stats of another forecast of the same counties)."""
    idx = s.index if mask is None else s.index[np.asarray(mask)]
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(draws):
        b = rng.choice(idx, len(idx), replace=True)
        v = summary(s.loc[b])[key]
        vals.append(v - summary(ref.loc[b])[key] if ref is not None else v)
    return np.quantile(vals, [0.025, 0.975])


def fit_twoway(y, X, p):
    """PPML with standard errors clustered two ways, by home county and by destination county (Cameron, Gelbach and
    Miller 2011): the inference for every travel coefficient reported."""
    import statsmodels.api as sm
    g = np.column_stack([pd.factorize(p.i)[0], pd.factorize(p.j)[0]])
    return sm.GLM(y, X, family=sm.families.Poisson()).fit(maxiter=300, cov_type="cluster", cov_kwds={"groups": g})


def term_table(m, terms):
    return pd.DataFrame({"coef": m.params[terms], "se (2-way)": m.bse[terms], "p (2-way)": m.pvalues[terms]})


# ---- one comparison row, the same in every travel script ---------------------------------------------------------------
HEAD = ("| Model | In-sample deviance | LOCO R^2 of shares | LOCO weighted share error [95%] | Change vs adopted [95%] | "
        "LOCO held-out deviance | LOCO top forecast destination, actual / forecast | LOCO big flows within 0.8-1.25x | "
        "Jul-Sep R^2 from Jan-Jun (stability) | Added terms, coef (2-way p) |\n|---|---:|---:|---:|---:|---:|---|---:|---:|---|")


def evaluate(X, p, y9, y6=None, y3=None, counties=None, extra=(), full=True):
    """LOCO county_stats on Jan-Sep (primary), Jan-Jun -> Jul-Sep county_stats (stability), the full Jan-Sep fit with
    two-way clustered errors (in-sample deviance; inference for `extra` terms)."""
    o = p.i.values
    ev = {"loco": county_stats(shares(y9, o), loco(y9, X, o, counties), o, y9)}
    if y6 is not None:
        ev["split"] = county_stats(shares(y3, o), shares(poisson_fit(y6, X).predict(X), o), o, y3)
    if full:
        ev["m"] = fit_twoway(y9, X, p)
    ev["extra"] = list(extra)
    return ev


def persistence(p, y6, y3):
    o = p.i.values
    r = summary(county_stats(shares(y3, o), shares(y6, o), o, y3))
    return f"persistence (Jan-Jun observed shares as the Jul-Sep forecast): R^2 {r['r2']:.1%}, weighted share error {r['werr']:.2f}"


def row(label, ev, ref=None):
    s = summary(ev["loco"])
    lo, hi = boot(ev["loco"], "werr")
    if ref is not None and ref is not ev:
        dl, dh = boot(ev["loco"], "werr", ref=ref["loco"])
        diff = f"{s['werr'] - summary(ref['loco'])['werr']:+.3f} [{dl:+.3f}, {dh:+.3f}]"
    else:
        diff = ""
    split = f"{summary(ev['split'])['r2']:.1%}" if "split" in ev else ""
    m = ev.get("m")
    terms = "; ".join(f"{t} {m.params[t]:+.3f} ({m.pvalues[t]:.3f})" for t in ev["extra"]) if m is not None else ""
    dev = f"{m.deviance / 1e6:,.1f}M" if m is not None else ""
    return (f"| {label} | {dev} | {s['r2']:.1%} | {s['werr']:.2f} [{lo:.2f}, {hi:.2f}] | {diff} | {s['dev'] / 1e6:,.1f}M | "
            f"{s['top']:.2f}x ({s['top_q1']:.2f}-{s['top_q3']:.2f}) | {s['within']:.0%} | {split} | {terms} |")
