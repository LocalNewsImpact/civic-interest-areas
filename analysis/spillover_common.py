"""Definitions shared by the spillover scripts, so the outlet set, the market counts, the home rule and the fit cannot
drift between them. Missouri, March 2026.

CAMPUS -- student newspapers of a college or university: the registry owner is the institution and the outlet is
  print or digital, published for its campus. Not local news for any county, as The Maneater (EXCLUDE) is: out of the
  spillover outcome, the fit, the scoring and every county count (2026-10-24). Kept: university-licensed public
  broadcasters (KBIA, KCUR, KRCU, KSMU, KXCV, STL Public Radio) and the School of Journalism's community newsrooms
  (Columbia Missourian, Boone County Journal, KOMU), which publish for the general public. Defined in
  excluded_outlets.py and part of EXCLUDE, so coverage and the maps leave them out too.

MARKET -- the outlets a county had in March: registry status active, or closed since but publishing in March
  (march_articles > 0); not EXCLUDE, not CAMPUS. One rule for the saturation counts (log_print and the other candidate
  counts), the crowded-county test and the search script. Statuses that say what an entry is (duplicate, replica,
  merged, not_local_news, legal, shopper, ...) stay out.

HOME -- the counties a story can be about and still be home coverage, for every outlet:
  1. the county the outlet is filed under (St. Louis city and county one unit), or HOME_COUNTY where it applies;
  2. every other county that holds part of the outlet's registry city (Census 2020 base population > 0 in the
     place-in-county rows, census_dl/ref/sub-est2024_29.csv, SUMLEV 157): Kansas City -> Jackson, Clay, Platte, Cass;
     Joplin -> Jasper, Newton; Sikeston -> Scott, New Madrid; Excelsior Springs -> Clay, Ray; ...
  3. a same-named city adjoining it across the state line: Kansas City, Kansas (Wyandotte) for Kansas City, Missouri
     (the authors' 2026-10-17 decision, now one case of the rule). No other Missouri city has one.
  HOME_COUNTY outlets (published in one county, covering another) take only their HOME_COUNTY: the office's city is
  not their market. Johnson County, Kansas and St. Clair and Madison counties, Illinois are not home for anyone: no
  outlet's city lies in them.

DENOMINATOR (a definition) -- every placed story stays in the denominator: a story with no central county, and a story
  centred out of state more than 60 miles from the home county, count 0 unless they mention another county.

WEIGHTS (definitions, set by the authors; not selected) -- a story centred in another county counts 1, a story centred
  at home that mentions another county counts MENTION_WEIGHT 0.5, a home-only story 0; a Sports story (CIN) counts
  SPORTS_WEIGHT 0.5 of that. Other weights are reported only as a sensitivity table.

FREQUENCY -- coverage/source_frequency.csv (outlet|frequency, from the sources registry). Codes filled 2026-10-24 from
  the Missouri Official Manual 2025-2026 newspaper list (MizzouNewsCrawler src/lookups/mo_bluebook_newspapers_2025_2026.csv,
  `schedule`), matched by host and name, where the code was blank: weekly -- The Banner Press, The Cash-Book Journal,
  Aurora Advertiser, St. Louis Business Journal, Tribune and Times, Cedar County Republican and Stockton Journal,
  Chariton Marquee, Kahoka Hometown Journal, Clinton County Leader, Plattsburg, Springfield Business Journal,
  Hermitage Index, Tipton Times, Community News; bi-weekly -- West & Mid Rivers Newsmagazine. Checked and kept:
  The Maryville Daily Forum (Manual: "Maryville Forum", Thurs.) and The Daily/Dexter Statesman ("The Statesman",
  Wed.) are weeklies despite the masthead; Richmond Daily News ("Richmond News", Fri.) likewise.
"""
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from excluded_outlets import CAMPUS, EXCLUDE, HOME_COUNTY, county_dma, home_fips, registry  # noqa: E402,F401

root = Path(__file__).resolve().parents[1]
unit = lambda f: "29189" if f == "29510" else f

NOT_LOCAL = EXCLUDE   # includes CAMPUS (excluded_outlets.py)

