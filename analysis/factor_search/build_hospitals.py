"""Missouri hospitals by county -> hospitals_mo.csv (one row per hospital) and county counts.

Base: CMS Hospital General Information (free/mo_hospitals.json), types kept: acute care, critical access, children's,
VA and DoD acute care. Dropped: psychiatric, rural emergency hospitals (no inpatient beds). Clinics are not in this list.
Gap: campuses reporting under another hospital's CMS number after a merger (Capital Region Medical Center, Jefferson
City, under MU Health Care since 2024). OpenStreetMap hospitals (amenity=hospital, osm/missouri-latest.osm.pbf) in a
county with no CMS hospital are printed for review; confirmed campuses are added in ADDED. To confirm (2026-10-16):
Cooper County Memorial Hospital (Boonville) and Southeast Health Center of Ripley County (Doniphan) appear in
OpenStreetMap but not in CMS; Audrain's former hospital (Mexico) closed and is correctly absent.
"""
import json
from pathlib import Path

import osmium
import pandas as pd
import shapely
from shapely.geometry import Point, shape

root = Path(__file__).resolve().parents[2]
KEEP = {"Acute Care Hospitals", "Critical Access Hospitals", "Childrens", "Acute Care - Veterans Administration",
        "Acute Care - Department of Defense"}
ADDED = [("CAPITAL REGION MEDICAL CENTER", "JEFFERSON CITY", "29051", "Acute Care Hospitals (campus under MU Health Care CMS number)")]
cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str})
by_name = {n.lower().replace("st ", "st. "): f for f, n in zip(cov.fips, cov.name)}
# county_covariates names both St. Louis city (29510) and St. Louis County (29189) "St. Louis": set them explicitly
by_name["st. louis"], by_name["st. louis city"] = "29189", "29510"
d = json.load(open(root / "free/mo_hospitals.json"))["results"]
rows = []
for h in d:
    if h["hospital_type"] in KEEP:
        n = h["countyparish"].lower().replace("saint ", "st. ").replace("st ", "st. ")
        f = by_name.get(n) or by_name.get(n + " city")
        rows.append((h["facility_name"], h["citytown"], f, h["hospital_type"]))
rows += ADDED
hosp = pd.DataFrame(rows, columns=["name", "city", "fips", "type"])
print("unmatched counties:", hosp[hosp.fips.isna()].to_string() if hosp.fips.isna().any() else "none")


class H(osmium.SimpleHandler):
    def __init__(self):
        super().__init__(); self.pts = []
    def node(self, n):
        if n.tags.get("amenity") == "hospital":
            self.pts.append((n.tags.get("name", ""), n.location.lon, n.location.lat))
    def area(self, a):
        if a.tags.get("amenity") == "hospital":
            try:
                lon = [nd.lon for r in a.outer_rings() for nd in r]; lat = [nd.lat for r in a.outer_rings() for nd in r]
                self.pts.append((a.tags.get("name", ""), sum(lon) / len(lon), sum(lat) / len(lat)))
            except Exception:
                pass


h = H(); h.apply_file(str(root / "osm/missouri-latest.osm.pbf"), locations=True)
geo = json.load(open(root / "flows/cousub_29.geojson"))
polys = {f["id"]: shape(f["geometry"]) for f in geo["counties"]["features"]}
ids = list(polys); tree = shapely.STRtree([polys[k] for k in ids])
have = set(hosp.fips.dropna())
print(f"\nOSM hospitals: {len(h.pts)}; in counties with no CMS hospital:")
for name, lon, lat in sorted(h.pts):
    hit = tree.query(Point(lon, lat), predicate="within")
    f = ids[hit[0]] if len(hit) else None
    if f and f not in have:
        print(f"  {f} {cov.set_index('fips').name.get(f)}: {name}")
hosp.to_csv(root / "analysis/hospitals_mo.csv", index=False)
print(f"\n{len(hosp)} hospitals kept in {hosp.fips.nunique()} counties")
