"""Statewide coverage ("spillover") model, Missouri, March 2026: which other counties each county's newsrooms cover.

Story-county pairs from newsrooms in county i about county j (i != j): a story counts once for each Missouri county it
is centred in or mentions (the story map's two layers per article, coverage/storymap/statewide_2026_03_articles.json,
Mizzou-Missouri-State dataset, without The Maneater and CoMoBuzz). PPML with origin fixed effects, robust errors, two models:

  gravity      exactly the travel model (gravity_terms.py): doubly constrained -- a fixed effect for every newsroom
               county and every county covered -- with the same distance and border terms
  + travel     gravity plus log of residents' travel i -> j beyond what gravity predicts for travel
               (actual / predicted, travel_model.py, Jan-Sep): does coverage follow the places residents really go?

Run for all newsrooms and without broadcasters. Output: coverage_predicted_<version>.csv
"""
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import FACTORS, design, root  # noqa: E402  the same gravity terms as the travel model

cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str}).set_index("fips")
tp = pd.read_csv(root / "analysis/od_predicted.csv", dtype={"i": str, "j": str}).set_index(["i", "j"])
data = json.load(open(root / "coverage/storymap/statewide_2026_03_articles.json"))
# The Maneater and CoMoBuzz are out of Boone's coverage, as on the maps (both are Boone outlets)
from excluded_outlets import EXCLUDE  # one list for every county count
data["articles"] = [a for a in data["articles"] if a["publisher"] not in EXCLUDE]
by_name = {n.lower(): f for f, n in cov.name.items()}
by_name.update({"st. louis": "29189", "st louis": "29189", "st. louis city": "29510", "saint louis": "29189"})


def county_fips(name):
    n = (name or "").lower().replace(" county", "").strip()
    return by_name.get(n) or by_name.get(n.replace("saint ", "st. "))


unmatched = Counter(a["publisher_county"] for a in data["articles"] if not county_fips(a["publisher_county"]))
print("publisher counties not matched (articles):", dict(unmatched))

pairs = tp.reset_index()[["i", "j", "dist", "adjacent", "ratio"]].copy()
for version, keep in (("all", lambda a: True), ("no_broadcast", lambda a: "broadcast" not in (a["publisher_type"] or ""))):
    arts = [a for a in data["articles"] if keep(a) and county_fips(a["publisher_county"])]
    n = Counter()
    for a in arts:
        i = county_fips(a["publisher_county"])
        for j in a["counties"]:
            if j.startswith("29") and j != i:
                n[(i, j)] += 1
    origins = sorted({county_fips(a["publisher_county"]) for a in arts})
    p = pairs[pairs.i.isin(origins)].copy()
    p["stories"] = [n.get((i, j), 0) for i, j in zip(p.i, p.j)]
    p = p[p.groupby("i").stories.transform("sum") > 0]
    Xd = design(p)
    X, O = Xd[FACTORS], Xd[[c for c in Xd.columns if c.startswith(("o_", "d_"))]]
    y = p.stories.astype(float)
    print(f"\n## {version}: {len(arts):,} stories from {len(origins)} newsroom counties; "
          f"{int(y.sum()):,} story-county pairs outside the newsroom's county")
    for label, Xm in (("gravity", pd.concat([X, O], axis=1)),
                      ("+ travel", pd.concat([X.assign(log_travel_beyond_gravity=np.log(p.ratio.clip(lower=1e-3).values)), O], axis=1))):
        m = sm.GLM(y, Xm, family=sm.families.Poisson()).fit(cov_type="HC1", maxiter=300)
        pred = m.predict(Xm)
        r2 = np.corrcoef(y, pred)[0, 1] ** 2
        c = pd.DataFrame({"coef": m.params, "se": m.bse, "p": m.pvalues}).loc[[k for k in m.params.index if not k.startswith(("o_", "d_"))]]
        print(f"### {label}: explains {r2:.0%} of story-county pairs")
        print(c.round(3).to_string())
        p["pred_" + ("gravity" if label == "gravity" else "travel")] = pred.values
    p.to_csv(root / f"analysis/coverage_predicted_{version}.csv", index=False)
