"""Transfer test score: Kansas home counties' out-of-county destination shares (Kansas and Missouri destinations,
Advan Neighborhood Patterns Plus, January-September 2026; od_ks_2026.csv) against the Kansas public model and the
public model with the corrections learned in Missouri (ks_predictions.csv, transfer_adjustments.py), beside the
Advan-fitted benchmark (ks_advan_fitted.csv, fitted in Kansas, counties held out).

Common destination set: a pair is scored only where every model has it -- the public model's destinations (counties
within 200 miles of a tract, about 220 miles county to county) and the benchmark's (250 miles); Advan and every model
are renormalised over that set, and Advan's share outside it is reported.
Metrics: share-weighted error and log-ratio error (public_scoring.py); county-paired bootstrap 95% intervals for every
difference (* = interval excludes zero). Classes with fewer than 5 counties (the four commuter counties: three in the
Kansas City metro, one in the Wichita ring) are not reported as classes; they are listed county by county.
PRED: another predictions file to score (e.g. the 2026-10-18 file kept for comparison)."""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
A = root / "analysis"
sys.path.insert(0, str(A))
from public_scoring import boot_diff, fmt_ci, per_county  # noqa: E402

od = pd.read_csv(A / "od_ks_2026.csv", dtype={"home_county": str, "dest_county": str})
od = od[(od.home_county != od.dest_county) & od.dest_county.str[:2].isin(["20", "29"]) & (od.home_county.str[:2] == "20")]
adv = od.groupby(["home_county", "dest_county"]).visits.sum()
adv = (adv / adv.groupby(level=0).transform("sum")).rename("advan").rename_axis(["home", "j"])
P = pd.read_csv(os.environ.get("PRED", A / "ks_predictions.csv"), dtype={"home": str, "j": str}).set_index(["home", "j"])[["public", "corrected"]]
F = pd.read_csv(A / "ks_advan_fitted.csv", dtype={"home": str, "j": str}).set_index(["home", "j"]).fitted
common = P.index.intersection(F.index)
outside = adv.groupby(level=0).sum() - adv.reindex(common).fillna(0).groupby(level=0).sum()
X = pd.DataFrame({"advan": adv.reindex(common).fillna(0), "public": P.public.reindex(common), "corrected": P.corrected.reindex(common),
                  "fitted": F.reindex(common)}).fillna(0)
for c in X.columns:
    X[c] = X[c] / X[c].groupby(level=0).transform("sum")
homes = X.index.get_level_values(0).values
c20 = pd.read_csv(A / "county_class_k4_20.csv", dtype={"fips": str}).set_index("fips")["class"]
dl = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str).dropna(subset=["FIPS County Code"])
kc = set((dl["FIPS State Code"] + dl["FIPS County Code"])[dl["CBSA Code"] == "28140"])
seg = lambda h: {"class 1": "small rural", "class 2": "indep. towns", "class 4": "hubs"}.get(
    c20.get(h), "commuter, KC metro" if h in kc else "commuter, Wichita ring")
E = {m: per_county(homes, X.advan.values, X[m].values) for m in ("fitted", "public", "corrected")}
H = E["fitted"].index
g = pd.Series({h: seg(h) for h in H})
n = g.value_counts()
SEGS = [s for s in ("small rural", "indep. towns", "hubs") if n.get(s, 0) >= 5]
small = [h for h in H if g[h] not in SEGS]
co = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
nm = dict(zip(co.STATEFP + co.COUNTYFP, co.COUNAME))
print(f"common destination set: {len(X)} pairs, {len(H)} Kansas homes; Advan share outside it per county: mean "
      f"{100 * outside.mean():.2f}%, max {100 * outside.max():.1f}% ({nm[outside.idxmax()]})")
LAB = {"fitted": "Advan-fitted in Kansas (counties held out)", "public": "Public model, Missouri settings, nothing tuned in Kansas",
       "corrected": "+ corrections learned in Missouri"}
for met, mn in (("sw", "share-weighted error, points"), ("lr", "log-ratio error, mean |ln(p/a)|, pairs with Advan share >= 1%")):
    print(f"\n### Kansas, {mn}")
    print("| Model | " + " | ".join(f"{s} ({n[s]})" for s in SEGS) + f" | all ({len(H)}) | " + " | ".join(f"{nm[h]} ({g[h]})" for h in small) + " |")
    print("|---|" + "---:|" * (len(SEGS) + 1 + len(small)))
    for m in ("fitted", "public", "corrected"):
        e = E[m][met]
        print(f"| {LAB[m]} | " + " | ".join(f"{e[g == s].mean():.2f}" for s in SEGS) + f" | {e.mean():.2f} | " + " | ".join(f"{e[h]:.2f}" for h in small) + " |")
    gg = g.where(g.isin(SEGS), "commuter (4, pooled)")
    for (x, y) in (("public", "fitted"), ("corrected", "fitted"), ("corrected", "public")):
        b = boot_diff(E[x][met] - E[y][met], gg)
        print(f"| {x} - {y}, 95% CI | " + " | ".join(fmt_ci(b[s]) for s in SEGS) + f" | {fmt_ci(b['all'])} | "
              + f"commuter pooled {fmt_ci(b['commuter (4, pooled)'])} |" + " |" * (len(small) - 1))

per = pd.DataFrame({"pub": E["public"].sw, "cor": E["corrected"].sw})
per["d"] = per.cor - per.pub
print("\nCounties the corrections hurt most / help most (share-weighted error):")
for h, r in pd.concat([per.sort_values("d").tail(6), per.sort_values("d").head(6)]).iterrows():
    t = X.loc[h].sort_values("advan", ascending=False).head(3)
    print(f"  {nm[h]:12s} ({seg(h)}) public {r.pub:.2f} -> {r.cor:.2f} | " + "; ".join(f"{nm[j]} A {100 * x:.0f} p {100 * y:.0f} c {100 * z:.0f}" for j, x, y, z in zip(t.index, t.advan, t.public, t.corrected)))
pd.concat({m: E[m] for m in E}, axis=1).assign(segment=g, advan_outside=outside.reindex(H)).to_csv(A / f"ks_scores{os.environ.get('OUTTAG', '')}.csv")
