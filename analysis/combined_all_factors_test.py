"""Supplement to combined_marginal_test.py: every factor that showed a small effect anywhere, including those the
adopted structure cannot hold. All scored out of sample.

TRAVEL    A adopted (doubly constrained)  vs  B origin effects only + every destination factor (population, stores,
          jobs, metro, area centre) + adopted pair terms + every rejected pair term. Fit Jan-Jun, score Jul-Sep.
COVERAGE  A adopted with travel  vs  A + every rejected term + saturation level (rural home x destination's own stories)
          vs  B origin effects only + destination factors (population, stores, jobs, metro, area centre, own stories,
          newsrooms, broadcaster) + every pair term. Leave one newsroom county out.
SPILLOVER adopted outlet model vs + every county factor (cohort, border, population, log newsrooms, one newsroom only,
          travel balance, log outlet stories, broadcaster x travel out); plain and ridge. Leave one county out.
"""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
here = Path(__file__).resolve().parent
src = (here / "combined_marginal_test.py").read_text()
exec(src.split("# ---- travel ---")[0].replace("RUN = set(sys.argv[1:])", "RUN = {'none'}"), globals())   # terms + helpers
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.api as sm  # noqa: E402
import statsmodels.formula.api as smf  # noqa: E402

pop_j = np.log(cov.population.reindex(pairs.j).values)
DEST = pd.DataFrame({"log_pop_j": pop_j,
                     "log_retail_pc_j": base["log_retail_pc_j"].values, "log_jobs_pc_j": base["log_jobs_pc_j"].values,
                     "metro_j": base["metro_j"].values, "dest_centre": [float(j in central) for j in pairs.j]})
