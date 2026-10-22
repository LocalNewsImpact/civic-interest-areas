"""Do the rejected factors, each marginal alone, add up when included together?  Every model scored out of sample.

TRAVEL    adopted model vs + every rejected pair term at once (same metro/micro area, nearest area centre, adjacent area
          centre, destination size x distance, intervening population, log driving time, on the way to a bigger centre,
          on-the-way weight). Destination-only factors (jobs, stores, metro) are absorbed by the destination effects.
          Fit Jan-Jun, score Jul-Sep: share correlation^2, and mean absolute error on big pairs' shares (>= 5%).
COVERAGE  adopted coverage-with-travel model vs + rings, saturation terms and the travel-side extras. Leave one newsroom
          county out; error in points on its destination shares (1%+ of visits or 2+ stories).
SPILLOVER adopted outlet model vs + cohort, border, population, newsrooms in the county, log outlet stories; plain and
          L2-shrunk (ridge). Leave one county out; mean absolute error in points.
"""
import json
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gravity_terms import FACTORS, FIPS, all_pairs, candidates, cov, miles, root  # noqa: E402

import warnings
warnings.filterwarnings("ignore")
out = lambda *a: print(*a, flush=True)
# sections to run (default all): travel, coverage_all, coverage_no_broadcast, spillover
RUN = set(sys.argv[1:]) or {"travel", "coverage_all", "coverage_no_broadcast", "spillover"}


def poisson_fit(y, X, maxiter=200):
    """Plain Poisson fit; if it fails to converge (many collinear terms), a barely shrunk one (ridge 1e-4)."""
    try:
        m = sm.GLM(y, X, family=sm.families.Poisson()).fit(maxiter=maxiter)
        if np.all(np.isfinite(m.params)):
            return m.params
    except (ValueError, np.linalg.LinAlgError):
        pass
    return sm.GLM(y, X, family=sm.families.Poisson()).fit_regularized(alpha=1e-4, L1_wt=0.0, maxiter=maxiter).params
pairs = all_pairs()
key = list(zip(pairs.i, pairs.j))
base = candidates(pairs)
FE = [c for c in base.columns if c.startswith(("o_", "d_"))]

# ---- extra pair terms ------------------------------------------------------------------------------------------------
d = pd.read_excel(root / "census_dl/ref/list1_2023.xlsx", header=2, dtype=str)
d = d[d["FIPS State Code"] == "29"]
cbsa = {"29" + r[11]: r[1] for r in d.itertuples()}
central = {"29" + r[11] for r in d.itertuples() if r[12] == "Central"}
nearest = {i: min((j for j in central if j != i), key=lambda j: miles(i, j)) for i in FIPS}
drive = pd.read_csv(root / "analysis/drive_od.csv", dtype={"i": str, "j": str}).set_index(["i", "j"])
drive["through"] = drive.through.fillna("").map(lambda s: set(s.split(";")) if s else set())
pop = cov.population
D = {k: miles(*k) for k in key}
X_extra = pd.DataFrame(index=pairs.index)
X_extra["same_area"] = [int(i in cbsa and cbsa.get(i) == cbsa.get(j)) for i, j in key]
X_extra["nearest_centre"] = [int(nearest[i] == j) for i, j in key]
X_extra["adjacent_centre"] = pairs.adjacent.values * np.array([int(j in central) for _, j in key])
X_extra["log_pop_j_x_log_dist"] = np.log(pop.reindex(pairs.j).values) * np.log(pairs.dist.values)
X_extra["log_intervening"] = [np.log1p(sum(pop[k] for k in FIPS if k not in (i, j) and D[(i, k)] < D[(i, j)])) for i, j in key]
X_extra["log_drive_minutes"] = np.log([drive.drive_minutes[k] for k in key])
on_c, on_w = [], []
for i, j in key:
    big = [k for k in central if k not in (i, j) and pop[k] > pop[j] and drive.drive_minutes[(i, k)] <= 90]
    on_c.append(int(any(j in drive.through[(i, k)] for k in big)))
    on_w.append(np.log1p(sum(pop[k] / drive.drive_minutes[(i, k)] ** 2 / 1000 for k in FIPS
                             if k not in (i, j) and j in drive.through[(i, k)])))
