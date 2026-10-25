"""Missouri counties with near-complete, high-quality collection from all known newsrooms, March 2026.

Known newsrooms: the pinned outlet registry (excluded_outlets.registry(); HOME_COUNTY applied), status active, not
EXCLUDE or CAMPUS (spillover_common.NOT_LOCAL: statewide and student outlets are not a county's local news). Per county:
  coverage        active newsrooms collected in March / all active newsrooms
  local_news      local news stories (enriched or enrichment_skipped) from them
  text_ok         stories with text (local news / (local news + text unavailable))
  full_length     local news stories of 600+ characters
  placed          local news stories placed on the map (statewide_2026_03_articles.json)
  paywall         any collected newsroom flagged has_paywall or requires_login
TV market: pinned county_dma.csv (excluded_outlets.county_dma()). Audrain, Boone and Osage excluded.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spillover_common import NOT_LOCAL, county_dma, registry  # noqa: E402

root = Path(__file__).resolve().parents[1]
reg = registry(keep_default_na=False)
reg = reg[(reg.status == "active") & (reg.county_fips.str.startswith("29")) & ~reg.outlet.isin(NOT_LOCAL)]
q = pd.read_csv(root / "coverage/source_quality_2026_03.csv", dtype={"source_id": str})
for c in ("has_paywall", "requires_login"):
    q[c] = q[c].astype(str).str.lower().isin(["t", "true"])
arts = json.load(open(root / "coverage/storymap/statewide_2026_03_articles.json"))["articles"]
placed = pd.DataFrame(arts).assign(placed=lambda x: x.counties.map(bool)).groupby("source").placed.agg(["sum", "size"])
m = reg.merge(q, on="source_id", how="left", suffixes=("", "_q"))
m["collected"] = m.collected_in_march.eq("yes") & m.local_news.fillna(0).gt(0)
m["placed_n"] = m.source_id.map(placed["sum"]).fillna(0)
dma = county_dma(dtype=str).set_index("county_geoid").dma_name
rows = []
for f, g in m.groupby("county_fips"):
    c = g[g.collected]
    ln = c.local_news.sum()
    rows.append({"fips": f, "county": g.county.iloc[0], "dma": dma.get(f, ""), "known": len(g), "collected": len(c),
                 "coverage": len(c) / len(g), "local_news": int(ln),
                 "text_ok": ln / (ln + c.text_unavailable.sum()) if ln else 0,
                 "full_length": 1 - c.short_texts.sum() / ln if ln else 0,
                 "placed": c.placed_n.sum() / ln if ln else 0,
                 "paywall": bool((c.has_paywall | c.requires_login).any()),
                 "missing": "; ".join(g[~g.collected].outlet)})
t = pd.DataFrame(rows)
t = t[~t.fips.isin(["29007", "29019", "29151"])]
good = t[(t.coverage == 1) & (t.text_ok >= .95) & (t.full_length >= .8) & (t.placed >= .6) & ~t.paywall]
print(f"{len(t)} counties with known newsrooms; {len(good)} meet every test "
      "(all known newsrooms collected, 95%+ with text, 80%+ full length, 60%+ placed, no paywall)\n")
t.to_csv(root / "analysis/county_collection_quality.csv", index=False)
