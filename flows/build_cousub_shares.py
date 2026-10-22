"""Tract maps -> county-subdivision maps. Builds, from Census 2020 cartographic files (../census_dl):

- cousub_29.geojson: Missouri county subdivisions (townships), plus `counties` and `dma` outlines dissolved from them,
  so every line on the map comes from one boundary set. Rings are wound clockwise, as d3-geo expects.
- bg_to_cousub.csv: each 2020 block group's share of land area in each subdivision (Missouri's block assignment
  files carry no subdivision, so the assignment is by area overlap; a block group's counts are split by it).
- cousub_shares_advan_<month>[_col].json: the tract map's measure on subdivisions -- the county's devices recorded
  in the subdivision over all its devices recorded in Missouri outside the county, in percent.
"""

import csv
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely.strtree import STRtree

here = Path(__file__).parent
DL = here.parent / "census_dl"
DMA = ["29007", "29019", "29027", "29041", "29051", "29053", "29089", "29125", "29131", "29135", "29139", "29141",
       "29151", "29175"]


def read_shp(base, key):
    """Polygon records of a shapefile -> {key(record): shapely geometry}. No GIS reader is installed."""
    with open(base + ".dbf", "rb") as fh:
        head = fh.read(32)
        n_rec, head_len, rec_len = struct.unpack("<IHH", head[4:12])
        fields = []
        while True:
            d = fh.read(32)
            if d[0] == 0x0D:
                break
            fields.append((d[:11].split(b"\0")[0].decode(), d[16]))
        fh.seek(head_len)
        recs = []
        for _ in range(n_rec):
            raw = fh.read(rec_len)[1:]
            rec, pos = {}, 0
            for name, size in fields:
                rec[name] = raw[pos:pos + size].decode("latin-1").strip()
                pos += size
            recs.append(rec)
    out = {}
    with open(base + ".shp", "rb") as fh:
        fh.seek(100)
        i = 0
        while True:
            h = fh.read(8)
            if len(h) < 8:
                break
            _, length = struct.unpack(">II", h)
            body = fh.read(length * 2)
            rec = recs[i]
            i += 1
            if struct.unpack("<i", body[:4])[0] != 5:
                continue
            n_parts, n_pts = struct.unpack("<ii", body[36:44])
            parts = list(struct.unpack(f"<{n_parts}i", body[44:44 + 4 * n_parts]))
            p0 = 44 + 4 * n_parts
            pts = [struct.unpack("<dd", body[p0 + 16 * k:p0 + 16 * k + 16]) for k in range(n_pts)]
            rings = [pts[a:b] for a, b in zip(parts, parts[1:] + [n_pts])]
            # shapefile: outer rings clockwise, holes counter-clockwise
            polys = []
            for ring in rings:
                if Polygon(ring).exterior.is_ccw:
                    if polys:
                        polys[-1][1].append(ring)
                else:
                    polys.append((ring, []))
            geom = MultiPolygon([Polygon(o, hs) for o, hs in polys]).buffer(0)
            out[key(rec)] = (rec, geom)
    return out


def cw(geom):
    """GeoJSON geometry with exterior rings clockwise, the winding d3-geo reads as 'inside'."""
    polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    return mapping(MultiPolygon([orient(p, sign=-1.0) for p in polys if p.area > 0]))


