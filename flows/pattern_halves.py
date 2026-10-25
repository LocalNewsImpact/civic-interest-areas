"""Superseded 2026-10-24: flows/travel_patterns.py writes <region out>/patterns_halves.json itself -- the odd- and
even-month mean reach (missing home-months left out) AND W and H refitted on each half (independent halves, matched to
the kept patterns). This script now only checks that the file matches the published patterns.
Usage: pattern_halves.py <region>"""
import json
import sys
from pathlib import Path

here = Path(__file__).parent
region = sys.argv[1] if len(sys.argv) > 1 else "columbia"
R = here.parent / json.load(open(here / "regions.json"))[region]["out"]
P, Hh = json.load(open(R / "patterns.json")), json.load(open(R / "patterns_halves.json"))
assert Hh.get("homes") == P["homes"] and Hh.get("units") == P["units"], "patterns_halves.json is not from the published fit"
assert "W_odd" in Hh, "patterns_halves.json has no half fits: rerun travel_patterns.py"
print(region, "halves match:", len(P["homes"]), "homes x", len(P["units"]), "units, K =", len(Hh["H_odd"]))
