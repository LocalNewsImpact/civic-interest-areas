"""Statewide coverage model, Missouri, March 2026: how stories from each county's newsrooms about other counties are
associated with residents' travel between the two counties.

DATA. Story-county pairs from newsrooms in county i about county j (i != j): a story counts once for each Missouri county
it is centred in or mentions (the story map's two layers per article, coverage/storymap/statewide_2026_03_articles.json,
Mizzou-Missouri-State dataset), excluded_outlets.EXCLUDE left out. A newsroom's county is excluded_outlets.home_fips:
the county it is filed under, except the HOME_COUNTY outlets (Mid Rivers Newsmagazine -> St. Charles, Greene County
Commonwealth -> Greene), whose stories count with their covered county as the newsroom county.

ADOPTED SPECIFICATION (the figures to quote). PPML; the travel model's gravity terms (gravity_terms.py) with a fixed
effect for every newsroom county and every county covered; plus
  log_visits              log residents' visits i -> j, Jan-Sep 2026, pass-through discounted (od_predicted.csv),
                          where visits > 0 (0 otherwise)
  log_visits_x_nonmetro   log_visits x nonmetropolitan newsroom county (USDA RUCC 4-9, county_covariates.metro = 0)
                          ADOPTED 2026-10-24 (coverage_saturation_test.py): held-out error on destinations with 1%+ of
                          visits -0.14 points (95% CI -0.22 to -0.06), all destinations a tie (+0.002)
  zero_visits             1 where no visit was recorded (201 of 13,110 Missouri pairs)
The elasticity -- the percentage difference in stories associated with 1% more visits, holding the gravity terms and
both sets of fixed effects fixed -- is reported for metro newsroom counties (log_visits) and nonmetro ones (log_visits
+ log_visits_x_nonmetro). It is an association, not an effect of travel on coverage. The pooled elasticity (no
interaction) is printed as a sensitivity.

STANDARD ERRORS. A story is counted once for each county it names, so the pairs from one newsroom county are not
independent: errors are clustered by newsroom county. Sensitivity: clustered by unordered county pair, and two-way by
newsroom county and county covered; robust (HC1, independent pairs) for reference only.

"Travel beyond gravity", log(visits / travel-model prediction), was used before 2026-10-24. The prediction is a function
of the same gravity terms and fixed effects, so given them the two coefficients are the same quantity (they differ only
through the 1e-3 floor on zero-visit pairs and the travel model's own coefficients); both are printed.

NOT ADOPTED, printed for the record so the earlier figures can be traced: fixed effects + log(1 + visits) with no
distance terms (0.7-0.8, the border_coverage_test.py family) and + log distance + border (0.52).

Run for all newsrooms and without broadcasters. Output: coverage_predicted_<version>.csv (pred_gravity: gravity terms
only; pred_travel: adopted specification).
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
from gravity_terms import FACTORS, design, root  # noqa: E402  the same gravity terms as the travel model
from excluded_outlets import EXCLUDE, home_fips  # noqa: E402  one list for every county count

warnings.filterwarnings("ignore")   # clustered covariance with fewer clusters than fixed-effect columns

cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str}).set_index("fips")
tp = pd.read_csv(root / "analysis/od_predicted.csv", dtype={"i": str, "j": str}).set_index(["i", "j"])
data = json.load(open(root / "coverage/storymap/statewide_2026_03_articles.json"))
data["articles"] = [a for a in data["articles"] if a["publisher"] not in EXCLUDE]
by_name = {n.lower(): f for f, n in cov.name.items()}
by_name.update({"st. louis": "29189", "st louis": "29189", "st. louis city": "29510", "saint louis": "29189"})


def county_name(f):
    return "St. Louis city" if f == "29510" else f"{cov.name[f]} County"


def county_fips(name):
    n = (name or "").lower().replace(" county", "").strip()
    return by_name.get(n) or by_name.get(n.replace("saint ", "st. "))


def newsroom_fips(a):
    """The newsroom's county: HOME_COUNTY where it applies, else the county the outlet is filed under."""
    filed = county_fips(a["publisher_county"])
    return home_fips(a["publisher"], filed) if filed else None


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


