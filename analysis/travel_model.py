"""Statewide travel model, Missouri, Jan-Sep 2026: where each county's residents go.

Visits by residents of county i to county j (i != j), Advan Neighborhood Patterns Plus, on one device -> person scale per
month (od_mo_2026.csv visits_statewide: recorded / statewide units per resident) and summed over the months used. A doubly-constrained gravity model -- fixed effects for every home county
and every destination, and the pair terms in gravity_terms.py (distance centred at 25 miles) -- estimated by Poisson
pseudo-maximum likelihood (PPML, the standard gravity estimator). Standard errors clustered two ways, by home county
and by destination county.

PASS-THROUGH DISCOUNT. A device is counted wherever it stops, so a gas stop on the way to somewhere else counts as a
visit. The county counts cannot separate those stops; the store-level data can (road_stop_share.csv, March Weekly
Patterns): the pair's share of visits at gas stations, convenience stores and fast food within 1 km of an Interstate or
US highway, above the share expected from the destination's own residents' store mix, is removed:
  visits_ij x (1 - discount_ij), pairs with 200+ store-level visitors (build_road_stop_share.py).
SENSITIVITIES (distance elasticity at 25 miles, held-out error, R^2): old county factor (visits), undiscounted, old
discount (discount_old), uncapped destinations only (od_mo_2026_uncapped.csv), distinct people (od_people_mo_2026.csv,
people_lower; St. Louis city and county one unit there, so those pairs use St. Louis County's terms and city is left
out; undiscounted: a person passing through is still a person).

VALIDATION (primary): leave-one-county-out -- 8 folds (seed 7); each held-out home county's destination shares predicted
from a model fitted without any of its travel; scored against its observed Jan-Sep shares. Reference: destination
effects + log distance only. Intervals: 95%, 1,000 bootstrap resamples of home counties (predictions held fixed).
STABILITY CHECK (secondary, not validation): fit Jan-Jun, score Jul-Sep, beside persistence (Jan-Jun observed shares as
the forecast).
Scores (gravity_terms.summary): R^2 = 1 - SSE/SST of shares; share-weighted absolute share error (points); big flows =
pairs FORECAST at 5%+ of the origin's out-of-county visits (selected on the forecast, not the outcome).
Also: the calibration's effect on the centred distance elasticity, and Missouri residents' visits to Kansas, which
od_mo_2026.csv (Missouri destinations only) does not hold.
Output: od_predicted.csv -- every pair's recorded and discounted visits, predicted visits, and shares of the
origin's outflow.
"""
import glob
import json
import sys
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import (FACTORS, LOG_D0, MONTHS, REF_MILES, all_pairs, boot, calibration_factor, fe_only_loco,  # noqa: E402
                           county_stats, cov, design, fit_twoway, loco, root, shares, stop_discount, summary,
                           term_table, travel_visits)

warnings.filterwarnings("ignore")
pairs = all_pairs()
pairs["stop_discount"] = stop_discount(pairs)
X = design(pairs)
FE = [c for c in X.columns if c.startswith(("o_", "d_"))]
ALL = MONTHS
disc = pairs.stop_discount.values
y = travel_visits(pairs, ALL, disc=disc)
m = fit_twoway(y, X, pairs)
pairs["visits_recorded"] = travel_visits(pairs, ALL, discounted=False)
pairs["visits"], pairs["predicted"] = y, m.predict(X).values
for col in ("visits", "predicted"):
    pairs[col + "_share"] = pairs[col] / pairs.groupby("i")[col].transform("sum")
pairs["ratio"] = pairs.visits / pairs.predicted
a = pairs.visits_share.values
ins = summary(county_stats(a, pairs.predicted_share.values, pairs.i.values, y))
print(f"pass-through discount: {1 - y.sum() / pairs.visits_recorded.sum():.1%} of out-of-county visits removed")
print(f"Jan-Sep fit: {len(pairs):,} county pairs, {y.sum():,.0f} visits; IN-SAMPLE R^2 of shares {ins['r2']:.1%}, "
      f"deviance {m.deviance / 1e6:,.1f}M")
print(f"\nCoefficients (distance centred at {REF_MILES:.0f} miles, home population at its mean; "
      "errors clustered by home and by destination county):")
print(term_table(m, FACTORS).round(4).to_string())


def elasticity(mod, mi, nonmetro):
    """d log visits / d log distance at `mi` miles, home county of mean population; delta-method s.e."""
    l = np.log(mi) - LOG_D0
    g = pd.Series(0.0, index=mod.params.index)
    g["log_dist"], g["log_dist_sq"] = 1, 2 * l
    if nonmetro:
        g["nonmetro_i_x_log_dist"], g["nonmetro_i_x_log_dist_sq"] = 1, 2 * l
    return float(g @ mod.params), float(np.sqrt(g @ mod.cov_params() @ g))


