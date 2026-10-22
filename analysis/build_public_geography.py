"""County geography for the public travel model, from public data only.

job centre   Missouri counties: the job-weighted median latitude and median longitude of the county's 2020 tract
             centres of population (CenPop2020_Mean_TR29), jobs = LODES 2023 workplace counts by tract (od_2023.csv.gz,
             S000 by w_geocode). Counties in the neighbouring states: the 2020 centre of population (CenPop2020_Mean_CO),
             since LODES for those states is not downloaded here.
metro class  OMB 2023 delineation (list1_2023.xlsx) and Census 2024 CBSA population (cbsa-est2024-alldata.csv):
             "large" metro >= 500,000; "small" metro < 500,000; "nonmetro" (micropolitan or outside any CBSA). These
             are the National Household Travel Survey MSASIZE classes 3-5, 1-2 and 6.
Output       analysis/county_public_geo.csv: fips, lat, lon, metro_class.
"""
import csv
import gzip
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
REF = root / "census_dl/ref"
tr = pd.read_csv(REF / "CenPop2020_Mean_TR29.txt", dtype=str, encoding="utf-8-sig")
tr["tract"] = tr.STATEFP + tr.COUNTYFP + tr.TRACTCE
tr[["lat", "lon"]] = tr[["LATITUDE", "LONGITUDE"]].astype(float)
jobs = defaultdict(float)
with gzip.open(root / "free/od_2023.csv.gz", "rt") as fh:
    for r in csv.DictReader(fh):
        jobs[r["w_geocode"][:11]] += float(r["S000"])
tr["jobs"] = tr.tract.map(jobs).fillna(0)


def wmedian(v, w):
    o = np.argsort(v); c = np.cumsum(w[o]); return float(v[o][np.searchsorted(c, c[-1] / 2)])


co = pd.read_csv(REF / "CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
co["fips"] = co.STATEFP + co.COUNTYFP
co[["lat", "lon"]] = co[["LATITUDE", "LONGITUDE"]].astype(float)
co = co[co.STATEFP.isin({"29", "17", "20", "19", "05", "40", "31", "47", "21"})].set_index("fips")[["lat", "lon"]]
for c, g in tr.groupby(tr.tract.str[:5]):
    w = g.jobs.values if g.jobs.sum() > 0 else np.ones(len(g))
    co.loc[c, ["lat", "lon"]] = wmedian(g.lat.values, w), wmedian(g.lon.values, w)

d = pd.read_excel(REF / "list1_2023.xlsx", header=2, dtype=str).dropna(subset=["FIPS County Code"])
pop = pd.read_csv(REF / "cbsa-est2024-alldata.csv", encoding="latin-1", dtype=str)
pop = pop[pop.LSAD.str.endswith("Statistical Area")].set_index("CBSA").POPESTIMATE2024.astype(float)
d["fips"] = d["FIPS State Code"] + d["FIPS County Code"]
metro = d[d["Metropolitan/Micropolitan Statistical Area"] == "Metropolitan Statistical Area"]
size = dict(zip(metro.fips, metro["CBSA Code"].map(pop)))
co["metro_class"] = [("large" if size[f] >= 500_000 else "small") if f in size else "nonmetro" for f in co.index]
co.rename_axis("fips").reset_index().to_csv(root / "analysis/county_public_geo.csv", index=False)
m = co[co.index.str[:2] == "29"]
print(m.metro_class.value_counts().to_dict(), "| Osage", m.loc["29151", "metro_class"], "| Audrain", m.loc["29007", "metro_class"])
