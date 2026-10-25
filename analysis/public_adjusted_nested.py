"""Stage 2 scored with the structure chosen inside the cross-validation: an outer loop around the learning of the
Advan-learned corrections.

The log chose the structure of the corrections (SPLIT3, C5AS, DIST_BY_RANK, CORE_NEAR, RC_PF, TRANSFER, the group
sets) on the same 8-fold score it reported. Here, for each outer fold k of home counties (the 8 folds of
public_adjusted_model.py):
  1. Stage 1: each class's public setting is chosen on the counties outside fold k (public_stage1_nested.py's
     candidates and rule);
  2. every candidate structure is scored by inner cross-validation on the other 7 folds only (learn on 6, predict 1);
  3. the structure with the lowest inner share-weighted error (all Advan destinations, the primary metric) is
     learned on all 7 folds and applied to fold k.
Fold k's counties are therefore scored with a setting and a structure neither chosen nor learned with them. Done for
each mode (C segment factors only, A + one factor per destination county, B + destination factor from public
measures), each mode choosing its own structure.

Candidate structures: the full factorial of the choices the Refinements table made -- commuter split (none; split,
rings of regional hubs their own class; split, learned as independent towns; split, learned as small rural) x
DIST_BY_RANK (0/1) x CORE_NEAR (0/1) x destination-order definitions (Missouri: regional centre at pull factor 1.1;
at 1.0; transferable) x group sets (none; commuting out and in; destination order; + commuting rank; + destination
class) = 240, plus the five rejected variants on the adopted structure (+ rank x order cell, destination class x
band, pooled hub factor, hub distance bands, metro-core factor): 245.

Also reported: the structure chosen the old way (lowest 8-fold score on all counties, Stage 1 chosen on all
counties) -- the in-sample selection -- and the transferable structure (TRANSFER=1 only) chosen on all Missouri
counties, exported for the Kansas test (segment_corrections_mo.pkl, transfer_adjustments.py).
Outputs: analysis/public_adjusted_nested_pairs.csv (county shares), public_adjusted_nested_choices.csv (structure per
outer fold and mode), public_adjusted_nested_configs.csv (every structure's inner and all-county scores).
Scored by score_segments.py.
"""
import itertools
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
os.environ.setdefault("BASE", "public_model_pairs_tiers_g_40_sales.csv")
import public_adjusted_model as M  # noqa: E402
import public_stage1_nested as S1  # noqa: E402

ADOPTED = dict(SPLIT3=True, C5AS="class 2", DIST_BY_RANK=True, DIST_HUB=False, CORE=False, CORE_NEAR=True, TRANSFER=True,
               RC_PF=1.0, COMMUTE=("commute_rank", "dest_order", "dest_class"), POOLED=())


def configs():
    out = []
    splits = [(False, "class 5"), (True, "class 5"), (True, "class 2"), (True, "class 1")]
    defs = [(False, 1.1), (False, 1.0), (True, 1.0)]
    groups = [(), ("commute_out", "commute_in"), ("dest_order",), ("commute_rank", "dest_order"), ("commute_rank", "dest_order", "dest_class")]
    for (sp, c5), dbr, near, (tr, rc), g in itertools.product(splits, (False, True), (False, True), defs, groups):
        out.append(dict(SPLIT3=sp, C5AS=c5, DIST_BY_RANK=dbr, DIST_HUB=False, CORE=False, CORE_NEAR=near, TRANSFER=tr, RC_PF=rc, COMMUTE=g, POOLED=()))
    for ch in ({"COMMUTE": ADOPTED["COMMUTE"] + ("rank_order",)}, {"COMMUTE": ("commute_rank", "dest_order", "dest_class_band")},
               {"POOLED": ("hub",)}, {"DIST_HUB": True}, {"CORE": True}):
        out.append({**ADOPTED, **ch})
    return out


def name(c):
    sp = "nosplit" if not c["SPLIT3"] else {"class 5": "split", "class 2": "split->indep", "class 1": "split->rural"}[c["C5AS"]]
    d = "transfer" if c["TRANSFER"] else f"MO pf{c['RC_PF']}"
    x = [sp, d, "dbr" if c["DIST_BY_RANK"] else "", "near" if c["CORE_NEAR"] else "", "+".join(c["COMMUTE"]) or "no groups",
         "pooled hub" if c["POOLED"] else "", "hub bands" if c["DIST_HUB"] else "", "core" if c["CORE"] else ""]
    return " ".join(v for v in x if v)


# ---- Stage 1 inside the outer folds --------------------------------------------------------------------------------
NAMES, V = S1.load_variants()
Esw, Elr, _ = S1.county_errors(V)
fold_h = pd.Series({h: M.fold_of[M.unit(h)] for h in M.homes_S})
seg_T = M.T.home.map(M.SEG_OF).values


def stage1_base(exclude_fold=None):
    choice = {}
    for s in M.SEGS:
        cs = [h for h in M.SEG_OF.index[M.SEG_OF == s] if fold_h[h] != exclude_fold]
        choice[s] = S1.choose(Esw, cs)
    idx = np.array([choice[s] for s in seg_T])
    return V[np.arange(len(M.T)), idx], choice


BASES = {k: stage1_base(k) for k in range(8)}
BASE_FULL = stage1_base(None)
P_BASES = {k: M.roll(b) for k, (b, _) in BASES.items()}
P_FULL = M.roll(BASE_FULL[0])
CFGS = configs()
MODES = ("C", "A", "B")


