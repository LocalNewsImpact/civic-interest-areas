"""Is spillover about the other outlets in the market rather than the border itself?  Missouri, March 2026.

For each outlet, from the active outlets in src/lookups/mo_outlet_registry.csv (town coordinates; St. Louis city and
county one unit):
  closer_any        other active outlets in the same county whose town is nearer the county edge than this one's
  closer_same       other active outlets in the same county whose town is nearer the neighbouring county THIS outlet's
                    town is nearest to -- the county it would cover across
  has_closer_same   at least one such outlet (0/1)
  border_rank       this outlet's rank by distance to the county edge among its county's active outlets, 0 = nearest,
                    divided by (outlets - 1); 0 where the county has one outlet
Each added to, or in place of the border distance in, the adopted model
(rate ~ broadcast + crowded_weekly + log_border_mi + log_print), on the same 83 fitted outlets. Scored by predicting
each county's outlets from all the others: mean and median miss, and mean miss by outlet type.
"""
import math
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from shapely.affinity import scale
from shapely.geometry import Point
from shapely.ops import unary_union

warnings.filterwarnings("ignore")
root = Path(__file__).resolve().parents[1]
unit = lambda f: "29189" if f == "29510" else f
KX = math.cos(math.radians(38.5))
flat = lambda geom: scale(geom, xfact=KX, yfact=1, origin=(0, 0))

ns = {}
src = (root / "flows/build_cousub_shares.py").read_text()
exec(src.split('if "--geo" in sys.argv')[0].replace("Path(__file__).parent", f'Path("{root / "flows"}")'), ns)
parts = defaultdict(list)
for k, (rec, geom) in ns["read_shp"](str(root / "census_dl/cousub/cb_2020_29_cousub_500k"), lambda r: r["GEOID"]).items():
    parts[unit(k[:5])].append(geom)
county = {f: flat(unary_union(g)) for f, g in parts.items()}
edge = {f: g.boundary for f, g in county.items()}
# neighbours: Missouri counties whose shapes touch (within 100 m)
nbrs = {f: [h for h in county if h != f and county[f].distance(county[h]) < 0.001] for f in county}

reg = pd.read_csv(Path.home() / "VSCode/NewsCrawler/MizzouNewsCrawler/src/lookups/mo_outlet_registry.csv", dtype=str)
reg = reg[(reg.status == "active") & reg.lat.notna()].assign(u=lambda x: x.county_fips.fillna("").map(unit))
reg = reg[reg.u.isin(county)].drop_duplicates("outlet").copy()
reg["pt"] = [flat(Point(float(x), float(y))) for x, y in zip(reg.lon, reg.lat)]
reg["edge_mi"] = [69 * edge[f].distance(p) for f, p in zip(reg.u, reg.pt)]
reg["near_nbr"] = [min(nbrs[f], key=lambda h: county[h].distance(p)) if nbrs[f] else None for f, p in zip(reg.u, reg.pt)]

d = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
r = reg.set_index("outlet")
feat = []
for o, f in zip(d.outlet, d.fips):
    me = r.loc[o] if o in r.index and r.loc[o, "u"] == f else None
    others = reg[(reg.u == f) & (reg.outlet != o)]
    if me is None:
        feat.append((np.nan, np.nan, np.nan))
        continue
    closer_any = int((others.edge_mi < me.edge_mi).sum())
    nb = me.near_nbr
    if nb is None:
        closer_same = 0
    else:
        mine = 69 * county[nb].distance(me.pt)
        closer_same = int(sum(69 * county[nb].distance(p) < mine for p in others.pt))
    rank = closer_any / len(others) if len(others) else 0.0
    feat.append((closer_any, closer_same, rank))
d[["closer_any", "closer_same", "border_rank"]] = feat
d["has_closer_same"] = (d.closer_same > 0).astype(float)
d["log1p_closer_same"] = np.log1p(d.closer_same)
d["log1p_closer_any"] = np.log1p(d.closer_any)
rows = [l.rstrip("\n").rsplit("|", 1) for l in open(root / "coverage/source_frequency.csv") if "|" in l]
freq = pd.DataFrame(rows, columns=["outlet", "f"]).drop_duplicates("outlet").set_index("outlet").f.str.strip()
d["kind"] = np.where(d.broadcast == 1, "broadcast",
                     d.outlet.map(freq).map({"daily": "daily", "weekly": "weekly"}).fillna("other print"))

NOT_FITTED = {"Greene County Commonwealth", "Three Rivers Publishing", "Mid Rivers Newsmagazine"}
g = d[d.good & ~d.outlet.isin(NOT_FITTED) & d.closer_any.notna()].copy()
print(f"{len(g)} fitted outlets with registry coordinates (of {(d.good & ~d.outlet.isin(NOT_FITTED)).sum()})")
fit = lambda f, x: smf.glm(f, x, family=sm.families.Binomial()).fit()


def score(f):
    pr = pd.Series(index=g.index, dtype=float)
    for fp in g.fips.unique():
        tr, te = g[g.fips != fp], g[g.fips == fp]
        pr[te.index] = fit(f, tr).predict(te)
    e = 100 * (pr - g.rate).abs()
    return e.mean(), e.median(), e.groupby(g.kind).mean()


ADOPTED = "rate ~ broadcast + crowded_weekly + log_border_mi + log_print"
NOBORDER = "rate ~ broadcast + crowded_weekly + log_print"
SPECS = {"adopted": ADOPTED, "adopted without border": NOBORDER}
for t in ["log1p_closer_any", "border_rank", "log1p_closer_same", "has_closer_same"]:
    SPECS[f"+ {t}"] = ADOPTED + f" + {t}"
    SPECS[f"{t} in place of border"] = NOBORDER + f" + {t}"
print("\n| Model | Mean | Median | Broadcast | Daily | Weekly | Other print | Term (coef, p) |\n|---|---:|---:|---:|---:|---:|---:|---|")
for lab, f in SPECS.items():
    m, md, k = score(f)
    term = f.split(" + ")[-1]
    mm = smf.glm(f, g, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(g.fips)[0]})
    tc = f"{term} {mm.params[term]:+.2f} ({mm.pvalues[term]:.3f})" if lab != "adopted" and term in mm.params else ""
    print(f"| {lab} | {m:.2f} | {md:.2f} | {k.get('broadcast', np.nan):.2f} | {k.get('daily', np.nan):.2f} | "
          f"{k.get('weekly', np.nan):.2f} | {k.get('other print', np.nan):.2f} | {tc} |")
show = d[d.fips.isin(["29007", "29019", "29151"])]
print("\n" + show[["outlet", "kind", "border_mi", "closer_any", "closer_same", "rate"]].round(2).to_string(index=False))
d.to_csv(root / "analysis/spillover_market_terms.csv", index=False)
