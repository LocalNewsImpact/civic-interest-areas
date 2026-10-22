"""Where the public model's gap to the Advan-fitted model comes from: correct the public prediction with one piece of
Advan detail at a time, fitted on other counties and applied to the held-out county (8 folds of home counties, the
folds of travel_commute_pair_test.py), and see how much of the gap closes.

  destination   one factor per destination county: Advan inflow / public inflow (what the destination's own draw adds)
  distance      one factor per distance band, per class of home county (the shape of decay as homes show it)
  adjacency     one factor for neighbouring counties, per class of home county
  size          one factor per destination-size band (taxable-sales quintile), per class of home county
Corrections are multiplicative, fitted in turn and iterated (5 rounds) when combined; predictions renormalised per
home county. Public reference: trade area capture, Huff on sales, survey decay (public_model_pairs_tiers_tac.csv).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
from gravity_terms import all_pairs, root  # noqa: E402

S = pd.read_csv(root / "analysis/compare_shares.csv", dtype={"i": str, "j": str})
pp = all_pairs()
assert (pp.i.values == S.i.values).all() and (pp.j.values == S.j.values).all()
adj = pp.adjacent.values.astype(bool)
a = S.advan.values
p0 = S["trade area: TAC leakage, Huff on sales, survey decay"].values
adv = S["Advan-fitted (adopted, counties held out)"].values
unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(root / "analysis/county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
cls = np.array([tier.get(unit(i), "class 1") for i in S.i])
LABEL = {"class 1": "small rural", "class 2": "indep. towns", "class 3": "commuter", "class 4": "hubs"}
dband = np.digitize(S.dist.values, [15, 30, 50, 80, 120])
ts = pd.read_csv(root / "census_dl/mo_dor/cnty/DI60IT15_SLS_CNTY_F_2025.csv", dtype=str, encoding="utf-8-sig")
ts = pd.Series(ts.Total.str.replace(r"[$,\s]", "", regex=True).astype(float).values, index="29" + ts.MOID.str.zfill(3).replace("193", "186"))   # DOR keeps Ste. Genevieve's pre-1979 code
sband = pd.qcut(ts, 5, labels=False).reindex(S.j).fillna(0).astype(int).values
iu = np.array([unit(i) for i in S.i])
folds = np.array_split(np.random.default_rng(7).permutation(sorted(set(iu))), 8)
norm = lambda p: p / pd.Series(p).groupby(S.i.values).transform("sum").values
err = lambda p, m: 100 * np.sum(a[m] * np.abs(p[m] - a[m])) / np.sum(a[m])
GROUPS = {"destination": lambda: S.j.values,
          "distance": lambda: np.char.add(cls.astype(str), dband.astype(str)),
          "adjacency": lambda: np.char.add(cls.astype(str), adj.astype(int).astype(str)),
          "size": lambda: np.char.add(cls.astype(str), sband.astype(str))}


def corrected(kinds):
    out = np.zeros(len(a))
    for f in folds:
        test = np.isin(iu, f); train = ~test
        p = p0.copy()
        for _ in range(5 if len(kinds) > 1 else 1):
            for k in kinds:
                g = GROUPS[k]()
                num = pd.Series(a[train]).groupby(g[train]).sum()
                den = pd.Series(p[train]).groupby(g[train]).sum()
                fac = (num / den).clip(0.05, 20)
                p = norm(p * pd.Series(g).map(fac).fillna(1.0).values)
        out[test] = p[test]
    return out


rows = {"Advan-fitted": adv, "public reference": p0}
for ks in (["destination"], ["distance"], ["adjacency"], ["size"], ["distance", "adjacency"], ["destination", "distance"],
           ["size", "distance", "adjacency"], ["destination", "distance", "adjacency"]):
    rows["public x " + " + ".join(ks)] = corrected(ks)
allm = np.ones(len(a), bool)
gap = err(p0, allm) - err(adv, allm)
print("| Model | " + " | ".join(LABEL.values()) + " | all | share of gap closed |\n|---|" + "---:|" * 6)
for lab, p in rows.items():
    e = err(p, allm)
    print(f"| {lab} | " + " | ".join(f"{err(p, cls == c):.2f}" for c in LABEL) + f" | {e:.2f} | {100 * (err(p0, allm) - e) / gap:.0f}% |")

# the distance factors themselves (all counties): how the public decay differs from what homes show
g = GROUPS["distance"]()
fac = (pd.Series(a).groupby(g).sum() / pd.Series(p0).groupby(g).sum())
tab = pd.DataFrame({LABEL[c]: [fac.get(f"{c}{b}", np.nan) for b in range(6)] for c in LABEL},
                   index=["<15 mi", "15-30", "30-50", "50-80", "80-120", "120+"]).round(2)
print("\nAdvan / public, by distance band and class of home county:\n" + tab.to_string())
g = GROUPS["adjacency"]()
fac = (pd.Series(a).groupby(g).sum() / pd.Series(p0).groupby(g).sum())
print("\nAdvan / public, neighbouring counties:", {LABEL[c]: round(fac.get(f"{c}1", np.nan), 2) for c in LABEL},
      " other:", {LABEL[c]: round(fac.get(f"{c}0", np.nan), 2) for c in LABEL})
g = GROUPS["size"]()
fac = (pd.Series(a).groupby(g).sum() / pd.Series(p0).groupby(g).sum())
tab = pd.DataFrame({LABEL[c]: [fac.get(f"{c}{b}", np.nan) for b in range(5)] for c in LABEL},
                   index=["sales Q1 (smallest)", "Q2", "Q3", "Q4", "Q5 (largest)"]).round(2)
print("\nAdvan / public, by destination size (2025 taxable sales quintile):\n" + tab.to_string())
