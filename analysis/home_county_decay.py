"""How interest in home-county news falls with distance from home, from the home outlets' own coverage (Missouri School of
Journalism analysis, March 2026, after the grounding gate): for each study town, the stories ITS OWN outlets (based in
the town; OWN_TOWN=0: every outlet in the home county) locate in each 3 km hexagon of the home county (the market maps' credit: central place 1, other places 0.5, Sports half),
per hexagon, by distance from the town. Fitted: density ~ (distance)^-beta, Poisson on distance bands, every study town
of every region pooled (one level per town). Compared with the decay of residents' travel in other counties.
Writes analysis/home_county_decay.csv."""
import math
import os
import runpy
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

root = Path(__file__).resolve().parents[1]
os.environ["TIE_LIB"] = "1"
OWN_TOWN = os.environ.get("OWN_TOWN", "1") == "1"      # 1: the town's own outlets; 0: every outlet in the home county
rows = []
for region in ("columbia", "springfield", "cape", "kirksville", "joplin", "kansascity", "stjoseph"):
    sys.argv = ["tie_footprint.py", region]
    ns = runpy.run_path(str(root / "analysis/tie_footprint.py"), run_name="tie_lib")
    centre, hex_county, credit, by_outlet = ns["centre"], ns["hex_county"], ns["credit"], ns["by_outlet"]
    kx = 111.32 * math.cos(math.radians(38.7)); ky = 110.57
    for town, home in ns["STUDY"].items():
        hh = ns["home_hexes_of"][town]
        if not hh:
            continue
        cx = np.mean([centre[k][0] for k in hh if k in centre]); cy = np.mean([centre[k][1] for k in hh if k in centre])
        dens = defaultdict(float)
        # the town's OWN outlets (based in the town): other towns' papers in the county cover their own towns, which is
        # not this town's residents' interest (the pooled county fit read Centralia's paper as Columbia's interest)
        own = [o for o, pg in ns["outlet_place"].items() if pg == ns["HOME_PLACE"][town] and o not in ns["EXCLUDE"]]
        if OWN_TOWN and not own:
            continue
        for o, al in by_outlet.items():
            if (o not in own) if OWN_TOWN else (ns["fips_of"](al[0]["publisher_county"]) != home or o in ns["EXCLUDE"]):
                continue
            for a in al:
                sw = 0.5 if ns["cin"].get(a["id"]) == "Sports" else 1
                for k, w in credit.get(a["id"], {}).items():
                    if hex_county.get(k) == home:
                        dens[k] += sw * w
        if not dens:
            continue
        for k, c_ in hex_county.items():
            if c_ != home or k not in centre:
                continue
            d = math.hypot((centre[k][0] - cx) * kx, (centre[k][1] - cy) * ky)
            rows.append({"region": region, "town": town, "km": max(d, 1.5), "stories": dens.get(k, 0.0)})
D = pd.DataFrame(rows).drop_duplicates(["town", "km", "stories"])
D["band"] = pd.cut(D.km, [0, 3, 6, 10, 15, 20, 30, 45, 200])
g = D.groupby(["town", "band"], observed=True).agg(stories=("stories", "sum"), hexes=("stories", "size"), km=("km", "mean")).reset_index()
g = g[g.hexes > 0]
X = pd.get_dummies(g.town, prefix="t").astype(float); X["log_km"] = np.log(g.km)
m = sm.GLM(g.stories, X, family=sm.families.Poisson(), exposure=g.hexes).fit()
beta = -m.params["log_km"]
print(f"{g.town.nunique()} towns: home-county coverage per hexagon ~ distance^-{beta:.2f} (s.e. {m.bse['log_km']:.2f})")
prof = g.groupby("band", observed=True).apply(lambda x: x.stories.sum() / x.hexes.sum())
# PROFILES: each town's own stories per hexagon by distance band, relative to its 0-3 km band, made non-increasing
# outward; and the pooled profile, for towns without their own outlets (written for confidence_layer.py)
BANDS = [0, 3, 6, 10, 15, 20, 30, 45, 200]
rel = []
for t, x in list(g.groupby("town")) + [("_pooled", g)]:
    y = x.groupby("band", observed=True).apply(lambda z: z.stories.sum() / z.hexes.sum())
    if len(y) == 0 or y.iloc[0] <= 0:
        continue
    r = np.minimum.accumulate((y / y.iloc[0]).values)
    rel += [{"town": t, "km_from": b.left, "km_to": b.right, "relative": round(float(v), 4)} for b, v in zip(y.index, r)]
pd.DataFrame(rel).to_csv(root / "analysis/home_county_profiles.csv", index=False)
print("stories per hexagon by distance band (pooled):", {str(k): round(v, 2) for k, v in prof.items()})
print(f"relative to 3 km: 10 km {(10 / 3) ** -beta:.2f}, 20 km {(20 / 3) ** -beta:.2f}, 40 km {(40 / 3) ** -beta:.2f}")
for t in ("Columbia", "Springfield", "Joplin", "Mexico", "Kirksville"):
    x = g[g.town == t]
    if len(x):
        print(f"  {t}: stories per hexagon by distance", {str(b): round(s_ / h_, 2) for b, s_, h_ in zip(x.band, x.stories, x.hexes)})
pd.DataFrame({"beta_home": [beta], "se": [m.bse["log_km"]], "towns": [g.town.nunique()], "outlets": ["own town" if OWN_TOWN else "home county"]}).to_csv(root / "analysis/home_county_decay.csv", index=False)
