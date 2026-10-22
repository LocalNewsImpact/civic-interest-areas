"""STAGE 1, public data only: non-work travel from each Missouri census tract to every county within 160 miles, and the
work + non-work combination. No Advan.

Draw      County Business Patterns 2022 employment in retail (NAICS 44-45), health care (62), arts and recreation
          (71), food and lodging (72), summed (cbp22co.txt; all states, so Illinois and the other neighbours count).
Decay     share of a tract's non-work trips to county j ~ draw_j x miles^-beta, miles to county j's job centre (county_public_geo.csv). beta is set by maximum likelihood so the model's trip-length
          distribution matches the 2022 National Household Travel Survey (tripv2pub.csv): non-work trips (WHYTRP1S
          30 medical, 40 shopping and errands, 50 social and recreation, 80 meals), weighted (WTTRDFIN), straight-line
          miles = route miles / 1.25 (rural road circuity), 20 to 160 straight-line miles, four distance bands. Calibrated
          separately for each metro size class: survey households by MSASIZE (6 not in a metro; 1-2 metro under 500,000;
          3-5 metro 500,000 and over), applied to tracts by their county's class (OMB 2023, Census 2024 population). Destinations under 20 miles and the home county are left out of the
          calibration: trips that short are mostly inside the home county, which the county frame cannot resolve.
Mix       the out-of-county combination of the work model (public_work_model.py) and the non-work model, weighted by the
          survey's share of trips of 20+ straight-line miles that are work trips (WHYTRP1S 10) versus non-work, by class.
Output    analysis/public_model_pairs.csv: tract, j, work_share, nonwork_share, combined_share (out-of-county, all
          states, each summing to 1 per tract).
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
REF = root / "census_dl/ref"
CIRC = 1.25
BANDS = [20, 35, 60, 100, 160]
REGION = os.environ.get("NHTS_REGION")          # "4" = West North Central only (sensitivity)
# one factor at a time against v1: DRAW est|emp, DIST pop|hub, CLASS rucc|msa, LOSS sq|ll, TAG = output suffix
DRAW, DIST, CLASS, LOSS, TAG = (os.environ.get(k, v) for k, v in (("DRAW", "emp"), ("DIST", "hub"), ("CLASS", "msa"), ("LOSS", "ll"), ("TAG", "")))
# SUBGROUP income|degree|tenure: a decay rate per survey group within each class; a tract's non-work shares are the
# mixture of its groups' shares, weighted by the tract's ACS 2020-2024 make-up (tract_acs_2024.csv)
SUBGROUP = os.environ.get("SUBGROUP", "")
WORKTAG = os.environ.get("WORKTAG", "")          # which work model pairs file to combine with (public_work_model.py TAG)

t = pd.read_csv(root / "census_dl/nhts/tripv2pub.csv", usecols=["WHYTRP1S", "TRPMILES", "WTTRDFIN", "MSASIZE", "URBRUR", "CENSUS_D", "HHFAMINC", "EDUC", "HOMEOWN"])
t = t[t.TRPMILES > 0]
if REGION:
    t = t[t.CENSUS_D == int(REGION)]
t["sl"] = t.TRPMILES / CIRC
if CLASS == "msa":
    t["cls"] = t.MSASIZE.map({1: "small", 2: "small", 3: "large", 4: "large", 5: "large", 6: "nonmetro"})
    CLASSES = ("nonmetro", "small", "large")
else:                                            # v1: survey URBRUR, tracts by RUCC
    t["cls"] = t.URBRUR.map({1: "urban", 2: "rural"})
    CLASSES = ("rural", "urban")
NONWORK = [30, 40, 50, 80]


GROUPS = {"income": {"inc_lt50": t.HHFAMINC.between(1, 5), "inc_50_100": t.HHFAMINC.between(6, 7), "inc_ge100": t.HHFAMINC.between(8, 11)},
          "degree": {"ba_plus": t.EDUC.between(4, 5), "no_ba": t.EDUC.between(1, 3)},
          "tenure": {"renter": t.HOMEOWN == 2, "owner": t.HOMEOWN == 1}}.get(SUBGROUP, {"all": t.WHYTRP1S.notna()})


def target(c, g="all"):
    s = t[GROUPS[g] & (t.cls == c) & t.WHYTRP1S.isin(NONWORK) & t.sl.between(BANDS[0], BANDS[-1])]
    h = np.histogram(s.sl, BANDS, weights=s.WTTRDFIN)[0]
    return h / h.sum(), len(s)


long_ = t[t.sl.between(BANDS[0], BANDS[-1])]
work_frac = {c: long_[(long_.cls == c) & (long_.WHYTRP1S == 10)].WTTRDFIN.sum()
             / long_[(long_.cls == c) & long_.WHYTRP1S.isin(NONWORK + [10])].WTTRDFIN.sum() for c in CLASSES}

tr = pd.read_csv(REF / "CenPop2020_Mean_TR29.txt", dtype=str, encoding="utf-8-sig")
tr["tract"] = tr.STATEFP + tr.COUNTYFP + tr.TRACTCE
tr[["lat", "lon", "pop"]] = tr[["LATITUDE", "LONGITUDE", "POPULATION"]].astype(float)
co = pd.read_csv(REF / "CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
co["fips"] = co.STATEFP + co.COUNTYFP
co[["lat", "lon"]] = co[["LATITUDE", "LONGITUDE"]].astype(float)
co = co[co.STATEFP.isin({"29", "17", "20", "19", "05", "40", "31", "47", "21"})].set_index("fips")
geo = pd.read_csv(root / "analysis/county_public_geo.csv", dtype={"fips": str}).set_index("fips")
if DIST == "hub":
    co[["lat", "lon"]] = geo.loc[co.index, ["lat", "lon"]].values
cbp = pd.read_csv(root / "census_dl/cbp/cbp22co.txt", dtype=str, usecols=["fipstate", "fipscty", "naics", DRAW])
cbp = cbp[cbp.naics.isin(["44----", "62----", "71----", "72----"])]
draw = cbp.assign(f=cbp.fipstate + cbp.fipscty, v=cbp[DRAW].astype(float)).groupby("f").v.sum()

R = 3959.0
tla, tlo = np.radians(tr.lat.values)[:, None], np.radians(tr.lon.values)[:, None]
cla, clo = np.radians(co.lat.values)[None, :], np.radians(co.lon.values)[None, :]
D = 2 * R * np.arcsin(np.sqrt(np.sin((cla - tla) / 2) ** 2 + np.cos(tla) * np.cos(cla) * np.sin((clo - tlo) / 2) ** 2))
cid = np.asarray(co.index, dtype=object)
home = np.asarray(tr.tract.str[:5], dtype=object)
notHome = cid[None, :] != home[:, None]
W = draw.reindex(cid).fillna(0).values[None, :]
if CLASS == "msa":
    cls_t = geo.metro_class.reindex(home).values
else:
    rucc = pd.read_csv(REF / "rucc2023.csv", dtype=str, encoding="latin-1")
    rucc = rucc[rucc.Attribute == "RUCC_2023"]
    rr = {r.FIPS.zfill(5): int(r.Value) >= 4 for r in rucc.itertuples()}
    cls_t = np.array(["rural" if rr.get(h, False) else "urban" for h in home])


def band_shares(beta, rows):
    m = notHome[rows] & (D[rows] >= BANDS[0]) & (D[rows] <= BANDS[-1])
    k = np.where(m, W * np.maximum(D[rows], 1) ** -beta, 0)
    k = k / k.sum(1, keepdims=True) * tr["pop"].values[rows, None]
    h = np.array([k[(D[rows] >= lo) & (D[rows] < hi)].sum() for lo, hi in zip(BANDS[:-1], BANDS[1:])])
    return h / h.sum()


acs = pd.read_csv(root / "analysis/tract_acs_2024.csv", dtype={"tract": str}).set_index("tract").reindex(tr.tract)
if SUBGROUP == "degree":
    acs["no_ba"] = 1 - acs.ba_plus
if SUBGROUP == "tenure":
    acs["owner"] = 1 - acs.renter
beta = {}
for c in CLASSES:
    rows = cls_t == c
    for g in GROUPS:
        tgt, n = target(c, g)
        grid = np.arange(0.5, 8.01, 0.05)
        if LOSS == "ll":                             # likelihood of the survey trips
            loss = [-np.sum(tgt * np.log(np.maximum(band_shares(b, rows), 1e-12))) for b in grid]
        else:                                        # v1: squared error of band shares
            loss = [np.sum((band_shares(b, rows) - tgt) ** 2) for b in grid]
        beta[c, g] = grid[int(np.argmin(loss))]
        print(f"{c} {g}: n={n} trips, {rows.sum()} tracts, beta={beta[c, g]:.2f}, work share of 20+ mi trips {work_frac[c]:.2f}")

m = notHome & (D <= 200)
NW = np.zeros_like(D)
for g in GROUPS:
    bt = np.array([beta[c, g] for c in cls_t])[:, None]
    K = np.where(m, W * np.maximum(D, 1) ** -bt, 0)
    wg = np.ones(len(tr)) if g == "all" else acs[g].fillna(acs[g].median()).values
    NW += wg[:, None] * K / K.sum(1, keepdims=True)
NW /= NW.sum(1, keepdims=True)
WORKDIST = os.environ.get("WORKDIST", DIST)      # the work model's distance can differ from the non-work model's
P = pd.read_csv(root / f"analysis/public_work_model_pairs{WORKTAG or ('_v1' if WORKDIST == 'pop' else '')}.csv", dtype={"tract": str, "j": str, "home": str})
P = P[P.home != P.j].copy()
P["work_share"] = P.pred_share / P.groupby("tract").pred_share.transform("sum")
ai, bi = P.a.values, P.b.values
P["nonwork_share"] = NW[ai, bi]
P["nonwork_share"] /= P.groupby("tract").nonwork_share.transform("sum")
wf = np.array([work_frac[c] for c in cls_t[ai]])
P["combined_share"] = wf * P.work_share + (1 - wf) * P.nonwork_share
P[["tract", "home", "j", "miles", "work_share", "nonwork_share", "combined_share"]].to_csv(
    root / f"analysis/public_model_pairs{TAG}.csv", index=False)
