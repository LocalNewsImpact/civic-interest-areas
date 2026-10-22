"""Advan Neighborhood Patterns Plus -> tract_shares_advan_<month>.json, the data behind tract_markets_advan.html.

Input: ../neighborhood/flows_audrain_boone_osage_2026.csv (extract.py over the Dewey export: Missouri destination
block groups, Jan-Sep 2026; one row per month x destination block group x home block group in the three counties).
Each tract's rate is the county's devices recorded in the tract over all its devices recorded in any Missouri tract
outside the county, in percent -- the measure tract_markets.html draws. The export holds Missouri destinations only,
so travel out of state is in neither part of the share.
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

month = sys.argv[1] if len(sys.argv) > 1 else "2026-03"
col = sys.argv[2] if len(sys.argv) > 2 else "device_home_areas"
here = Path(__file__).parent
counts = defaultdict(lambda: defaultdict(int))
for r in csv.DictReader(open(here.parent / "neighborhood/flows_audrain_boone_osage_2026.csv")):
    if r["month"] != month or r["dest_county"] == r["home_county"]:
        continue
    counts[r["home_county_name"]][r["dest_cbg"][:11]] += int(r[col])
out = {}
for county, tracts in counts.items():
    total = sum(tracts.values())
    out[county] = {t: {"rate": round(100 * v / total, 3)} for t, v in tracts.items() if v}
    top = sorted(out[county].items(), key=lambda kv: -kv[1]["rate"])[:3]
    print(f"{county:8} {len(out[county]):5} tracts  outside total {total:,}  top {[(t, x['rate']) for t, x in top]}")
suffix = month.replace("-", "_") + ("" if col == "device_home_areas" else "_" + col.replace("_device_home_areas", ""))
json.dump(out, open(here / f"tract_shares_advan_{suffix}.json", "w"))
