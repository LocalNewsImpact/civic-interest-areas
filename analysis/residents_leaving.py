"""Share of RESIDENTS (people/devices) seen outside their home county in a month -- not visits.

Advan Neighborhood Patterns Plus reports, for each destination block group, people by HOME block group (population-
scaled). People from different home block groups are distinct, so each home block group h is handled on its own:
  residents_h   people from h seen in h itself that month (everyone active is seen at home)
  p_hc          people from h seen in outside block group c / residents_h        (c in another county)
  lower         max_c p_hc                       at least the busiest outside block group's share left
  by_county     sum over destination counties of that county's busiest block group's share (capped at 1): each
                county counted once -- low within a county, high for people seen in several counties
  (Rejected: 1 - prod(1 - p_hc) and sum_c p_hc both run to ~100% -- thousands of small outside entries, many at
  Advan's privacy floor, add up.) Work-hours numerators use the all-day residents as the denominator.
County share = residents-weighted mean over its home block groups; averaged over Jan-Sep 2026. Also with work-hours
counts (seen there in working hours) as a stricter "regular" version. Missouri destinations only.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
src = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "neighborhood/flows_audrain_boone_osage_2026.csv"
HOME = {"29007": "Audrain", "29019": "Boone", "29151": "Osage"}
res = []
# residents: people from h seen in h itself, all day (the denominator for both measures)
own, out = {}, {"device_home_areas": defaultdict(lambda: defaultdict(float)),
                "work_hours_device_home_areas": defaultdict(lambda: defaultdict(float))}
peak = {c: defaultdict(float) for c in out}
for r in csv.DictReader(open(src)):
    k = (r["month"], r["home_cbg"])
    if r["dest_cbg"] == r["home_cbg"]:
        own[k] = float(r["device_home_areas"])
    elif r["dest_county"] != r["home_county"]:
        for col in out:
            v = float(r[col])
            # per destination COUNTY: its busiest block group -- people seen in that county, counted once (low)
            out[col][k][r["dest_county"]] = max(out[col][k][r["dest_county"]], v)
            peak[col][k] = max(peak[col][k], v)
for col in out:
    rows = []
    for (m, h), n_home in own.items():
        if n_home <= 0:
            continue
        by_county = np.array(list(out[col][(m, h)].values()) or [0.0]) / n_home
        rows.append((m, h[:5], n_home, min(1.0, peak[col][(m, h)] / n_home), min(1.0, by_county.sum())))
    d = pd.DataFrame(rows, columns=["month", "county", "residents", "lower", "by_county"])
    for c in ("lower", "by_county"):
        d[c + "_w"] = d[c] * d.residents
    g = d.groupby(["county", "month"])[["residents", "lower_w", "by_county_w"]].sum()
    for c in ("lower", "by_county"):
        g[c] = g[c + "_w"] / g.residents
    s = g.groupby("county")[["lower", "by_county"]].mean()
    s["measure"] = "seen outside the county in a month" if col == "device_home_areas" else "seen outside in working hours"
    res.append(s)
t = pd.concat(res).reset_index()
t["name"] = t.county.map(HOME)
print("| County | Measure | Lower bound (busiest outside block group) | Each destination county counted once |")
print("|---|---|---:|---:|")
for r in t.sort_values(["name", "measure"], ascending=[True, False]).itertuples():
    print(f"| {r.name} | {r.measure} | {r.lower:.0%} | {r.by_county:.0%} |")
t.to_csv(root / "analysis/residents_leaving_three_counties.csv", index=False)
