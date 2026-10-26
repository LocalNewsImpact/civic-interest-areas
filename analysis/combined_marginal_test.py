"""Do the rejected factors, each marginal alone, add up when included together?  Every model scored out of sample.

TRAVEL    adopted model vs + every rejected pair term at once (same metro/micro area, nearest area centre, adjacent area
          centre, destination size x distance, intervening population, log driving time, on the way to a bigger centre,
          on-the-way weight). Destination-only factors (jobs, stores, metro) are absorbed by the destination effects.
          Outcome: the adopted one (calibrated, pass-through discounted). Primary: leave one home county out (8 folds,
          seed 7), Jan-Sep: R^2 of shares (1 - SSE/SST), share-weighted error, big flows (FORECAST at 5%+) absolute
          error and share within 0.8-1.25x. NESTED: the factor-addition decision made inside each outer training set
          -- among adopted, adopted + each rejected term alone, adopted + all, the candidate with the lowest inner
          leave-one-county-out error (7 folds of the training counties) is fitted on the training counties and scores
          the outer held-out counties; the score of choosing by cross-validation, not of a chosen model. Stability
          check: fit Jan-Jun, score Jul-Sep, beside persistence (Jan-Jun observed shares).
          travel_nested_all (run by name only): the same nested test over every candidate the travel log tested
          (route and area terms, competing destinations, home-county ACS measures x distance, hospitals), each alone;
          two procedures scored on the outer counties: lowest inner error, and the selection rule applied inside the
          training counties (admit a candidate only if its inner county-paired gain interval excludes zero).
COVERAGE  adopted coverage model (coverage_model.py) vs + rings, saturation terms and the travel-side extras. Newsroom counties
          held out (8 folds, seed 7, as coverage_model.py); mean absolute share error (points) per newsroom county on
          the destinations holding 1%+ of its residents' visits, averaged over counties (each county weighs the same).
SPILLOVER adopted outlet model (spillover_common.FINAL) vs + cohort, border, population, newsrooms, log outlet stories, travel out; plain and
          L2-shrunk (ridge). Leave one county out; mean absolute error in points.
Every held-out error carries a 95% interval from 1,000 bootstrap resamples of the held-out counties (predictions held
fixed), and every comparison the interval of its difference from the adopted model on the same resamples.
"""
import json
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import FACTORS, FIPS, MONTHS, all_pairs, candidates, cov, miles, root  # noqa: E402
import gravity_terms as gt  # noqa: E402

import warnings
warnings.filterwarnings("ignore")
out = lambda *a: print(*a, flush=True)
# sections to run (default all): travel, coverage_all, coverage_no_broadcast, spillover
RUN = set(sys.argv[1:]) or {"travel", "coverage_all", "coverage_no_broadcast", "spillover"}


def poisson_fit(y, X, maxiter=200):
    """Plain Poisson fit; if it fails to converge (many collinear terms), a barely shrunk one (ridge 1e-4)."""
    try:
        m = sm.GLM(y, X, family=sm.families.Poisson()).fit(maxiter=maxiter)
        if np.all(np.isfinite(m.params)):
            return m.params
    except (ValueError, np.linalg.LinAlgError):
        pass
    return sm.GLM(y, X, family=sm.families.Poisson()).fit_regularized(alpha=1e-4, L1_wt=0.0, maxiter=maxiter).params


def boot_errs(e, ref=None, draws=1000, seed=7, per_county=False):
    """e: {held-out county: [errors]}. Mean error, its 95% interval over counties (1,000 draws), and the interval of the
    difference from ref (same counties, paired). per_county=True: the mean of per-county means, each county weighing
    the same (coverage's declared metric); else the mean over all scored units (spillover: outlets)."""
    ks = sorted(e)
    rng = np.random.default_rng(seed)
    if per_county:
        mean = lambda d, b: np.mean([np.mean(d[k]) for k in b])
    else:
        mean = lambda d, b: np.mean(np.concatenate([d[k] for k in b]))
    v = [mean(e, b) - (mean(ref, b) if ref is not None else 0) for b in (rng.choice(ks, len(ks)) for _ in range(draws))]
    lo, hi = np.quantile(v, [.025, .975])
    m = mean(e, ks) - (mean(ref, ks) if ref is not None else 0)
    return f"{m:+.2f} [{lo:+.2f}, {hi:+.2f}]" if ref is not None else f"{m:.2f} [{lo:.2f}, {hi:.2f}]"


