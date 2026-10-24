"""The spillover model under the selection rule, and the nested figure for that procedure.  Missouri, March 2026.

Rule (spillover_common.FINAL), a joint test:
  1. the adopted set beats intercept only: held-out gain (mean absolute miss with the set minus intercept only, each
     county's outlets predicted by a fit without that county) with a county-paired bootstrap 95% interval excluding 0;
  2. each adopted coefficient's county-cluster bootstrap 95% CI excludes zero;
  3. candidate additions are tested one at a time against the adopted set; the one with the largest gain among those
     whose paired interval excludes zero is added, and the test repeats until none passes.
If 1 or 2 fails, the model is intercept only. Run on all fitted outlets, then repeated inside each fold without the
held-out county (nested): the nested miss is the honest figure for the procedure.

Outlets: the fitted set of analysis/spillover_outlets.csv. Candidates (computed in spillover_outlets.py): outlets per
10,000, all outlets, TV stations, border (print and digital), border (every outlet), miles to a town of 25,000+,
crowded weekly.
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spillover_common import FINAL, cluster_inference, loo, paired_gain, predict, terms_of  # noqa: E402

root = Path(__file__).resolve().parents[1]
d = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
g = d[d.fitted].copy().reset_index(drop=True)
ADOPTED = terms_of(FINAL)
CANDIDATES = ["outlets_per_10k", "log_outlets", "log_tv", "log_border_np", "log_border_mi", "log_hub_mi", "crowded_weekly"]


def select(data, B=999, log=False):
    joint = paired_gain(ADOPTED, [], data, B=B)
    ci = cluster_inference(data, FINAL, B=B)[1].drop("Intercept")
    coef_ok = bool(((ci.ci_lo > 0) | (ci.ci_hi < 0)).all())
    if log:
        print(f"  1. adopted set vs intercept only: gain {joint['gain']:+.2f} [{joint['lo']:+.2f}, {joint['hi']:+.2f}]; "
              f"{'passes' if joint['kept'] else 'fails'}")
        print("  2. coefficient bootstrap CIs: " + "; ".join(f"{t} {r.coef:+.3f} [{r.ci_lo:+.3f}, {r.ci_hi:+.3f}]"
                                                         for t, r in ci.iterrows()) + f"; {'pass' if coef_ok else 'fail'}")
    if not (joint["kept"] and coef_ok):
        return []
    chosen = list(ADOPTED)
    while True:
        cand = {t: paired_gain(chosen + [t], chosen, data, B=B) for t in CANDIDATES if t not in chosen}
        ok = {t: r for t, r in cand.items() if r["kept"]}
        if log:
            print(f"  3. additions to {' + '.join(chosen)}: " + "; ".join(
                f"{t} {r['gain']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}]" for t, r in sorted(cand.items(), key=lambda kv: kv[1]["gain"])))
        if not ok:
            return chosen
        chosen.append(min(ok, key=lambda t: ok[t]["gain"]))


print(f"{len(g)} fitted outlets, {g.fips.nunique()} counties; adopted set {FINAL.split('~ ')[1]}")
full = select(g, B=1999, log=True)
print(f"chosen on all fitted outlets: {' + '.join(full) or '(intercept only)'}")
e, picks = [], Counter()
for c in g.fips.unique():
    tr, te = g[g.fips != c], g[g.fips == c]
    m = select(tr)
    picks[tuple(m)] += 1
    e.append(np.abs(predict(tr, te, m) - te.rate.to_numpy(float)))
e = np.concatenate(e)
ea, e0 = np.abs(loo(ADOPTED, g)), np.abs(loo([], g))
print(f"\nadopted, not nested: mean {100 * ea.mean():.2f}, median {100 * np.median(ea):.2f}; intercept only "
      f"{100 * e0.mean():.2f} / {100 * np.median(e0):.2f}")
print(f"nested (rule applied inside each fold): mean {100 * e.mean():.2f}, median {100 * np.median(e):.2f}; "
      f"skill against intercept only {1 - e.mean() / e0.mean():+.3f}")
print("chosen in the folds: " + "; ".join(f"{' + '.join(k) or '(intercept only)'} {n}" for k, n in picks.most_common()))
