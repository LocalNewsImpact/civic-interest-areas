"""Statewide county-to-county travel, Missouri, Jan-Sep 2026 -> od_mo_2026.csv, od_mo_2026_uncapped.csv,
dest_bg_capped_mo_2026.csv. Run AFTER build_calibration.py (its factors are applied here; nothing is rewritten later).

From the raw Advan Neighborhood Patterns Plus files (Dewey; one row per Missouri destination block group per month,
DEVICE_HOME_AREAS = home block group -> devices). Summed to home county x destination county x month, for homes in
Missouri; homes outside Missouri are kept as one total per destination county (home_county 'OUT').

od_mo_2026.csv columns:
  month, home_county, dest_county
  visits, work_hours_visits        recorded / factor (calibration_county_month.csv; the 2026-10-16 calibration)
  visits_recorded, work_hours_recorded   Advan's counts as delivered
  visits_statewide, work_hours_statewide recorded / factor_statewide (one device -> person scale per month, no county term)
  visits_trimmed, work_hours_trimmed     recorded / factor_trimmed (county factor without phantom home block groups)
  'OUT' rows carry recorded counts in every column (no Missouri factor applies).
od_mo_2026_uncapped.csv: the same columns, counted only in destination block group-months whose DEVICE_HOME_AREAS is
  not truncated (fewer than CAP_KEYS = 2,000 home keys). Advan keeps at most 2,000 home block groups per destination
  row; a capped row loses its smallest origins (one or two panel devices each), so long-distance and small-county
  pairs are under-counted there.
dest_bg_capped_mo_2026.csv: month, area, dest_county, home_keys, work_hours_keys, capped (0/1; home_keys >= 2,000),
  devices_home_keyed (sum of DEVICE_HOME_AREAS), device_counts (DEVICE_COUNTS).
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
A = root / "analysis"
RAW = root / "neighborhood/raw"
CAP_KEYS = 2000
cal = pd.read_csv(A / "calibration_county_month.csv", dtype={"county": str})
assert {"factor", "factor_statewide", "factor_trimmed"} <= set(cal.columns), "run build_calibration.py first"
FAC = {k: cal.set_index(["county", "month"])[k].to_dict() for k in ("factor", "factor_statewide", "factor_trimmed")}

cells = defaultdict(lambda: [0, 0])          # all destination block groups
cells_u = defaultdict(lambda: [0, 0])        # uncapped destination block groups only
flags = []
for f in sorted(RAW.glob("*.csv.gz")):
    month = f.name[:7]
    n = ncap = 0
    with gzip.open(f, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            dest = r["AREA"][:5]
            homes = json.loads(r["DEVICE_HOME_AREAS"] or "{}")
            work = json.loads(r["WORK_HOURS_DEVICE_HOME_AREAS"] or "{}")
            capped = len(homes) >= CAP_KEYS
            flags.append((month, r["AREA"], dest, len(homes), len(work), int(capped), sum(homes.values()),
                          float(r["DEVICE_COUNTS"] or 0)))
            for d, k in ((homes, 0), (work, 1)):
                for h, v in d.items():
                    key = (month, h[:5] if h.startswith("29") else "OUT", dest)
                    cells[key][k] += v
                    if not capped:
                        cells_u[key][k] += v
            n += 1
            ncap += capped
    print(month, n, "destination block groups,", ncap, "capped", flush=True)


def write(c, path):
    rows = []
    for (m, h, d), (v, wv) in sorted(c.items()):
        out = [m, h, d]
        for k in ("factor", "factor_statewide", "factor_trimmed"):
            x = 1.0 if h == "OUT" else FAC[k].get((h, m), float("nan"))
            out += [v / x, wv / x]
        rows.append(out[:5] + [v, wv] + out[5:])
    d = pd.DataFrame(rows, columns=["month", "home_county", "dest_county", "visits", "work_hours_visits", "visits_recorded",
                                    "work_hours_recorded", "visits_statewide", "work_hours_statewide", "visits_trimmed",
                                    "work_hours_trimmed"])
    assert d.loc[d.home_county != "OUT", "visits"].notna().all(), "home county-month without a calibration factor"
    d.to_csv(path, index=False)
    return d


od = write(cells, A / "od_mo_2026.csv")
odu = write(cells_u, A / "od_mo_2026_uncapped.csv")
fl = pd.DataFrame(flags, columns=["month", "area", "dest_county", "home_keys", "work_hours_keys", "capped",
                                  "devices_home_keyed", "device_counts"])
fl.to_csv(A / "dest_bg_capped_mo_2026.csv", index=False)
x = od[(od.home_county != "OUT") & (od.home_county != od.dest_county)].groupby("month").visits_recorded.sum()
xu = odu[(odu.home_county != "OUT") & (odu.home_county != odu.dest_county)].groupby("month").visits_recorded.sum()
print(len(od), "cells;", len(odu), "in uncapped destinations")
print("capped destination block groups by month:", fl.groupby("month").capped.sum().to_dict())
print("share of Missouri out-of-county device-visits in capped destination block groups:", (1 - xu / x).round(3).to_dict())
