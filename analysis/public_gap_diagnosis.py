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
src = open(here / "travel_commute_pair_test.py").read().split('print("| Model | "')[0]
__file__ = str(here / "travel_commute_pair_test.py")
exec(src)
PUBLIC_DEST = ["log_pop_j", "log_jobs_pc_j", "log_retail_pc_j", "metro_j", "dest_centre"]
full = models["+ commuting out and in"]
dist_flex = ["log_dist_sq", "nonmetro_i_x_log_dist_sq", "log_pop_i_x_log_dist"]
variants = {"Advan-fitted (all ingredients)": (full, True),
            "- destination effects (public destination measures instead)": (full + PUBLIC_DEST, False),
            "- adjacency": ([c for c in full if c != "adjacent"], True),
            "- pair commuting": ([c for c in full if c not in ("commute_out", "commute_in")], True),
            "- flexible distance (log distance only)": ([c for c in full if c not in dist_flex + ["nonmetro_i_x_log_dist"]], True),
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
out = inflow.sort_values("share of public error", ascending=False).head(15)
print("\nDestinations carrying the public model's error (inflow = sum of home counties' shares):")
print(out[["name", "advan", pub, "ratio", "dest effect", "share of public error"]].round(3).rename(columns={pub: "public"}).to_string())
print("\nDestination effect vs public measures, R^2:",
      round(sm.OLS(np.array([fe.get(j, 0) for j in cov.index]), sm.add_constant(X0.groupby(pairs.j)[PUBLIC_DEST].first().reindex(cov.index).values)).fit().rsquared, 3))