if "--geo" in sys.argv or not (here / "bg_to_cousub.csv").exists():
    cous = read_shp(str(DL / "cousub/cb_2020_29_cousub_500k"), lambda r: r["GEOID"])
    bgs = read_shp(str(DL / "bg/cb_2020_29_bg_500k"), lambda r: r["GEOID"])
    feats = [{"type": "Feature", "id": g, "properties": {"name": rec["NAME"], "county": g[:5]}, "geometry": cw(geom)}
             for g, (rec, geom) in cous.items()]
    by_county = defaultdict(list)
    for g, (_, geom) in cous.items():
        by_county[g[:5]].append(geom)
    counties = {c: unary_union(gs).buffer(1e-5).buffer(-1e-5) for c, gs in by_county.items()}
    cfeats = [{"type": "Feature", "id": c, "properties": {}, "geometry": cw(g)} for c, g in counties.items()]
    dma = unary_union([counties[c] for c in DMA]).buffer(1e-5).buffer(-1e-5)
    json.dump({"cousub": {"type": "FeatureCollection", "features": feats},
               "counties": {"type": "FeatureCollection", "features": cfeats},
               "dma": {"type": "Feature", "properties": {}, "geometry": cw(dma)}},
              open(here / "cousub_29.geojson", "w"), separators=(",", ":"))
    ids = list(cous)
    tree = STRtree([cous[i][1] for i in ids])
    split = 0
    with open(here / "bg_to_cousub.csv", "w", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(["bg", "cousub", "share"])
        for bg, (_, geom) in bgs.items():
            parts = {}
            for k in tree.query(geom):
                c = ids[k]
                if c[:5] != bg[:5]:
                    continue
                a = geom.intersection(cous[c][1]).area
                if a > 0:
                    parts[c] = a
            tot = sum(parts.values())
            kept = {c: a / tot for c, a in parts.items() if a / tot >= 0.02}   # edge slivers of the 1:500k files
            norm = sum(kept.values())
            split += len(kept) > 1
            for c, a in kept.items():
                w.writerow([bg, c, round(a / norm, 4)])
    print(f"{len(feats)} subdivisions, {len(cfeats)} counties; {len(bgs)} block groups, {split} split across subdivisions")

def crosswalk(bgs, path):
    """Each block group's share of land area in each subdivision (same county), slivers under 2% dropped."""
    ids = list(cous_geo)
    tree = STRtree([cous_geo[i] for i in ids])
    with open(path, "w", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(["bg", "cousub", "share"])
        for bg, (_, geom) in bgs.items():
            parts = {ids[k]: geom.intersection(cous_geo[ids[k]]).area for k in tree.query(geom) if ids[k][:5] == bg[:5]}
            parts = {c: a for c, a in parts.items() if a > 0}
            tot = sum(parts.values()) or 1
            kept = {c: a / tot for c, a in parts.items() if a / tot >= 0.02}
            norm = sum(kept.values()) or 1
            for c, a in kept.items():
                w.writerow([bg, c, round(a / norm, 4)])


cous_geo = {g: geom for g, (_, geom) in read_shp(str(DL / "cousub/cb_2020_29_cousub_500k"), lambda r: r["GEOID"]).items()}
# Advan reports Jan-Jul 2026 on 2020 block groups and Aug-Sep on 2010 block groups (4,506 in Missouri): one lookup each
if not (here / "bg2010_to_cousub.csv").exists():
    crosswalk(read_shp(str(DL / "bg2010/gz_2010_29_150_00_500k"),
                       lambda r: r["STATE"] + r["COUNTY"] + r["TRACT"] + r["BLKGRP"]), here / "bg2010_to_cousub.csv")
XW = {}
for vintage, f in ((2020, "bg_to_cousub.csv"), (2010, "bg2010_to_cousub.csv")):
    XW[vintage] = defaultdict(list)
    for r in csv.DictReader(open(here / f)):
        XW[vintage][r["bg"]].append((r["cousub"], float(r["share"])))

# which months: one ("2026-03") or the nine of Jan-Sep 2026 ("jan-sep"); the nine are pass-through discounted by
# county pair, as the travel model is (analysis/travel_model.py: od_predicted.csv stop_discount)
arg = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "2026-03"
months = [f"2026-{m:02d}" for m in range(1, 10)] if arg == "jan-sep" else [arg]
discount = defaultdict(float)
# population calibration by home county and month (analysis/build_calibration.py): counts divided by that month's factor
cal = {(r["county"], r["month"]): float(r["factor"]) for r in csv.DictReader(open(here.parent / "analysis/calibration_county_month.csv"))}
if arg == "jan-sep":
    for r in csv.DictReader(open(here.parent / "analysis/od_predicted.csv")):
        discount[(r["i"], r["j"])] = float(r["stop_discount"])
for col in ("device_home_areas", "work_hours_device_home_areas"):
    counts = defaultdict(lambda: defaultdict(float))
    missing = 0
    for r in csv.DictReader(open(here.parent / "neighborhood/flows_audrain_boone_osage_2026.csv")):
        if r["month"] not in months or r["dest_county"] == r["home_county"]:
            continue
        xw = XW[2010 if r["month"] >= "2026-08" else 2020]
        if r["dest_cbg"] not in xw:
            missing += 1
            continue
        keep = (1 - discount[(r["home_county"], r["dest_county"])]) / cal[(r["home_county"], r["month"])]
        for c, s in xw[r["dest_cbg"]]:
            counts[r["home_county_name"]][c] += int(r[col]) * s * keep
    out = {}
    for county, units in counts.items():
        total = sum(units.values())
        out[county] = {c: round(100 * v / total, 3) for c, v in units.items() if v}
        vals = sorted(out[county].values())
        print(f"{col[:10]:10} {county:8} {len(vals):4} subdivisions  max {vals[-1]:.2f}%")
    print("rows with no block group in the lookup:", missing)
    suffix = arg.replace("-", "_") + ("" if col == "device_home_areas" else "_work_hours")
    json.dump(out, open(here / f"cousub_shares_advan_{suffix}.json", "w"))