MENTION_WEIGHT = 0.5
SPORTS_WEIGHT = 0.5
# MODEL PROCEDURE (authors, 2026-10-24; one procedure for every model in the project):
#   1. Core terms are set by theory and tested as a block, not one at a time.
#   2. Hypothesis terms are stated in advance and reported with coefficient and held-out gain whatever the result.
#   GAIN (every script): held-out mean miss without the term(s) minus with them, points; positive = the term helps.
#   3. Exploratory additions are adopted only if the NESTED procedure's held-out gain (selection repeated inside each
#      fold without the held-out county) has a county-paired bootstrap 95% interval excluding zero (multiplicity guard;
#      spillover_rule_selection.py). Selection code breaks ties toward fewer terms.
#   4. One primary metric per model, declared. Spillover: mean absolute held-out miss on the fitted outlets (each
#      county's outlets predicted by a fit without that county); the median is reported beside it.
# SPILLOVER: hypothesis terms, pre-specified -- broadcaster (TV and radio reach beyond their county) and print and
# digital outlets in the county, log(1 + count) (saturation: the more outlets, the less each covers beyond it). They
# are not selected by any rule here. They were first found by a search; the honest error of that search is its nested
# figure (spillover_nested_selection.py, search B). Figures: spillover_outlets.py and spillover_rule_selection.py output.
FINAL = "rate ~ broadcast + log_print"
PER_10K = "rate ~ broadcast + outlets_per_10k + log_print"
BORDER_FORM = "rate ~ broadcast + log_border_np + log_print"
WITH_CROWDED = "rate ~ broadcast + crowded_weekly + log_border_np + log_print"
FINAL_ALL_BORDER = "rate ~ broadcast + crowded_weekly + log_border_mi + log_print"
NOT_FITTED = frozenset({"Three Rivers Publishing"})   # three newspapers' stories under one name
FIT_FLOOR = 20
SCORE_FLOOR = 10
STUDY = (("Audrain", "29007"), ("Boone", "29019"), ("Osage", "29151"))
TWIN_CITY = {("kansas city", "MO"): frozenset({"20209"})}


def frequency():
    rows = [l.rstrip("\n").rsplit("|", 1) for l in open(root / "coverage/source_frequency.csv") if "|" in l]
    return pd.DataFrame(rows, columns=["outlet", "f"]).drop_duplicates("outlet").set_index("outlet").f.str.strip()


def market():
    """MARKET outlets with `u` (county unit) and `freq`."""
    r = registry()
    march = pd.to_numeric(r.march_articles, errors="coerce").fillna(0)
    r = r[((r.status == "active") | ((r.status == "closed") & (march > 0))) & ~r.outlet.isin(NOT_LOCAL)].copy()
    r["u"] = r.county_fips.fillna("").map(unit)
    r["freq"] = r.outlet.map(frequency()).fillna("")
    r["is_print"] = r.type.str.contains("print|newspaper", na=False)
    r["is_print_digital"] = r.type.str.contains("print|newspaper|digital", na=False)
    r["is_tv"] = r.type.str.contains("video", na=False)
    return r


def outlet_rows(outlets_fips):
    """Registry row per outlet, the one filed in the outlet's county unit where a name repeats.
    outlets_fips: DataFrame with outlet, fips (unit)."""
    reg = registry()
    reg["u"] = reg.county_fips.fillna("").map(unit)
    reg = reg.drop(columns="fips").merge(outlets_fips[["outlet", "fips"]].drop_duplicates("outlet"), on="outlet")
    return reg[(reg.u == reg.fips) | ~reg.outlet.duplicated(keep=False)].drop_duplicates("outlet").set_index("outlet")


def _city_counties():
    pe = pd.read_csv(root / "census_dl/ref/sub-est2024_29.csv", dtype=str, encoding="latin-1")
    p = pe[(pe.SUMLEV == "157") & (pe.ESTIMATESBASE2020.astype(int) > 0)].copy()
    p["name"] = p.NAME.str.replace(r" \(pt\.\)$", "", regex=True).str.replace(r" (city|town|village)$", "", regex=True).str.lower()
    out = defaultdict(set)
    for n, c in zip(p.name, p.STATE + p.COUNTY):
        out[n].add(unit(c))
    return out


