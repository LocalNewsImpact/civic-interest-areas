"""Story-resampling intervals and threshold sensitivity for coverage density and the balanced diet (Supplementary
material S3; review, 2026-10-31).

Intervals: the stories that locate anywhere (every outlet statewide, March 2026) are resampled with replacement DRAWS
times; each draw recomputes every hexagon's weighted stories, in all and by CIN category, and each area's share of
hexagons with frequent coverage (9+ a month) and with a balanced diet (8 of 10 categories at 1+ a month). Percentile
95% intervals. The outlets, their story counts' expectation and the areas are held fixed: the intervals describe the
sampling of stories within the month, not of outlets or of months.

Sensitivity: the same shares with frequent coverage at 6+, 9+ and 12+ stories a month and the balanced diet at 7, 8 and
9 of 10 categories, on the stories as observed.

Reads area_coverage_alignment.py as a library (COV_LIB=1: its story attribution, areas and weights; the adopted
tiers 2/9 and the diet rule 8 of 10 are its and cin_diet.py's). Writes analysis/coverage_intervals.csv.
Env REGION (default columbia), DRAWS (default 999)."""
import os
import runpy
import sys
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
DRAWS, SEED = int(os.environ.get("DRAWS", 999)), 20261031
FREQUENT, NEED, FLOOR = (6.0, 9.0, 12.0), (7, 8, 9), 1.0
CATS = ["Emergencies and Public Safety", "Civic information", "Political life", "Education", "Environment and Planning",
        "Health", "Transportation Systems", "Economic Development", "Civic Life", "Sports"]
os.environ["COV_LIB"] = "1"
sys.argv = ["area_coverage_alignment.py"]
A = runpy.run_path(str(root / "analysis/area_coverage_alignment.py"), run_name="cov_lib")
story_hexes, art_out, CIN, SPORTS_W, layer = A["story_hexes"], A["art_out"], A["CIN"], A["SPORTS_W"], A["layer"]
assert A["TIERS"]["frequent"] == 9.0, "the adopted tier moved; FREQUENT lists it as 9"

stories = [aid for aid in story_hexes if aid in art_out]
cat = np.array([CATS.index(CIN[a]) if isinstance(CIN.get(a), str) and CIN[a] in CATS else -1 for a in stories])
sw = np.array([SPORTS_W if CIN.get(a) == "Sports" else 1.0 for a in stories])
N = len(stories)
print(f"{N:,} stories located; {DRAWS} draws", flush=True)


def shares(cv, bycat):
    """frequent share at each threshold; balanced-diet share at each number of categories required"""
    met = (bycat >= FLOOR).sum(0)
    return [float((cv >= f).mean()) for f in FREQUENT] + [float((met >= n).mean()) for n in NEED]


def draw(m, Wa, bycat_rows):
    """the shares when each story counts m times, over an area's story-by-hexagon weights Wa"""
    cv = m @ Wa
    bycat = np.stack([m[r] @ Wa[r] if len(r) else np.zeros(Wa.shape[1]) for r in bycat_rows])
    return shares(cv, bycat)


rng = np.random.default_rng(SEED)
rows = []
cols = [f"frequent {int(f)}+" for f in FREQUENT] + [f"balanced {n} of 10" for n in NEED]
for town, rank in A["AREAS"]:
    area = list(layer[town][rank]["all"])
    hix = {k: i for i, k in enumerate(area)}
    W = np.zeros((N, len(area)), np.float32)
    for i, a in enumerate(stories):
        for k, (w, _) in story_hexes[a].items():
            j = hix.get(k)
            if j is not None:
                W[i, j] = w * sw[i]
    rows_in = np.flatnonzero(W.any(1))
    Wa, ca = W[rows_in], cat[rows_in]
    bycat_rows = [np.flatnonzero(ca == c) for c in range(len(CATS))]
    point = draw(np.ones(len(rows_in)), Wa, bycat_rows)
    boot = np.array([draw(rng.multinomial(N, np.full(N, 1 / N))[rows_in].astype(np.float32), Wa, bycat_rows)
                     for _ in range(DRAWS)])
    lo, hi = np.percentile(boot, 2.5, axis=0), np.percentile(boot, 97.5, axis=0)
    label = f"{town} {'I' * rank}"
    row = {"area": label, "hexagons": len(area), "stories_in_area": len(rows_in)}
    for c, p, l_, h_ in zip(cols, point, lo, hi):
        row[c] = round(p, 3); row[f"{c} lo"] = round(float(l_), 3); row[f"{c} hi"] = round(float(h_), 3)
    rows.append(row)
    print(f"{label}: " + "; ".join(f"{c} {100 * p:.0f}% [{100 * l_:.0f}, {100 * h_:.0f}]" for c, p, l_, h_ in zip(cols, point, lo, hi)),
          flush=True)
pd.DataFrame(rows).to_csv(root / f"analysis/coverage_intervals{A['SUFFIX']}.csv", index=False)
