"""The published story data: March 2026 local news from the outlets of Boone, Audrain and Osage counties, as the
analysis used it (user, 2026-10-22: these three counties only, no article text).

Inputs (the analysis's own, so the files match its numbers):
  coverage/storymap/statewide_2026_03_articles.json   outlet, its county and type; the story's central county and
                                                      every county it touches
  flows/reach/march_story_points.csv                  the central place: Census geoid, its level, coordinates
  flows/reach/march_story_places.csv                  every place the story names
  coverage/storymap/statewide_2026_03_scope.csv       geographic scope (enrichment)
  coverage/cin_labels_2026_03.csv                     CIN category and the classifier's confidence
  <url_date.csv>                                      URL and publish date, read from production for these ids
Outlets filed in the three counties, less the campus and statewide outlets (analysis/excluded_outlets.py).

Writes data/stories/march_2026_three_counties_articles.csv (one row per article) and
data/stories/march_2026_three_counties_places.csv (one row per article and place named). No headline, no body.

Usage: export_three_county_stories.py <url_date.csv>"""
import csv
import json
import sys
from pathlib import Path

import pandas as pd

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "analysis"))
from excluded_outlets import EXCLUDE  # noqa: E402

COUNTIES = {"Boone": "29019", "Audrain": "29007", "Osage": "29151"}
out = root / "data/stories"
out.mkdir(parents=True, exist_ok=True)
arts = json.load(open(root / "coverage/storymap/statewide_2026_03_articles.json"))["articles"]
mine = {a["id"]: a for a in arts
        if (a["publisher_county"] or "").replace(" County", "").strip() in COUNTIES and a["publisher"] not in EXCLUDE}
ud = pd.read_csv(sys.argv[1], dtype=str).set_index("article_id")
pts = pd.read_csv(root / "flows/reach/march_story_points.csv", dtype={"point_geoid": str}).set_index("article_id")
plc = pd.read_csv(root / "flows/reach/march_story_places.csv", dtype={"geoid": str})
scope = pd.read_csv(root / "coverage/storymap/statewide_2026_03_scope.csv").set_index("article_id").scope
cin = pd.read_csv(root / "coverage/cin_labels_2026_03.csv").set_index("id")
missing = set(mine) - set(ud.index)
assert not missing, f"{len(missing)} articles have no URL/date row"


def kind(t):
    t = t or ""
    return "TV" if "video" in t else "radio" if "audio" in t else "print/digital"


rows = []
for aid, a in sorted(mine.items(), key=lambda kv: (ud.publish_date.get(kv[0], ""), kv[1]["publisher"], kv[0])):
    p = pts.loc[aid] if aid in pts.index else None
    rows.append({
        "article_id": aid,
        "outlet": a["publisher"],
        "outlet_county": a["publisher_county"].replace(" County", "").strip(),
        "outlet_type": kind(a["publisher_type"]),
        "publish_date": ud.publish_date[aid],
        "url": ud.url[aid],
        "central_geoid": "" if p is None or pd.isna(p.point_geoid) else p.point_geoid,
        "central_level": "" if p is None or pd.isna(p.point_geoid_level) else p.point_geoid_level,
        "central_lat": "" if p is None or pd.isna(p.point_lat) else round(float(p.point_lat), 5),
        "central_lon": "" if p is None or pd.isna(p.point_lon) else round(float(p.point_lon), 5),
        "central_county": a["central"] or "",
        "counties": ";".join(a["counties"]),
        "scope": scope.get(aid, "") if isinstance(scope.get(aid, ""), str) else "",
        "cin_category": cin.primary_label.get(aid, "") if isinstance(cin.primary_label.get(aid, ""), str) else "",
        "cin_confidence": "" if pd.isna(cin.primary_label_confidence.get(aid)) else round(float(cin.primary_label_confidence[aid]), 3),
    })
with open(out / "march_2026_three_counties_articles.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
places = plc[plc.article_id.isin(mine)][["article_id", "geoid", "geoid_level", "state", "is_point"]].drop_duplicates()
places = places.assign(is_point=places.is_point.map({"t": 1, "f": 0})).sort_values(["article_id", "is_point", "geoid"],
                                                                                    ascending=[True, False, True])
places.to_csv(out / "march_2026_three_counties_places.csv", index=False)
print(f"{len(rows)} articles, {len(places)} places")
