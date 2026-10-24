"""Is poor collection distorting the models?  Refit on well-collected outlets and counties only.

Good county: county_collection_quality.py's tests (all known newsrooms collected; 95%+ stories with text; 80%+ full
length; 60%+ placed; no paywall). Good outlet: the same text, length and placement tests on the outlet itself (spillover_outlets.py `good`).
  SPILLOVER  the adopted outlet model (spillover_common.FINAL) and the earlier broadcaster + urban share forms, on all
             outlets (10+ placed stories) vs good outlets vs outlets in good counties: coefficients (county-clustered,
             t with G-1 df) and leave-one-county-out error
  CORRELATION crossover (distinct residents seen outside the county) vs print and digital spillover across counties,
             in three subsets -- all outlets, well-collected outlets, outlets in well-collected counties -- each
             unweighted and weighted by the county's print and digital stories; n counties, r, p
  COVERAGE   coverage model's response to travel (log travel beyond gravity), all newsroom counties vs good ones
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
warnings.filterwarnings("ignore")
here = Path(__file__).resolve().parent
root = here.parent
sys.path.insert(0, str(here))
from spillover_common import FINAL, cluster_inference, loo as _loo, terms_of, wcorr  # noqa: E402
q = pd.read_csv(root / "coverage/source_quality_2026_03.csv", dtype={"source_id": str})
q["text_ok"] = q.local_news / (q.local_news + q.text_unavailable).replace(0, np.nan)
q["full_length"] = 1 - q.short_texts / q.local_news.replace(0, np.nan)
cq = pd.read_csv(root / "analysis/county_collection_quality.csv", dtype={"fips": str})
good_counties = set(cq[(cq.coverage == 1) & (cq.text_ok >= .95) & (cq.full_length >= .8) & (cq.placed >= .6) & ~cq.paywall].fips)
so = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
so["good_outlet"] = so.good    # spillover_outlets.py's well-collected test, the one the model is fitted on
so["good_county"] = so.fips.isin(good_counties)
sets = {"all outlets": so, "well-collected outlets": so[so.good_outlet], "outlets in well-collected counties": so[so.good_county]}


def loo(f, d):
    return 100 * np.abs(_loo(terms_of(f), d)).mean()


print("## SPILLOVER")
print("| Outlets | n (counties) | Model | Held-out mean miss | Coefficients (clustered-t p) |\n|---|---|---|---:|---|")
for lab, d in sets.items():
    for f in (FINAL, "rate ~ broadcast + pct_urban", "rate ~ broadcast + travel_out + pct_urban"):
        inf = cluster_inference(d, f, B=0)[1].drop("Intercept")
        cf = "; ".join(f"{k} {r.coef:+.2f} ({r.p_cluster_t:.3f})" for k, r in inf.iterrows())
        print(f"| {lab} | {len(d)} ({d.fips.nunique()}) | {f.split('~ ')[1]} | {loo(f, d):.1f} | {cf} |")

print("\n## CORRELATION, crossover vs print and digital spillover across counties")
print("| Outlets | Counties | r, unweighted (p) | r, weighted by stories (p) |\n|---|---:|---:|---:|")
for lab, d in sets.items():
    x = d[d.broadcast == 0].groupby("fips").agg(p=("placed", "sum"), s=("spill", "sum"), c=("travel_out", "first")).dropna()
    r0, p0, n = wcorr(x.c, x.s / x.p)
    r1, p1, _ = wcorr(x.c, x.s / x.p, x.p)
    print(f"| {lab} | {n} | {r0:+.2f} ({p0:.3f}) | {r1:+.2f} ({p1:.3f}) |")

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
