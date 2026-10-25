"""Coverage model held-out error under the two rural flags, county-paired.

Runs coverage_model.py twice in this process -- once with the adopted settlement flag (gravity_terms cov.rural: under
50% of the 2020 population in Census urban areas), once with the RUCC nonmetro flag it replaced on 2026-10-25 (1 -
cov.metro) -- and keeps each run's per-newsroom-county held-out errors. Both flags enter the distance block
(rural_i_x_log_dist(_sq)) and the hypothesis term (log_visits_x_rural). Change = settlement - RUCC; 95% interval from
1,000 draws of newsroom counties (seed 7), the same county draws for both flags. Positive = the settlement flag
predicts worse. No files are written (coverage_predicted_*.csv stays the adopted run's).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gravity_terms as gt  # noqa: E402

SRC = HERE / "coverage_model.py"
HOOK = "    E0 = heldout(y, Xa, p, start)\n"
SETTLEMENT = gt.cov.rural.copy()


def run(flag):
    gt.cov["rural"] = SETTLEMENT if flag == "settlement" else (1 - gt.cov.metro).astype(int)
    src = SRC.read_text()
    assert src.count(HOOK) == 1
    g = {"__file__": str(SRC), "__name__": "__main__", "_SAVE": {}}
    exec(compile(src.replace(HOOK, HOOK + "    _SAVE[version] = E0.copy()\n"), str(SRC), "exec"), g)
    return g["_SAVE"]


def bt(d, draws=1000, seed=7):
    rng = np.random.default_rng(seed)
    return np.quantile([d.iloc[rng.integers(0, len(d), len(d))].mean() for _ in range(draws)], [0.025, 0.975])


to_csv = pd.DataFrame.to_csv
pd.DataFrame.to_csv = lambda *a, **k: None
try:
    E = {flag: run(flag) for flag in ("rucc", "settlement")}
finally:
    pd.DataFrame.to_csv = to_csv
    gt.cov["rural"] = SETTLEMENT

switched = gt.cov.index[(gt.cov.metro == 1) & (SETTLEMENT == 1)]
print("\n# RURAL FLAG: settlement vs RUCC, coverage held-out error (points), county-paired")
print("| Version | Metric | RUCC | Settlement | Change [95%] | Counties worse / better |")
print("|---|---|---:|---:|---:|---:|")
for v in E["rucc"]:
    for k, lab in (("travel", "primary: 1%+ of visits"), ("all", "all destinations")):
        a, b = E["rucc"][v][k], E["settlement"][v][k]
        d = (b - a).dropna()
        lo, hi = bt(d)
        print(f"| {v} | {lab} | {a.mean():.3f} | {b.mean():.3f} | {d.mean():+.3f} [{lo:+.3f}, {hi:+.3f}] | "
              f"{int((d > 0).sum())} / {int((d < 0).sum())} |")
d = (E["settlement"]["all"].travel - E["rucc"]["all"].travel).dropna()
s = d[d.index.isin(switched)]
print(f"newsroom counties RUCC metro, settlement rural ({len(s)}): mean change {s.mean():+.3f}; "
      f"other counties {d.drop(s.index).mean():+.3f}")
for f, name in (("29007", "Audrain"), ("29019", "Boone"), ("29151", "Osage")):
    print(f"  {name}: RUCC {E['rucc']['all'].travel[f]:.2f}, settlement {E['settlement']['all'].travel[f]:.2f}")
