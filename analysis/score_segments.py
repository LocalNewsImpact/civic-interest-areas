"""Score adjusted public models by segment: small rural, independent towns, commuter (major-metro ring), commuter
(regional-hub ring or outside a metro), hubs -- share-weighted absolute error against Advan, counties held out.
Usage: score_segments.py OUTTAG=label ... (files analysis/public_adjusted_pairs<OUTTAG>.csv; columns adjusted_A/C)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
A = root / "analysis"
S = pd.read_csv(A / "compare_shares.csv", dtype={"i": str, "j": str}); key = list(zip(S.i, S.j)); a = S.advan.values
tr = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_TR29.txt", dtype=str, encoding="utf-8-sig")
tp = dict(zip(tr.STATEFP + tr.COUNTYFP + tr.TRACTCE, tr.POPULATION.astype(float)))
unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(A / "county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
dl = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str).dropna(subset=["FIPS County Code"])
bigm = set((dl["FIPS State Code"] + dl["FIPS County Code"])[dl["CBSA Code"].isin(["28140", "41180"])])
seg = lambda i: {"class 1": "small rural", "class 2": "indep. towns", "class 4": "hubs"}.get(
    tier.get(unit(i), "class 1"), "commuter: major metro" if i in bigm else "commuter: regional hub")
g = np.array([seg(i) for i in S.i])
SEGS = ["small rural", "indep. towns", "commuter: major metro", "commuter: regional hub", "hubs"]
err = lambda p, m: 100 * np.sum(a[m] * np.abs(p[m] - a[m])) / np.sum(a[m])


def roll(f, col):
    T = pd.read_csv(A / f, dtype={"tract": str, "j": str, "home": str})
    w = T[col] / T.groupby("tract")[col].transform("sum") * T.tract.map(tp)
    gg = w.groupby([T.home, T.j]).sum()
    x = np.array([gg.get(k, 0.0) for k in key])
    return x / pd.Series(x).groupby(S.i.values).transform("sum").values


rows = {"Advan-fitted": S["Advan-fitted (adopted, counties held out)"].values}
first = True
for arg in sys.argv[1:]:
    tag, label = arg.split("=", 1)
    f = f"public_adjusted_pairs{tag}.csv"
    if first:
        rows["public, best setting per segment"] = roll(f, "combined_share"); first = False
    rows[f"{label}: segments only"] = roll(f, "adjusted_C")
    rows[f"{label}: + per-destination"] = roll(f, "adjusted_A")
print("| Model | " + " | ".join(SEGS) + " | all |\n|---|" + "---:|" * 6)
for k, p in rows.items():
    print(f"| {k} | " + " | ".join(f"{err(p, g == s):.2f}" for s in SEGS) + f" | {err(p, np.ones(len(a), bool)):.2f} |")