pairs = all_pairs()
key = list(zip(pairs.i, pairs.j))
base = candidates(pairs)
FE = [c for c in base.columns if c.startswith(("o_", "d_"))]

# ---- extra pair terms ------------------------------------------------------------------------------------------------
d = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str)
d = d[d["FIPS State Code"] == "29"]
cbsa = {"29" + r[11]: r[1] for r in d.itertuples()}
central = {"29" + r[11] for r in d.itertuples() if r[12] == "Central"}
nearest = {i: min((j for j in central if j != i), key=lambda j: miles(i, j)) for i in FIPS}
drive = pd.read_csv(root / "analysis/drive_od.csv", dtype={"i": str, "j": str}).set_index(["i", "j"])
drive["through"] = drive.through.fillna("").map(lambda s: set(s.split(";")) if s else set())
pop = cov.population
D = {k: miles(*k) for k in key}
X_extra = pd.DataFrame(index=pairs.index)
X_extra["same_area"] = [int(i in cbsa and cbsa.get(i) == cbsa.get(j)) for i, j in key]
X_extra["nearest_centre"] = [int(nearest[i] == j) for i, j in key]
X_extra["adjacent_centre"] = pairs.adjacent.values * np.array([int(j in central) for _, j in key])
X_extra["log_pop_j_x_log_dist"] = np.log(pop.reindex(pairs.j).values) * np.log(pairs.dist.values)
X_extra["log_intervening"] = [np.log1p(sum(pop[k] for k in FIPS if k not in (i, j) and D[(i, k)] < D[(i, j)])) for i, j in key]
X_extra["log_drive_minutes"] = np.log([drive.drive_minutes[k] for k in key])
on_c, on_w = [], []
for i, j in key:
    big = [k for k in central if k not in (i, j) and pop[k] > pop[j] and drive.drive_minutes[(i, k)] <= 90]
    on_c.append(int(any(j in drive.through[(i, k)] for k in big)))
    on_w.append(np.log1p(sum(pop[k] / drive.drive_minutes[(i, k)] ** 2 / 1000 for k in FIPS
                             if k not in (i, j) and j in drive.through[(i, k)])))
X_extra["on_way_centre"], X_extra["on_way_weight"] = on_c, on_w
EXTRA = list(X_extra.columns)
out("extra pair terms built:", EXTRA)


# ---- coverage and spillover data, as coverage_model.py and spillover_common.py define them ------------------------------
from excluded_outlets import EXCLUDE, home_fips  # noqa: E402  one exclusion list (incl. CAMPUS) and the home rule
ARTS = [a for a in json.load(open(root / "coverage/storymap/statewide_2026_03_articles.json"))["articles"]
        if a["publisher"] not in EXCLUDE]
_by_name = {n.lower(): f for f, n in cov.name.items()}
_by_name.update({"st. louis": "29189", "st louis": "29189", "st. louis city": "29510", "saint louis": "29189"})


def county_fips(name):
    n = (name or "").lower().replace(" county", "").strip()
    return _by_name.get(n) or _by_name.get(n.replace("saint ", "st. "))


def newsroom_fips(a):
    """coverage_model.py: HOME_COUNTY where it applies, else the county the outlet is filed under."""
    filed = county_fips(a["publisher_county"])
    return home_fips(a["publisher"], filed) if filed else None


own, outlets, bcast = Counter(), defaultdict(set), set()
for a in ARTS:
    f = newsroom_fips(a)
    if not f or not a["counties"]:
        continue
    outlets[f].add(a["publisher"])
    if "broadcast" in (a["publisher_type"] or ""):
        bcast.add(f)
    own[f] += f in a["counties"]
