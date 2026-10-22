"""The travel matrix of travel_patterns.py for odd months (January, March, May, July 2026) and even months (February,
April, June) separately, same home block groups, units and masking as the published patterns -- for the certainty of
each pattern's market (analysis/confidence_layer.py). Runs travel_patterns.py's own code up to the fit.
Writes <region out>/patterns_halves.json: {X_odd, X_even} (home block group x unit, mean reach).
Usage: pattern_halves.py <region>"""
import json
import sys
from pathlib import Path

import numpy as np

here = Path(__file__).parent
src = open(here / "travel_patterns.py").read()
cut = src.index("MASK = np.ones((len(homes), len(units)))")
__file__ = str(here / "travel_patterns.py")
exec(compile(src[:cut], str(here / "travel_patterns.py"), "exec"))
P_ = json.load(open(R / "patterns.json"))
assert P_["homes"] == homes and P_["units"] == units, "homes or units differ from the published patterns"
odd, even = [i for i, m in enumerate(MONTHS) if int(m[-2:]) % 2 == 1], [i for i, m in enumerate(MONTHS) if int(m[-2:]) % 2 == 0]
json.dump({"X_odd": cube[odd].mean(0).round(4).tolist(), "X_even": cube[even].mean(0).round(4).tolist(),
           "months_odd": [MONTHS[i] for i in odd], "months_even": [MONTHS[i] for i in even]}, open(R / "patterns_halves.json", "w"))
print(REGION, "halves written:", len(homes), "homes x", len(units), "units")
