"""Kansas home tract x destination block group x month, January-July 2026 (2020 block groups) -- the Kansas counterpart
of the table activity_space.py builds for Missouri. Advan Neighborhood Patterns Plus: Kansas destinations from
neighborhood/raw_ks/*.parquet, Missouri destinations (Kansans' visits) from neighborhood/raw/*.csv.gz.
Output analysis/od_tract_bg_ks_2026_janjul.parquet: tract, bg, v, month."""
import csv
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

csv.field_size_limit(sys.maxsize)
root = Path(__file__).resolve().parents[1]
parts = []
for m in range(1, 8):
    month = f"2026-0{m}"
    rows = defaultdict(float)
    for f in glob.glob(str(root / f"neighborhood/raw_ks/{month}-01*.parquet")):
        for r in pq.read_table(f, columns=["AREA", "DEVICE_HOME_AREAS"]).to_pylist():
            for h, v in json.loads(r["DEVICE_HOME_AREAS"] or "{}").items():
                if h.startswith("20"):
                    rows[h[:11], r["AREA"]] += v
    for f in glob.glob(str(root / f"neighborhood/raw/{month}-01*.csv.gz")):
        for chunk in pd.read_csv(f, usecols=["AREA", "DEVICE_HOME_AREAS"], dtype=str, chunksize=500):
            for area, homes in zip(chunk.AREA, chunk.DEVICE_HOME_AREAS):
                if '"20' in (homes or ""):
                    for h, v in json.loads(homes).items():
                        if h.startswith("20"):
                            rows[h[:11], area] += v
    d = pd.DataFrame([(t, b, v) for (t, b), v in rows.items()], columns=["tract", "bg", "v"]); d["month"] = month
    parts.append(d); print(month, len(d), flush=True)
pq.write_table(pa.Table.from_pandas(pd.concat(parts)), root / "analysis/od_tract_bg_ks_2026_janjul.parquet")
