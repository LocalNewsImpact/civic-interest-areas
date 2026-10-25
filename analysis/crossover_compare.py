"""Crossover per Missouri county (St. Louis city and county one unit), January-September 2026 -> crossover_compare.csv

current      share of residents' summed block-group counts that are outside the county (od_mo_2026.csv, calibrated)
dedup_lower  ADOPTED (authors' decision 2026-10-24): distinct residents seen in at least one block group outside
             the county in a month / calibrated residents, averaged over months (leaving_unique_mo_2026.csv). Per home
             block group: people in its busiest outside block group (Missouri or Kansas), capped at
             D_h = E_h x (own_h / E_h)^(1 - b), E_h = ACS population x the statewide units per resident, own_h =
             residents seen at home, b = how far leaving falls with home detection (build_unique_od.py, 2SLS, about
             0.6); summed over the county's block groups and divided by the sum of D_h. b mixes phantom phones with
             residents who stay home more (both raise detection and lower leaving); the second biases b upward.
bounds       the county figure R(b) over a grid of b from 0 to 1 (step 0.01; crossover_b_grid.csv): dedup_bound_low /
             dedup_bound_high = its min / max over [0, 1], dedup_bound_width = high - low; dedup_band_low /
             dedup_band_high = its min / max over the 95% interval of b. Sums at b = 0 and b = 1, or over
             max(own_h, E_h) and min(own_h, E_h), are not bounds: R(b) need not be monotone.
sensitivity  dedup_b1 = option iii (D_h = E_h: every extra phone a phantom); dedup_b0 = own_h (every extra phone a
             resident; E_h where own_h = 0); dedup_linear = (1 - b) own_h + b E_h; all Missouri + Kansas destinations.
alternatives dedup_seen_at_home   denominator = residents seen at home (2026-10-16 measure, unit test fixed;
                                  dedup_seen_at_home_coded: as published, city <-> county counted as leaving)
             dedup_maxany         option i: denominator = the block group's residents in its busiest block group
             dedup_trimmed        option ii: seen at home, phantom home block groups (own > 3 x E_h) at E_h
             dedup_acs_mo         option iii, Missouri destinations only
commute      LODES 2023 Missouri main file, primary jobs (JT01; free/mo_od_main_JT01_2023.csv.gz): employed residents
             working in another Missouri county / population (ACS 2020-2024) and / employed residents. The JT00
             (all jobs) figures are kept as commute_pop_jt00, commute_emp_jt00; commute_pop_all, commute_emp_all count
             jobs in another county of Missouri or of KS, IL, IA, AR, OK, NE, TN, KY (free/mo_residents_od_JT01_2023.csv.gz,
             built here from the main and aux JT01 files).
conservative the higher of dedup_lower and commute_pop; set_by names which.
Destinations observed: Missouri and Kansas block groups. Illinois, Iowa, Arkansas, Oklahoma and Nebraska are not in the
data, so a resident seen only there is not counted as leaving (border counties' figures are low by that much).
"""
import csv
import gzip
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
A = root / "analysis"
unit = lambda f: "29189" if f == "29510" else f
cov = pd.read_csv(A / "county_covariates.csv", dtype={"fips": str})
cov["u"] = cov.fips.map(unit)
pop = cov.groupby("u").population.sum()
name = cov.groupby("u").name.first()
name.loc["29189"] = "St. Louis (city + county)"
od = pd.read_csv(A / "od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
assert {"visits", "visits_recorded", "visits_statewide"} <= set(od.columns), "od_mo_2026.csv not built by build_statewide_od.py"
assert (od.visits != od.visits_recorded)[od.home_county != "OUT"].mean() > 0.9, "od_mo_2026.csv visits are not calibrated"
od = od[od.home_county != "OUT"].assign(h=lambda x: x.home_county.map(unit), d=lambda x: x.dest_county.map(unit))
current = od[od.h != od.d].groupby("h").visits.sum() / od.groupby("h").visits.sum()
lv = pd.read_csv(A / "leaving_unique_mo_2026.csv", dtype={"county": str})
assert "left_lower_calibrated" in lv, "run build_unique_od.py first"
B_SLOPE = lv.detection_slope_b.iloc[0], lv.detection_slope_b_lo.iloc[0], lv.detection_slope_b_hi.iloc[0]
lv["u"] = lv.county.map(unit)
g = lv.groupby(["u", "month"]).sum(numeric_only=True)
mean = lambda num, den: (g[num] / g[den]).groupby("u").mean()
OPTS = {"dedup_seen_at_home_coded": ("left_lower_coded", "residents_seen_at_home"),
        "dedup_seen_at_home": ("left_lower", "residents_seen_at_home"),
        "dedup_maxany": ("left_lower_maxany", "max_seen_any"),
        "dedup_trimmed": ("left_lower_trimmed", "denominator_trimmed"),
        "dedup_acs_mo": ("left_lower_acs_mo", "expected_units"),
        "dedup_b1": ("left_lower_acs", "expected_units"),
        "dedup_b0": ("left_lower_b0", "denominator_b0"),
        "dedup_linear": ("left_lower_linear", "denominator_linear"),
        "dedup_lower": ("left_lower_calibrated", "denominator_calibrated")}


def lodes(path):
    emp, out = Counter(), Counter()
    with gzip.open(path, "rt") as fh:
        for r in csv.DictReader(fh):
            h, w = unit(r["h_geocode"][:5]), unit(r["w_geocode"][:5])
            n = int(r["S000"])
            emp[h] += n
            out[h] += n * (w != h)
    return pd.Series(out), pd.Series(emp)


MO_RES = root / "free/mo_residents_od_JT01_2023.csv.gz"
AUX = ("ks", "il", "ia", "ar", "ok", "ne", "tn", "ky")


def build_mo_residents():
    """Missouri residents' primary jobs anywhere observed: the Missouri main JT01 file (home and job in Missouri) plus
    the rows of the KS, IL, IA, AR, OK, NE, TN and KY aux JT01 files whose home block is in Missouri (job in that
    state). Same columns as LODES OD files. Missouri's own aux file (homes in other states) is not included."""
    import io
    n = Counter()
    with gzip.open(MO_RES, "wt", newline="") as fo:
        with gzip.open(root / "free/mo_od_main_JT01_2023.csv.gz", "rt") as fh:
            head = fh.readline()
            fo.write(head)
            for line in fh:
                fo.write(line)
                n["mo"] += 1
        for st_ in AUX:
            with gzip.open(root / f"free/{st_}_od_aux_JT01_2023.csv.gz", "rt") as fh:
                assert fh.readline() == head, st_
                for line in fh:
                    if line.split(",", 2)[1].startswith("29"):
                        fo.write(line)
                        n[st_] += 1
    print(f"wrote {MO_RES.name}: rows by job state {dict(n)}")


if not MO_RES.exists():
    build_mo_residents()
out1, emp1 = lodes(root / "free/mo_od_main_JT01_2023.csv.gz")
outa, empa = lodes(MO_RES)            # job anywhere observed (Missouri + 8 neighbouring states)
out0, emp0 = lodes(root / "free/od_2023.csv.gz")          # JT00, all jobs
cal = pd.read_csv(A / "calibration_county_month.csv", dtype={"county": str})
cal["u"] = cal.county.map(unit)
c = cal.groupby(["u", "month"])[["seen_at_home", "population"]].sum()
factor = (c.seen_at_home / c.population).groupby("u").median()
t = pd.DataFrame({"name": name, "population": pop, "current": current,
                  **{k: mean(*v) for k, v in OPTS.items()},
                  "commute_pop": out1 / pop, "commute_emp": out1 / emp1,
                  "commute_pop_all": outa / pop, "commute_emp_all": outa / empa,
                  "commute_pop_jt00": out0 / pop, "commute_emp_jt00": out0 / emp0, "factor_median": factor})
t = t[t.name.notna() & t.dedup_lower.notna()]
gr = pd.read_csv(A / "crossover_b_grid.csv", dtype={"county": str})
assert abs(gr.b_adopted.iloc[0] - B_SLOPE[0]) < 1e-6, "crossover_b_grid.csv is from another run of build_unique_od.py"
band = gr[(gr.b >= gr.b_lo) & (gr.b <= gr.b_hi)]
t["dedup_bound_low"], t["dedup_bound_high"] = gr.groupby("county").crossover.min(), gr.groupby("county").crossover.max()
t["dedup_band_low"], t["dedup_band_high"] = band.groupby("county").crossover.min(), band.groupby("county").crossover.max()
at_b = gr[np.isclose(gr.b, gr.b_adopted)].set_index("county").crossover
assert (at_b.reindex(t.index) - t.dedup_lower).abs().max() < 1e-4, "grid at the adopted b does not reproduce dedup_lower"
t["dedup_bound_width"] = t.dedup_bound_high - t.dedup_bound_low
t["conservative"] = t[["dedup_lower", "commute_pop"]].max(axis=1)
t["set_by"] = np.where(t.dedup_lower >= t.commute_pop, "phone data", "commuting")
t.index.name = None
t.to_csv(A / "crossover_compare.csv")

print("Destinations observed: Missouri and Kansas block groups; Illinois, Iowa, Arkansas, Oklahoma, Nebraska not observed.\n")
print("Crossover options: Spearman correlation across", len(t), "counties with the calibration factor (median over months) and "
      "with LODES out-commuting (JT01), and the crossover table")
LAB = {"dedup_seen_at_home_coded": "Seen at home, as published (coded county test)",
       "dedup_seen_at_home": "Seen at home, St. Louis unit fixed",
       "dedup_maxany": "(i) Busiest block group anywhere",
       "dedup_trimmed": "(ii) Seen at home, phantom block groups trimmed",
       "dedup_acs_mo": "(iii) ACS x statewide rate, Missouri destinations",
       "dedup_b1": "(iii) ACS x statewide rate, + Kansas (b = 1, sensitivity)",
       "dedup_b0": "Seen at home, + Kansas (b = 0, sensitivity)",
       "dedup_linear": f"Linear split, (1 - b) own + b E, b = {B_SLOPE[0]:.2f} (sensitivity)",
       "dedup_lower": f"Calibrated, E (own / E)^(1 - b), b = {B_SLOPE[0]:.2f} (adopted)"}
print("| Denominator | rho, factor | rho, commuters / employed | rho, commuters / population | Audrain | Boone | Osage | "
      "Missouri median | St. Louis |")
print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
for k, lab in LAB.items():
    rho = lambda col: t[k].corr(t[col], method="spearman")
    print(f"| {lab} | {rho('factor_median'):+.2f} | {rho('commute_emp'):+.2f} | {rho('commute_pop'):+.2f} | "
          f"{t.loc['29007', k]:.0%} | {t.loc['29019', k]:.0%} | {t.loc['29151', k]:.0%} | {t[k].median():.0%} | {t.loc['29189', k]:.0%} |")
print(f"| Summed block-group share (current) | {t.current.corr(t.factor_median, method='spearman'):+.2f} | "
      f"{t.current.corr(t.commute_emp, method='spearman'):+.2f} | {t.current.corr(t.commute_pop, method='spearman'):+.2f} | "
      f"{t.loc['29007', 'current']:.0%} | {t.loc['29019', 'current']:.0%} | {t.loc['29151', 'current']:.0%} | "
      f"{t.current.median():.0%} | {t.loc['29189', 'current']:.0%} |")
print(f"| LODES JT01 commuters / population | | | | {t.loc['29007', 'commute_pop']:.0%} | {t.loc['29019', 'commute_pop']:.0%} | "
      f"{t.loc['29151', 'commute_pop']:.0%} | {t.commute_pop.median():.0%} | {t.loc['29189', 'commute_pop']:.0%} |")
print(f"| LODES JT00 commuters / population | | | | {t.loc['29007', 'commute_pop_jt00']:.0%} | {t.loc['29019', 'commute_pop_jt00']:.0%} | "
      f"{t.loc['29151', 'commute_pop_jt00']:.0%} | {t.commute_pop_jt00.median():.0%} | {t.loc['29189', 'commute_pop_jt00']:.0%} |")
print(f"\nDetection slope b = {B_SLOPE[0]:.3f} [{B_SLOPE[1]:.3f}, {B_SLOPE[2]:.3f}]")
print("| County | Calibrated (adopted) | Range over b in [0, 1] | Range over the b interval | b = 1 (sensitivity) | b = 0 (sensitivity) | Linear split (sensitivity) |\n|---|---:|---:|---:|---:|---:|---:|")
for f in ("29007", "29019", "29151", None, "29189"):
    r = t.median(numeric_only=True) if f is None else t.loc[f]
    print(f"| {'Missouri median' if f is None else t.loc[f, 'name']} | {r.dedup_lower:.0%} | {r.dedup_bound_low:.0%}-{r.dedup_bound_high:.0%} | {r.dedup_band_low:.0%}-{r.dedup_band_high:.0%} | "
          f"{r.dedup_b1:.0%} | {r.dedup_b0:.0%} | {r.dedup_linear:.0%} |")
for c_ in ("dedup_lower", "dedup_linear", "dedup_b0", "dedup_b1"):
    o = (t[c_] > t.dedup_bound_high + 1e-9) | (t[c_] < t.dedup_bound_low - 1e-9)
    print(f"containment check, {c_}: inside the range over b in [0, 1] in {len(t) - o.sum()} of {len(t)} counties"
          + ("" if not o.any() else f"; outside: {t.name[o].tolist()}"))
assert not ((t.dedup_lower > t.dedup_bound_high + 1e-9) | (t.dedup_lower < t.dedup_bound_low - 1e-9)).any(), "calibrated outside its grid range"
t["size"] = pd.cut(t.population, [0, 10_000, 20_000, 50_000, 1e8], labels=["<10k", "10-20k", "20-50k", "50k+"])
print("\n| County population | Counties | Range over b in [0, 1], width, median (middle 80%), points | Range over the b interval, width, median | Calibrated, median | Low, median | High, median |")
print("|---|---:|---:|---:|---:|---:|---:|")
for k, g_ in t.groupby("size", observed=True):
    print(f"| {k} | {len(g_)} | {100 * g_.dedup_bound_width.median():.1f} ({100 * g_.dedup_bound_width.quantile(.1):.1f}-"
          f"{100 * g_.dedup_bound_width.quantile(.9):.1f}) | {100 * (g_.dedup_band_high - g_.dedup_band_low).median():.1f} | {g_.dedup_lower.median():.0%} | {g_.dedup_bound_low.median():.0%} | {g_.dedup_bound_high.median():.0%} |")
t = t.drop(columns="size")
print("\n| County | Current crossover (summed counts) | Distinct people seen outside, monthly (lower bound) | "
      "Commuting out / population | Commuting out / employed | Conservative | Set by |")
print("|---|---:|---:|---:|---:|---:|---|")
for f in ("29007", "29019", "29151", "29051", "29027", "29077", "29095", "29189"):
    r = t.loc[f]
    print(f"| {r['name']} | {r.current:.0%} | {r.dedup_lower:.0%} | {r.commute_pop:.0%} | {r.commute_emp:.0%} | {r.conservative:.0%} | {r.set_by} |")
print(f"\nall {len(t)} counties: correlation of current crossover with the conservative lower bound "
      f"{np.corrcoef(t.current, t.conservative)[0, 1]:.2f}; conservative set by phone data in {(t.set_by == 'phone data').sum()}, "
      f"by commuting in {(t.set_by == 'commuting').sum()}")
print("medians:", {c: f"{t[c].median():.1%}" for c in ("current", "dedup_lower", "commute_pop", "commute_emp", "commute_pop_jt00",
                                                       "commute_emp_jt00", "conservative")})
print("commuters / population including jobs in the 8 neighbouring states: median", f"{t.commute_pop_all.median():.1%}",
      "; Audrain, Boone, Osage, St. Louis:", t.loc[["29007", "29019", "29151", "29189"], "commute_pop_all"].round(3).tolist())
print("JT01 - JT00, commuters / employed: median", f"{(t.commute_emp - t.commute_emp_jt00).median():+.3f}",
      "range", f"{(t.commute_emp - t.commute_emp_jt00).min():+.3f} to {(t.commute_emp - t.commute_emp_jt00).max():+.3f}")
print("Kansas destinations add (dedup_b1 - dedup_acs_mo), points: median", f"{100 * (t.dedup_b1 - t.dedup_acs_mo).median():.2f}",
      "; largest:", (100 * (t.dedup_b1 - t.dedup_acs_mo)).sort_values().tail(4).round(1).rename(t.name).to_dict())
