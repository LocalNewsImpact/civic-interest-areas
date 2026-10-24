"""Kansas counties assigned to the Missouri county classes: nearest Missouri class centre (k = 4) on the same two
measures, standardised with Missouri's mean and spread -- log population, ACS 2020-2024 5-year total population in
both states (Missouri: crossover_compare.csv, datadesk census_value; Kansas: table B01003, census_dl/acs_tract/b01003.dat,
the Census table-based summary file -- the same figures, e.g. Boone 188,043 in both) and commuting outflow (employed residents working in another county of the state /
employed residents; LODES 2023 main file of each state). Output analysis/county_class_k4_20.csv."""
import csv
import gzip
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
A = root / "analysis"
cc = pd.read_csv(A / "crossover_compare.csv", dtype={"Unnamed: 0": str}).rename(columns={"Unnamed: 0": "fips"}).set_index("fips")
mo = pd.DataFrame({"log_pop": np.log(cc.population), "out": cc.commute_emp}).dropna()
k4 = pd.read_csv(A / "county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
mo = mo[mo.index.isin(k4.index)]
mu, sd = mo.mean(), mo.std()
Z = (mo - mu) / sd
centre = Z.groupby(k4.reindex(Z.index)).mean()
work, out = defaultdict(float), defaultdict(float)
with gzip.open(root / "free/ks/ks_od_main_JT00_2023.csv.gz", "rt") as fh:
    for r in csv.DictReader(fh):
        h, w, n = r["h_geocode"][:5], r["w_geocode"][:5], float(r["S000"])
        work[h] += n
        if w != h:
            out[h] += n
co = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
co = co[co.STATEFP == "20"]
acs = pd.read_csv(root / "census_dl/acs_tract/b01003.dat", sep="|", dtype=str)
acs = acs[acs.GEO_ID.str.startswith("0500000US20")]
acs = pd.Series(acs.B01003_E001.astype(float).values, index=acs.GEO_ID.str[-5:])
ks = pd.DataFrame({"log_pop": np.log(acs.reindex(co.STATEFP + co.COUNTYFP).values),
                   "out": [out[f] / work[f] for f in co.STATEFP + co.COUNTYFP]}, index=co.STATEFP + co.COUNTYFP)
d = (((ks - mu) / sd).values[:, None, :] - centre.values[None, :, :]) ** 2
ks["class"] = centre.index[d.sum(2).argmin(1)]
names = dict(zip(co.STATEFP + co.COUNTYFP, co.COUNAME))
old = pd.read_csv(A / "county_class_k4_20.csv", dtype={"fips": str}).set_index("fips")["class"] if (A / "county_class_k4_20.csv").exists() else None
if old is not None:
    moved = ks.index[old.reindex(ks.index).values != ks["class"].values]
    print("moved from the previous file:", [f"{f} {old.get(f)} -> {ks.loc[f, 'class']}" for f in moved])
print(ks["class"].value_counts().sort_index().to_dict())
ks.rename_axis("fips")[["class"]].to_csv(A / "county_class_k4_20.csv")
for c in sorted(ks["class"].unique()):
    print(c, ", ".join(names[f] for f in ks.index[ks["class"] == c][:14]))
