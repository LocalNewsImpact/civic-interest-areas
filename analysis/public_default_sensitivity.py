"""Question the public model's default weights, one at a time. Each variant is built by public_travel_tiers.py with
one default changed (run_default_sensitivity.sh); nothing is fitted to Advan. Scored against Advan out-of-county
county shares, January-September 2026: share-weighted absolute error by county class, and the error by pair size
(the pair's Advan share), as each band's contribution to the all-county error."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
A = root / "analysis"
S = pd.read_csv(A / "compare_shares.csv", dtype={"i": str, "j": str})
tr = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_TR29.txt", dtype=str, encoding="utf-8-sig")
pop = dict(zip(tr.STATEFP + tr.COUNTYFP + tr.TRACTCE, tr.POPULATION.astype(float)))
key = list(zip(S.i, S.j))
a = S.advan.values
unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(A / "county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
cls = np.array([tier.get(unit(i), "class 1") for i in S.i])
LABEL = {"class 1": "small rural", "class 2": "indep. towns", "class 3": "commuter", "class 4": "hubs"}
BANDS = [(0, .01, "<1%"), (.01, .05, "1-5%"), (.05, .15, "5-15%"), (.15, 1.01, ">15%")]


def roll_up(f, col="combined_share"):
    P = pd.read_csv(A / f, dtype={"tract": str, "j": str, "home": str})
    P = P[(P.j.str[:2] == "29") & (P.home != P.j)]
    w = P[col] / P.groupby("tract")[col].transform("sum") * P.tract.map(pop)
    g = w.groupby([P.home, P.j]).sum()
    x = np.array([g.get(k, 0.0) for k in key])
    return x / pd.Series(x).groupby(S.i.values).transform("sum").values


err = lambda p, m: 100 * np.sum(a[m] * np.abs(p[m] - a[m])) / np.sum(a[m])
allm = np.ones(len(a), bool)


def band_part(p):
    return [100 * np.sum((a * np.abs(p - a))[(a >= lo) & (a < hi)]) / np.sum(a) for lo, hi, _ in BANDS]


def ratio(p):            # typical miss within the band, actual / predicted (median of |log ratio|, as a factor)
    out = []
    for lo, hi, _ in BANDS:
        m = (a >= lo) & (a < hi)
        out.append(np.exp(np.median(np.abs(np.log((a[m] + 1e-5) / (p[m] + 1e-5))))))
    return out


rows = [("Advan-fitted (reference)", S["Advan-fitted (adopted, counties held out)"].values)]
for arg in sys.argv[1:]:
    tag, label = arg.split("=", 1)
    rows.append((label, roll_up(f"public_model_pairs_tiers{tag}.csv")))
base = rows[1][1]
print("| Variant | " + " | ".join(LABEL.values()) + " | all |\n|---|" + "---:|" * 5)
for i, (lab, p) in enumerate(rows):
    e = [err(p, cls == c) for c in LABEL] + [err(p, allm)]
    if i < 2:
        print(f"| **{lab}** | " + " | ".join(f"{v:.2f}" for v in e) + " |")
    else:
        eb = [err(base, cls == c) for c in LABEL] + [err(base, allm)]
        print(f"| {lab} | " + " | ".join(f"{v - b:+.2f}" for v, b in zip(e, eb)) + " |")
print("\nError by pair size (contribution to the all-county error, points) and typical miss (x):")
n = [int(((a >= lo) & (a < hi)).sum()) for lo, hi, _ in BANDS]
print("| Model | " + " | ".join(f"{b} ({k} pairs)" for (_, _, b), k in zip(BANDS, n)) + " |\n|---|" + "---:|" * 4)
for lab, p in rows[:2]:
    print(f"| {lab} | " + " | ".join(f"{e:.2f} / {r:.2f}x" for e, r in zip(band_part(p), ratio(p))) + " |")
