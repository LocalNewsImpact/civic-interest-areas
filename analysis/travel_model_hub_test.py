"""Does a regional-centre factor improve the adopted travel model's forecast of each county's main destination?

Candidates, all from the OMB 2023 core-based statistical area delineation (built from commuting data, independent of
the Advan travel data), each added to the adopted doubly-constrained model (gravity_terms.FACTORS):
  same_area        destination is in the same metro or micropolitan area as the home county
  nearest_centre   destination is the central county nearest the home county (2020 population centres)
  adjacent_centre  destination is a central county sharing a border with the home county
  log_intervening  log of the population living closer to the home county than the destination is
A destination-only term (destination is a central county) is absorbed by the destination fixed effects; it was tested
in the singly-constrained model (travel_model_dc_test.py, row 2).
Outcome: the adopted one. Scored as travel_model.py (gravity_terms.HEAD): leave-one-county-out primary, top FORECAST
destination actual / forecast (1.00 = unbiased), Jan-Jun -> Jul-Sep stability check beside persistence; added terms'
coefficients with errors clustered by home and destination county.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
exec(open(Path(__file__).resolve().parent / "travel_model_dc_test.py").read().split("models = [")[0])
warnings.filterwarnings("ignore")
D = {(i, j): miles(i, j) for i in FIPS for j in FIPS if i != j}
X0["log_intervening"] = [np.log1p(sum(cov.population[k] for k in FIPS if k not in (i, j) and D[(i, k)] < D[(i, j)]))
                         for i, j in zip(pairs.i, pairs.j)]
tests = (("adopted", []), ("+ same area", ["same_area"]), ("+ nearest centre", ["nearest_centre"]),
         ("+ adjacent centre", ["adjacent_centre"]), ("+ intervening opportunities", ["log_intervening"]),
         ("+ same area + nearest centre + adjacent centre + intervening",
          ["same_area", "nearest_centre", "adjacent_centre", "log_intervening"]))
EV = {}
for label, extra in tests:
    EV[label] = evaluate(Xof(FACTORS + extra), pairs, y9, y6, y3, extra=extra)
    print("done:", label, flush=True)
print("\n" + HEAD)
for label, _ in tests:
    print(row(label, EV[label], EV["adopted"]))
print(persistence(pairs, y6, y3))
