"""Distinct people, de-duplicated: statewide, Missouri homes, Jan-Sep 2026. Run after build_calibration.py.

From the raw Advan Neighborhood Patterns Plus files: Missouri destination block groups (neighborhood/raw) and Kansas
destination block groups (neighborhood/raw_ks). Illinois, Iowa, Arkansas, Oklahoma and Nebraska destinations are not
in the data: a Missouri resident seen only there is not observed leaving. For each month, home block group h and
destination unit j, the people from h seen in j's single busiest block group are all distinct, and people from
different home block groups are distinct, so a home COUNTY's figure is a sum over its block groups. h's own block
group is left out of every destination figure. St. Louis city (29510) and county (29189) are one unit (29189) wherever
"another county" is tested: unit() is applied BEFORE the left-the-county test.

Denominator per home block group (review 2026-10-24; see crossover_compare.py for the comparison):
  own_h       residents seen at home (2026-10-16 measure; inflated where Advan over-detects homes)
  max_any_h   largest count of h's residents in any one block group (option i)
  trim_h      own_h, or E_h where h is a phantom home block group (own_h > 3 x E_h) (option ii)
  E_h         expected units = ACS 2020-2024 population of h x the statewide units per resident that month (option iii):
              no term taken from seen-at-home in the county
  D_h         ADOPTED (user decision 2026-10-24, option A): calibrated, E_h x (own_h / E_h)^(1 - b), b estimated here
              from how leaving falls with home detection across months (see below); b = 1 gives E_h, b = 0 gives own_h
Each block group's leavers are capped at its denominator.

od_unique_mo_2026.csv (unchanged definition): month, home_county, dest_county (as coded; Missouri destinations),
  people_lower (sum over h of min(busiest block group, own_h) / factor), people_summed (summed block groups / factor)
od_people_mo_2026.csv (distinct-people travel outcome; St. Louis merged in home and destination; Missouri and Kansas
  destinations): month, home_county, dest_county,
  people_lower_recorded    sum over h of min(busiest block group of j, D_h), Advan units
  people_lower             sum over h of min(busiest block group of j, D_h) x ACS population_h / D_h: people (adopted)
  people_lower_b1          sum over h of min(busiest block group of j, E_h) / factor_statewide (b = 1 sensitivity)
  people_lower_calibrated  sum over h of min(busiest block group of j, own_h) / county factor (2026-10-16 method)
  visits_recorded          summed block-group counts for the same pair (own block group excluded), Advan units
leaving_unique_mo_2026.csv: month, county (as coded; 29510 and 29189 separate rows, merged by the reader),
  residents_seen_at_home, left_lower, share_left_lower   own_h denominator, Missouri destinations, unit test fixed
  left_lower_coded         as left_lower with the old coded-county test (city <-> county counted as leaving)
  max_seen_any, left_lower_maxany                          option i (Missouri + Kansas destinations)
  denominator_trimmed, left_lower_trimmed, phantom_bgs     option ii
  expected_units, acs_population, left_lower_acs, share_left_acs   option iii (adopted)
  left_lower_acs_mo        option iii, Missouri destinations only
  denominator_calibrated, left_lower_calibrated   D_h (adopted)
  denominator_b0, left_lower_b0                    own_h (E_h where own_h = 0), Missouri + Kansas: the b = 0 bound
  denominator_linear, left_lower_linear            sensitivity: (1 - b) own_h + b E_h (the excess split linearly)
  denominator_max, left_lower_dmax / denominator_min, left_lower_dmin
                           max(own_h, E_h) / min(own_h, E_h) (E_h where own_h = 0), leavers capped at each: the
                           county figure's true low and high bounds over every b in [0, 1]
crossover_bg_month_mo_2026.csv: month, home_bg, own, expected_units, denominator_calibrated (D_h), acs_population, b
  (read by residents_leaving.py, residents_leaving_tracts.py, unique_people_by_county.py)
  detection_slope_b, detection_slope_b_lo, detection_slope_b_hi   b and its 95% interval (same in every row)
"""
import csv
import gzip
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

