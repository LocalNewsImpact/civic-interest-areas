"""Nested model selection for the spillover model: the term search repeated inside each fold.  Missouri, March 2026.

The adopted terms were found by searching candidate terms against the held-out error they are scored on. This script
repeats that search without the held-out county: for each county, every candidate model is scored by leaving out each
of the OTHER counties in turn, the best is refitted on those counties and predicts the held-out county's outlets. The
nested error is the honest figure for having searched; the non-nested error of the chosen model is optimistic.

Outlets: the adopted model's fitted set (analysis/spillover_outlets.csv, `fitted`: well collected, 20+ placed stories,
not NOT_FITTED). Candidate terms (spillover_outlets.py; county counts from spillover_common.market):
  log_outlets, outlets_per_10k, log_print, log_tv   saturation: MARKET outlets, per 10,000 residents, print and digital
                                                    outlets, TV stations (log of 1 + count for the last two)
  log_border_mi, log_border_np                      log miles to the county edge; the same for print and digital only
  log_hub_mi                                        log miles to the nearest town of 25,000+ in another county
  daily_x_<term>                                    the term for print dailies only (outlets_per_10k ... log_hub_mi)
Searches:
  A  documented search: broadcaster + crowded weekly, plus up to 2 of the 13 terms above (93 models)
  B  wider: broadcaster, plus up to 3 of the 13 terms, crowded weekly and log town population (576 models)
"""
import itertools
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spillover_common import FINAL, loo, predict, terms_of  # noqa: E402

root = Path(__file__).resolve().parents[1]
d = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
g = d[d.fitted].copy().reset_index(drop=True)
BASE_T = ["log_outlets", "outlets_per_10k", "log_print", "log_tv", "log_border_mi", "log_hub_mi"]
for t in BASE_T:
    g["daily_x_" + t] = g.daily * g[t]
POOL = BASE_T + ["log_border_np"] + ["daily_x_" + t for t in BASE_T]
assert not g[POOL + ["crowded_weekly", "log_town_pop"]].isna().any().any()
counties = g.fips.unique()
print(f"{len(g)} fitted outlets, {len(counties)} counties; dailies {g.daily.sum()}, crowded weeklies {g.crowded_weekly.sum()}, "
      f"broadcasters {g.broadcast.sum()}")


def mae(terms, data):
    return np.abs(loo(terms, data)).mean()


def search(base, pool, kmax, label):
    models = [tuple(base + list(s)) for k in range(kmax + 1) for s in itertools.combinations(pool, k)]
    full = {m: mae(list(m), g) for m in models}
    best = min(full, key=full.get)
    adopted = tuple(terms_of(FINAL))
    print(f"\n## {label}: {len(models)} models")
    print(f"non-nested best: {' + '.join(best)}: mean {100 * full[best]:.2f}"
          + (f"; adopted: mean {100 * full[adopted]:.2f}" if adopted in full else ""))
    e, picks = [], Counter()
    for c in counties:
        tr, te = g[g.fips != c], g[g.fips == c]
        inner = {m: mae(list(m), tr) for m in models}
        pick = min(inner, key=inner.get)
        picks[pick] += 1
        e.append(predict(tr, te, list(pick)) - te.rate.to_numpy(float))
    e = np.abs(np.concatenate(e))
    print(f"nested: mean {100 * e.mean():.2f}, median {100 * np.median(e):.2f} ({len(e)} outlets)")
    print("chosen in the folds: " + "; ".join(f"{' + '.join(m[len(base):]) or '(base only)'} {n}" for m, n in picks.most_common(5)))
    return e


ea = np.abs(loo(terms_of(FINAL), g))
e0 = np.abs(loo([], g))
print(f"\nadopted ({FINAL.split('~ ')[1]}), not nested: mean {100 * ea.mean():.2f}, median {100 * np.median(ea):.2f}; "
      f"intercept only {100 * e0.mean():.2f} / {100 * np.median(e0):.2f}")
na = search(["broadcast", "crowded_weekly"], POOL, 2, "A, documented search: broadcaster + crowded weekly + up to 2 of 13")
nb = search(["broadcast"], POOL + ["crowded_weekly", "log_town_pop"], 3, "B, wider: broadcaster + up to 3 of 15")
for lab, e in (("A", na), ("B", nb)):
    print(f"nested {lab}: skill against intercept only {1 - e.mean() / e0.mean():+.3f}")
