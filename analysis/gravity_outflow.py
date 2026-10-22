"""How much of each home county's outflow destination population (and distance) explains.

For Audrain, Boone and Osage: visits by residents to every other Missouri county, March 2026 (Advan Neighborhood
Patterns Plus, device_home_areas summed by destination county), across the 114 other counties, fitted by Poisson
regression (PPML, the standard gravity estimate):
  population only:  visits ~ population^a
  gravity:          visits ~ population^a * distance^b   (county centroid to centroid, miles)
"Explains" is the squared correlation of predicted and actual visits. Actual / gravity names the market counties
visited more or less than size and distance predict.
"""
import csv
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np

root = Path(__file__).resolve().parents[1]
HOME = {"Audrain": "29007", "Boone": "29019", "Osage": "29151"}
pop = {r["fips"]: int(r["population"]) for r in csv.DictReader(open(root / "free/mo_county_population.csv"))}
geo = json.load(open(root / "flows/cousub_29.geojson"))


# AREA centroids. An average of boundary vertices is pulled toward densely drawn river borders -- it put Boone
# and Callaway, which share Cedar Creek, 7 miles apart instead of about 25.
from shapely.geometry import shape

cent = {f["id"]: (lambda c: (c.x, c.y))(shape(f["geometry"]).centroid) for f in geo["counties"]["features"]}


def miles(a, b):
    (x1, y1), (x2, y2) = cent[a], cent[b]
    p1, p2, dl = math.radians(y1), math.radians(y2), math.radians(x2 - x1)
    return 3959 * math.acos(min(1, math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)))


print("centroid check, miles:", {k: round(miles(*v)) for k, v in
      {"Boone-Callaway": ("29019", "29027"), "Boone-Cole": ("29019", "29051"), "Osage-Cole": ("29151", "29051"),
       "Audrain-Boone": ("29007", "29019")}.items()})
visits = {k: Counter() for k in HOME}
for r in csv.DictReader(open(root / "neighborhood/flows_audrain_boone_osage_2026.csv")):
    if r["month"] == "2026-03":
        visits[r["home_county_name"]][r["dest_county"]] += int(r["device_home_areas"])



def fit(y, cols):
    X = np.column_stack([np.ones(len(y))] + cols)
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ b
    r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return b, r2, y - pred


def rank(a):
    order = np.argsort(a)
    r = np.empty(len(a)); r[order] = np.arange(len(a))
    return r


# county names, from the Census subdivision file the maps use
ns = {}
src = (root / "flows/build_cousub_shares.py").read_text()
exec(src.split('if "--geo" in sys.argv')[0].replace("Path(__file__).parent", f'Path("{root / "flows"}")'), ns)
CNAME = {c[:5]: rec["NAMELSADCO"].replace(" County", "") for c, (rec, _) in
         ns["read_shp"](str(root / "census_dl/cousub/cb_2020_29_cousub_500k"), lambda r: r["GEOID"]).items()}
CNAME["29510"] = "St. Louis city"
DMA = ["29007", "29019", "29027", "29041", "29051", "29053", "29089", "29125", "29131", "29135", "29139", "29141",
       "29151", "29175"]


def ppml(v, cols, iters=60):
    """Poisson regression, log link (PPML): the standard gravity estimate -- weights each county by its traffic and
    keeps the zeros, which a fit on logs throws out or inflates."""
    X = np.column_stack([np.ones(len(v))] + cols)
    b = np.zeros(X.shape[1]); b[0] = math.log(v.mean() + 1e-9)
    for _ in range(iters):
        mu = np.exp(X @ b)
        z = X @ b + (v - mu) / mu
        W = mu
        b = np.linalg.solve(X.T @ (W[:, None] * X), X.T @ (W * z))
    return b, np.exp(X @ b)


for name, home in HOME.items():
    dests = [c for c in pop if c != home and c in cent]
    v = np.array([visits[name].get(c, 0) for c in dests], float)
    lp = np.log(np.array([pop[c] for c in dests], float))
    ld = np.log(np.array([miles(home, c) for c in dests]))
    fits = {}
    for label, cols in (("population", [lp]), ("population + distance", [lp, ld])):
        b, mu = ppml(v, cols)
        # share of the variation in each county's share of visits that the prediction accounts for
        r2 = np.corrcoef(v, mu)[0, 1] ** 2
        fits[label] = (b, mu, r2)
    b, mu, _ = fits["population + distance"]
    _, mu_p, _ = fits["population"]
    share, pred, pred_p = v / v.sum(), mu / mu.sum(), mu_p / mu_p.sum()
    print(f"\n## {name}: {int(v.sum()):,} visits to the other 114 counties")
    print(f"population alone explains {fits['population'][2]:.0%}; population + distance {fits['population + distance'][2]:.0%} "
          f"[population elasticity {b[1]:.2f}, distance {b[2]:.2f}]")
    print("| County | Visits | Predicted by population | Predicted by population + distance | Actual / gravity |")
    print("|---|---:|---:|---:|---:|")
    idx = sorted((i for i, c in enumerate(dests) if c in DMA or share[i] >= 0.02), key=lambda i: -share[i])
    for i in idx:
        print(f"| {CNAME[dests[i]]}{'' if dests[i] in DMA else ' (outside market)'} | {100 * share[i]:.1f}% | "
              f"{100 * pred_p[i]:.1f}% | {100 * pred[i]:.1f}% | {share[i] / pred[i]:.1f}x |")
