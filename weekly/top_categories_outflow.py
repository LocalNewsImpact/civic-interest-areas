"""Top place categories (Advan TOP_CATEGORY) of each home county's visits outside the county, weeks of March 2026,
with the most-visited named places in each. A place whose name is only its category ("Used Car Dealers") is counted
but not offered as an example."""
import collections
import csv
from pathlib import Path

N = 8
rows = list(csv.DictReader(open(Path(__file__).with_name("visits_audrain_boone_osage_2026_03.csv"))))
for home in ("Audrain", "Boone", "Osage"):
    rs = [r for r in rows if r["home_county_name"] == home and r["poi_county"] != r["home_county"]]
    total = sum(int(r["visitors"]) for r in rs)
    cat = collections.Counter(); places = collections.defaultdict(collections.Counter)
    for r in rs:
        v = int(r["visitors"]); c = r["top_category"] or "(none)"
        cat[c] += v
        n = (r["location_name"] or "").strip()
        if n and n not in (r["top_category"], r["sub_category"]) and not n.endswith(("Dealers", "Restaurants", "Stores")):
            places[c][(n, (r["city"] or "").title())] += v
    print(f"\n## {home} — {total:,} visits outside the county")
    print("| Category | Share | Examples (city) |\n|---|---:|---|")
    for c, v in cat.most_common(N):
        ex = "; ".join(f"{n} ({city})" for (n, city), _ in places[c].most_common(3))
        print(f"| {c} | {v / total:.1%} | {ex} |")
