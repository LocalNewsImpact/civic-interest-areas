"""Does coverage fall off at non-bordering counties more than travel does?  Statewide, Missouri.

Pairs: newsroom county i -> county j (newsroom counties as in coverage_model.py). Ring = county boundaries apart (1 borders, 2 one county
between, 3+). Travel = residents' visits Jan-Sep 2026, the travel model's adopted outcome (gravity_terms.travel_visits:
visits_statewide, pass-through discounted). Both from coverage_predicted_<version>.csv (coverage_model.py).
  1. Shares by ring: per newsroom county, the share of its residents' out-of-county visits and of its newsrooms'
     out-of-county story pairs going to each ring; medians across newsroom counties.
  2. Same travel, different ring: story share by bands of travel share, ring 1 vs ring 2 vs ring 3+.
  3. Model: Poisson regression (PPML) of stories with newsroom-county and covered-county fixed effects on log(1 + visits),
     ring, and log visits x not-bordering -- is coverage associated with travel differently beyond the border?
     SPECIFICATION LABEL: border test, NO distance terms -- not the adopted coverage model (coverage_model.py). Without
     distance, log visits carries distance as well as travel, so its coefficient (about 0.6) is not the coverage
     elasticity; quote only the adopted 0.36. Errors clustered by newsroom county: a story counts once for each county it
     names, so pairs from one newsroom county are not independent.
"""
import sys
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import FIPS, all_pairs, cov, root  # noqa: E402

adj = all_pairs()
nbr = {f: set(adj[(adj.i == f) & (adj.adjacent == 1)].j) for f in FIPS}


def rings(f):
    d, q = {f: 0}, deque([f])
    while q:
        x = q.popleft()
        for y in nbr[x]:
            if y not in d:
                d[y] = d[x] + 1; q.append(y)
    return d


R = {f: rings(f) for f in FIPS}
for version in ("all", "no_broadcast"):
    cp = pd.read_csv(root / f"analysis/coverage_predicted_{version}.csv", dtype={"i": str, "j": str})
    p = cp[["i", "j", "stories", "visits"]].copy()
    p["ring"] = [min(R[i][j], 3) for i, j in zip(p.i, p.j)]
    p["visit_share"] = p.visits / p.groupby("i").visits.transform("sum")
    p["story_share"] = p.stories / p.groupby("i").stories.transform("sum")
    print(f"\n# {version.replace('_', ' ')}: {p.i.nunique()} newsroom counties, {int(p.stories.sum()):,} out-of-county story pairs")
    by = p.groupby(["i", "ring"])[["visit_share", "story_share"]].sum().reset_index()
    t = by.groupby("ring")[["visit_share", "story_share"]].median()
    t["stories per visit share"] = t.story_share / t.visit_share
    print("1. median share across newsroom counties, by ring (1 = borders):")
    print(t.round(3).to_string())
    bands = [0, .005, .01, .02, .05, .10, 1]
    p["band"] = pd.cut(p.visit_share, bands, labels=["<0.5%", "0.5-1%", "1-2%", "2-5%", "5-10%", "10%+"])
    t2 = p.pivot_table(index="band", columns="ring", values="story_share", aggfunc="mean", observed=False)
    n2 = p.pivot_table(index="band", columns="ring", values="story_share", aggfunc="size", observed=False)
    print("2. mean story share by travel band (rows) and ring (columns); pairs in brackets:")
    print("\n".join(f"   {b:>7}: " + "  ".join(f"ring {r}: {t2.loc[b, r]:.2%} ({int(n2.loc[b, r])})" for r in t2.columns)
                    for b in t2.index))
    X = pd.DataFrame({"log_visits": np.log1p(p.visits)})
    X["ring2"], X["ring3plus"] = (p.ring == 2).astype(float), (p.ring == 3).astype(float)
    X["log_visits_x_not_bordering"] = X.log_visits * (p.ring >= 2)
    O = pd.get_dummies(p.i, prefix="o").astype(float)
    D = pd.get_dummies(p.j, prefix="d", drop_first=True).astype(float)
    m = sm.GLM(p.stories.astype(float), pd.concat([X, O, D], axis=1), family=sm.families.Poisson()).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(p.i)[0]}, maxiter=300)
    c = pd.DataFrame({"coef": m.params, "se": m.bse, "p": m.pvalues}).loc[X.columns]
    print("3. model -- BORDER TEST SPECIFICATION, NO DISTANCE TERMS, NOT THE ADOPTED COVERAGE MODEL (do not quote as the"
          " elasticity; adopted: coverage_model.py)\n   newsroom-county and covered-county fixed effects; errors clustered"
          f" by newsroom county ({p.i.nunique()} clusters):")
    print(c.round(3).to_string())
    b, bx = m.params["log_visits"], m.params["log_visits_x_not_bordering"]
    lo, hi = m.conf_int().loc["log_visits_x_not_bordering"]
    print(f"   in this specification, 1% more visits is associated with {b:.2f}% more stories for bordering counties,"
          f" {b + bx:.2f}% for non-bordering (difference {bx:+.2f}, 95% CI {lo:+.2f} to {hi:+.2f})")
osage = R["29151"]
print("\nOsage to Boone:", osage["29019"], "boundaries apart; Osage to Cole:", osage["29051"])
