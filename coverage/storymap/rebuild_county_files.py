"""Rebuild the per-county story-map files from the statewide export.

Each <county>_all.json names its publishers in spec.publishers; <county>_articles.json is those publishers'
articles from statewide_2026_03_articles.json -- reproduced exactly for Audrain, Osage and Boone without
broadcasters, and to within one article for Boone (export timing), on 2026-10-17. Outlets in
analysis/excluded_outlets.EXCLUDE are dropped from both, so a county's coverage counts only its local outlets.
"""
import json
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parents[1] / "analysis"))
from excluded_outlets import EXCLUDE  # noqa: E402

arts = json.load(open(here / "statewide_2026_03_articles.json"))["articles"]
names = {a["source"]: a["publisher"] for a in arts}
for stem in ("audrain_all", "boone_all", "boone_no_broadcast", "osage_all"):
    d = json.load(open(here / f"{stem}.json"))
    keep = [p for p in d["spec"]["publishers"] if names.get(p) not in EXCLUDE]
    dropped = sorted(names.get(p, p) for p in d["spec"]["publishers"] if p not in keep)
    sel = [{"id": a["id"], "central": a["central"], "counties": a["counties"]} for a in arts if a["source"] in set(keep)]
    d["spec"]["publishers"], d["articles"] = keep, len(sel)
    d["publishers"] = [n for n in d.get("publishers", []) if n not in EXCLUDE]
    json.dump(d, open(here / f"{stem}.json", "w"))
    json.dump(sel, open(here / f"{stem}_articles.json", "w"))
    print(stem, len(sel), "articles from", len(keep), "publishers", f"(dropped {dropped})" if dropped else "")
