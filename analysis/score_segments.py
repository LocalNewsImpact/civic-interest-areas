"""Score the Missouri public models by segment: small rural, independent towns, commuter (major-metro ring), commuter
(regional-hub ring or outside a metro), hubs -- against Advan, on the common destination set (the public model's
destinations; Advan and the Advan-fitted model renormalised over it), two metrics (public_scoring.py), and
county-paired bootstrap 95% intervals for each difference (* = interval excludes zero).

Default: the nested results (public_adjusted_nested_pairs.csv, public_adjusted_nested.py) -- Stage 1 chosen with the
county left out, Stage 2 structure chosen inside the outer loop -- beside the in-sample choices they replace.
The Advan-fitted benchmark is read from compare_shares.csv as it stands (public_vs_advan_compare.py, which runs the
adopted model of travel_commute_pair_test.py with each county held out).
Usage: score_segments.py                       nested results
       score_segments.py OUTTAG=label ...      public_adjusted_pairs<OUTTAG>.csv (columns adjusted_A/C), as before."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
A = root / "analysis"
sys.path.insert(0, str(A))
from public_scoring import boot_diff, fmt_ci, per_county, renorm  # noqa: E402

S = pd.read_csv(A / "compare_shares.csv", dtype={"i": str, "j": str}); key = list(zip(S.i, S.j))
tr = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_TR29.txt", dtype=str, encoding="utf-8-sig")
tp = dict(zip(tr.STATEFP + tr.COUNTYFP + tr.TRACTCE, tr.POPULATION.astype(float)))
unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(A / "county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
dl = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str).dropna(subset=["FIPS County Code"])
bigm = set((dl["FIPS State Code"] + dl["FIPS County Code"])[dl["CBSA Code"].isin(["28140", "41180"])])
seg = lambda i: {"class 1": "small rural", "class 2": "indep. towns", "class 4": "hubs"}.get(
    tier.get(unit(i), "class 1"), "commuter: major metro" if i in bigm else "commuter: regional hub")
SEGS = ["small rural", "indep. towns", "commuter: major metro", "commuter: regional hub", "hubs"]


def roll(f, col):
    T = pd.read_csv(A / f, dtype={"tract": str, "j": str, "home": str})
    T = T[(T.j.str[:2] == "29") & (T.home != T.j)]
    w = T[col] / T.groupby("tract")[col].transform("sum") * T.tract.map(tp)
    gg = w.groupby([T.home, T.j]).sum()
    return np.array([gg.get(k, 0.0) for k in key])


if len(sys.argv) > 1:
    first = None
    rows = {}
    for arg in sys.argv[1:]:
        tag, label = arg.split("=", 1)
        f = f"public_adjusted_pairs{tag}.csv"
        if first is None:
            first = roll(f, "combined_share"); rows["public base"] = first
        rows[f"{label}: segments only"] = roll(f, "adjusted_C")
        rows[f"{label}: + per-destination"] = roll(f, "adjusted_A")
    common = first > 0
    hdr = {}
else:
    N = pd.read_csv(A / "public_adjusted_nested_pairs.csv", dtype={"i": str, "j": str})
    assert (N.i.values == S.i.values).all() and (N.j.values == S.j.values).all()
    common = N.common.values.astype(bool)
    rows = {"Public, setting chosen in-sample (superseded)": N.public_insample.values,
            "**Public, setting chosen nested (leave one county out)**": N.public_nested.values,
            "+ segment corrections, structure chosen in-sample (superseded)": N.C_insample.values,
            "+ segment corrections, adopted structure of 2026-10-18 (superseded)": N.C_adopted.values,
            "**+ segment corrections, outer loop (transferable)**": N.C_outer.values,
            "+ corrections, destination factor from public measures, outer loop": N.B_outer.values,
            "+ corrections + one factor per destination county, outer loop (Missouri only)": N.A_outer.values}
a = renorm(S.i.values, S.advan.values * common)
fit = renorm(S.i.values, S["Advan-fitted (adopted, counties held out)"].values * common)
out_share = pd.Series(S.advan.values * ~common).groupby(S.i.values).sum()
E = {"Advan-fitted": per_county(S.i.values, a, fit)}
E.update({k: per_county(S.i.values, a, renorm(S.i.values, p * common)) for k, p in rows.items()})
g = pd.Series({h: seg(h) for h in E["Advan-fitted"].index})
n = g.value_counts()
print(f"common destination set: {int((~common).sum())} pairs outside (public = 0) hold {100 * out_share.mean():.2f}% of Advan "
      f"share per county on average (max {100 * out_share.max():.1f}%)")
for met, mn in (("sw", "share-weighted error, points"), ("lr", "log-ratio error, mean |ln(p/a)|, pairs with Advan share >= 1%")):
    print(f"\n### Missouri, {mn}")
    print("| Model | " + " | ".join(f"{s} ({n[s]})" for s in SEGS) + f" | all ({len(g)}) |\n|---|" + "---:|" * 6)
    for k, e in E.items():
        print(f"| {k} | " + " | ".join(f"{e[met][g == s].mean():.2f}" for s in SEGS) + f" | {e[met].mean():.2f} |")
    cmp = [(k, "Advan-fitted") for k in E if k != "Advan-fitted" and "superseded" not in k]
    if len(sys.argv) == 1:
        cmp.append(("**+ segment corrections, outer loop (transferable)**", "**Public, setting chosen nested (leave one county out)**"))
        cmp.append(("+ corrections + one factor per destination county, outer loop (Missouri only)", "**Public, setting chosen nested (leave one county out)**"))
    for x, y in cmp:
        b = boot_diff(E[x][met] - E[y][met], g)
        print(f"| {x.strip('*')} - {y.strip('*')}, 95% CI | " + " | ".join(fmt_ci(b[s]) for s in SEGS) + f" | {fmt_ci(b['all'])} |")
if len(sys.argv) == 1:
    pd.concat({k.strip("*"): e for k, e in E.items()}, axis=1).assign(segment=g, advan_outside=out_share).to_csv(A / "mo_scores_nested.csv")
