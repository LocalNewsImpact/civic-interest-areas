"""Calibrate Advan counts to population, by home county and month -> calibration_county_month.csv; rewrites
od_mo_2026.csv with calibrated visits.

Advan Neighborhood Patterns Plus is "normalized against panel size and country population": one national factor, so a
county where the panel holds more of the residents than nationally is inflated (residents seen at home ran 1.2-4.3x
the ACS population in Audrain, Boone and Osage, varying by month). Factor(county, month) = people from the county seen
in their own home block group that month / ACS 2020-2024 population. Every count of the county's residents that month
is divided by it. County, not tract: Aug-Sep 2026 are on 2010 block groups, whose tract codes differ from the 2020
tracts that carry ACS populations; county codes do not change.
od_mo_2026.csv keeps the uncalibrated counts as visits_recorded / work_hours_recorded, so re-running is safe.
"""
import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

csv.field_size_limit(sys.maxsize)
root = Path(__file__).resolve().parents[1]
seen = defaultdict(float)
for f in sorted((root / "neighborhood/raw").glob("*.csv.gz")):
    month = f.name[:7]
    with gzip.open(f, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            a = r["AREA"]
            seen[(a[:5], month)] += float(json.loads(r["DEVICE_HOME_AREAS"] or "{}").get(a, 0))
    print(month, flush=True)
pop = pd.read_csv(root / "free/mo_county_population.csv", dtype={"fips": str}).set_index("fips").population
cal = pd.DataFrame([(c, m, v, pop[c], v / pop[c]) for (c, m), v in seen.items() if c in pop.index],
                   columns=["county", "month", "seen_at_home", "population", "factor"])
cal.to_csv(root / "analysis/calibration_county_month.csv", index=False)
print("factor across counties and months: median", round(cal.factor.median(), 2), "middle 80%",
      round(cal.factor.quantile(.1), 2), "-", round(cal.factor.quantile(.9), 2))
print(cal[cal.county.isin(["29007", "29019", "29151"])].pivot(index="month", columns="county", values="factor").round(2).to_string())

od = pd.read_csv(root / "analysis/od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
if "visits_recorded" not in od:
    od = od.rename(columns={"visits": "visits_recorded", "work_hours_visits": "work_hours_recorded"})
fac = cal.set_index(["county", "month"]).factor
k = [fac.get((h, m), float("nan")) if h != "OUT" else 1.0 for h, m in zip(od.home_county, od.month)]
od["visits"] = od.visits_recorded / k
od["work_hours_visits"] = od.work_hours_recorded / k
od[["month", "home_county", "dest_county", "visits", "work_hours_visits", "visits_recorded", "work_hours_recorded"]].to_csv(
    root / "analysis/od_mo_2026.csv", index=False)
print("od_mo_2026.csv rewritten; rows without a factor:", int(pd.isna(k).sum()))
