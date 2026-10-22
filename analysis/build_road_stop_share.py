"""Share of each county pair's visits that are highway stops -> road_stop_share.csv

Advan Weekly Patterns Plus, Missouri places, the four full weeks of March 2026 (2026-03-02 .. 03-23). For every place,
VISITOR_HOME_CBGS gives visitors by home block group; summed to home county x place county. A "road stop" is a gas
station (NAICS 4471 / 4571), a convenience store (445131) or a limited-service restaurant (722513). The check on the
travel model's "on the way" factor: a county on the route to somewhere else should show a high road-stop share.
"""
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

root = Path(__file__).resolve().parents[1]
WEEKS = ("2026-03-02", "2026-03-09", "2026-03-16", "2026-03-23")
road = lambda n: (n or "").startswith(("4471", "4571", "445131", "722513"))
tot, stop = defaultdict(float), defaultdict(float)
for f in sorted((root / "weekly/raw").glob("*.parquet")):
    if f.name[:10] not in WEEKS:
        continue
    t = pq.read_table(f, columns=["NAICS_CODE", "POI_CBG", "VISITOR_HOME_CBGS"]).to_pylist()
    for r in t:
        if not r["POI_CBG"] or not r["VISITOR_HOME_CBGS"]:
            continue
        j, is_stop = r["POI_CBG"][:5], road(r["NAICS_CODE"])
        for h, n in json.loads(r["VISITOR_HOME_CBGS"]).items():
            if h.startswith("29"):
                tot[(h[:5], j)] += n
                if is_stop:
                    stop[(h[:5], j)] += n
    print(f.name[:10], len(tot), "pairs so far", flush=True)
out = pd.DataFrame([(i, j, v, stop[(i, j)]) for (i, j), v in tot.items()], columns=["i", "j", "visitors", "road_stop_visitors"])
out["road_stop_share"] = out.road_stop_visitors / out.visitors
out.to_csv(root / "analysis/road_stop_share.csv", index=False)
x = out[out.i != out.j]
print(f"{len(x):,} county pairs; road-stop share, visitor-weighted: {x.road_stop_visitors.sum() / x.visitors.sum():.1%}; "
      f"within home county: {out[out.i == out.j].road_stop_visitors.sum() / out[out.i == out.j].visitors.sum():.1%}")
