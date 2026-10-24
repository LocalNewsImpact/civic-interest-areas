"""STAGE 1, public data only: out-of-county travel from each Missouri census tract, by need. A resident leaves the home
county for what it cannot supply; distance makes those trips rarer, so the nearest county with spare capacity gets
them. No Advan.

Needs and capacity (County Business Patterns 2022 employment; NAICS 2017 codes as published):
  grocery     supermarkets (445110; else 4451, else 445) + supercenters, which sell groceries too
  boxstore    supercenters and warehouse clubs (452311; else 4523 - 452319, else 452 - 4522 - 452319): CBP withholds
              detail rows in small counties, so the most detailed published code is used
  medical     health care (62)
  specialty   furniture (442), electronics and appliances (443), clothing (448), sporting goods, hobby, book and music
              (451), department stores (4522)
Unmet share   grocery, box store, medical: u = max(0, 1 - capacity per resident / Missouri capacity per resident), of the home
              county. Boone and Cole meet their own; Osage, with no supercenter, does not.
Draw          DRAWMODE=spare: spare capacity, max(0, capacity - Missouri rate x residents), plus 1;
              DRAWMODE=cap: capacity itself. Unmet need sets how much leaves; the draw sets where it goes.
Volume        visit-days per resident per month, by tract:
  work        LODES 2023 workers living in the tract who work in another county / tract population x 20 days, plus
              long-distance business trips (survey FARREAS 1)
  grocery,    u x survey shopping and errand trips per person per month (WHYTRP1S 40), divided between the two by
  boxstore    Missouri's employment split between supermarkets and supercenters
  medical     u x survey medical trips per person per month (WHYTRP1S 30)
  specialty   survey long-distance "other" trips (FARREAS 4), occasional by nature
  recreation  survey social and recreational trips of 20-50 straight-line miles + long-distance vacation (FARREAS 2)
  visiting    long-distance visits to family or friends (FARREAS 3); draw = 2020 population
Decay         share ~ draw x miles^-beta per need, beta by maximum likelihood against the survey's trip lengths, rural and
              urban households separately (as public_travel_components.py).
Trade area    RETAIL=tac replaces grocery and box store with one retail need from trade area analysis: Missouri
              Department of Revenue 2025 taxable sales by county (DI60IT15_SLS_CNTY), pull factor = per-capita sales /
              Missouri per-capita sales; trade area capture TAC = sales / (Missouri per-capita sales x residents x
              county per-capita income / Missouri's, ACS 2020-2024); leakage = max(0, 1 - TAC). Huff allocation:
              attraction = taxable sales (HUFF=sales) or sales beyond the county's own expected (HUFF=surplus);
              neighbouring states' sales = CBP retail jobs x Missouri sales per retail job. LAMBDA=kind:x fixes a
              distance exponent (2 = Reilly's law; the visitation law's r^-2), in place of the survey fit.
Output        analysis/public_model_pairs_tiers.csv
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
REF = root / "census_dl/ref"
CIRC = float(os.environ.get("CIRC", "1.25"))       # route miles / straight-line miles
# default weights, each switchable to test it (public_default_sensitivity.py):
#   MULT=kind:x,...   scale a kind's volume     WORK_DAYS (20)   WFH=1: x (1 - tract work-from-home share, ACS B08006)
#   LD_DAYS=0: long-distance volume in trips, not days away     HUFF_ALPHA (1): retail attraction = sales^alpha
#   LEAK=huffhome: retail leakage = 1 - Huff probability of the home county (exponent LEAK_LAMBDA, 2), per tract
#   URBAN_CLASSES="class 3,...": county classes given the urban decay rate
MULT = {k: float(v) for k, v in (x.split(":") for x in os.environ.get("MULT", "").split(",") if x)}
WORK_DAYS = float(os.environ.get("WORK_DAYS", "20"))
HUFF_ALPHA = float(os.environ.get("HUFF_ALPHA", "1"))
LEAK = os.environ.get("LEAK", "tac")
TAG = os.environ.get("TAG", "")
REC_CODES = os.environ.get("REC_CODES", "721///,71----").split(",")

# ---- survey --------------------------------------------------------------------------------------------------------
t = pd.read_csv(root / "census_dl/nhts/tripv2pub.csv", usecols=["WHYTRP1S", "TRPMILES", "WTTRDFIN", "URBRUR", "WHYFROM", "WHYTO"])
t = t[t.TRPMILES > 0]
t["sl"] = t.TRPMILES / CIRC
ld = pd.read_csv(root / "census_dl/nhts/ldtv2pub.csv", usecols=["FARREAS", "GCDTOT", "NTSAWAY", "LONGDIST", "WTPERFIN", "URBRUR", "WORKER"])
workers = ld[ld.WORKER == 1].groupby("URBRUR").WTPERFIN.sum()
persons = ld.groupby("URBRUR").WTPERFIN.sum()
L = ld[(ld.FARREAS > 0) & (ld.GCDTOT >= 50)].copy()
L["days"] = np.where(L.NTSAWAY >= 0, L.NTSAWAY + 1, 1)
L["w"] = L.WTPERFIN * (L.days if os.environ.get("LD_DAYS", "1") == "1" else 1)
L["vol"] = L.WTPERFIN * np.minimum(L.LONGDIST * (L.days if os.environ.get("LD_DAYS", "1") == "1" else 1), 30)
per_month = lambda s, u: s.WTTRDFIN.sum() / 365 * 30 / persons[u]
ld_month = lambda code, u: L[(L.URBRUR == u) & (L.FARREAS == code)].vol.sum() / persons[u]
# CHAIN=1: errands made from work go to the work county. Chained rate = health care, meals, shopping and errand trips
# (WHYTO 11-14) that start at work (WHYFROM 3-5), per worker per month; retail leakage then uses only the same
# trips starting at home (WHYFROM 1), per person, so no trip is counted twice.
CHAIN = os.environ.get("CHAIN") == "1"
WORK_OBS = os.environ.get("WORK_OBS") == "1"      # work destinations = LODES as observed, not the gravity fit
errand = t.WHYTO.between(11, 14)
chain_rate = {u: t[(t.URBRUR == u) & errand & t.WHYFROM.between(3, 5)].WTTRDFIN.sum() / 365 * 30 / workers[u] for u in (1, 2)}
home_rate = {u: per_month(t[(t.URBRUR == u) & errand & (t.WHYFROM == 1)], u) for u in (1, 2)}
print("errand trips from work per worker per month:", {k: round(v, 2) for k, v in chain_rate.items()},
      "| from home per person:", {k: round(v, 2) for k, v in home_rate.items()})
rate = {u: {"everyday": home_rate[u] if CHAIN else per_month(t[(t.URBRUR == u) & (t.WHYTRP1S == 40)], u),
            "medical": per_month(t[(t.URBRUR == u) & (t.WHYTRP1S == 30)], u),
            "business": ld_month(1, u), "specialty": ld_month(4, u),
            "recreation": per_month(t[(t.URBRUR == u) & (t.WHYTRP1S == 50) & t.sl.between(20, 50)], u) + ld_month(2, u),
            "visiting": ld_month(3, u)} for u in (1, 2)}
# REGULAR=1: an activity space is regular travel -- the long-distance kinds (50+ mile business trips, specialty shopping,
# visiting, vacations) are occasional and are dropped; day-trip recreation (20-50 miles) stays
if os.environ.get("REGULAR") == "1":
    for u in (1, 2):
        rate[u].update({"business": 0.0, "specialty": 0.0, "visiting": 0.0,
                        "recreation": per_month(t[(t.URBRUR == u) & (t.WHYTRP1S == 50) & t.sl.between(20, 50)], u)})

# ---- geography and capacity ----------------------------------------------------------------------------------------
ST = os.environ.get("STATE", "29")                 # home state FIPS (29 Missouri, 20 Kansas)
SUF = "" if ST == "29" else f"_{ST}"
tr = pd.read_csv(REF / f"CenPop2020_Mean_TR{ST}.txt", dtype=str, encoding="utf-8-sig")
tr["tract"] = tr.STATEFP + tr.COUNTYFP + tr.TRACTCE
tr[["lat", "lon", "pop"]] = tr[["LATITUDE", "LONGITUDE", "POPULATION"]].astype(float)
co = pd.read_csv(REF / "CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
co["fips"] = co.STATEFP + co.COUNTYFP
co[["lat", "lon", "pop"]] = co[["LATITUDE", "LONGITUDE", "POPULATION"]].astype(float)
co = co[co.STATEFP.isin({"29": {"29", "17", "20", "19", "05", "40", "31", "47", "21"}, "20": {"20", "29", "31", "40", "08"}}[ST])].set_index("fips")
cid = np.asarray(co.index, dtype=object)
cbp = pd.read_csv(root / "census_dl/cbp/cbp22co.txt", dtype=str, usecols=["fipstate", "fipscty", "naics", "emp"])
cbp["f"] = cbp.fipstate + cbp.fipscty
E = cbp.assign(emp=cbp.emp.astype(float)).pivot_table(index="f", columns="naics", values="emp", aggfunc="sum").reindex(cid).fillna(0)
col = lambda c: E[c] if c in E else pd.Series(0.0, index=E.index)
def _first(xs):
    """the most detailed of several codes that is published for each county (CBP withholds detail rows)"""
    out = np.zeros(len(E))
    for x in xs[::-1]:
        x = np.asarray(x, float)
        out = np.where(x > 0, x, out)
    return out


supercenter = _first([col("452311"), (col("4523//") - col("452319")).clip(lower=0),
                      (col("452///") - col("4522//") - col("452319")).clip(lower=0)])
supermarket = _first([col("445110"), col("4451//"), col("445///")])
CAP = {"grocery": supermarket + supercenter, "boxstore": supercenter,          # supercenters sell groceries too
       "medical": col("62----").values,
       "specialty": sum(col(c).values for c in ("442///", "443///", "448///", "451///", "4522//"))}
POP = co["pop"].values
mo = cid.astype(str).astype(object)
is_mo = np.array([c[:2] == ST for c in cid])            # the home state (named for Missouri, its first use)
DRAW, UNMET = {}, {}
for k, cap in CAP.items():
    cap = np.asarray(cap, float)
    r = cap[is_mo].sum() / POP[is_mo].sum()
    DRAW[k] = (np.maximum(cap - r * POP, 0) if os.environ.get("DRAWMODE", "spare") == "spare" else cap) + 1
    UNMET[k] = pd.Series(np.clip(1 - cap / (r * POP), 0, 1), index=cid)
GROCERY_SHARE = supermarket[is_mo].sum() / (supermarket[is_mo].sum() + supercenter[is_mo].sum())
print(f"grocery share of everyday shopping trips (Missouri employment split): {GROCERY_SHARE:.2f}")
DRAW["recreation"] = sum(col(c).values for c in REC_CODES) + 1

# ---- trade area analysis (RETAIL=tac): Missouri Department of Revenue 2025 taxable sales by county ----------------
RETAIL = os.environ.get("RETAIL", "needs")         # needs: grocery and box-store unmet need; tac: trade area capture
HUFF = os.environ.get("HUFF", "sales")             # retail attraction: sales, or surplus (sales beyond own residents)
FIXED = {k: float(v) for k, v in (x.split(":") for x in os.environ.get("LAMBDA", "").split(",") if x)}   # e.g. retail:2
if ST == "29":
    ts = pd.read_csv(root / "census_dl/mo_dor/cnty/DI60IT15_SLS_CNTY_F_2025.csv", dtype=str, encoding="utf-8-sig")
    ts = pd.Series(ts.Total.str.replace(r"[$,\s]", "", regex=True).astype(float).values, index="29" + ts.MOID.str.zfill(3).replace("193", "186"))   # DOR keeps Ste. Genevieve's pre-1979 code
else:    # Kansas: FY2025 state sales tax collections by county (one state rate, so proportional to taxable sales)
    _k = pd.read_csv(root / "analysis/ks_pull_factors_fy25.csv", dtype={"fips": str})
    ts = pd.Series(_k.sales_tax.values, index=_k.fips)
acs_c = pd.read_csv(root / "free/mo_county_acs_2024.csv", dtype={"fips": str})
pci = acs_c[acs_c.variable == "per_capita_income"].set_index("fips").estimate
if ST != "29":   # county per-capita income, ACS 2020-2024 (B19301), from the table-based summary file
    _b = pd.read_csv(root / "census_dl/acs_tract/b19301.dat", sep="|", dtype=str)
    _b = _b[_b.GEO_ID.str.startswith("0500000US" + ST)]
    pci = pd.Series(pd.to_numeric(_b.B19301_E001, errors="coerce").values, index=_b.GEO_ID.str[-5:])
retail_emp = sum(col(c).values for c in ("44----", "45----")) if "45----" in E else col("44----").values
TS = ts.reindex(cid).values
per_emp = np.nansum(TS[is_mo]) / retail_emp[is_mo].sum()
TS = np.where(np.isnan(TS), retail_emp * per_emp, TS)               # neighbouring states: CBP retail jobs x Missouri sales per job
state_pc = TS[is_mo].sum() / POP[is_mo].sum()
pci_mo = (pci.reindex(cid[is_mo]).values * POP[is_mo]).sum() / POP[is_mo].sum()
PF = pd.Series(TS / POP / state_pc, index=cid)                        # pull factor
TAC = pd.Series(TS / (state_pc * POP * pci.reindex(cid).fillna(pci_mo).values / pci_mo), index=cid)   # trade area capture
UNMET["retail"] = (1 - TAC).clip(lower=0, upper=1)
expected = state_pc * POP * pci.reindex(cid).fillna(pci_mo).values / pci_mo
DRAW["retail"] = (TS if HUFF == "sales" else np.maximum(TS - expected, 0)) ** HUFF_ALPHA + 1
if RETAIL == "tac":
    for c, n in ((("29151", "Osage"), ("29051", "Cole"), ("29019", "Boone"), ("29007", "Audrain"), ("29127", "Marion"), ("29135", "Moniteau")) if ST == "29" else ()):
        print(f"{n}: pull factor {PF[c]:.2f}, trade area capture {TAC[c]:.2f}, retail leakage {UNMET['retail'][c]:.2f}")
DRAW["visiting"] = POP
home = np.asarray(tr.tract.str[:5], dtype=object)
rucc = pd.read_csv(REF / "rucc2023.csv", dtype=str, encoding="latin-1")
rucc = rucc[rucc.Attribute == "RUCC_2023"]
rural = np.array([{r.FIPS.zfill(5): int(r.Value) >= 4 for r in rucc.itertuples()}.get(h, False) for h in home])
if os.environ.get("URBAN_CLASSES"):
    k4 = pd.read_csv(root / f"analysis/county_class_k4{SUF}.csv", dtype={"fips": str}).set_index("fips")["class"]   # the home state's classes
    to_urban = {c.strip() for c in os.environ["URBAN_CLASSES"].split(",")}
    rural &= ~np.array([k4.get("29189" if h == "29510" else h, "class 1") in to_urban for h in home])
for c, n in ((("29151", "Osage"), ("29051", "Cole"), ("29019", "Boone"), ("29007", "Audrain"), ("29127", "Marion")) if ST == "29" else ()):
    print(f"{n}: unmet grocery {UNMET['grocery'][c]:.2f}, box store {UNMET['boxstore'][c]:.2f}, medical {UNMET['medical'][c]:.2f}, specialty {UNMET['specialty'][c]:.2f}")

R = 3959.0
tla, tlo = np.radians(tr.lat.values)[:, None], np.radians(tr.lon.values)[:, None]
cla, clo = np.radians(co.lat.values)[None, :], np.radians(co.lon.values)[None, :]
D = 2 * R * np.arcsin(np.sqrt(np.sin((cla - tla) / 2) ** 2 + np.cos(tla) * np.cos(cla) * np.sin((clo - tlo) / 2) ** 2))
keep = (cid[None, :] != home[:, None]) & (D <= 200)


def survey_bands(k, u):
    if k in ("grocery", "boxstore", "medical", "retail"):
        s = t[(t.URBRUR == u) & (t.WHYTRP1S == {"grocery": 40, "boxstore": 40, "retail": 40, "medical": 30}[k]) & t.sl.between(20, 160)]
        bands = [20, 35, 60, 100, 160]
        return bands, np.histogram(s.sl, bands, weights=s.WTTRDFIN)[0], len(s)
    s = L[(L.URBRUR == u) & (L.FARREAS == {"specialty": 4, "recreation": 2, "visiting": 3}[k]) & L.GCDTOT.between(50, 200)]
    bands = [50, 75, 100, 150, 200]
    return bands, np.histogram(s.GCDTOT, bands, weights=s.w)[0], len(s)


def model_bands(k, beta, rows, bands):
    d = D[rows]
    m = keep[rows] & (d >= bands[0]) & (d <= bands[-1])
    x = np.where(m, DRAW[k][None, :] * np.maximum(d, 1) ** -beta, 0)
    x = x / np.maximum(x.sum(1, keepdims=True), 1e-300) * tr["pop"].values[rows, None]
    h = np.array([x[(d >= lo) & (d < hi)].sum() for lo, hi in zip(bands[:-1], bands[1:])])
    return h / h.sum()


SH = {}
KINDS_NW = (["retail"] if RETAIL == "tac" else ["grocery", "boxstore"]) + ["medical", "specialty", "recreation", "visiting"]
for k in KINDS_NW:
    bt = np.zeros(len(tr))
    for u, rows, lab in ((2, rural, "rural"), (1, ~rural, "urban")):
        bands, h, n = survey_bands(k, u)
        tgt = h / h.sum()
        grid = np.arange(0.2, 8.01, 0.05)
        b = grid[int(np.argmin([-np.sum(tgt * np.log(np.maximum(model_bands(k, g, rows, bands), 1e-12))) for g in grid]))]
        b = FIXED.get(k, FIXED.get("all", b))         # a published exponent in place of the survey fit
        bt[rows] = b
        print(f"{k} {lab}: n={n}, beta={b:.2f}")
    x = np.where(keep, DRAW[k][None, :] * np.maximum(D, 1) ** -bt[:, None], 0)
    SH[k] = x / x.sum(1, keepdims=True)

P = pd.read_csv(root / f"analysis/public_work_model_pairs{SUF}_v1.csv", dtype={"tract": str, "j": str, "home": str})
out_workers = P[P.home != P.j].groupby("tract").y.sum()
P = P[(P.home != P.j) & (P.miles <= 200)].copy()
# WORK_HYBRID=miles: observed LODES within that distance, the gravity fit beyond it -- long LODES flows are largely
# employers' imputed establishment assignments (LEHD multi-unit imputation), not where people travel
HYB = float(os.environ.get("WORK_HYBRID", "0"))
if HYB:
    near = P.miles <= HYB
    obs_near = P.act_share.where(near, 0).groupby(P.tract).transform("sum")
    fit_far = P.pred_share.where(~near, 0).groupby(P.tract).transform("sum")
    obs_far = P.act_share.where(~near, 0).groupby(P.tract).transform("sum")
    # keep each tract's observed near/far split of commuters; distribute the far part by the gravity fit
    P["work_src"] = np.where(near, P.act_share, P.pred_share / fit_far.replace(0, np.nan) * obs_far).astype(float)
    P["work_src"] = P.work_src.fillna(0)
    WORK_OBS = True
else:
    P["work_src"] = P.act_share if WORK_OBS else P.pred_share
P["work"] = P.work_src / P.work_src.groupby(P.tract).transform("sum")
P["work"] = P["work"].fillna(0)
P["chained"] = P.act_share / P.act_share.groupby(P.tract).transform("sum")
P["chained"] = P["chained"].fillna(0)
ai, bi = P.a.values, P.b.values
for k in SH:
    P[k] = SH[k][ai, bi]
    P[k] /= P.groupby("tract")[k].transform("sum")
NEEDS = ["work"] + (["chained"] if CHAIN else []) + KINDS_NW
popt = P.tract.map(dict(zip(tr.tract, tr["pop"]))).clip(lower=1).values
u = np.where(rural[ai], 2, 1)
rt = lambda k: np.array([rate[x][k] for x in u])
wfh = pd.read_csv(root / f"analysis/tract_acs_2024{SUF}.csv", dtype={"tract": str}).set_index("tract").wfh
work_days = WORK_DAYS * ((1 - P.tract.map(wfh).fillna(wfh.median()).values) if os.environ.get("WFH") == "1" else 1)
if LEAK == "huffhome":                           # gross leakage: the Huff share of the home county itself
    lam = float(os.environ.get("LEAK_LAMBDA", "2"))
    hi = pd.Series(np.arange(len(cid)), index=cid)
    Dh = D.copy(); Dh[np.arange(len(tr)), hi.reindex(home).fillna(0).astype(int).values] = np.maximum(D[np.arange(len(tr)), hi.reindex(home).fillna(0).astype(int).values], 3)
    U = np.where(D <= 200, DRAW["retail"][None, :] * Dh ** -lam, 0)
    leak_t = 1 - U[np.arange(len(tr)), hi.reindex(home).fillna(0).astype(int).values] / U.sum(1)
    retail_leak = P.tract.map(dict(zip(tr.tract, leak_t))).values
else:
    retail_leak = P.home.map(UNMET["retail"]).values
V = {"work": P.tract.map(out_workers).fillna(0).values / popt * work_days + rt("business"),
     "grocery": P.home.map(UNMET["grocery"]).values * rt("everyday") * GROCERY_SHARE,
     "boxstore": P.home.map(UNMET["boxstore"]).values * rt("everyday") * (1 - GROCERY_SHARE),
     "retail": retail_leak * rt("everyday"),
     "chained": P.tract.map(out_workers).fillna(0).values / popt * np.array([chain_rate[x] for x in u]),
     "medical": P.home.map(UNMET["medical"]).values * rt("medical"),
     "specialty": rt("specialty"), "recreation": rt("recreation"), "visiting": rt("visiting")}
vol = np.column_stack([np.asarray(V[k], float) * MULT.get(k, 1.0) * np.ones(len(P)) for k in NEEDS])
P["combined_share"] = (P[NEEDS].values * vol).sum(1) / vol.sum(1)
for c, n in ((("29151", "Osage"), ("29019", "Boone"), ("29007", "Audrain")) if ST == "29" else (("20091", "Johnson KS"), ("20173", "Sedgwick"), ("20001", "Allen"))):
    m = (P.home == c).values
    first = ~P[m].tract.duplicated().values
    vv = np.average(vol[m][first], weights=popt[m][first], axis=0)      # population-weighted over tracts
    print(f"{n}: out-of-county visit-days per resident per month: " + ", ".join(f"{k} {v:.2f}" for k, v in zip(NEEDS, vv)))
P[["tract", "home", "j", "miles"] + NEEDS + ["combined_share"]].to_csv(root / f"analysis/public_model_pairs_tiers{SUF}{TAG}.csv", index=False)