csv.field_size_limit(sys.maxsize)
root = Path(__file__).resolve().parents[1]
A = root / "analysis"
unit = lambda c: "29189" if c == "29510" else c
cal = pd.read_csv(A / "calibration_county_month.csv", dtype={"county": str})
assert "factor_statewide" in cal, "run build_calibration.py first"
fac = cal.set_index(["county", "month"]).factor.to_dict()
s_m = cal.groupby("month").factor_statewide.first().to_dict()
cal["u"] = cal.county.map(unit)
g = cal.groupby(["u", "month"])[["seen_at_home", "population"]].sum()
fac_u = (g.seen_at_home / g.population).to_dict()
hb = pd.read_csv(A / "home_bg_month_mo_2026.csv", dtype={"home_bg": str, "county": str})
HB = {m: x.set_index("home_bg")[["own", "max_seen_any", "expected_units", "phantom", "acs_population"]].to_dict("index")
      for m, x in hb.groupby("month")}

low, summed = defaultdict(float), defaultdict(float)
ppl = defaultdict(lambda: [0.0, 0.0, 0.0])           # (m, i_unit, j_unit) -> [lower at E, lower at own, summed]
leave = defaultdict(lambda: defaultdict(float))       # (m, county) -> measure -> value
bgrows = []                                           # (month, h, own, E, busiest outside block group, ACS population)
pairs_hj = []                                         # (month, h, j unit, busiest block group of j, summed)
for f in sorted((root / "neighborhood/raw").glob("*.csv.gz")):
    month = f.name[:7]
    best = defaultdict(float)            # (h, j coded) -> busiest Missouri block group count
    best_u = defaultdict(float)          # (h, j unit, MO + KS) -> busiest block group count
    sum_u = defaultdict(float)
    out = {k: defaultdict(float) for k in ("coded", "unit_mo", "unit_all")}

    def take(a, homes, ks):
        j = a[:5]
        for h, v in homes.items():
            if not h.startswith("29") or h == a:
                continue
            v = float(v)
            ju, hu = unit(j), unit(h[:5])
            if v > best_u[(h, ju)]:
                best_u[(h, ju)] = v
            sum_u[(h, ju)] += v
            if ju != hu and v > out["unit_all"][h]:
                out["unit_all"][h] = v
            if ks:
                continue
            if v > best[(h, j)]:
                best[(h, j)] = v
            summed[(month, h[:5], j)] += v
            if j != h[:5] and v > out["coded"][h]:
                out["coded"][h] = v
            if ju != hu and v > out["unit_mo"][h]:
                out["unit_mo"][h] = v
    with gzip.open(f, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            take(r["AREA"], json.loads(r["DEVICE_HOME_AREAS"] or "{}"), False)
    for p in (root / "neighborhood/raw_ks").glob(f"{month}-01*.parquet"):
        for r in pq.read_table(p, columns=["AREA", "DEVICE_HOME_AREAS"]).to_pylist():
            if '"29' in (r["DEVICE_HOME_AREAS"] or ""):
                take(r["AREA"], json.loads(r["DEVICE_HOME_AREAS"]), True)
    H = HB[month]
    z = {"own": 0.0, "max_seen_any": 0.0, "expected_units": 0.0, "phantom": 0, "acs_population": 0.0}
    for (h, j), v in best.items():
        low[(month, h[:5], j)] += min(v, H.get(h, z)["own"])
    for (h, j), v in best_u.items():
        b = H.get(h, z)
        c = ppl[(month, unit(h[:5]), j)]
        c[0] += min(v, b["expected_units"])
        c[1] += min(v, b["own"])
        c[2] += sum_u[(h, j)]
        pairs_hj.append((month, h, j, v, sum_u[(h, j)]))
    for h, b in H.items():
        L = leave[(month, h[:5])]
        trim = b["expected_units"] if b["phantom"] else b["own"]
        L["residents_seen_at_home"] += b["own"]
        L["left_lower"] += min(out["unit_mo"].get(h, 0.0), b["own"])
        L["left_lower_coded"] += min(out["coded"].get(h, 0.0), b["own"])
        L["max_seen_any"] += b["max_seen_any"]
        L["left_lower_maxany"] += min(out["unit_all"].get(h, 0.0), b["max_seen_any"])
        L["denominator_trimmed"] += trim
        L["left_lower_trimmed"] += min(out["unit_all"].get(h, 0.0), trim)
        L["phantom_bgs"] += b["phantom"]
        L["expected_units"] += b["expected_units"]
        L["acs_population"] += b["acs_population"]
        L["left_lower_acs"] += min(out["unit_all"].get(h, 0.0), b["expected_units"])
        L["left_lower_acs_mo"] += min(out["unit_mo"].get(h, 0.0), b["expected_units"])
        bgrows.append((month, h, b["own"], b["expected_units"], out["unit_all"].get(h, 0.0), b["acs_population"]))
    print(month, len(best), "home block group x county cells", flush=True)

with open(A / "od_unique_mo_2026.csv", "w", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["month", "home_county", "dest_county", "people_lower", "people_summed"])
    for (m, i, j), v in sorted(summed.items()):
        k = fac.get((i, m), 1.0)
        w.writerow([m, i, j, round(low[(m, i, j)] / k, 2), round(v / k, 2)])
cols = ["residents_seen_at_home", "left_lower", "left_lower_coded", "max_seen_any", "left_lower_maxany", "denominator_trimmed",
        "left_lower_trimmed", "phantom_bgs", "expected_units", "acs_population", "left_lower_acs", "left_lower_acs_mo"]
lv = pd.DataFrame([(m, c, *[L[k] for k in cols]) for (m, c), L in sorted(leave.items())], columns=["month", "county", *cols])
lv["share_left_lower"] = (lv.left_lower / lv.residents_seen_at_home.where(lv.residents_seen_at_home > 0)).round(4)
lv["share_left_acs"] = (lv.left_lower_acs / lv.expected_units.where(lv.expected_units > 0)).round(4)

# ---- calibrated denominator (user decision 2026-10-24, option A) --------------------------------------------------------
# Within a county, block groups where Advan detects more phones at home than the ACS predicts (d_h = own_h / E_h > 1)
# show a lower leaving rate (busiest outside block group / own_h). Regressing log leaving rate in month m2 on log
# detection in month m1 (m1 != m2, same block-group vintage, so the noise in own_h is not shared), county x month-pair
# fixed effects, ACS-population weights: slope = -b. b = 1: the extra phones never leave (phantoms; denominator E_h);
# b = 0: they leave like residents (denominator own_h). Every ordered month pair is stacked (both directions, equal
# weight); the interval is clustered by county. Denominator D_h = E_h x d_h^(1 - b) (= own_h^(1-b) E_h^b); D_h = E_h
# where own_h = 0 (detection unknown); D_h = 0 where E_h = 0 (no ACS residents). Leavers capped at D_h.
B = pd.DataFrame(bgrows, columns=["month", "h", "own", "E", "out", "pop"])
B["cu"] = B.h.str[:5].map(unit)
B["vintage"] = np.where(B.month <= "2026-07", 2020, 2010)
ok = (B.own > 0) & (B.E > 0)
B.loc[ok, "ld"] = np.log(B.own[ok] / B.E[ok])
B.loc[ok & (B.out > 0), "lr"] = np.log(B.out[ok & (B.out > 0)] / B.own[ok & (B.out > 0)])


def slope(st):
    """weighted within (pair, county) slope of lr on ld; county-clustered s.e."""
    g = st.groupby(["pair", "cu"])
    w = st["pop"]
    x = st.ld - (st.ld * w).groupby([st.pair, st.cu]).transform("sum") / g["pop"].transform("sum")
    y = st.lr - (st.lr * w).groupby([st.pair, st.cu]).transform("sum") / g["pop"].transform("sum")
    sxx = (w * x * x).sum()
    bta = (w * x * y).sum() / sxx
    sc = (w * x * (y - bta * x)).groupby(st.cu).sum()
    G = len(sc)
    se = np.sqrt((sc ** 2).sum() * G / (G - 1)) / sxx
    return bta, se


parts = []
for v, x in B[ok].groupby("vintage"):
    months = sorted(x.month.unique())
    det = {m: x[x.month == m].set_index("h").ld for m in months}
    lea = {m: x[(x.month == m) & x.lr.notna()].set_index("h")[["lr", "pop", "cu"]] for m in months}
    for m1, m2 in itertools.permutations(months, 2):
        j = lea[m2].join(det[m1], how="inner")
        parts.append(j.assign(pair=f"{m1}>{m2}"))
st = pd.concat(parts).reset_index(drop=True)
st = st[st["pop"] > 0]
bta, se = slope(st)
b = -bta
for pr in ("2026-03>2026-06", "2026-06>2026-03"):
    bb, ss = slope(st[st.pair == pr])
    print(f"cross-month slope, detection {pr[:7]} -> leaving {pr[-7:]}: {bb:+.3f} [{bb - 1.96 * ss:+.3f}, {bb + 1.96 * ss:+.3f}]")
print(f"detection slope, all {st.pair.nunique()} ordered month pairs stacked (both directions): {bta:+.3f} "
      f"[{bta - 1.96 * se:+.3f}, {bta + 1.96 * se:+.3f}] (county-clustered; {len(st):,} block-group pairs, "
      f"{st.cu.nunique()} counties) -> b = {b:.3f}")
B["D"] = np.where(ok, B.E * np.exp((1 - b) * B.ld.fillna(0)), np.where(B.own <= 0, B.E, 0.0))
B["D0"] = np.where(B.own > 0, B.own, B.E)
B["Dlin"] = np.where(B.own > 0, (1 - b) * B.own + b * B.E, B.E)    # sensitivity: the excess phones split linearly
B["county"] = B.h.str[:5]
# true bounds on the calibrated county figure: for every b in [0, 1], D_h lies between min(own_h, E_h) and
# max(own_h, E_h) (own^(1-b) E^b is monotone in b, rising or falling with d_h); D_h = E_h where own_h = 0 in all three
B["Dmax"] = np.where(B.own > 0, np.maximum(B.own, B.E), B.E)
B["Dmin"] = np.where(B.own > 0, np.minimum(B.own, B.E), B.E)
B["L_cal"] = np.minimum(B.out, B.D)
B["L0"] = np.minimum(B.out, B.D0)
B["Llin"] = np.minimum(B.out, B.Dlin)
B["Lmax"] = np.minimum(B.out, B.Dmax)
B["Lmin"] = np.minimum(B.out, B.Dmin)
cal_lv = B.groupby(["month", "county"]).agg(denominator_calibrated=("D", "sum"), left_lower_calibrated=("L_cal", "sum"),
                                            denominator_b0=("D0", "sum"), left_lower_b0=("L0", "sum"),
                                            denominator_linear=("Dlin", "sum"), left_lower_linear=("Llin", "sum"),
                                            denominator_max=("Dmax", "sum"), left_lower_dmax=("Lmax", "sum"),
                                            denominator_min=("Dmin", "sum"), left_lower_dmin=("Lmin", "sum")).reset_index()
lv = lv.merge(cal_lv, on=["month", "county"], how="left")
SLOPE = {"detection_slope_b": round(b, 4), "detection_slope_b_lo": round(-(bta + 1.96 * se), 4),
         "detection_slope_b_hi": round(-(bta - 1.96 * se), 4)}
lv = lv[["month", "county", "residents_seen_at_home", "left_lower", "share_left_lower"] + cols[2:] + ["share_left_acs",
        "denominator_calibrated", "left_lower_calibrated", "denominator_b0", "left_lower_b0", "denominator_linear",
        "left_lower_linear", "denominator_max", "left_lower_dmax", "denominator_min", "left_lower_dmin"]].round(1).assign(**SLOPE)
lv.to_csv(A / "leaving_unique_mo_2026.csv", index=False)
B[["month", "h", "own", "E", "D", "pop"]].rename(columns={"h": "home_bg", "E": "expected_units", "D": "denominator_calibrated",
                                                          "pop": "acs_population"}).round(1).assign(**SLOPE).to_csv(
    A / "crossover_bg_month_mo_2026.csv", index=False)

# distinct-people travel outcome, capped at the calibrated denominator; people = units x ACS population / D_h
Dk = {(m, h): (d, e, p) for m, h, d, e, p in zip(B.month, B.h, B.D, B.E, B["pop"])}
ppl2 = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])      # [lower at D (units), people at D, lower at E / s_m, summed]
for m, h, j, v, sv in pairs_hj:
    d, e, p = Dk.get((m, h), (0.0, 0.0, 0.0))
    c = ppl2[(m, unit(h[:5]), j)]
    c[0] += min(v, d)
    c[1] += min(v, d) * p / d if d > 0 else 0.0
    c[2] += min(v, e) / s_m[m]
    c[3] += sv
with open(A / "od_people_mo_2026.csv", "w", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["month", "home_county", "dest_county", "people_lower_recorded", "people_lower", "people_lower_b1",
                "people_lower_calibrated", "visits_recorded"])
    for (m, i, j), (ld, pd_, pe, sv) in sorted(ppl2.items()):
        lo = ppl[(m, i, j)][1]
        w.writerow([m, i, j, round(ld, 1), round(pd_, 2), round(pe, 2), round(lo / fac_u.get((i, m), float("nan")), 2), round(sv, 1)])
print("done")
