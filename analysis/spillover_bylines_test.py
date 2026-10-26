"""Do newsroom size (distinct bylines) and volume (local stories) change a print outlet's spillover?  March 2026.

Outlets: print and digital, 10+ placed stories (spillover_outlets.csv). Bylines from production articles.author for the
same March articles (coverage/bylines/march_2026_authors.csv): split on " and ", "&", ";", ","; lowercased; generic
credits dropped (staff, report, news, press, wire services). Per outlet:
  bylines        distinct named authors
  byline_share   share of its stories with a named author (completeness varies by site)
  volume         local stories it published in March (all, not only placed)
Added to the adopted model's print term (spillover_common.FINAL: log(1 + print and digital outlets in the county);
the broadcaster term is constant here), alone and together; fitted on the adopted outlets, each county's scored
outlets held out (spillover_common.heldout_error). Also run on outlets with >= 50% bylined stories only.
"""
import re
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from spillover_common import FINAL, adopted_split, heldout_error, rural_by_unit  # noqa: E402,F401  the adopted spillover model
root = Path(__file__).resolve().parents[1]
a = pd.read_csv(root / "coverage/bylines/march_2026_authors.csv", keep_default_na=False)
a.columns = ["id", "outlet", "author"]
GENERIC = re.compile(r"staff|report|news|press|associated|reuters|wire|editor|team|desk|submitted|contributed|release|admin|"
                     r"^by$|^the |department|office|county|city of|courtesy", re.I)
names = defaultdict(set)
for o, au in zip(a.outlet, a.author):
    for n in re.split(r"\s+and\s+|&|;|,|\|", au):
        n = re.sub(r"^\s*by\s+", "", n.strip(), flags=re.I).strip().lower()
        if len(n) >= 4 and " " in n and not GENERIC.search(n):
            names[o].add(n)
per = a.groupby("outlet").agg(volume=("id", "size"), byline_share=("author", lambda s: (s != "").mean()))
per["bylines"] = [len(names[o]) for o in per.index]
so = pd.read_csv(root / "analysis/spillover_outlets.csv", dtype={"fips": str})
so = so.join(per, on="outlet")
p = so[so.broadcast == 0].copy()
p["log_bylines"] = np.log1p(p.bylines)
p["log_volume"] = np.log(p.volume)
p["stories_per_byline"] = np.log(p.volume / p.bylines.clip(lower=1))
print(f"{len(p)} print/digital outlets; bylines median {p.bylines.median():.0f} (range {p.bylines.min()}-{p.bylines.max()}); "
      f"volume median {p.volume.median():.0f}; bylined share median {p.byline_share.median():.0%}; "
      f"outlets >= 50% bylined: {(p.byline_share >= .5).sum()}")
print(f"correlations: log bylines vs log volume {np.corrcoef(p.log_bylines, p.log_volume)[0, 1]:.2f}; "
      f"spillover vs log bylines {np.corrcoef(p.rate, p.log_bylines)[0, 1]:+.2f}; vs log volume {np.corrcoef(p.rate, p.log_volume)[0, 1]:+.2f}")
specs = {"adopted, print and digital (FINAL without the broadcaster term)": "rate ~ log_print",
         "+ bylines": "rate ~ log_print + log_bylines",
         "+ volume": "rate ~ log_print + log_volume",
         "+ bylines + volume": "rate ~ log_print + log_bylines + log_volume",
         "+ stories per byline": "rate ~ log_print + stories_per_byline"}
for label, sub in (("all print/digital outlets", p), ("outlets with >= 50% bylined stories", p[p.byline_share >= .5])):
    sf = adopted_split(sub)[0]
    print(f"\n## {label} (fitted {len(sf)}, scored {int(sub.scored.sum())} outlets, {sf.fips.nunique()} counties)")
    print("| Model | Leave-one-county-out error (points) | Added terms (coef, p, county-clustered) |\n|---|---:|---|")
    for name, f in specs.items():
        m = smf.glm(f, sf, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(sf.fips)[0]})
        extra = [k for k in m.params.index if k not in ("Intercept", "log_print")]
        print(f"| {name} | {heldout_error(f, sub):.2f} | " + "; ".join(f"{k} {m.params[k]:+.2f} (p {m.pvalues[k]:.3f})" for k in extra) + " |")
cols = ["outlet", "fips", "placed", "volume", "bylines", "byline_share", "rate"]
print("\nthe three counties' print outlets:")
print(p[p.fips.isin(["29007", "29019", "29151"])][cols].round(2).to_string(index=False))
p.to_csv(root / "analysis/spillover_bylines.csv", index=False)
