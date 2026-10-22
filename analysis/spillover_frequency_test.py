"""Are weeklies less likely to spill over than dailies?  Print and digital outlets, March 2026.

Frequency from the sources registry (sources.metadata frequency; coverage/source_frequency.csv). Groups: daily;
weekly (incl. monthly); between (bi-, tri-, semi-weekly). Outlets with a blank frequency are reported but left out
of the fits. Model as spillover_outlets.py (crossover = distinct residents seen outside the county, lower bound),
print/digital outlets only, plus frequency. Scored by leaving out one county at a time; coefficients with
county-clustered errors.
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
root = Path(__file__).resolve().parents[1]
rows = [l.rstrip("\n").rsplit("|", 1) for l in open(root / "coverage/source_frequency.csv") if "|" in l]
freq = pd.DataFrame(rows, columns=["outlet", "frequency"]).drop_duplicates("outlet").set_index("outlet").frequency
so = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
p = so[so.broadcast == 0].copy()
p["frequency"] = p.outlet.map(freq).fillna("")
group = {"daily": "daily", "weekly": "weekly", "monthly": "weekly", "bi-weekly": "between", "tri-weekly": "between",
         "semi weekly": "between", "semiweekly": "between", "biweekly": "between"}
p["freq"] = p.frequency.map(group).fillna("unknown")
p["weekly"] = (p.freq == "weekly").astype(int)
print("Print/digital outlets by frequency:")
print(p.groupby("freq").agg(outlets=("rate", "size"), median_spillover=("rate", "median"),
                            median_crossover=("travel_out", "median"), median_stories=("placed", "median"))
      .assign(median_spillover=lambda x: (100 * x.median_spillover).round(0).astype(int).astype(str) + "%",
              median_crossover=lambda x: (100 * x.median_crossover).round(0).astype(int).astype(str) + "%").to_string())
k = p[p.freq != "unknown"].copy()
specs = {"crossover only (adopted, print)": "rate ~ travel_out",
         "+ weekly (vs daily and between)": "rate ~ travel_out + weekly",
         "+ frequency, three groups": "rate ~ travel_out + C(freq, Treatment('daily'))"}
print(f"\n| Model ({len(k)} outlets, {k.fips.nunique()} counties) | Leave-one-county-out error (points) | Frequency terms (coef, p) |")
print("|---|---:|---|")
for name, f in specs.items():
    e = []
    for fp in k.fips.unique():
        tr, te = k[k.fips != fp], k[k.fips == fp]
        e += list(np.abs(smf.glm(f, tr, family=sm.families.Binomial()).fit().predict(te) - te.rate))
    m = smf.glm(f, k, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(k.fips)[0]})
    extra = [t for t in m.params.index if t not in ("Intercept", "travel_out")]
    print(f"| {name} | {100 * np.mean(e):.1f} | " + "; ".join(f"{t} {m.params[t]:+.2f} (p {m.pvalues[t]:.3f})" for t in extra) + " |")
m = smf.glm("rate ~ travel_out + weekly", k, family=sm.families.Binomial()).fit()
for f in (0.25, 0.45, 0.65):
    pr = m.predict(pd.DataFrame({"travel_out": [f, f], "weekly": [0, 1]}))
    print(f"  crossover {f:.0%}: daily {pr[0]:.0%}, weekly {pr[1]:.0%}")
