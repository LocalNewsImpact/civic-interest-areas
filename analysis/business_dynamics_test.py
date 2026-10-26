"""Do county business openings and closings improve the crossover or spillover models?  Missouri.

Census Bureau, Business Dynamics Statistics 2023 release, state-county table (bds2023_st_cty.csv). Rates only, never
counts: establishment openings and closings per 100 establishments (BDS estabs_entry_rate, estabs_exit_rate), their
difference (net) and sum (turnover), and jobs created and lost by opening and closing establishments per 100 jobs.
Averaged 2021-2023 so one year's noise in a small county does not carry; St. Louis city and county one unit
(recomputed from the summed counts). Standardized.
  CROSSOVER  share of residents seen outside the county (distinct people, lower bound) ~ log population + rural +
             commuting share + one rate; OLS on the logit; leave one county out.
  SPILLOVER  the adopted outlet model (spillover_common.FINAL) + one rate; fitted on the adopted outlets, each
             county's scored outlets held out (spillover_common.heldout_error).
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from spillover_common import FINAL, adopted_split, heldout_error, rural_by_unit  # noqa: E402,F401  the adopted spillover model
root = Path(__file__).resolve().parents[1]
unit = lambda f: "29189" if f == "29510" else f
b = pd.read_csv(root / "census_dl/bds/bds2023_st_cty.csv", dtype={"st": str, "cty": str}, na_values=["D"])
b = b[(b.st == "29") & b.year.between(2020, 2023)].copy()
b["u"] = (b.st + b.cty).map(unit)
NUM = ["estabs", "estabs_entry", "estabs_exit", "denom", "job_creation_births", "job_destruction_deaths"]
b = b.groupby(["u", "year"])[NUM].sum(min_count=1).reset_index().sort_values(["u", "year"])
# BDS's rate denominator: the average of this year's and last year's establishments (jobs: its own denom column)
b["estab_denom"] = (b.estabs + b.groupby("u").estabs.shift()) / 2
b = b[b.year >= 2021].dropna(subset=NUM)  # two county-years are suppressed (D); left out of numerator and denominator
s = b.groupby("u")[NUM + ["estab_denom"]].sum()
R = pd.DataFrame({
    "opening_rate": 100 * s.estabs_entry / s.estab_denom,
    "closing_rate": 100 * s.estabs_exit / s.estab_denom,
    "job_rate_openings": 100 * s.job_creation_births / s.denom,
    "job_rate_closings": 100 * s.job_destruction_deaths / s.denom,
})
R["net_opening_rate"] = R.opening_rate - R.closing_rate
R["turnover_rate"] = R.opening_rate + R.closing_rate
VARS = list(R.columns)
print(f"{len(R)} county units, 2021-2023. Rates per 100 establishments (jobs: per 100 jobs):")
print(R.describe().loc[["mean", "min", "50%", "max"]].round(1).to_string())
print("Boone / Audrain / Osage:")
print(R.loc[["29019", "29007", "29151"]].round(1).to_string())
Z = (R - R.mean()) / R.std()

# ---- crossover ----
cc = pd.read_csv(root / "analysis/crossover_compare.csv", dtype={"Unnamed: 0": str}).rename(columns={"Unnamed: 0": "fips"}).set_index("fips")
cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str})
cov["u"] = cov.fips.map(unit)
c = cc[["dedup_lower", "commute_pop", "population"]].join(rural_by_unit()).join(Z)
c["y"] = np.log(c.dedup_lower / (1 - c.dedup_lower)); c["log_pop"] = np.log(c.population)
inv = lambda z: 1 / (1 + np.exp(-z))
loo_c = lambda f: 100 * np.mean([abs(inv(smf.ols(f, c.drop(index=k)).fit().predict(c.loc[[k]]).iloc[0]) - c.loc[k, "dedup_lower"]) for k in c.index])
B = "y ~ log_pop + rural + commute_pop"
print(f"\n## CROSSOVER ({len(c)} counties): baseline error {loo_c(B):.1f} points")
res = []
for v in VARS:
    m = smf.ols(B + f" + {v}", c).fit(cov_type="HC1")
    res.append((v, loo_c(B + f" + {v}"), m.params[v], m.pvalues[v]))
print(pd.DataFrame(res, columns=["rate", "error", "coef", "p"]).sort_values("error").round(3).to_string(index=False))

# ---- spillover ----
so = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str}).join(Z, on="fips")
q = pd.read_csv(root / "coverage/source_quality_2026_03.csv").groupby("canonical_name").agg(
    ln=("local_news", "max"), tu=("text_unavailable", "max"), shrt=("short_texts", "max"))
so = so.drop(columns=["ln", "tu", "shrt", "good"], errors="ignore").join(q, on="outlet")   # the outlet file carries them too
so["good"] = (so.ln / (so.ln + so.tu) >= .95) & (1 - so.shrt / so.ln >= .8) & (so.placed / so.ln >= .6)
BASE = FINAL                       # the adopted outlet model (spillover_common.FINAL)
fit = lambda f, d: smf.glm(f, d, family=sm.families.Binomial()).fit()
loo = heldout_error                # fitted on the adopted outlets, each county's scored outlets held out


for lab, d in (("adopted outlets", so),):
    df = adopted_split(d)[0]
    print(f"\n## SPILLOVER, {lab} ({BASE}): fitted {len(df)}, scored {int(d.scored.sum())} outlets, {df.fips.nunique()} counties; adopted model error {loo(BASE, d):.2f} points")
    res = []
    for v in VARS:
        m = smf.glm(BASE + f" + {v}", df, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(df.fips)[0]})
        res.append((v, loo(BASE + f" + {v}", d), m.params[v], m.pvalues[v]))
    print(pd.DataFrame(res, columns=["rate", "error", "coef", "p"]).sort_values("error").round(3).to_string(index=False))
