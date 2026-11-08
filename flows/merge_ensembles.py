"""One ensemble file from per-town ensemble files (2026-11-07). scripts/reproduce.sh runs area_ensemble.py as one
process per town (TOWNS=<town>, OUT=<part>) so the ensembles use several cores; a town's record depends only on its own
members, so the parts are joined by town. Checked against one process for all towns (2026-11-07, PYTHONHASHSEED=0):
the probabilities, areas and month split are identical; set iteration order, which depends on what the process ran
before, still moves the travel-alone outline's vertex order, town key order, a one-resident rounding in people50_split
and county ties in the distant_ties diagnostic.

usage: merge_ensembles.py <out.json> <part.json> ... ; a town found in two parts is an error.
"""
import json
import sys

out = {}
for part in sys.argv[2:]:
    for town, rec in json.load(open(part)).items():
        if town in out:
            raise SystemExit(f"{town} in more than one part ({part})")
        out[town] = rec
json.dump(out, open(sys.argv[1], "w"))
print(f"merged {', '.join(out)} -> {sys.argv[1]}")
