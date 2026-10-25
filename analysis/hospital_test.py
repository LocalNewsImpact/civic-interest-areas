"""Do hospital locations improve the crossover, spillover, travel or coverage models?  Missouri, 2026.

Hospitals: analysis/hospitals_mo.csv (CMS general acute, critical access, children's, VA/DoD; no psychiatric, no
clinics; Capital Region added). County terms: has_hospital, hospitals (count). Pair terms (i -> j):
  nearest_hospital      j is the nearest other county with a hospital (2020 population centres)
  nearest_x_none        the same, when i has no hospital of its own
Scored out of sample: crossover and spillover by leaving out one county (crossover p-values HC1; spillover clustered
by county); travel (outcome: the adopted one, calibrated and pass-through discounted) by leaving out one home county
(8 folds, seed 7; 95% bootstrap intervals over counties for the change vs adopted), with the Jan-Jun -> Jul-Sep
stability check (R^2 = 1 - SSE/SST) beside persistence, coefficients with errors clustered by home and destination
county; coverage as coverage_model.py: newsroom counties held out in 8 folds (seed 7), per-county mean absolute share
error on destinations with 1%+ of visits, averaged over counties.
"""
import json
import sys
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
here = Path(__file__).resolve().parent
root = here.parent
sys.path.insert(0, str(here))
from gravity_terms import FACTORS, FIPS, all_pairs, design, miles  # noqa: E402

h = pd.read_csv(root / "analysis/hospitals_mo.csv", dtype={"fips": str})
count = h.fips.value_counts()
hosp_counties = set(count.index)
unit = lambda f: "29189" if f == "29510" else f
nearest = {i: min((j for j in hosp_counties if j != i), key=lambda j: miles(i, j)) for i in FIPS}
print(f"{len(h)} hospitals in {len(hosp_counties)} counties; {len(FIPS) - len(hosp_counties)} counties have none")

# ---- 1 crossover -------------------------------------------------------------------------------------------------
cc = pd.read_csv(root / "analysis/crossover_compare.csv", dtype={"Unnamed: 0": str}).rename(columns={"Unnamed: 0": "fips"}).set_index("fips")
cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str})
cov["u"] = cov.fips.map(unit)
c = cc[["dedup_lower", "commute_pop", "population"]].join(cov.groupby("u").metro.max())
c["y"] = np.log(c.dedup_lower / (1 - c.dedup_lower)); c["log_pop"] = np.log(c.population); c["nonmetro"] = 1 - c.metro
cu = Counter(); [cu.update({unit(f): n}) for f, n in count.items()]
c["has_hospital"] = [float(cu[f] > 0) for f in c.index]; c["log_hospitals"] = np.log1p([cu[f] for f in c.index])
inv = lambda z: 1 / (1 + np.exp(-z))


def loo(f, d):
    return 100 * np.mean([abs(inv(smf.ols(f, d.drop(index=k)).fit().predict(d.loc[[k]]).iloc[0]) - d.loc[k, "dedup_lower"]) for k in d.index])


B = "y ~ log_pop + nonmetro + commute_pop"
print("\n## 1 CROSSOVER (share of residents seen outside the county)")
for lab, f in (("baseline", B), ("+ has hospital", B + " + has_hospital"), ("+ hospitals (log count)", B + " + log_hospitals")):
    m = smf.ols(f, c).fit(cov_type="HC1")
    t = [k for k in m.params.index if k in ("has_hospital", "log_hospitals")]
    print(f"  {lab}: error {loo(f, c):.1f} points" + "".join(f"; {k} {m.params[k]:+.2f} (p {m.pvalues[k]:.3f})" for k in t))

# ---- 2 spillover ---------------------------------------------------------------------------------------------------
so = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
so["has_hospital"] = [float(cu[f] > 0) for f in so.fips]


def loo_o(f):
    return 100 * np.mean(sum((list(np.abs(smf.glm(f, so[so.fips != k], family=sm.families.Binomial()).fit()
                                         .predict(so[so.fips == k]) - so[so.fips == k].rate)) for k in so.fips.unique()), []))


print("\n## 2 SPILLOVER (outlets)")
for lab, f in (("adopted", "rate ~ broadcast + travel_out"), ("+ has hospital", "rate ~ broadcast + travel_out + has_hospital")):
    m = smf.glm(f, so, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(so.fips)[0]})
    print(f"  {lab}: error {loo_o(f):.1f} points" + (f"; has_hospital {m.params['has_hospital']:+.2f} (p {m.pvalues['has_hospital']:.3f})" if "has_hospital" in m.params else ""))

