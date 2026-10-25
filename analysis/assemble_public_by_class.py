"""One public model, each county class built with its own public setting -- no Advan in any parameter; Advan chose
among settings (nested: public_stage1_nested.py chooses each class's setting with the scored county left out; the
setting chosen on all Missouri counties is the one used here and in Kansas).

Settings (analysis/public_stage1_choice.csv, rows county = ALL), by class:
  class 1  small rural
  class 2  independent towns
  class 3  commuter counties in the Kansas City or St. Louis metro (OMB 2023)
  class 5  commuter counties outside those metros (rings of regional hubs; in Kansas the Wichita ring)
  class 4  hubs
LEGACY=1 or REGULAR=1: the hand-picked settings of 2026-10-18 (small rural observed LODES within 90 mi, 40 work days,
chained errands, Huff on sales; independent towns the same with decay 6; commuter gravity work part, 20 days; hubs
Huff on surplus sales; class 5 = CLASS5), and the regular-travel builds.
STATE=20: the Kansas builds of the same settings (public_model_pairs_tiers_20<TAG>.csv; county_class_k4_20.csv).
Output analysis/public_model_pairs_tiers[_20]_byclass<OUTTAG>.csv (tract shares, same columns as the inputs).
Environment (printed at start): STATE, OUTTAG, LEGACY, REGULAR, HYB, CLASS5. Runs of 2026-10-24:
  OUTTAG=_nested                                    Missouri, settings chosen on all Missouri counties
  STATE=20 OUTTAG=_nested                           Kansas, the same settings (transfer_adjustments.py BASE)
  LEGACY=1 CLASS5=_g_40_sales OUTTAG=_c5_g_40_sales the 2026-10-18 base of public_adjusted_pairs_trnear.csv"""
import os
from pathlib import Path

import pandas as pd

A = Path(__file__).resolve().parent
_R = ("r" + os.environ.get("HYB", "")) if os.environ.get("REGULAR") == "1" else ""   # regular-travel builds (REGULAR=1), HYB="45": observed LODES within 45 mi
if os.environ.get("REGULAR") == "1" or os.environ.get("LEGACY") == "1":
    PICK = {"class 1": f"_{_R}g_40_sales", "class 2": f"_{_R}c_40_l6all", "class 3": "_rc_grav20" if _R else "_c_grav20", "class 4": f"_{_R}g_20_surplus",
            "class 5": os.environ.get("CLASS5", f"_{_R}c_grav20")}
else:
    _ch = pd.read_csv(A / "public_stage1_choice.csv", keep_default_na=False)
    _ch = _ch[_ch.county == "ALL"].set_index("segment").insample_choice
    PICK = {"class 1": _ch["small rural"], "class 2": _ch["indep. towns"], "class 3": _ch["commuter: major metro"],
            "class 5": _ch["commuter: regional hub"], "class 4": _ch["hubs"]}
ST = os.environ.get("STATE", "29")
SUF = "" if ST == "29" else f"_{ST}"
tier = pd.read_csv(A / f"county_class_k4{SUF}.csv", dtype={"fips": str}).set_index("fips")["class"]
_dl = pd.read_excel(A.parent / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str).dropna(subset=["FIPS County Code"])
_bigm = set((_dl["FIPS State Code"] + _dl["FIPS County Code"])[_dl["CBSA Code"].isin(["28140", "41180"])])


def klass(h):
    """class 5: commuter counties outside the Kansas City and St. Louis metros (rings of regional hubs)"""
    c = tier.get("29189" if h == "29510" else h, "class 1")
    return "class 5" if c == "class 3" and h not in _bigm else c


print("environment:", {k: os.environ.get(k, "") for k in ("STATE", "OUTTAG", "LEGACY", "REGULAR", "HYB", "CLASS5")}, "| settings:", PICK)
parts = []
for c, tag in PICK.items():
    T = pd.read_csv(A / f"public_model_pairs_tiers{SUF}{tag}.csv", dtype={"tract": str, "j": str, "home": str})
    parts.append(T[T.home.map(klass) == c][["tract", "home", "j", "miles", "combined_share"]])
out = pd.concat(parts)
out.to_csv(A / f"public_model_pairs_tiers{SUF}_byclass{os.environ.get('OUTTAG', '')}.csv", index=False)
print(len(out), "rows,", out.tract.nunique(), "tracts")
