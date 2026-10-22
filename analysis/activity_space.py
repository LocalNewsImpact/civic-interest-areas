"""The shape of each Missouri tract's regular travel: its activity space, as a proxy for what residents consider local.

Observed: Advan Neighborhood Patterns Plus, January-July 2026 (2020 block groups; August-September use 2010 block
groups), destination block group -> home block groups (DEVICE_HOME_AREAS), summed to home tract x destination block
group; regular = the destination block group appears in at least 4 of the 7 months. Home county INCLUDED: the shape
is where residents go, not how much each place matters (shares of home-county visits are not interpretable).
Geometry: destination block groups (Census 2020 cartographic boundaries) at their representative point, on the 3 km
hexagon grid of the market maps (circumradius 1.5 km; flows/market_patterns.py).
Footprint: the fewest hexagons holding 80% of the tract's regular visits (heaviest first).
Measures per tract:
  area_km2       footprint hexagons x 5.85 km2
  lobes          separate clusters of footprint hexagons (neighbours, or one empty hexagon between) holding at least
                 5% of the visits -- separate markets
  elongation     standard deviational ellipse, long axis / short axis (visit-weighted, all regular visits)
  orientation    of the long axis, degrees from north
  outside_home   share of regular visits outside the home county
  reach_km       visit-weighted median distance from the tract's centre of population
Output analysis/activity_space_mo.csv; analysis/od_tract_bg_mo_2026_janjul.parquet (the tract x block group table).
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

csv_limit = __import__("csv").field_size_limit(sys.maxsize)
root = Path(__file__).resolve().parents[1]
A = root / "analysis"
OUT_TABLE = A / "od_tract_bg_mo_2026_janjul.parquet"

if not OUT_TABLE.exists():
    parts = []
    for f in sorted((root / "neighborhood/raw").glob("2026-0[1-7]*.csv.gz")):
        rows = defaultdict(float)
        for chunk in pd.read_csv(f, usecols=["AREA", "DEVICE_HOME_AREAS"], dtype=str, chunksize=500):
            for area, homes in zip(chunk.AREA, chunk.DEVICE_HOME_AREAS):
                for h, v in json.loads(homes or "{}").items():
                    if h.startswith("29"):
                        rows[h[:11], area] += v
        m = pd.DataFrame([(t, b, v) for (t, b), v in rows.items()], columns=["tract", "bg", "v"])
        m["month"] = f.name[:7]
        parts.append(m)
        print(f.name[:7], len(m), "tract x block group cells", flush=True)
    pq.write_table(pa.Table.from_pandas(pd.concat(parts)), OUT_TABLE)
monthly = pq.read_table(OUT_TABLE).to_pandas()


def regular(months, min_months):
    m = monthly[monthly.month.isin(months)]
    t = m.groupby(["tract", "bg"]).agg(v=("v", "sum"), months=("month", "nunique")).reset_index()
    return t[t.months >= min_months]


ALLM = [f"2026-0{i}" for i in range(1, 8)]
tab = regular(ALLM, 4)
HALF = {"odd": regular(ALLM[0::2], 2), "even": regular(ALLM[1::2], 2)}     # Jan, Mar, May, Jul / Feb, Apr, Jun
print(len(tab), "regular tract x block group cells,", tab.tract.nunique(), "tracts", flush=True)

# geometry (read_shp from flows/build_cousub_shares.py)
_here = root / "flows"
__file__ = str(_here / "build_cousub_shares.py")
exec(open(_here / "build_cousub_shares.py").read().split("\ndef cw(")[0])
_b = read_shp(str(DL / "bg/cb_2020_29_bg_500k"), lambda r: r["GEOID"])
bgpt = {k: (g.representative_point().x, g.representative_point().y) for k, (_, g) in _b.items()}
LAT0, SIZE = 38.7, 1.5
kx, ky = 111.32 * math.cos(math.radians(LAT0)), 110.57
HEX_AREA = 3 * math.sqrt(3) / 2 * SIZE ** 2


def axial(lon, lat):
    x, y = lon * kx, lat * ky
    qf, rf = (math.sqrt(3) / 3 * x - y / 3) / SIZE, (2 / 3 * y) / SIZE
    sf_ = -qf - rf
    rq, rr, rs = round(qf), round(rf), round(sf_)
    dq, dr, ds = abs(rq - qf), abs(rr - rf), abs(rs - sf_)
    if dq > dr and dq > ds:
        rq = -rr - rs
    elif dr > ds:
        rr = -rq - rs
    return rq, rr


hexdist = lambda a, b: (abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[0] + a[1] - b[0] - b[1])) // 2
def geo(t_):
    t_ = t_[t_.bg.isin(bgpt)].copy()
    t_["lon"] = t_.bg.map(lambda b: bgpt[b][0]); t_["lat"] = t_.bg.map(lambda b: bgpt[b][1])
    t_["hex"] = [axial(x, y) for x, y in zip(t_.lon, t_.lat)]
    return t_


tab = geo(tab)
HALF = {k: geo(v) for k, v in HALF.items()}
tr = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_TR29.txt", dtype=str, encoding="utf-8-sig")
tr["t"] = tr.STATEFP + tr.COUNTYFP + tr.TRACTCE
tc = tr.set_index("t")[["LATITUDE", "LONGITUDE"]].astype(float)


def measure(g, t):
    h = g.groupby("hex").v.sum().sort_values(ascending=False)
    tot = h.sum()
    foot = list(h.index[: int((h.cumsum() < 0.8 * tot).sum() + 1)])
    # lobes: clusters with neighbours up to 2 hexagons apart
    left, lobes = set(foot), []
    while left:
        seed = left.pop(); comp = {seed}; stack = [seed]
        while stack:
            c = stack.pop()
            near = [o for o in left if hexdist(c, o) <= 2]
            for o in near:
                left.discard(o); comp.add(o); stack.append(o)
        lobes.append(h[list(comp)].sum() / tot)
    x = (g.lon.values - tc.LONGITUDE[t]) * kx; y = (g.lat.values - tc.LATITUDE[t]) * ky; w = g.v.values / g.v.sum()
    mx, my = (w * x).sum(), (w * y).sum()
    cov = np.cov(np.vstack([x - mx, y - my]), aweights=w)
    ev, evec = np.linalg.eigh(cov)
    elong = math.sqrt(max(ev[1], 1e-9) / max(ev[0], 1e-9))
    orient = (math.degrees(math.atan2(evec[0, 1], evec[1, 1])) + 180) % 180
    d = np.hypot(x, y); o = np.argsort(d); cw = np.cumsum(w[o])
    return {"foot": set(foot), "area_km2": len(foot) * HEX_AREA, "hexes": len(foot), "lobes": sum(s >= 0.05 for s in lobes),
            "elongation": elong, "orientation": orient,
            "outside_home": g.v[g.bg.str[:5] != t[:5]].sum() / g.v.sum(), "reach_km": d[o][np.searchsorted(cw, 0.5)]}


def footprints(t_):
    return {t: measure(g, t) for t, g in t_.groupby("tract") if t in tc.index and g.v.sum() > 0}


out = footprints(tab)
R = pd.DataFrame(out).T.rename_axis("tract")
R.drop(columns="foot").to_csv(A / "activity_space_mo.csv")
# replicability of the observed data: the same footprint from odd and from even months
H = {k: footprints(v) for k, v in HALF.items()}
both = sorted(set(H["odd"]) & set(H["even"]))
jac = [len(H["odd"][t]["foot"] & H["even"][t]["foot"]) / len(H["odd"][t]["foot"] | H["even"][t]["foot"]) for t in both]
lob = [H["odd"][t]["lobes"] == H["even"][t]["lobes"] for t in both]
ar = [H["odd"][t]["area_km2"] / H["even"][t]["area_km2"] for t in both]
print(f"\nREPLICABILITY (Advan, odd vs even months, {len(both)} tracts): footprint overlap (Jaccard) median {np.median(jac):.2f}, "
      f"middle half {np.quantile(jac, .25):.2f}-{np.quantile(jac, .75):.2f}; same number of lobes {100 * np.mean(lob):.0f}%; "
      f"area ratio middle 90% {np.quantile(ar, .05):.2f}-{np.quantile(ar, .95):.2f}")
pickle_out = {t: sorted(v["foot"]) for t, v in out.items()}
__import__("pickle").dump({"all": pickle_out, "odd": {t: sorted(v["foot"]) for t, v in H["odd"].items()},
                           "even": {t: sorted(v["foot"]) for t, v in H["even"].items()}}, open(A / "activity_space_footprints_mo.pkl", "wb"))
R = R.drop(columns="foot")
unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(A / "county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
L = {"class 1": "small rural", "class 2": "indep. towns", "class 3": "commuter", "class 4": "hubs"}
R["cls"] = [L[tier.get(unit(t[:5]), "class 1")] for t in R.index]
R = R.astype({c: float for c in ["area_km2", "hexes", "lobes", "elongation", "orientation", "outside_home", "reach_km"]})
print("\nMedian by class:")
print(R.groupby("cls")[["area_km2", "lobes", "elongation", "outside_home", "reach_km"]].median().round(2).reindex(L.values()).to_string())
print("\nTracts by number of lobes (separate markets), % by class:")
lb = R.assign(lb=np.minimum(R.lobes, 4).astype(int).astype(str).replace("4", "4+")).groupby(["cls", "lb"]).size().unstack().fillna(0)
print((lb.div(lb.sum(axis=1), axis=0) * 100).round(0).reindex(L.values()).to_string())
for t in ["29007950100", "29007950300", "29007950700", "29151480100", "29019000100"]:
    if t in R.index:
        r = R.loc[t]; print(f"  {t}: area {r.area_km2:.0f} km2, lobes {r.lobes:.0f}, elongation {r.elongation:.1f}, orientation {r.orientation:.0f}, outside home {100 * r.outside_home:.0f}%, reach {r.reach_km:.0f} km")