print("\nDistance elasticity of visits (home county of mean population), estimate (2-way s.e.):")
print("| Distance | Metro home county | Nonmetro home county |\n|---|---:|---:|")
for mi in (10, 25, 50, 100):
    print(f"| {mi} mi | " + " | ".join("{:+.2f} ({:.2f})".format(*elasticity(m, mi, nm)) for nm in (False, True)) + " |")

# ---- primary validation: leave one county out ------------------------------------------------------------------------
unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(root / "analysis/county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
names = {"class 1": "small rural", "class 2": "independent towns", "class 3": "commuter counties", "class 4": "hubs"}
ctier = pd.Series({f: tier.get(unit(f), "class 1") for f in sorted(set(pairs.i))})
REFL = "reference: destination effects + log distance"
ph = loco(y, X, pairs.i.values)
pfe = fe_only_loco(y, pairs)
S = {"adopted": county_stats(a, ph, pairs.i.values, y, ref_ps=pfe),
     REFL: county_stats(a, loco(y, X[["log_dist"] + FE], pairs.i.values), pairs.i.values, y, ref_ps=pfe),
     "fixed effects only": county_stats(a, pfe, pairs.i.values, y, ref_ps=pfe)}
ref = S["adopted"]
print("\n## VALIDATION: each home county held out (8 folds), Jan-Sep shares; [95% bootstrap interval over counties]")
print("| Model | R^2 of shares (1 - SSE/SST) | R^2 vs fixed effects only | Weighted share error (points) | Big flows: abs error (points) | "
      "Big flows within 0.8-1.25x | Top forecast destination: actual / forecast (median, middle half) | Held-out deviance |")
print("|---|---:|---:|---:|---:|---:|---|---:|")
for label, s in S.items():
    r = summary(s)
    ci = {k: boot(s, k) for k in ("r2", "werr", "big", "within")}
    print(f"| {label} | {r['r2']:.1%} [{ci['r2'][0]:.1%}, {ci['r2'][1]:.1%}] | {r['r2_fe']:.1%} | {r['werr']:.2f} [{ci['werr'][0]:.2f}, "
          f"{ci['werr'][1]:.2f}] | {r['big']:.2f} [{ci['big'][0]:.2f}, {ci['big'][1]:.2f}] | {r['within']:.0%} "
          f"[{ci['within'][0]:.0%}, {ci['within'][1]:.0%}] | {r['top']:.2f}x ({r['top_q1']:.2f}-{r['top_q3']:.2f}) | "
          f"{r['dev'] / 1e6:,.1f}M |")
r = summary(ref)
print(f"adopted, selected on the OUTCOME (biased, for comparison): big flows observed at 5%+ error {r['big_obs']:.2f}; "
      f"top observed destination {r['top_obs']:.2f}x (forecast-selected {r['top']:.2f}x); {r['n_big']} pairs forecast at 5%+")
q = np.quantile((a / ph)[ph >= 0.05], [.1, .5, .9])
print(f"adopted, pairs forecast at 5%+ held out: actual / forecast 10th-90th percentile {q[0]:.2f}-{q[2]:.2f} (median {q[1]:.2f})")
d = boot(S[REFL], "werr", ref=ref)
print(f"weighted share error, reference - adopted: {summary(S[REFL])['werr'] - r['werr']:+.2f} [{d[0]:+.2f}, {d[1]:+.2f}]")
print("\nby tier (county_class_k4.csv), held-out weighted share error [95% interval]:")
for c, n in names.items():
    mk = (ctier.reindex(ref.index) == c).values
    lo, hi = boot(ref, "werr", mask=mk)
    print(f"  {n} ({mk.sum()} counties): {ref[mk].werr.mean():.2f} [{lo:.2f}, {hi:.2f}]")

# ---- secondary: stability across months ------------------------------------------------------------------------------
y6, y3 = travel_visits(pairs, ALL[:6], disc=disc), travel_visits(pairs, ALL[6:], disc=disc)
s3 = shares(y3, pairs.i.values)
m6 = fit_twoway(y6, X, pairs)
T = {"model fitted Jan-Jun": county_stats(s3, shares(m6.predict(X).values, pairs.i.values), pairs.i.values, y3),
     "persistence: Jan-Jun observed shares": county_stats(s3, shares(y6, pairs.i.values), pairs.i.values, y3)}
print("\n## STABILITY CHECK (not validation): Jul-Sep shares forecast from Jan-Jun")
print("| Forecast | R^2 of shares (1 - SSE/SST) | Weighted share error | Big flows: abs error | Big flows within 0.8-1.25x |")
print("|---|---:|---:|---:|---:|")
for label, s in T.items():
    r = summary(s)
    print(f"| {label} | {r['r2']:.1%} | {r['werr']:.2f} | {r['big']:.2f} | {r['within']:.0%} |")
dm = summary(T["model fitted Jan-Jun"])["werr"] - summary(T["persistence: Jan-Jun observed shares"])["werr"]
d = boot(T["model fitted Jan-Jun"], "werr", ref=T["persistence: Jan-Jun observed shares"])
print(f"model - persistence, weighted share error: {dm:+.2f} [{d[0]:+.2f}, {d[1]:+.2f}]")

# ---- sensitivities: outcome definitions ------------------------------------------------------------------------------
def sens_row(label, yy, P, XX, mod=None):
    mod = mod or fit_twoway(yy, XX, P)
    o_ = P.i.values
    st = summary(county_stats(shares(yy, o_), loco(yy, XX, o_), o_, yy, ref_ps=fe_only_loco(yy, P)))
    print(f"| {label} | " + " | ".join("{:+.3f} ({:.3f})".format(*elasticity(mod, REF_MILES, nm)) for nm in (False, True))
          + f" | {st['werr']:.2f} | {st['r2']:.1%} | {st['r2_fe']:.1%} |", flush=True)


print("\n## Sensitivities: distance elasticity at 25 miles, mean-size home county (2-way s.e.); held out (each home county left out)")
print("| Outcome | Metro home | Nonmetro home | Weighted share error | R^2 | R^2 vs fixed effects only |\n|---|---:|---:|---:|---:|---:|")
sens_row("adopted: visits_statewide, highway discount", y, pairs, X, m)
sens_row("county factor (visits, 2026-10-16)", travel_visits(pairs, ALL, col="visits", disc=disc), pairs, X)
sens_row("undiscounted", travel_visits(pairs, ALL, discounted=False), pairs, X)
sens_row("old discount (discount_old)", travel_visits(pairs, ALL, disc=stop_discount(pairs, "discount_old")), pairs, X)
sens_row("uncapped destinations only", travel_visits(pairs, ALL, disc=disc, src="od_mo_2026_uncapped.csv"), pairs, X)
pp = pd.read_csv(root / "analysis/od_people_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
pp = pp[pp.month.isin(ALL) & (pp.home_county != pp.dest_county)].groupby(["home_county", "dest_county"]).people_lower.sum()
P2 = pairs[(pairs.i != "29510") & (pairs.j != "29510")].reset_index(drop=True)
sens_row("distinct people (people_lower; St. Louis one unit)", np.array([pp.get(k, 0.0) for k in zip(P2.i, P2.j)]), P2, design(P2))

# ---- out-of-state travel: Kansas -------------------------------------------------------------------------------------
kv = defaultdict(float)
for f in sorted(glob.glob(str(root / "neighborhood/raw_ks/*.parquet"))):
    for row in pq.read_table(f, columns=["DATE_RANGE_START", "DEVICE_HOME_AREAS"]).to_pylist():
        mo = str(row["DATE_RANGE_START"])[:7]
        for h, v in json.loads(row["DEVICE_HOME_AREAS"] or "{}").items():
            if h.startswith("29"):
                kv[(mo, h[:5])] += v
ks = pd.DataFrame([(mo, h, v) for (mo, h), v in kv.items()], columns=["month", "home", "v"])
ks["v"] = ks.v / calibration_factor(ks.home, ks.month)          # statewide units per resident
ksv = ks[ks.month.isin(ALL)].groupby("home").v.sum()
mov = pairs.groupby("i").visits_recorded.sum()            # statewide scale, not discounted: the same basis as ksv
BORDER = ["29095", "29047", "29165", "29037", "29013", "29217", "29011", "29097", "29145", "29119", "29021", "29005",
          "29087", "29003"]
print("\n## Kansas destinations (neighborhood/raw_ks): Missouri residents' visits, Jan-Sep, statewide scale, undiscounted")
print("| Home county | Visits to Kansas | Share of out-of-county visits (Missouri + Kansas) |\n|---|---:|---:|")
for f in BORDER:
    k = ksv.get(f, 0)
    print(f"| {cov.name[f]} | {k:,.0f} | {k / (k + mov[f]):.1%} |")
kb = sum(ksv.get(f, 0) for f in BORDER)
print(f"| 14 border counties | {kb:,.0f} | {kb / (kb + mov[BORDER].sum()):.1%} |")
print(f"| all Missouri | {ksv.sum():,.0f} | {ksv.sum() / (ksv.sum() + mov.sum()):.1%} |")
pairs.to_csv(root / "analysis/od_predicted.csv", index=False)
