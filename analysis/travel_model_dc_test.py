"""Doubly-constrained gravity: a fixed effect for every destination as well as every origin, so each county's own
overall draw (state capital, university, hospitals, shopping) is measured from the data rather than proxied by
population and stores. What remains to explain is how distance and pair ties distribute the travel.

Outcome: the adopted one (calibrated, pass-through discounted; gravity_terms.travel_visits). Scored as travel_model.py
(gravity_terms.HEAD): in-sample deviance (labelled in-sample); leave-one-county-out (8 folds, seed 7) R^2 of shares
(1 - SSE/SST), share-weighted error with a 95% bootstrap interval over home counties, its change against the adopted
model, held-out deviance, each county's top FORECAST destination (actual / forecast, median and middle half), pairs
FORECAST at 5%+ within 0.8-1.25x; and the Jan-Jun -> Jul-Sep stability check, beside persistence. Added terms: Jan-Sep
fit, errors clustered by home and destination county.

The preamble (above the model list) is exec'd by the other travel_* scripts: pairs, X0, O, Dd, y9, y6, y3, share, y_for.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import (FACTORS, FIPS, HEAD, MONTHS, SINGLY, all_pairs, candidates, cov, evaluate, miles,  # noqa: E402
                           persistence, root, row, shares, stop_discount, summary, travel_visits)

warnings.filterwarnings("ignore")
pairs = all_pairs()
DISC = stop_discount(pairs)
d = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str)
d = d[d["FIPS State Code"] == "29"]
cbsa = {"29" + r[11]: r[1] for r in d.itertuples()}
central = {"29" + r[11] for r in d.itertuples() if r[12] == "Central"}
X0 = candidates(pairs)
X0["dest_centre"] = [int(j in central) for j in pairs.j]
X0["same_area"] = [int(i in cbsa and cbsa.get(i) == cbsa.get(j)) for i, j in zip(pairs.i, pairs.j)]
nearest = {i: min((j for j in central if j != i), key=lambda j: miles(i, j)) for i in FIPS}
X0["nearest_centre"] = [int(nearest[i] == j) for i, j in zip(pairs.i, pairs.j)]
X0["adjacent_centre"] = X0["adjacent"] * X0["dest_centre"]
X0["log_pop_j_x_log_dist"] = X0["log_pop_j"] * X0["log_dist"]                     # big destinations reach farther
O = [c for c in X0.columns if c.startswith("o_")]
Dd = X0[[c for c in X0.columns if c.startswith("d_")]]   # one destination dropped: the origin effects carry the level
ALL = MONTHS


def y_for(months):
    return travel_visits(pairs, months, disc=DISC)


y9, y6, y3 = y_for(ALL), y_for(ALL[:6]), y_for(ALL[6:])
share = lambda x: shares(x, pairs.i.values)
pair = ["log_dist", "rural_i_x_log_dist", "adjacent"]
curved = ["log_dist_sq", "rural_i_x_log_dist_sq"]
base = FACTORS


def Xof(cols, dc=True):
    return pd.concat([X0[cols + O]] + ([Dd] if dc else []), axis=1)


models = [
    ("singly constrained: destination population + stores, distance, border, rural x distance", SINGLY, False),
    ("singly + area centre + curved distance", SINGLY + ["dest_centre", "log_dist_sq"], False),
    ("doubly constrained: distance, rural x distance, border", pair, True),
    ("doubly + curved distance", pair + curved, True),
    ("doubly + curved + same metro/micro area", pair + curved + ["same_area"], True),
    ("doubly + curved + destination size x distance", pair + curved + ["log_pop_j_x_log_dist"], True),
    ("doubly + curved + origin size x distance (adopted before 2026-10-18)", pair + curved + ["log_pop_i_x_log_dist"], True),
    ("doubly + curved + both sizes x distance", pair + curved + ["log_pop_j_x_log_dist", "log_pop_i_x_log_dist"], True),
    ("ADOPTED: + commuting out and in (gravity_terms.FACTORS)", FACTORS, True),
    ("adopted + adjacent centre + nearest centre", FACTORS + ["adjacent_centre", "nearest_centre"], True),
]
if __name__ == "__main__" and "selection" in sys.argv[1:]:
    # SELECTION (authors, final, 2026-10-24): the core gravity terms are tested as BLOCKS, each against the adopted model
    # without it -- distance (the five distance terms), border, commuting (out + in) -- held out (each home county left
    # out, 8 folds, seed 7), county-paired bootstrap, 1,000 draws; never one term at a time. Also the whole set against
    # fixed effects only. Coefficients with 2-way clustered intervals for reference. Exploratory additions are decided
    # by the nested procedure only (combined_marginal_test.py travel_nested_all).
    from gravity_terms import DIST_TERMS, boot, county_stats, fe_only_loco, fit_twoway, loco
    a9, o = share(y9), pairs.i.values
    pfe = fe_only_loco(y9, pairs)
    full = county_stats(a9, loco(y9, Xof(FACTORS), o), o, y9, ref_ps=pfe)
    fe = county_stats(a9, pfe, o, y9, ref_ps=pfe)
    print("| Block removed from the adopted model | Held-out error | Change in error when removed (gain from the block) [95%] |")
    print("|---|---:|---:|")
    print(f"| none (adopted, 8 terms) | {full.werr.mean():.3f} | |")
    for lab, blk in (("distance (log distance, its square, rural x both, home population x distance)", DIST_TERMS),
                     ("border", ["adjacent"]), ("commuting (out and in)", ["commute_out", "commute_in"]),
                     ("all pair terms (fixed effects only)", FACTORS)):
        st = fe if blk is FACTORS else county_stats(a9, loco(y9, Xof([c for c in FACTORS if c not in blk]), o), o, y9, ref_ps=pfe)
        lo, hi = boot(st, "werr", ref=full)
        print(f"| {lab} | {st.werr.mean():.3f} | {st.werr.mean() - full.werr.mean():+.3f} [{lo:+.3f}, {hi:+.3f}] |", flush=True)
    m = fit_twoway(y9, Xof(FACTORS), pairs)
    ci = m.conf_int()
    print("\n| Adopted term | Coef [95%, 2-way clustered] |\n|---|---:|")
    for t in FACTORS:
        print(f"| {t} | {m.params[t]:+.3f} [{ci.loc[t, 0]:+.3f}, {ci.loc[t, 1]:+.3f}] |")
elif __name__ == "__main__":
    EV = {}
    for label, cols, dc in models:
        prev = max((set(c) for lab, c, _ in models if set(c) < set(cols)), key=len, default=set())
        EV[label] = evaluate(Xof(cols, dc), pairs, y9, y6, y3, extra=[c for c in cols if c not in prev])
        print("done:", label, flush=True)
    ref = EV["ADOPTED: + commuting out and in (gravity_terms.FACTORS)"]
    print("\n" + HEAD)
    for label, *_ in models:
        print(row(label, EV[label], ref))
    print(persistence(pairs, y6, y3))
    m9 = ref["m"]
    p9 = m9.predict(Xof(FACTORS)).values
    ps = share(p9)
    from gravity_terms import loco
    ph = loco(y9, Xof(FACTORS), pairs.i.values)
    a = share(y9)
    print("\nstudy counties' main destinations (largest observed), actual / expected share: in-sample, held out")
    for f, n in (("29151", "Osage"), ("29007", "Audrain"), ("29019", "Boone")):
        k = np.flatnonzero(pairs.i.values == f)
        k = k[np.argsort(-a[k])][:4]
        print(" ", n, [(cov.name[pairs.j[x]], f"{a[x] / ps[x]:.2f}", f"{a[x] / ph[x]:.2f}") for x in k])
