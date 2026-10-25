"""How stable each civic interest area (the network-tie map; halves fitted independently, confidence_layer.py) is, against how many residents follow it: for every study town and market
(market_patterns.py) in every region, the residents and share following the pattern, the hexagons the approved map
shows, and the share of them whose tie clears the map's floor in both halves of the year (confidence_layer.py)."""
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
            on, basef = g["shown_set"](net, set(g["MAPS"].get("in_market", [])))
            h = C.get(town, {}).get(str(m["rank"]))
            if not h:
                continue
            ext = [k for k in on if net[k] < 100]
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
