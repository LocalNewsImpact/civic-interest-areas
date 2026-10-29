"""Civic Information Index indicators against the adopted spillover model (spillover_common.FINAL), on its outlets.

Each of 28 indicators added alone (leave one county out). Then an honest check of choosing several: for every held-out
county, indicators are chosen by forward selection (error across five groups of the other counties, up to 4) on the other counties only, and the held-out county is
then predicted -- the selection never sees the county it is scored on. Fitted on the adopted outlets (well
collected, 20+ stories), each county's scored outlets (10+) held out.
Civic Information Index 2026, Internews Listening Post Collective and Brown University Information Futures Lab.
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from spillover_common import FINAL, adopted_split, heldout_error, rural_by_unit  # noqa: E402,F401  the adopted spillover model
root = Path(__file__).resolve().parents[2]
unit = lambda f: "29189" if f == "29510" else f
cii = pd.read_csv(root / "census_dl/civic_index/cii_2026.csv", dtype={"FIPS": str})
cii["FIPS"] = cii.FIPS.str.zfill(5)
cii = cii[cii.FIPS.str.startswith("29")].set_index("FIPS")
cols = [c for c in cii.columns if c not in ("Name", "County", "State", "Abbr", "Population") and "percentile" not in c.lower()]
X = cii[cols].apply(pd.to_numeric, errors="coerce")
w = pd.to_numeric(cii.Population, errors="coerce")
u = X.index.map(unit)
X = X.mul(w, axis=0).groupby(u).sum(min_count=1).div(w.groupby(u).sum(), axis=0)
short = {c: "v" + str(n) for n, c in enumerate(cols)}
label = {v: c for c, v in short.items()}
X = X.rename(columns=short)
# an indicator must vary across Missouri's own counties: some are state or regional figures repeated for every county
# (the volunteer rate is 29.8% everywhere), and standardizing one turns rounding noise into a fake variable
raw = cii[cols].apply(pd.to_numeric, errors="coerce").rename(columns=short)
VARS = [v for v in X.columns if X[v].notna().all() and raw[v].nunique() >= 3]
print("dropped as not varying by county:", [label[v] for v in X.columns if v not in VARS])
X = (X[VARS] - X[VARS].mean()) / X[VARS].std()
so = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str}).join(X, on="fips")
q = pd.read_csv(root / "coverage/source_quality_2026_03.csv").groupby("canonical_name").agg(
    ln=("local_news", "max"), tu=("text_unavailable", "max"), shrt=("short_texts", "max"))
so = so.drop(columns=["ln", "tu", "shrt", "good"], errors="ignore").join(q, on="outlet")   # the outlet file carries them too
so["good"] = (so.ln / (so.ln + so.tu) >= .95) & (1 - so.shrt / so.ln >= .8) & (so.placed / so.ln >= .6)
BASE = FINAL                       # the adopted outlet model (spillover_common.FINAL)
fit = lambda f, d: smf.glm(f, d, family=sm.families.Binomial()).fit()
loo = heldout_error                # fitted on the adopted outlets, each county's scored outlets held out


def cv_err(f, d, folds=5):
    """Error from five groups of counties: fit on four, predict the fifth."""
    cs = np.array(sorted(d.fips.unique())); grp = {c: k % folds for k, c in enumerate(cs)}
    e = []
    for k in range(folds):
        te = d.fips.map(grp).eq(k)
        e += list(np.abs(fit(f, d[~te]).predict(d[te]) - d[te].rate))
    return np.mean(e)


def nested(d, k=4):
    e, picks = [], []
    df, ds = adopted_split(d)
    for fp in ds.fips.unique():
        tr, te = df[df.fips != fp], ds[ds.fips == fp]
        chosen, best = [], cv_err(BASE, tr)
        for _ in range(k):
            trial = [(cv_err(BASE + " + " + " + ".join(chosen + [v]), tr), v) for v in VARS if v not in chosen]
            a, v = min(trial)
            if a >= best - 0.001:
                break
            chosen.append(v); best = a
        picks += chosen
        e += list(np.abs(fit(BASE + "".join(f" + {v}" for v in chosen), tr).predict(te) - te.rate))
    return 100 * np.mean(e), pd.Series(picks).map(label).value_counts()


for lab, d in (("adopted outlets", so),):
    b0 = loo(BASE, d)
    df = adopted_split(d)[0]
    print(f"\n## {lab} ({BASE}): fitted {len(df)}, scored {int(d.scored.sum())} outlets, {df.fips.nunique()} counties; adopted model error {b0:.2f} points")
    res = []
    for v in VARS:
        m = smf.glm(BASE + f" + {v}", df, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(df.fips)[0]})
        res.append((label[v], loo(BASE + f" + {v}", d), m.params[v], m.pvalues[v]))
    r = pd.DataFrame(res, columns=["indicator", "error", "coef", "p"]).sort_values("error")
    print("Each indicator alone (best 8):")
    print(r.head(8).round(3).to_string(index=False))
    e, picks = nested(d)
    print(f"Choosing up to 4 indicators, chosen without seeing the held-out county: error {e:.2f} points (adopted {b0:.2f})")
    print("indicators most often chosen:", picks.head(5).to_dict())
