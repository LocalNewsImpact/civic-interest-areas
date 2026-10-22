"""Census 2010 cartographic tract shapefile -> GeoJSON, with the 11-digit GEOID the flow data uses.

Reads the .dbf and .shp directly (polygon records only); no GIS library is installed here.
Shapefile outer rings are clockwise, which is the winding d3-geo expects, so rings are kept as read.
"""

import json
import struct
import sys

base, out = sys.argv[1], sys.argv[2]

# --- .dbf: dBase III table --------------------------------------------------------------
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
    records = []
    for _ in range(n_rec):
        raw = fh.read(rec_len)[1:]                       # first byte is the deletion flag
        rec, pos = {}, 0
        for name, size in fields:
            rec[name] = raw[pos:pos + size].decode("latin-1").strip()
            pos += size
        records.append(rec)

# --- .shp: polygon records ----------------------------------------------------------------
features = []
with open(base + ".shp", "rb") as fh:
    fh.seek(100)
    i = 0
    while True:
        h = fh.read(8)
        if len(h) < 8:
            break
        _, length = struct.unpack(">II", h)
        body = fh.read(length * 2)
        stype = struct.unpack("<i", body[:4])[0]
        rec = records[i]
        i += 1
        if stype != 5:
            continue
        n_parts, n_pts = struct.unpack("<ii", body[36:44])
        parts = list(struct.unpack(f"<{n_parts}i", body[44:44 + 4 * n_parts]))
        p0 = 44 + 4 * n_parts
        pts = [struct.unpack("<dd", body[p0 + 16 * k:p0 + 16 * k + 16]) for k in range(n_pts)]
        rings = [[[round(x, 5), round(y, 5)] for x, y in pts[a:b]]
                 for a, b in zip(parts, parts[1:] + [n_pts])]
        geoid = rec["STATE"] + rec["COUNTY"] + rec["TRACT"]
        features.append({"type": "Feature", "id": geoid,
                         "properties": {"GEOID": geoid, "NAME": rec.get("NAME", "")},
                         "geometry": {"type": "Polygon", "coordinates": rings}})

# a tract split into several rings arrives as several records with the same GEOID: merge them
merged = {}
for f in features:
    g = merged.setdefault(f["id"], {"type": "Feature", "id": f["id"], "properties": f["properties"],
                                    "geometry": {"type": "MultiPolygon", "coordinates": []}})
    g["geometry"]["coordinates"].append(f["geometry"]["coordinates"])
json.dump({"type": "FeatureCollection", "features": list(merged.values())}, open(out, "w"),
          separators=(",", ":"))
print(f"{len(records)} dbf records, {len(features)} polygons, {len(merged)} tracts -> {out}")
