"""Exploratory additions to the spillover model: the nested guard.  Missouri, March 2026.

Procedure (spillover_common.py, MODEL PROCEDURE). Broadcaster and print outlets in the county are pre-specified
hypothesis terms (spillover_outlets.py reports their coefficients and drop-one gains); nothing here selects them.
Exploratory candidates are added by a search: starting from the hypothesis pair, add the candidate that lowers the
held-out mean miss most (each county's outlets predicted by a fit without that county), and repeat while one lowers
it; ties go to fewer terms. The search is then repeated inside each fold without the held-out county (nested), and
an addition is ADOPTED only if the nested procedure's held-out gain over the hypothesis pair -- the pair's miss minus
the nested miss, the same outlets; positive = the search helps -- has a county-paired bootstrap 95% interval above
zero (multiplicity guard).

Outlets: the fitted set of analysis/spillover_outlets.csv. Exploratory candidates (computed in spillover_outlets.py):
outlets per 10,000, all outlets, TV stations, border (print and digital), border (every outlet), miles to a town of
25,000+, crowded weekly.
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spillover_common import FINAL, loo, loo_fips, paired_interval, predict, terms_of  # noqa: E402

root = Path(__file__).resolve().parents[1]
d = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
g = d[d.fitted].copy().reset_index(drop=True)
HYPOTHESIS = terms_of(FINAL)
CANDIDATES = ["outlets_per_10k", "log_outlets", "log_tv", "log_border_np", "log_border_mi", "log_hub_mi", "crowded_weekly"]


def search(data, log=False):
    chosen = list(HYPOTHESIS)
    cur = np.abs(loo(chosen, data)).mean()
    while True:
        sc = {t: np.abs(loo(chosen + [t], data)).mean() for t in CANDIDATES if t not in chosen}
        if log:
            print(f"  from {' + '.join(chosen)} ({100 * cur:.2f}): " + "; ".join(
                f"{t} {100 * v:.2f}" for t, v in sorted(sc.items(), key=lambda kv: kv[1])))
        if not sc:
            return chosen
        best = min(sc, key=sc.get)
        if not sc[best] < cur:          # strict improvement only: a tie keeps the smaller model
            return chosen
        chosen.append(best)
        cur = sc[best]


print(f"{len(g)} fitted outlets, {g.fips.nunique()} counties; hypothesis terms {' + '.join(HYPOTHESIS)}")
full = search(g, log=True)
extra = [t for t in full if t not in HYPOTHESIS]
print(f"search on all fitted outlets adds: {' + '.join(extra) or 'nothing'}")
e_nested, picks = [], Counter()
for c in g.fips.unique():
    tr, te = g[g.fips != c], g[g.fips == c]
    m = search(tr)
    picks[tuple(t for t in m if t not in HYPOTHESIS)] += 1
    e_nested.append(np.abs(predict(tr, te, m) - te.rate.to_numpy(float)))
e_nested = np.concatenate(e_nested)
e_h, e_0 = np.abs(loo(HYPOTHESIS, g)), np.abs(loo([], g))
fips = loo_fips(g)
print(f"\nhypothesis pair, held out: mean {100 * e_h.mean():.2f}, median {100 * np.median(e_h):.2f}; intercept only "
      f"{100 * e_0.mean():.2f} / {100 * np.median(e_0):.2f}")
print(f"search with additions, not nested: mean {100 * np.abs(loo(full, g)).mean():.2f}")
print(f"nested search: mean {100 * e_nested.mean():.2f}, median {100 * np.median(e_nested):.2f}")
print("additions chosen in the folds: " + "; ".join(f"{' + '.join(k) or 'none'} {n}" for k, n in picks.most_common()))
for sd in range(1, 6):
    r = paired_interval(e_nested, e_h, fips, seed=sd)
    print(f"GUARD (seed {sd}): gain of the nested search over the hypothesis pair (pair miss - nested miss) {r['gain']:+.2f} points, 95% interval "
          f"{r['lo']:+.2f} to {r['hi']:+.2f}: {'additions ADOPTED' if r['kept'] else 'no addition adopted'}")