X_extra["on_way_centre"], X_extra["on_way_weight"] = on_c, on_w
EXTRA = list(X_extra.columns)
out("extra pair terms built:", EXTRA)

# ---- travel ----------------------------------------------------------------------------------------------------------
od = pd.read_csv(root / "analysis/od_mo_2026.csv", dtype={"home_county": str, "dest_county": str})
od = od[(od.home_county != "OUT") & (od.home_county != od.dest_county)]
disc = pd.read_csv(root / "analysis/od_predicted.csv", dtype={"i": str, "j": str}).set_index(["i", "j"]).stop_discount


def y_for(months):
    v = od[od.month.isin(months)].groupby(["home_county", "dest_county"]).visits.sum()
    return np.array([v.get(k, 0) * (1 - disc[k]) for k in key], float)


ALL = [f"2026-{m:02d}" for m in range(1, 10)]
y6, y3 = y_for(ALL[:6]), y_for(ALL[6:])
share = lambda x: x / pd.Series(x).groupby(pairs.i.values).transform("sum").values
s3 = share(y3)
bigp = s3 >= 0.05
if "travel" in RUN:
  out("\n## TRAVEL (fit Jan-Jun, score Jul-Sep)")
  out("| Model | Terms | Jul-Sep shares explained | Big pairs: mean abs share error (points) | Big pairs within 0.8-1.25x |")
  out("|---|---:|---:|---:|---:|")
  for label, cols in (("adopted", FACTORS), ("adopted + all rejected pair terms", FACTORS + EXTRA)):
    X = pd.concat([base[FACTORS], X_extra[[c for c in cols if c in EXTRA]], base[FE]], axis=1)
    m = sm.GLM(y6, X, family=sm.families.Poisson()).fit(maxiter=300)
    p3 = share(m.predict(X))
    r = s3[bigp] / p3[bigp]
    out(f"| {label} | {len(cols)} | {np.corrcoef(s3, p3)[0, 1] ** 2:.2%} | {100 * np.mean(np.abs(s3 - p3)[bigp]):.2f} | "
        f"{np.mean((r >= .8) & (r <= 1.25)):.0%} |")

# ---- coverage --------------------------------------------------------------------------------------------------------
data = json.load(open(root / "coverage/storymap/statewide_2026_03_articles.json"))
by_name = {n.lower(): f for f, n in cov.name.items()}
by_name.update({"st. louis": "29189", "st louis": "29189", "st. louis city": "29510"})
fips_of = lambda n: by_name.get((n or "").lower().replace(" county", "").strip())
EXCL = {"The Maneater", "CoMoBuzz"}
own, outlets, bcast = Counter(), defaultdict(set), set()
for a in data["articles"]:
    f = fips_of(a["publisher_county"])
    if not f or a["publisher"] in EXCL or not a["counties"]:
        continue
    outlets[f].add(a["publisher"])
    if "broadcast" in (a["publisher_type"] or ""):
        bcast.add(f)
    own[f] += f in a["counties"]
nbr = {f: set(pairs[(pairs.i == f) & (pairs.adjacent == 1)].j) for f in FIPS}


def rings(f):
    dd, q = {f: 0}, deque([f])
    while q:
        x = q.popleft()
        for yy in nbr[x]:
            if yy not in dd:
                dd[yy] = dd[x] + 1; q.append(yy)
    return dd


