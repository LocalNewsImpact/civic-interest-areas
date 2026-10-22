"""Mid-Missouri cross-county flows: the data behind the schematic (flows.json).

Sources (all free; years differ, which the credit line says):
- GeoDS / SafeGraph weekly county-to-county flows, 2021 (Kang et al., Scientific Data 2020): `pop_flows`,
  people x places x week scaled to the population. Averaged over the 52 weeks.
- Census LEHD LODES 8, 2023: workers by home and work county (one per job).
- CMS Hospital Service Area File, 2023: Medicare inpatient stays by patient ZIP and hospital. 2023, not 2025:
  from 2024 Capital Region Medical Center (Jefferson City) reports under MU Health Care's Columbia number.

A schematic, not a count: weekly visits are rounded, and commuting is the work share of them (GeoDS counts a
person once per place per week, so a commuter adds about one visit a week for the workplace).
"""

import glob
import json
from pathlib import Path

import pandas as pd

FREE = Path.home() / "VSCode/advan/free"

COUNTIES = {  # FIPS: (name, primary?) -- the map places each at its county's centre
    "29007": ("Audrain", True),
    "29019": ("Boone", True),
    "29151": ("Osage", True),
    "29027": ("Callaway", False),
    "29051": ("Cole", False),
}
NAMES = {k: v[0] for k, v in COUNTIES.items()}

# phone flows: the 2021 weekly average for each ordered pair
# Some files carry an extra seventh column (census_block_group, or from late June 2021 number_devices_primary_daytime),
# which moves the date and both flow counts one place right: read each file by its own width.
cols = ["o", "d", "lng_o", "lat_o", "lng_d", "lat_d", "week", "visitor_flows", "pop_flows"]


def read_week(f):
    wide = len(open(f).readline().split(",")) == 10
    names = cols[:6] + ["extra"] + cols[6:] if wide else cols
    return pd.read_csv(f, header=None, names=names, dtype={"o": str, "d": str})[cols]


files = sorted(glob.glob(str(FREE / "weeks5/weekly_county2county_2021_*.csv")))
g = pd.concat(read_week(f) for f in files)
assert g.week.str.match(r"\d\d/\d\d/21 - ").all(), "a 2021 file was read with the wrong layout"
weeks = g.week.nunique()
visits = (g.groupby(["o", "d"]).pop_flows.sum() / weeks).to_dict()

# workers
w = pd.read_csv(FREE / "od_2023.csv.gz", dtype={"w_geocode": str, "h_geocode": str}, usecols=["w_geocode", "h_geocode", "S000"])
w["o"], w["d"] = w.h_geocode.str[:5], w.w_geocode.str[:5]
workers = w[w.o.isin(COUNTIES) & w.d.isin(COUNTIES)].groupby(["o", "d"]).S000.sum().to_dict()

# hospital stays: each ZIP to the county holding most of its land; hospitals by the provider list's county
z = pd.read_csv(FREE / "zcta_county.txt", sep="|", dtype=str, encoding="utf-8-sig")
z = z[z.GEOID_ZCTA5_20.notna()].assign(land=lambda x: pd.to_numeric(x.AREALAND_PART))
zip_county = z.sort_values("land").groupby("GEOID_ZCTA5_20").tail(1).set_index("GEOID_ZCTA5_20").GEOID_COUNTY_20
hosp_county = {x["facility_id"]: x["countyparish"].title() for x in json.load(open(FREE / "mo_hospitals.json"))["results"]}
# not in today's hospital list: Capital Region Medical Center (Jefferson City), its rehab unit (letter T in the third
# place marks a unit of the hospital with the same last three digits), Rusk Rehabilitation Center (Columbia; CMS IRF
# list), Boone Hospital's rehab unit and MU Health Care's psychiatric unit (S)
hosp_county.update({"260047": "Cole", "26T047": "Cole", "263027": "Boone", "26T068": "Boone", "26S141": "Boone"})
h = pd.read_csv(FREE / "hsaf_2023.csv", dtype=str)
h.columns = [c.upper() for c in h.columns]
h = h[h.ZIP_CD_OF_RESIDENCE.map(zip_county).isin(COUNTIES)].copy()
h["home"] = h.ZIP_CD_OF_RESIDENCE.map(zip_county)
h["cases"] = pd.to_numeric(h.TOTAL_CASES, errors="coerce")
h["where"] = h.MEDICARE_PROV_NUM.map(lambda p: hosp_county.get(p, "elsewhere"))
hospital = {}
for fips in COUNTIES:
    x = h[h.home == fips]
    tot = x.cases.sum()
    by = (x.groupby("where").cases.sum() / tot).sort_values(ascending=False)
    hospital[fips] = [{"county": k, "share": round(float(v), 2)} for k, v in by.head(2).items() if v >= 0.05]

# population: ACS 2020-2024 five-year estimates, from datadesk's census layers (county_population.csv)
pop = pd.read_csv(FREE / "county_population.csv", dtype={"fips": str}).set_index("fips").population.to_dict()
nodes = []
for fips, (name, primary) in COUNTIES.items():
    nodes.append({"fips": fips, "county": name, "primary": primary, "population": int(pop[fips]) if fips in pop else None,
                  "stay_home_share": round(visits.get((fips, fips), 0) / sum(v for (o, _), v in visits.items() if o == fips), 2),
                  "hospital": hospital[fips]})
flows = []
for o in COUNTIES:
    for d in COUNTIES:
        if o == d:
            continue
        v = visits.get((o, d), 0)
        flows.append({"from": o, "to": d, "weekly": round(v), "workers": int(workers.get((o, d), 0))})
out = {"nodes": nodes, "flows": flows, "weeks": weeks}
json.dump(out, open(Path(__file__).with_name("flows.json"), "w"), indent=1)
for f in sorted(flows, key=lambda f: -f["weekly"]):
    print(f"{NAMES[f['from']]:9} -> {NAMES[f['to']]:9} {f['weekly']:8,}/wk   workers {f['workers']:6,}   work share {f['workers'] / max(1, f['weekly']):5.1%}")
print({n["county"]: n["hospital"] for n in nodes})