O_ONLY = [c for c in FE if c.startswith("o_")]

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
out("## TRAVEL (fit Jan-Jun, score Jul-Sep)")
out("| Model | Terms | Jul-Sep shares explained | Big pairs: mean abs share error (points) | Big pairs within 0.8-1.25x |")
out("|---|---:|---:|---:|---:|")
for label, X in (("A adopted (destination effects)", pd.concat([base[FACTORS], base[FE]], axis=1)),
                 ("B origin effects + every destination factor + every pair term",
                  pd.concat([base[FACTORS], X_extra, DEST, base[O_ONLY]], axis=1))):
    p3 = share(np.exp(X.values @ np.asarray(poisson_fit(y6, X, 300))))
    r = s3[bigp] / p3[bigp]
    nterms = X.shape[1] - sum(c.startswith(("o_", "d_")) for c in X.columns)
    out(f"| {label} | {nterms} | {np.corrcoef(s3, p3)[0, 1] ** 2:.2%} | {100 * np.mean(np.abs(s3 - p3)[bigp]):.2f} | "
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
    cp = pd.read_csv(root / f"analysis/coverage_predicted_{version}.csv", dtype={"i": str, "j": str})
    p = cp[["i", "j", "stories"]].merge(tp[["i", "j", "visits", "ratio"]], on=["i", "j"])
    p = p[p.groupby("i").stories.transform("sum") > 0].reset_index(drop=True)
    rows = [pidx[k] for k in zip(p.i, p.j)]
    lv = np.log1p(p.visits.values)
    own_j = np.log1p(np.array([own[j] for j in p.j], float))
    nr_j = np.log1p(np.array([len(outlets[j]) for j in p.j], float))
    bc_j = np.array([float(j in bcast) for j in p.j])
    rural = 1 - cov.metro.reindex(p.i).values
    adopted = base.iloc[rows][FACTORS].reset_index(drop=True).assign(log_travel_beyond=np.log(p.ratio.clip(lower=1e-3)).values)
    rejected = pd.DataFrame({
        "ring2": [float(R[i][j] == 2) for i, j in zip(p.i, p.j)], "ring3plus": [float(R[i][j] >= 3) for i, j in zip(p.i, p.j)],
        "lv_x_own": lv * own_j, "lv_x_rural": lv * rural, "lv_x_own_x_rural": lv * own_j * rural,
        "lv_x_newsrooms": lv * nr_j, "lv_x_broadcast": lv * bc_j, "rural_x_own_level": rural * own_j,
    }).join(X_extra.iloc[rows].reset_index(drop=True))
    dest = DEST.iloc[rows].reset_index(drop=True).assign(own_j=own_j, newsrooms_j=nr_j, broadcast_j=bc_j)
    Oc = pd.get_dummies(p.i, prefix="o").astype(float)
    Dc = pd.get_dummies(p.j, prefix="d", drop_first=True).astype(float)
    y = p.stories.values.astype(float)
    out(f"\n## COVERAGE, {version.replace('_', ' ')} (leave one newsroom county out)")
    out("| Model | Terms | Mean abs share error (points) |\n|---|---:|---:|")
    for label, Xc, FEc in (("A adopted (with travel)", adopted, pd.concat([Oc, Dc], axis=1)),
                           ("A + every rejected term incl. saturation level", pd.concat([adopted, rejected], axis=1), pd.concat([Oc, Dc], axis=1)),
                           ("B origin effects + destination factors + every pair term", pd.concat([adopted, rejected, dest], axis=1), Oc)):
        Xm = pd.concat([Xc, FEc], axis=1)
        errs = []
        for f in p.i.unique():
            tr, te = (p.i != f).values, (p.i == f).values
            Xt = Xm.drop(columns=[f"o_{f}"])
            pr = np.exp(Xt[te].values @ np.asarray(poisson_fit(y[tr], Xt[tr])))
            sp, sy = pr / pr.sum(), y[te] / max(y[te].sum(), 1)
            sel = (p.visits[te] / p.visits[te].sum() >= 0.01).values | (y[te] >= 2)
            errs += list(100 * np.abs(sp - sy)[sel])
        out(f"| {label} | {Xc.shape[1]} | {np.mean(errs):.2f} |")

# ---- spillover -------------------------------------------------------------------------------------------------------
so = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
unit = lambda f: "29189" if f == "29510" else f
odu = od.assign(h=od.home_county.map(unit), d=od.dest_county.map(unit))
odu = odu[odu.h != odu.d]
balance = odu.groupby("d").visits.sum() / odu.groupby("h").visits.sum()
nr = {u: set() for u in so.fips}
for a in data["articles"]:
    f = fips_of(a["publisher_county"])
    if f and a["publisher"] not in EXCL and a["counties"]:
        nr.setdefault(unit(f), set()).add(a["publisher"])
so["log_newsrooms"] = [np.log(max(len(nr[f]), 1)) for f in so.fips]
so["one_newsroom"] = [float(len(nr[f]) == 1) for f in so.fips]
so["log_balance"] = np.log(balance.reindex(so.fips).values)
so["log_stories"] = np.log(so.placed)
so["bc_x_travel"] = so.broadcast * so.travel_out
F0 = "rate ~ broadcast + travel_out"
F1 = (F0 + " + C(type, Treatment('Rural')) + border + log_pop + log_newsrooms + one_newsroom + log_balance"
      " + log_stories + bc_x_travel")
out("\n## SPILLOVER, outlets (leave one county out)")
out("| Model | Mean abs error (points) |\n|---|---:|")
for label, f, alpha in (("adopted", F0, 0), ("+ every county factor", F1, 0),
                        ("+ every county factor, ridge 0.05", F1, 0.05), ("+ every county factor, ridge 0.2", F1, 0.2)):
    e = []
    for fp in so.fips.unique():
        tr, te = so[so.fips != fp], so[so.fips == fp]
        mod = smf.glm(f, tr, family=sm.families.Binomial())
        if alpha == 0:
            pr = mod.fit().predict(te)
        else:
            params = mod.fit_regularized(alpha=alpha, L1_wt=0.0).params
            Xte = smf.glm(f, pd.concat([tr, te]), family=sm.families.Binomial()).exog[-len(te):]
            pr = 1 / (1 + np.exp(-(Xte @ np.asarray(params))))
        e += list(np.abs(np.asarray(pr) - te.rate.values))
    out(f"| {label} | {100 * np.mean(e):.1f} |")
