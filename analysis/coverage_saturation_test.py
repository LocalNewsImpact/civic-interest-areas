"""Is coverage associated with travel LESS where the destination already has its own coverage?  EXPLORATORY additions
to the adopted coverage model, admitted only through the nested procedure.

Hypothesis (authors): residents travel to population centres by gravity, but newsrooms -- especially rural ones -- do not
follow them there in proportion, because the centre is already covered by its own newsrooms and broadcasters.

Pairs, stories and visits: coverage_predicted_<version>.csv, as coverage_model.py builds them (newsroom county =
excluded_outlets.home_fips; excluded_outlets.EXCLUDE left out; visits = gravity_terms.travel_visits, the adopted
outcome). Destination's own coverage (March):
  own_stories_j   stories by j's own newsrooms that are about j   (log1p)
  newsrooms_j     outlets in j with placed stories                 (log1p)
  broadcaster_j   j has a TV or radio newsroom
Base: the ADOPTED coverage specification (coverage_model.py) -- controls (distance block, border, commuting block),
newsroom-county and destination fixed effects, log visits where > 0, zero-visit indicator, hypothesis term log visits x
nonmetro newsroom county. The destination effects absorb each destination's overall draw, so what is tested is how the
association of stories with visits changes: log visits x the destination's own coverage. Coefficients: errors
clustered by newsroom county (a story counts once per county it names).

Held out (gravity_terms.loco folds: newsroom counties in 8 folds, seed 7): mean absolute share error (points) per
newsroom county. PRIMARY: destinations with 1%+ of the county's visits. Beside it: all destinations (dominated by
pairs with no stories). Intervals: 95%, 1,000 county draws (seed 7), county-paired for differences.
NESTED PROCEDURE (combined_marginal_test.py's, for coverage): inside each outer training set, every candidate (adopted,
adopted + each addition) is scored by an inner leave-county-out (7 folds of the training counties) on the primary
metric; (a) lowest inner error, (b) the selection rule: admit a candidate only if its inner county-paired gain interval
excludes zero, then the lowest inner error among those admitted, else the adopted model. The chosen candidate, fitted
on the training counties, scores the outer held-out counties. An addition is adopted only if the nested procedure's
outer held-out gain interval excludes zero. One-at-a-time held-out scores are printed beside, not used to adopt.
"""
import json
import sys
import warnings
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gravity_terms as gt  # noqa: E402
from gravity_terms import FACTORS, cov, design, root  # noqa: E402
from excluded_outlets import EXCLUDE, home_fips  # noqa: E402

warnings.filterwarnings("ignore")   # clustered covariance with fewer clusters than fixed-effect columns

data = json.load(open(root / "coverage/storymap/statewide_2026_03_articles.json"))
by_name = {n.lower(): f for f, n in cov.name.items()}
by_name.update({"st. louis": "29189", "st louis": "29189", "st. louis city": "29510", "saint louis": "29189"})


def fips_of(name):
    n = (name or "").lower().replace(" county", "").strip()
    return by_name.get(n) or by_name.get(n.replace("saint ", "st. "))


own, outlets, bcast = Counter(), defaultdict(set), set()
for a in data["articles"]:
    f = home_fips(a["publisher"], fips_of(a["publisher_county"]))
    if not f or a["publisher"] in EXCLUDE or not a["counties"]:
        continue
    outlets[f].add(a["publisher"])
    if "broadcast" in (a["publisher_type"] or ""):
        bcast.add(f)
    if f in a["counties"]:
        own[f] += 1


def boot(d, draws=1000, seed=7):
    d = pd.Series(d).dropna()
    rng = np.random.default_rng(seed)
    b = [d.iloc[rng.integers(0, len(d), len(d))].mean() for _ in range(draws)]
    return np.quantile(b, [0.025, 0.975])


def fitter(start):
    def fit(yy, XX):
        return np.asarray(sm.GLM(yy, XX, family=sm.families.Poisson()).fit(
            maxiter=300, start_params=start.reindex(XX.columns).fillna(0).values).params)
    return fit


def predict(y, X, o, train, test, fit):
    cc = X.columns[(X[train] != 0).any()]
    lin = X.loc[test, cc].values @ fit(y[train], X.loc[train, cc])
    lin = lin - pd.Series(lin).groupby(o[test]).transform("max").values
    return gt.shares(np.exp(lin), o[test])


def errors(ps, y, o, vs):
    """Per county: mean absolute share error (points), all destinations / destinations with 1%+ of visits."""
    ok = np.isfinite(ps)
    err = pd.Series(100 * np.abs(ps - gt.shares(y, o)))[ok]
    oo = pd.Series(o)[ok]
    return pd.DataFrame({"all": err.groupby(oo.values).mean(), "travel": err[vs[ok]].groupby(oo[vs[ok]].values).mean()})


