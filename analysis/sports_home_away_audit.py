"""Sports stories centred away from home, before and after the focus-v4 re-run (home-team rule).

A Sports story is spillover when the county it is centred in is not the outlet's home county. Before focus-v4 the
enrichment model centred a game story on where it was played; focus-v4 centres it on the publication's local team.
This compares each re-run Sports story's centre county in the story-map export made before the re-run
(coverage/rerun_2026_10_17/statewide_export_pre_sports.json) with the current export, and writes the stories still
centred away from home for reading (coverage/rerun_2026_10_17/sports_still_away.csv).
"""
import json
from pathlib import Path

import pandas as pd

root = Path(__file__).resolve().parents[1]
R = root / "coverage/rerun_2026_10_17"
ids = set(open(R / "sports_ids.txt").read().split())
cin = pd.read_csv(root / "coverage/cin_labels_2026_03.csv").set_index("id").primary_label
cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str}).set_index("fips")
name_of = cov.name.to_dict()
by_name = {n.lower(): f for f, n in name_of.items()}
by_name.update({"st. louis": "29189", "st louis": "29189", "st. louis city": "29510"})
fips_of = lambda n: by_name.get((n or "").lower().replace(" county", "").strip())
unit = lambda f: "29189" if f == "29510" else f
titles = pd.read_csv(R / "sports_before_articles.csv").set_index("id").title


def frame(path):
    rows = []
    for a in json.load(open(path))["articles"]:
        if cin.get(a["id"]) != "Sports":
            continue
        h = fips_of(a["publisher_county"])
        c = a["central"]
        rows.append({"id": a["id"], "outlet": a["publisher"], "type": a["publisher_type"] or "", "home": h,
                     "central": c, "away": bool(c) and bool(h) and unit(c) != unit(h)})
    return pd.DataFrame(rows).set_index("id")


b = frame(R / "statewide_export_pre_sports.json")
a = frame(root / "coverage/storymap/statewide_2026_03_articles.json")
x = b.join(a[["central", "away"]], rsuffix="_after", how="inner")
x["rerun"] = x.index.isin(ids)
x["broadcast"] = x.type.str.contains("broadcast")
print(f"Sports stories in both exports: {len(x)} ({x.rerun.sum()} re-run)")
for label, s in (("re-run", x[x.rerun]), ("not re-run", x[~x.rerun])):
    print(f"\n## {label}: {len(s)} stories")
    t = pd.crosstab(s.away.map({True: "away", False: "home"}).rename("before"),
                    s.away_after.map({True: "away", False: "home"}).rename("after"), margins=True)
    print(t.to_string())
    for kind, k in (("print/digital", s[~s.broadcast]), ("broadcast", s[s.broadcast])):
        if len(k):
            print(f"  {kind}: centred away {k.away.mean():.1%} before, {k.away_after.mean():.1%} after ({len(k)})")
still = x[x.away_after].assign(title=lambda y: y.index.map(titles), home_name=lambda y: y.home.map(name_of),
                               central_name=lambda y: y.central_after.map(name_of))
still[["outlet", "home_name", "central_name", "rerun", "title"]].sort_values(["outlet"]).to_csv(R / "sports_still_away.csv")
print(f"\nstill centred away: {len(still)} -> {R / 'sports_still_away.csv'}")
