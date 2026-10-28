"""Travel against coverage OUTSIDE the home county, by county -> ../flows/alignment_2026_03.json.

Residents live in their home county all of the time, so a visit share says nothing about how much the home county
matters to them: the home county is not compared. Both shares are of the home county's totals OUTSIDE it:
travel %   = the county's share of residents' visits to other Missouri counties, January-September 2026 (Advan
             Neighborhood Patterns Plus, ../neighborhood/flows_audrain_boone_osage_2026.csv), with the travel model's
             pass-through discount (../analysis/od_predicted.csv, stop_discount)
coverage % = the county's share of the home county's weighted stories about other Missouri counties, March 2026,
             weighted as the paper's spillover measure (Table 1; authors, 2026-10-28): 1 where a story is centred, 0.5
             for each county it mentions, Sports at half (the story map's articles, storymap/*_articles.json, with
             their CIN category from ../data/stories/march_2026_three_counties_articles.csv). Before 2026-10-28 every
             story-county pair counted 1.
alignment  = smaller / larger, 0..1: 1 is 1:1.
For reference, not comparison: placed stories, stories about the home county, stories about any other county.
Coverage counts only with at least MIN_STORIES stories AND FLOOR% of story-county pairs. Each DMA county is then
  compare       travel >= FLOOR and coverage counts      -> alignment
  travel_only   travel >= FLOOR, coverage does not count -> residents go, few or no stories
  stories_only  coverage counts, travel < FLOOR          -> stories, little travel
and anything else is left off.
"""
import csv
import json
from collections import Counter
from pathlib import Path

here = Path(__file__).parent
flows = here.parent / "flows"
ns = {}
src = (flows / "build_cousub_shares.py").read_text()
exec(src.split('if "--geo" in sys.argv')[0].replace("Path(__file__).parent", f'Path("{flows}")'), ns)
cous = ns["read_shp"](str(here.parent / "census_dl/cousub/cb_2020_29_cousub_500k"), lambda r: r["GEOID"])
NAMES = {c[:5]: rec["NAMELSADCO"].replace(" County", "") for c, (rec, _) in cous.items()}
HOME = {"Audrain": "29007", "Boone": "29019", "Osage": "29151"}
DMA = ["29007", "29019", "29027", "29041", "29051", "29053", "29089", "29125", "29131", "29135", "29139", "29141",
       "29151", "29175"]
FLOOR = 2.0
MIN_STORIES = 5
# travel by destination county, January-September 2026 (the home county is dropped below)
discount = {(r["i"], r["j"]): float(r["stop_discount"]) for r in csv.DictReader(open(here.parent / "analysis/od_predicted.csv"))}
# population calibration by home county and month (../analysis/build_calibration.py)
cal = {(r["county"], r["month"]): float(r["factor"]) for r in csv.DictReader(open(here.parent / "analysis/calibration_county_month.csv"))}
travel = {k: Counter() for k in HOME}
for r in csv.DictReader(open(here.parent / "neighborhood/flows_audrain_boone_osage_2026.csv")):
    if r["month"] <= "2026-09":
        keep = (1 - discount.get((r["home_county"], r["dest_county"]), 0.0)) / cal[(r["home_county"], r["month"])]
        travel[r["home_county_name"]][r["dest_county"]] += int(r["device_home_areas"]) * keep
out = {}
CIN = {r["article_id"]: r["cin_category"] for r in csv.DictReader(open(here.parent / "data/stories/march_2026_three_counties_articles.csv"))}
for f in sorted((here / "storymap").glob("*_all.json")) + [here / "storymap/boone_no_broadcast.json"]:
    d = json.load(open(f))
    county, home = d["county"], HOME[d["county"]]
    arts = json.load(open(here / f"storymap/{f.stem}_articles.json"))
    cov, nstories = Counter(), Counter()
    for a in arts:
        sw = 0.5 if CIN[a["id"]] == "Sports" else 1.0
        for c in a["counties"]:
            if c.startswith("29") and c != home:
                cov[c] += sw * (1.0 if c == a["central"] else 0.5)
                nstories[c] += 1
    ctotal = sum(cov.values())
    ttotal = sum(v for c, v in travel[county].items() if c != home)
    rows = {}
    for c in DMA:
        if c == home:
            continue
        t = 100 * travel[county].get(c, 0) / ttotal
        n = nstories.get(c, 0)
        cv = 100 * cov.get(c, 0) / ctotal if ctotal else 0.0
        counts = n >= MIN_STORIES and cv >= FLOOR
        kind = ("compare" if t >= FLOOR and counts else "travel_only" if t >= FLOOR
                else "stories_only" if counts else None)
        if kind:
            rows[c] = {"name": NAMES[c], "travel": round(t, 1), "coverage": round(cv, 1), "stories": n, "kind": kind,
                       "alignment": round(min(t, cv) / max(t, cv), 2) if kind == "compare" else None}
    out[f.stem] = {"county": county, "home": home, "version": d["version"], "publishers": d["publishers"],
                   "articles": d["articles"], "placed": sum(1 for a in arts if a["counties"]), "weighted": round(ctotal, 1),
                   "stories_home": sum(1 for a in arts if home in a["counties"]),
                   "stories_away": sum(1 for a in arts if any(c.startswith("29") and c != home for c in a["counties"])),
                   "market_weighted": round(sum(n for c, n in cov.items() if c in DMA), 1), "counties": rows}
    print(f.stem, "placed", out[f.stem]["placed"], "home", out[f.stem]["stories_home"], "away", out[f.stem]["stories_away"],
          {v["name"]: (v["kind"], v["travel"], v["stories"], v["coverage"], v["alignment"]) for v in rows.values()})
json.dump({"floor": FLOOR, "min_stories": MIN_STORIES, "maps": out}, open(flows / "alignment_2026_03.json", "w"), indent=1)
