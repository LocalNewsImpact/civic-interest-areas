"""Calibrate Advan counts to population, by home county and month -> calibration_county_month.csv,
home_bg_month_mo_2026.csv, bg_acs_population.csv. Run BEFORE build_statewide_od.py, which applies the factors.

Advan Neighborhood Patterns Plus is "normalized against panel size and country population": one national factor, so a
county where the panel holds more of the residents than nationally is inflated. Every count is a whole number of panel
devices x one monthly scale (the smallest value in a capped row, 14-20 in 2026, is one panel device).

calibration_county_month.csv, one row per Missouri county x month:
  county, month, seen_at_home, population, factor
      factor = people from the county seen in their own home block group that month / ACS 2020-2024 population (the
      2026-10-16 calibration). It ranges 0.24-10.8 across county-months: it measures home detection as much as panel
      size (Scotland: 40-60k "seen at home" against 4,686 people; St. Louis city: residents seen in another block group
      more often than at home in 82% of block groups).
  max_seen_any         sum over the county's home block groups of the largest count of the block group's residents in
                       any ONE block group (its own or another; Missouri and Kansas destinations): at least this many
                       distinct devices live there
  units_per_resident   statewide, one value per month: sum of max_seen_any over Missouri / Missouri ACS population
  factor_statewide     = units_per_resident: the device -> person scale with no county term (review 2026-10-24,
                       crossover option iii). Counts / factor_statewide are people at the statewide panel rate.
  seen_at_home_trimmed, population_trimmed, factor_trimmed
                       as factor, leaving out phantom home block groups (below); a county whose home block groups are
                       all phantom takes factor_statewide
  home_bgs, phantom_bgs, home_bgs_no_own_key
home_bg_month_mo_2026.csv, one row per Missouri home block group x month (every block group that has a row or a key):
  month, home_bg, county, own (residents seen in the block group itself; 0 when it has no own key), own_key (0/1),
  max_seen_any, acs_population (ACS 2020-2024 B01003; Aug-Sep 2010 block groups by area-weighted overlay of the 2020
  block groups), expected_units = acs_population x units_per_resident, home_ratio = own / expected_units,
  phantom = home_ratio > PHANTOM (3; block groups with no ACS population and own > 0 are phantom)
bg_acs_population.csv: bg, vintage (2020 / 2010), population -- built once from census_dl/ (b01003.dat; cb_2020 and
  gz_2010 block-group shapes).
County, not tract, for the factor: Aug-Sep 2026 are on 2010 block groups, whose tract codes differ from the 2020
tracts; county codes do not change. od_mo_2026.csv is not touched here (it used to be rewritten in place).
"""
import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

csv.field_size_limit(sys.maxsize)
root = Path(__file__).resolve().parents[1]
A = root / "analysis"
PHANTOM = 3.0


def bg_population():
    """ACS 2020-2024 block-group population, 2020 block groups and (area-weighted) 2010 block groups."""
    f = A / "bg_acs_population.csv"
    if f.exists():
        return pd.read_csv(f, dtype={"bg": str})
    import shapefile
    from shapely.geometry import shape
    from shapely.strtree import STRtree
    acs = {}
    for line in open(root / "census_dl/acs_tract/b01003.dat"):
        if line.startswith("1500000US29"):
            g, e, _ = line.strip().split("|")
            acs[g[9:]] = float(e)

    def read(base, key):
        return {key(sr.record.as_dict()): shape(sr.shape.__geo_interface__).buffer(0)
                for sr in shapefile.Reader(str(base)).iterShapeRecords()}
    b20 = read(root / "census_dl/bg/cb_2020_29_bg_500k", lambda d: d["GEOID"])
    b10 = read(root / "census_dl/bg2010/gz_2010_29_150_00_500k", lambda d: d["STATE"] + d["COUNTY"] + d["TRACT"] + d["BLKGRP"])
    k10 = list(b10)
    tree = STRtree([b10[k] for k in k10])
    p10 = dict.fromkeys(k10, 0.0)
    for g, geom in b20.items():
        hits = [(k10[i], geom.intersection(b10[k10[i]]).area) for i in tree.query(geom)]
        tot = sum(x for _, x in hits)
        for k, x in hits:
            if x > 0 and acs.get(g, 0) > 0:
                p10[k] += acs[g] * x / tot
    d = pd.DataFrame([(g, 2020, acs.get(g, 0.0)) for g in b20] + [(k, 2010, round(v, 1)) for k, v in p10.items()],
                     columns=["bg", "vintage", "population"])
    d.to_csv(f, index=False)
    return d


