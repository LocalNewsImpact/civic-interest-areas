"""How far an outlet's spillover reaches: miles from the newsroom (registry office location; the home county's
population centre where the registry has none) to the population centre of each other county its March 2026 stories
are centred in or mention, weighted as the adopted spillover measure (spillover_outlets.py): centred 1, mention 0.5
(split across the other counties a story mentions), Sports stories at half weight. Same outlets as the spillover model
(10+ placed stories; `good` = well collected). Statewide stories are placed by county, so a distance is to a county's
population centre: the nearest possible reach is the next county's centre (typically 20-30 miles).

Per outlet: weighted mean and median miles. Writes analysis/spillover_radius.csv."""
import json
import math
import runpy
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "analysis"))
from spillover_common import MENTION_WEIGHT, NOT_LOCAL, SPORTS_WEIGHT, home_fips, registry  # noqa: E402

data = json.load(open(root / "coverage/storymap/statewide_2026_03_articles.json"))
cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str}).set_index("fips")
cp = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
cen = {r.STATEFP + r.COUNTYFP: (float(r.LATITUDE), float(r.LONGITUDE)) for r in cp.itertuples()}
CIN = pd.read_csv(root / "coverage/cin_labels_2026_03.csv").set_index("id").primary_label
so = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str, "home_also": str}).set_index("outlet")
reg = registry()
reg = reg[reg.state == "MO"].dropna(subset=["lat", "lon"]).drop_duplicates("outlet").set_index("outlet")


def miles(p, q):
    (y1, x1), (y2, x2) = p, q
    a, b = math.radians(y1), math.radians(y2)
    return 3959 * math.acos(min(1, math.sin(a) * math.sin(b) + math.cos(a) * math.cos(b) * math.cos(math.radians(x2 - x1))))


by_name = {n.lower(): f for f, n in cov.name.items()}
by_name.update({"st. louis": "29189", "st louis": "29189", "st. louis city": "29510"})
fips_of = lambda n: by_name.get((n or "").lower().replace(" county", "").strip())
unit = lambda f: "29189" if f == "29510" else f
near = {}
w = defaultdict(list)           # outlet -> [(miles, weight)]
for a in data["articles"]:
    pub = a["publisher"]
    f = fips_of(a["publisher_county"])
    if not f or not a["counties"] or pub in NOT_LOCAL or pub not in so.index:
        continue
    i = unit(home_fips(pub, f))
    if i != so.at[pub, "fips"]:
        continue
    if i not in near:
        src = [i] + (["29510"] if i == "29189" else [])
        near[i] = {g for g in cen if not g.startswith("29") and any(miles(cen[s], cen[g]) <= 60 for s in src)}
    # HOME rule (spillover_common.home_set), as spillover_outlets.csv records it
    home_also = {i} | (set(so.at[pub, "home_also"].split(";")) if isinstance(so.at[pub, "home_also"], str) else set())
    away = lambda c: ((c.startswith("29") and unit(c) not in home_also) or c in near[i]) and c not in home_also
    office = (float(reg.at[pub, "lat"]), float(reg.at[pub, "lon"])) if pub in reg.index else cen[i]
    sw = SPORTS_WEIGHT if CIN.get(a["id"]) == "Sports" else 1.0
    if a["central"] and away(a["central"]):
        w[pub].append((miles(office, cen[a["central"]]), sw, unit(a["central"])))
    else:
        others = [c for c in set(a["counties"]) if away(c) and c in cen]
        for c in others:
            w[pub].append((miles(office, cen[c]), sw * MENTION_WEIGHT / len(others), unit(c)))


def wmedian(v, wt):
    o = np.argsort(v); v, wt = np.asarray(v)[o], np.asarray(wt)[o]
    return float(v[np.searchsorted(np.cumsum(wt), wt.sum() / 2)])


rows = []
for pub, xs in w.items():
    m, wt = np.array([x[0] for x in xs]), np.array([x[1] for x in xs])
    byc = pd.Series(wt).groupby([x[2] for x in xs]).sum()
    rows.append({"outlet": pub, "mean_mi": float((m * wt).sum() / wt.sum()), "median_mi": wmedian(m, wt),
                 "within_30": float(wt[m <= 30].sum() / wt.sum()), "within_60": float(wt[m <= 60].sum() / wt.sum()),
                 "spill_weight": float(wt.sum()), "top_county": byc.idxmax(), "top_share": float(byc.max() / wt.sum()),
                 "top_mi": float(np.average(m[[x[2] == byc.idxmax() for x in xs]]))})
