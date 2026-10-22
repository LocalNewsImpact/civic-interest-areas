"""Transfer test: the segment corrections learned on all Missouri counties (public_adjusted_model.py EXPORT=
segment_corrections_mo.pkl: DIST_BY_RANK, SPLIT3 with C5AS="class 2", TRANSFER, CORE_NEAR; groups commute_rank,
dest_order, dest_class) applied to Kansas's public model, every key computed from Kansas public data:
  home class         county_class_k4_20.csv (nearest Missouri class centre); commuter counties outside a 1M+ metro
                     take the independent-town corrections, as in Missouri
  distance band      tract miles to the destination's centre of population, bands <15, 15-30, 30-50, 50-80, 80-120,
                     120+; learned apart for the dominant/secondary commuting county and the hub relation
  adjacency          Census county adjacency 2023
  commuting rank     LODES 2023 (Kansas main + Missouri auxiliary), the home county's out-of-county work destinations
                     in Kansas and Missouri
  destination order  transferable definitions: central county of a 1M+ metro area (OMB 2023, Census 2024); rest of
                     such a metro; resort (marinas + RV parks and camps per resident, top tenth of U.S. counties, CBP
                     2022); regional centre (pull factor >= 1 and >= 60,000 trade-area customers: Kansas Department of
                     Revenue FY2025 for Kansas, Missouri DOR 2025 for Missouri); sub-regional (pull factor >= 1); local;
                     a core or big-metro county within 50 miles of home is its own order
  destination class  the destination's home class (Kansas or Missouri file)
Frame: destinations in Kansas and Missouri (the Advan files cover Kansas destinations; Kansans' visits to Missouri are
in the Missouri files), out of county. Output analysis/ks_predictions.csv: home, j, miles, public, corrected.
"""
import csv
import gzip
import pickle
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
A = root / "analysis"
REF = root / "census_dl/ref"
K = pickle.load(open(A / "segment_corrections_mo.pkl", "rb"))
CUTS = [15, 30, 50, 80, 120]
FRAME = {"20", "29"}

T = pd.read_csv(A / "public_model_pairs_tiers_20_byclass_c5_g_40_sales.csv", dtype={"tract": str, "j": str, "home": str})
T = T[T.j.str[:2].isin(FRAME) & (T.home != T.j)].copy()

