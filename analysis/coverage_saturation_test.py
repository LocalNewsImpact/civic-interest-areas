"""Does coverage follow travel LESS when the destination already has its own coverage?

Hypothesis (user): residents travel to population centres by gravity, but newsrooms -- especially rural ones -- do not
follow them there in proportion, because the centre is already covered by its own newsrooms and broadcasters.
Pairs: newsroom county i -> other Missouri county j. Stories_ij = March 2026 story-county pairs (coverage_predicted_*).
Visits_ij = residents' visits Jan-Sep 2026, pass-through discounted (od_predicted.csv).
Destination's own coverage (March, The Maneater and CoMoBuzz excluded):
  own_stories_j   stories by j's own newsrooms that are about j   (log1p)
  newsrooms_j     outlets in j with placed stories                 (log1p)
  broadcaster_j   j has a TV or radio newsroom
Model: Poisson (PPML) with newsroom-county and destination fixed effects -- they absorb each destination's overall draw,
so what is tested is how the RESPONSE to travel changes: log visits x own coverage (and x rural home county).
Scored by leave-one-newsroom-county-out: predict each county's out-of-county story shares from the rest; mean absolute
error in percentage points over its destinations with 1%+ of visits or 2+ stories.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import cov, root  # noqa: E402

data = json.load(open(root / "coverage/storymap/statewide_2026_03_articles.json"))
by_name = {n.lower(): f for f, n in cov.name.items()}
by_name.update({"st. louis": "29189", "st louis": "29189", "st. louis city": "29510"})
fips_of = lambda n: by_name.get((n or "").lower().replace(" county", "").strip())
EXCLUDE = {"The Maneater", "CoMoBuzz"}
own, outlets, bcast = Counter(), defaultdict(set), set()
for a in data["articles"]:
    f = fips_of(a["publisher_county"])
    if not f or a["publisher"] in EXCLUDE or not a["counties"]:
        continue
    outlets[f].add(a["publisher"])
    if "broadcast" in (a["publisher_type"] or ""):
        bcast.add(f)
    if f in a["counties"]:
        own[f] += 1
tp = pd.read_csv(root / "analysis/od_predicted.csv", dtype={"i": str, "j": str})[["i", "j", "visits", "dist", "adjacent"]]

for version in ("all", "no_broadcast"):
    cp = pd.read_csv(root / f"analysis/coverage_predicted_{version}.csv", dtype={"i": str, "j": str})[["i", "j", "stories"]]
    p = cp.merge(tp, on=["i", "j"]).reset_index(drop=True)
    p = p[p.groupby("i").stories.transform("sum") > 0].reset_index(drop=True)
    lv = np.log1p(p.visits.values)
    own_j = np.log1p(np.array([own[j] for j in p.j], float))
    nr_j = np.log1p(np.array([len(outlets[j]) for j in p.j], float))
    bc_j = np.array([float(j in bcast) for j in p.j])
    rural_i = 1 - cov.metro.reindex(p.i).values
    base = pd.DataFrame({"log_visits": lv, "log_dist": np.log(p.dist.values), "adjacent": p.adjacent.values})
    FE = pd.concat([pd.get_dummies(p.i, prefix="o").astype(float),
                    pd.get_dummies(p.j, prefix="d", drop_first=True).astype(float)], axis=1)
    specs = {
        "travel only (no saturation)": base,
        "x destination's own stories": base.assign(lv_x_own=lv * own_j),
        "x destination's newsrooms": base.assign(lv_x_newsrooms=lv * nr_j),
        "x destination has broadcaster": base.assign(lv_x_broadcast=lv * bc_j),
        "x own stories, x rural home, x both": base.assign(lv_x_own=lv * own_j, lv_x_rural=lv * rural_i,
                                                          lv_x_own_x_rural=lv * own_j * rural_i),
        "x own stories + x broadcaster": base.assign(lv_x_own=lv * own_j, lv_x_broadcast=lv * bc_j),
    }
    y = p.stories.values.astype(float)
    print(f"\n# {version.replace('_', ' ')}: {p.i.nunique()} newsroom counties, {int(y.sum()):,} out-of-county story pairs")
    print("| Model | Deviance | Leave-one-county-out error (points) | Saturation terms (coef, p) |\n|---|---:|---:|---|")
    for label, X in specs.items():
        Xm = pd.concat([X, FE], axis=1)
        m = sm.GLM(y, Xm, family=sm.families.Poisson()).fit(cov_type="HC1", maxiter=300)
        errs = []
        for f in p.i.unique():
            tr, te = p.i != f, (p.i == f).values
            # the held-out county's own fixed effect cancels out of its shares, so it is dropped
            Xt = Xm.drop(columns=[f"o_{f}"])
            mt = sm.GLM(y[tr.values], Xt[tr.values], family=sm.families.Poisson()).fit(maxiter=200)
            pr = mt.predict(Xt[te])
            share_p, share_y = pr / pr.sum(), y[te] / max(y[te].sum(), 1)
            sel = (p.visits[te] / p.visits[te].sum() >= 0.01).values | (y[te] >= 2)
            errs += list(100 * np.abs(share_p - share_y)[sel])
        terms = [c for c in X.columns if c.startswith("lv_x")]
        est = "; ".join(f"{t.replace('lv_x_', '')} {m.params[t]:+.3f} ({m.pvalues[t]:.3f})" for t in terms)
        print(f"| {label} | {m.deviance:,.0f} | {np.mean(errs):.2f} | {est} |")
        if label == "x own stories, x rural home, x both":
            b = m.params
            for o in (0, 20, 100, 500):
                lo = np.log1p(o)
                metro = b.log_visits + b.lv_x_own * lo
                rural = metro + b.lv_x_rural + b.lv_x_own_x_rural * lo
                print(f"    response of stories to visits, destination with {o} stories of its own: "
                      f"metro home {metro:.2f}, rural home {rural:.2f}")