r = pd.DataFrame(rows).set_index("outlet").join(so[["fips", "broadcast", "placed", "rate", "type", "pct_urban", "town_pop",
                                                     "crowded_weekly", "border", "good"]])
r.to_csv(root / "analysis/spillover_radius.csv")


def table(by, d=r):
    g = d.groupby(by)
    t = pd.DataFrame({"outlets": g.size(), "median of outlets' median miles": g.median_mi.median().round(0),
                      "median of outlets' mean miles": g.mean_mi.median().round(0),
                      "share within 30 mi": g.within_30.median().round(2), "share within 60 mi": g.within_60.median().round(2),
                      "median spillover rate": g.rate.median().round(2)})
    print(t.to_string(), "\n")


print(f"{len(r)} outlets, {int(r.good.sum())} well collected; office located from registry for "
      f"{sum(o in reg.index for o in r.index)}")
r["all"] = "all outlets"
table("all"); table("all", r[r.good])
r["kind"] = np.where(r.broadcast == 1, "broadcast", np.where(r.crowded_weekly == 1, "weekly in a daily-and-TV county", "print/digital, other"))
table("kind")
table("type")
r["urban"] = pd.cut(r.pct_urban, [-0.01, 0.0001, 0.5, 1.01], labels=["no urban area", "under half urban", "half+ urban"])
table("urban")
r["size"] = pd.qcut(r.placed, 3, labels=["smallest third (stories)", "middle third", "largest third"])
table("size")
r["town"] = pd.cut(r.town_pop, [0, 2500, 10000, 50000, 1e7], labels=["town < 2,500", "2,500-10,000", "10,000-50,000", "50,000+"])
table("town")
table("border")

# THE TRAVEL MODEL'S FIVE HOME CLASSES (assemble_public_by_class.py): k-means tiers, commuter counties split into rings
# of the Kansas City and St. Louis metros and rings of regional hubs; hubs split the same way (metro core / regional hub)
tier = pd.read_csv(root / "analysis/county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
_dl = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str).dropna(subset=["FIPS County Code"])
bigm = set((_dl["FIPS State Code"] + _dl["FIPS County Code"])[_dl["CBSA Code"].isin(["28140", "41180"])])
NAME = {"class 1": "small rural", "class 2": "independent town"}


def klass(f):
    c = tier.get(f, "class 1")
    if c == "class 3":
        return "ring: Kansas City / St. Louis metro" if f in bigm else "ring: regional hub"
    if c == "class 4":
        return "hub: Kansas City / St. Louis core" if f in bigm else "hub: regional"
    return NAME[c]


r["home class"] = r.fips.map(klass)
r.drop(columns=["all"]).to_csv(root / "analysis/spillover_radius.csv")
table("home class")
from scipy import stats  # noqa: E402
print("Kruskal-Wallis, median miles by home class: p = %.4f" % stats.kruskal(*[x.median_mi.values for _, x in r.groupby("home class")]).pvalue)
a, b = (r[r["home class"] == k].median_mi for k in ("ring: Kansas City / St. Louis metro", "ring: regional hub"))
print("metro rings vs regional-hub rings, Mann-Whitney p = %.4f" % stats.mannwhitneyu(a, b).pvalue)
g = r.groupby("home class")
print(pd.DataFrame({"outlets": g.size(), "share to top county": g.top_share.median().round(2), "top county miles": g.top_mi.median().round(0),
                    "spillover rate": g.rate.median().round(2)}).to_string())
a, b = (r[r["home class"] == k].top_share for k in ("ring: Kansas City / St. Louis metro", "ring: regional hub"))
print("rings, share to top county, Mann-Whitney p = %.4f" % stats.mannwhitneyu(a, b).pvalue)
print(r[r["home class"].str.startswith("ring")].sort_values(["home class", "top_share"])[["home class", "fips", "top_county", "top_share", "top_mi", "median_mi", "rate"]].round(2).to_string())
