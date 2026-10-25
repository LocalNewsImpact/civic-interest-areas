"""What makes the public model so much worse than the Advan-fitted one? Two views.

1  Take the Advan-fitted model apart: remove one ingredient at a time and re-score (each county held out, 8 folds,
   share-weighted error by class). Ingredients: destination fixed effects (each county's own measured draw, replaced
   by public destination measures: log population, jobs and retail per resident, metro, metro centre), adjacency,
   pair commuting, the flexible distance terms.
2  Where the public reference misses: by destination county, Advan inflow (sum of shares over home counties) against
   the public model's, with the Advan-fitted model's destination effect beside it.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
# the adopted travel model's terms and data (travel_model_dc_test.py preamble: pairs, X0, O, Dd, y9, share, ...)
exec(open(here / "travel_model_dc_test.py").read().split("models = [")[0])
from gravity_terms import FACTORS, loco  # noqa: E402
unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(root / "analysis/county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
names = {"class 1": "small rural", "class 2": "independent towns", "class 3": "commuter counties", "class 4": "hubs"}
iu = np.array([unit(i) for i in pairs.i])
cls = np.array([tier.get(u, "class 1") for u in iu])
a = share(y9)
cv = lambda X, counties: loco(y9, X, pairs.i.values)              # each county held out, 8 folds, seed 7
err = lambda ps, mask: 100 * np.sum(a[mask] * np.abs(ps[mask] - a[mask])) / np.sum(a[mask])
PUBLIC_DEST = ["log_pop_j", "log_jobs_pc_j", "log_retail_pc_j", "metro_j", "dest_centre"]
full = FACTORS                                   # the adopted 8 terms (rural flag: Census settlement, 2026-10-25)
dist_flex = ["log_dist_sq", "rural_i_x_log_dist_sq", "log_pop_i_x_log_dist"]
variants = {"Advan-fitted (all ingredients)": (full, True),
            "- destination effects (public destination measures instead)": (full + PUBLIC_DEST, False),
            "- adjacency": ([c for c in full if c != "adjacent"], True),
            "- pair commuting": ([c for c in full if c not in ("commute_out", "commute_in")], True),
            "- flexible distance (log distance only)": ([c for c in full if c not in dist_flex + ["rural_i_x_log_dist"]], True),
            "- destination effects - adjacency": ([c for c in full if c != "adjacent"] + PUBLIC_DEST, False)}
print("| Variant | " + " | ".join(names.values()) + " | all |\n|---|" + "---:|" * 5)
for lab, (cols, fe) in variants.items():
    X = pd.concat([X0[cols + O]] + ([Dd] if fe else []), axis=1)
    ps = cv(X, sorted(set(iu)))
    print(f"| {lab} | " + " | ".join(f"{err(ps, cls == c):.2f}" for c in names) + f" | {err(ps, np.ones(len(a), bool)):.2f} |", flush=True)

# 2  destinations
S = pd.read_csv(root / "analysis/compare_shares.csv", dtype={"i": str, "j": str})
pub = "trade area: TAC leakage, Huff on sales, survey decay"
m = sm.GLM(y9, pd.concat([X0[full + O], Dd], axis=1), family=sm.families.Poisson()).fit(maxiter=300)
fe = {c[2:]: v for c, v in m.params.items() if c.startswith("d_")}
inflow = S.groupby("j")[["advan", pub, "Advan-fitted (adopted, counties held out)"]].sum()
inflow["miss"] = (inflow[pub] - inflow.advan)
inflow["ratio"] = inflow.advan / inflow[pub]
inflow["dest effect"] = [fe.get(j, 0.0) for j in inflow.index]
inflow["name"] = [cov.name[j] for j in inflow.index]
tot = np.abs(S[pub] - S.advan).mul(S.advan).sum()
S["contrib"] = S.advan * np.abs(S[pub] - S.advan)
c = S.groupby("j").contrib.sum() / tot
inflow["share of public error"] = c
top = inflow.sort_values("share of public error", ascending=False).head(15)
print(f"\nDestinations carrying the public model's error: the 15 largest carry {top['share of public error'].sum():.1%} of it. "
      "Audrain, Boone and Osage as destinations (inflow = sum of home counties' shares):")
out = inflow.reindex(["29007", "29019", "29151"])
print(out[["name", "advan", pub, "ratio", "dest effect", "share of public error"]].round(3).rename(columns={pub: "public"}).to_string())
print("\nDestination effect vs public measures, R^2:",
      round(sm.OLS(np.array([fe.get(j, 0) for j in cov.index]), sm.add_constant(X0.groupby(pairs.j)[PUBLIC_DEST].first().reindex(cov.index).values)).fit().rsquared, 3))