_CITY = None


def home_set(outlet, filed_unit, city, state="MO"):
    """HOME: the county units a story can be centred in and still be home coverage for this outlet."""
    global _CITY
    if outlet in HOME_COUNTY:
        return frozenset({unit(HOME_COUNTY[outlet])})
    if _CITY is None:
        _CITY = _city_counties()
    c = (city or "").strip().lower()
    s = {filed_unit}
    if state == "MO" and filed_unit in _CITY.get(c, set()):
        s |= _CITY[c]
    s |= TWIN_CITY.get((c, state), frozenset())
    return frozenset(s)


_REG = None


def outlet_home(outlet, filed):
    """(home unit, HOME set) for an outlet filed under county `filed`: HOME_COUNTY applied, the registry city of the row
    filed in that county (else any row of the outlet), home_set's rule."""
    global _REG
    if _REG is None:
        _REG = registry()
        _REG["u"] = _REG.county_fips.fillna("").map(unit)
    i = unit(home_fips(outlet, filed))
    rr = _REG[_REG.outlet == outlet]
    if (rr.u == i).any():
        rr = rr[rr.u == i]
    city, st = (rr.city.iloc[0], rr.state.iloc[0]) if len(rr) else ("", "MO")
    return i, home_set(outlet, i, city, st)


# ---- fitting: one IRLS for the fractional logit (quasi-binomial), used by the loops ----------------------------------
def irls(X, y, it=100):
    """Fractional-logit coefficients by Newton steps; least squares where X'WX is singular."""
    b = np.zeros(X.shape[1])
    for _ in range(it):
        mu = 1 / (1 + np.exp(-np.clip(X @ b, -30, 30)))
        H = (X * (mu * (1 - mu))[:, None]).T @ X
        gr = X.T @ (y - mu)
        try:
            step = np.linalg.solve(H, gr)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(H, gr, rcond=None)[0]
        b = b + step
        if np.max(np.abs(step)) < 1e-10:
            break
    return b


def design(d, terms):
    return np.column_stack([np.ones(len(d))] + [d[t].to_numpy(float) for t in terms])


def terms_of(formula):
    rhs = formula.split("~", 1)[1].strip()
    return [] if rhs == "1" else [t.strip() for t in rhs.split("+")]


def predict(train, test, terms, y="rate"):
    b = irls(design(train, terms), train[y].to_numpy(float))
    return 1 / (1 + np.exp(-design(test, terms) @ b))


def loo(terms, fit, score=None, y="rate"):
    """Each county's outlets in `score` predicted by a fit on `fit` without that county. Returns the errors."""
    score = fit if score is None else score
    e = []
    for c in score.fips.unique():
        te = score[score.fips == c]
        e.append(predict(fit[fit.fips != c], te, terms, y) - te[y].to_numpy(float))
    return np.concatenate(e)


def skill(terms, fit, score=None, y="rate"):
    """Held-out mean and median absolute miss (points), skill against intercept-only (1 - MAE/MAE0), out-of-sample R^2."""
    e, e0 = loo(terms, fit, score, y), loo([], fit, score, y)
    return {"mean": 100 * np.abs(e).mean(), "median": 100 * np.median(np.abs(e)),
            "skill": 1 - np.abs(e).mean() / np.abs(e0).mean(), "r2": 1 - (e ** 2).mean() / (e0 ** 2).mean(), "n": len(e)}


def paired_interval(e_with, e_without, fips, B=1999, seed=20261024):
    """GAIN = mean held-out miss WITHOUT minus WITH (points; positive: `with` predicts better), with a county-paired
    bootstrap percentile 95% interval: counties resampled with replacement, both error sets of a county kept together.
    `kept`: the interval lies above zero."""
    e_with, e_without, fips = np.asarray(e_with), np.asarray(e_without), np.asarray(fips)
    keys, inv = np.unique(fips, return_inverse=True)
    dsum, n = np.bincount(inv, e_without - e_with), np.bincount(inv)
    draws = np.random.default_rng(seed).integers(0, len(keys), (B, len(keys)))
    boot = dsum[draws].sum(1) / n[draws].sum(1)
    return {"gain": 100 * (e_without.mean() - e_with.mean()), "lo": 100 * np.quantile(boot, .025),
            "hi": 100 * np.quantile(boot, .975), "median_with": 100 * np.median(e_with),
            "median_without": 100 * np.median(e_without), "kept": bool(np.quantile(boot, .025) > 0)}


