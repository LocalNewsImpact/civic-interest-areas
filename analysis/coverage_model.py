"""Statewide coverage model, Missouri, March 2026: how stories from each county's newsrooms about other counties are
associated with residents' travel between the two counties.

DATA. Story-county pairs from newsrooms in county i about county j (i != j): a story counts once for each Missouri county
it is centred in or mentions (the story map's two layers per article, coverage/storymap/statewide_2026_03_articles.json,
Mizzou-Missouri-State dataset), excluded_outlets.EXCLUDE left out (statewide outlets, campus newspapers). A newsroom's
county is excluded_outlets.home_fips: the county it is filed under, except the HOME_COUNTY outlets, whose stories count
with their covered county. Outlets filed under a county outside Missouri are not in the fit; they are listed in the
output with their stories (to be homed in a Missouri county through HOME_COUNTY or excluded).
Visits: gravity_terms.travel_visits, the travel model's adopted outcome (visits_statewide, Jan-Sep 2026, pass-through
discounted) -- the same visits the travel model fits.

ADOPTED SPECIFICATION. PPML; a fixed effect for every newsroom county and every county covered; plus
  CONTROLS (theory; gravity_terms.FACTORS, tested only as blocks, never one term at a time):
    distance block   log_dist, log_dist_sq, rural_i_x_log_dist, rural_i_x_log_dist_sq, log_pop_i_x_log_dist
                     (hierarchy: log_dist is kept with its square and with its interactions; the block enters or leaves
                     whole)
    border           adjacent
    commuting block  commute_out, commute_in
  TRAVEL
    log_visits              log visits i -> j where visits > 0 (0 otherwise)
    zero_visits             1 where no visit was recorded
  HYPOTHESIS TERM (stated in advance; reported whatever the result)
    log_visits_x_rural      log_visits x rural newsroom county (gravity_terms cov.rural: under 50% of the 2020
                            population in Census urban areas; RUCC nonmetro until 2026-10-25, under which Osage, 0%
                            urban, counted as metro)
The elasticity -- the percentage difference in stories associated with 1% more visits, holding the controls and both
sets of fixed effects fixed -- is reported for urban newsroom counties (log_visits) and rural ones (log_visits +
log_visits_x_rural). It is an association, not an effect of travel on coverage. The pooled elasticity (no
hypothesis term) is printed as a sensitivity.

STANDARD ERRORS. A story is counted once for each county it names, so the pairs from one newsroom county are not
independent: errors are clustered by newsroom county. Sensitivity: clustered by unordered county pair, and two-way by
newsroom county and county covered; robust (HC1, independent pairs) for reference only.

HELD OUT. gravity_terms.loco: newsroom counties held out in 8 folds (seed 7), each held-out county's out-of-county story
shares predicted from the others (its own fixed effect cancels out of its shares). Error = mean absolute share error
(points) per newsroom county, averaged over counties. PRIMARY: destinations with 1%+ of the county's visits (chosen by
travel, not by the held-out stories). Beside it: all destinations -- dominated by pairs with no stories, whose share
error is near zero for any model (the share of zero pairs is printed). Intervals: 95%, 1,000 bootstrap draws of
newsroom counties (seed 7), county-paired for differences. Each control block and the hypothesis term is scored by
leaving it out of the adopted model.

"Travel beyond gravity", log(visits / travel-model prediction), was used before 2026-10-24: given the same terms and
fixed effects it is the same quantity as log visits (printed). NOT ADOPTED, printed so earlier figures can be traced:
fixed effects + log(1 + visits) with no distance terms (0.7-0.8, the border_coverage_test.py family) and + log distance
+ border (0.52).

Run for all newsrooms and without broadcasters. Output: coverage_predicted_<version>.csv (visits: the adopted outcome;
pred_gravity: controls only; pred_travel: adopted specification).
"""
import json
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gravity_terms as gt  # noqa: E402  the same gravity terms and outcome as the travel model
from gravity_terms import FACTORS, DIST_TERMS, design, root  # noqa: E402
from excluded_outlets import EXCLUDE, home_fips  # noqa: E402  one list for every county count

