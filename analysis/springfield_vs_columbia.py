"""Springfield group (Greene, Webster, Barry) against the Boone group (Boone, Audrain, Osage) and Missouri.

Crossover: distinct residents seen outside the county in a month, lower bound (crossover_compare.csv), Jan-Sep 2026.
Spillover: share of stories about another county (spillover_outlets.csv), March 2026, all outlets and print/digital;
"good" = outlets with 95%+ text, 80%+ full length, 60%+ placed. Urban share: Census 2020. Population: ACS 2020-2024.
Missouri: median across the 114 county units (crossover) and the 68 counties with newsrooms in the model (spillover).
Top destination: largest share of residents' summed visits outside the county (od_predicted.csv).
"""
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
GROUPS = {"Boone group": {"29019": "Boone", "29007": "Audrain", "29151": "Osage"},
          "Springfield group": {"29077": "Greene", "29225": "Webster", "29009": "Barry"}}
cc = pd.read_csv(root / "analysis/crossover_compare.csv", dtype={"Unnamed: 0": str}).rename(columns={"Unnamed: 0": "fips"}).set_index("fips")
so = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
q = pd.read_csv(root / "coverage/source_quality_2026_03.csv")
q = q.groupby("canonical_name").agg(ln=("local_news", "max"), tu=("text_unavailable", "max"), sh=("short_texts", "max"))
so = so.join(q, on="outlet")
so["good"] = (so.ln / (so.ln + so.tu) >= .95) & (1 - so.sh / so.ln >= .8) & (so.placed / so.ln >= .6)
ua = pd.read_excel(root / "census_dl/urban/2020_UA_COUNTY.xlsx", dtype=str)
ua = ua[ua.STATE == "29"].assign(f=lambda x: "29" + x.COUNTY)
urban = (ua.POP_URB.astype(float) / ua.POP_COU.astype(float)).groupby(ua.f).first()
tp = pd.read_csv(root / "analysis/od_predicted.csv", dtype={"i": str, "j": str})
names = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str}).set_index("fips").name


def spill(d):
    return d.spill.sum() / d.placed.sum() if len(d) else np.nan


def row(f, name):
    o = so[so.fips == f]
    t = tp[tp.i == f].sort_values("visits_share", ascending=False).iloc[0]
    return {"county": name, "population": int(cc.population[f]), "urban": urban[f], "newsrooms": len(o),
            "broadcasters": int(o.broadcast.sum()), "crossover": cc.dedup_lower[f], "commuting": cc.commute_pop[f],
            "spill_all": spill(o), "spill_print": spill(o[o.broadcast == 0]),
            "spill_print_good": spill(o[(o.broadcast == 0) & o.good]),
            "top_destination": f"{names[t.j]} {t.visits_share:.0%}"}


rows = [row(f, n) for g in GROUPS.values() for f, n in g.items()]
cnt = so.groupby("fips").apply(lambda d: pd.Series({"all": spill(d), "print": spill(d[d.broadcast == 0]),
                                                    "good": spill(d[(d.broadcast == 0) & d.good])}))
rows.append({"county": "Missouri median", "population": int(cc.population.median()), "urban": urban.median(),
             "newsrooms": so.groupby("fips").size().median(), "broadcasters": np.nan,
             "crossover": cc.dedup_lower.median(), "commuting": cc.commute_pop.median(),
             "spill_all": cnt["all"].median(), "spill_print": cnt["print"].median(), "spill_print_good": cnt["good"].median(),
             "top_destination": ""})
t = pd.DataFrame(rows)
pct = lambda v: "—" if pd.isna(v) else f"{v:.0%}"
print("| County | Population | Urban | Newsrooms (broadcast) | Crossover (people) | Commuting out | Spillover, all | "
      "Spillover, print | Spillover, print, well collected | Top destination |")
print("|---|---:|---:|---|---:|---:|---:|---:|---:|---|")
for r in t.itertuples():
    nr = f"{r.newsrooms:.0f}" + ("" if pd.isna(r.broadcasters) else f" ({r.broadcasters})")
    print(f"| {r.county} | {r.population:,} | {pct(r.urban)} | {nr} | {pct(r.crossover)} | {pct(r.commuting)} | "
          f"{pct(r.spill_all)} | {pct(r.spill_print)} | {pct(r.spill_print_good)} | {r.top_destination} |")
t.to_csv(root / "analysis/springfield_vs_columbia.csv", index=False)
