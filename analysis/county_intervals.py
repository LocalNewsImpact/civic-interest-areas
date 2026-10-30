"""95% intervals for the county figures the article quotes: spillover, crossover, their ratio, and the crossover-spillover
correlation.

SPILLOVER  each county's stories-weighted spillover (spillover_outlets.county_figure) recomputed with every outlet's
           stories resampled (multinomial over its five kinds of story: centred elsewhere, mention, Sports centred, Sports
           mention, home), outlet story counts fixed; 9,999 draws, seed 7, percentile interval. Reads
           analysis/spillover_outlets.csv (run spillover_outlets.py first).
CROSSOVER  the county figure over the 95% interval of the detection slope b (crossover_compare.csv dedup_band_low /
           dedup_band_high): b's uncertainty is the measure's; the device counts are a panel, not a sample of residents.
RATIO      crossover / spillover: the spillover draws against crossover at b, widened to the ends of the b interval.
CORRELATION crossover against print and digital spillover across the counties of the fitted outlets (the Methods rule;
           collection_quality_robustness.py), unweighted: r, p, and a Fisher z 95% interval.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spillover_common import MENTION_WEIGHT as MW
from spillover_common import SPORTS_WEIGHT as SW
from spillover_common import wcorr

root = Path(__file__).resolve().parents[1]
DRAWS, SEED = 9999, 7
COUNTIES = (("Audrain", "29007"), ("Boone", "29019"), ("Osage", "29151"))
d = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
cc = pd.read_csv(root / "analysis/crossover_compare.csv", dtype={"Unnamed: 0": str}).rename(
    columns={"Unnamed: 0": "fips"}).set_index("fips")
WEIGHT = np.array([1, MW, SW, SW * MW, 0])    # centred elsewhere, mention, Sports centred, Sports mention, home


def kinds(x):
    c = np.column_stack([x.centred - x.centred_s, x.mention - x.mention_s, x.centred_s, x.mention_s,
                         x.placed - x.centred - x.mention]).astype(int)
    assert (c >= 0).all() and np.allclose(c @ WEIGHT, x.spill), "outlet counts do not rebuild spillover"
    return c


def draws(x, rng):
    """Stories-weighted spillover of outlets `x`, DRAWS resamples of each outlet's stories."""
    c = kinds(x)
    n = c.sum(axis=1)
    tot = sum(rng.multinomial(k, row / k, size=DRAWS) @ WEIGHT for row, k in zip(c, n))
    return tot / n.sum()


rng = np.random.default_rng(SEED)
print(f"SPILLOVER: stories resampled within each outlet, {DRAWS:,} draws; CROSSOVER: over the 95% interval of b; "
      "RATIO: crossover / spillover")
print("| County | Stories | Spillover [95%] | Crossover [b interval] | Ratio [95%] |\n|---|---:|---|---|---|")
for name, f in COUNTIES:
    for sub, x in (("all", d[d.fips == f]), ("print and digital", d[(d.fips == f) & (d.broadcast == 0)])):
        if sub != "all" and len(x) == len(d[d.fips == f]):
            continue
        s = draws(x, rng)
        point = x.spill.sum() / x.placed.sum()
        lo, hi = np.quantile(s, [.025, .975])
        c, cl, ch = cc.loc[f, ["dedup_lower", "dedup_band_low", "dedup_band_high"]]
        ratio = c / s
        rlo, rhi = min(np.quantile(cl / s, .025), np.quantile(ratio, .025)), max(np.quantile(ch / s, .975),
                                                                                np.quantile(ratio, .975))
        lab = name if sub == "all" else f"{name}, {sub}"
        print(f"| {lab} | {int(x.placed.sum())} | {point:.1%} [{lo:.1%}, {hi:.1%}] | {c:.1%} [{cl:.1%}, {ch:.1%}] | "
              f"{c / point:.2f} [{rlo:.2f}, {rhi:.2f}] |")

g = d[d.fitted.astype(bool) & (d.broadcast == 0)].groupby("fips").agg(p=("placed", "sum"), s=("spill", "sum"))
g["c"] = g.index.map(cc.dedup_lower)
g = g.dropna()
r, p, n = wcorr(g.c, g.s / g.p)
z, se = np.arctanh(r), 1 / np.sqrt(n - 3)
print(f"\nCORRELATION, crossover against print and digital spillover, {n} counties: r = {r:.2f} "
      f"[{np.tanh(z - 1.96 * se):.2f}, {np.tanh(z + 1.96 * se):.2f}], p = {p:.3f}")
