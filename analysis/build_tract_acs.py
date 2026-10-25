"""Tract household income, education and tenure for the public travel model. ACS 2020-2024 5-year, table-based summary
file (census_dl/acs_tract/acsdt5y2024-*.dat, no API key), Missouri 2020 tracts.
  med_income   B19013 median household income
  inc_lt50, inc_50_100, inc_ge100   B19001 household income shares: under $50,000 (bins 2-10), $50,000-99,999 (11-13),
               $100,000 and over (14-17) -- the National Household Travel Survey HHFAMINC groups 1-5, 6-7, 8-11
  ba_plus      B15003 share of adults 25+ with a bachelor's degree or higher (22-25) -- survey EDUC 4-5
  renter       B25003 share of occupied housing units renter-occupied (3) -- survey HOMEOWN 2
  wfh          B08006 share of workers 16+ who worked from home (17)
Output analysis/tract_acs_2024.csv."""
from pathlib import Path

import pandas as pd

root = Path(__file__).resolve().parents[1]
D = root / "census_dl/acs_tract"
ST = "29"                                          # Missouri


def read(t):
    x = pd.read_csv(D / f"{t}.dat", sep="|", dtype=str)
    x = x[x.GEO_ID.str.startswith("1400000US" + ST)].copy()
    x["tract"] = x.GEO_ID.str[-11:]
    return x.set_index("tract").drop(columns="GEO_ID").apply(pd.to_numeric, errors="coerce")


a, b, e, h, m = read("b19013"), read("b19001"), read("b15003"), read("b25003"), read("b08006")
E = lambda df, t, n: df[f"{t}_E{n:03d}"]
out = pd.DataFrame(index=a.index)
out["med_income"] = E(a, "B19013", 1).where(lambda v: v > 0)          # negative = ACS suppression code
tot = E(b, "B19001", 1)
out["inc_lt50"] = sum(E(b, "B19001", n) for n in range(2, 11)) / tot
out["inc_50_100"] = sum(E(b, "B19001", n) for n in range(11, 14)) / tot
out["inc_ge100"] = sum(E(b, "B19001", n) for n in range(14, 18)) / tot
out["ba_plus"] = sum(E(e, "B15003", n) for n in range(22, 26)) / E(e, "B15003", 1)
out["renter"] = E(h, "B25003", 3) / E(h, "B25003", 1)
out["wfh"] = E(m, "B08006", 17) / E(m, "B08006", 1)
out.rename_axis("tract").reset_index().to_csv(root / "analysis/tract_acs_2024.csv", index=False)
print(out.describe().round(3).to_string())
print("missing:", out.isna().sum().to_dict())
