"""Is the adopted spillover model fitted to the Columbia-Jefferson City market? Leave one TV market (DMA) out.

For each DMA, the adopted model is refitted without any of that market's outlets and predicts them. Each market's
held-out miss is set beside its in-sample miss (the full fit) for the same outlets: a model tuned to a market misses it
by much more when the market is held out, and misses it by less than it misses the others in sample.
Scored on the fitted outlets (well collected, 20+ placed stories, not NOT_FITTED). Reads analysis/spillover_outlets.csv
(spillover_outlets.py) and the crawler's county -> DMA table.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

root = Path(__file__).resolve().parents[1]
FINAL = "rate ~ broadcast + crowded_weekly + log_border_mi + log_print"
NOT_FITTED = {"Greene County Commonwealth", "Three Rivers Publishing", "Mid Rivers Newsmagazine"}
d = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
dma = pd.read_csv(Path.home() / "VSCode/NewsCrawler/MizzouNewsCrawler/src/enrichment/reference/county_dma.csv",
                  dtype=str).set_index("county_geoid").dma_name
d["dma"] = d.fips.map(dma)
g = d[d.good & ~d.outlet.isin(NOT_FITTED) & (d.placed >= 20)].copy()
fit = lambda x: smf.glm(FINAL, x, family=sm.families.Binomial()).fit()
g["in_sample"] = fit(g).predict(g)
rows = []
for m, te in g.groupby("dma"):
    tr = g[g.dma != m]
    p = fit(tr).predict(te)
    w = te.placed
    rows.append({"dma": m, "outlets": len(te), "counties": te.fips.nunique(),
                 "miss_in_sample": 100 * (te.in_sample - te.rate).abs().mean(),
                 "miss_held_out": 100 * (p - te.rate).abs().mean(),
                 "actual": np.average(te.rate, weights=w), "expected_held_out": np.average(p, weights=w)})
r = pd.DataFrame(rows).sort_values("outlets", ascending=False)
pd.set_option("display.width", 200)
print(r.round(3).to_string(index=False))
big = r[r.outlets >= 3]
print(f"\nmarkets with 3+ fitted outlets: mean miss in sample {big.miss_in_sample.mean():.1f}, "
      f"held out {big.miss_held_out.mean():.1f} (gap {(big.miss_held_out - big.miss_in_sample).mean():+.1f})")