_tp = pd.read_csv(root / "analysis/od_predicted.csv", dtype={"i": str, "j": str})
_pidx = {k: n for n, k in enumerate(key)}


def coverage_data(version):
    """Story-county pairs as coverage_model.py builds them, and its ADOPTED terms: the gravity terms + log visits (where
    > 0) + zero-visit indicator + log visits x rural newsroom county (gravity_terms cov.rural: under 50% of the 2020
    population in Census urban areas; fixed effects separate)."""
    keep = (lambda a: True) if version == "all" else (lambda a: "broadcast" not in (a["publisher_type"] or ""))
    arts = [a for a in ARTS if keep(a) and newsroom_fips(a)]
    n = Counter()
    for a in arts:
        i = newsroom_fips(a)
        for j in a["counties"]:
            if j.startswith("29") and j != i:
                n[(i, j)] += 1
    origins = sorted({newsroom_fips(a) for a in arts})
    p = _tp[_tp.i.isin(origins)][["i", "j", "visits"]].copy()
    p["stories"] = [n.get((i, j), 0) for i, j in zip(p.i, p.j)]
    p = p[p.groupby("i").stories.transform("sum") > 0].reset_index(drop=True)
    rows = [_pidx[k] for k in zip(p.i, p.j)]
    pos = (p.visits > 0).values
    lv = np.where(pos, np.log(p.visits.where(pos, 1.0)), 0.0)
    rural = cov.rural.reindex(p.i).values.astype(float)
    adopted = base.iloc[rows][FACTORS].reset_index(drop=True).assign(
        log_visits=lv, zero_visits=(~pos).astype(float), log_visits_x_rural=lv * rural)
    Oc = pd.get_dummies(p.i, prefix="o").astype(float)
    Dc = pd.get_dummies(p.j, prefix="d", drop_first=True).astype(float)
    return p, p.stories.values.astype(float), rows, lv, rural, adopted, Oc, Dc


def coverage_loo(Xm, p, y):
    """As coverage_model.py: newsroom counties held out in 8 folds (seed 7, gravity_terms.loco), each held-out county's
    story shares predicted from the others; absolute share error (points) on the destinations with 1%+ of its
    residents' out-of-county visits (the declared primary metric; never selected on stories). {county: errors};
    score with boot_errs(per_county=True)."""
    ps = gt.loco(np.asarray(y, float), Xm, p.i.values, fit=lambda yy, XX: np.asarray(poisson_fit(yy, XX, 300)))
    err = 100 * np.abs(ps - gt.shares(y, p.i.values))
    vs = gt.shares(p.visits.values, p.i.values) >= 0.01
    return {f: err[(p.i.values == f) & vs] for f in p.i.unique() if ((p.i.values == f) & vs).any()}


nbr = {f: set(pairs[(pairs.i == f) & (pairs.adjacent == 1)].j) for f in FIPS}


def rings(f):
    dd, q = {f: 0}, deque([f])
    while q:
        x = q.popleft()
        for yy in nbr[x]:
            if yy not in dd:
                dd[yy] = dd[x] + 1; q.append(yy)
    return dd


R = {f: rings(f) for f in FIPS}

from spillover_common import FINAL as SPILL_FINAL, terms_of  # noqa: E402  the adopted spillover model
SO = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
for t_ in sorted(set(SO.type.dropna()) - {"Rural"}):
    SO[f"type_{t_}"] = (SO.type == t_).astype(float)
TYPE_COLS = [c for c in SO.columns if c.startswith("type_")]
_nr = defaultdict(set)
for a in ARTS:
    f = newsroom_fips(a)
    if f and a["counties"]:
        _nr["29189" if f == "29510" else f].add(a["publisher"])
SO["log_newsrooms"] = [np.log(max(len(_nr[f]), 1)) for f in SO.fips]
SO["log_stories"] = np.log(SO.placed)
SPILL_ADOPTED = terms_of(SPILL_FINAL)


