"""REGULAR-TRAVEL DISTANCE per study town (authors, 2026-10-25): "People are not driving 120 miles for errands or even 60
miles regularly." D80 / D90 / D95 = the distance from the town's CENTRE OF POPULATION (the 2020-population-weighted mean
of its home block groups' Census population centres) within which 80 / 90 / 95% of its residents' regular travel lies.
Data: Advan Neighborhood Patterns Plus, January-July 2026, the block-group flows the patterns are fitted on
(regions.json "flows"; DEVICE_HOME_AREAS by month, destination block group and home block group). The town's home block
groups are those of the patterns (<region out>/homes.csv: town, or the town's place).
REGULAR = a destination block group seen from a home block group in 4+ of the 7 months (the definition of
analysis/activity_space.py, there per home tract; here per home block group, the patterns' home unit -- per TOWN, every
destination of a large town passes: Columbia D90 177 km). Weight = residents seen there (device home counts) summed over
the months -- activity_space.py's visit weight -- then over the town's home block groups. (Weighting by reach x the
home block group's population instead moves D90 by at most 3 km: Columbia 100.0, Mexico 51.8, Linn 102.5.) The home block group's own row
(residents seen at home) is not travel and is left out; travel inside the town counts. Destination at its block group's
2020 population centre, else its county's.
Writes flows/regular_distance.json {town: {region, centre: [lon, lat], D80, D90, D95, regular_destinations, weight}}.
Usage: regular_distance.py"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

here = Path(__file__).resolve().parent
root = here.parent
REG = {k: v for k, v in json.load(open(here / "regions.json")).items() if k == "columbia"}   # the Columbia-Jefferson City TV market only
MONTHS = [f"2026-0{m}" for m in range(1, 8)]
ref = root / "census_dl/ref"
cp = pd.concat([pd.read_csv(ref / f"CenPop2020_Mean_BG{s}.txt", dtype=str, encoding="utf-8-sig") for s in ("29", "20")])
cp["bg"] = cp.STATEFP + cp.COUNTYFP + cp.TRACTCE + cp.BLKGRPCE
BG = {b: (float(lo), float(la), float(p)) for b, lo, la, p in zip(cp.bg, cp.LONGITUDE, cp.LATITUDE, cp.POPULATION)}
co = pd.read_csv(ref / "CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
CO = {s + c: (float(lo), float(la)) for s, c, lo, la in zip(co.STATEFP, co.COUNTYFP, co.LONGITUDE, co.LATITUDE)}


def km(lon1, lat1, lon2, lat2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def wq(d, w, q):
    o = np.argsort(d)
    c = np.cumsum(w[o]) / w.sum()
    return float(d[o][np.searchsorted(c, q)])


out = {}
for flows in sorted({c["flows"] for c in REG.values()}):
    regions = [r for r, c in REG.items() if c["flows"] == flows]
    town_bgs = {}
    for r in regions:
        hm = pd.read_csv(root / REG[r]["out"] / "homes.csv", dtype={"home_cbg": str, "place": str})
        for t, (_, place) in REG[r]["towns"].items():
            town_bgs[t] = (r, set(hm.home_cbg[(hm.town == t) | (hm.place == place)]))
    bg_town = {b: t for t, (_, bs) in town_bgs.items() for b in bs}
    parts = []
    for ch in pd.read_csv(root / flows, usecols=["month", "dest_cbg", "dest_county", "home_cbg", "device_home_areas"],
                          dtype={"dest_cbg": str, "home_cbg": str, "dest_county": str}, chunksize=2_000_000):
        ch = ch[ch.month.isin(MONTHS) & ch.home_cbg.isin(bg_town) & (ch.dest_cbg != ch.home_cbg)]
        parts.append(ch.groupby(["home_cbg", "dest_cbg", "dest_county", "month"]).device_home_areas.sum().reset_index())
    f = pd.concat(parts).groupby(["home_cbg", "dest_cbg", "dest_county", "month"]).device_home_areas.sum().reset_index()
    g = f.groupby(["home_cbg", "dest_cbg", "dest_county"]).agg(w=("device_home_areas", "sum"), months=("month", "nunique")).reset_index()
    g = g[g.months >= 4].assign(town=lambda d: d.home_cbg.map(bg_town))
    for t, (r, bs) in town_bgs.items():
        pts = [BG[b] for b in bs if b in BG]
        P_ = sum(p for *_, p in pts)
        clon, clat = sum(lo * p for lo, _, p in pts) / P_, sum(la * p for _, la, p in pts) / P_
        s = g[g.town == t]
        ll = [BG.get(b, CO.get(c, (np.nan, np.nan)))[:2] for b, c in zip(s.dest_cbg, s.dest_county)]
        lon, lat = np.array([x[0] for x in ll]), np.array([x[1] for x in ll])
        d, w = km(clon, clat, lon, lat), s.w.to_numpy(float)
        ok = ~np.isnan(d)
        if not ok.any():
            print(t, "no regular travel", flush=True); continue
        out[t] = {"region": r, "centre": [round(clon, 5), round(clat, 5)], "home_block_groups": len(bs),
                  **{f"D{int(q * 100)}": round(wq(d[ok], w[ok], q), 1) for q in (0.8, 0.9, 0.95)},
                  "regular_destinations": int(ok.sum()), "weight": round(float(w[ok].sum())),
                  "unplaced_weight_share": round(float(w[~ok].sum() / w.sum()), 4)}
        print(t, out[t], flush=True)
json.dump(out, open(here / "regular_distance.json", "w"), indent=1)
print("wrote", here / "regular_distance.json")
