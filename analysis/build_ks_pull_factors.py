"""Kansas county trade pull factors, FY2025 (July 2024 - June 2025): Kansas Department of Revenue, Office of Policy and
Research, County Trade Pull Factor report (census_dl/ks_dor/pullfactorfy25.pdf, text by pdftotext -layout).
Columns: population, state sales tax collections, per-capita sales tax, pull factor (CTPF), trade area capture
(customers), market share. Sales tax at one state rate is proportional to taxable sales, so the pull factor and trade
area capture are those of taxable sales. Output analysis/ks_pull_factors_fy25.csv with 2020 county FIPS."""
import re
from pathlib import Path

import pandas as pd

root = Path(__file__).resolve().parents[1]
txt = (root / "census_dl/ks_dor/pullfactorfy25.txt").read_text()
row = re.compile(r"^([A-Z][A-Za-z .]+?)\s+([\d,]+)\s+\$\s+([\d,]+)\s+\$\s+([\d,.]+)\s+([\d.]+)\s+([\d,]+)\s+([\d.]+)%")
rows = [m.groups() for m in map(row.match, txt.splitlines()) if m]
df = pd.DataFrame(rows, columns=["county", "population", "sales_tax", "per_capita", "pull_factor", "tac", "market_share"])
for c in df.columns[1:]:
    df[c] = df[c].str.replace(",", "").astype(float)
co = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_CO.txt", dtype=str, encoding="utf-8-sig")
co = co[co.STATEFP == "20"]
fips = {n.lower(): s + c for n, s, c in zip(co.COUNAME, co.STATEFP, co.COUNTYFP)}
df["fips"] = df.county.str.strip().str.lower().map(fips)
df = df[df.county.str.lower() != "statewide"].drop_duplicates("fips")          # the report prints the table twice
print(len(df), "counties;", df.fips.isna().sum(), "unmatched:", df.county[df.fips.isna()].tolist())
df.to_csv(root / "analysis/ks_pull_factors_fy25.csv", index=False)
print(df.sort_values("tac", ascending=False).head(8)[["county", "population", "pull_factor", "tac"]].to_string(index=False))