def spill_errs(terms, alpha=0.0):
    """spillover_outlets.py's scheme: fitted on the well-collected outlets with 20+ stories (fitted), scored on those
    with 10+ (scored), each county's scored outlets predicted by a fit without that county; fractional logit, ridge
    alpha on the non-intercept terms (per outlet). {county: absolute errors, points}."""
    fit, sc = SO[SO.fitted.astype(bool)], SO[SO.scored.astype(bool)]
    Xof_ = lambda d: np.column_stack([np.ones(len(d))] + [d[t].to_numpy(float) for t in terms])
    e = {}
    for c in sc.fips.unique():
        tr, te = fit[fit.fips != c], sc[sc.fips == c]
        Xt, yt = Xof_(tr), tr.rate.to_numpy(float)
        b = np.zeros(Xt.shape[1]); P = np.eye(len(b)) * alpha * len(yt); P[0, 0] = 0
        for _ in range(100):
            mu = 1 / (1 + np.exp(-np.clip(Xt @ b, -30, 30)))
            H = (Xt * (mu * (1 - mu))[:, None]).T @ Xt + P
            step = np.linalg.lstsq(H, Xt.T @ (yt - mu) - P @ b, rcond=None)[0]
            b = b + step
            if np.max(np.abs(step)) < 1e-10:
                break
        e[c] = 100 * np.abs(1 / (1 + np.exp(-Xof_(te) @ b)) - te.rate.to_numpy(float))
    return e

# ---- travel ----------------------------------------------------------------------------------------------------------
DISC = gt.stop_discount(pairs)
y9, y6, y3 = (gt.travel_visits(pairs, m, disc=DISC) for m in (MONTHS, MONTHS[:6], MONTHS[6:]))
o = pairs.i.values
share = lambda x: gt.shares(x, o)
fitp = lambda yy, XX: np.asarray(poisson_fit(yy, XX, 300))
Xt = lambda extra: pd.concat([base[FACTORS], X_extra[list(extra)], base[FE]], axis=1)
if "travel" in RUN:
  a9 = share(y9)
  S = {}
  for label, extra in (("adopted", []), ("adopted + all rejected pair terms", EXTRA)):
    S[label] = gt.county_stats(a9, gt.loco(y9, Xt(extra), o, fit=fitp), o, y9)
  ref = S["adopted"]
  # nested: choose the terms inside each outer training set
  cands = {"adopted": [], **{f"+ {e}": [e] for e in EXTRA}, "+ all": EXTRA}
  counties = sorted(set(o))
  nested = np.full(len(o), np.nan)
  chosen = []
  for k, f in enumerate(np.array_split(np.random.default_rng(7).permutation(counties), 8)):
    test = np.isin(o, f)
    tr_c = [c for c in counties if c not in set(f)]
    inner = {}
    for name, extra in cands.items():
      X = Xt(extra)
      ps = gt.loco(y9[~test], X[~test].reset_index(drop=True), o[~test], folds=7, seed=7, fit=fitp)
      inner[name] = gt.summary(gt.county_stats(a9[~test], ps, o[~test]))["werr"]
    best = min(inner, key=inner.get)
    chosen.append(best)
    X = Xt(cands[best])
    cc = X.columns[(X[~test] != 0).any()]
    lin = X.loc[test, cc].values @ fitp(y9[~test], X.loc[~test, cc])
    lin = lin - pd.Series(lin).groupby(o[test]).transform("max").values
    nested[test] = gt.shares(np.exp(lin), o[test])
    out(f"  outer fold {k + 1}: chosen {best} (inner error {inner[best]:.3f}; adopted {inner['adopted']:.3f})")
  S["nested: terms chosen inside each training set"] = gt.county_stats(a9, nested, o, y9)
  out("\n## TRAVEL (primary: leave one home county out, Jan-Sep; [95% interval over counties])")
  out("| Model | Terms | R^2 of shares (1 - SSE/SST) | Weighted share error | Change vs adopted | Big flows (forecast 5%+): abs error | Change vs adopted | Big flows within 0.8-1.25x |")
  out("|---|---:|---:|---:|---:|---:|---:|---:|")
  nt = {"adopted": len(FACTORS), "adopted + all rejected pair terms": len(FACTORS) + len(EXTRA), "nested: terms chosen inside each training set": "chosen"}
  for label, st in S.items():
    r = gt.summary(st)
    ci = {k: gt.boot(st, k) for k in ("werr", "big", "r2")}
    dif = {k: ("" if st is ref else "{:+.2f} [{:+.2f}, {:+.2f}]".format(r[k] - gt.summary(ref)[k], *gt.boot(st, k, ref=ref))) for k in ("werr", "big")}
    out(f"| {label} | {nt[label]} | {r['r2']:.1%} [{ci['r2'][0]:.1%}, {ci['r2'][1]:.1%}] | {r['werr']:.2f} [{ci['werr'][0]:.2f}, {ci['werr'][1]:.2f}] | "
        f"{dif['werr']} | {r['big']:.2f} [{ci['big'][0]:.2f}, {ci['big'][1]:.2f}] | {dif['big']} | {r['within']:.0%} |")
  out("\n## TRAVEL, stability check (not validation): fit Jan-Jun, score Jul-Sep")
  out("| Forecast | R^2 of shares (1 - SSE/SST) | Weighted share error | Big flows (forecast 5%+): abs error | Big flows within 0.8-1.25x |")
  out("|---|---:|---:|---:|---:|")
  s3 = share(y3)
  T = {"persistence: Jan-Jun observed shares": gt.county_stats(s3, share(y6), o, y3)}
  for label, extra in (("adopted", []), ("adopted + all rejected pair terms", EXTRA)):
    X = Xt(extra)
    T[label] = gt.county_stats(s3, share(np.exp(X.values @ fitp(y6, X))), o, y3)
  for label, st in T.items():
    r = gt.summary(st)
    out(f"| {label} | {r['r2']:.1%} | {r['werr']:.2f} | {r['big']:.2f} | {r['within']:.0%} |")

