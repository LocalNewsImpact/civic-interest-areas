"""Share of RESIDENTS (people/devices) seen outside their home county in a month -- not visits.

Advan Neighborhood Patterns Plus reports, for each destination block group, people by HOME block group (population-
scaled). People from different home block groups are distinct, so each home block group h is handled on its own:
  residents_h   people from h seen in h itself that month (2026-10-16 denominator; inflated where Advan over-detects
                homes -- see build_calibration.py)
  E_h           expected units: ACS 2020-2024 population of h x the statewide units per resident that month
                (home_bg_month_mo_2026.csv; the adopted denominator, review 2026-10-24, option iii)
  p_hc          people from h seen in outside block group c / the denominator      (c in another county)
  lower         max_c p_hc                       at least the busiest outside block group's share left
  by_county     sum over destination counties of that county's busiest block group's share (capped at 1): each
                county counted once -- low within a county, high for people seen in several counties
  (Rejected: 1 - prod(1 - p_hc) and sum_c p_hc both run to ~100% -- thousands of small outside entries add up; the
  smallest entry Advan reports is one panel device x the monthly scale, 14-20 people in 2026.) Work-hours numerators
  use the all-day denominator.
County share = denominator-weighted mean over its home block groups; averaged over Jan-Sep 2026. Columns lower /
by_county use residents_h, lower_acs / by_county_acs use E_h. Also with work-hours counts (seen there in working hours)
as a stricter "regular" version. Missouri destinations only (the three counties do not border Kansas).
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
hb = pd.read_csv(root / "analysis/home_bg_month_mo_2026.csv", dtype={"home_bg": str})
E = hb.set_index(["month", "home_bg"]).expected_units.to_dict()
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
    for (m, h) in set(own) | set(peak[col]):
        n_home = own.get((m, h), 0.0)
        by =np.array(list(out[col][(m, h)].values()) or [0.0])
        for den, lab in ((n_home, ""), (E.get((m, h), 0.0), "_acs")):
            if den > 0:
                rows.append((m, h[:5], lab, den, min(1.0, peak[col][(m, h)] / den), min(1.0, by.sum() / den)))
    d = pd.DataFrame(rows, columns=["month", "county", "lab", "residents", "lower", "by_county"])
    for c in ("lower", "by_county"):
        d[c + "_w"] = d[c] * d.residents
    g = d.groupby(["lab", "county", "month"])[["residents", "lower_w", "by_county_w"]].sum()
    for c in ("lower", "by_county"):
        g[c] = g[c + "_w"] / g.residents
    s = g.groupby(["lab", "county"])[["lower", "by_county"]].mean().unstack(0)
    s.columns = [a + b for a, b in s.columns]
    s["measure"] = "seen outside the county in a month" if col == "device_home_areas" else "seen outside in working hours"
    res.append(s)
t = pd.concat(res).reset_index()
t["name"] = t.county.map(HOME)
print("| County | Measure | Lower bound (busiest outside block group), / seen at home | / ACS x statewide rate | "
      "Each destination county counted once, / seen at home | / ACS x statewide rate |")
print("|---|---|---:|---:|---:|---:|")
for r in t.sort_values(["name", "measure"], ascending=[True, False]).itertuples():
    print(f"| {r.name} | {r.measure} | {r.lower:.0%} | {r.lower_acs:.0%} | {r.by_county:.0%} | {r.by_county_acs:.0%} |")
t[["county", "lower", "by_county", "measure", "name", "lower_acs", "by_county_acs"]].to_csv(
    root / "analysis/residents_leaving_three_counties.csv", index=False)
