"""Like-for-like: the public models (no Advan) against the adopted Advan-fitted travel model, all scored on the same
outcome -- the adopted Advan outcome (calibrated, pass-through discounted; gravity_terms.travel_visits), county ->
county destination shares, January-September 2026, out-of-county Missouri pairs -- with the same measures by county
tier. The Advan-fitted model is the adopted one (gravity_terms.FACTORS, doubly constrained), each county held out in
8 folds (gravity_terms.loco, seed 7: the same folds as travel_commute_pair_test.py); the public models never see
Advan, so they need no holding out. Public tract shares are rolled up to counties, weighted by tract population (2020).
Scores on the common destination set (the public model's destinations, Advan and the fitted model renormalised over
it): share-weighted error and log-ratio error (public_scoring.py).
Output: analysis/compare_shares.csv (advan = observed shares over all Missouri destinations; the Advan-fitted model;
the public builds), read by every public_* script."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
src = open(here / "travel_model_dc_test.py").read().split("models = [")[0]
__file__ = str(here / "travel_model_dc_test.py")
exec(src)
from gravity_terms import loco  # noqa: E402
from public_scoring import per_county, renorm  # noqa: E402

ps_advan = loco(y9, Xof(FACTORS), pairs.i.values)
a = share(y9)
unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(root / "analysis/county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
names = {"class 1": "small rural", "class 2": "independent towns", "class 3": "commuter counties", "class 4": "hubs"}
tr = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_TR29.txt", dtype=str, encoding="utf-8-sig")
pop = dict(zip(tr.STATEFP + tr.COUNTYFP + tr.TRACTCE, tr.POPULATION.astype(float)))
k = {(i, j): n for n, (i, j) in enumerate(zip(pairs.i, pairs.j))}


def roll_up(f, col):
    """Tract shares (out-of-county) -> county shares over Missouri destinations, weighted by tract population."""
    P = pd.read_csv(root / f"analysis/{f}", dtype={"tract": str, "j": str, "home": str})
    P = P[(P.j.str[:2] == "29") & (P.home != P.j)].copy()
    P["w"] = P[col] / P.groupby("tract")[col].transform("sum") * P.tract.map(pop)
    g = P.groupby(["home", "j"]).w.sum()
    ps = np.array([g.get((i, j), 0.0) for i, j in zip(pairs.i, pairs.j)])
    return ps / pd.Series(ps).groupby(pairs.i.values).transform("sum").values


rows = {"Advan-fitted (adopted, counties held out)": ps_advan,
        "public: work only": roll_up("public_model_pairs_base.csv", "work_share"),
        "BASELINE public: work + non-work (employment draw, likelihood)": roll_up("public_model_pairs_base.csv", "combined_share"),
        "four kinds: shopping draw = share beyond home": roll_up("public_model_pairs_comp_share.csv", "combined_share"),
        "needs (draw = capacity), recreation without hotels": roll_up("public_model_pairs_tiers_cap71.csv", "combined_share"),
        "trade area: TAC leakage, Huff on sales, survey decay": roll_up("public_model_pairs_tiers_tac.csv", "combined_share"),
        "trade area: TAC leakage, Huff on sales, lambda 2 (Reilly)": roll_up("public_model_pairs_tiers_tac_l2.csv", "combined_share"),
        "trade area: TAC leakage, Huff on surplus sales, lambda 2": roll_up("public_model_pairs_tiers_tac_surplus_l2.csv", "combined_share"),
        "trade area + every kind at lambda 2 (visitation law)": roll_up("public_model_pairs_tiers_tac_all2.csv", "combined_share")}
common = rows["trade area: TAC leakage, Huff on sales, survey decay"] > 0
ac = renorm(pairs.i.values, a * common)
cls = pd.Series({f: tier.get(unit(f), "class 1") for f in sorted(set(pairs.i))})
E = {lab: per_county(pairs.i.values, ac, renorm(pairs.i.values, ps * common)) for lab, ps in rows.items()}
print(f"common destination set: Advan share outside {100 * pd.Series(a * ~common).groupby(pairs.i.values).sum().mean():.2f}% per county")
base = E["BASELINE public: work + non-work (employment draw, likelihood)"]
print("| Factor | " + " | ".join(names.values()) + " | all |\n|---|" + "---:|" * 5)
cell = lambda e, c: e[(cls.reindex(e.index) == c).values] if c != "all" else e
for lab, e in E.items():
    if lab.startswith(("Advan", "BASELINE")):
        print(f"| **{lab}** | " + " | ".join(f"{cell(e, c).sw.mean():.2f} / {cell(e, c).lr.mean():.2f}" for c in list(names) + ["all"]) + " |")
    else:
        print(f"| {lab} | " + " | ".join(f"{cell(e, c).sw.mean() - cell(base, c).sw.mean():+.2f} / {cell(e, c).lr.mean() - cell(base, c).lr.mean():+.2f}"
                                         for c in list(names) + ["all"]) + " |")
print("(share-weighted error / log-ratio error; factor rows: change against the baseline; negative = better)")

for h, n in (("29019", "Boone"), ("29077", "Greene"), ("29151", "Osage")):
    far = (pairs.i.values == h) & (pairs.dist.values > 60)
    print(f"{n}: share of out-of-county visits beyond 60 miles: Advan {100 * a[far].sum():.1f}; " + "; ".join(f"{l[:40]} {100 * ps[far].sum():.1f}" for l, ps in rows.items() if not l.startswith("Advan")))

for i, j, n in (("29151", "29051", "Osage -> Cole"), ("29007", "29019", "Audrain -> Boone"), ("29007", "29127", "Audrain -> Marion"),
                ("29019", "29051", "Boone -> Cole"), ("29019", "29189", "Boone -> St. Louis County"), ("29077", "29043", "Greene -> Christian"),
                ("29077", "29213", "Greene -> Taney")):
    print(f"{n}: Advan {100 * a[k[(i, j)]]:.1f}%; " + "; ".join(f"{l[:12]} {100 * ps[k[(i, j)]]:.1f}%" for l, ps in rows.items() if not l.startswith("Advan")))

pd.DataFrame({"i": pairs.i, "j": pairs.j, "dist": pairs.dist, "advan": a, **{l: ps for l, ps in rows.items()}}).to_csv(
    root / "analysis/compare_shares.csv", index=False)
