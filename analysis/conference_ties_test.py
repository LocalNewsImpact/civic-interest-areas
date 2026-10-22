"""Do shared high school athletic conferences explain travel the models miss? Boone, Audrain and Osage.

Conference ties: datadesk visuals 34-36 ("<County> County athletic conferences", Mapping paper folder), the counties
whose schools share an athletic conference with a school in the home county; two FIPS corrected (Cooper is 29053, not
29131; Howard is 29089, not 29167). Outcome: Advan out-of-county destination shares, January-September 2026, against
two predictions -- the Advan-fitted travel model (each county held out) and the public baseline -- as actual /
predicted, for conference and other destination counties within 80 miles.
"""
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
TIES = {"29019": ["29159", "29029", "29051", "29007", "29089", "29137", "29175", "29053", "29195", "29151", "29027", "29135",
                  "29045", "29111", "29121", "29127", "29205", "29131"],
        "29007": ["29089", "29137", "29175", "29053", "29195", "29019", "29027", "29127", "29001", "29163", "29113", "29173",
                  "29139", "29219"],
        "29151": ["29051", "29089", "29019", "29027", "29135", "29125", "29055", "29093", "29053", "29131"]}
s = pd.read_csv(root / "analysis/compare_shares.csv", dtype={"i": str, "j": str})
models = {"Advan-fitted": "Advan-fitted (adopted, counties held out)",
          "public baseline": "BASELINE public: work + non-work (employment draw, likelihood)"}
co = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
nm = dict(zip(co.STATEFP + co.COUNTYFP, co.COUNAME))
rows = []
for h, ties in TIES.items():
    x = s[(s.i == h) & (s.dist <= 80)].copy()
    x["tie"] = x.j.isin(ties)
    for lab, c in models.items():
        for tie, g in x.groupby("tie"):
            rows.append({"home": nm[h], "model": lab, "conference": "shared" if tie else "not shared", "counties": len(g),
                         "actual %": round(100 * g.advan.sum(), 1), "predicted %": round(100 * g[c].sum(), 1),
                         "actual / predicted": round(g.advan.sum() / g[c].sum(), 2)})
print(pd.DataFrame(rows).to_string(index=False))
print("\nPooled over the three counties, Advan-fitted model, log(actual/predicted) by pair, destinations within 80 miles:")
x = s[s.i.isin(TIES) & (s.dist <= 80)].copy()
x["tie"] = [j in TIES[i] for i, j in zip(x.i, x.j)]
x["lr"] = np.log((x.advan + 1e-5) / (x[models["Advan-fitted"]] + 1e-5))
w = x.advan + x[models["Advan-fitted"]]
for tie, g in x.groupby("tie"):
    print(f"  {'shared' if tie else 'not shared'}: {len(g)} pairs, share-weighted mean log ratio {np.average(g.lr, weights=w[g.index]):+.2f}")
x["lrp"] = np.log((x.advan + 1e-5) / (x[models["public baseline"]] + 1e-5))
print("  public baseline: " + "; ".join(f"{'shared' if t else 'not shared'} {np.average(g.lrp, weights=(g.advan + g[models['public baseline']])):+.2f}" for t, g in x.groupby("tie")))
for h in TIES:
    g = x[x.i == h].sort_values("advan", ascending=False).head(12)
    print(f"\n{nm[h]}: " + "; ".join(f"{nm[j]}{'*' if t else ''} {100 * a:.1f}/{100 * p:.1f}" for j, t, a, p in zip(g.j, g.tie, g.advan, g[models['Advan-fitted']])))
print("(* shares a conference; actual / Advan-fitted predicted, %)")
