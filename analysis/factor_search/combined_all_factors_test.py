"""Supplement to combined_marginal_test.py: every factor that showed a small effect anywhere, including those the
adopted structure cannot hold. All scored out of sample.

TRAVEL    A adopted (doubly constrained)  vs  B origin effects only + every destination factor (population, stores,
          jobs, metro, area centre) + adopted pair terms + every rejected pair term. Outcome: the adopted one
          (calibrated, pass-through discounted). Primary: leave one home county out (8 folds, seed 7), Jan-Sep. Stability
          check: fit Jan-Jun, score Jul-Sep, beside persistence.
COVERAGE  A adopted (coverage_model.py: gravity terms + log visits + zero-visit indicator + log visits x rural
          newsroom county, gravity_terms cov.rural; excluded_outlets.EXCLUDE, home_fips)  vs  A + every rejected term +
          saturation level (rural home x destination's own stories)  vs  B origin effects only + destination factors
          (population, stores, jobs, metro, area centre, own stories, newsrooms, broadcaster) + every pair term.
          Newsroom counties held out in 8
          folds (seed 7); per-county mean error on destinations with 1%+ of visits.
SPILLOVER adopted outlet model (spillover_common.FINAL) vs + every county factor (cohort, border, population, log newsrooms, one newsroom only,
          travel balance, log outlet stories, broadcaster x travel out); plain and ridge. Leave one county out.
Every held-out error carries a 95% interval from 1,000 bootstrap resamples of the held-out counties (predictions held
fixed), and every comparison the interval of its difference from the adopted model on the same resamples.
"""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
here = Path(__file__).resolve().parents[1]
src = (Path(__file__).resolve().parent / "combined_marginal_test.py").read_text()
exec(src.split("# ---- travel ---")[0].replace("RUN = set(sys.argv[1:])", "RUN = {'none'}"), globals())   # terms + helpers
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.api as sm  # noqa: E402
import statsmodels.formula.api as smf  # noqa: E402

pop_j = np.log(cov.population.reindex(pairs.j).values)
DEST = pd.DataFrame({"log_pop_j": pop_j,
                     "log_retail_pc_j": base["log_retail_pc_j"].values, "log_jobs_pc_j": base["log_jobs_pc_j"].values,
                     "metro_j": base["metro_j"].values, "dest_centre": [float(j in central) for j in pairs.j]})
O_ONLY = [c for c in FE if c.startswith("o_")]
RUN = set(sys.argv[1:]) or {"travel", "coverage", "spillover"}