def loo_fips(score):
    """County of each error, in the order loo() returns them."""
    return np.concatenate([score.fips[score.fips == c].to_numpy() for c in score.fips.unique()])


def paired_gain(terms_with, terms_without, fit, score=None, B=1999, seed=20261024):
    """Held-out gain of a term: mean absolute miss without it minus with it (positive = the term helps), both by leaving
    each county out, and a county-paired bootstrap percentile 95% interval (B draws). Also the median of each."""
    score = fit if score is None else score
    ew, eo = np.abs(loo(terms_with, fit, score)), np.abs(loo(terms_without, fit, score))
    return paired_interval(ew, eo, loo_fips(score), B, seed)


def cluster_inference(d, formula, B=1999, seed=20261024):
    """Coefficients with county-cluster inference.
    se_crv3, p_cluster_t: CRV3 -- the cluster jackknife, V = (G-1)/G * sum_g (b_(g) - b_bar)(b_(g) - b_bar)', each b_(g)
      refitted without county g; p from t with G-1 df. The inference used for every reported p.
    se_crv1, p_crv1: the sandwich with small-cluster correction G/(G-1)(N-1)/(N-K), for comparison.
    ci_lo, ci_hi: pairs county-cluster bootstrap (B draws, percentile 95%); draws in which a term does not vary are
      dropped for it (boot_dropped)."""
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    grp = pd.factorize(d.fips)[0]
    m = smf.glm(formula, d, family=sm.families.Binomial()).fit(
        cov_type="cluster", cov_kwds={"groups": grp, "use_correction": True})
    G = len(set(grp))
    terms = terms_of(formula)
    X, y = design(d, terms), d.rate.to_numpy(float)
    fips = d.fips.to_numpy()
    idx = {c: np.flatnonzero(fips == c) for c in d.fips.unique()}
    jk = np.array([irls(X[fips != c], y[fips != c]) for c in idx])
    se3 = np.sqrt((G - 1) / G * ((jk - jk.mean(0)) ** 2).sum(0))
    p3 = 2 * stats.t.sf(np.abs(m.params.to_numpy() / se3), G - 1)
    p1 = 2 * stats.t.sf(np.abs(m.params / m.bse), G - 1)
    cl = list(idx)
    rng = np.random.default_rng(seed)
    draws, dropped = [], np.zeros(len(terms) + 1, int)
    for _ in range(B):
        rows = np.concatenate([idx[c] for c in rng.choice(cl, len(cl), replace=True)])
        Xb = X[rows]
        b = irls(Xb, y[rows])
        flat = np.r_[False, Xb[:, 1:].std(0) == 0]
        b[flat] = np.nan; dropped += flat
        draws.append(b)
    bs = pd.DataFrame(draws, columns=m.params.index) if draws else pd.DataFrame(np.nan, index=[0], columns=m.params.index)
    out = pd.DataFrame({"coef": m.params, "se_crv3": se3, "p_cluster_t": p3, "se_crv1": m.bse, "p_crv1": p1,
                        "ci_lo": bs.quantile(.025), "ci_hi": bs.quantile(.975),
                        "boot_sign_flip": [(np.sign(bs[k].dropna()) != np.sign(m.params[k])).mean() for k in m.params.index],
                        "boot_dropped": dropped})
    return m, out, G


def wcorr(x, y, w=None):
    """Pearson r, and p from the (weighted) least-squares slope; n."""
    import statsmodels.api as sm
    x, y = np.asarray(x, float), np.asarray(y, float)
    w = np.ones(len(x)) if w is None else np.asarray(w, float)
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    r = np.average((x - mx) * (y - my), weights=w) / math.sqrt(np.average((x - mx) ** 2, weights=w) * np.average((y - my) ** 2, weights=w))
    p = sm.WLS(y, sm.add_constant(x), weights=w).fit().pvalues[1]
    return r, p, len(x)
