"""STAGE 1, public data only: where Missouri residents work, from each census tract to every county in Missouri and the
eight neighbouring states. No Advan, no destination fixed effects -- every destination's pull is a public measure, so
the model applies to any place.

Outcome   LODES 2023 primary jobs (JT01; JT=JT00 all jobs), home tract -> work county: the Missouri main OD file
          (mo_od_main_JT01_2023.csv.gz) plus the auxiliary OD files of IL, KS, IA, AR, OK, NE, TN, KY (Missouri residents
          working in those states); STATE=20: the Kansas main file and the MO, NE, OK, CO auxiliary files.
Builds    DIST=pop TAG=_v1 (Missouri) and STATE=20 DIST=pop TAG=_v1 (Kansas): the files public_travel_tiers.py reads.
Inputs    distance: miles between the tract's 2020 centre of population (CenPop2020_Mean_TR29) and the destination
            county's job centre (county_public_geo.csv, build_public_geography.py), log and log squared
          destination employment: County Business Patterns 2022 total employment (cbp22co.txt), log
          destination population: 2020 Census (CenPop2020_Mean_CO), log
          same county as home; crosses a state line
          rural home (USDA RUCC 2023 nonmetro) x log distance
Estimator conditional Poisson (multinomial over each tract's destinations: tract totals fixed, as origin fixed effects
          would), maximum likelihood by L-BFGS. Destinations: every county within 200 miles of the tract.
Scored    leave counties out (8 folds of home counties): share of each held-out tract's workers going to each county,
          share-weighted absolute error; and the same for the destinations outside Missouri.
"""
import csv
import gzip
import math
import os
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

