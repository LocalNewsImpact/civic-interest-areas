"""The frame on which a public-data travel build is compared with Advan, for public_stage1_nested.py.

Public model: BASE (default the trade area build public_model_pairs_tiers_tac.csv; public_stage1_nested.py sets
public_model_pairs_tiers_g_40_sales.csv), tract -> county shares, rolled up to counties by 2020 tract population.
Advan and the Advan-fitted model (counties held out): compare_shares.csv (public_vs_advan_compare.py).

Destination set: every model is scored on the public model's destinations (counties within 200 miles of the tract);
Advan and the Advan-fitted model are renormalised over that set (COMMON), and Advan's share outside it is reported
(outside). Scores: share-weighted error and log-ratio error (public_scoring.py), by segment of home county (SEGS: the
travel model's county classes, commuter counties split by whether their metro has 1 million people or more).
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
from gravity_terms import all_pairs, root  # noqa: E402

A_ = root / "analysis"
S = pd.read_csv(A_ / "compare_shares.csv", dtype={"i": str, "j": str})
pp = all_pairs()
assert (pp.i.values == S.i.values).all() and (pp.j.values == S.j.values).all()
a_raw = S.advan.values
adv_raw = S["Advan-fitted (adopted, counties held out)"].values
BASE = os.environ.get("BASE", "public_model_pairs_tiers_tac.csv")      # the public build the frame is aligned to
T = pd.read_csv(A_ / BASE, dtype={"tract": str, "j": str, "home": str})
T = T[(T.j.str[:2] == "29") & (T.home != T.j)].reset_index(drop=True)
_tr = pd.read_csv(root / "census_dl/ref/CenPop2020_Mean_TR29.txt", dtype=str, encoding="utf-8-sig")
tpop = dict(zip(_tr.STATEFP + _tr.COUNTYFP + _tr.TRACTCE, _tr.POPULATION.astype(float)))
unit = lambda f: "29189" if f == "29510" else f
tier = pd.read_csv(A_ / "county_class_k4.csv", dtype={"fips": str}).set_index("fips")["class"]
_dl = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str).dropna(subset=["FIPS County Code"])
_bigm = set((_dl["FIPS State Code"] + _dl["FIPS County Code"])[_dl["CBSA Code"].isin(["28140", "41180"])])

# ---- integer codes for fast group sums ----------------------------------------------------------------------------
homes_S, ii = np.unique(S.i.values, return_inverse=True)
key = list(zip(S.i, S.j))
_kidx = {k: n for n, k in enumerate(key)}
sidx = np.array([_kidx[(h, j)] for h, j in zip(T.home, T.j)])         # T row -> S row
tracts_T, tcode = np.unique(T.tract.values, return_inverse=True)
tw = T.tract.map(tpop).values
NS = len(S)

# ---- common destination set: the public model's support ----------------------------------------------------------
COMMON = np.zeros(NS, bool); COMMON[sidx] = True


def renorm_S(x):
    s = np.bincount(ii, x, minlength=len(homes_S))[ii]
    return np.where(s > 0, x / np.where(s > 0, s, 1), 0.0)


a = renorm_S(a_raw * COMMON)                     # Advan, renormalised over the common set
adv = renorm_S(adv_raw * COMMON)                 # Advan-fitted, the same
outside = pd.Series(a_raw * ~COMMON).groupby(S.i.values).sum()     # Advan share outside the common set, per home


def tract_norm(x, rows=None):
    """Normalise shares to 1 within each tract (over the rows given)."""
    if rows is None:
        s = np.bincount(tcode, x, minlength=len(tracts_T))[tcode]
    else:
        tc = tcode[rows]; s = np.bincount(tc, x, minlength=len(tracts_T))[tc]
    return np.where(s > 0, x / np.where(s > 0, s, 1), 0.0)


def roll(share_T):
    """Tract shares (aligned with T) -> county shares on the S frame, weighted by 2020 tract population."""
    x = np.bincount(sidx, share_T * tw, minlength=NS)
    return renorm_S(x)


# ---- segments of home county ---------------------------------------------------------------------------------------
seg = lambda i: {"class 1": "small rural", "class 2": "indep. towns", "class 4": "hubs"}.get(
    tier.get(unit(i), "class 1"), "commuter: major metro" if i in _bigm else "commuter: regional hub")
SEGS = ["small rural", "indep. towns", "commuter: major metro", "commuter: regional hub", "hubs"]
SEG_OF = pd.Series({h: seg(h) for h in homes_S})