warnings.filterwarnings("ignore")   # clustered covariance with fewer clusters than fixed-effect columns

BLOCKS = {"distance block (5 terms)": DIST_TERMS, "border (adjacent)": ["adjacent"],
          "commuting block (out + in)": ["commute_out", "commute_in"]}
HYP = "log_visits_x_rural"

cov = gt.cov                       # county covariates with the settlement-based rural flag
tp = pd.read_csv(root / "analysis/od_predicted.csv", dtype={"i": str, "j": str}).set_index(["i", "j"])
data = json.load(open(root / "coverage/storymap/statewide_2026_03_articles.json"))
n_excluded = sum(a["publisher"] in EXCLUDE for a in data["articles"])
data["articles"] = [a for a in data["articles"] if a["publisher"] not in EXCLUDE]
by_name = {n.lower(): f for f, n in cov.name.items()}
by_name.update({"st. louis": "29189", "st louis": "29189", "st. louis city": "29510", "saint louis": "29189"})


def county_name(f):
    return "St. Louis city" if f == "29510" else f"{cov.name[f]} County"


def county_fips(name):
    n = (name or "").lower().replace(" county", "").strip()
    return by_name.get(n) or by_name.get(n.replace("saint ", "st. "))


def newsroom_fips(a):
    """The newsroom's county: HOME_COUNTY where it applies, else the county the outlet is filed under (None outside
    Missouri, unless HOME_COUNTY homes the outlet in a Missouri county)."""
    return home_fips(a["publisher"], county_fips(a["publisher_county"]))


def poisson(y, X, **kw):
    return sm.GLM(y, X, family=sm.families.Poisson()).fit(maxiter=300, **kw)


def clusters(p):
    gi = pd.factorize(p.i)[0]
    gj = pd.factorize(p.j)[0]
    gd = pd.factorize(pd.Series([min(a, b) + max(a, b) for a, b in zip(p.i, p.j)]))[0]
    return {"newsroom county (adopted)": dict(cov_type="cluster", cov_kwds={"groups": gi}),
            "county pair (unordered)": dict(cov_type="cluster", cov_kwds={"groups": gd}),
            "two-way newsroom county x county covered": dict(cov_type="cluster",
                                                             cov_kwds={"groups": np.column_stack([gi, gj])}),
            "HC1 (pairs independent; reference only)": dict(cov_type="HC1")}


def heldout(y, X, p, start):
    """Per newsroom county: mean absolute share error (points), all destinations and destinations with 1%+ of visits."""
    def fit(yy, XX):
        return np.asarray(sm.GLM(yy, XX, family=sm.families.Poisson()).fit(
            maxiter=300, start_params=start.reindex(XX.columns).fillna(0).values).params)
    ps = gt.loco(np.asarray(y, float), X, p.i.values, fit=fit)
    err = pd.Series(100 * np.abs(ps - gt.shares(y, p.i.values)))
    vs = gt.shares(p.visits.values, p.i.values) >= 0.01
    return pd.DataFrame({"all": err.groupby(p.i.values).mean(), "travel": err[vs].groupby(p.i.values[vs]).mean()})


def bt(d, draws=1000, seed=7):
    d = d.dropna()
    rng = np.random.default_rng(seed)
    b = [d.iloc[rng.integers(0, len(d), len(d))].mean() for _ in range(draws)]
    return np.quantile(b, [0.025, 0.975])


def wald(m, terms):
    """Joint Wald test of `terms` with the model's (clustered) covariance: chi2, df, p."""
    from scipy import stats
    b, V = m.params[terms].values, m.cov_params().loc[terms, terms].values
    chi2 = float(b @ np.linalg.pinv(V) @ b)
    return chi2, len(terms), stats.chi2.sf(chi2, len(terms))


# ---- outlets outside Missouri and HOME_COUNTY --------------------------------------------------------------------------
out_state = [a for a in data["articles"] if not newsroom_fips(a)]
print(f"stories excluded by excluded_outlets.EXCLUDE: {n_excluded:,}")
print(f"stories NOT IN THE FIT, outlet filed under a county outside Missouri and not homed by HOME_COUNTY: "
      f"{len(out_state)}")