# classes
c20 = pd.read_csv(A / "county_class_k4_20.csv", dtype={"fips": str}).set_index("fips")["class"]
c29 = pd.read_csv(A / "county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
dl = pd.read_excel(REF / "list1_2023.xlsx", header=2, dtype=str).dropna(subset=["FIPS County Code"])
dl["f"] = dl["FIPS State Code"] + dl["FIPS County Code"]
cpop = pd.read_csv(REF / "cbsa-est2024-alldata.csv", encoding="latin-1", dtype=str)
cpop = cpop[cpop.LSAD.str.endswith("Statistical Area")].set_index("CBSA").POPESTIMATE2024.astype(float)
big = set(dl.f[dl["CBSA Code"].map(cpop).fillna(0) >= 1e6])
core = big & set(dl.f[dl["Central/Outlying County"] == "Central"])
big_rest = big - core


def klass(h):
    c = (c20 if h[:2] == "20" else c29).get("29189" if h == "29510" else h, "class 1")
    return "class 2" if c == "class 3" and h not in big else c          # C5AS="class 2"


# pull factor and trade-area customers by destination
ks = pd.read_csv(A / "ks_pull_factors_fy25.csv", dtype={"fips": str}).set_index("fips")
mo = pd.read_csv(root / "census_dl/mo_dor/cnty/DI60IT15_SLS_CNTY_F_2025.csv", dtype=str, encoding="utf-8-sig")
mo = pd.Series(mo.Total.str.replace(r"[$,\s]", "", regex=True).astype(float).values, index="29" + mo.MOID.str.zfill(3).replace("193", "186"))
co = pd.read_csv(REF / "CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
co["f"] = co.STATEFP + co.COUNTYFP
cpos = co.set_index("f")[["LATITUDE", "LONGITUDE", "POPULATION"]].astype(float)
mo_pc = mo.sum() / cpos.POPULATION.reindex(mo.index).sum()
PF = pd.concat([ks.pull_factor, (mo / cpos.POPULATION.reindex(mo.index)) / mo_pc])
CUST = pd.concat([ks.tac, mo / mo_pc])
cbe = pd.read_csv(root / "census_dl/cbp/cbp22co.txt", dtype=str, usecols=["fipstate", "fipscty", "naics", "est"])
rec = cbe[cbe.naics.isin(["713930", "7212//"])].assign(f=lambda d: d.fipstate + d.fipscty, e=lambda d: d.est.astype(float)).groupby("f").e.sum()
resort_rate = rec.reindex(cpos.index).fillna(0) / cpos.POPULATION * 1e4
rcut = resort_rate.quantile(0.9)


def order(j):
    if j in core: return 1
    if j in big_rest: return 6
    if resort_rate.get(j, 0) >= rcut: return 5
    if PF.get(j, 0) >= 1.0 and CUST.get(j, 0) >= 60000: return 2
    if PF.get(j, 0) >= 1.0: return 3
    return 4


def miles(i, j):
    a, b = np.radians(cpos.loc[i, ["LATITUDE", "LONGITUDE"]].values), np.radians(cpos.loc[j, ["LATITUDE", "LONGITUDE"]].values)
    return 2 * 3959 * np.arcsin(np.sqrt(np.sin((b[0] - a[0]) / 2) ** 2 + np.cos(a[0]) * np.cos(b[0]) * np.sin((b[1] - a[1]) / 2) ** 2))


# commuting rank (Kansas homes; destinations in Kansas and Missouri)
flow = defaultdict(float)
for f in (root / "free/ks/ks_od_main_JT00_2023.csv.gz", root / "free/ks/mo_od_aux_JT00_2023.csv.gz"):
    with gzip.open(f, "rt") as fh:
        for r in csv.DictReader(fh):
            if r["h_geocode"][:2] == "20":
                flow[r["h_geocode"][:5], r["w_geocode"][:5]] += float(r["S000"])
rank = {}
for h in set(T.home):
    out = sorted(((v, w) for (hh, w), v in flow.items() if hh == h and w != h and w[:2] in FRAME), reverse=True)
    for n, (_, w) in enumerate(out):
        rank[h, w] = 1 if n == 0 else 2 if n == 1 else 3 if n < 5 else 4
adj = pd.read_csv(REF / "county_adjacency2023.txt", sep="|", dtype=str, encoding="latin-1")
ADJ = set(zip(adj["County GEOID"], adj["Neighbor GEOID"]))

pairs = T[["home", "j"]].drop_duplicates()
pairs["dist"] = [miles(h, j) for h, j in zip(pairs.home, pairs.j)]
pairs["rank"] = [rank.get((h, j), 4) for h, j in zip(pairs.home, pairs.j)]
pairs["order"] = [order(j) for j in pairs.j]
pairs.loc[(pairs.dist < 50) & (pairs.order == 1), "order"] = 7
pairs.loc[(pairs.dist < 50) & (pairs.order == 6), "order"] = 8
pairs["hub"] = (pairs["rank"] == 1) & pairs.order.isin([1, 2, 7])
pairs["cls"] = pairs.home.map(klass)
pairs["dcls"] = [int(klass(j)[-1]) for j in pairs.j]
pairs["adj"] = [(h, j) in ADJ for h, j in zip(pairs.home, pairs.j)]
T = T.merge(pairs, on=["home", "j"])
T["band"] = np.digitize(T.miles.values, CUTS) + 10 * (((T["rank"] <= 2) & ~T.hub) | T.hub)
f = np.array([K["fb"].get((c, b), 1.0) for c, b in zip(T.cls, T.band)]) * np.array([K["fa"].get((c, v), 1.0) for c, v in zip(T.cls, T.adj)])
for g, col in (("commute_rank", "rank"), ("dest_order", "order"), ("dest_class", "dcls")):
    f *= np.array([K["fx"].get((g, c, v), 1.0) for c, v in zip(T.cls, T[col])])
T["corrected"] = T.combined_share * f
tp = pd.read_csv(REF / "CenPop2020_Mean_TR20.txt", dtype=str, encoding="utf-8-sig")
tp = dict(zip(tp.STATEFP + tp.COUNTYFP + tp.TRACTCE, tp.POPULATION.astype(float)))
out = []
for col in ("combined_share", "corrected"):
    w = T[col] / T.groupby("tract")[col].transform("sum") * T.tract.map(tp)
    g = w.groupby([T.home, T.j]).sum()
    out.append(g / g.groupby(level=0).transform("sum"))
res = pd.DataFrame({"public": out[0], "corrected": out[1]}).reset_index().merge(pairs[["home", "j", "dist", "cls", "order"]], on=["home", "j"])
res.to_csv(A / "ks_predictions.csv", index=False)
names = dict(zip(co.f, co.COUNAME))
print(len(res), "pairs,", res.home.nunique(), "Kansas home counties; destination orders:",
      res.drop_duplicates("j").order.value_counts().sort_index().to_dict())
for h in ("20091", "20209", "20173", "20155", "20001"):
    g = res[res.home == h].sort_values("corrected", ascending=False).head(4)
    print(f"{names[h]}: " + "; ".join(f"{names[j]} public {100 * p:.0f}% corrected {100 * q:.0f}%" for j, p, q in zip(g.j, g.public, g.corrected)))
