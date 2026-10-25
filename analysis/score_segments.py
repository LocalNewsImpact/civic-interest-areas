"""Score the Missouri public models by segment: small rural, independent towns, commuter (major-metro ring), commuter
(regional-hub ring or outside a metro), hubs -- against Advan (the adopted outcome, compare_shares.csv).

Primary metric (declared): share-weighted error over ALL Advan destinations in Missouri -- pairs outside a model's
support count as error (model share 0). Beside it: the same on the common destination set (the public model's
destinations, Advan and the Advan-fitted model renormalised over it), and the log-ratio error (public_scoring.py).
County-paired bootstrap 95% intervals (* = interval excludes zero); the gap to the Advan-fitted model and the share of
it the corrections close, each with its interval.

Default: the nested results (public_adjusted_nested_pairs.csv, public_adjusted_nested.py): Stage 1 chosen with the
county left out (public_nested) or inside each outer fold (public_foldbase, the base the outer-loop corrections act on);
Stage 2 structure chosen inside the outer loop (C/B/A_outer). The corrections are compared with their own fold base.
The Advan-fitted benchmark is read from compare_shares.csv (public_vs_advan_compare.py: the adopted model of
gravity_terms.FACTORS, each county held out, gravity_terms.loco).
Usage: score_segments.py                       nested results
       score_segments.py OUTTAG=label ...      public_adjusted_pairs<OUTTAG>.csv (columns adjusted_A/C)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
A = root / "analysis"
sys.path.insert(0, str(A))
from public_scoring import boot_diff, boot_share_closed, fmt_ci, fmt_pct, per_county, renorm  # noqa: E402

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
    x = np.array([gg.get(k, 0.0) for k in key])
    return renorm(S.i.values, x)


NESTED = len(sys.argv) == 1
if not NESTED:
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
else:
    N = pd.read_csv(A / "public_adjusted_nested_pairs.csv", dtype={"i": str, "j": str})
    assert (N.i.values == S.i.values).all() and (N.j.values == S.j.values).all()
    common = N.common.values.astype(bool)
    rows = {"Public, Stage 1 chosen nested (leave one county out)": N.public_nested.values,
            "Public, Stage 1 chosen in each outer fold (base of the outer loop)": N.public_foldbase.values,
            "Public, Stage 1 chosen in-sample (not out of sample)": N.public_insample.values,
            "+ segment corrections, outer loop (C, transferable)": N.C_outer.values,
            "+ destination factor from public measures, outer loop (B)": N.B_outer.values,
            "+ one factor per destination county, outer loop (A, Missouri only)": N.A_outer.values,
            "+ segment corrections, structure chosen in-sample (not out of sample)": N.C_insample.values}
FIT = "Advan-fitted (counties held out)"
a_all = S.advan.values
fit_all = S["Advan-fitted (adopted, counties held out)"].values
out_share = pd.Series(a_all * ~common).groupby(S.i.values).sum()
SETS = {"all Advan destinations (primary)": (a_all, {FIT: fit_all, **rows}),
        "common destination set": (renorm(S.i.values, a_all * common),
                                   {k: renorm(S.i.values, p * common) for k, p in {FIT: fit_all, **rows}.items()})}
print(f"common destination set: {int((~common).sum())} pairs outside (public = 0) hold {100 * out_share.mean():.2f}% of Advan "
      f"share per county on average (max {100 * out_share.max():.1f}%)")
E = {}
for sname, (a, P) in SETS.items():
    E[sname] = {k: per_county(S.i.values, a, p) for k, p in P.items()}
g = pd.Series({h: seg(h) for h in E["common destination set"][FIT].index})
n = g.value_counts()
hdr = "| Model | " + " | ".join(f"{s} ({n[s]})" for s in SEGS) + f" | all ({len(g)}) |\n|---|" + "---:|" * 6
BASE_FOR = {"+ segment corrections, outer loop (C, transferable)": "Public, Stage 1 chosen in each outer fold (base of the outer loop)",
            "+ destination factor from public measures, outer loop (B)": "Public, Stage 1 chosen in each outer fold (base of the outer loop)",
            "+ one factor per destination county, outer loop (A, Missouri only)": "Public, Stage 1 chosen in each outer fold (base of the outer loop)"}
for sname in SETS:
    for met, mn in (("sw", "share-weighted error, points"), ("lr", "log-ratio error, mean |ln(p/a)|, pairs with Advan share >= 1%")):
        if met == "lr" and sname.startswith("common"):
            continue
        e_ = E[sname]
        print(f"\n### Missouri, {mn}, {sname}\n" + hdr)
        for k, e in e_.items():
            print(f"| {k} | " + " | ".join(f"{e[met][g == s].mean():.2f}" for s in SEGS) + f" | {e[met].mean():.2f} |")
        print(f"| **gap to the Advan-fitted model, 95% CI** | | | | | | |")
        for k in e_:
            if k == FIT or "not out of sample" in k:
                continue
            b = boot_diff(e_[k][met] - e_[FIT][met], g)
            print(f"| {k} - Advan-fitted | " + " | ".join(fmt_ci(b[s]) for s in SEGS) + f" | {fmt_ci(b['all'])} |")
        if NESTED:
            print(f"| **gain from the corrections (against their own fold base) and share of the gap closed, 95% CI** | | | | | | |")
            for k, b0 in BASE_FOR.items():
                b = boot_diff(e_[k][met] - e_[b0][met], g)
                sc = boot_share_closed(e_[b0][met], e_[k][met], e_[FIT][met], g)
                print(f"| {k.split(',')[0]} - fold base | " + " | ".join(fmt_ci(b[s]) for s in SEGS) + f" | {fmt_ci(b['all'])} |")
                print(f"| {k.split(',')[0]}: share of the fold base's gap closed | " + " | ".join(fmt_pct(sc[s]) for s in SEGS) + f" | {fmt_pct(sc['all'])} |")
if NESTED:
    pd.concat({f"{s}|{k}": e for s, d in E.items() for k, e in d.items()}, axis=1).assign(segment=g, advan_outside=out_share).to_csv(A / "mo_scores_nested.csv")