if out_state:
    tot = Counter(j[:2] for a in out_state for j in a["counties"])
    print(f"  from {len({a['publisher'] for a in out_state})} outlets; county mentions in Missouri {tot.get('29', 0)}, "
          f"elsewhere {sum(tot.values()) - tot.get('29', 0)}")
moved = Counter(a["publisher"] for a in data["articles"] if newsroom_fips(a)
                and newsroom_fips(a) != county_fips(a["publisher_county"]))
print(f"stories counted with their HOME_COUNTY newsroom county: {sum(moved.values())} from {len(moved)} outlets")

pairs = gt.all_pairs()
pairs["visits"] = gt.travel_visits(pairs, gt.MONTHS)
pairs["ratio"] = tp.ratio.reindex(list(zip(pairs.i, pairs.j))).values     # travel model's file, equivalence check only
for version, keep in (("all", lambda a: True), ("no_broadcast", lambda a: "broadcast" not in (a["publisher_type"] or ""))):
    arts = [a for a in data["articles"] if keep(a) and newsroom_fips(a)]
    n = Counter()
    for a in arts:
        i = newsroom_fips(a)
        for j in a["counties"]:
            if j.startswith("29") and j != i:
                n[(i, j)] += 1
    origins = sorted({newsroom_fips(a) for a in arts})
    p = pairs[pairs.i.isin(origins)].copy()
    p["stories"] = [n.get((i, j), 0) for i, j in zip(p.i, p.j)]
    p = p[p.groupby("i").stories.transform("sum") > 0].reset_index(drop=True)
    Xd = design(p)
    X, O = Xd[FACTORS], Xd[[c for c in Xd.columns if c.startswith(("o_", "d_"))]]
    y = p.stories.astype(float)
    pos = (p.visits > 0).values
    log_visits = np.where(pos, np.log(p.visits.where(pos, 1.0)), 0.0)
    zero = (~pos).astype(float)
    rural = cov.rural.reindex(p.i).values
    vs = gt.shares(p.visits.values, p.i.values) >= 0.01
    print(f"\n## {version}: {len(arts):,} stories from {p.i.nunique()} newsroom counties; "
          f"{int(y.sum()):,} story-county pairs outside the newsroom's county; {len(p):,} county pairs, "
          f"{int((~pos).sum())} with no recorded visits ({int(y[~pos].sum())} story-county pairs on them)")
    print(f"   county pairs with no stories: {(y == 0).mean():.0%} of all pairs, {(y[vs] == 0).mean():.0%} of pairs "
          f"with 1%+ of visits ({int(vs.sum()):,} pairs) -- the all-destinations score is dominated by zero pairs")

    # controls only (no travel term): pred_gravity
    Xg = pd.concat([X, O], axis=1)
    p["pred_gravity"] = poisson(y, Xg).predict(Xg).values
    cl = clusters(p)

    def with_travel(t, zero_col=True, interact=True, drop=()):
        """Controls (less `drop`) + travel term t (+ zero-visit indicator) (+ hypothesis term) + fixed effects."""
        Z = X.drop(columns=list(drop)).assign(log_visits=t)
        if zero_col:
            Z = Z.assign(zero_visits=zero)
        if interact:
            Z = Z.assign(**{HYP: t * rural})
        return pd.concat([Z, O], axis=1)

    def split(m):
        """(urban elasticity, s.e.), (rural elasticity, s.e.) from a fit with the hypothesis term."""
        b_, V = m.params, m.cov_params()
        se_n = np.sqrt(V.loc["log_visits", "log_visits"] + V.loc[HYP, HYP] + 2 * V.loc["log_visits", HYP])
        return (b_["log_visits"], m.bse["log_visits"]), (b_["log_visits"] + b_[HYP], se_n)

    # ADOPTED
    Xa = with_travel(log_visits)
    ma = poisson(y, Xa, **cl["newsroom county (adopted)"])
    p["pred_travel"] = ma.predict(Xa).values
    (bm, sm_), (bn, sn) = split(ma)
    r2 = np.corrcoef(y, p.pred_travel)[0, 1] ** 2
    n_m, n_n = int((cov.rural.reindex(p.i.unique()) == 0).sum()), int((cov.rural.reindex(p.i.unique()) == 1).sum())
    print(f"### ADOPTED: controls (distance block, border, commuting block) + both fixed effects + log visits + "
          f"zero-visit indicator + hypothesis term log visits x rural newsroom county; errors clustered by newsroom "
          f"county ({p.i.nunique()} clusters); r^2 of fitted with observed pairs {r2:.2f}")
    c = pd.DataFrame({"coef": ma.params, "se": ma.bse, "p": ma.pvalues}).loc[FACTORS + ["log_visits", HYP, "zero_visits"]]
    print(c.round(3).to_string())
    for lab, (b, se), k_ in (("urban newsroom counties", (bm, sm_), n_m), ("rural newsroom counties", (bn, sn), n_n)):
        print(f"ELASTICITY (adopted, {version}), {lab} ({k_}): {b:.3f}, s.e. {se:.3f}, 95% CI {b - 1.96 * se:.2f} to "
              f"{b + 1.96 * se:.2f}. 1% more visits is associated with {b:.2f}% more stories; twice the visits, "
              f"{2 ** b:.2f} times the stories")
    print("  s.e. by clustering, urban / rural (a story counts once per county it names; pairs are not independent):")
    for lab, kw in cl.items():
        a1, a2 = sm_, sn
        if not lab.startswith("newsroom county"):
            (_, a1), (_, a2) = split(poisson(y, Xa, **kw))
        print(f"    {lab:44s} {a1:.3f} / {a2:.3f}")

    # held out: control blocks and the hypothesis term, each left out of the adopted model
    start = ma.params
    E0 = heldout(y, Xa, p, start)
    print(f"  HELD OUT (8 folds of newsroom counties; mean abs share error, points; [95%, 1,000 county draws]; change "
          f"= model without the term(s) - adopted, county-paired; positive = the term(s) lower held-out error):")
    print("  | Model | Primary: 1%+ of visits | Change | All destinations | Change | Wald (clustered) |")
    print("  |---|---:|---:|---:|---:|---|")
    lo_t, hi_t = bt(E0.travel)
    lo_a, hi_a = bt(E0["all"])
    print(f"  | adopted | {E0.travel.mean():.3f} [{lo_t:.3f}, {hi_t:.3f}] | — | {E0['all'].mean():.3f} "
          f"[{lo_a:.3f}, {hi_a:.3f}] | — | — |")
    tests = [(f"without {k} (CONTROL)", with_travel(log_visits, drop=v), v) for k, v in BLOCKS.items()]
    tests.append((f"without {HYP} (HYPOTHESIS; = pooled)", with_travel(log_visits, interact=False), [HYP]))
    for lab, Xm, terms in tests:
        E = heldout(y, Xm, p, start)
        cells = []
        for k in ("travel", "all"):
            d = (E[k] - E0[k])
            lo, hi = bt(d)
            cells += [f"{E[k].mean():.3f}", f"{d.mean():+.3f} [{lo:+.3f}, {hi:+.3f}]"]
        chi2, df, pv = wald(ma, terms)
        print(f"  | {lab} | " + " | ".join(cells) + f" | chi2 {chi2:.1f}, df {df}, p {pv:.3g} |")
    print(f"  HYPOTHESIS TERM {HYP}: {ma.params[HYP]:+.3f} (s.e. {ma.bse[HYP]:.3f}, p {ma.pvalues[HYP]:.3g})")

    # pooled elasticity, no hypothesis term (sensitivity)
    mp = poisson(y, with_travel(log_visits, interact=False), **cl["newsroom county (adopted)"])
    print(f"  SENSITIVITY, pooled (no hypothesis term): {mp.params['log_visits']:.3f} (s.e. {mp.bse['log_visits']:.3f})")

    # zero-visit pairs: how the elasticities move with their treatment
    print("  elasticity, urban / rural, by treatment of the zero-visit pairs:")
    alt = {"indicator + log visits where > 0 (adopted)": (bm, bn)}
    for lab, col in (("zeros set to log(1e-3) = -6.9 (before 2026-10-24)", np.log(p.visits.clip(lower=1e-3))),
                     ("log(visits + 1)", np.log1p(p.visits)),
                     ("log(visits + 10)", np.log(p.visits + 10)),
                     ("log(visits + 100)", np.log(p.visits + 100))):
        (a1, _), (a2, _) = split(poisson(y, with_travel(col.values, zero_col=False)))
        alt[lab] = (a1, a2)
    Xz = with_travel(log_visits, zero_col=False)[pos]
    (a1, _), (a2, _) = split(poisson(y[pos], Xz.loc[:, Xz.abs().sum() > 0]))
    alt["zero-visit pairs dropped"] = (a1, a2)
    for lab, (v1, v2) in alt.items():
        print(f"    {lab:52s} {v1:.3f} / {v2:.3f}")

    # equivalence: travel beyond gravity (pooled, as it was used; travel model's od_predicted.csv)
    ok = np.isfinite(p.ratio.values)
    floor = np.log(p.visits.clip(lower=1e-3)).values
    mr = poisson(y[ok], with_travel(np.log(p.ratio.clip(lower=1e-3)).values, zero_col=False, interact=False)[ok])
    mf = poisson(y[ok], with_travel(floor, zero_col=False, interact=False)[ok])
    print(f"  pooled log(visits / travel-model prediction), zeros at 1e-3 (\"travel beyond gravity\", before "
          f"2026-10-24; od_predicted.csv): {mr.params['log_visits']:.3f}; pooled log visits with the same floor "
          f"{mf.params['log_visits']:.3f}. Given the same terms and fixed effects the two are one quantity (they differ "
          f"only where od_predicted.csv's visits differ from the adopted outcome)")

    # leave one newsroom county out: range of each elasticity
    loo = {}
    for f in sorted(set(p.i)):
        k = (p.i != f).values
        Xk = Xa[k].drop(columns=[f"o_{f}"])
        Xk = Xk.loc[:, Xk.abs().sum() > 0]
        mk = poisson(y[k], Xk, start_params=ma.params[Xk.columns].values)
        loo[f] = (mk.params["log_visits"], mk.params["log_visits"] + mk.params[HYP])
    L = pd.DataFrame(loo, index=["urban", "rural"]).T
    print(f"  leave one newsroom county out ({len(L)} fits):")
    for col in L.columns:
        s = L[col]
        print(f"    {col:9s} {s.min():.3f} to {s.max():.3f}; median {s.median():.3f}")

    # NOT ADOPTED, for the record
    lv1 = np.log1p(p.visits.values)
    nd = poisson(y, pd.concat([pd.DataFrame({"t": lv1}), O], axis=1), **cl["newsroom county (adopted)"])
    db = poisson(y, pd.concat([pd.DataFrame({"t": lv1, "log_dist": X.log_dist.values, "adjacent": p.adjacent.values}),
                               O], axis=1), **cl["newsroom county (adopted)"])
    mnc = poisson(y, with_travel(log_visits, interact=False, drop=BLOCKS["commuting block (out + in)"]))
    print("  NOT ADOPTED -- do not quote (without the controls, distance loads onto travel; pooled elasticities):")
    print(f"    fixed effects + log(1 + visits), no distance terms (border_coverage_test.py family):  "
          f"{nd.params['t']:.3f} (s.e. {nd.bse['t']:.3f})")
    print(f"    fixed effects + log(1 + visits) + log distance + border:                            "
          f"{db.params['t']:.3f} (s.e. {db.bse['t']:.3f})")
    print(f"    pooled, without the commuting block:                                                "
          f"{mnc.params['log_visits']:.3f}")
    p[["i", "j", "dist", "adjacent", "ratio", "visits", "stories", "pred_gravity", "pred_travel"]].to_csv(
        root / f"analysis/coverage_predicted_{version}.csv", index=False)
