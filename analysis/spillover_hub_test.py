"""Does splitting OMB "metro central" into regional hubs and suburban central counties improve the spillover model?

Hub = a metro central county that draws more visits from other Missouri counties than its residents make elsewhere
(visitors in / residents out, Jan-Sep 2026): > 1.25 hub, < 1 suburban. Cole and Clay sit between the two thresholds,
so three variants are tested: A both hubs, B both suburban, C their own "balanced" group.
Model as spillover_by_type.py: quasi-binomial GLM across newsroom counties with 10+ placed stories (March),
spill ~ type + log population + residents' share of visits outside. Reported: hub - suburban difference (Wald),
deviance and Pearson dispersion, and actual vs predicted for Boone (the one study county that is a hub).
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

root = Path(__file__).resolve().parents[1]
cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str}).set_index("fips")
d = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str)
d = d[d["FIPS State Code"] == "29"]
omb = {"29" + r[11]: (("metro central" if r[12] == "Central" else "metro outlying") if r[5].startswith("Metropolitan")
                      else "micropolitan") for r in d.itertuples()}
cov["omb"] = [omb.get(f, "rural") for f in cov.index]
od = pd.read_csv(root / "analysis/od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
od = od[od.home_county != "OUT"]
away = od[od.home_county != od.dest_county]
cov["travel_out"] = away.groupby("home_county").visits.sum() / od.groupby("home_county").visits.sum()
cov["draw"] = away.groupby("dest_county").visits.sum() / away.groupby("home_county").visits.sum()
BORDER = {"29051": "Cole", "29047": "Clay"}


def classify(f, variant):
    if cov.omb[f] != "metro central":
        return cov.omb[f]
    if f in BORDER:
        return {"A": "hub", "B": "suburban central", "C": "balanced central"}[variant]
    return "hub" if cov.draw[f] > 1.25 else "suburban central" if cov.draw[f] < 1 else "balanced central"


data = json.load(open(root / "coverage/storymap/statewide_2026_03_articles.json"))
by_name = {n.lower(): f for f, n in cov.name.items()}
by_name.update({"st. louis": "29189", "st louis": "29189", "st. louis city": "29510"})
fips_of = lambda n: by_name.get((n or "").lower().replace(" county", "").strip())
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from spillover_common import NOT_LOCAL as EXCLUDE, home_fips  # one outlet set (EXCLUDE + CAMPUS) and HOME_COUNTY for every count
HUBS = ["29019"]   # Boone

for version, keep in (("all outlets", lambda a: True), ("print and digital", lambda a: "broadcast" not in (a["publisher_type"] or ""))):
    n = defaultdict(lambda: [0, 0])
    for a in data["articles"]:
        i = home_fips(a["publisher"], fips_of(a["publisher_county"]))
        if a["publisher"] in EXCLUDE or not i or not a["counties"] or not keep(a):
            continue
        n[i][0] += 1
        n[i][1] += any(c.startswith("29") and c != i for c in a["counties"])
    base = cov.join(pd.DataFrame(n, index=["placed", "spill"]).T, how="inner")
    base = base[base.placed >= 10].copy()
    base["stay"], base["rate"], base["log_pop"] = base.placed - base.spill, base.spill / base.placed, np.log(base.population)
    print(f"\n# {version}: {len(base)} newsroom counties")
    fits = {}
    for variant in ("OMB only", "A", "B", "C"):
        c = base.copy()
        c["type"] = c.omb if variant == "OMB only" else [classify(f, variant) for f in c.index]
        m = smf.glm("spill + stay ~ C(type, Treatment('rural')) + log_pop + travel_out", c,
                    family=sm.families.Binomial()).fit(scale="X2")
        c["pred"] = m.predict(c)
        fits[variant] = (m, c)
        line = f"## {variant}: deviance {m.deviance:,.0f}, dispersion {m.scale:.1f}"
        if variant != "OMB only":
            hub, sub = "C(type, Treatment('rural'))[T.hub]", "C(type, Treatment('rural'))[T.suburban central]"
            t = m.t_test(f"{hub} - {sub} = 0")
            line += (f"; hub vs suburban central: {float(np.squeeze(t.effect)):+.2f} on the log-odds scale "
                     f"(p {float(np.squeeze(t.pvalue)):.3f})")
            line += f"; groups {c.type.value_counts().reindex(['hub', 'suburban central', 'balanced central']).fillna(0).astype(int).to_dict()}"
        print(line)
    print("| Hub | Population | Stories | Touch another county | OMB only | A | B | C |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for f in HUBS:
        if f not in base.index:
            continue
        r = base.loc[f]
        preds = " | ".join(f"{fits[v][1].pred[f]:.0%}" for v in ("OMB only", "A", "B", "C"))
        print(f"| {cov.name[f]} | {int(r.population):,} | {int(r.placed)} | {r.rate:.0%} | {preds} |")