root = Path(__file__).resolve().parents[1]
REF = root / "census_dl/ref"
ST = os.environ.get("STATE", "29")                 # home state FIPS (29 Missouri, 20 Kansas)
SUF = "" if ST == "29" else f"_{ST}"
tr = pd.read_csv(REF / f"CenPop2020_Mean_TR{ST}.txt", dtype=str, encoding="utf-8-sig")
tr["tract"] = tr.STATEFP + tr.COUNTYFP + tr.TRACTCE
tr[["lat", "lon", "pop"]] = tr[["LATITUDE", "LONGITUDE", "POPULATION"]].astype(float)
co = pd.read_csv(REF / "CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
co["fips"] = co.STATEFP + co.COUNTYFP
co[["lat", "lon", "pop"]] = co[["LATITUDE", "LONGITUDE", "POPULATION"]].astype(float)
STATES = {"29": {"29", "17", "20", "19", "05", "40", "31", "47", "21"}, "20": {"20", "29", "31", "40", "08"}}[ST]
co = co[co.STATEFP.isin(STATES)].set_index("fips")
geo = pd.read_csv(root / "analysis/county_public_geo.csv", dtype={"fips": str}).set_index("fips")
if os.environ.get("DIST", "hub") == "hub":
    co[["lat", "lon"]] = geo.loc[co.index, ["lat", "lon"]].values          # destination = its job centre (build_public_geography.py)
cbp = pd.read_csv(root / "census_dl/cbp/cbp22co.txt", dtype=str)
cbp = cbp[cbp.naics == "------"]
emp = dict(zip(cbp.fipstate + cbp.fipscty, cbp.emp.astype(float)))
rucc = pd.read_csv(REF / "rucc2023.csv", dtype=str, encoding="latin-1")
rucc = rucc[rucc.Attribute == "RUCC_2023"] if "Attribute" in rucc else rucc
rcol = "Value" if "Value" in rucc else rucc.columns[-1]
rural = {r.FIPS.zfill(5): int(float(getattr(r, rcol))) >= 4 for r in rucc.itertuples()} if "FIPS" in rucc else {}

flow = defaultdict(float)
# LODES job type: JT01 primary jobs, one job per worker (adopted 2026-10-24, as gravity_terms.py); JT=JT00 all jobs
JT = os.environ.get("JT", "JT01")
# Missouri JT01: free/mo_residents_od_JT01_2023.csv.gz = the Missouri main file + the Missouri-home rows of the eight
# neighbouring states' aux files (the same rows as reading them one by one); out-of-state jobs enter as destinations
files = ([root / "free/mo_residents_od_JT01_2023.csv.gz"] if JT == "JT01" and ST == "29" else
         [root / ("free/od_2023.csv.gz" if JT == "JT00" else f"free/mo_od_main_{JT}_2023.csv.gz")] + [root / f"free/{s}_od_aux_{JT}_2023.csv.gz" for s in ("il", "ks", "ia", "ar", "ok", "ne", "tn", "ky")]
         if ST == "29" else [root / f"free/ks/ks_od_main_{JT}_2023.csv.gz"] + [root / f"free/ks/{s}_od_aux_{JT}_2023.csv.gz" for s in ("mo", "ne", "ok", "co")])
for f in files:
    with gzip.open(f, "rt") as fh:
        for r in csv.DictReader(fh):
            if r["h_geocode"].startswith(ST):
                flow[(r["h_geocode"][:11], r["w_geocode"][:5])] += float(r["S000"])

R = 3959.0
tla, tlo = np.radians(tr.lat.values)[:, None], np.radians(tr.lon.values)[:, None]
cla, clo = np.radians(co.lat.values)[None, :], np.radians(co.lon.values)[None, :]
D = 2 * R * np.arcsin(np.sqrt(np.sin((cla - tla) / 2) ** 2 + np.cos(tla) * np.cos(cla) * np.sin((clo - tlo) / 2) ** 2))
cid = list(co.index)
home_c = tr.tract.str[:5].values
rows = []
for a, t in enumerate(tr.tract):
    for b in np.flatnonzero(D[a] <= 200):
        j = cid[b]
        rows.append((a, b, t, j, D[a, b], flow.get((t, j), 0.0)))
P = pd.DataFrame(rows, columns=["a", "b", "tract", "j", "miles", "y"])
P["home"] = P.tract.str[:5]
P["same"] = (P.home == P.j).astype(float)
P["state_line"] = (P.j.str[:2] != ST).astype(float)
ld = np.log(np.maximum(P.miles, 1.0))
P["ld"] = ld * (1 - P.same)                      # distance applies between counties; home county has its own term
P["ld2"] = P.ld ** 2
P["log_emp"] = np.log([max(emp.get(j, 1.0), 1.0) for j in P.j])
P["log_pop_j"] = np.log(co.loc[P.j, "pop"].clip(lower=1).values)
P["rural_ld"] = np.array([rural.get(h, False) for h in P.home], float) * P.ld
acs = pd.read_csv(root / f"analysis/tract_acs_2024{SUF}.csv", dtype={"tract": str}).set_index("tract")
acs["log_income"] = np.log(acs.med_income)
for c in ("log_income", "ba_plus", "renter"):                   # tract measure (standardised) x log distance
    v = acs[c].fillna(acs[c].median()); v = (v - v.mean()) / v.std()
    P[{"log_income": "income_ld", "ba_plus": "degree_ld", "renter": "renter_ld"}[c]] = P.tract.map(v).fillna(0).values * P.ld
TERMS = ["same", "ld", "ld2", "log_emp", "log_pop_j", "state_line", "rural_ld"] + [t for t in os.environ.get("EXTRA", "").split(",") if t]
Xall = P[TERMS].values
grp = P.a.values


def nll(beta, X, y, g):
    eta = X @ beta
    m = np.zeros(g.max() + 1); np.maximum.at(m, g, eta)
    e = np.exp(eta - m[g])
    s = np.bincount(g, e, minlength=len(m))
    ytot = np.bincount(g, y, minlength=len(m))
    p = e / s[g]
    ll = np.sum(y * (eta - m[g])) - np.sum(ytot * np.log(np.maximum(s, 1e-300)))
    grad = X.T @ (y - ytot[g] * p)
    return -ll, -grad


def fit(mask):
    res = minimize(nll, np.zeros(len(TERMS)), args=(Xall[mask], P.y.values[mask], grp[mask]), jac=True, method="L-BFGS-B")
    return res.x


def shares(beta, mask):
    eta = Xall[mask] @ beta; g = grp[mask]
    m = np.zeros(g.max() + 1); np.maximum.at(m, g, eta)
    e = np.exp(eta - m[g]); s = np.bincount(g, e, minlength=len(m))
    return e / s[g]


beta = fit(np.ones(len(P), bool))
print("coefficients (all tracts):", dict(zip(TERMS, np.round(beta, 3))))
counties = sorted(set(home_c))
folds = np.array_split(np.random.default_rng(7).permutation(counties), 8)
pred = np.zeros(len(P))
for f in folds:
    test = P.home.isin(f).values
    b = fit(~test)
    pred[test] = shares(b, test)
ytot = P.groupby("a").y.transform("sum").values
act = np.where(ytot > 0, P.y / np.maximum(ytot, 1), 0)
w = act
print(f"held-out tracts: share-weighted error {100 * np.sum(w * np.abs(pred - act)) / np.sum(w):.2f} points; "
      f"R^2 of shares {np.corrcoef(pred, act)[0, 1] ** 2:.3f}")
out = P.state_line.values == 1
print(f"outside the home state: actual {act[out].sum() / act.sum():.2%} of workers' destinations, predicted {pred[out].sum() / pred.sum():.2%}")
P.assign(pred_share=pred, act_share=act).to_csv(root / f"analysis/public_work_model_pairs{SUF}{os.environ.get('TAG', '')}.csv", index=False)
