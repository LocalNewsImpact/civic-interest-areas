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
  E_h         expected units = ACS 2020-2024 population of h x the statewide units per resident that month (option iii,
              adopted): no term taken from seen-at-home in the county
Each block group's leavers are capped at its denominator.

od_unique_mo_2026.csv (unchanged definition): month, home_county, dest_county (as coded; Missouri destinations),
  people_lower (sum over h of min(busiest block group, own_h) / factor), people_summed (summed block groups / factor)
od_people_mo_2026.csv (distinct-people travel outcome; St. Louis merged in home and destination; Missouri and Kansas
  destinations): month, home_county, dest_county,
  people_lower_recorded    sum over h of min(busiest block group of j, E_h), Advan units
  people_lower             people_lower_recorded / factor_statewide: people (the adopted scale)
  people_lower_calibrated  sum over h of min(busiest block group of j, own_h) / county factor (2026-10-16 method)
  visits_recorded          summed block-group counts for the same pair (own block group excluded), Advan units
leaving_unique_mo_2026.csv: month, county (as coded; 29510 and 29189 separate rows, merged by the reader),
  residents_seen_at_home, left_lower, share_left_lower   own_h denominator, Missouri destinations, unit test fixed
  left_lower_coded         as left_lower with the old coded-county test (city <-> county counted as leaving)
  max_seen_any, left_lower_maxany                          option i (Missouri + Kansas destinations)
  denominator_trimmed, left_lower_trimmed, phantom_bgs     option ii
  expected_units, acs_population, left_lower_acs, share_left_acs   option iii (adopted)
  left_lower_acs_mo        option iii, Missouri destinations only
"""
import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

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
    print(month, len(best), "home block group x county cells", flush=True)

with open(A / "od_unique_mo_2026.csv", "w", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["month", "home_county", "dest_county", "people_lower", "people_summed"])
    for (m, i, j), v in sorted(summed.items()):
        k = fac.get((i, m), 1.0)
        w.writerow([m, i, j, round(low[(m, i, j)] / k, 2), round(v / k, 2)])
with open(A / "od_people_mo_2026.csv", "w", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["month", "home_county", "dest_county", "people_lower_recorded", "people_lower", "people_lower_calibrated",
                "visits_recorded"])
    for (m, i, j), (le, lo, sv) in sorted(ppl.items()):
        w.writerow([m, i, j, round(le, 1), round(le / s_m[m], 2), round(lo / fac_u.get((i, m), float("nan")), 2), round(sv, 1)])
cols = ["residents_seen_at_home", "left_lower", "left_lower_coded", "max_seen_any", "left_lower_maxany", "denominator_trimmed",
        "left_lower_trimmed", "phantom_bgs", "expected_units", "acs_population", "left_lower_acs", "left_lower_acs_mo"]
lv = pd.DataFrame([(m, c, *[L[k] for k in cols]) for (m, c), L in sorted(leave.items())], columns=["month", "county", *cols])
lv["share_left_lower"] = (lv.left_lower / lv.residents_seen_at_home.where(lv.residents_seen_at_home > 0)).round(4)
lv["share_left_acs"] = (lv.left_lower_acs / lv.expected_units.where(lv.expected_units > 0)).round(4)
lv = lv[["month", "county", "residents_seen_at_home", "left_lower", "share_left_lower"] + cols[2:] + ["share_left_acs"]]
lv.round(1).to_csv(A / "leaving_unique_mo_2026.csv", index=False)
print("done")
