"""Side tests of the 2026-10-17 spillover model, rerun on the adopted model (spillover_common.FINAL: broadcaster +
log(1 + print and digital outlets in the county)), its outlets and its held-out scheme (fitted on the well-collected
outlets with 20+ placed stories, each county's scored outlets -- 10+ placed stories -- predicted by a fit without that
county; mean absolute miss, points). Missouri, March 2026.

  1 BY OUTLET TYPE   held-out miss of the adopted model by type (broadcasters; print dailies; print weeklies; other
                     print and digital: frequency from coverage/source_frequency.csv); and the print-outlet term applied
                     to non-weeklies only (log_print x not weekly), the same scores.
  2 WEEKLY ALONE     a print weekly that is its county's only print outlet: by the registry (log_print = log 2), by the
                     outlets collected (the only outlet of its county in spillover_outlets.csv), any print weekly; each
                     added to the adopted model: coefficient with CRV3 p (spillover_common.cluster_inference) and the
                     held-out gain with a county-paired interval (spillover_common.paired_gain).
  3 CROWDED WEEKLIES  median spillover of print weeklies in a county with a daily and a TV station (crowded_weekly)
                     against the other fitted outlets; and the adopted model fitted on all 128 outlets (no quality
                     restriction, no story floor beyond 10), scored the same way, against the adopted fit.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spillover_common import (FINAL, adopted_split, cluster_inference, frequency, heldout_error, loo,  # noqa: E402
                              paired_gain, terms_of)

warnings.filterwarnings("ignore")
root = Path(__file__).resolve().parents[1]
so = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
freq = frequency()
so["weekly"] = ((so.broadcast == 0) & (so.outlet.map(freq).fillna("") == "weekly")).astype(int)
so["kind"] = np.select([so.broadcast == 1, so.daily == 1, so.weekly == 1], ["broadcaster", "print daily", "print weekly"],
                       "other print and digital")
so["log_print_nonweekly"] = so.log_print * (1 - so.weekly)
so["alone_registry"] = (so.weekly.astype(bool) & np.isclose(so.log_print, np.log(2))).astype(int)
so["alone_collected"] = (so.weekly.astype(bool) & (so.groupby("fips").outlet.transform("size") == 1)).astype(int)
fit, sc = adopted_split(so)
print(f"adopted model {FINAL}: fitted {len(fit)} outlets ({fit.fips.nunique()} counties), scored {len(sc)}; "
      f"held-out mean miss {heldout_error(FINAL, so):.2f} points")


def by_kind(formula, fit_, sc_):
    e = np.abs(loo(terms_of(formula), fit_, sc_))
    kinds = pd.concat([sc_[sc_.fips == c].kind for c in sc_.fips.unique()]).to_numpy()
    return 100 * e.mean(), {k: (round(100 * e[kinds == k].mean(), 2), int((kinds == k).sum())) for k in sorted(set(kinds))}


print("\n## 1 BY OUTLET TYPE (held-out mean miss, points; scored outlets per type)")
for lab, f in (("adopted", FINAL), ("print-outlet term for non-weeklies only", "rate ~ broadcast + log_print_nonweekly")):
    m_, k_ = by_kind(f, fit, sc)
    print(f"  {lab}: all {m_:.2f}; " + "; ".join(f"{k} {v[0]:.2f} ({v[1]})" for k, v in k_.items()))
_, ci, G = cluster_inference(fit, "rate ~ broadcast + log_print_nonweekly")
print(f"  non-weeklies-only term: coef {ci.loc['log_print_nonweekly', 'coef']:+.3f} (CRV3 p {ci.loc['log_print_nonweekly', 'p_cluster_t']:.3f}, {G} counties)")

print("\n## 2 WEEKLY ALONE IN ITS COUNTY (added to the adopted model)")
for term, lab in (("alone_registry", "alone by the registry"), ("alone_collected", "alone by the outlets collected"),
                  ("weekly", "any print weekly")):
    _, ci, G = cluster_inference(fit, f"{FINAL} + {term}")
    g = paired_gain(terms_of(FINAL) + [term], terms_of(FINAL), fit, sc)
    print(f"  {lab}: {int(fit[term].sum())} fitted outlets; coef {ci.loc[term, 'coef']:+.3f} (CRV3 p {ci.loc[term, 'p_cluster_t']:.3f}); "
          f"gain {g['gain']:+.2f} [{g['lo']:+.2f}, {g['hi']:+.2f}]")

print("\n## 3 CROWDED-COUNTY WEEKLIES; THE ADOPTED MODEL FITTED ON ALL OUTLETS")
cw = fit[fit.crowded_weekly == 1]
print(f"  fitted crowded weeklies: {len(cw)}, median spillover {100 * cw.rate.median():.1f}%; other fitted outlets "
      f"{100 * fit[fit.crowded_weekly == 0].rate.median():.1f}%")
for lab, f in (("adopted", FINAL), ("broadcaster only", "rate ~ broadcast")):
    e_all = 100 * np.abs(loo(terms_of(f), so, so)).mean()
    e_ad = 100 * np.abs(loo(terms_of(f), fit, sc)).mean()
    print(f"  {lab}: fitted on all {len(so)} outlets, scored on all {len(so)} held out: {e_all:.2f}; "
          f"adopted fit and scoring: {e_ad:.2f}")
