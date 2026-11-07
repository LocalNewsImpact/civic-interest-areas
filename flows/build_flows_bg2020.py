"""The study counties' block-group flows, January-September 2026, all on 2020 block groups (2026-11-07).

Advan reports January-July 2026 on 2020 block groups and August-September on 2010 block groups (4,506 in Missouri;
build_cousub_shares.py keeps one lookup for each). The areas use all nine months, so August and September are restated
on 2020 block groups, home and destination alike. The weight of 2020 block group b in 2010 block group a is the 2020
population of b's blocks inside a: each 2020 block's population (P1_001N, 2020 PL 94-171 redistricting file, Census API,
cached in census_dl/ref/pl2020_blocks_<county>.csv) times the share of its land inside the 2010 block (Census 2010-2020
tabulation block relationship file, census_dl/TAB2010_TAB2020_ST29.zip), normalized over a; land area where a has no
2020 population. Every count is split by home weight x destination weight. A 2010 home block group's own row (its
residents seen at home) goes to each 2020 block group's own row; pieces whose 2020 destination is the 2020 home are
dropped (travel within home). January-July rows pass through unchanged.

usage: build_flows_bg2020.py. Reads neighborhood/flows_audrain_boone_osage_2026.csv; writes
neighborhood/flows_audrain_boone_osage_2026_bg2020.csv (the same columns) and flows/bg2010_to_bg2020.csv (b10, bg20, w).
"""
import io
import json
import os
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

here = Path(__file__).parent
DL = here.parent / "census_dl"
SRC = here.parent / "neighborhood/flows_audrain_boone_osage_2026.csv"
OUT = here.parent / "neighborhood/flows_audrain_boone_osage_2026_bg2020.csv"
ON_2010 = ("2026-08", "2026-09")


def block_population(county):
    """2020 Census population of every block in the county (state + county FIPS), cached under census_dl/ref, as
    build_homes.py caches it."""
    cache = DL / "ref" / f"pl2020_blocks_{county}.csv"
    if cache.exists():
        return pd.read_csv(cache, dtype={"block": str}).set_index("block")["pop"]
    key = os.environ.get("CENSUS_API_KEY")
    url = (f"https://api.census.gov/data/2020/dec/pl?get=P1_001N&for=block:*&in=state:{county[:2]}%20county:{county[2:]}"
           + (f"&key={key}" if key else ""))
    rows = json.load(urllib.request.urlopen(url, timeout=120))[1:]
    s = pd.DataFrame([(r[1] + r[2] + r[3] + r[4], int(r[0])) for r in rows], columns=["block", "pop"]).set_index("block")["pop"]
    s.to_csv(cache)
    return s


with zipfile.ZipFile(DL / "TAB2010_TAB2020_ST29.zip") as z:
    rel = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), sep="|", dtype=str, encoding="utf-8-sig")
rel = rel[(rel.STATE_2010 == "29") & (rel.STATE_2020 == "29")]
rel["b10"] = rel.STATE_2010 + rel.COUNTY_2010 + rel.TRACT_2010 + rel.BLK_2010.str[:1]
rel["b20"] = rel.STATE_2020 + rel.COUNTY_2020 + rel.TRACT_2020 + rel.BLK_2020
rel["bg20"] = rel.b20.str[:12]
for c in ("AREALAND_2020", "AREALAND_INT"):
    rel[c] = rel[c].astype(float)
pop = pd.concat(block_population(c) for c in sorted({b[:5] for b in rel.b20}))
rel["pop"] = rel.b20.map(pop).fillna(0) * (rel.AREALAND_INT / rel.AREALAND_2020.where(rel.AREALAND_2020 > 0)).fillna(0)
g = rel.groupby(["b10", "bg20"]).agg(pop=("pop", "sum"), land=("AREALAND_INT", "sum")).reset_index()
tp, tl = g.groupby("b10")["pop"].transform("sum"), g.groupby("b10").land.transform("sum")
g["w"] = (g["pop"] / tp).where(tp > 0, g.land / tl.where(tl > 0))
g = g[g.w > 1e-4]                                       # slivers of boundary realignment
g["w"] = g.w / g.groupby("b10").w.transform("sum")
XW = g[["b10", "bg20", "w"]]
XW.to_csv(here / "bg2010_to_bg2020.csv", index=False)
print(f"2010 block groups {XW.b10.nunique():,} -> 2020 {XW.bg20.nunique():,}; one-to-one {(XW.groupby('b10').size() == 1).sum():,}")

f = pd.read_csv(SRC, dtype=str)
NUM = [c for c in f.columns if c.endswith("device_home_areas")]
f[NUM] = f[NUM].astype(float)
keep, new = f[~f.month.isin(ON_2010)], f[f.month.isin(ON_2010)]
names = f.drop_duplicates("home_county").set_index("home_county").home_county_name.to_dict()
hx = XW.rename(columns={"b10": "home_cbg", "bg20": "h20", "w": "wh"})
dx = XW.rename(columns={"b10": "dest_cbg", "bg20": "d20", "w": "wd"})
missing = (~new.home_cbg.isin(hx.home_cbg)).sum() + (~new.dest_cbg.isin(dx.dest_cbg)).sum()
assert missing == 0, f"{missing} August-September block groups not in the relationship file"
own = new[new.home_cbg == new.dest_cbg].merge(hx, on="home_cbg").assign(d20=lambda d: d.h20)
own[NUM] = own[NUM].mul(own.wh, axis=0)
trav = new[new.home_cbg != new.dest_cbg].merge(hx, on="home_cbg").merge(dx, on="dest_cbg")
trav = trav[trav.h20 != trav.d20]
trav[NUM] = trav[NUM].mul(trav.wh * trav.wd, axis=0)
conv = (pd.concat([own, trav]).groupby(["month", "d20", "h20"])[NUM].sum().reset_index()
        .rename(columns={"d20": "dest_cbg", "h20": "home_cbg"}))
conv["dest_county"], conv["home_county"] = conv.dest_cbg.str[:5], conv.home_cbg.str[:5]
conv["home_county_name"] = conv.home_county.map(names)
for m in ON_2010:
    a, b = new[new.month == m], conv[conv.month == m]
    print(f"{m}: devices {a.device_home_areas.sum():,.0f} -> {b.device_home_areas.sum():,.0f}; home block groups "
          f"{a.home_cbg.nunique()} -> {b.home_cbg.nunique()}; seen at home {a[a.home_cbg == a.dest_cbg].device_home_areas.sum():,.0f}"
          f" -> {b[b.home_cbg == b.dest_cbg].device_home_areas.sum():,.0f}")
pd.concat([keep, conv[f.columns]]).to_csv(OUT, index=False)
print("written", OUT.relative_to(here.parent))
