"""Predicted and actual coverage, by county, March 2026.

Stories touching each Missouri county other than home (story-county pairs: a story counts once for each county it
is centred in or mentions -- coverage/storymap/*_articles.json, the story map's two layers joined per article),
against two predictions:
  gravity   stories ~ population^a * distance^b, Poisson regression (PPML) across the 114 other counties
  travel    the county's share of residents' visits outside home (Advan, March 2026) x the out-of-county pairs
A gap counts only when it is outside the Poisson 95% range of the prediction; with 1-10 stories most gaps are not.
"""
import csv
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
from shapely.geometry import shape

root = Path(__file__).resolve().parents[1]
HOME = {"Audrain": "29007", "Boone": "29019", "Osage": "29151"}
DMA = ["29007", "29019", "29027", "29041", "29051", "29053", "29089", "29125", "29131", "29135", "29139", "29141",
       "29151", "29175"]
pop = {r["fips"]: int(r["population"]) for r in csv.DictReader(open(root / "free/mo_county_population.csv"))}
geo = json.load(open(root / "flows/cousub_29.geojson"))
cent = {f["id"]: (lambda c: (c.x, c.y))(shape(f["geometry"]).centroid) for f in geo["counties"]["features"]}
ns = {}
src = (root / "flows/build_cousub_shares.py").read_text()
exec(src.split('if "--geo" in sys.argv')[0].replace("Path(__file__).parent", f'Path("{root / "flows"}")'), ns)
CNAME = {c[:5]: rec["NAMELSADCO"].replace(" County", "") for c, (rec, _) in
         ns["read_shp"](str(root / "census_dl/cousub/cb_2020_29_cousub_500k"), lambda r: r["GEOID"]).items()}
CNAME["29510"] = "St. Louis city"


def miles(a, b):
    (x1, y1), (x2, y2) = cent[a], cent[b]
    p1, p2, dl = math.radians(y1), math.radians(y2), math.radians(x2 - x1)
    return 3959 * math.acos(min(1, math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)))


def ppml(v, cols, iters=80):
    X = np.column_stack([np.ones(len(v))] + cols)
    b = np.zeros(X.shape[1]); b[0] = math.log(v.mean() + 1e-9)
    for _ in range(iters):
        mu = np.exp(X @ b)
        z = X @ b + (v - mu) / mu
        b = np.linalg.solve(X.T @ (mu[:, None] * X), X.T @ (mu * z))
    return b, np.exp(X @ b)


def poisson_range(mu):
    """Smallest and largest counts inside the central 95% of Poisson(mu)."""
    lo, hi, cdf, k, p = None, None, 0.0, 0, math.exp(-mu)
    while hi is None:
        cdf += p
        if lo is None and cdf > 0.025:
            lo = k
        if cdf >= 0.975:
            hi = k
        k += 1
        p *= mu / k
    return lo, hi


travel = {k: Counter() for k in HOME}
for r in csv.DictReader(open(root / "neighborhood/flows_audrain_boone_osage_2026.csv")):
    if r["month"] == "2026-03":
        travel[r["home_county_name"]][r["dest_county"]] += int(r["device_home_areas"])

for version in ("audrain_all", "boone_all", "boone_no_broadcast", "osage_all"):
    name = version.split("_")[0].title()
    home = HOME[name]
    arts = json.load(open(root / f"coverage/storymap/{version}_articles.json"))
    cov = Counter(c for a in arts for c in a["counties"] if c.startswith("29") and c != home)
    dests = [c for c in pop if c != home and c in cent]
    v = np.array([cov.get(c, 0) for c in dests], float)
    total = v.sum()
    lp = np.log(np.array([pop[c] for c in dests], float))
    ld = np.log(np.array([miles(home, c) for c in dests]))
    b, mu_g = ppml(v, [lp, ld])
    t = np.array([travel[name].get(c, 0) for c in dests], float)
    mu_t = total * t / t.sum()
    r2 = lambda mu: np.corrcoef(v, mu)[0, 1] ** 2
    print(f"\n## {name} ({'without broadcasters' if 'no_broadcast' in version else 'all newsrooms'}): "
          f"{int(total)} story-county pairs outside the county")
    print(f"gravity explains {r2(mu_g):.0%} [population {b[1]:.2f}, distance {b[2]:.2f}]; travel explains {r2(mu_t):.0%}")
    print("| County | Stories | Gravity predicts | Travel predicts | vs travel |")
    print("|---|---:|---:|---:|---|")
    idx = sorted((i for i, c in enumerate(dests) if c in DMA and (v[i] >= 1 or mu_t[i] >= 1)), key=lambda i: -max(v[i], mu_t[i]))
    for i in idx:
        lo, hi = poisson_range(mu_t[i])
        verdict = "more than travel" if v[i] > hi else "less than travel" if v[i] < lo else "within chance"
        print(f"| {CNAME[dests[i]]} | {int(v[i])} | {mu_g[i]:.1f} | {mu_t[i]:.1f} | {verdict} |")
    out_mkt = [(CNAME[dests[i]], int(v[i]), round(mu_t[i], 1)) for i in np.argsort(-v)[:5] if dests[i] not in DMA]
    print("largest outside the market (stories, travel predicts):", out_mkt)
