"""Saturation and border terms for the spillover model.  Missouri, March 2026.

Base: rate ~ broadcast + crowded_weekly, fitted on the adopted model's outlets (analysis/spillover_outlets.csv,
`fitted`: well collected, 20+ placed stories, not NOT_FITTED). Each candidate is added alone and scored by predicting
each county's outlets from all the others (leave one county out), mean and median absolute miss in points, with the
term's coefficient and its county-clustered p (small-cluster correction, t with G-1 df). This is the search that chose
the adopted terms; spillover_nested_selection.py repeats it inside each fold.

Candidates (computed in spillover_outlets.py; county counts from spillover_common.market -- active, or closed but
publishing in March; not EXCLUDE or CAMPUS; St. Louis city and county one unit):
  log_outlets        log of MARKET outlets in the county
  outlets_per_10k    MARKET outlets per 10,000 residents
  log_print / log_tv print and digital outlets; TV stations (log of 1 + count)
  log_border_mi      log miles from the outlet's registry point to the nearest edge of its county
  log_border_np      the same for print and digital outlets only (0 for broadcasters)
  log_hub_mi         log miles to the nearest town of 25,000+ in another county
Each also as a daily-only term (print daily x term), so the dailies can move without changing the weeklies.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from spillover_common import cluster_inference, loo, terms_of  # noqa: E402

root = Path(__file__).resolve().parents[1]
d = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
g = d[d.fitted].copy()
TERMS = ["log_outlets", "outlets_per_10k", "log_print", "log_tv", "log_border_mi", "log_border_np", "log_hub_mi"]
for t in TERMS:
    g[f"daily_x_{t}"] = g.daily * g[t]
assert not g[TERMS].isna().any().any(), "candidate terms missing for a fitted outlet"
BASE = "rate ~ broadcast + crowded_weekly"


def err(f):
    e = np.abs(loo(terms_of(f), g))
    return 100 * e.mean(), 100 * np.median(e)


def coef(f, term):
    r = cluster_inference(g, f, B=0)[1].loc[term]
    return r.coef, r.p_cluster_t


print(f"{len(g)} outlets, {g.fips.nunique()} counties; print dailies {g.daily.sum()}, crowded weeklies "
      f"{g.crowded_weekly.sum()}, broadcasters {g.broadcast.sum()}")
b = err(BASE)
print(f"\n| Term added | Mean miss | Median miss | Coefficient (clustered-t p) |\n|---|---:|---:|---|\n| (base) | {b[0]:.2f} | {b[1]:.2f} | |")
for t in TERMS:
    for lab, term in ((t, t), (f"daily x {t}", f"daily_x_{t}")):
        if lab == "daily x log_border_np":
            continue
        f = BASE + f" + {term}"
        e = err(f)
        c, p = coef(f, term)
        print(f"| {lab} | {e[0]:.2f} | {e[1]:.2f} | {c:+.2f} ({p:.3f}) |")
for f in [BASE + " + daily", BASE + " + daily + daily_x_log_outlets", BASE + " + daily + daily_x_log_border_mi",
          BASE + " + log_border_mi + log_print", BASE + " + log_border_np + log_print"]:
    e = err(f)
    print(f"| {f.replace(BASE + ' + ', '')} | {e[0]:.2f} | {e[1]:.2f} | |")
g.to_csv(root / "analysis/spillover_saturation_terms.csv", index=False)
