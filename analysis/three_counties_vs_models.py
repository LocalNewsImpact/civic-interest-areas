"""Boone, Audrain and Osage against the statewide models -> three_counties_table.csv (and printed tables)

Travel: residents' visits Jan-Sep 2026 (pass-through discounted) against the doubly-constrained travel model
(travel_model.py). The model is never exact, so each county's figure is read against its TYPICAL ERROR: the middle 80%
of actual / predicted across all big flows statewide (pairs carrying >= 5% of a home county's visits outside it).
Inside that range is "within the model's usual error".
Stories: March 2026 story-county pairs against the coverage model with travel (coverage_model.py) -- what the
newsrooms would write if coverage followed residents' travel the way it does statewide. A gap counts only outside the
Poisson 95% range; expected stories are whole numbers ("under 1" below one).
Rows: counties in the Columbia-Jefferson City market with 2%+ of the home county's visits or 5+ stories.
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
cov = pd.read_csv(root / "analysis/county_covariates.csv", dtype={"fips": str}).set_index("fips")
tp = pd.read_csv(root / "analysis/od_predicted.csv", dtype={"i": str, "j": str})
HOME = {"Audrain": "29007", "Boone": "29019", "Osage": "29151"}
DMA = ["29007", "29019", "29027", "29041", "29051", "29053", "29089", "29125", "29131", "29135", "29139", "29141",
       "29151", "29175"]
big = tp[tp.visits_share >= 0.05].ratio
lo, hi = big.quantile(0.10), big.quantile(0.90)
print(f"Typical model error on big flows statewide: middle 80% {lo:.2f}x-{hi:.2f}x (middle half "
      f"{big.quantile(.25):.2f}x-{big.quantile(.75):.2f}x)")


def poisson_range(mu):
    lo_, cdf, k, p = None, 0.0, 0, math.exp(-mu)
    while True:
        cdf += p
        if lo_ is None and cdf > 0.025:
            lo_ = k
        if cdf >= 0.975:
            return lo_, k
        k += 1
        p *= mu / k


whole = lambda x: "under 1" if x < 0.5 else str(int(round(x)))
rows = []
for version, label in (("all", "all outlets"), ("no_broadcast", "print and digital")):
    cp = pd.read_csv(root / f"analysis/coverage_predicted_{version}.csv", dtype={"i": str, "j": str}).set_index(["i", "j"])
    for name, f in HOME.items():
        if version == "no_broadcast" and name != "Boone":
            continue
        t = tp[tp.i == f].set_index("j")
        print(f"\n### {name} ({label})")
        print("| County | Share of residents' visits outside the county | Visits vs model | Stories | Expected stories | Stories |")
        print("|---|---:|---|---:|---:|---|")
        for j in sorted((j for j in DMA if j != f), key=lambda j: -t.visits_share[j]):
            n, mu = int(cp.stories[(f, j)]), float(cp.pred_travel[(f, j)])
            if t.visits_share[j] < 0.02 and n < 5:
                continue
            ratio = t.ratio[j]
            travel = ("within the model's usual error" if lo <= ratio <= hi else
                      "more than the model's usual error" if ratio > hi else "less than the model's usual error")
            a, b = poisson_range(mu)
            story = "more than expected" if n > b else "fewer than expected" if n < a else "as expected"
            rows.append({"home": name, "outlets": label, "county": cov.name[j], "visits_share": round(t.visits_share[j], 3),
                         "visits_vs_model": round(ratio, 2), "travel": travel, "stories": n,
                         "expected_stories": whole(mu), "coverage": story})
            print(f"| {cov.name[j]} | {t.visits_share[j]:.1%} | {ratio:.2f}x, {travel} | {n} | {whole(mu)} | {story} |")
pd.DataFrame(rows).to_csv(root / "analysis/three_counties_table.csv", index=False)