R = {f: rings(f) for f in FIPS}
tp = pd.read_csv(root / "analysis/od_predicted.csv", dtype={"i": str, "j": str})
pidx = {k: n for n, k in enumerate(key)}
for version in ("all", "no_broadcast"):
    if f"coverage_{version}" not in RUN:
        continue
    cp = pd.read_csv(root / f"analysis/coverage_predicted_{version}.csv", dtype={"i": str, "j": str})
    p = cp[["i", "j", "stories"]].merge(tp[["i", "j", "visits", "ratio"]], on=["i", "j"])
    p = p[p.groupby("i").stories.transform("sum") > 0].reset_index(drop=True)
    rows = [pidx[k] for k in zip(p.i, p.j)]
    lv = np.log1p(p.visits.values)
    own_j = np.log1p(np.array([own[j] for j in p.j], float))
    rural = 1 - cov.metro.reindex(p.i).values
    adopted = base.iloc[rows][FACTORS].reset_index(drop=True).assign(log_travel_beyond=np.log(p.ratio.clip(lower=1e-3)).values)
    more = pd.DataFrame({
        "ring2": [float(R[i][j] == 2) for i, j in zip(p.i, p.j)], "ring3plus": [float(R[i][j] >= 3) for i, j in zip(p.i, p.j)],
        "lv_x_own": lv * own_j, "lv_x_rural": lv * rural, "lv_x_own_x_rural": lv * own_j * rural,
        "lv_x_newsrooms": lv * np.log1p([len(outlets[j]) for j in p.j]), "lv_x_broadcast": lv * np.array([float(j in bcast) for j in p.j]),
    }).join(X_extra.iloc[rows].reset_index(drop=True))
    FEc = pd.concat([pd.get_dummies(p.i, prefix="o").astype(float), pd.get_dummies(p.j, prefix="d", drop_first=True).astype(float)], axis=1)
    y = p.stories.values.astype(float)
    out(f"\n## COVERAGE, {version.replace('_', ' ')} (leave one newsroom county out)")
    out("| Model | Terms | Mean abs share error (points) | Deviance (full fit) |\n|---|---:|---:|---:|")
    for label, Xc in (("adopted (with travel)", adopted), ("adopted + all rejected terms", pd.concat([adopted, more], axis=1))):
        Xm = pd.concat([Xc, FEc], axis=1)
        dev = sm.GLM(y, Xm, family=sm.families.Poisson()).fit(maxiter=300).deviance
        errs = []
        for f in p.i.unique():
            tr, te = (p.i != f).values, (p.i == f).values
            Xt = Xm.drop(columns=[f"o_{f}"])
            pr = np.exp(Xt[te].values @ np.asarray(poisson_fit(y[tr], Xt[tr])))
            sp, sy = pr / pr.sum(), y[te] / max(y[te].sum(), 1)
            sel = (p.visits[te] / p.visits[te].sum() >= 0.01).values | (y[te] >= 2)
            errs += list(100 * np.abs(sp - sy)[sel])
        out(f"| {label} | {Xc.shape[1]} | {np.mean(errs):.2f} | {dev:,.0f} |")

# ---- spillover -------------------------------------------------------------------------------------------------------
so = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
so["newsrooms"] = [np.log(len(outlets.get(f, {1})) or 1) for f in so.fips]
so["log_stories"] = np.log(so.placed)
F0 = "rate ~ broadcast + travel_out"
F1 = F0 + " + C(type, Treatment('Rural')) + border + log_pop + newsrooms + log_stories"
if "spillover" not in RUN:
    sys.exit()
out("\n## SPILLOVER, outlets (leave one county out)")
out("| Model | Mean abs error (points) |\n|---|---:|")
for label, f, alpha in (("adopted", F0, 0), ("+ all rejected county factors", F1, 0),
                        ("+ all rejected, ridge-shrunk (alpha 0.05)", F1, 0.05), ("+ all rejected, ridge-shrunk (alpha 0.2)", F1, 0.2)):
    e = []
    for fp in so.fips.unique():
        tr, te = so[so.fips != fp], so[so.fips == fp]
        mod = smf.glm(f, tr, family=sm.families.Binomial())
        m = mod.fit() if alpha == 0 else mod.fit_regularized(alpha=alpha, L1_wt=0.0)
        X = mod.exog if alpha else None
        pr = m.predict(te) if alpha == 0 else 1 / (1 + np.exp(-(smf.glm(f, te, family=sm.families.Binomial()).exog @ m.params)))
        e += list(np.abs(np.asarray(pr) - te.rate.values))
    out(f"| {label} | {100 * np.mean(e):.1f} |")