# ---- 3 travel ------------------------------------------------------------------------------------------------------
import gravity_terms as gt  # noqa: E402
pairs = all_pairs()
key = list(zip(pairs.i, pairs.j))
pairs["nearest_hospital"] = [float(nearest[i] == j) for i, j in key]
pairs["nearest_x_none"] = [float(nearest[i] == j and i not in hosp_counties) for i, j in key]
DISC = gt.stop_discount(pairs)
y9, y6, y3 = (gt.travel_visits(pairs, m, disc=DISC) for m in (gt.MONTHS, gt.MONTHS[:6], gt.MONTHS[6:]))
Xd = design(pairs)
print("\n## 3 TRAVEL (leave one home county out; stability: fit Jan-Jun, score Jul-Sep)")
print(gt.persistence(pairs, y6, y3))
ev0 = None
for lab, extra in (("adopted", []), ("+ nearest hospital county", ["nearest_hospital"]),
                   ("+ nearest, and when home has none", ["nearest_hospital", "nearest_x_none"])):
    ev = gt.evaluate(Xd.assign(**{e: pairs[e].values for e in extra}), pairs, y9, y6, y3, extra=extra)
    r = gt.summary(ev["loco"])
    ev0 = ev0 or ev
    d = "" if ev is ev0 else "; change {:+.2f} [{:+.2f}, {:+.2f}]".format(
        r["werr"] - gt.summary(ev0["loco"])["werr"], *gt.boot(ev["loco"], "werr", ref=ev0["loco"]))
    print(f"  {lab}: LOCO weighted share error {r['werr']:.2f}{d}, big-flow error {r['big']:.2f}; Jul-Sep R^2 "
          f"{gt.summary(ev['split'])['r2']:.2%}" + "".join(f"; {e} {ev['m'].params[e]:+.2f} (2-way p {ev['m'].pvalues[e]:.3f})" for e in extra))

def boot_diff(a, b, draws=1000, seed=7):
    """County-paired bootstrap draws of mean(a - b) over counties."""
    d = (a - b).dropna().values
    rng = np.random.default_rng(seed)
    return [d[rng.integers(0, len(d), len(d))].mean() for _ in range(draws)]


# ---- 4 coverage ----------------------------------------------------------------------------------------------------
tp = pd.read_csv(root / "analysis/od_predicted.csv", dtype={"i": str, "j": str})
pidx = {k: n for n, k in enumerate(key)}
print("\n## 4 COVERAGE (coverage_model.py adopted specification; leave one newsroom county out; destinations with 1%+ of visits)")
for version in ("all", "no_broadcast"):
    cp = pd.read_csv(root / f"analysis/coverage_predicted_{version}.csv", dtype={"i": str, "j": str})
    p = cp[["i", "j", "stories"]].merge(tp[["i", "j", "visits"]], on=["i", "j"])
    p = p[p.groupby("i").stories.transform("sum") > 0].reset_index(drop=True)
    rows = [pidx[k] for k in zip(p.i, p.j)]
    pos = (p.visits > 0).values
    lv = np.where(pos, np.log(p.visits.where(pos, 1.0)), 0.0)
    nonmetro = 1 - gt.cov.metro.reindex(p.i).values     # coverage_model.py adopted specification
    base = Xd.iloc[rows][FACTORS].reset_index(drop=True).assign(log_visits=lv, zero_visits=(~pos).astype(float),
                                                                log_visits_x_nonmetro=lv * nonmetro)
    FE = pd.concat([pd.get_dummies(p.i, prefix="o").astype(float), pd.get_dummies(p.j, prefix="d", drop_first=True).astype(float)], axis=1)
    y = p.stories.values.astype(float)
    E = {}
    for lab, extra in (("adopted", []), ("+ nearest hospital (and when home has none)", ["nearest_hospital", "nearest_x_none"])):
        Xc = base.assign(**{e: pairs[e].values[rows] for e in extra})
        Xm = pd.concat([Xc, FE], axis=1)
        # as coverage_model.py: newsroom counties held out in 8 folds (seed 7); per-county mean absolute share error on
        # destinations with 1%+ of the county's visits (not selected on stories), averaged over counties
        ps = gt.loco(y, Xm, p.i.values)
        err = 100 * np.abs(ps - gt.shares(y, p.i.values))
        vs = gt.shares(p.visits.values, p.i.values) >= 0.01
        per = pd.Series(err[vs]).groupby(p.i.values[vs]).mean()
        E[lab] = per
        d = "" if lab == "adopted" else "; change {:+.2f} [{:+.2f}, {:+.2f}]".format(
            (per - E["adopted"]).mean(), *np.quantile(boot_diff(per, E["adopted"]), [.025, .975]))
        mf = sm.GLM(y, Xm, family=sm.families.Poisson()).fit(maxiter=300)
        print(f"  {version} {lab}: error {per.mean():.2f} points{d}" + "".join(f"; {e} {mf.params[e]:+.2f}" for e in extra))
