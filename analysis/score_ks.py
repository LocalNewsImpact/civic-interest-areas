"""Transfer test score: Kansas home counties' out-of-county destination shares (Kansas and Missouri destinations,
Advan Neighborhood Patterns Plus, January-September 2026; od_ks_2026.csv) against the Kansas public model and the
public model with the corrections learned in Missouri (ks_predictions.csv). Share-weighted absolute error (points) by
class, as in Missouri, and the typical miss by pair size."""
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
A = root / "analysis"
od = pd.read_csv(A / "od_ks_2026.csv", dtype={"home_county": str, "dest_county": str})
od = od[(od.home_county != od.dest_county) & od.dest_county.str[:2].isin(["20", "29"])]
adv = od.groupby(["home_county", "dest_county"]).visits.sum()
adv = (adv / adv.groupby(level=0).transform("sum")).rename("advan")
P = pd.read_csv(A / "ks_predictions.csv", dtype={"home": str, "j": str}).set_index(["home", "j"])
P = P.join(adv.rename_axis(["home", "j"]), how="outer")
F = pd.read_csv(A / "ks_advan_fitted.csv", dtype={"home": str, "j": str}).set_index(["home", "j"]).fitted
P = P.join(F, how="left").fillna({"advan": 0, "public": 0, "corrected": 0, "fitted": 0})
P = P[P.index.get_level_values(0).str[:2] == "20"]
for c in ("public", "corrected", "advan", "fitted"):
    P[c] = P[c] / P[c].groupby(level=0).transform("sum")
c20 = pd.read_csv(A / "county_class_k4_20.csv", dtype={"fips": str}).set_index("fips")["class"]
dl = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str).dropna(subset=["FIPS County Code"])
kc = set((dl["FIPS State Code"] + dl["FIPS County Code"])[dl["CBSA Code"] == "28140"])
seg = lambda h: {"class 1": "small rural", "class 2": "indep. towns", "class 4": "hubs"}.get(
    c20.get(h), "commuter: major metro" if h in kc else "commuter: regional hub")
P["seg"] = [seg(h) for h in P.index.get_level_values(0)]
a = P.advan.values
err = lambda col, m: 100 * np.sum(a[m] * np.abs(P[col].values[m] - a[m])) / np.sum(a[m])
SEGS = ["small rural", "indep. towns", "commuter: major metro", "commuter: regional hub", "hubs"]
n = P.reset_index().drop_duplicates("home").seg.value_counts()
print("| Kansas model | " + " | ".join(f"{s} ({n.get(s, 0)})" for s in SEGS) + " | all (105) |\n|---|" + "---:|" * 6)
for col, lab in (("fitted", "Advan-fitted in Kansas (counties held out)"), ("public", "public, best setting per class"), ("corrected", "+ corrections learned in Missouri")):
    print(f"| {lab} | " + " | ".join(f"{err(col, P.seg.values == s):.2f}" for s in SEGS) + f" | {err(col, np.ones(len(a), bool)):.2f} |")
co = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
nm = dict(zip(co.STATEFP + co.COUNTYFP, co.COUNAME))
per = P.assign(e_pub=a * np.abs(P.public - a), e_cor=a * np.abs(P.corrected - a)).groupby(level=0)[["e_pub", "e_cor"]].sum() * 100
per["d"] = per.e_cor - per.e_pub
print("\nCounties the corrections hurt most / help most:")
for h, r in pd.concat([per.sort_values("d").tail(6), per.sort_values("d").head(6)]).iterrows():
    g = P.loc[h].sort_values("advan", ascending=False).head(3)
    print(f"  {nm[h]:12s} ({seg(h)}) public {r.e_pub:.2f} -> {r.e_cor:.2f} | " + "; ".join(f"{nm[j]} A {100 * x:.0f} p {100 * y:.0f} c {100 * z:.0f}" for j, x, y, z in zip(g.index, g.advan, g.public, g.corrected)))
