"""Does the coverage model's metro / nonmetro elasticity gap reflect rurality, or newsroom size and outlet type?

The adopted coverage model (coverage_model.py) has log visits x nonmetro newsroom county as a hypothesis term (metro
0.50, nonmetro 0.26). Nonmetro counties also have fewer and smaller newsrooms, fewer dailies and few TV stations, so
the term may measure newsroom size or type, not rurality. Data build, controls, fixed effects, PPML, newsroom-county
clustering and held-out scoring are coverage_model.py's (its definitions are executed from its source, without its
model runs). All outlets.

Newsroom-county measures (interacted with log visits; their levels are absorbed by the newsroom-county effects):
  nonmetro       USDA RUCC 4-9 (the adopted term)
  log_outlets    log(1 + active local outlets filed in the county), pinned registry (excluded_outlets.registry():
                 status active, Missouri, not EXCLUDE, HOME_COUNTY applied), collected or not -- a size measure not
                 built from the stories
  has_daily      an active registry outlet in the county publishes daily (coverage/source_frequency.csv; outlets with
                 no recorded frequency count as not daily)
  has_tv         an active registry video broadcaster in the county
  log_stories    log(1 + all March stories by the county's newsrooms, home and away). SECONDARY: built from the same
                 stories as the outcome, so mechanically related to it; reported, not used in the combined model
Tests
  1. Each measure x log visits alone, and size + type together with and without nonmetro; implied elasticities for
     profiles; held out (coverage_model.heldout: 8 folds of newsroom counties, mean absolute share error per county;
     PRIMARY destinations with 1%+ of visits) against the adopted model, county-paired 95% intervals.
  2. Outlet as the source unit: stories by outlet o about county j (j outside its home county), outlet and destination
     fixed effects, the home county's controls and log visits; elasticity by outlet type (non-daily print, daily
     print, digital native, broadcast), and metro / nonmetro within each type. Errors clustered by newsroom county.
  3. Matched on output: newsroom counties inside the overlap of metro and nonmetro counties' out-of-county story
     pairs (and, separately, of registry outlet counts); the adopted model refitted on them.
Only model-level statistics and Audrain / Boone / Osage are printed; other counties' figures are appended to
advan-notes/statewide_and_other_results.md.
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_src = (HERE / "coverage_model.py").read_text()
exec(compile(_src[:_src.index("# ---- outlets outside Missouri")], str(HERE / "coverage_model.py"), "exec"))
from excluded_outlets import registry  # noqa: E402

NOTES = Path("/Users/kiesowd/VSCode/advan-notes/statewide_and_other_results.md")
STUDY = {"29007": "Audrain", "29019": "Boone", "29151": "Osage"}
CL = lambda p: dict(cov_type="cluster", cov_kwds={"groups": pd.factorize(p.i)[0]})  # noqa: E731

# ---- newsroom-county measures ------------------------------------------------------------------------------------------
rows = [l.rstrip("\n").rsplit("|", 1) for l in open(root / "coverage/source_frequency.csv") if "|" in l]
freq = {o.strip(): f.strip() for o, f in rows}
reg = registry()
reg = reg[(reg.status == "active") & (reg.state == "MO") & ~reg.outlet.isin(EXCLUDE) & reg.county_fips.notna()]
n_outlets = reg.groupby("county_fips").size()
daily_c = set(reg[reg.outlet.map(freq) == "daily"].county_fips)
tv_c = set(reg[reg.type.str.replace("_", " ").str.contains("video broadcast", na=False)].county_fips)
stories_c = Counter(newsroom_fips(a) for a in data["articles"] if newsroom_fips(a))

# ---- county pairs, as coverage_model.py builds them (all outlets) --------------------------------------------------------
pairs = gt.all_pairs()
pairs["visits"] = gt.travel_visits(pairs, gt.MONTHS)
arts = [a for a in data["articles"] if newsroom_fips(a)]
n = Counter()
for a in arts:
    i = newsroom_fips(a)
    for j in a["counties"]:
        if j.startswith("29") and j != i:
            n[(i, j)] += 1
p = pairs[pairs.i.isin({newsroom_fips(a) for a in arts})].copy()
p["stories"] = [n.get((i, j), 0) for i, j in zip(p.i, p.j)]
p = p[p.groupby("i").stories.transform("sum") > 0].reset_index(drop=True)
Xd = design(p)
X, O = Xd[FACTORS], Xd[[c for c in Xd.columns if c.startswith(("o_", "d_"))]]
y = p.stories.astype(float)
pos = (p.visits > 0).values
lv = np.where(pos, np.log(p.visits.where(pos, 1.0)), 0.0)
Z = pd.DataFrame({"nonmetro": 1 - cov.metro.reindex(p.i).values,
                  "log_outlets": np.log1p(n_outlets.reindex(p.i).fillna(0).values),
                  "has_daily": p.i.isin(daily_c).astype(float).values,
                  "has_tv": p.i.isin(tv_c).astype(float).values,
                  "log_stories": np.log1p(np.array([stories_c[i] for i in p.i], float))})
C = Z.groupby(p.i.values).first()                     # one row per newsroom county
C["out_pairs"] = p.groupby("i").stories.sum()
C["outlets"] = n_outlets.reindex(C.index).fillna(0).astype(int)


def model(terms):
    """Adopted controls + log visits + zero-visit indicator + log visits x each of `terms` + fixed effects."""
    T = X.assign(log_visits=lv, zero_visits=(~pos).astype(float))
    for t in terms:
        T[f"lv_x_{t}"] = lv * Z[t].values
    return pd.concat([T, O], axis=1)


def elast(m, prof):
    """Elasticity and s.e. for a profile {term: value} (linear combination of log_visits and the interactions)."""
    names = ["log_visits"] + [f"lv_x_{t}" for t in prof]
    w = np.array([1.0] + list(prof.values()))
    V = m.cov_params().loc[names, names].values
    return float(m.params[names].values @ w), float(np.sqrt(w @ V @ w))


print(f"# Newsroom counties: {len(C)} ({int((C.nonmetro == 0).sum())} metro, {int(C.nonmetro.sum())} nonmetro); "
      f"{int(y.sum()):,} out-of-county story-county pairs")
print("Measures by metro / nonmetro (medians or shares of newsroom counties):")
g = C.groupby(C.nonmetro.map({0: "metro", 1: "nonmetro"}))
print(pd.DataFrame({"counties": g.size(), "active outlets (median)": g.outlets.median(),
                    "has a daily": g.has_daily.mean().round(2), "has TV": g.has_tv.mean().round(2),
                    "out-of-county story pairs (median)": g.out_pairs.median()}).to_string())
print("Correlation across newsroom counties with nonmetro: "
      + ", ".join(f"{t} {np.corrcoef(C.nonmetro, C[t])[0, 1]:+.2f}" for t in ("log_outlets", "has_daily", "has_tv", "log_stories")))

# ---- test 1 ------------------------------------------------------------------------------------------------------------
specs = {"adopted: x nonmetro": ["nonmetro"], "x log outlets (registry)": ["log_outlets"], "x has daily": ["has_daily"],
         "x has TV": ["has_tv"], "x log stories (SECONDARY, built from the outcome)": ["log_stories"],
         "x outlets + daily + TV (no nonmetro)": ["log_outlets", "has_daily", "has_tv"],
         "x nonmetro + outlets + daily + TV": ["nonmetro", "log_outlets", "has_daily", "has_tv"]}
fits, E = {}, {}
for k, t in specs.items():
    Xm = model(t)
    fits[k] = poisson(y, Xm, **CL(p))
    E[k] = heldout(y, Xm, p, fits[k].params)
E0 = E["adopted: x nonmetro"]
print("\n## 1. Size and type in place of, and beside, nonmetro (interactions with log visits; clustered s.e.)")
print("Held-out error, points; change = model - adopted, county-paired 95% (negative = lower error than adopted)")
print("| Model | log visits | x nonmetro | x log outlets | x has daily | x has TV | x log stories | Primary (1%+ of visits) | "
      "Change | All destinations | Change |\n|---|---|---|---|---|---|---|---:|---:|---:|---:|")
for k, m in fits.items():
    cells = []
    for t in ["log_visits", "lv_x_nonmetro", "lv_x_log_outlets", "lv_x_has_daily", "lv_x_has_tv", "lv_x_log_stories"]:
        cells.append(f"{m.params[t]:+.3f} ({m.bse[t]:.3f})" if t in m.params else "")
    for col in ("travel", "all"):
        e = E[k][col]
        cells.append(f"{e.mean():.3f}")
        if k == "adopted: x nonmetro":
            cells.append("—")
        else:
            d = e - E0[col]
            lo, hi = bt(d)
            cells.append(f"{d.mean():+.3f} [{lo:+.3f}, {hi:+.3f}]")
    print(f"| {k} | " + " | ".join(cells) + " |")
med = lambda mask: float(np.log1p(C.outlets[mask].median())) if mask.any() else np.log1p(1)  # noqa: E731
profiles = {
    "one weekly only (1 outlet, no daily, no TV)": dict(log_outlets=np.log1p(1), has_daily=0, has_tv=0),
    "daily, no TV (median outlets of such counties)": dict(log_outlets=med((C.has_daily == 1) & (C.has_tv == 0)), has_daily=1, has_tv=0),
    "daily + TV (median outlets of such counties)": dict(log_outlets=med((C.has_daily == 1) & (C.has_tv == 1)), has_daily=1, has_tv=1),
}
print("\nImplied elasticities by profile (s.e.); counties in each profile, metro / nonmetro:")
print("| Profile | Counties (metro / nonmetro) | Outlets x size + type model | Metro, full model | Nonmetro, full model |"
      "\n|---|---|---|---|---|")
mt, mf = fits["x outlets + daily + TV (no nonmetro)"], fits["x nonmetro + outlets + daily + TV"]
for lab, pr in profiles.items():
    d_, t_ = pr["has_daily"], pr["has_tv"]
    mask = (C.has_daily == d_) & (C.has_tv == t_) & ((C.outlets <= 1) if lab.startswith("one") else True)
    cnt = f"{int((mask & (C.nonmetro == 0)).sum())} / {int((mask & (C.nonmetro == 1)).sum())}"
    a = elast(mt, pr)
    b0, b1 = elast(mf, {"nonmetro": 0, **pr}), elast(mf, {"nonmetro": 1, **pr})
    print(f"| {lab} | {cnt} | {a[0]:.2f} ({a[1]:.2f}) | {b0[0]:.2f} ({b0[1]:.2f}) | {b1[0]:.2f} ({b1[1]:.2f}) |")
print("\nStudy counties: profile and implied elasticity")
print("| County | Nonmetro | Active outlets | Daily | TV | Adopted (x nonmetro) | Size + type model | Full model |\n|---|---|---|---|---|---|---|---|")
for f, nm in STUDY.items():
    if f not in C.index:
        continue
    r = C.loc[f]
    pr = dict(log_outlets=r.log_outlets, has_daily=r.has_daily, has_tv=r.has_tv)
    print(f"| {nm} | {int(r.nonmetro)} | {int(r.outlets)} | {int(r.has_daily)} | {int(r.has_tv)} | "
          f"{elast(fits['adopted: x nonmetro'], {'nonmetro': r.nonmetro})[0]:.2f} | {elast(mt, pr)[0]:.2f} | "
          f"{elast(mf, {'nonmetro': r.nonmetro, **pr})[0]:.2f} |")

# ---- test 2: outlet as the source unit -----------------------------------------------------------------------------------
def otype(a):
    t = (a["publisher_type"] or "").replace("_", " ")
    if "broadcast" in t:
        return "broadcast"
    if "digital" in t:
        return "digital native"
    f_ = freq.get(a["publisher"], "")
    return "daily print" if f_ == "daily" else ("non-daily print" if f_ else None)


home = {a["publisher"]: newsroom_fips(a) for a in arts}
typ = {a["publisher"]: otype(a) for a in arts}
no = Counter()
for a in arts:
    for j in a["counties"]:
        if j.startswith("29") and j != home[a["publisher"]]:
            no[(a["publisher"], j)] += 1
outl = sorted(o for o in home if typ[o] and sum(v for (o2, _), v in no.items() if o2 == o) > 0)
pi = pairs.set_index(["i", "j"])
q = pd.DataFrame([(o, home[o], j) for o in outl for j in gt.FIPS if j != home[o]], columns=["outlet", "i", "j"])
q["stories"] = [no.get((o, j), 0) for o, j in zip(q.outlet, q.j)]
q["visits"] = pi.visits.reindex(list(zip(q.i, q.j))).values
q["dist"] = pi.dist.reindex(list(zip(q.i, q.j))).values
q["adjacent"] = pi.adjacent.reindex(list(zip(q.i, q.j))).values
Xq = gt.candidates(q)
posq = (q.visits > 0).values
lvq = np.where(posq, np.log(q.visits.where(posq, 1.0)), 0.0)
nmq = 1 - cov.metro.reindex(q.i).values
OF = pd.get_dummies(q.outlet, prefix="out").astype(float)
DF = Xq[[c for c in Xq.columns if c.startswith("d_")]]
types = ["non-daily print", "daily print", "digital native", "broadcast"]
base_q = Xq[FACTORS].assign(zero_visits=(~posq).astype(float))
TA = base_q.copy()
for t in types:
    TA[f"lv_{t}"] = lvq * (q.outlet.map(typ) == t).values
XA = pd.concat([TA, OF, DF], axis=1)
mA = poisson(q.stories.astype(float), XA.loc[:, XA.abs().sum() > 0], **CL(q))
TB = base_q.copy()
for t in types:
    w = (q.outlet.map(typ) == t).values
    TB[f"lv_{t}_metro"] = lvq * w * (1 - nmq)
    TB[f"lv_{t}_nonmetro"] = lvq * w * nmq
XB = pd.concat([TB, OF, DF], axis=1)
mB = poisson(q.stories.astype(float), XB.loc[:, XB.abs().sum() > 0], **CL(q))
VB = mB.cov_params()
print(f"\n## 2. Outlet as the source unit ({len(outl)} outlets with out-of-county stories; outlet and destination fixed "
      f"effects; errors clustered by newsroom county)")
print("| Outlet type | Outlets (metro / nonmetro home) | Elasticity, all | Metro home | Nonmetro home | Nonmetro - metro |"
      "\n|---|---|---|---|---|---|")
for t in types:
    os_ = [o for o in outl if typ[o] == t]
    nm_ = sum(1 - cov.metro[home[o]] for o in os_)
    a, b = f"lv_{t}_metro", f"lv_{t}_nonmetro"
    cell_m = f"{mB.params[a]:.2f} ({mB.bse[a]:.2f})" if (len(os_) - nm_) > 0 else "—"
    cell_n = f"{mB.params[b]:.2f} ({mB.bse[b]:.2f})" if nm_ > 0 else "—"
    diff = "—"
    if nm_ > 0 and len(os_) - nm_ > 0:
        dd = mB.params[b] - mB.params[a]
        sd = np.sqrt(VB.loc[a, a] + VB.loc[b, b] - 2 * VB.loc[a, b])
        diff = f"{dd:+.2f} ({sd:.2f}, p {2 * (1 - __import__('scipy').stats.norm.cdf(abs(dd / sd))):.3f})"
    print(f"| {t} | {len(os_)} ({int(len(os_) - nm_)} / {int(nm_)}) | {mA.params[f'lv_{t}']:.2f} ({mA.bse[f'lv_{t}']:.2f}) | "
          f"{cell_m} | {cell_n} | {diff} |")

# ---- test 3: matched on output -------------------------------------------------------------------------------------------
print("\n## 3. Matched on output: the adopted model on newsroom counties in the metro / nonmetro overlap")
print("| Sample | Newsroom counties (metro / nonmetro) | Metro | Nonmetro | x nonmetro (s.e., p) |\n|---|---|---|---|---|")
matched = {}
for lab, col in (("all newsroom counties", None), ("overlap of out-of-county story pairs", "out_pairs"),
                 ("overlap of active registry outlets", "outlets")):
    keep = C.index
    if col:
        a_, b_ = C[col][C.nonmetro == 0], C[col][C.nonmetro == 1]
        lo, hi = max(a_.min(), b_.min()), min(a_.max(), b_.max())
        keep = C.index[(C[col] >= lo) & (C[col] <= hi)]
        lab = f"{lab} ({lo:g}-{hi:g})"
    matched[lab] = list(keep)
    k = p.i.isin(keep).values
    Xk = model(["nonmetro"])[k]
    Xk = Xk.loc[:, Xk.abs().sum() > 0]
    mk = poisson(y[k], Xk, **CL(p[k]))
    e0, e1 = elast(mk, {"nonmetro": 0}), elast(mk, {"nonmetro": 1})
    print(f"| {lab} | {int((C.loc[keep].nonmetro == 0).sum())} / {int(C.loc[keep].nonmetro.sum())} | {e0[0]:.2f} ({e0[1]:.2f}) | "
          f"{e1[0]:.2f} ({e1[1]:.2f}) | {mk.params['lv_x_nonmetro']:+.3f} ({mk.bse['lv_x_nonmetro']:.3f}, "
          f"p {mk.pvalues['lv_x_nonmetro']:.3f}) |")

# ---- other counties' figures: appended to the notes file -----------------------------------------------------------------
nm = lambda f: county_name(f)  # noqa: E731
with open(NOTES, "a") as fh:
    fh.write("\n## Coverage: newsroom size and type vs nonmetro (coverage_newsroom_size_test.py, 2026-10-25)\n\n")
    fh.write("Newsroom counties by profile (registry active outlets, daily, TV):\n\n| County | Nonmetro | Active outlets | Daily | TV | "
             "Out-of-county story pairs |\n|---|---|---|---|---|---|\n")
    for f, r in C.sort_values(["nonmetro", "outlets"]).iterrows():
        fh.write(f"| {nm(f)} | {int(r.nonmetro)} | {int(r.outlets)} | {int(r.has_daily)} | {int(r.has_tv)} | {int(r.out_pairs)} |\n")
    for lab, keep in matched.items():
        if lab != "all newsroom counties":
            fh.write(f"\nMatched sample, {lab}: " + ", ".join(nm(f) for f in sorted(keep)) + "\n")
print(f"\nOther counties' profiles and matched samples appended to {NOTES}")
