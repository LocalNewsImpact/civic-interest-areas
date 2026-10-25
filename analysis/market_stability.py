"""A DIAGNOSTIC OF ONE DRAWING (2026-10-25): for every study town and area (market_patterns.py) in every region, the
residents and share following the pattern, the hexagons drawn by the member of the settings ensemble with the adopted
settings (one middle-value drawing, not the published area: the area is the ensemble core, flows/area_ensemble.py), and
the share of them whose tie clears that drawing's floor in both halves of the year (independent halves,
confidence_layer.py). The ensemble exists for the built towns only, so this check of the minimum-size rule over all 58
areas is run on the one drawing."""
import json
import os
import runpy
import sys
from pathlib import Path

import pandas as pd

root = Path(__file__).resolve().parents[1]
os.environ["TIE_LIB"] = "1"
rows = []
for region in ("columbia", "springfield", "cape", "kirksville", "joplin", "kansascity", "stjoseph"):
    sys.argv = ["confidence_layer.py", region]
    src = open(root / "analysis/confidence_layer.py").read()
    g = {"__file__": str(root / "analysis/confidence_layer.py"), "__name__": "lib"}
    exec(compile(src[:src.index("if __name__ == \"__main__\":")], "confidence_layer.py", "exec"), g)
    C = json.load(open(root / ("flows/reach/confidence_columbia.json" if region == "columbia" else f"flows/reach/{region}/confidence.json")))
    for town, ms in g["MAPS"]["towns"].items():
        for m in ms:
            net = m["index"]["net"]                    # the published (network-tie) map; halves fitted independently
            home = g["HOMES"][town]
            on, basef = g["shown_set"](net, set(g["MAPS"].get("in_market", [])), home)
            h = C.get(town, {}).get(str(m["rank"]))
            if not h:
                continue
            ext = [k for k in on if k not in home]
            both = [k for k in ext if h["odd"].get(k, 0) >= basef and h["even"].get(k, 0) >= basef]
            rows.append({"region": region, "town": town, "rank": m["rank"], "residents": m["residents"], "share": m["share"],
                         "shown": len(ext), "holds_both": round(len(both) / max(len(ext), 1), 2)})
D = pd.DataFrame(rows).sort_values("residents")
D.to_csv(root / "analysis/market_stability.csv", index=False)
pd.set_option("display.width", 200)
print(D.to_string(index=False))
D["size"] = pd.cut(D.residents, [0, 500, 1000, 2000, 5000, 1e9], labels=["<500", "500-1k", "1-2k", "2-5k", "5k+"])
print(D.groupby("size", observed=True).agg(markets=("town", "size"), holds_both=("holds_both", "median"), min_holds=("holds_both", "min")).to_string())
print("Spearman rho (residents, share holding in both halves):", round(D.residents.corr(D.holds_both, method="spearman"), 2))
# THE AREA COUNT the log quotes, by town and in all (2026-10-25: every quoted number printed by the script producing it)
print("areas by town:", D.groupby(["region", "town"]).size().to_dict())
print("areas in all:", len(D), "in", D.town.nunique(), "towns")
print("(a diagnostic of one drawing -- the member with the adopted settings -- not of the published, ensemble-based area)")
