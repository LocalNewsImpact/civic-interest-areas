"""Transfer test score: Kansas home counties' out-of-county destination shares (Kansas and Missouri destinations,
Advan Neighborhood Patterns Plus, January-September 2026; od_ks_2026.csv, OUTCOME visits_statewide: Kansas calibration
factors on the statewide device->person scale used in Missouri; no pass-through discount, for want of Kansas road-stop
shares) against the Kansas public model and the public model with the corrections learned in Missouri
(ks_predictions.csv, transfer_adjustments.py), beside the Advan-fitted benchmark (ks_advan_fitted.csv, fitted in
Kansas, counties held out, destinations within 250 miles).

Primary metric (declared): share-weighted error over ALL Advan destinations -- a pair outside a model's support counts
as error (model share 0): the public model covers destinations within 200 miles of a tract (about 220 miles county to
county), the benchmark 250 miles. Beside it: the common destination set (pairs every model covers; Advan and every
model renormalised over it; Advan's share outside reported) and the log-ratio error (public_scoring.py).
County-paired bootstrap 95% intervals (* = interval excludes zero); the gap to the benchmark and the share of the
public model's gap the corrections close. Classes with fewer than 5 counties (the four commuter counties: three in the
Kansas City metro, one in the Wichita ring) are not reported as classes; they are listed county by county and pooled
only for intervals. PRED: another predictions file to score."""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
A = root / "analysis"
sys.path.insert(0, str(A))
from public_scoring import boot_diff, boot_share_closed, fmt_ci, fmt_pct, per_county  # noqa: E402

OUTCOME = os.environ.get("OUTCOME", "visits_statewide")
od = pd.read_csv(A / "od_ks_2026.csv", dtype={"home_county": str, "dest_county": str})
od = od[(od.home_county != od.dest_county) & od.dest_county.str[:2].isin(["20", "29"]) & (od.home_county.str[:2] == "20")]
adv = od.groupby(["home_county", "dest_county"])[OUTCOME].sum()
adv = (adv / adv.groupby(level=0).transform("sum")).rename("advan").rename_axis(["home", "j"])
P = pd.read_csv(os.environ.get("PRED", A / "ks_predictions.csv"), dtype={"home": str, "j": str}).set_index(["home", "j"])[["public", "corrected"]]
F = pd.read_csv(A / "ks_advan_fitted.csv", dtype={"home": str, "j": str}).set_index(["home", "j"]).fitted
common = P.index.intersection(F.index)
outside = adv.groupby(level=0).sum() - adv.reindex(common).fillna(0).groupby(level=0).sum()
union = adv.index.union(P.index).union(F.index)
X_all = pd.DataFrame({"advan": adv.reindex(union), "public": P.public.reindex(union), "corrected": P.corrected.reindex(union),
                      "fitted": F.reindex(union)}).fillna(0)
X_all = X_all[X_all.index.get_level_values(0).str[:2] == "20"]
X_c = X_all.loc[common].copy()
for c in X_c.columns:
    X_c[c] = X_c[c] / X_c[c].groupby(level=0).transform("sum")
c20 = pd.read_csv(A / "county_class_k4_20.csv", dtype={"fips": str}).set_index("fips")["class"]
dl = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str).dropna(subset=["FIPS County Code"])
kc = set((dl["FIPS State Code"] + dl["FIPS County Code"])[dl["CBSA Code"] == "28140"])
seg = lambda h: {"class 1": "small rural", "class 2": "indep. towns", "class 4": "hubs"}.get(
    c20.get(h), "commuter, KC metro" if h in kc else "commuter, Wichita ring")
co = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
nm = dict(zip(co.STATEFP + co.COUNTYFP, co.COUNAME))
SETS = {"all Advan destinations (primary)": X_all, "common destination set": X_c}
E = {s: {m: per_county(X.index.get_level_values(0).values, X.advan.values, X[m].values) for m in ("fitted", "public", "corrected")} for s, X in SETS.items()}
H = E["common destination set"]["fitted"].index
g = pd.Series({h: seg(h) for h in H})
n = g.value_counts()
CL = [s for s in ("small rural", "indep. towns", "hubs") if n.get(s, 0) >= 5]
small = [h for h in H if g[h] not in CL]
gg = g.where(g.isin(CL), "commuter (4, pooled)")
cols = CL + ["all", "commuter (4, pooled)"]
print(f"outcome {OUTCOME}; common destination set: {len(X_c)} pairs, {len(H)} Kansas homes; Advan share outside it per county: "
      f"mean {100 * outside.mean():.2f}%, max {100 * outside.max():.1f}% ({nm[outside.idxmax()]})")
LAB = {"fitted": "Advan-fitted in Kansas (counties held out)", "public": "Public model, Missouri settings, nothing tuned in Kansas",
       "corrected": "+ corrections learned in Missouri"}
for sname in SETS:
    for met, mn in (("sw", "share-weighted error, points"), ("lr", "log-ratio error, mean |ln(p/a)|, pairs with Advan share >= 1%")):
        if met == "lr" and sname.startswith("common"):
            continue
        e_ = E[sname]
        print(f"\n### Kansas, {mn}, {sname}")
        print("| Model | " + " | ".join(f"{s} ({n[s]})" for s in CL) + f" | all ({len(H)}) | " + " | ".join(f"{nm[h]} ({g[h]})" for h in small) + " |")
        print("|---|" + "---:|" * (len(CL) + 1 + len(small)))
        for m in ("fitted", "public", "corrected"):
            e = e_[m][met].reindex(H)
            print(f"| {LAB[m]} | " + " | ".join(f"{e[g == s].mean():.2f}" for s in CL) + f" | {e.mean():.2f} | " + " | ".join(f"{e[h]:.2f}" for h in small) + " |")
        print("| 95% CI | " + " | ".join(cols) + " |")
        for x, y in (("public", "fitted"), ("corrected", "fitted"), ("corrected", "public")):
            b = boot_diff((e_[x][met] - e_[y][met]).reindex(H), gg)
            print(f"| {x} - {y} | " + " | ".join(fmt_ci(b[s]) for s in cols) + " |")
        sc = boot_share_closed(e_["public"][met].reindex(H), e_["corrected"][met].reindex(H), e_["fitted"][met].reindex(H), gg)
        print("| share of the public model's gap the corrections close | " + " | ".join(fmt_pct(sc[s]) for s in cols) + " |")

ea = E["all Advan destinations (primary)"]
per = pd.DataFrame({"pub": ea["public"].sw, "cor": ea["corrected"].sw}).reindex(H)
per["d"] = per.cor - per.pub
print("\nCounties the corrections hurt most / help most (share-weighted error, all destinations):")
for h, r in pd.concat([per.sort_values("d").tail(6), per.sort_values("d").head(6)]).iterrows():
    t = X_all.loc[h].sort_values("advan", ascending=False).head(3)
    print(f"  {nm[h]:12s} ({seg(h)}) public {r.pub:.2f} -> {r.cor:.2f} | " + "; ".join(f"{nm[j]} A {100 * x:.0f} p {100 * y:.0f} c {100 * z:.0f}" for j, x, y, z in zip(t.index, t.advan, t.public, t.corrected)))
pd.concat({f"{s}|{m}": e for s, d in E.items() for m, e in d.items()}, axis=1).assign(segment=g, advan_outside=outside.reindex(H)).to_csv(
    A / f"ks_scores{os.environ.get('OUTTAG', '')}.csv")
