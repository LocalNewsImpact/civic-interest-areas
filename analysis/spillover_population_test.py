"""Is the print-outlet term county population under another name?  Missouri, March 2026.

The adopted spillover model (spillover_common.FINAL: rate ~ broadcast + log_print) reads log(1 + print and digital
outlets in the county) as market saturation. Counties with more outlets are also more populous, so the term may stand
for county size. Each alternative below adds or substitutes one population measure on the adopted outlets
(analysis/spillover_outlets.csv, `fitted`): county population (log_pop), the outlet's town population (log_town_pop),
the county's urban share (pct_urban). Coefficients with county-cluster inference (spillover_common.cluster_inference:
CRV3, t with G-1 df; bootstrap CI); held-out mean miss under the adopted scheme (spillover_common.heldout_error).

Also prints the descriptive shares the paper quotes: mean spillover rate of the fitted outlets by broadcaster and, for
print and digital outlets, by the number of print and digital outlets in the county (1 / 2-3 / 4+).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spillover_common import FINAL, cluster_inference, heldout_error  # noqa: E402

root = Path(__file__).resolve().parents[1]
d = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
g = d[d.fitted.astype(bool)].copy()

print(f"{len(g)} fitted outlets in {g.fips.nunique()} counties, {int(g.broadcast.sum())} broadcasters")
print("\n## correlation with log(1 + print and digital outlets in the county), fitted outlets")
for c, lab in [("log_pop", "log county population"), ("log_town_pop", "log town population"), ("pct_urban", "urban share")]:
    print(f"  {lab}: r {g.log_print.corr(g[c]):+.2f}")

print("\n## models (coefficient, CRV3 s.e., p; held-out mean miss, points)")
MODELS = [("adopted", FINAL),
          ("population in place of print outlets", "rate ~ broadcast + log_pop"),
          ("print outlets + county population", "rate ~ broadcast + log_print + log_pop"),
          ("print outlets + town population", "rate ~ broadcast + log_print + log_town_pop"),
          ("print outlets + urban share", "rate ~ broadcast + log_print + pct_urban")]
for lab, f in MODELS:
    _, inf, G = cluster_inference(g, f)
    terms = "; ".join(f"{k} {r.coef:+.3f} (s.e. {r.se_crv3:.3f}, p {r.p_cluster_t:.3f})"
                      for k, r in inf.iterrows() if k != "Intercept")
    print(f"  {lab}: {terms}; held-out {heldout_error(f, d):.2f}")

print("\n## descriptive shares, fitted outlets (mean spillover rate)")
by = g.groupby("broadcast").rate.agg(["count", "mean"])
print(f"  broadcasters {by.loc[1, 'mean']:.1%} (n {by.loc[1, 'count']}); print and digital {by.loc[0, 'mean']:.1%} "
      f"(n {by.loc[0, 'count']})")
p = g[g.broadcast == 0].assign(n_print=lambda x: np.round(np.exp(x.log_print) - 1).astype(int))
band = pd.cut(p.n_print, [-1, 1, 3, np.inf], labels=["1", "2-3", "4+"])
for k, r in p.groupby(band, observed=True).rate.agg(["count", "mean"]).iterrows():
    print(f"  print and digital, {k} print and digital outlets in the county: {r['mean']:.1%} (n {int(r['count'])})")
