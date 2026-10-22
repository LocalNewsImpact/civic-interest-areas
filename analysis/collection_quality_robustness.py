"""Is poor collection distorting the models?  Refit on well-collected outlets and counties only.

Good county: county_collection_quality.py's tests (all known newsrooms collected; 95%+ stories with text; 80%+ full
length; 60%+ placed; no paywall). Good outlet: the same text, length and placement tests on the outlet itself.
  SPILLOVER  outlet model (broadcaster + urban share; and + crossover) on all outlets vs good outlets vs outlets in
             good counties: coefficients and leave-one-county-out error
  CORRELATION crossover vs spillover across counties, all vs good counties
  COVERAGE   coverage model's response to travel (log travel beyond gravity), all newsroom counties vs good ones
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

warnings.filterwarnings("ignore")
here = Path(__file__).resolve().parent
root = here.parent
q = pd.read_csv(root / "coverage/source_quality_2026_03.csv", dtype={"source_id": str})
q["text_ok"] = q.local_news / (q.local_news + q.text_unavailable).replace(0, np.nan)
q["full_length"] = 1 - q.short_texts / q.local_news.replace(0, np.nan)
cq = pd.read_csv(root / "analysis/county_collection_quality.csv", dtype={"fips": str})
good_counties = set(cq[(cq.coverage == 1) & (cq.text_ok >= .95) & (cq.full_length >= .8) & (cq.placed >= .6) & ~cq.paywall].fips)
so = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
so = so.merge(q[["canonical_name", "text_ok", "full_length"]].drop_duplicates("canonical_name"), left_on="outlet",
              right_on="canonical_name", how="left")
so["placed_share"] = so.placed / so.outlet.map(q.groupby("canonical_name").local_news.max())
so["good_outlet"] = (so.text_ok >= .95) & (so.full_length >= .8) & (so.placed_share >= .6)
so["good_county"] = so.fips.isin(good_counties)
sets = {"all outlets": so, "good outlets": so[so.good_outlet], "outlets in good counties": so[so.good_county]}


def loo(f, d):
    e = []
    for fp in d.fips.unique():
        tr, te = d[d.fips != fp], d[d.fips == fp]
        e += list(np.abs(smf.glm(f, tr, family=sm.families.Binomial()).fit().predict(te) - te.rate))
    return 100 * np.mean(e)


print("## SPILLOVER")
print("| Outlets | n (counties) | Model | Error | Broadcaster | Urban share | Crossover |\n|---|---|---|---:|---:|---:|---:|")
for lab, d in sets.items():
    for f in ("rate ~ broadcast + pct_urban", "rate ~ broadcast + travel_out + pct_urban", "rate ~ broadcast + travel_out"):
        m = smf.glm(f, d, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.fips)[0]})
        g = lambda k: f"{m.params[k]:+.2f} (p {m.pvalues[k]:.2f})" if k in m.params else "—"
        print(f"| {lab} | {len(d)} ({d.fips.nunique()}) | {f.split('~ ')[1]} | {loo(f, d):.1f} | {g('broadcast')} | {g('pct_urban')} | {g('travel_out')} |")

print("\n## CORRELATION, crossover vs spillover across counties (print and digital)")
for lab, d in sets.items():
    x = d[d.broadcast == 0].groupby("fips").agg(p=("placed", "sum"), s=("spill", "sum"), c=("travel_out", "first"))
    if len(x) > 4:
        r, p = stats.pearsonr(x.c, x.s / x.p)
        print(f"  {lab}: {len(x)} counties, r = {r:.2f} (p {p:.2f})")

sys.path.insert(0, str(here))
from gravity_terms import FACTORS, all_pairs, design  # noqa: E402
pairs = all_pairs(); key = list(zip(pairs.i, pairs.j)); pidx = {k: n for n, k in enumerate(key)}
Xd = design(pairs)
tp = pd.read_csv(root / "analysis/od_predicted.csv", dtype={"i": str, "j": str})
print("\n## COVERAGE: response of stories to travel beyond the gravity prediction")
for version in ("all", "no_broadcast"):
    cp = pd.read_csv(root / f"analysis/coverage_predicted_{version}.csv", dtype={"i": str, "j": str})
    for lab, keep in (("all newsroom counties", None), ("good counties", good_counties)):
        p = cp[["i", "j", "stories"]].merge(tp[["i", "j", "ratio"]], on=["i", "j"])
        if keep is not None:
            p = p[p.i.isin(keep)]
        p = p[p.groupby("i").stories.transform("sum") > 0].reset_index(drop=True)
        rows = [pidx[k] for k in zip(p.i, p.j)]
        X = Xd.iloc[rows][FACTORS].reset_index(drop=True).assign(log_travel_beyond=np.log(p.ratio.clip(lower=1e-3)).values)
        FE = pd.concat([pd.get_dummies(p.i, prefix="o").astype(float), pd.get_dummies(p.j, prefix="d", drop_first=True).astype(float)], axis=1)
        m = sm.GLM(p.stories.values.astype(float), pd.concat([X, FE], axis=1), family=sm.families.Poisson()).fit(cov_type="HC1", maxiter=300)
        print(f"  {version}, {lab}: {p.i.nunique()} newsroom counties, response {m.params['log_travel_beyond']:+.2f} "
              f"(se {m.bse['log_travel_beyond']:.2f})")
