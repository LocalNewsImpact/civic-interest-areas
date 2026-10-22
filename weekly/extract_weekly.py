"""Advan Weekly Patterns Plus (Dewey; Missouri places, weeks of 2026-03-02 .. 2026-03-23) -> one row per
week x place x home block group in Audrain, Boone or Osage.

Citation: Advan Research. (2025). Foot Traffic / Weekly Patterns Plus [Data set]. Dewey Data.
https://doi.org/10.82551/C103-N851
The week of 2026-03-30 runs into April and is left out. VISITOR_HOME_CBGS counts visitors (people), per week.
"""

import csv
import glob
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

here = Path(__file__).parent
WEEKS = ("2026-03-02", "2026-03-09", "2026-03-16", "2026-03-23")
HOME = {"29007": "Audrain", "29019": "Boone", "29151": "Osage"}
COLS = ["DATE_RANGE_START", "PERSISTENT_ID", "LOCATION_NAME", "BRAND", "TOP_CATEGORY", "SUB_CATEGORY",
        "NAICS_CODE", "LATITUDE", "LONGITUDE", "POI_CBG", "CITY", "STREET_ADDRESS", "VISITOR_COUNTS",
        "VISITOR_HOME_CBGS"]
out = here / "visits_audrain_boone_osage_2026_03.csv"
with open(out, "w", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["week", "place_id", "location_name", "brand", "top_category", "sub_category", "naics_code",
                "latitude", "longitude", "poi_cbg", "poi_county", "city", "street_address", "place_visitors",
                "home_cbg", "home_county", "home_county_name", "visitors"])
    for f in sorted(glob.glob(str(here / "raw/*.parquet"))):
        week = Path(f).name[:10]
        if week not in WEEKS:
            continue
        n = 0
        for r in pq.read_table(f, columns=COLS).to_pylist():
            homes = json.loads(r["VISITOR_HOME_CBGS"] or "{}")
            for h, v in homes.items():
                if h[:5] in HOME:
                    poi = r["POI_CBG"] or ""
                    w.writerow([week, r["PERSISTENT_ID"], r["LOCATION_NAME"], r["BRAND"],
                                (r["TOP_CATEGORY"] or "").strip(), (r["SUB_CATEGORY"] or "").strip(),
                                r["NAICS_CODE"], r["LATITUDE"], r["LONGITUDE"], poi, poi[:5], r["CITY"],
                                r["STREET_ADDRESS"], r["VISITOR_COUNTS"], h, h[:5], HOME[h[:5]], v])
                    n += 1
        print(week, n, "place x home rows", flush=True)
print(out)