# ---- travel: nested selection over every candidate tested --------------------------------------------------------------
if "travel_nested_all" in RUN:
  import math
  # competing destinations (travel_competing_test.py)
  cp = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO29.txt", dtype=str, encoding="utf-8-sig")
  cen = {r.STATEFP + r.COUNTYFP: (float(r.LATITUDE), float(r.LONGITUDE)) for r in cp.itertuples()}
  size = cov.places.astype(float).to_dict()
  brg = lambda a_, b_: math.atan2(cen[b_][0] - cen[a_][0], (cen[b_][1] - cen[a_][1]) * math.cos(math.radians((cen[a_][0] + cen[b_][0]) / 2)))
  fl = [f for f in FIPS if f in cen and f in size]
  C = pd.DataFrame(index=pairs.index)
  alt, altd, acc = [], [], []
  for i, j in key:
    dij = max(miles(i, j), 1.0)
    riv = [k for k in fl if k not in (i, j) and size[k] >= size.get(j, 0)]
    bj = brg(i, j)
    rivd = [k for k in riv if abs((brg(i, k) - bj + math.pi) % (2 * math.pi) - math.pi) >= math.radians(60)]
    alt.append(math.log(max(min((miles(i, k) for k in riv), default=400.0), 1.0) / dij))
    altd.append(math.log(max(min((miles(i, k) for k in rivd), default=400.0), 1.0) / dij))
    acc.append(math.log(sum(size[k] / max(miles(j, k), 1.0) for k in fl if k not in (i, j))))
  C["alt_ratio"], C["alt_ratio_dir"], C["fotheringham"] = alt, altd, acc
  # home-county ACS measures x centred log distance (civic_variables_test.py)
  acs = pd.read_csv(root / "free/mo_county_acs_2024.csv", dtype={"fips": str})
  pct = acs.pivot(index="fips", columns="variable", values="percent")
  est = acs.pivot(index="fips", columns="variable", values="estimate")
  V = pd.DataFrame({"median_household_income": np.log(est.median_household_income), "per_capita_income": np.log(est.per_capita_income),
                    "median_age": est.median_age, "mean_travel_time": est.mean_travel_time})
  for v in ("age_65_and_over", "households_with_broadband", "below_poverty", "bachelors_or_higher", "in_labor_force", "owner_occupied"):
    V[v] = pct[v]
  V = (V - V.mean()) / V.std()
  for v in V.columns:
    C[f"{v}_x_log_dist"] = V[v].reindex(pairs.i).values * base["log_dist"].values
  # hospitals (hospital_test.py)
  hc = set(pd.read_csv(root / "analysis/hospitals_mo.csv", dtype={"fips": str}).fips)
  nh = {i: min((j for j in hc if j != i), key=lambda j: miles(i, j)) for i in FIPS}
  C["nearest_hospital"] = [float(nh[i] == j) for i, j in key]
  C["nearest_x_none"] = [float(nh[i] == j and i not in hc) for i, j in key]
  C = C.join(X_extra)
  assert not C.isna().any().any(), C.columns[C.isna().any()].tolist()
  cands = {"adopted": [], **{f"+ {e}": [e] for e in EXTRA}, "+ all eight route/area terms": EXTRA,
           **{f"+ {e}": [e] for e in ("alt_ratio", "alt_ratio_dir", "fotheringham")},
           **{f"+ {v}_x_log_dist": [f"{v}_x_log_dist"] for v in V.columns},
           "+ nearest_hospital": ["nearest_hospital"], "+ nearest_hospital, nearest_x_none": ["nearest_hospital", "nearest_x_none"]}
  out(f"\n## TRAVEL, nested selection over {len(cands) - 1} candidates (each alone, and the eight route/area terms together)")
  Xc = {n_: pd.concat([base[FACTORS], C[list(e)], base[FE]], axis=1) for n_, e in cands.items()}
  start = {n_: pd.Series(np.asarray(poisson_fit(y9, X_, 300)), index=X_.columns) for n_, X_ in Xc.items()}
  def fit_ws(n_):
    def f_(yy, XX):
      return np.asarray(sm.GLM(yy, XX, family=sm.families.Poisson()).fit(maxiter=300, start_params=start[n_][XX.columns].values).params)
    return f_
  a9 = share(y9)
  counties = sorted(set(o))
  outer = {"argmin": np.full(len(o), np.nan), "rule": np.full(len(o), np.nan)}
  outer_all = {n_: np.full(len(o), np.nan) for n_ in cands}
  log = []
  for k, f in enumerate(np.array_split(np.random.default_rng(7).permutation(counties), 8)):
    test = np.isin(o, f)
    inner = {}
    for n_, X_ in Xc.items():
      ps = gt.loco(y9[~test], X_[~test].reset_index(drop=True), o[~test], folds=7, seed=7, fit=fit_ws(n_))
      inner[n_] = gt.county_stats(a9[~test], ps, o[~test])
      cc = X_.columns[(X_[~test] != 0).any()]
      lin = X_.loc[test, cc].values @ fit_ws(n_)(y9[~test], X_.loc[~test, cc])
      lin = lin - pd.Series(lin).groupby(o[test]).transform("max").values
      outer_all[n_][test] = gt.shares(np.exp(lin), o[test])
    werr = {n_: st.werr.mean() for n_, st in inner.items()}
    best = min(werr, key=werr.get)
    admitted = [n_ for n_ in cands if n_ != "adopted" and gt.boot(inner["adopted"], "werr", ref=inner[n_])[0] > 0]
    rule = min(admitted, key=werr.get) if admitted else "adopted"
    outer["argmin"][test], outer["rule"][test] = outer_all[best][test], outer_all[rule][test]
    log.append((k + 1, best, rule, admitted))
    out(f"  outer fold {k + 1}: lowest inner error {best} ({werr[best]:.3f}, adopted {werr['adopted']:.3f}); "
        f"selection rule admits {admitted or 'none'} -> {rule}")
  ref_ = gt.county_stats(a9, outer_all["adopted"], o, y9)
  out("| Procedure / model | Held-out error | Gain vs adopted [95%, county-paired, 1,000 draws] |\n|---|---:|---:|")
  out(f"| adopted (same folds) | {ref_.werr.mean():.3f} | |")
  verdict = {}
  for lab, ps in (("nested (DECIDING): lowest inner error", outer["argmin"]), ("nested: selection rule inside the training counties", outer["rule"]),
                  ("one at a time, not nested (reference only): + alt_ratio", outer_all["+ alt_ratio"])):
    st = gt.county_stats(a9, ps, o, y9)
    lo, hi = gt.boot(ref_, "werr", ref=st)
    verdict[lab] = lo > 0
    out(f"| {lab} | {st.werr.mean():.3f} | {ref_.werr.mean() - st.werr.mean():+.3f} [{lo:+.3f}, {hi:+.3f}] |")
  out("DECISION (the authors' procedure: adopt only if the nested gain's interval excludes zero): "
      + ("adopt the procedure's choices" if verdict["nested (DECIDING): lowest inner error"] else "no addition adopted"))

