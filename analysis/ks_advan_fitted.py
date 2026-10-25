"""The Advan-fitted benchmark for Kansas: the adopted travel model's form (Poisson, origin and destination fixed
effects; log distance and its square, nonmetro origin x log distance and its square, origin size x log distance,
adjacency, pair commuting out and in) fitted to Kansas Advan (od_ks_2026.csv, Kansas homes, Kansas and Missouri
destinations, out of county), each home county held out (8 folds). Outcome: visits_statewide (Kansas calibration
factors, analysis/calibration_county_month_ks.csv, on the statewide device->person scale used in Missouri); no
pass-through discount (no Kansas road-stop shares). Commuting: LODES 2023 primary jobs (JT01) of residents, in and out of state. Every fold's fit is
checked for convergence (no start values are used). Scored by score_ks.py."""
import csv
import gzip
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

root = Path(__file__).resolve().parents[1]
A = root / "analysis"; REF = root / "census_dl/ref"
OUTCOME = "visits_statewide"     # Kansas factors (calibration_county_month_ks.csv), statewide basis, as Missouri
od = pd.read_csv(A / "od_ks_2026.csv", dtype={"home_county": str, "dest_county": str})
od = od[(od.home_county != od.dest_county) & od.dest_county.str[:2].isin(["20", "29"]) & (od.home_county.str[:2] == "20")]
y = od.groupby(["home_county", "dest_county"])[OUTCOME].sum()
co = pd.read_csv(REF / "CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig"); co["f"] = co.STATEFP + co.COUNTYFP
cp = co.set_index("f")[["LATITUDE", "LONGITUDE", "POPULATION"]].astype(float)
homes = sorted(cp.index[cp.index.str[:2] == "20"]); dests = sorted(set(cp.index[cp.index.str[:2].isin(["20", "29"])]))
P = pd.DataFrame([(i, j) for i in homes for j in dests if i != j], columns=["i", "j"])
la, lo = np.radians(cp.LATITUDE), np.radians(cp.LONGITUDE)
a1, a2, o1, o2 = la.reindex(P.i).values, la.reindex(P.j).values, lo.reindex(P.i).values, lo.reindex(P.j).values
P["dist"] = 2 * 3959 * np.arcsin(np.sqrt(np.sin((a2 - a1) / 2) ** 2 + np.cos(a1) * np.cos(a2) * np.sin((o2 - o1) / 2) ** 2))
P = P[P.dist <= 250].reset_index(drop=True)
P["y"] = [y.get((i, j), 0) for i, j in zip(P.i, P.j)]
adj = pd.read_csv(REF / "county_adjacency2023.txt", sep="|", dtype=str, encoding="latin-1")
ADJ = set(zip(adj["County GEOID"], adj["Neighbor GEOID"]))
rucc = pd.read_csv(REF / "rucc2023.csv", dtype=str, encoding="latin-1"); rucc = rucc[rucc.Attribute == "RUCC_2023"]
nonmetro = {r.FIPS.zfill(5): float(int(r.Value) >= 4) for r in rucc.itertuples()}
flow, work = defaultdict(float), defaultdict(float)
# LODES 2023 primary jobs (JT01) of Kansas and Missouri residents, in state and out of state (no row twice): Kansas
# main + the Kansas-home rows of the MO, NE, OK, CO aux files; Missouri homes from free/mo_residents_od_JT01_2023.csv.gz.
# Out-of-state jobs enter the denominators ("all workers living in i"), as in gravity_terms.py
for f, home in [("free/ks/ks_od_main_JT01_2023.csv.gz", None)] + [(f"free/ks/{s}_od_aux_JT01_2023.csv.gz", "20") for s in ("mo", "ne", "ok", "co")] \
        + [("free/mo_residents_od_JT01_2023.csv.gz", None)]:
    with gzip.open(root / f, "rt") as fh:
        for r in csv.DictReader(fh):
            if home and not r["h_geocode"].startswith(home):
                continue
            h, w, n = r["h_geocode"][:5], r["w_geocode"][:5], float(r["S000"])
            flow[h, w] += n; work[h] += n
ld = np.log(P.dist.values)
X = pd.DataFrame({"log_dist": ld, "log_dist_sq": ld ** 2})
nm_i = P.i.map(nonmetro).fillna(0).values
X["nonmetro_x_ld"] = nm_i * ld; X["nonmetro_x_ld_sq"] = nm_i * ld ** 2
X["log_pop_i_x_ld"] = np.log(cp.POPULATION.reindex(P.i).values) * ld
X["adjacent"] = [float((i, j) in ADJ) for i, j in zip(P.i, P.j)]
X["commute_out"] = [math.log1p(1000 * flow[i, j] / max(work[i], 1)) for i, j in zip(P.i, P.j)]
X["commute_in"] = [math.log1p(1000 * flow[j, i] / max(work[j], 1)) for i, j in zip(P.i, P.j)]
O = pd.get_dummies(P.i, prefix="o").astype(float); D = pd.get_dummies(P.j, prefix="d").astype(float).iloc[:, 1:]
XX = pd.concat([X, O, D], axis=1)
folds = np.array_split(np.random.default_rng(7).permutation(homes), 8)
pred = np.zeros(len(P))
for f in folds:
    test = P.i.isin(f).values; train = ~test
    cc = XX.columns[(XX[train] != 0).any()]
    m = sm.GLM(P.y.values[train], XX.loc[train, cc], family=sm.families.Poisson()).fit(maxiter=300)
    assert m.converged, f"fold not converged ({m.fit_history['iteration']} iterations)"
    lin = XX.loc[test, [c for c in cc if not c.startswith("o_")]].values @ m.params[[c for c in cc if not c.startswith("o_")]].values
    lin = lin - pd.Series(lin).groupby(P.i.values[test]).transform("max").values      # each origin's own maximum
    pred[test] = np.exp(lin)
P["fitted"] = pred
P["fitted"] = P.fitted / P.groupby("i").fitted.transform("sum")
P[["i", "j", "dist", "y", "fitted"]].rename(columns={"i": "home"}).to_csv(A / "ks_advan_fitted.csv", index=False)
print("pairs", len(P), "homes", P.i.nunique())
