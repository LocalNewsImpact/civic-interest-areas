"""Out-of-county visits by purpose (NAICS) for each home county, from visits_audrain_boone_osage_2026_03.csv."""
import collections
import csv
from pathlib import Path

NAMES = {'29019':'Boone','29051':'Cole','29027':'Callaway','29007':'Audrain','29151':'Osage','29510':'St. Louis city',
         '29189':'St. Louis Co.','29095':'Jackson','29131':'Miller','29029':'Camden','29175':'Randolph','29089':'Howard',
         '29053':'Cooper','29135':'Moniteau','29073':'Gasconade','29125':'Maries','29139':'Montgomery','29173':'Ralls',
         '29137':'Monroe','29163':'Pike','29183':'St. Charles','29113':'Lincoln','29219':'Warren','29071':'Franklin',
         '29161':'Phelps','29169':'Pulaski','29105':'Laclede','29077':'Greene','29099':'Jefferson','29047':'Clay',
         '29141':'Morgan','29159':'Pettis','29127':'Marion','29213':'Taney'}


def purpose(naics):
    n = naics or ""
    # Advan's weekly file holds no NAICS 62 place at all; a pharmacy is the only health category in it
    if n[:4] == "4461": return "Pharmacy"
    if n[:2] in ("44", "45"): return "Retail"
    if n[:2] == "62": return "Healthcare"
    if n[:3] == "722": return "Restaurants"
    return "Other"


rows = list(csv.DictReader(open(Path(__file__).with_name("visits_audrain_boone_osage_2026_03.csv"))))
print("smallest visitor entry", min(int(r["visitors"]) for r in rows))
for home in ("Audrain", "Boone", "Osage"):
    rs = [r for r in rows if r["home_county_name"] == home]
    hf = rs[0]["home_county"]
    tot = collections.Counter(); out = collections.Counter(); dest = collections.defaultdict(collections.Counter)
    places = collections.defaultdict(collections.Counter)
    for r in rs:
        p, v = purpose(r["naics_code"]), int(r["visitors"])
        tot[p] += v
        if r["poi_county"] != hf:
            out[p] += v; dest[p][r["poi_county"]] += v
            places[p][(r["location_name"], r["city"])] += v
    print(f"\n## {home}")
    print("| Purpose | Visitors (4 wks) | Outside county | Top destination counties | Top places outside |")
    print("|---|---:|---:|---|---|")
    for p in ("Retail", "Pharmacy", "Restaurants", "Other"):
        o = out[p]
        tops = ", ".join(f"{NAMES.get(c, c)} {v / o:.0%}" for c, v in dest[p].most_common(3)) if o else ""
        tp = "; ".join(f"{n} ({c.title()})" for (n, c), _ in places[p].most_common(3))
        print(f"| {p} | {tot[p]:,} | {o / max(1, tot[p]):.0%} | {tops} | {tp} |")