# ---- coverage --------------------------------------------------------------------------------------------------------
for version in ("all", "no_broadcast"):
    if f"coverage_{version}" not in RUN:
        continue
    p, y, rows, lv, rural, adopted, Oc, Dc = coverage_data(version)
    own_j = np.log1p(np.array([own[j] for j in p.j], float))
    more = pd.DataFrame({
        "ring2": [float(R[i][j] == 2) for i, j in zip(p.i, p.j)], "ring3plus": [float(R[i][j] >= 3) for i, j in zip(p.i, p.j)],
        "lv_x_own": lv * own_j, "lv_x_own_x_rural": lv * own_j * rural,
        "lv_x_newsrooms": lv * np.log1p([len(outlets[j]) for j in p.j]), "lv_x_broadcast": lv * np.array([float(j in bcast) for j in p.j]),
    }).join(X_extra.iloc[rows].reset_index(drop=True))
    out(f"\n## COVERAGE, {version.replace('_', ' ')} (coverage_model.py adopted specification; newsroom counties held out, 8 folds; per-county mean error)")
    out("| Model | Terms | Mean abs share error (points) [95%] | Change vs adopted [95%] | Deviance (full fit, in-sample) |\n|---|---:|---:|---:|---:|")
    E0 = None
    for label, Xc in (("adopted (gravity terms + log visits, zero-visit indicator, log visits x rural)", adopted),
                      ("adopted + all rejected terms", pd.concat([adopted, more], axis=1))):
        Xm = pd.concat([Xc, Oc, Dc], axis=1)
        dev = sm.GLM(y, Xm, family=sm.families.Poisson()).fit(maxiter=300).deviance
        errs = coverage_loo(Xm, p, y)
        E0 = E0 or errs
        out(f"| {label} | {Xc.shape[1]} | {boot_errs(errs, per_county=True)} | {'' if errs is E0 else boot_errs(errs, E0, per_county=True)} | {dev:,.0f} |")

# ---- spillover -------------------------------------------------------------------------------------------------------
if "spillover" not in RUN:
    sys.exit()
REJ = TYPE_COLS + ["border", "log_pop", "log_newsrooms", "log_stories", "travel_out"]
out(f"\n## SPILLOVER, outlets (spillover_common.FINAL = {SPILL_FINAL}; fitted {int(SO.fitted.sum())}, scored "
    f"{int(SO.scored.sum())} outlets; leave one county out)")
out("| Model | Mean abs error (points) [95%] | Change vs adopted [95%] |\n|---|---:|---:|")
E0 = None
for label, terms, alpha in (("adopted", SPILL_ADOPTED, 0), ("+ all rejected county factors (cohort, border, population, newsrooms, log stories, travel out)", SPILL_ADOPTED + REJ, 0),
                            ("+ all rejected, ridge 0.05", SPILL_ADOPTED + REJ, 0.05), ("+ all rejected, ridge 0.2", SPILL_ADOPTED + REJ, 0.2)):
    e = spill_errs(terms, alpha)
    E0 = E0 or e
    out(f"| {label} | {boot_errs(e)} | {'' if e is E0 else boot_errs(e, E0)} |")
