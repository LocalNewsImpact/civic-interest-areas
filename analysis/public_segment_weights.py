"""STAGE 2: Advan sets the weight of each public travel component, separately for each county class.

Components (each a public model of out-of-county destination shares, rolled up from tracts to counties by 2020
population; built by public_work_model.py, public_nonwork_model.py, public_travel_components.py,
public_travel_tiers.py):
  work                       LODES 2023 gravity
  nonwork: employment draw   CBP retail/health/arts/food employment, survey decay
  nonwork: by degree         the same, survey decay by degree group mixed by tract ACS
  shopping: share beyond home    draw x S_j / (S_j + S_home)
  shopping: excess over home     draw = (S_j - S_home)+
  retail: Huff on sales          trade area capture leakage; attraction = 2025 taxable sales; survey decay
  retail: Huff on surplus, l=2   attraction = sales beyond the county's own expected; distance exponent 2 (Reilly)
  medical, specialty         health care; furniture/electronics/clothing/sporting/department stores
  recreation: arts           arts, entertainment and recreation employment (NAICS 71)
  recreation: with hotels    + accommodation (721)
  visiting                   2020 population
Model     predicted share(i, j) = sum_k w[k, class(i)] x component_k(i, j); w >= 0, summing to 1 in each class
          (softmax), fitted by maximum likelihood of Advan out-of-county shares (January-September 2026), each home
          county weighted equally.
Scored    each county held out of its class's fit (leave one county out), share-weighted absolute error by class --
          the measure of public_vs_advan_compare.py.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

root = Path(__file__).resolve().parents[1]
A = root / "analysis"
S = pd.read_csv(A / "compare_shares.csv", dtype={"i": str, "j": str})
tr = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_TR29.txt", dtype=str, encoding="utf-8-sig")
pop = dict(zip(tr.STATEFP + tr.COUNTYFP + tr.TRACTCE, tr.POPULATION.astype(float)))
COMP = {"work": ("public_model_pairs_base.csv", "work_share"),
        "nonwork: employment draw": ("public_model_pairs_base.csv", "nonwork_share"),
        "nonwork: by degree": ("public_model_pairs_nw_degree.csv", "nonwork_share"),
        "shopping: share beyond home": ("public_model_pairs_comp_share.csv", "shopping"),
        "shopping: excess over home": ("public_model_pairs_comp_excess.csv", "shopping"),
        "retail: Huff on sales": ("public_model_pairs_tiers_tac.csv", "retail"),
        "retail: Huff on surplus, l=2": ("public_model_pairs_tiers_tac_surplus_l2.csv", "retail"),
        "medical": ("public_model_pairs_tiers_tac.csv", "medical"),
        "specialty": ("public_model_pairs_tiers_tac.csv", "specialty"),
        "recreation: arts": ("public_model_pairs_tiers_tac.csv", "recreation"),
        "recreation: with hotels": ("public_model_pairs_comp_share.csv", "recreation"),
        "visiting": ("public_model_pairs_tiers_tac.csv", "visiting")}
key = list(zip(S.i, S.j))
cache = {}
X = []
for name, (f, c) in COMP.items():
    if f not in cache:
        cache[f] = pd.read_csv(A / f, dtype={"tract": str, "j": str, "home": str})
    P = cache[f]
    P = P[(P.j.str[:2] == "29") & (P.home != P.j)]
    w = P[c] / P.groupby("tract")[c].transform("sum") * P.tract.map(pop)
    g = w.groupby([P.home, P.j]).sum()
    x = np.array([g.get(k, 0.0) for k in key])
    X.append(x / pd.Series(x).groupby(S.i.values).transform("sum").values)
X = np.column_stack(X)
names = list(COMP)
a = S.advan.values
unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(A / "county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
cls = np.array([tier.get(unit(i), "class 1") for i in S.i])
LABEL = {"class 1": "small rural", "class 2": "independent towns", "class 3": "commuter counties", "class 4": "hubs"}
EPS = 1e-6


def fit(rows):
    Xr, ar = X[rows], a[rows]

    def f(th):
        w = np.exp(th - th.max()); w /= w.sum()
        p = Xr @ w + EPS
        g_p = -ar / p                                          # d(-sum a log p)/dp
        g_w = Xr.T @ g_p
        return -np.sum(ar * np.log(p)), w * (g_w - w @ g_w)    # chain rule through the softmax
    return (lambda th: (np.exp(th - th.max()) / np.exp(th - th.max()).sum()))(
        minimize(f, np.zeros(X.shape[1]), jac=True, method="L-BFGS-B").x)


err = lambda p, m: 100 * np.sum(a[m] * np.abs(p[m] - a[m])) / np.sum(a[m])
pred = np.zeros(len(a))
weights = {}
for c in LABEL:
    m = cls == c
    weights[c] = fit(m)
    for h in sorted(set(S.i[m])):
        test = (S.i.values == h)
        pred[test] = X[test] @ fit(m & ~test)

ref = {"Advan-fitted": S["Advan-fitted (adopted, counties held out)"].values,
       "public baseline": S["BASELINE public: work + non-work (employment draw, likelihood)"].values,
       "public: work only": X[:, names.index("work")],
       "public: weights by class (counties held out)": pred}
print("| Model | " + " | ".join(LABEL.values()) + " | all |\n|---|" + "---:|" * 5)
for lab, p in ref.items():
    print(f"| {lab} | " + " | ".join(f"{err(p, cls == c):.2f}" for c in LABEL) + f" | {err(p, np.ones(len(a), bool)):.2f} |")
print("\nWeights fitted on all counties of each class:\n| Component | " + " | ".join(LABEL.values()) + " |\n|---|" + "---:|" * 4)
for k, n in enumerate(names):
    print(f"| {n} | " + " | ".join(f"{weights[c][k]:.2f}" for c in LABEL) + " |")
k = {kk: n for n, kk in enumerate(key)}
for i, j, n in (("29151", "29051", "Osage -> Cole"), ("29007", "29019", "Audrain -> Boone"), ("29007", "29127", "Audrain -> Marion"),
                ("29019", "29051", "Boone -> Cole"), ("29019", "29189", "Boone -> St. Louis County")):
    print(f"{n}: Advan {100 * a[k[(i, j)]]:.1f}%  Advan-fitted {100 * ref['Advan-fitted'][k[(i, j)]]:.1f}%  public weights by class {100 * pred[k[(i, j)]]:.1f}%")
pd.DataFrame(weights, index=names).rename(columns=LABEL).to_csv(A / "public_segment_weights.csv")
S.assign(public_segment=pred).to_csv(A / "compare_shares.csv", index=False)
