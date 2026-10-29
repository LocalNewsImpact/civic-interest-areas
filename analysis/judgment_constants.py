"""Table S2: the civic interest areas with each constant set by judgment halved or doubled, against the adopted areas.

Reads the adopted ensemble (flows/reach/probability_columbia.json) and the six redrawn ensembles that
scripts/reproduce.sh (stage sensitivity) writes to flows/reach/sensitivity/prob_<variant>.json, each with its area
rule applied by flows/area_core.py. For each variant and town: the share of the adopted area's places the redrawn area
also includes, the Jaccard overlap, square miles, and frequent coverage (9+ stories a month) on the redrawn area.
"""
import json, os, runpy, sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
D = root / "flows/reach/sensitivity"
os.environ["COV_LIB"] = "1"
sys.argv = ["area_coverage_alignment.py"]
A = runpy.run_path(str(root / "analysis/area_coverage_alignment.py"), run_name="cov_lib")
cov, TIERS, MAPS, km2_of = A["cov"], A["TIERS"], A["MAPS"], A["km2_of"]
TOWNS = ("Columbia", "Mexico", "Linn")
VARIANTS = [   # (file key, constant, value): adopted direct 0.3, shared places 0.7, direction 0.5
    ("direct_half", "Direct news ties", "0.15"), ("direct_double", "Direct news ties", "0.6"),
    ("shared_half", "Ties through shared places", "0.35"), ("shared_double", "Ties through shared places", "1.4"),
    ("gamma_quarter", "Direction strength", "0.25"), ("gamma_one", "Direction strength", "1.0")]


def area(pr, t):
    return {k for k in pr[t]["1"]["core50_area_hexes"] if k in MAPS["hexes"]}


def frequent(hs):
    return 100 * sum(1 for k in hs if sum(cov["all"][o].get(k, 0) for o in cov["all"]) >= TIERS["frequent"]) / max(1, len(hs))


def sq_mi(hs):
    return km2_of(hs) / 2.58999


adopted = json.load(open(root / "flows/reach/probability_columbia.json"))
a0 = {t: area(adopted, t) for t in TOWNS}
rows = [("As adopted", "0.3, 0.7, 0.5", {t: (100.0, 1.0, sq_mi(a0[t]), frequent(a0[t])) for t in TOWNS})]
for key, constant, value in VARIANTS:
    pr = json.load(open(D / f"prob_{key}.json"))
    m = {}
    for t in TOWNS:
        a1 = area(pr, t)
        m[t] = (100 * len(a0[t] & a1) / len(a0[t]), len(a0[t] & a1) / len(a0[t] | a1), sq_mi(a1), frequent(a1))
    rows.append((constant, value, m))

print("Table S2. Places kept | frequent coverage: Columbia, Mexico, Linn")
print("| Constant | Value | " + " | ".join(f"Kept {t}" for t in TOWNS) + " | " + " | ".join(f"Frequent {t}" for t in TOWNS) + " |")
print("|---|---|" + "---:|" * 6)
for constant, value, m in rows:
    print(f"| {constant} | {value} | " + " | ".join(f"{m[t][0]:.0f}%" for t in TOWNS) + " | "
          + " | ".join(f"{m[t][3]:.0f}%" for t in TOWNS) + " |")
print("\nJaccard overlap | square miles: Columbia, Mexico, Linn")
for constant, value, m in rows:
    print(f"  {constant:28s} {value:14s} " + "  ".join(f"{m[t][1]:.2f} {m[t][2]:,.0f}" for t in TOWNS))
kept = [m[t][0] for _, _, m in rows[1:] for t in TOWNS]
shift = [abs(m[t][3] - rows[0][2][t][3]) for _, _, m in rows[1:] for t in TOWNS]
print(f"\nplaces kept {min(kept):.0f}% to {max(kept):.0f}%; frequent coverage moves at most {max(shift):.0f} points")
