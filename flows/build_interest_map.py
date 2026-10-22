"""Revealed media market: a theoretical interest index for Columbia, Mexico and Linn, by tract.

  interest(h, t) = travel(h, t) x magnification(h, t)

TRAVEL (observed, modelled): reach_models.py M2 on the selected terms, fitted on January-July 2026, with a TOWN AS ONE
UNIT -- a tract inside a town takes the town's reach (the most-visited of its tracts: residents seen in the town's
busiest block group, the lower bound). Rural tracts keep their own reach. A town's value is the median over its home
block groups. The home town is the most relevant place; interest decays outward except where residents travel.
COVERAGE (observed): s = share of the home county's local outlets' March 2026 stories about the tract's town (a rural
tract: its county, stories not about one of the market's towns), weighted as in spillover -- centred 1, mention 0.5,
Sports half -- statewide outlets excluded (analysis/excluded_outlets.py).
MAGNIFICATION (assumption): outside the home town, 1 + w * s / s_bar, s_bar the travel-weighted mean coverage share of
the places residents go; w = 1 doubles travel interest in a place its residents' own outlets cover as much as the
average place they go. The home town is 1. Shown at w = 0.5, 1 and 2.
INDEX: 100 x travel x magnification, capped at 100. The home town is 100 by definition: residents are always in their
own town (reach leaves out a block group's own residents, so a town smaller than its block group -- Linn -- would
otherwise measure only the rest of its tract). 100 elsewhere reads "as local as home".
SHOWN: index 5+. TRANSIT: a tract under 5 that the road route (build_routes.py) from half or more of the town's home
block groups to a shown tract passes through -- on the way, drawn lightly.
Usage: build_interest_map.py "<terms>" <a>.  Writes flows/reach/interest_towns.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

here = Path(__file__).parent
exec(open(here / "reach_models.py").read().split("\nm2 = lambda")[0])     # g, homes, tracts, SPECS, fit_predict
sys.path.insert(0, str(here.parent / "analysis"))
from excluded_outlets import EXCLUDE  # noqa: E402

name, a = sys.argv[1], float(sys.argv[2])
out, _ = fit_predict(g, g.drop_duplicates(["hi", "ti"]), SPECS[name])
out["m2"] = (out.people + a * out.m1) / (out.own + a)
STUDY = {"Columbia": ("29019", "Boone"), "Mexico": ("29007", "Audrain"), "Linn": ("29151", "Osage")}
WS = (0.5, 1, 2)

# towns of the market: tract -> its town (the first listed), town -> tracts
t_town = {t: (p.split(";")[0] if p else "") for t, p in tracts.places.items()}
town_tracts = {}
for t, p in t_town.items():
    if p:
        town_tracts.setdefault(p, []).append(t)

# coverage shares by home county
arts = json.load(open(here.parent / "coverage/storymap/statewide_2026_03_articles.json"))["articles"]
cin = pd.read_csv(here.parent / "coverage/cin_labels_2026_03.csv").set_index("id").primary_label
pl = pd.read_csv(R / "home_story_places.csv", dtype=str)
pl = pl[pl.state == "MO"]
pl["unit"] = np.where(pl.geoid_level == "place", pl.geoid, np.where(pl.geoid_level == "county", pl.geoid, ""))
pl = pl[pl.unit != ""]
# a place that is not one of the market's towns counts for its county (county from the story's own county rollup)
pl["town"] = pl.unit.where(pl.unit.isin(town_tracts))
pl["is_point"] = pl.is_point == "t"
cov = {}
for town, (fips, cname) in STUDY.items():
    ids = {x["id"] for x in arts if (x["publisher_county"] or "").replace(" County", "") == cname and x["publisher"] not in EXCLUDE
           and x["counties"]}
    p = pl[pl.article_id.isin(ids)].copy()
    p["sw"] = np.where(p.article_id.map(cin) == "Sports", 0.5, 1.0)
    # per story and unit: centred 1, mention 0.5
    by_town = p[p.town.notna()].groupby(["article_id", "town"]).agg(pt=("is_point", "max"), sw=("sw", "first"))
    by_town["w"] = np.where(by_town.pt, 1, 0.5) * by_town.sw
    s_town = by_town.groupby("town").w.sum() / len(ids)
    rural = p[p.town.isna() & (p.geoid_level == "county")].groupby(["article_id", "unit"]).agg(pt=("is_point", "max"), sw=("sw", "first"))
    rural["w"] = np.where(rural.pt, 1, 0.5) * rural.sw
    s_cty = rural.groupby("unit").w.sum() / len(ids)
    cov[town] = {"stories": len(ids), "town": s_town, "county": s_cty}

FLOOR = 5
routes = pd.read_csv(R / "routes.csv", dtype=str)
res = {}
for town, (fips, _) in STUDY.items():
    o = out[out.home_cbg.map(homes.town) == town]
    m = o.pivot(index="home_cbg", columns="tract", values="m2")
    # town as one unit: each tract in a town takes the town's maximum
    for p_, ts in town_tracts.items():
        cols = [t for t in ts if t in m]
        m[cols] = np.repeat(m[cols].max(axis=1).values[:, None], len(cols), 1)
    travel = m.median()
    home_place = homes[homes.town == town].place.dropna().iloc[0]
    s = pd.Series({t: (cov[town]["town"].get(t_town[t], 0) if t_town[t] else cov[town]["county"].get(t[:5], 0)) for t in travel.index})
    home = travel.index.map(lambda t: t_town[t] == home_place)
    ext = ~np.asarray(home)
    s_bar = (travel[ext] * s[ext]).sum() / travel[ext].sum()
    r = {"stories": cov[town]["stories"], "s_bar": round(float(s_bar), 4), "travel": travel.round(4).to_dict(),
         "coverage": s.round(4).to_dict(), "index": {}}
    for w in WS:
        mag = np.where(ext, 1 + w * s / s_bar, 1)
        I = np.where(ext, 100 * travel * mag, 100)
        idx = pd.Series(I, index=travel.index).clip(upper=100)
        r["index"][str(w)] = idx.round(2).to_dict()
        shown = set(idx[idx >= FLOOR].index)
        hb = homes[homes.town == town].index
        rt = routes[routes.home_cbg.isin(hb) & routes.dest_tract.isin(shown)].drop_duplicates(["home_cbg", "via_tract"])
        n = rt.groupby("via_tract").home_cbg.nunique()
        r.setdefault("transit", {})[str(w)] = sorted(t for t in n[n >= len(hb) / 2].index if t not in shown)
    res[town] = r
    top = pd.Series(r["index"]["1"]).sort_values(ascending=False)
    top_ext = top[ext[travel.index.get_indexer(top.index)]].head(6)
    print(f"{town}: {r['stories']} home stories; s_bar {s_bar:.3f}; top external at w=1: "
          + ", ".join(f"{t_town[t] or t[:5]}:{t[-6:]} {v:.0f} (travel {100 * travel[t]:.1f}%, cov {100 * s[t]:.1f}%)" for t, v in top_ext.items()))
    for w in WS:
        band = lambda v: np.digitize(v, [5, 10, 20, 40])
        print(f"  w={w}: tracts changing band vs travel alone: "
              f"{int((band(pd.Series(r['index'][str(w)])) != band(np.where(ext, 100 * travel, 100))).sum())}; "
              f"at 100 outside the home town: {int((pd.Series(r['index'][str(w)])[ext] >= 100).sum())}; "
              f"shown {int((pd.Series(r['index'][str(w)]) >= FLOOR).sum())}, transit {len(r['transit'][str(w)])}")
json.dump(res, open(R / "interest_towns.json", "w"))