rows = []
for f in sorted((root / "neighborhood/raw").glob("*.csv.gz")):
    month = f.name[:7]
    own, mx, areas = {}, defaultdict(float), set()

    def take(a, homes):
        for h, v in homes.items():
            if h.startswith("29"):
                v = float(v)
                if v > mx[h]:
                    mx[h] = v
                if h == a:
                    own[h] = v
    with gzip.open(f, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            areas.add(r["AREA"])
            take(r["AREA"], json.loads(r["DEVICE_HOME_AREAS"] or "{}"))
    for g in (root / "neighborhood/raw_ks").glob(f"{month}-01*.parquet"):
        for r in pq.read_table(g, columns=["AREA", "DEVICE_HOME_AREAS"]).to_pylist():
            if '"29' in (r["DEVICE_HOME_AREAS"] or ""):
                take(r["AREA"], json.loads(r["DEVICE_HOME_AREAS"]))
    homes = sorted(h for h in areas | set(mx) if h.startswith("29"))
    nokey = [h for h in homes if h not in own]
    print(month, len(homes), "home block groups;", len(nokey), "with no own key (residents never seen at home):",
          " ".join(nokey), flush=True)
    rows += [(month, h, own.get(h, 0.0), int(h in own), mx.get(h, 0.0)) for h in homes]

bg = pd.DataFrame(rows, columns=["month", "home_bg", "own", "own_key", "max_seen_any"])
bg["county"] = bg.home_bg.str[:5]
pop_bg = bg_population()
bg["vintage"] = np.where(bg.month <= "2026-07", 2020, 2010)
bg = bg.merge(pop_bg.rename(columns={"bg": "home_bg", "population": "acs_population"}), on=["home_bg", "vintage"], how="left")
print("home block groups without an ACS population row:", int(bg.acs_population.isna().sum()))
bg["acs_population"] = bg.acs_population.fillna(0.0)
s = bg.groupby("month").max_seen_any.sum() / bg.groupby("month").acs_population.sum()
bg["expected_units"] = bg.acs_population * bg.month.map(s)
pos = bg.expected_units > 0
bg["home_ratio"] = np.where(pos, bg.own / bg.expected_units.where(pos, 1.0), np.where(bg.own > 0, np.inf, 0.0))
bg["phantom"] = (bg.home_ratio > PHANTOM).astype(int)
bg[["month", "home_bg", "county", "own", "own_key", "max_seen_any", "acs_population", "expected_units", "home_ratio",
    "phantom"]].round({"expected_units": 1, "home_ratio": 3}).to_csv(A / "home_bg_month_mo_2026.csv", index=False)

pop = pd.read_csv(root / "free/mo_county_population.csv", dtype={"fips": str}).set_index("fips").population
cal = bg.groupby(["county", "month"]).agg(seen_at_home=("own", "sum"), max_seen_any=("max_seen_any", "sum"),
                                          home_bgs=("home_bg", "size"), phantom_bgs=("phantom", "sum"),
                                          home_bgs_no_own_key=("own_key", lambda x: int((x == 0).sum())))
trim = bg[bg.phantom == 0].groupby(["county", "month"]).agg(seen_at_home_trimmed=("own", "sum"),
                                                             population_trimmed=("acs_population", "sum"))
cal = cal.join(trim).reset_index()
cal = cal[cal.county.isin(pop.index)].copy()
cal["population"] = cal.county.map(pop)
cal["factor"] = cal.seen_at_home / cal.population
cal["units_per_resident"] = cal.month.map(s)
cal["factor_statewide"] = cal.units_per_resident
cal[["seen_at_home_trimmed", "population_trimmed"]] = cal[["seen_at_home_trimmed", "population_trimmed"]].fillna(0.0)
ok = cal.population_trimmed > 0
cal["factor_trimmed"] = np.where(ok, cal.seen_at_home_trimmed / cal.population_trimmed.where(ok, 1.0), cal.factor_statewide)
cal = cal[["county", "month", "seen_at_home", "population", "factor", "max_seen_any", "units_per_resident", "factor_statewide",
           "seen_at_home_trimmed", "population_trimmed", "factor_trimmed", "home_bgs", "phantom_bgs", "home_bgs_no_own_key"]]
cal.to_csv(A / "calibration_county_month.csv", index=False)

print("units per resident, statewide (factor_statewide):", s.round(3).to_dict())
for c in ("factor", "factor_trimmed"):
    print(f"{c} across counties and months: median {cal[c].median():.2f}, middle 80% {cal[c].quantile(.1):.2f}-"
          f"{cal[c].quantile(.9):.2f}, range {cal[c].min():.2f}-{cal[c].max():.2f}")
print(f"phantom home block group-months (own > {PHANTOM:g} x expected): {bg.phantom.sum()} of {len(bg)} "
      f"({bg.phantom.mean():.1%}), holding {bg.own[bg.phantom == 1].sum() / bg.own.sum():.1%} of devices seen at home")
print(cal[cal.county.isin(["29007", "29019", "29151", "29199", "29510"])].pivot(index="month", columns="county", values="factor").round(2).to_string())

# Study towns: estimated residents (mean over Jan-Jul, the travel-pattern months) under each calibration, against the
# ACS population of the same block groups (flows/reach/*/homes.csv, written by flows/build_homes.py)
towns = {"Columbia": "", "Mexico": "", "Linn": "", "Lancaster": "kirksville/", "Webb City": "joplin/"}
jj = bg[bg.month <= "2026-07"].merge(cal[["county", "month", "factor", "factor_trimmed", "factor_statewide"]], on=["county", "month"])
print("\n| Town | Block groups | Seen at home / factor (2026-10-16) | / factor_trimmed | / factor_statewide | ACS population of the block groups |")
print("|---|---:|---:|---:|---:|---:|")
for town, sub in towns.items():
    p = root / f"flows/reach/{sub}homes.csv"
    if not p.exists():
        continue
    hs = set(pd.read_csv(p, dtype={"home_cbg": str}).query("town == @town").home_cbg)
    x = jj[jj.home_bg.isin(hs)]
    est = {k: (x.own / x[k]).groupby(x.month).sum().mean() for k in ("factor", "factor_trimmed", "factor_statewide")}
    acs = pop_bg[(pop_bg.vintage == 2020) & pop_bg.bg.isin(hs)].population.sum()
    print(f"| {town} | {len(hs)} | {est['factor']:,.0f} | {est['factor_trimmed']:,.0f} | {est['factor_statewide']:,.0f} | {acs:,.0f} |")
