"""Distance form sensitivity: a restricted cubic spline in log distance in place of the adopted quadratic.

The adopted travel model (gravity_terms.FACTORS) carries log distance and its square, both again for rural
home counties. Here those four terms are replaced by a restricted cubic spline in log distance -- 4 knots at the 5th,
35th, 65th and 95th percentiles of log distance over the 13,110 Missouri county pairs (Harrell's standard placement),
so 3 basis terms, linear beyond the outer knots -- and the same 3 terms x rural home county (Census settlement flag). The pair
quantiles put the first knot near 39 miles, beyond most visits, so the spline is linear below it; a second spline puts
the knots at the same percentiles of log distance weighted by visits (where the travel is). Every other
term (log home population x log distance, border, commuting out and in), both sets of fixed effects, the outcome
(gravity_terms.travel_visits) and the estimator (PPML, errors clustered by home and destination county) are the
adopted model's. The adopted model is not changed.

Reported beside the adopted model: held-out share-weighted error (each home county held out, 8 folds, seed 7; 95%
county bootstrap, county-paired change), R^2 (uniform; against fixed effects only), and the distance elasticity at 25
miles for an urban and a rural home county of mean size (delta-method 2-way s.e.).
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import (FACTORS, LOG_D0, MONTHS, all_pairs, boot, candidates, cov, county_stats,  # noqa: E402
                           fe_only_loco, fit_twoway, loco, shares, summary, travel_visits)

warnings.filterwarnings("ignore")
pairs = all_pairs()
o = pairs.i.values
y = travel_visits(pairs, MONTHS)
X0 = candidates(pairs)
FE = [c for c in X0.columns if c.startswith(("o_", "d_"))]
L = np.log(pairs.dist.values)
KNOTS = np.quantile(L, [0.05, 0.35, 0.65, 0.95])


o_ = np.argsort(L)
_c = np.cumsum(travel_visits(pairs, MONTHS)[o_]); _c = _c / _c[-1]
KNOTS_V = np.array([L[o_][np.searchsorted(_c, q)] for q in (0.05, 0.35, 0.65, 0.95)])


def rcs(x, t=KNOTS):
    """Restricted cubic spline basis (Harrell): x and k - 2 nonlinear terms, scaled by (t_k - t_1)^2."""
    x = np.asarray(x, float)
    k = len(t)
    pos = lambda v: np.maximum(v, 0) ** 3
    cols = [x]
    for j in range(k - 2):
        cols.append((pos(x - t[j]) - pos(x - t[k - 2]) * (t[k - 1] - t[j]) / (t[k - 1] - t[k - 2])
                     + pos(x - t[k - 1]) * (t[k - 2] - t[j]) / (t[k - 1] - t[k - 2])) / (t[k - 1] - t[0]) ** 2)
    return np.column_stack(cols)


rural = cov.rural.reindex(pairs.i).values          # Census settlement flag (gravity_terms)
keep = ["log_pop_i_x_log_dist", "adjacent", "commute_out", "commute_in"]
Xa = X0[FACTORS + FE]


def spline_X(t):
    Sx = pd.DataFrame(rcs(L, t), columns=["rcs1", "rcs2", "rcs3"], index=pairs.index)
    for c in list(Sx.columns):
        Sx[f"rural_x_{c}"] = Sx[c] * rural
    return pd.concat([Sx, X0[keep], X0[FE]], axis=1)


def elasticity(m, mi, nm, spline):
    l = np.log(mi)
    g = pd.Series(0.0, index=m.params.index)
    if spline is not False:
        h = 1e-5
        d = (rcs([l + h], spline) - rcs([l - h], spline))[0] / (2 * h)
        for k_, c in enumerate(["rcs1", "rcs2", "rcs3"]):
            g[c] = d[k_]
            if nm:
                g[f"rural_x_{c}"] = d[k_]
    else:
        lc = l - LOG_D0
        g["log_dist"], g["log_dist_sq"] = 1, 2 * lc
        if nm:
            g["rural_i_x_log_dist"], g["rural_i_x_log_dist_sq"] = 1, 2 * lc
    return float(g @ m.params), float(np.sqrt(g @ m.cov_params() @ g))


a = shares(y, o)
pfe = fe_only_loco(y, pairs)
res = {}
for label, X, spline in (("adopted: quadratic in log distance", Xa, False),
                         ("restricted cubic spline, 4 knots at pair quantiles", spline_X(KNOTS), KNOTS),
                         ("restricted cubic spline, 4 knots at visit-weighted quantiles", spline_X(KNOTS_V), KNOTS_V)):
    m = fit_twoway(y, X, pairs)
    st = county_stats(a, loco(y, X, o), o, y, ref_ps=pfe)
    res[label] = (m, st, spline)
print(f"knots (miles): pair quantiles {', '.join(f'{v:.1f}' for v in np.exp(KNOTS))}; "
      f"visit-weighted {', '.join(f'{v:.1f}' for v in np.exp(KNOTS_V))}")
ref = res["adopted: quadratic in log distance"][1]
print("| Distance form | Held-out error [95%] | Change vs adopted [95%] | R^2 | R^2 vs fixed effects only | "
      "Elasticity at 25 mi, urban (s.e.) | rural (s.e.) | In-sample deviance |")
print("|---|---:|---:|---:|---:|---:|---:|---:|")
for label, (m, st, spline) in res.items():
    r = summary(st)
    lo, hi = boot(st, "werr")
    ch = "" if st is ref else "{:+.3f} [{:+.3f}, {:+.3f}]".format(r["werr"] - summary(ref)["werr"], *boot(st, "werr", ref=ref))
    em, en = elasticity(m, 25, False, spline), elasticity(m, 25, True, spline)
    print(f"| {label} | {r['werr']:.3f} [{lo:.2f}, {hi:.2f}] | {ch} | {r['r2']:.1%} | {r['r2_fe']:.1%} | "
          f"{em[0]:+.3f} ({em[1]:.3f}) | {en[0]:+.3f} ({en[1]:.3f}) | {m.deviance / 1e6:,.1f}M |")
print("\nelasticity by distance, urban / rural home county:")
for label, (m, _, spline) in res.items():
    print(f"  {label}: " + "; ".join(f"{mi} mi {elasticity(m, mi, False, spline)[0]:+.2f} / {elasticity(m, mi, True, spline)[0]:+.2f}"
                                     for mi in (10, 25, 50, 100)))
