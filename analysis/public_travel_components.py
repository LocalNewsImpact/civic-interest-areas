"""STAGE 1, public data only: out-of-county travel from each Missouri census tract as four kinds of travel, each with its
own destination draw and its own distance decay, combined by how many visit-days each produces. No Advan.

  work       the public work model (public_work_model.py, LODES 2023), as is.
  shopping   medical, shopping and errands, meals (survey WHYTRP1S 30, 40, 80). Draw = County Business Patterns 2022
             employment in retail, health care, food and lodging (NAICS 44-45, 62, 72), counted only for what the
             destination offers beyond the home county: draw_j x S_j / (S_j + S_home). A county smaller than home
             has little to offer -- Callaway to a Boone resident -- while for a small county every neighbour is
             bigger and the discount is slight.
  recreation vacation (long-distance file FARREAS 2). Draw = employment in accommodation and arts, entertainment and
             recreation (NAICS 721, 71): Branson, the lakes, the metros' attractions.
  visiting   visiting family or friends (FARREAS 3). Draw = 2020 population.

Decay     share ~ draw x miles^-beta per kind; beta by maximum likelihood against the survey's trip-length distribution,
          separately for rural and urban households (URBRUR; tracts by RUCC 2023 >= 4 nonmetro):
            shopping    2022 survey trip file, 20-160 straight-line miles (route miles / 1.25)
            recreation, visiting   long-distance file, most recent trip of 50+ miles, great-circle miles to the
                        farthest destination (GCDTOT), 50-200 miles; each reported trip weighted by person weight x
                        days away (NTSAWAY + 1), so the distribution is of visit-days.
Mix       visit-days per person per month, by kind and household type: survey trips of 20-50 straight-line miles x 30
          (trip file, WTTRDFIN annual trips / 365 per person), plus long-distance trips in the past 30 days x days away
          (LONGDIST x (NTSAWAY + 1), capped at 30 visit-days a month). Work
          includes long-distance business trips; shopping includes long-distance "other". Social and recreational
          day trips of 20-50 miles (WHYTRP1S 50) count as recreation.
Output    analysis/public_model_pairs_comp.csv: tract, home, j, miles, each kind's share and the combined share
          (out-of-county destinations within 200 miles, each summing to 1 per tract).
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
REF = root / "census_dl/ref"
CIRC = 1.25
TRADEUP = os.environ.get("TRADEUP", "share")      # share: S_j/(S_j+S_home); excess: (S_j-S_home)+; none
TAG = os.environ.get("TAG", "")

# ---- survey ------------------------------------------------------------------------------------------------------
t = pd.read_csv(root / "census_dl/nhts/tripv2pub.csv", usecols=["WHYTRP1S", "TRPMILES", "WTTRDFIN", "URBRUR"])
t = t[t.TRPMILES > 0]
t["sl"] = t.TRPMILES / CIRC
ld = pd.read_csv(root / "census_dl/nhts/ldtv2pub.csv", usecols=["FARREAS", "GCDTOT", "NTSAWAY", "LONGDIST", "WTPERFIN", "URBRUR"])
persons = ld.groupby("URBRUR").WTPERFIN.sum()                     # every sampled person is on the long-distance file
L = ld[(ld.FARREAS > 0) & (ld.GCDTOT >= 50)].copy()
L["days"] = np.where(L.NTSAWAY >= 0, L.NTSAWAY + 1, 1)
L["w"] = L.WTPERFIN * L.days                                     # distance distribution: the reported trip, in days
L["vol"] = L.WTPERFIN * np.minimum(L.LONGDIST * L.days, 30)      # visit-days in the past 30 days, at most 30
KIND_TRIP = {10: "work", 30: "shopping", 40: "shopping", 80: "shopping", 50: "recreation"}
KIND_LD = {1: "work", 4: "shopping", 2: "recreation", 3: "visiting"}
KINDS = ["work", "shopping", "recreation", "visiting"]
volume = {}
for u in (1, 2):
    s = t[(t.URBRUR == u) & t.sl.between(20, 50)]
    day = s.groupby(s.WHYTRP1S.map(KIND_TRIP)).WTTRDFIN.sum() / 365 * 30 / persons[u]
    far = L[L.URBRUR == u].groupby(L.FARREAS.map(KIND_LD)).vol.sum() / persons[u]
    volume[u] = {k: day.get(k, 0) + far.get(k, 0) for k in KINDS}
print("visit-days per person per month, out-of-town (20+ straight-line miles):")
for u, lab in ((2, "rural"), (1, "urban")):
    print(f"  {lab}: " + ", ".join(f"{k} {v:.2f}" for k, v in volume[u].items()))
print(f"  check: survey trips per person per day (all) {t.WTTRDFIN.sum() / 365 / persons.sum():.2f}")

# ---- geography -----------------------------------------------------------------------------------------------------
tr = pd.read_csv(REF / "CenPop2020_Mean_TR29.txt", dtype=str, encoding="utf-8-sig")
tr["tract"] = tr.STATEFP + tr.COUNTYFP + tr.TRACTCE
tr[["lat", "lon", "pop"]] = tr[["LATITUDE", "LONGITUDE", "POPULATION"]].astype(float)
co = pd.read_csv(REF / "CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
co["fips"] = co.STATEFP + co.COUNTYFP
co[["lat", "lon", "pop"]] = co[["LATITUDE", "LONGITUDE", "POPULATION"]].astype(float)
co = co[co.STATEFP.isin({"29", "17", "20", "19", "05", "40", "31", "47", "21"})].set_index("fips")
cbp = pd.read_csv(root / "census_dl/cbp/cbp22co.txt", dtype=str, usecols=["fipstate", "fipscty", "naics", "emp"])
cbp["f"] = cbp.fipstate + cbp.fipscty
cbp["emp"] = cbp.emp.astype(float)
sector = lambda codes: cbp[cbp.naics.isin(codes)].groupby("f").emp.sum()
cid = np.asarray(co.index, dtype=object)
home = np.asarray(tr.tract.str[:5], dtype=object)
S = sector(["44----", "62----", "72----"]).reindex(cid).fillna(0).values
REC = sector(["721///", "71----"]).reindex(cid).fillna(0).values
POP = co["pop"].values
rucc = pd.read_csv(REF / "rucc2023.csv", dtype=str, encoding="latin-1")
rucc = rucc[rucc.Attribute == "RUCC_2023"]
rural = np.array([{r.FIPS.zfill(5): int(r.Value) >= 4 for r in rucc.itertuples()}.get(h, False) for h in home])

R = 3959.0
tla, tlo = np.radians(tr.lat.values)[:, None], np.radians(tr.lon.values)[:, None]
cla, clo = np.radians(co.lat.values)[None, :], np.radians(co.lon.values)[None, :]
D = 2 * R * np.arcsin(np.sqrt(np.sin((cla - tla) / 2) ** 2 + np.cos(tla) * np.cos(cla) * np.sin((clo - tlo) / 2) ** 2))
keep = (cid[None, :] != home[:, None]) & (D <= 200)
S_home = pd.Series(S, index=cid).reindex(home).fillna(0).values[:, None]
DRAW = {"shopping": {"share": S[None, :] * S[None, :] / (S[None, :] + S_home), "excess": np.maximum(S[None, :] - S_home, 0) + 1,
                     "none": np.broadcast_to(S[None, :], D.shape)}[TRADEUP],
        "recreation": np.broadcast_to(REC[None, :], D.shape),
        "visiting": np.broadcast_to(POP[None, :], D.shape)}


def survey_bands(kind, u):
    if kind == "shopping":
        s = t[(t.URBRUR == u) & t.WHYTRP1S.isin([30, 40, 80]) & t.sl.between(20, 160)]
        bands = [20, 35, 60, 100, 160]
        h = np.histogram(s.sl, bands, weights=s.WTTRDFIN)[0]
    else:
        s = L[(L.URBRUR == u) & (L.FARREAS == {"recreation": 2, "visiting": 3}[kind]) & L.GCDTOT.between(50, 200)]
        bands = [50, 75, 100, 150, 200]
        h = np.histogram(s.GCDTOT, bands, weights=s.w)[0]
    return bands, h / h.sum(), len(s)


def model_bands(kind, beta, rows, bands):
    d = D[rows]
    m = keep[rows] & (d >= bands[0]) & (d <= bands[-1])
    k = np.where(m, DRAW[kind][rows] * np.maximum(d, 1) ** -beta, 0)
    k = k / np.maximum(k.sum(1, keepdims=True), 1e-300) * tr["pop"].values[rows, None]
    h = np.array([k[(d >= lo) & (d < hi)].sum() for lo, hi in zip(bands[:-1], bands[1:])])
    return h / h.sum()


SH = {}
for kind in ("shopping", "recreation", "visiting"):
    bt = np.zeros(len(tr))
    for u, rows, lab in ((2, rural, "rural"), (1, ~rural, "urban")):
        bands, tgt, n = survey_bands(kind, u)
        grid = np.arange(0.2, 8.01, 0.05)
        loss = [-np.sum(tgt * np.log(np.maximum(model_bands(kind, b, rows, bands), 1e-12))) for b in grid]
        b = grid[int(np.argmin(loss))]
        bt[rows] = b
        print(f"{kind} {lab}: n={n}, beta={b:.2f}, survey {np.round(tgt, 3)}, model {np.round(model_bands(kind, b, rows, bands), 3)}")
    K = np.where(keep, DRAW[kind] * np.maximum(D, 1) ** -bt[:, None], 0)
    SH[kind] = K / K.sum(1, keepdims=True)

P = pd.read_csv(root / "analysis/public_work_model_pairs_v1.csv", dtype={"tract": str, "j": str, "home": str})
P = P[(P.home != P.j) & (P.miles <= 200)].copy()
P["work"] = P.pred_share / P.groupby("tract").pred_share.transform("sum")
ai, bi = P.a.values, P.b.values
for kind in ("shopping", "recreation", "visiting"):
    P[kind] = SH[kind][ai, bi]
    P[kind] /= P.groupby("tract")[kind].transform("sum")
vol = np.array([[volume[2 if r else 1][k] for k in KINDS] for r in rural[ai]])
P["combined_share"] = (P[KINDS].values * vol).sum(1) / vol.sum(1)
P[["tract", "home", "j", "miles"] + KINDS + ["combined_share"]].to_csv(root / f"analysis/public_model_pairs_comp{TAG}.csv", index=False)
