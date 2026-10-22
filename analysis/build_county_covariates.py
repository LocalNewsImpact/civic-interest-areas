"""One row per Missouri county: what might draw or send travel -> county_covariates.csv

population   ACS 2020-2024 5-year (datadesk census_value), free/mo_county_population.csv
lat, lon     2020 Census mean centre of population (CenPop2020) -- where people live, not the map centroid
rucc         USDA ERS Rural-Urban Continuum Code 2023 (1-3 metro, 4-9 nonmetro); metro = rucc <= 3
jobs         LODES 8, 2023, Missouri main OD file: jobs by workplace county
retail       Advan Weekly Patterns Plus places with NAICS 44-45, week of 2026-03-02, by county
places       all Advan Weekly Patterns Plus places that week, by county
"""
import csv
import gzip
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

root = Path(__file__).resolve().parents[1]
pop = {r["fips"]: int(r["population"]) for r in csv.DictReader(open(root / "free/mo_county_population.csv"))}
cen = {}
for r in csv.DictReader(open(root / "census_dl/ref/CenPop2020_Mean_CO29.txt", encoding="utf-8-sig")):
    cen["29" + r["COUNTYFP"]] = (r["COUNAME"], float(r["LATITUDE"]), float(r["LONGITUDE"]))
rucc = {r["FIPS"]: int(r["Value"]) for r in csv.DictReader(open(root / "census_dl/ref/rucc2023.csv", encoding="latin-1"))
        if r["FIPS"].startswith("29") and r["Attribute"] == "RUCC_2023"}
jobs = Counter()
with gzip.open(root / "free/od_2023.csv.gz", "rt") as fh:
    for r in csv.DictReader(fh):
        jobs[r["w_geocode"][:5]] += int(r["S000"])
wk = sorted((root / "weekly/raw").glob("2026-03-02*.parquet"))[0]
t = pq.read_table(wk, columns=["NAICS_CODE", "POI_CBG"]).to_pylist()
retail = Counter(r["POI_CBG"][:5] for r in t if r["POI_CBG"] and (r["NAICS_CODE"] or "")[:2] in ("44", "45"))
places = Counter(r["POI_CBG"][:5] for r in t if r["POI_CBG"])
with open(root / "analysis/county_covariates.csv", "w", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["fips", "name", "population", "lat", "lon", "rucc", "metro", "jobs", "retail", "places"])
    for f in sorted(cen):
        n, lat, lon = cen[f]
        w.writerow([f, n, pop.get(f, ""), lat, lon, rucc.get(f, ""), int(rucc.get(f, 9) <= 3), jobs[f], retail[f], places[f]])
print(len(cen), "counties; missing population", [f for f in cen if f not in pop], "missing rucc", [f for f in cen if f not in rucc])
print("totals: jobs", sum(jobs[f] for f in cen), "retail", sum(retail.values()))
