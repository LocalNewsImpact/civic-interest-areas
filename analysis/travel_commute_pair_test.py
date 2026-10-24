"""Pair-level commuting as a predictor of travel: does the LODES flow between two specific counties predict visits?

Public data: LODES 2023 Missouri main origin-destination file (od_2023.csv.gz), jobs S000, home county -> work county,
as built in gravity_terms.py:
  commute_out   log(1 + 1000 x workers living in i who work in j / all workers living in i)
  commute_in    log(1 + 1000 x workers living in j who work in i / all workers living in j)
Added to the pooled model without commuting (the model adopted before 2026-10-18); with both, the model is the adopted
one (gravity_terms.FACTORS). Outcome: the adopted one (calibrated, pass-through discounted). Scored: every county held
out in 8 folds (seed 7), each predicted from all other counties (its commuting flows are public data about it, so they
are used for it; its travel is not); share-weighted absolute error of destination shares by tier (county_class_k4.csv),
with 95% bootstrap intervals over home counties, and the change against the adopted model; top-3 error = absolute share
error of each small rural county's three largest FORECAST destinations. Coefficients: errors clustered by home and
destination county.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
exec(open(Path(__file__).resolve().parent / "travel_model_dc_test.py").read().split("models = [")[0])
from gravity_terms import boot, county_stats, fit_twoway, loco, term_table  # noqa: E402
warnings.filterwarnings("ignore")

pre = [c for c in FACTORS if not c.startswith("commute")]
models = {"pooled, no commuting (adopted before 2026-10-18)": pre, "+ commuting out": pre + ["commute_out"],
          "+ commuting out and in (ADOPTED)": FACTORS}
unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(root / "analysis/county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
names = {"class 1": "small rural", "class 2": "independent towns", "class 3": "commuter counties", "class 4": "hubs"}
o = pairs.i.values
a = share(y9)
S, P = {}, {}
for label, cols in models.items():
    P[label] = loco(y9, Xof(cols), o)
    S[label] = county_stats(a, P[label], o, y9)
    print("done:", label, flush=True)
ctier = pd.Series({f: tier.get(unit(f), "class 1") for f in S[label].index})
ref = S["+ commuting out and in (ADOPTED)"]
print("\nheld-out weighted share error, points [95% interval]; change vs adopted [95%]")
print("| Model | " + " | ".join(names.values()) + " | all | small rural top-3 |")
print("|---|" + "---|" * 6)
for label in models:
    s, cells = S[label], []
    for c in list(names) + ["all"]:
        mk = np.ones(len(s), bool) if c == "all" else (ctier.reindex(s.index) == c).values
        v = s[mk].werr.mean()
        lo, hi = boot(s, "werr", mask=mk)
        cell = f"{v:.2f} [{lo:.2f}, {hi:.2f}]"
        if s is not ref:
            dl, dh = boot(s, "werr", ref=ref, mask=mk)
            cell += f"; {v - ref[mk].werr.mean():+.2f} [{dl:+.2f}, {dh:+.2f}]"
        cells.append(cell)
    ps = P[label]
    rk = pd.Series(ps).groupby(o).rank(ascending=False, method="first").values
    top = np.array([ctier.get(i) == "class 1" for i in o]) & (rk <= 3)
    print(f"| {label} | " + " | ".join(cells) + f" | {100 * np.mean(np.abs(ps[top] - a[top])):.2f} |", flush=True)
m = fit_twoway(y9, Xof(FACTORS), pairs)
print("\nadopted model, Jan-Sep (2-way clustered):")
print(term_table(m, ["commute_out", "commute_in", "log_dist", "adjacent"]).round(4).to_string())