# ---- travel ----------------------------------------------------------------------------------------------------------
if "travel" in RUN:
    od = pd.read_csv(root / "analysis/od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
    od = od[(od.home_county != "OUT") & (od.home_county != od.dest_county)]
    DISC = gt.stop_discount(pairs)
    y9, y6, y3 = (gt.travel_visits(pairs, m, disc=DISC) for m in (MONTHS, MONTHS[:6], MONTHS[6:]))
    o = pairs.i.values
    share = lambda x: gt.shares(x, o)
    fitp = lambda yy, XX: np.asarray(poisson_fit(yy, XX, 300))
    a9, s3 = share(y9), share(y3)
    MODELS = (("A adopted (destination effects)", pd.concat([base[FACTORS], base[FE]], axis=1)),
              ("B origin effects + every destination factor + every pair term", pd.concat([base[FACTORS], X_extra, DEST, base[O_ONLY]], axis=1)))
    S, T = {}, {"persistence: Jan-Jun observed shares": gt.county_stats(s3, share(y6), o, y3)}
    for label, X in MODELS:
        S[label] = gt.county_stats(a9, gt.loco(y9, X, o, fit=fitp), o, y9)
        T[label] = gt.county_stats(s3, share(np.exp(X.values @ fitp(y6, X))), o, y3)
    ref = S[MODELS[0][0]]
    out("## TRAVEL (primary: leave one home county out, Jan-Sep; [95% interval over counties])")
    out("| Model | Terms | R^2 of shares (1 - SSE/SST) | Weighted share error | Change vs adopted | Big flows (forecast 5%+): abs error | Change vs adopted | Big flows within 0.8-1.25x |")
    out("|---|---:|---:|---:|---:|---:|---:|---:|")
    for label, X in MODELS:
        st, r = S[label], gt.summary(S[label])
        nterms = X.shape[1] - sum(c.startswith(("o_", "d_")) for c in X.columns)
        ci = {k: gt.boot(st, k) for k in ("werr", "big", "r2")}
        dif = {k: ("" if st is ref else "{:+.2f} [{:+.2f}, {:+.2f}]".format(r[k] - gt.summary(ref)[k], *gt.boot(st, k, ref=ref))) for k in ("werr", "big")}
        out(f"| {label} | {nterms} | {r['r2']:.1%} [{ci['r2'][0]:.1%}, {ci['r2'][1]:.1%}] | {r['werr']:.2f} [{ci['werr'][0]:.2f}, {ci['werr'][1]:.2f}] | "
            f"{dif['werr']} | {r['big']:.2f} [{ci['big'][0]:.2f}, {ci['big'][1]:.2f}] | {dif['big']} | {r['within']:.0%} |")
    out("\n## TRAVEL, stability check (not validation): fit Jan-Jun, score Jul-Sep")
    out("| Forecast | R^2 of shares (1 - SSE/SST) | Weighted share error | Big flows (forecast 5%+): abs error | Big flows within 0.8-1.25x |")
    out("|---|---:|---:|---:|---:|")
    for label, st in T.items():
        r = gt.summary(st)
        out(f"| {label} | {r['r2']:.1%} | {r['werr']:.2f} | {r['big']:.2f} | {r['within']:.0%} |")

# ---- coverage --------------------------------------------------------------------------------------------------------
for version in ("all", "no_broadcast"):
    if "coverage" not in RUN:
        break
    p, y, rows, lv, rural, adopted, Oc, Dc = coverage_data(version)
    own_j = np.log1p(np.array([own[j] for j in p.j], float))
    nr_j = np.log1p(np.array([len(outlets[j]) for j in p.j], float))
    bc_j = np.array([float(j in bcast) for j in p.j])
    rejected = pd.DataFrame({
        "ring2": [float(R[i][j] == 2) for i, j in zip(p.i, p.j)], "ring3plus": [float(R[i][j] >= 3) for i, j in zip(p.i, p.j)],
        "lv_x_own": lv * own_j, "lv_x_own_x_rural": lv * own_j * rural,
        "lv_x_newsrooms": lv * nr_j, "lv_x_broadcast": lv * bc_j, "rural_x_own_level": rural * own_j,
    }).join(X_extra.iloc[rows].reset_index(drop=True))
    dest = DEST.iloc[rows].reset_index(drop=True).assign(own_j=own_j, newsrooms_j=nr_j, broadcast_j=bc_j)
    out(f"\n## COVERAGE, {version.replace('_', ' ')} (coverage_model.py adopted specification; newsroom counties held out, 8 folds; per-county mean error)")
    out("| Model | Terms | Mean abs share error (points) [95%] | Change vs adopted [95%] |\n|---|---:|---:|---:|")
    E0 = None
    for label, Xc, FEc in (("A adopted", adopted, pd.concat([Oc, Dc], axis=1)),
                           ("A + every rejected term incl. saturation level", pd.concat([adopted, rejected], axis=1), pd.concat([Oc, Dc], axis=1)),
                           ("B origin effects + destination factors + every pair term", pd.concat([adopted, rejected, dest], axis=1), Oc)):
        errs = coverage_loo(pd.concat([Xc, FEc], axis=1), p, y)
        E0 = E0 or errs
        out(f"| {label} | {Xc.shape[1]} | {boot_errs(errs, per_county=True)} | {'' if errs is E0 else boot_errs(errs, E0, per_county=True)} |")

# ---- spillover -------------------------------------------------------------------------------------------------------
if "spillover" in RUN:
    unit = lambda f: "29189" if f == "29510" else f
    od = pd.read_csv(root / "analysis/od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
    od = od[(od.home_county != "OUT") & (od.home_county != od.dest_county)]
    odu = od.assign(h=od.home_county.map(unit), d=od.dest_county.map(unit))
    odu = odu[odu.h != odu.d]
    balance = odu.groupby("d").visits.sum() / odu.groupby("h").visits.sum()
    SO["one_newsroom"] = [float(len(_nr[f]) == 1) for f in SO.fips]
    SO["log_balance"] = np.log(balance.reindex(SO.fips).values)
    SO["bc_x_travel"] = SO.broadcast * SO.travel_out
    REJ = TYPE_COLS + ["border", "log_pop", "log_newsrooms", "one_newsroom", "log_balance", "log_stories", "travel_out", "bc_x_travel"]
    out(f"\n## SPILLOVER, outlets (spillover_common.FINAL = {SPILL_FINAL}; leave one county out)")
    out("| Model | Mean abs error (points) [95%] | Change vs adopted [95%] |\n|---|---:|---:|")
    E0 = None
    for label, terms, alpha in (("adopted", SPILL_ADOPTED, 0), ("+ every county factor", SPILL_ADOPTED + REJ, 0),
                                ("+ every county factor, ridge 0.05", SPILL_ADOPTED + REJ, 0.05),
                                ("+ every county factor, ridge 0.2", SPILL_ADOPTED + REJ, 0.2)):
        e = spill_errs(terms, alpha)
        E0 = E0 or e
        out(f"| {label} | {boot_errs(e)} | {'' if e is E0 else boot_errs(e, E0)} |")
