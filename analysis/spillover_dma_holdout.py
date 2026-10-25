"""Is the adopted spillover model fitted to one TV market? Leave one market (DMA) out.  Missouri, March 2026.

For each DMA, the adopted model (spillover_common.FINAL) is refitted without any of that market's outlets and predicts
them. Each market's held-out miss is set beside its in-sample miss (the full fit) for the same outlets, and beside the
miss of an intercept-only model fitted the same way (skill = 1 - held-out miss / intercept-only miss): a model tuned
to a market misses it by much more when the market is held out. Scored on the fitted outlets (analysis/spillover_
outlets.csv, `fitted`). Mention and Sports weights are definitions (spillover_common); this compares markets, not
weights. Writes analysis/spillover_dma_holdout.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spillover_common import FINAL, county_dma, predict, terms_of  # noqa: E402

root = Path(__file__).resolve().parents[1]
T = terms_of(FINAL)
d = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
dma = county_dma(dtype=str).set_index("county_geoid").dma_name
g = d[d.fitted].copy()
g["dma"] = g.fips.map(dma)
assert g.dma.notna().all(), g[g.dma.isna()].outlet.tolist()
g["in_sample"] = predict(g, g, T)
rows = []
for m, te in g.groupby("dma"):
    tr = g[g.dma != m]
    p, p0 = predict(tr, te, T), predict(tr, te, [])
    w = te.placed
    rows.append({"dma": m, "outlets": len(te), "counties": te.fips.nunique(),
                 "miss_in_sample": 100 * (te.in_sample - te.rate).abs().mean(),
                 "miss_held_out": 100 * np.abs(p - te.rate).mean(),
                 "miss_intercept_only": 100 * np.abs(p0 - te.rate).mean(),
                 "actual": np.average(te.rate, weights=w), "expected_held_out": np.average(p, weights=w)})
r = pd.DataFrame(rows).sort_values("outlets", ascending=False)
r["skill"] = 1 - r.miss_held_out / r.miss_intercept_only
r.to_csv(root / "analysis/spillover_dma_holdout.csv", index=False)
print(f"adopted model: {FINAL}; {len(g)} fitted outlets in {g.dma.nunique()} markets\n")
print("| Market | Outlets | Counties | Miss in sample | Held out | Intercept only, held out | Skill | Actual | Expected, held out |")
print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
for x in r.itertuples():
    print(f"| {x.dma} | {x.outlets} | {x.counties} | {x.miss_in_sample:.1f} | {x.miss_held_out:.1f} | {x.miss_intercept_only:.1f} | "
          f"{x.skill:+.2f} | {x.actual:.0%} | {x.expected_held_out:.0%} |")
big = r[r.outlets >= 3]
print(f"\nmarkets with 3+ fitted outlets ({len(big)}): mean miss in sample {big.miss_in_sample.mean():.1f}, held out "
      f"{big.miss_held_out.mean():.1f} (gap {(big.miss_held_out - big.miss_in_sample).mean():+.1f}); intercept only held out "
      f"{big.miss_intercept_only.mean():.1f}")
