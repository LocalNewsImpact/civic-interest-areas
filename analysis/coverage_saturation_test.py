"""Is coverage associated with travel LESS where the destination already has its own coverage?

Hypothesis (user): residents travel to population centres by gravity, but newsrooms -- especially rural ones -- do not
follow them there in proportion, because the centre is already covered by its own newsrooms and broadcasters.

Pairs: newsroom county i -> other Missouri county j, as in coverage_model.py (stories from coverage_predicted_*.csv;
a newsroom's county is excluded_outlets.home_fips; excluded_outlets.EXCLUDE left out). Visits_ij = residents' visits
Jan-Sep 2026, pass-through discounted (od_predicted.csv).
Destination's own coverage (March):
  own_stories_j   stories by j's own newsrooms that are about j   (log1p)
  newsrooms_j     outlets in j with placed stories                 (log1p)
  broadcaster_j   j has a TV or radio newsroom
Base model: the ADOPTED coverage specification (coverage_model.py) -- gravity terms, newsroom-county and destination
fixed effects, log visits where > 0, log visits x nonmetropolitan newsroom county (adopted 2026-10-24 from this test)
and a zero-visit indicator. The destination effects absorb each destination's overall draw, so what is tested is how
the association of stories with visits changes: log visits x own coverage (and x own coverage x nonmetro home). The
pooled model without the nonmetro interaction is scored against it. Errors clustered by newsroom county (a story counts once per county it names).
Held out: each newsroom county left out in turn, its out-of-county story shares predicted from the rest (its own
fixed effect cancels out of its shares). Scored on destination sets NOT chosen by the held-out stories:
  all     mean absolute share error (points) over every destination
  travel  over destinations with 1%+ of the county's visits
Interval: 95% bootstrap over newsroom counties (2,000 draws) of the mean error and of the paired difference from
the base model.
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
from gravity_terms import FACTORS, cov, design, root  # noqa: E402
from excluded_outlets import EXCLUDE, home_fips  # noqa: E402

warnings.filterwarnings("ignore")   # clustered covariance with fewer clusters than fixed-effect columns
rng = np.random.default_rng(0)

data = json.load(open(root / "coverage/storymap/statewide_2026_03_articles.json"))
by_name = {n.lower(): f for f, n in cov.name.items()}
by_name.update({"st. louis": "29189", "st louis": "29189", "st. louis city": "29510", "saint louis": "29189"})


def fips_of(name):
    n = (name or "").lower().replace(" county", "").strip()
    return by_name.get(n) or by_name.get(n.replace("saint ", "st. "))


own, outlets, bcast = Counter(), defaultdict(set), set()
for a in data["articles"]:
    filed = fips_of(a["publisher_county"])
    if not filed or a["publisher"] in EXCLUDE or not a["counties"]:
        continue
    f = home_fips(a["publisher"], filed)
    outlets[f].add(a["publisher"])
    if "broadcast" in (a["publisher_type"] or ""):
        bcast.add(f)
    if f in a["counties"]:
        own[f] += 1
tp = pd.read_csv(root / "analysis/od_predicted.csv", dtype={"i": str, "j": str})[["i", "j", "visits", "dist", "adjacent"]]


def boot(d):
    d = np.asarray(d)
    b = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
    return d.mean(), np.percentile(b, 2.5), np.percentile(b, 97.5)


for version in ("all", "no_broadcast"):
    cp = pd.read_csv(root / f"analysis/coverage_predicted_{version}.csv", dtype={"i": str, "j": str})[["i", "j", "stories"]]
    p = cp.merge(tp, on=["i", "j"]).reset_index(drop=True)
    p = p[p.groupby("i").stories.transform("sum") > 0].reset_index(drop=True)
    pos = (p.visits > 0).values
    lv = np.where(pos, np.log(p.visits.where(pos, 1.0)), 0.0)
    own_j = np.log1p(np.array([own[j] for j in p.j], float))
    nr_j = np.log1p(np.array([len(outlets[j]) for j in p.j], float))
    bc_j = np.array([float(j in bcast) for j in p.j])
    rural_i = 1 - cov.metro.reindex(p.i).values
    Xd = design(p)
    base = Xd[FACTORS].assign(log_visits=lv, log_visits_x_nonmetro=lv * rural_i, zero_visits=(~pos).astype(float))
    FE = Xd[[c for c in Xd.columns if c.startswith(("o_", "d_"))]]
    specs = {
        "adopted: log visits x nonmetro home (no saturation)": base,
        "pooled: no nonmetro interaction (adopted before 2026-10-24)": base.drop(columns=["log_visits_x_nonmetro"]),
        "x destination's own stories": base.assign(lv_x_own=lv * own_j),
        "x destination's newsrooms": base.assign(lv_x_newsrooms=lv * nr_j),
        "x destination has broadcaster": base.assign(lv_x_broadcast=lv * bc_j),
        "x own stories, x own stories x nonmetro home": base.assign(lv_x_own=lv * own_j,
                                                                   lv_x_own_x_rural=lv * own_j * rural_i),
        "x own stories + x broadcaster": base.assign(lv_x_own=lv * own_j, lv_x_broadcast=lv * bc_j),
    }
    y = p.stories.values.astype(float)
    gi = pd.factorize(p.i)[0]
    vshare = (p.visits / p.groupby("i").visits.transform("sum")).values
    print(f"\n# {version.replace('_', ' ')}: {p.i.nunique()} newsroom counties, {int(y.sum()):,} out-of-county story pairs")
    print("Held-out error, points: mean absolute share error per newsroom county, averaged; [95% bootstrap over counties];"
          " change = paired difference from the adopted model")
    print("| Model | Deviance | Held-out, all destinations | change | Held-out, 1%+ of visits | change |"
          " Saturation terms (coef, clustered s.e., p) |\n|---|---:|---:|---:|---:|---:|---|")
    ref = {}
    for label, X in specs.items():
        Xm = pd.concat([X, FE], axis=1)
        m = sm.GLM(y, Xm, family=sm.families.Poisson()).fit(cov_type="cluster", cov_kwds={"groups": gi}, maxiter=300)
        e_all, e_tr = {}, {}
        for f in p.i.unique():
            tr, te = (p.i != f).values, (p.i == f).values
            Xt = Xm.drop(columns=[f"o_{f}"])
            mt = sm.GLM(y[tr], Xt[tr], family=sm.families.Poisson()).fit(
                maxiter=200, start_params=m.params[Xt.columns].values)
            pr = mt.predict(Xt[te]).values
            err = 100 * np.abs(pr / pr.sum() - y[te] / max(y[te].sum(), 1))
            e_all[f] = err.mean()
            e_tr[f] = err[vshare[te] >= 0.01].mean()
        ea, et = pd.Series(e_all), pd.Series(e_tr)
        if not ref:
            ref = {"all": ea, "tr": et}
        cells = []
        for e, r in ((ea, ref["all"]), (et, ref["tr"])):
            mu, lo, hi = boot(e)
            cells.append(f"{mu:.3f} [{lo:.3f}, {hi:.3f}]")
            if e is r:
                cells.append("—")
            else:
                d, dl, dh = boot((e - r).reindex(e.index))
                cells.append(f"{d:+.3f} [{dl:+.3f}, {dh:+.3f}]")
        terms = [c for c in X.columns if c.startswith("lv_x")]
        est = "; ".join(f"{t.replace('lv_x_', '')} {m.params[t]:+.3f} ({m.bse[t]:.3f}, p {m.pvalues[t]:.3f})" for t in terms)
        if not terms:
            est = f"log visits {m.params['log_visits']:.3f} ({m.bse['log_visits']:.3f})"
            if "log_visits_x_nonmetro" in m.params:
                est += (f"; x nonmetro {m.params['log_visits_x_nonmetro']:+.3f} ({m.bse['log_visits_x_nonmetro']:.3f}, "
                        f"p {m.pvalues['log_visits_x_nonmetro']:.3f})")
        print(f"| {label} | {m.deviance:,.0f} | " + " | ".join(cells) + f" | {est} |")
        if label == "x own stories, x own stories x nonmetro home":
            b = m.params
            resp = []
            for o in (0, 20, 100, 500):
                lo_ = np.log1p(o)
                metro = b.log_visits + b.lv_x_own * lo_
                rural = metro + b.log_visits_x_nonmetro + b.lv_x_own_x_rural * lo_
                resp.append(f"{o} own stories: metro home {metro:.2f}, rural home {rural:.2f}")
            sat = resp
    print("Association of stories with visits (elasticity) by the destination's own stories, "
          "model 'x own stories, x own stories x nonmetro home':")
    for r in sat:
        print("   ", r)
