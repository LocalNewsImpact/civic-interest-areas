"""Stage 1, the public model's setting per county class, chosen without the county it is scored on.

Candidates: every Missouri build of public_travel_tiers.py (analysis/public_model_pairs_tiers<TAG>.csv) other than the
assembled by-class files, the Kansas builds (_20_) and the regular-travel builds (_r*): 53 settings, each built from
public data only. For each class (score_segments.py's five: small rural, independent towns, commuter rings of the
Kansas City and St. Louis metros, commuter rings of regional hubs, hubs) the setting is the one with the lowest mean
share-weighted error against Advan:
  in-sample   chosen on all the class's counties and scored on the same counties (what the log reported, 4.30-4.34)
  nested      leave one county out: chosen on the class's other counties, scored on the held-out one (reported)
Advan therefore chooses among settings but sets no parameter. Scored on the common destination set
(public_adjusted_model.py), share-weighted error and log-ratio error (public_scoring.py).

Outputs: analysis/public_stage1_choice.csv (the setting chosen on all counties of each class -- the one Kansas takes;
and each county's nested choice), analysis/public_stage1_nested_pairs.csv (county shares, nested and in-sample).
"""
import glob
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
os.environ.setdefault("BASE", "public_model_pairs_tiers_g_40_sales.csv")
import public_adjusted_model as M  # noqa: E402
from public_scoring import per_county  # noqa: E402

CACHE = M.A_ / "public_stage1_variants.npz"


def candidate_files():
    fs = sorted(glob.glob(str(M.A_ / "public_model_pairs_tiers*.csv")))
    return [f for f in fs if "_20_" not in f and "byclass" not in f and "/public_model_pairs_tiers_r" not in f]


def load_variants():
    """names, V (T rows x variants, tract-normalised combined_share), aligned with M.T."""
    fs = candidate_files()
    names = [Path(f).stem.replace("public_model_pairs_tiers", "") or "(none)" for f in fs]
    if CACHE.exists() and CACHE.stat().st_mtime > max(os.path.getmtime(f) for f in fs):
        z = np.load(CACHE, allow_pickle=True)
        if list(z["names"]) == names and z["V"].shape[0] == len(M.T):
            return names, z["V"]
    V = np.zeros((len(M.T), len(fs)))
    for n, f in enumerate(fs):
        P = pd.read_csv(f, dtype={"tract": str, "j": str, "home": str}, usecols=["tract", "home", "j", "combined_share"])
        P = P[(P.j.str[:2] == "29") & (P.home != P.j)].reset_index(drop=True)
        assert len(P) == len(M.T) and (P.tract.values == M.T.tract.values).all() and (P.j.values == M.T.j.values).all(), f
        V[:, n] = M.tract_norm(P.combined_share.values.astype(float))
    np.savez_compressed(CACHE, names=np.array(names), V=V)
    return names, V


def county_errors(V):
    """Per-county share-weighted and log-ratio error of every variant (common set): two DataFrames county x variant."""
    sw, lr, P = {}, {}, {}
    for n in range(V.shape[1]):
        p = M.roll(V[:, n])
        e = per_county(M.S.i.values, M.a, p)
        sw[n], lr[n], P[n] = e.sw, e.lr, p
    return pd.DataFrame(sw), pd.DataFrame(lr), P


def choose(E, counties):
    """Variant index with the lowest mean share-weighted error over the counties given."""
    return int(E.loc[list(counties)].mean().values.argmin())


def main():
    names, V = load_variants()
    Esw, Elr, P = county_errors(V)
    seg = M.SEG_OF
    rows, full = [], {}
    p_nest = np.zeros(M.NS); p_ins = np.zeros(M.NS)
    for s in M.SEGS:
        cs = list(seg.index[seg == s])
        b = choose(Esw, cs); full[s] = names[b]
        for c in cs:
            bn = choose(Esw, [x for x in cs if x != c])
            m = M.S.i.values == c
            p_nest[m] = P[bn][m]; p_ins[m] = P[b][m]
            rows.append({"segment": s, "county": c, "nested_choice": names[bn], "insample_choice": names[b]})
    ch = pd.DataFrame(rows)
    pd.concat([pd.DataFrame([{"segment": s, "county": "ALL", "nested_choice": "", "insample_choice": full[s]} for s in M.SEGS]), ch]).to_csv(
        M.A_ / "public_stage1_choice.csv", index=False)
    pd.DataFrame({"i": M.S.i, "j": M.S.j, "common": M.COMMON, "advan": M.a, "fitted": M.adv, "public_nested": p_nest,
                  "public_insample": p_ins}).to_csv(M.A_ / "public_stage1_nested_pairs.csv", index=False)
    en, ei, ef = (per_county(M.S.i.values, M.a, p) for p in (p_nest, p_ins, M.adv))
    print(f"{len(names)} candidate settings; common destination set: Advan share outside {100 * M.outside.mean():.2f}% "
          f"per county on average")
    print("| Class (counties) | setting chosen on all counties | in-sample | nested (LOO) | Advan-fitted |\n|---|---|---:|---:|---:|")
    cell = lambda e, m: f"{e.sw[m].mean():.2f} / {e.lr[m].mean():.2f}"
    for s in M.SEGS:
        m = seg.reindex(en.index) == s
        alt = ch[ch.segment == s].nested_choice.value_counts()
        print(f"| {s} ({int(m.sum())}) | {full[s]} (nested picks: {', '.join(f'{k} {v}' for k, v in alt.items())}) | {cell(ei, m)} | {cell(en, m)} | {cell(ef, m)} |")
    allm = pd.Series(True, index=en.index)
    print(f"| all ({len(en)}) | | {cell(ei, allm)} | {cell(en, allm)} | {cell(ef, allm)} |")
    print("(share-weighted error / log-ratio error)")


if __name__ == "__main__":
    main()
