"""How many directions does a home area's regular travel go beyond its home county? Missouri tracts.

Observed: Advan Neighborhood Patterns Plus, home tract -> destination county (od_tract_mo_2026.csv), January-July 2026
(2020 block groups; August-September are 2010 block groups and are not in the tract file); regular travel = destinations
visited in at least 6 of the 7 months (the 2026-10-16 rule was 7 of 9: the same share, 78%, rounded up); home county
excluded (Measurement corrections). Directions: destination counties grouped into eight 45-degree sectors by bearing from the tract's centre
of population to the county's. Count = fewest directions covering 80% of the tract's regular out-of-county visits;
effective number = 1 / sum of squared direction shares.
Predicted: the public model with Missouri segment corrections (public_adjusted_pairs_trnear.csv, adjusted_C; each
county held out) and without (combined_share), the same directions from its tract shares.
Scored: the share of tracts whose count is right (1, 2, 3+), and whose first direction is right.
"""
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
A = root / "analysis"
tr = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_TR29.txt", dtype=str, encoding="utf-8-sig"); tr["t"] = tr.STATEFP + tr.COUNTYFP + tr.TRACTCE
tl = tr.set_index("t")[["LATITUDE", "LONGITUDE", "POPULATION"]].astype(float)
co = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig"); co["f"] = co.STATEFP + co.COUNTYFP
cl = co.set_index("f")[["LATITUDE", "LONGITUDE"]].astype(float)
NAMES = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def directions(d):
    """d: columns t, j, v (out-of-county) -> direction shares per tract"""
    d = d[d.t.isin(tl.index) & d.j.isin(cl.index) & (d.j != d.t.str[:5])].copy()
    dy = cl.LATITUDE.reindex(d.j).values - tl.LATITUDE.reindex(d.t).values
    dx = (cl.LONGITUDE.reindex(d.j).values - tl.LONGITUDE.reindex(d.t).values) * np.cos(np.radians(38.5))
    d["dir"] = (((np.degrees(np.arctan2(dx, dy)) + 360) % 360 + 22.5) // 45 % 8).astype(int)
    m = d.groupby(["t", "dir"]).v.sum()
    return m / m.groupby(level=0).transform("sum")


def summary(s):
    k = s.groupby(level=0).apply(lambda x: int((x.sort_values(ascending=False).cumsum() < 0.8).sum() + 1))
    first = s.groupby(level=0).idxmax().map(lambda x: x[1])
    neff = 1 / (s ** 2).groupby(level=0).sum()
    return pd.DataFrame({"k": k, "first": first, "neff": neff})


od = pd.read_csv(A / "od_tract_mo_2026.csv", dtype={"home_tract": str, "dest_county": str})
assert od.month.max() <= "2026-07", "od_tract_mo_2026.csv must hold 2020 block-group months only (build_tract_od.py)"
MIN_MONTHS = int(np.ceil(7 / 9 * od.month.nunique()))
months = od.groupby(["home_tract", "dest_county"]).month.nunique()
v = od.groupby(["home_tract", "dest_county"]).all_day.sum()[lambda x: months.reindex(x.index) >= MIN_MONTHS]
print(f"regular travel: destinations seen in at least {MIN_MONTHS} of {od.month.nunique()} months")
obs = summary(directions(v.reset_index().set_axis(["t", "j", "v"], axis=1)))
Q = pd.read_csv(A / "public_adjusted_pairs_trnear.csv", dtype={"tract": str, "j": str, "home": str})
Q = Q[Q.j.str[:2] == "29"]
pred = {lab: summary(directions(Q[["tract", "j", col]].set_axis(["t", "j", "v"], axis=1)))
        for col, lab in (("combined_share", "public"), ("adjusted_C", "public + corrections"))}
unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(A / "county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
L = {"class 1": "small rural", "class 2": "indep. towns", "class 3": "commuter", "class 4": "hubs"}
obs["cls"] = [L[tier.get(unit(t[:5]), "class 1")] for t in obs.index]
obs["pop"] = tl.POPULATION.reindex(obs.index).values
kb = lambda k: np.where(k >= 3, "3+", k.astype(str))
obs["kb"] = kb(obs.k)
print("Observed: residents (by tract) whose regular out-of-county travel (80%) goes in --")
tab = obs.groupby(["cls", "kb"])["pop"].sum().unstack().fillna(0)
tab = (tab.div(tab.sum(1), axis=0) * 100).round(0).reindex(L.values())
tab["median effective number"] = obs.groupby("cls").neff.median().round(2).reindex(L.values())
tab.columns = [f"{c} direction(s)" if c in ("1", "2", "3+") else c for c in tab.columns]
print(tab.to_string())
allp = obs.groupby("kb")["pop"].sum() / obs["pop"].sum() * 100
print("all residents:", allp.round(0).to_dict())
print("\nPredicted against observed, tracts (each county held out):")
rows = []
for lab, p in pred.items():
    j = obs.join(p, rsuffix="_p", how="inner")
    rows.append({"model": lab, "count right (1/2/3+)": f"{100 * (kb(j.k) == kb(j.k_p)).mean():.0f}%",
                 "first direction right": f"{100 * (j['first'] == j.first_p).mean():.0f}%",
                 "count within one": f"{100 * (np.abs(np.minimum(j.k, 3) - np.minimum(j.k_p, 3)) <= 1).mean():.0f}%",
                 "median effective number, predicted / observed": f"{j.neff_p.median():.2f} / {j.neff.median():.2f}"})
print(pd.DataFrame(rows).to_string(index=False))
for t in ["29007950100", "29007950300", "29151480100"]:
    if t in obs.index:
        print(t, "observed", obs.loc[t, "k"], NAMES[obs.loc[t, "first"]], "| predicted (corrected)", pred["public + corrections"].loc[t, "k"], NAMES[pred["public + corrections"].loc[t, "first"]])
