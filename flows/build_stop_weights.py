"""Road stops count less in the civic interest areas (authors, 2026-10-26: "short stops should be devalued. They are still
important but not as much as work, school, recreation, healthcare") -> flows/reach/stop_weights.csv

A road stop is analysis/build_road_stop_share.py's "codes" definition: gas stations (447, 4571), convenience stores
(445120, 445131) and limited-service restaurants (722513). Advan Weekly Patterns Plus, the same four full weeks of
March 2026. For each home county i of the market's study counties and each destination block group b: visitors from i to
places in b, and visitors to its road stops. The share is shrunk toward i's share over all of its residents' visits outside
their own block group (K = 200 visitors of prior weight), so a block group seen a few times takes the county's mix.
Neighborhood Patterns Plus (the travel input) records residents seen in a block group, not why; a resident seen in b is
counted at factor = 1 - (1 - W) x share, so road-stop visits count W of other visits (W = 0.5, env STOP_W).
Also writes flows/reach/visit_points.csv (authors, 2026-10-27): every place with visitors from the three counties --
lon, lat, its block group, and those visitors with road stops at W -- the weight market_patterns.py spreads a rural block
group's or a town's travel by (where the visits are, not where mapped destinations are).
Ashland, March 2026: three quarters of Columbia residents' visits are to places where the median stay is 10 minutes or
less, most at the US 63 exit (McDonald's, FastLane, Phillips 66, Casey's, Break Time)."""
import json
import os
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

here = Path(__file__).resolve().parent
root = here.parent
WEEKS = ("2026-03-02", "2026-03-09", "2026-03-16", "2026-03-23")
HOME = ("29007", "29019", "29151")          # Audrain, Boone, Osage
K, W = 200.0, float(os.environ.get("STOP_W", 0.5))
codes = lambda n: n.startswith(("447", "4571", "445120", "445131", "722513"))   # build_road_stop_share.py

tot, stop = defaultdict(float), defaultdict(float)
pts = defaultdict(float)                    # (store, lon, lat, block group) -> visitors from the counties, stops at W
for f in sorted((root / "weekly/raw").glob("*.parquet")):
    if f.name[:10] not in WEEKS:
        continue
    for r in pq.read_table(f, columns=["PERSISTENT_ID_STORE", "NAICS_CODE", "POI_CBG", "VISITOR_HOME_CBGS",
                                       "LONGITUDE", "LATITUDE"]).to_pylist():
        if not r["POI_CBG"] or not r["VISITOR_HOME_CBGS"]:
            continue
        s_ = codes(r["NAICS_CODE"] or "")
        for h, v in json.loads(r["VISITOR_HOME_CBGS"]).items():
            if h[:5] in HOME and h != r["POI_CBG"]:
                tot[(h[:5], r["POI_CBG"])] += v
                stop[(h[:5], r["POI_CBG"])] += v * s_
                if r["LONGITUDE"] is not None:
                    pts[(r["PERSISTENT_ID_STORE"], round(r["LONGITUDE"], 5), round(r["LATITUDE"], 5), r["POI_CBG"])] += v * (W if s_ else 1.0)
pd.DataFrame([(lo, la, b, round(v, 1)) for (_, lo, la, b), v in pts.items()],
             columns=["lon", "lat", "block_group", "visitors"]).to_csv(here / "reach/visit_points.csv", index=False)
print(f"visit points: {len(pts):,} places")
d = pd.DataFrame([(i, b, v, stop[(i, b)]) for (i, b), v in tot.items()], columns=["home_county", "dest_cbg", "visitors", "stop_visitors"])
prior = d.groupby("home_county").apply(lambda g: g.stop_visitors.sum() / g.visitors.sum())
d["share"] = (d.stop_visitors / d.visitors).round(4)
d["share_shrunk"] = ((d.stop_visitors + K * d.home_county.map(prior)) / (d.visitors + K)).round(4)
d["factor"] = (1 - (1 - W) * d.share_shrunk).round(4)
d.sort_values(["home_county", "dest_cbg"]).to_csv(here / "reach/stop_weights.csv", index=False)
print("road-stop share of visits outside the home block group, by home county:", prior.round(3).to_dict())
print(d.sort_values("stop_visitors", ascending=False).head(10).to_string(index=False))