unmatched = Counter(a["publisher_county"] for a in data["articles"] if not county_fips(a["publisher_county"]))
print("publisher counties not matched (articles):", dict(unmatched))
moved = Counter(a["publisher"] for a in data["articles"] if county_fips(a["publisher_county"])
                and newsroom_fips(a) != county_fips(a["publisher_county"]))
print("stories counted with their HOME_COUNTY newsroom county:", dict(moved))

pairs = tp.reset_index()[["i", "j", "dist", "adjacent", "ratio", "visits"]].copy()
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
    print(f"\n## {version}: {len(arts):,} stories from {p.i.nunique()} newsroom counties; "
          f"{int(y.sum()):,} story-county pairs outside the newsroom's county; {len(p):,} county pairs, "
          f"{int((~pos).sum())} with no recorded visits ({int(y[~pos].sum())} story-county pairs on them)")

    # gravity terms only (no travel term): pred_gravity
    Xg = pd.concat([X, O], axis=1)
    p["pred_gravity"] = poisson(y, Xg).predict(Xg).values

    # ADOPTED: log visits, and log visits x nonmetropolitan newsroom county
    nonmetro = 1 - cov.metro.reindex(p.i).values
    cl = clusters(p)

    def with_travel(t, zero_col=True, interact=True):
        """Gravity terms + travel term t (+ zero-visit indicator) (+ t x nonmetro newsroom county) + fixed effects."""
        Z = X.assign(log_visits=t)
        if zero_col:
            Z = Z.assign(zero_visits=zero)
        if interact:
            Z = Z.assign(log_visits_x_nonmetro=t * nonmetro)
        return pd.concat([Z, O], axis=1)

    def split(m):
        """(metro elasticity, s.e.), (nonmetro elasticity, s.e.) from a fit with the interaction."""
        b_, V = m.params, m.cov_params()
        se_n = np.sqrt(V.loc["log_visits", "log_visits"] + V.loc["log_visits_x_nonmetro", "log_visits_x_nonmetro"]
                       + 2 * V.loc["log_visits", "log_visits_x_nonmetro"])
        return (b_["log_visits"], m.bse["log_visits"]), (b_["log_visits"] + b_["log_visits_x_nonmetro"], se_n)

    Xa = with_travel(log_visits)
    ma = poisson(y, Xa, **cl["newsroom county (adopted)"])
    p["pred_travel"] = ma.predict(Xa).values
    (bm, sm_), (bn, sn) = split(ma)
    r2 = np.corrcoef(y, p.pred_travel)[0, 1] ** 2
    n_m, n_n = int((cov.metro.reindex(p.i.unique()) == 1).sum()), int((cov.metro.reindex(p.i.unique()) == 0).sum())
    print(f"### ADOPTED: gravity terms + both fixed effects + log visits + log visits x nonmetro newsroom county + "
          f"zero-visit indicator; errors clustered by newsroom county ({p.i.nunique()} clusters); r^2 of fitted with "
          f"observed pairs {r2:.2f}")
    c = pd.DataFrame({"coef": ma.params, "se": ma.bse, "p": ma.pvalues}).loc[
        FACTORS + ["log_visits", "log_visits_x_nonmetro", "zero_visits"]]
    print(c.round(3).to_string())
    for lab, (b, se), k_ in (("metro newsroom counties", (bm, sm_), n_m), ("nonmetro newsroom counties", (bn, sn), n_n)):
        print(f"ELASTICITY (adopted, {version}), {lab} ({k_}): {b:.3f}, s.e. {se:.3f}, 95% CI {b - 1.96 * se:.2f} to "
              f"{b + 1.96 * se:.2f}. 1% more visits is associated with {b:.2f}% more stories; twice the visits, "
              f"{2 ** b:.2f} times the stories")
    print("  s.e. by clustering, metro / nonmetro (a story counts once per county it names; pairs are not independent):")
    for lab, kw in cl.items():
        (_, a1), (_, a2) = (bm, sm_), (bn, sn)
        if not lab.startswith("newsroom county"):
            (_, a1), (_, a2) = split(poisson(y, Xa, **kw))
        print(f"    {lab:44s} {a1:.3f} / {a2:.3f}")

    # pooled elasticity, no interaction (sensitivity; the adopted specification before the rural-home term)
    mp = poisson(y, with_travel(log_visits, interact=False), **cl["newsroom county (adopted)"])
    print(f"  SENSITIVITY, pooled (no nonmetro interaction): {mp.params['log_visits']:.3f} "
          f"(s.e. {mp.bse['log_visits']:.3f})")

    # zero-visit pairs: how the elasticities move with their treatment
    print("  elasticity, metro / nonmetro, by treatment of the zero-visit pairs:")
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

    # equivalence: travel beyond gravity (pooled, as it was used)
    floor = np.log(p.visits.clip(lower=1e-3)).values
    mr = poisson(y, with_travel(np.log(p.ratio.clip(lower=1e-3)).values, zero_col=False, interact=False))
    mf = poisson(y, with_travel(floor, zero_col=False, interact=False))
    print(f"  pooled log(visits / travel-model prediction), zeros at 1e-3 (\"travel beyond gravity\", before "
          f"2026-10-24): {mr.params['log_visits']:.3f}; pooled log visits with the same floor "
          f"{mf.params['log_visits']:.3f}. Given the same gravity terms and fixed effects the two are one quantity")

    # leave one newsroom county out
    loo = {}
    for f in sorted(set(p.i)):
        k = (p.i != f).values
        Xk = Xa[k].drop(columns=[f"o_{f}"])
        Xk = Xk.loc[:, Xk.abs().sum() > 0]
        mk = poisson(y[k], Xk, start_params=ma.params[Xk.columns].values)
        loo[f] = (mk.params["log_visits"], mk.params["log_visits"] + mk.params["log_visits_x_nonmetro"])
    L = pd.DataFrame(loo, index=["metro", "nonmetro"]).T
    print(f"  leave one newsroom county out ({len(L)} fits):")
    for col in L.columns:
        s = L[col]
        lo_f, hi_f = s.idxmin(), s.idxmax()
        print(f"    {col:9s} {s.min():.3f} (without {county_name(lo_f)}, {int(p[p.i == lo_f].stories.sum())} story-county "
              f"pairs) to {s.max():.3f} (without {county_name(hi_f)}, {int(p[p.i == hi_f].stories.sum())}); "
              f"median {s.median():.3f}")

    # NOT ADOPTED, for the record
    lv1 = np.log1p(p.visits.values)
    nd = poisson(y, pd.concat([pd.DataFrame({"t": lv1}), O], axis=1), **cl["newsroom county (adopted)"])
    db = poisson(y, pd.concat([pd.DataFrame({"t": lv1, "log_dist": np.log(p.dist.values), "adjacent": p.adjacent.values}),
                               O], axis=1), **cl["newsroom county (adopted)"])
    nc = [t for t in FACTORS if not t.startswith("commute")]
    mnc = poisson(y, pd.concat([X[nc].assign(log_visits=log_visits, zero_visits=zero), O], axis=1))   # pooled
    print("  NOT ADOPTED -- do not quote (without the gravity terms, distance loads onto travel):")
    print(f"    fixed effects + log(1 + visits), no distance terms (border_coverage_test.py family):  "
          f"{nd.params['t']:.3f} (s.e. {nd.bse['t']:.3f})")
    print(f"    fixed effects + log(1 + visits) + log distance + border:                            "
          f"{db.params['t']:.3f} (s.e. {db.bse['t']:.3f})")
    print(f"    pooled, without the two commuting terms:                                            "
          f"{mnc.params['log_visits']:.3f}")
    p[["i", "j", "dist", "adjacent", "ratio", "stories", "pred_gravity", "pred_travel"]].to_csv(
        root / f"analysis/coverage_predicted_{version}.csv", index=False)