for version in ("all", "no_broadcast"):
    p = pd.read_csv(root / f"analysis/coverage_predicted_{version}.csv", dtype={"i": str, "j": str})
    p = p[p.groupby("i").stories.transform("sum") > 0].reset_index(drop=True)
    pos = (p.visits > 0).values
    lv = np.where(pos, np.log(p.visits.where(pos, 1.0)), 0.0)
    own_j = np.log1p(np.array([own[j] for j in p.j], float))
    nr_j = np.log1p(np.array([len(outlets[j]) for j in p.j], float))
    bc_j = np.array([float(j in bcast) for j in p.j])
    nonmetro = 1 - cov.metro.reindex(p.i).values
    Xd = design(p)
    FE = Xd[[c for c in Xd.columns if c.startswith(("o_", "d_"))]]
    base = Xd[FACTORS].assign(log_visits=lv, zero_visits=(~pos).astype(float), log_visits_x_nonmetro=lv * nonmetro)
    adds = {
        "adopted (no saturation)": {},
        "+ x destination's own stories": {"lv_x_own": lv * own_j},
        "+ x destination's newsrooms": {"lv_x_newsrooms": lv * nr_j},
        "+ x destination has broadcaster": {"lv_x_broadcast": lv * bc_j},
        "+ x own stories, x own stories x nonmetro home": {"lv_x_own": lv * own_j,
                                                           "lv_x_own_x_nonmetro": lv * own_j * nonmetro},
        "+ x own stories, x broadcaster": {"lv_x_own": lv * own_j, "lv_x_broadcast": lv * bc_j},
    }
    Xc = {k: pd.concat([base.assign(**v), FE], axis=1) for k, v in adds.items()}
    y = p.stories.values.astype(float)
    o = p.i.values
    vs = gt.shares(p.visits.values, o) >= 0.01
    gi = pd.factorize(p.i)[0]
    print(f"\n# {version.replace('_', ' ')}: {p.i.nunique()} newsroom counties, {int(y.sum()):,} out-of-county story "
          f"pairs; pairs with no stories {(y == 0).mean():.0%} of all, {(y[vs] == 0).mean():.0%} of 1%+ of visits")
    full = {k: sm.GLM(y, X_, family=sm.families.Poisson()).fit(cov_type="cluster", cov_kwds={"groups": gi}, maxiter=300)
            for k, X_ in Xc.items()}
    start = {k: m.params for k, m in full.items()}
    ref = "adopted (no saturation)"

    # outer folds (gravity_terms.loco's), with the nested choice inside each training set
    counties = sorted(set(o))
    outer = {k: np.full(len(o), np.nan) for k in Xc}
    nested = {"lowest inner error": np.full(len(o), np.nan), "selection rule": np.full(len(o), np.nan)}
    for fold, f in enumerate(np.array_split(np.random.default_rng(7).permutation(counties), 8)):
        test = np.isin(o, f)
        train = ~test
        inner = {}
        for k, X_ in Xc.items():
            outer[k][test] = predict(y, X_, o, train, test, fitter(start[k]))
            ps = gt.loco(y[train], X_[train].reset_index(drop=True), o[train], folds=7, seed=7, fit=fitter(start[k]))
            inner[k] = errors(ps, y[train], o[train], vs[train]).travel
        best = min(inner, key=lambda k: inner[k].mean())
        admitted = [k for k in Xc if k != ref and boot(inner[ref] - inner[k])[0] > 0]
        rule = min(admitted, key=lambda k: inner[k].mean()) if admitted else ref
        nested["lowest inner error"][test] = outer[best][test]
        nested["selection rule"][test] = outer[rule][test]
        print(f"  outer fold {fold + 1}: lowest inner error: {best} ({inner[best].mean():.3f}; adopted "
              f"{inner[ref].mean():.3f}); selection rule admits {admitted or 'none'} -> {rule}")
    E = {k: errors(v, y, o, vs) for k, v in outer.items()}
    E0 = E[ref]
    print("Held-out error, points [95%]; gain = adopted - model, county-paired (positive = lower error than adopted)")
    print("| Model / procedure | Primary: 1%+ of visits | Gain | All destinations | Gain | Saturation terms "
          "(coef, clustered s.e., p) |\n|---|---:|---:|---:|---:|---|")

    def row(label, e, terms=""):
        cells = []
        for k in ("travel", "all"):
            lo, hi = boot(e[k])
            cells.append(f"{e[k].mean():.3f} [{lo:.3f}, {hi:.3f}]")
            if e is E0:
                cells.append("—")
            else:
                d = E0[k] - e[k]
                dl, dh = boot(d)
                cells.append(f"{d.mean():+.3f} [{dl:+.3f}, {dh:+.3f}]")
        print(f"| {label} | " + " | ".join(cells) + f" | {terms} |")

    for k, m in full.items():
        t = [c for c in m.params.index if c.startswith("lv_x")]
        est = "; ".join(f"{c.replace('lv_x_', '')} {m.params[c]:+.3f} ({m.bse[c]:.3f}, p {m.pvalues[c]:.3f})" for c in t)
        if not t:
            est = (f"log visits {m.params['log_visits']:.3f} ({m.bse['log_visits']:.3f}); x nonmetro "
                   f"{m.params['log_visits_x_nonmetro']:+.3f} ({m.bse['log_visits_x_nonmetro']:.3f})")
        row(("one at a time (not nested): " if t else "") + k, E[k], est)
    for k, v in nested.items():
        e = errors(v, y, o, vs)
        row(f"NESTED: {k}", e, "")
        d = E0.travel - e.travel
        lo, hi = boot(d)
        print(f"   -> nested ({k}) primary gain {d.mean():+.3f} [{lo:+.3f}, {hi:+.3f}]: "
              f"{'interval excludes zero' if lo > 0 or hi < 0 else 'interval includes zero: no addition adopted'}")
    b = full["+ x own stories, x own stories x nonmetro home"].params
    print("Association of stories with visits (elasticity) by the destination's own stories, "
          "model '+ x own stories, x own stories x nonmetro home' (not adopted):")
    for n_ in (0, 20, 100, 500):
        lo_ = np.log1p(n_)
        metro = b.log_visits + b.lv_x_own * lo_
        rural = metro + b.log_visits_x_nonmetro + b.lv_x_own_x_nonmetro * lo_
        print(f"    {n_} own stories: metro home {metro:.2f}, nonmetro home {rural:.2f}")
