"""One public model, each county class built with its best public setting (public_default_sensitivity.py runs):
  small rural        observed LODES within 90 miles, gravity beyond; 40 work days; chained errands; Huff on sales
  independent towns  the same with decay 6 for retail, medical and specialty
  commuter           gravity work part, 20 work days, chained errands
  hubs               observed LODES within 90 miles; 20 work days; Huff on surplus sales (Reilly, exponent 2 form)
  class 5            commuter counties outside the Kansas City and St. Louis metros: CLASS5 = the tag of the setting
                     (default the commuter setting)
Output analysis/public_model_pairs_tiers_byclass.csv (tract shares, same columns as the inputs it is cut from)."""
from pathlib import Path

import pandas as pd

A = Path(__file__).resolve().parent
import os
_R = ("r" + os.environ.get("HYB", "")) if os.environ.get("REGULAR") == "1" else ""   # regular-travel builds (REGULAR=1), HYB="45": observed LODES within 45 mi
PICK = {"class 1": f"_{_R}g_40_sales", "class 2": f"_{_R}c_40_l6all", "class 3": "_rc_grav20" if _R else "_c_grav20", "class 4": f"_{_R}g_20_surplus",
        "class 5": os.environ.get("CLASS5", f"_{_R}c_grav20")}
ST = os.environ.get("STATE", "29")
SUF = "" if ST == "29" else f"_{ST}"
tier = pd.read_csv(A / f"county_class_k4{SUF}.csv", dtype={"fips": str}).set_index("fips")["class"]
_dl = pd.read_excel(A.parent / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str).dropna(subset=["FIPS County Code"])
_bigm = set((_dl["FIPS State Code"] + _dl["FIPS County Code"])[_dl["CBSA Code"].isin(["28140", "41180"])])


def klass(h):
    """class 5: commuter counties outside the Kansas City and St. Louis metros (rings of regional hubs)"""
    c = tier.get("29189" if h == "29510" else h, "class 1")
    return "class 5" if c == "class 3" and h not in _bigm else c
parts = []
for c, tag in PICK.items():
    T = pd.read_csv(A / f"public_model_pairs_tiers{SUF}{tag}.csv", dtype={"tract": str, "j": str, "home": str})
    parts.append(T[T.home.map(klass) == c][["tract", "home", "j", "miles", "combined_share"]])
out = pd.concat(parts)
out.to_csv(A / f"public_model_pairs_tiers{SUF}_byclass{os.environ.get('OUTTAG', '')}.csv", index=False)
print(len(out), "rows,", out.tract.nunique(), "tracts")
