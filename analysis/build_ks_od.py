"""Kansas county-to-county travel, January-September 2026 -> analysis/od_ks_2026.csv, and Kansas calibration factors
-> analysis/calibration_county_month_ks.csv (the Kansas counterparts of build_statewide_od.py and build_calibration.py).
Advan Neighborhood Patterns Plus (Dewey): Kansas destination block groups from neighborhood/raw_ks/*.parquet; Missouri
destination block groups from neighborhood/raw/*.csv.gz (Kansans' visits to Missouri). DEVICE_HOME_AREAS = home block
group -> devices; summed to home county x destination county x month for homes in Kansas.

od_ks_2026.csv columns: month, home_county, dest_county,
  visits, work_hours_visits                  recorded counts (unchanged: ks_advan_fitted.py and score_ks.py read visits)
  visits_recorded, work_hours_recorded       the same, named as in od_mo_2026.csv
  visits_calibrated, work_hours_calibrated   recorded / factor (calibration_county_month_ks.csv)
  visits_statewide, work_hours_statewide     recorded / factor_statewide
calibration_county_month_ks.csv (as Missouri's): county, month, seen_at_home (Kansans seen in their own home block
  group), population (ACS 2020-2024 B01003, census_dl/acs_tract/b01003.dat), factor = seen_at_home / population,
  max_seen_any (per home block group, its residents in the busiest single block group, Kansas or Missouri; summed),
  units_per_resident = Kansas sum of max_seen_any / Kansas population (one value per month), factor_statewide (= it).
"""
import csv
import glob
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
cells = defaultdict(lambda: [0, 0])
types = defaultdict(int)
own = defaultdict(float)                 # (month, home bg) -> seen at home
mx = defaultdict(float)                  # (month, home bg) -> busiest block group


def add(month, area, home_json, work_json):
    dest = area[:5]
    for col, k in ((home_json, 0), (work_json, 1)):
        for h, v in json.loads(col or "{}").items():
            if h.startswith("20"):
                cells[(month, h[:5], dest)][k] += v
                if k == 0:
                    if h == area:
                        own[(month, h)] = float(v)
                    if v > mx[(month, h)]:
                        mx[(month, h)] = float(v)


for f in sorted(glob.glob(str(root / "neighborhood/raw_ks/*.parquet"))):
    t = pq.read_table(f, columns=["AREA", "AREA_TYPE", "DATE_RANGE_START", "DEVICE_HOME_AREAS", "WORK_HOURS_DEVICE_HOME_AREAS"]).to_pylist()
    for r in t:
        types[r["AREA_TYPE"]] += 1
        add(str(r["DATE_RANGE_START"])[:7], r["AREA"], r["DEVICE_HOME_AREAS"], r["WORK_HOURS_DEVICE_HOME_AREAS"])
    print("KS", Path(f).name[:10], len(t), "destination areas", flush=True)
for f in sorted(glob.glob(str(root / "neighborhood/raw/*.csv.gz"))):
    n = 0
    with gzip.open(f, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            if '"20' in (r["DEVICE_HOME_AREAS"] or ""):
                add(r["DATE_RANGE_START"][:7], r["AREA"], r["DEVICE_HOME_AREAS"], r["WORK_HOURS_DEVICE_HOME_AREAS"])
            n += 1
    print("MO", Path(f).name[:10], n, "destination areas", flush=True)
print("area types:", dict(types))

pop = {}
for line in open(root / "census_dl/acs_tract/b01003.dat"):
    if line.startswith("0500000US20"):
        g, e, _ = line.strip().split("|")
        pop[g[9:]] = float(e)
seen, best = defaultdict(float), defaultdict(float)
for (m, h), v in own.items():
    seen[(h[:5], m)] += v
for (m, h), v in mx.items():
    best[(h[:5], m)] += v
cal = pd.DataFrame([(c, m, seen.get((c, m), 0.0), pop[c], best[(c, m)]) for (c, m) in sorted(best) if c in pop],
                   columns=["county", "month", "seen_at_home", "population", "max_seen_any"])
cal["factor"] = cal.seen_at_home / cal.population
s = cal.groupby("month").max_seen_any.sum() / sum(pop.values())
cal["units_per_resident"] = cal.month.map(s)
cal["factor_statewide"] = cal.units_per_resident
cal = cal[["county", "month", "seen_at_home", "population", "factor", "max_seen_any", "units_per_resident", "factor_statewide"]]
cal.to_csv(A / "calibration_county_month_ks.csv", index=False)
print(f"Kansas factor across {cal.county.nunique()} counties x months: median {cal.factor.median():.2f}, middle 80% "
      f"{cal.factor.quantile(.1):.2f}-{cal.factor.quantile(.9):.2f}, county medians {cal.groupby('county').factor.median().min():.2f}-"
      f"{cal.groupby('county').factor.median().max():.2f}; units per resident {s.round(3).to_dict()}")
F = cal.set_index(["county", "month"])[["factor", "factor_statewide"]].to_dict("index")
nan = {"factor": float("nan"), "factor_statewide": float("nan")}
with open(A / "od_ks_2026.csv", "w", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["month", "home_county", "dest_county", "visits", "work_hours_visits", "visits_recorded", "work_hours_recorded",
                "visits_calibrated", "work_hours_calibrated", "visits_statewide", "work_hours_statewide"])
    for (m, h, d), (v, wv) in sorted(cells.items()):
        k = F.get((h, m), nan)
        w.writerow([m, h, d, v, wv, v, wv, v / k["factor"], wv / k["factor"], v / k["factor_statewide"], wv / k["factor_statewide"]])
print(len(cells), "cells")
