"""Scores shared by the public-model scripts (score_segments.py, score_ks.py, public_stage1_nested.py,
public_adjusted_nested.py, public_adjusted_model.py).

Two metrics, both per home county and then averaged over the counties of a class (every county weighs the same):
  share-weighted error  100 x sum_j a_j |p_j - a_j| (points); a = Advan out-of-county destination shares, p = model.
                        It scales with the concentration of a county's travel: if every pair is missed by the same
                        relative amount r, the error is r x HHI (sum of a_j^2), so a county sending 70% to one hub
                        scores worse than a county spreading over ten destinations for the same relative miss.
  log-ratio error       mean over the county's pairs with a_j >= 1% of |ln(p_j / a_j)|, p floored at 0.01%.
                        Scale-free: invariant to concentration, symmetric in over- and under-prediction, and it counts
                        the 1-5% pairs the share-weighted error barely sees. Chosen over error / HHI (still dominated by
                        the largest pair) and KL divergence (share-weighted again, infinite where p = 0). The 1% floor
                        keeps the smallest Advan pairs, where few devices make the observed share itself noisy, out.
                        exp(value) is the typical factor by which a pair's share is missed (0.41 -> x1.5).
Comparisons between models: county-paired bootstrap (the same counties drawn for both models), 2,000 draws, 95%
percentile interval of the difference in the class mean; the all-county interval resamples within each class
(stratified), so the class mix stays fixed.
"""
import numpy as np
import pandas as pd

RATIO_FLOOR = 0.01       # pairs with Advan share >= 1% enter the log-ratio error
P_FLOOR = 1e-4           # model share floor (0.01%) inside the log
N_BOOT = 2000


def per_county(home, a, p):
    """Per-county share-weighted error (points) and log-ratio error; home, a, p aligned arrays (a, p sum to 1 per home)."""
    home = np.asarray(home); a = np.asarray(a, float); p = np.asarray(p, float)
    sw = pd.Series(100 * a * np.abs(p - a)).groupby(home).sum()
    m = a >= RATIO_FLOOR
    lr = pd.Series(np.abs(np.log(np.maximum(p[m], P_FLOOR) / a[m]))).groupby(home[m]).mean()
    return pd.DataFrame({"sw": sw, "lr": lr.reindex(sw.index)})


def renorm(home, x):
    x = np.asarray(x, float)
    s = pd.Series(x).groupby(np.asarray(home)).transform("sum").values
    return np.where(s > 0, x / np.where(s > 0, s, 1), 0.0)


def boot_diff(d, groups, n=N_BOOT, seed=0):
    """d: per-county differences (Series indexed by county); groups: Series county -> class. Returns
    {class: (mean, lo, hi, n)} and 'all' (stratified by class)."""
    rng = np.random.default_rng(seed)
    out = {}
    g = groups.reindex(d.index)
    draws_by = {}
    for c in g.dropna().unique():
        v = d[g == c].dropna().values
        if len(v) == 0:
            continue
        b = v[rng.integers(0, len(v), (n, len(v)))].mean(1)
        draws_by[c] = (b, len(v))
        out[c] = (v.mean(), *np.percentile(b, [2.5, 97.5]), len(v))
    tot = sum(k for _, k in draws_by.values())
    ball = sum(b * k for b, k in draws_by.values()) / tot
    out["all"] = (d.reindex(g.dropna().index).mean(), *np.percentile(ball, [2.5, 97.5]), tot)
    return out


def fmt_ci(t, nd=2):
    m, lo, hi, _ = t
    star = "" if lo <= 0 <= hi else "*"
    return f"{m:+.{nd}f} [{lo:+.{nd}f}, {hi:+.{nd}f}]{star}"


def boot_share_closed(e_from, e_to, e_ref, groups, n=N_BOOT, seed=0):
    """Share of the gap from e_from to the benchmark e_ref that e_to closes: (mean e_from - mean e_to) /
    (mean e_from - mean e_ref), per class and all (stratified), with a county-paired bootstrap 95% interval.
    Inputs: per-county Series on the same index."""
    rng = np.random.default_rng(seed)
    g = groups.reindex(e_from.index)
    out, parts = {}, {}
    for c in g.dropna().unique():
        idx = np.flatnonzero((g == c).values)
        f, t, r = e_from.values[idx], e_to.values[idx], e_ref.values[idx]
        b = rng.integers(0, len(idx), (n, len(idx)))
        num, den = (f[b] - t[b]).mean(1), (f[b] - r[b]).mean(1)
        parts[c] = (num * len(idx), den * len(idx))
        out[c] = ((f - t).mean() / (f - r).mean(), *np.percentile(num / den, [2.5, 97.5]), len(idx))
    num = sum(p[0] for p in parts.values()); den = sum(p[1] for p in parts.values())
    m = g.notna().values
    out["all"] = ((e_from[m] - e_to[m]).mean() / (e_from[m] - e_ref[m]).mean(), *np.percentile(num / den, [2.5, 97.5]), int(m.sum()))
    return out


def fmt_pct(t):
    m, lo, hi, _ = t
    return f"{100 * m:.0f}% [{100 * lo:.0f}, {100 * hi:.0f}]"
