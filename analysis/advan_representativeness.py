"""Limitation test: does Advan's coverage of residents vary with age, income and rurality? Missouri home block groups,
January-July 2026 (2020 block groups, which carry the ACS tables). -> advan_representativeness.csv (block-group table)

Outcomes per home block group (home_bg_month_mo_2026.csv, mean over months of the ratio):
  detection ratio     d_h = own_h / E_h: residents seen at home / expected units (ACS population x the statewide units per
                      resident that month; 1 = the statewide rate)
  device rate         max_seen_any_h / E_h: the block group's residents in the busiest single block group they are seen
                      in (at least this many distinct devices live there) / expected units
Covariates (ACS 2020-2024 5-year, block groups, census_dl/acs_tract/): share aged 65+ (B01001), median household
income (B19013; log2) or share below the poverty line (C17002), log2 population density (B01003 / land area of the
cb_2020 block group), nonmetro county (USDA RUCC 2023 codes 4-9). Weighted least squares of log2 ratio, ACS-population
weights, intervals clustered by county (St. Louis city and county one cluster). A coefficient is the change in log2
of the ratio: x 2^coef on the ratio. Block groups with no ACS population, no residents seen at home, or no median
income are left out of the model that needs them.
Target counties (Audrain, Boone, Osage): population-weighted mean ratios by statewide tercile of age 65+ share and of
median household income.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import shapefile
import statsmodels.formula.api as smf

root = Path(__file__).resolve().parents[1]
A = root / "analysis"
T = root / "census_dl/acs_tract"
unit = lambda c: "29189" if c == "29510" else c
HOME = {"29007": "Audrain", "29019": "Boone", "29151": "Osage"}


def table(name, cols):
    """Missouri block-group rows of a national ACS table-based summary file -> DataFrame of the named estimate columns."""
    rows = []
    with open(T / f"{name}.dat") as fh:
        head = fh.readline().strip().split("|")
        idx = [head.index(c) for c in cols]
        for line in fh:
            if line.startswith("1500000US29"):
                x = line.strip().split("|")
                rows.append([x[0][9:]] + [float(x[i]) for i in idx])
    return pd.DataFrame(rows, columns=["bg"] + cols).set_index("bg")


age = table("b01001", ["B01001_E001"] + [f"B01001_E{k:03d}" for k in list(range(20, 26)) + list(range(44, 50))])
pov = table("c17002", ["C17002_E001", "C17002_E002", "C17002_E003"])
inc = table("b19013", ["B19013_E001"])
pop = table("b01003", ["B01003_E001"])
acs = pd.DataFrame({"pop": pop.B01003_E001,
                    "share65": age.iloc[:, 1:].sum(axis=1) / age.B01001_E001.where(age.B01001_E001 > 0),
                    "poverty": (pov.C17002_E002 + pov.C17002_E003) / pov.C17002_E001.where(pov.C17002_E001 > 0),
                    "income": inc.B19013_E001.where(inc.B19013_E001 > 0)})
land = {r.as_dict()["GEOID"]: r.as_dict()["ALAND"] / 2.59e6 for r in shapefile.Reader(str(root / "census_dl/bg/cb_2020_29_bg_500k")).iterRecords()}
acs["density"] = acs["pop"] / pd.Series(land).reindex(acs.index).where(lambda x: x > 0)
rucc = pd.read_csv(root / "census_dl/ref/rucc2023.csv", dtype={"FIPS": str}, encoding="latin-1")
rucc = rucc[rucc.Attribute == "RUCC_2023"].set_index("FIPS").Value.astype(int)

hb = pd.read_csv(A / "home_bg_month_mo_2026.csv", dtype={"home_bg": str, "county": str})
hb = hb[(hb.month <= "2026-07") & (hb.expected_units > 0)]
hb = hb.assign(d=hb.own / hb.expected_units, dev=hb.max_seen_any / hb.expected_units)
g = hb.groupby("home_bg")[["d", "dev"]].mean()
x = g.join(acs, how="inner")
x["county"] = x.index.str[:5]
x["cu"] = x.county.map(unit)
x["nonmetro"] = (x.county.map(rucc) >= 4).astype(int)
x = x[(x["pop"] > 0) & (x.d > 0) & x.density.notna()]
x["log_d"], x["log_dev"] = np.log2(x.d), np.log2(x.dev)
x["share65_10"] = 10 * x.share65                  # per 10 points of the population aged 65+
x["poverty_10"] = 10 * x.poverty
x["log_income"], x["log_density"] = np.log2(x.income), np.log2(x.density)
x.to_csv(A / "advan_representativeness.csv")

rows = []
for y, lab in (("log_d", "detection ratio (seen at home)"), ("log_dev", "device rate (busiest block group)")):
    for form in ("share65_10 + log_income + log_density + nonmetro", "share65_10 + poverty_10 + log_density + nonmetro"):
        dd = x.dropna(subset=form.replace(" ", "").split("+"))
        m = smf.wls(f"{y} ~ {form}", dd, weights=dd["pop"]).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(dd.cu)[0]})
        ci = m.conf_int()
        for k in m.params.index[1:]:
            rows.append((lab, form.split(" + ")[1], k, m.params[k], ci.loc[k, 0], ci.loc[k, 1], m.pvalues[k], int(m.nobs),
                         dd.cu.nunique(), m.rsquared))
r = pd.DataFrame(rows, columns=["outcome", "income_term", "term", "coef", "lo", "hi", "p", "n", "clusters", "r2"])
LAB = {"share65_10": "+10 points aged 65+", "log_income": "x2 median household income", "poverty_10": "+10 points below poverty",
       "log_density": "x2 population density", "nonmetro": "nonmetro county (RUCC 4-9)"}
print(f"{x.shape[0]:,} home block groups, {x.cu.nunique()} county clusters; log2 ratio, ACS-population weighted\n")
print("| Outcome | Model | Term | Coefficient (log2) | 95% interval | x on the ratio | p |\n|---|---|---|---:|---|---:|---:|")
for t in r.itertuples():
    print(f"| {t.outcome} | with {'income' if t.income_term == 'log_income' else 'poverty'} | {LAB[t.term]} | {t.coef:+.3f} | "
          f"[{t.lo:+.3f}, {t.hi:+.3f}] | {2 ** t.coef:.2f} | {t.p:.3f} |")
print("R2:", r.groupby(["outcome", "income_term"]).r2.first().round(3).to_dict())
# pairwise correlations (population-weighted Spearman not used; plain Spearman across block groups)
print("Spearman with log2 detection ratio:", {k: round(x.log_d.corr(x[k], method="spearman"), 2) for k in ("share65", "income", "poverty", "density")})
print("Spearman with log2 device rate:", {k: round(x.log_dev.corr(x[k], method="spearman"), 2) for k in ("share65", "income", "poverty", "density")})

w = lambda s: s.quantile([1 / 3, 2 / 3]).values
q65, qinc = w(x.share65), w(x.income.dropna())
x["t65"] = pd.cut(x.share65, [-1, *q65, 2], labels=["low", "middle", "high"])
x["tinc"] = pd.cut(x.income, [-1, *qinc, 1e9], labels=["low", "middle", "high"])
print(f"\nstatewide terciles (block groups): aged 65+ {q65[0]:.1%} / {q65[1]:.1%}; median household income ${qinc[0]:,.0f} / ${qinc[1]:,.0f}")
print("| County | Tercile of | Low | Middle | High |\n|---|---|---|---|---|")
for c, n in HOME.items():
    s = x[x.county == c]
    for col, lab in (("t65", "aged 65+"), ("tinc", "median income")):
        cell = []
        for k in ("low", "middle", "high"):
            u = s[s[col] == k]
            cell.append("-" if u.empty else f"{np.average(u.d, weights=u['pop']):.2f} / {np.average(u.dev, weights=u['pop']):.2f} ({len(u)})")
        print(f"| {n} | {lab} | {' | '.join(cell)} |")
print("(cells: detection ratio / device rate, population-weighted mean over the county's block groups in the tercile "
      "(block groups); 1.00 = the statewide rate)")
