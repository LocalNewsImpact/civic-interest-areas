"""Which model best predicts a resident's reach? Leave one month out, January-July 2026.

Reach(m, h, t): share of home block group h's residents seen in tract t in month m (build_reach.py). Each model is
fitted on six months and predicts the seventh, for every home block group and every tract of the Columbia-Jefferson
City TV market; the error is the mean absolute difference from the observed reach, in points. Scored for residents
(every h, t) and for each study town (the median over the town's home block groups, per tract).

  M0 observed   h's mean reach to t over the training months
  M1 gravity    logistic model of reach; the term sets below
  M2 shrunk     M0 pulled toward M1: (people + a * M1) / (residents seen + a), summed over the training months; a
                chosen inside the training months by the same leave-one-month-out (first run: M2 beat M0, M1, the
                county-path model and their mean)

Terms, all computed from the training months only:
  base        distance (log km, and its square), same county, same tract, the tract's pull (mean reach to it from
              the other home block groups), h's propensity (h's mean reach)
  town        the tract is in h's town: the home town is the most relevant place
  direction   share of h's reach to OTHER tracts lying in t's direction from home (kernel cos^4 of the bearing
              difference, about +-35 degrees; tracts within 2 km of home have no direction): interest rises in the
              directions residents travel and falls in the directions they do not
  corridor    share of h's reach to OTHER tracts whose fastest road route (build_routes.py) passes through t: the
              routes between home and the places residents go
  minutes     road minutes in place of straight-line distance
Writes flows/reach/model_scores.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

here = Path(__file__).parent
R = here / "reach"
g = pd.read_csv(R / "reach_2026_jan_jul.csv", dtype={"home_cbg": str, "tract": str})
homes = pd.read_csv(R / "homes.csv", dtype={"home_cbg": str, "county": str, "place": str}).set_index("home_cbg")
tracts = pd.read_csv(R / "tracts.csv", dtype={"tract": str, "county": str, "places": str}).fillna({"places": ""}).set_index("tract")
H, T = list(homes.index), list(tracts.index)
hi, ti = {h: i for i, h in enumerate(H)}, {t: i for i, t in enumerate(T)}
g["hi"], g["ti"] = g.home_cbg.map(hi), g.tract.map(ti)
MONTHS = sorted(g.month.unique())

# fixed matrices, home x tract
la1, lo1 = np.radians(homes.lat.values)[:, None], np.radians(homes.lon.values)[:, None]
la2, lo2 = np.radians(tracts.lat.values)[None, :], np.radians(tracts.lon.values)[None, :]
KM = 6371 * 2 * np.arcsin(np.sqrt(np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2))
BEAR = np.arctan2(np.sin(lo2 - lo1) * np.cos(la2), np.cos(la1) * np.sin(la2) - np.sin(la1) * np.cos(la2) * np.cos(lo2 - lo1))
mn = pd.read_csv(R / "route_minutes.csv", dtype={"home_cbg": str, "tract": str})
MIN = np.full((len(H), len(T)), np.nan)
MIN[mn.home_cbg.map(hi), mn.tract.map(ti)] = mn.minutes.replace(np.inf, np.nan)
MIN = np.where(np.isnan(MIN), KM / 1.2, MIN)          # unroutable: straight line at 72 km/h
SAME_COUNTY = (homes.county.to_numpy(str)[:, None] == tracts.county.to_numpy(str)[None, :]).astype(float)
SAME_TRACT = (homes.index.str[:11].to_numpy(str)[:, None] == np.array(T)[None, :]).astype(float)
SAME_TOWN = np.array([[float(bool(p) and p == p and p in tracts.places[t].split(";")) for t in T] for p in homes.place.fillna("")])
# direction kernel K[h, d, t] and route membership V[h, d, t] (t on the route h -> d, t != d)
far = (KM >= 2).astype(float)
K = np.clip(np.cos(BEAR[:, :, None] - BEAR[:, None, :]), 0, None) ** 4 * far[:, :, None] * far[:, None, :]
K[:, np.arange(len(T)), np.arange(len(T))] = 0
rt = pd.read_csv(R / "routes.csv", dtype=str)
rt = rt[rt.dest_tract != rt.via_tract]
V = np.zeros((len(H), len(T), len(T)))
V[rt.home_cbg.map(hi), rt.dest_tract.map(ti), rt.via_tract.map(ti)] = 1
logit = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))

SPECS = {
    "base": ["ld", "ld2", "same_county", "same_tract", "pull", "lprop"],
    "base+town": ["ld", "ld2", "same_county", "same_tract", "pull", "lprop", "same_town"],
    "base+direction": ["ld", "ld2", "same_county", "same_tract", "pull", "lprop", "ldir"],
    "base+corridor": ["ld", "ld2", "same_county", "same_tract", "pull", "lprop", "lcorr"],
    "base+town+direction+corridor": ["ld", "ld2", "same_county", "same_tract", "pull", "lprop", "same_town", "ldir", "lcorr"],
    "all, road minutes": ["lm", "lm2", "same_county", "same_tract", "pull", "lprop", "same_town", "ldir", "lcorr"],
}


def matrices(tr):
    """Training-month terms, home x tract."""
    Rm = np.zeros((len(H), len(T)))
    m0 = tr.groupby(["hi", "ti"]).reach.mean()
    Rm[m0.index.get_level_values(0), m0.index.get_level_values(1)] = m0.values
    tot = Rm.sum(1, keepdims=True)
    pull = (Rm.sum(0, keepdims=True) - Rm) / (len(H) - 1)
    return {"Rm": Rm, "ldir": np.log(np.einsum("hd,hdt->ht", Rm, K) / tot + 0.01),
            "lcorr": np.log(np.einsum("hd,hdt->ht", Rm, V) / tot + 0.01),
            "pull": logit(pull), "lprop": np.repeat(logit(Rm.mean(1, keepdims=True)), len(T), 1),
            "ld": np.log1p(KM), "ld2": np.log1p(KM) ** 2, "lm": np.log1p(MIN), "lm2": np.log1p(MIN) ** 2,
            "same_county": SAME_COUNTY, "same_tract": SAME_TRACT, "same_town": SAME_TOWN}


def frame(M, x):
    return pd.DataFrame({k: v[x.hi.values, x.ti.values] for k, v in M.items() if k != "Rm"}, index=x.index)


def fit_predict(tr, te, terms):
    M = matrices(tr)
    a = tr.drop_duplicates(["hi", "ti", "month"])
    X = lambda f: sm.add_constant(f[terms], has_constant="add")
    glm = sm.GLM(a.reach, X(frame(M, a)), family=sm.families.Binomial()).fit()
    sums = tr.groupby(["hi", "ti"])[["people", "own"]].sum()
    out = te[["hi", "ti", "reach", "home_cbg", "tract"]].join(sums, on=["hi", "ti"])
    out["m0"] = M["Rm"][out.hi, out.ti]
    out["m1"] = glm.predict(X(frame(M, te)))
    return out, glm


m2 = lambda o, a: (o.people + a * o.m1) / (o.own + a)
A_GRID = [0, 100, 300, 1000, 3000, 10000]
TOWNS = ("Columbia", "Mexico", "Linn")
rows, coefs = [], {}
for name, terms in SPECS.items():
    for m in MONTHS:
        tr, te = g[g.month != m], g[g.month == m]
        inner = {a: [] for a in A_GRID}
        for k in sorted(tr.month.unique()):
            o, _ = fit_predict(tr[tr.month != k], tr[tr.month == k], terms)
            for a in A_GRID:
                inner[a].append((m2(o, a) - o.reach).abs().mean())
        a_best = min(A_GRID, key=lambda a: np.mean(inner[a]))
        out, glm = fit_predict(tr, te, terms)
        out["m2"] = m2(out, a_best)
        coefs.setdefault(name, []).append(glm.params)
        out["town"] = out.home_cbg.map(homes.town).fillna("")
        for c in ("m0", "m1", "m2"):
            r = {"terms": name, "month": m, "model": c, "a": a_best, "resident": 100 * (out[c] - out.reach).abs().mean()}
            for town in TOWNS:
                x = out[out.town == town].groupby("tract")[[c, "reach"]].median()
                r[town] = 100 * (x[c] - x.reach).abs().mean()
            rows.append(r)
    s = pd.DataFrame(rows)
    print(name, s[(s.terms == name)].groupby("model")[["resident", *TOWNS]].mean().round(3).to_dict("index"), flush=True)
s = pd.DataFrame(rows)
s.to_csv(R / "model_scores.csv", index=False)
print("\nmean over held-out months (points of reach):")
print(s.groupby(["model", "terms"], sort=False)[["resident", *TOWNS]].mean().round(3).to_string())
for name in SPECS:
    print(f"\n{name}: coefficients, mean over folds")
    print(pd.concat(coefs[name], axis=1).mean(axis=1).round(3).to_string())