def sw_home(p):
    # selection metric = the primary metric: share-weighted error over all Advan destinations (0 outside the support)
    return np.bincount(M.ii, 100 * M.a_raw * np.abs(p - M.a_raw), minlength=len(M.homes_S))


def run_cfg(n):
    K = M.keys(CFGS[n])
    res = {}
    for mode in MODES:
        par = M.MODES[mode]
        inner = np.zeros(8); outer = np.zeros(M.NS)
        for k in range(8):
            pb, base = P_BASES[k], BASES[k][0]
            pred = np.zeros(len(M.T))
            for l in range(8):
                if l == k:
                    continue
                F = M.learn(K, pb, (M.fold_S != k) & (M.fold_S != l), par)
                rows = M.fold_T == l
                pred[rows] = M.apply(K, base, rows, F)
            e = sw_home(M.roll(pred))
            inner[k] = e[(fold_h != k).values].mean()
            F = M.learn(K, pb, M.fold_S != k, par)
            rows = M.fold_T == k
            pk = np.zeros(len(M.T)); pk[rows] = M.apply(K, base, rows, F)
            q = M.roll(pk); outer[M.fold_S == k] = q[M.fold_S == k]
        full = M.roll(M.cv(K, BASE_FULL[0], P_FULL, mode))
        res[mode] = (inner, outer, full, sw_home(full).mean())
    return n, res


def main():
    t0 = time.time()
    print(f"{len(CFGS)} candidate structures x {len(MODES)} modes; Stage 1 per outer fold:",
          {k: {s: NAMES[v] for s, v in BASES[k][1].items()} for k in (0,)}, "...", flush=True)
    R = {}
    with mp.get_context("fork").Pool(int(os.environ.get("PROCS", "2"))) as pool:
        for n, res in pool.imap_unordered(run_cfg, range(len(CFGS)), chunksize=2):
            R[n] = res
            if len(R) % 25 == 0:
                print(f"  {len(R)}/{len(CFGS)} structures, {time.time() - t0:.0f}s", flush=True)
    out = pd.DataFrame({"i": M.S.i, "j": M.S.j, "dist": M.S.dist, "common": M.COMMON, "advan": M.a, "fitted": M.adv})
    st1 = pd.read_csv(M.A_ / "public_stage1_nested_pairs.csv", dtype={"i": str, "j": str})
    assert (st1.i.values == out.i.values).all() and (st1.j.values == out.j.values).all()
    out["public_nested"] = st1.public_nested.values; out["public_insample"] = st1.public_insample.values
    base_outer = np.zeros(M.NS)
    for k in range(8):
        base_outer[M.fold_S == k] = P_BASES[k][M.fold_S == k]
    out["public_foldbase"] = base_outer
    ch, cf = [], []
    for n, c in enumerate(CFGS):
        cf.append({"structure": name(c), **{f"{m}_inner_mean": R[n][m][0].mean() for m in MODES},
                   **{f"{m}_allcounty_cv": R[n][m][3] for m in MODES}, "transferable": c["TRANSFER"]})
    for mode in MODES:
        sel = np.zeros(M.NS)
        for k in range(8):
            best = int(np.argmin([R[n][mode][0][k] for n in range(len(CFGS))]))
            sel[M.fold_S == k] = R[best][mode][1][M.fold_S == k]
            ch.append({"mode": mode, "outer_fold": k, "structure": name(CFGS[best]), "inner_error": R[best][mode][0][k],
                       "stage1": "; ".join(f"{s}: {NAMES[v]}" for s, v in BASES[k][1].items())})
        out[f"{mode}_outer"] = sel
        bi = int(np.argmin([R[n][mode][3] for n in range(len(CFGS))]))
        out[f"{mode}_insample"] = R[bi][mode][2]
        ch.append({"mode": mode, "outer_fold": "in-sample", "structure": name(CFGS[bi]), "inner_error": R[bi][mode][3],
                   "stage1": "; ".join(f"{s}: {NAMES[v]}" for s, v in BASE_FULL[1].items())})
        na = CFGS.index(ADOPTED)
        out[f"{mode}_adopted"] = R[na][mode][2]
    out.to_csv(M.A_ / "public_adjusted_nested_pairs.csv", index=False)
    pd.DataFrame(ch).to_csv(M.A_ / "public_adjusted_nested_choices.csv", index=False)
    cfdf = pd.DataFrame(cf).sort_values("C_allcounty_cv")
    cfdf.to_csv(M.A_ / "public_adjusted_nested_configs.csv", index=False)
    # transferable structure for Kansas: chosen on all Missouri counties (Kansas is held out entirely)
    tn = min((n for n, c in enumerate(CFGS) if c["TRANSFER"]), key=lambda n: R[n]["C"][3])
    print("transferable structure chosen on all Missouri counties (mode C):", name(CFGS[tn]), f"{R[tn]['C'][3]:.2f}")
    M.export(M.keys(CFGS[tn]), P_FULL, "segment_corrections_mo.pkl")
    pd.Series({"structure": name(CFGS[tn]), **{s: NAMES[v] for s, v in BASE_FULL[1].items()}}).to_csv(M.A_ / "public_transfer_choice.csv")
    print(pd.DataFrame(ch).to_string())
    print("\nBest 10 structures by the all-county score (mode C):\n" + cfdf.head(10)[["structure", "C_allcounty_cv", "C_inner_mean"]].round(3).to_string())
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
