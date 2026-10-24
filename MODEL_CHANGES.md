# Model changes — travel, coverage and spillover

Log of the modelling decisions from 2026-10-16: what was adopted, what was tested and rejected, and the evidence for
each. The peer-review fixes of 2026-10-24 restate every model's figures: current figures are under **Current
results**, replaced ones under **Superseded figures** (end). Scripts are in `analysis/` unless noted;
`make_visuals.sh` rebuilds every figure from the adopted models.

## Data and periods

| Item | Setting |
|---|---|
| Travel | Advan Neighborhood Patterns Plus (Dewey), Missouri destinations, January–September 2026; summed to home county × destination county (`build_statewide_od.py` → `od_mo_2026.csv`). Outcome in every travel script: calibrated visits × pass-through discount (`gravity_terms.travel_visits`) |
| Travel, Kansas | Advan Neighborhood Patterns Plus, Kansas destination block groups, January–September 2026 (`neighborhood/raw_ks/`): Missouri residents' visits to Kansas, and the Kansas transfer test (`build_ks_od.py` → `od_ks_2026.csv`) |
| Coverage | Missouri School of Journalism analysis of local news stories, March 2026 (the only month enriched); a story is placed in every county it is centred in or mentions |
| Store-level visits | Advan Weekly Patterns Plus, Missouri, weeks of 2026-03-02 to 03-23 |
| Boundaries | Advan reports 2020 block groups for Jan–Jul and 2010 block groups for Aug–Sep; county codes are the same, and the township maps use one area crosswalk per vintage |

## Current results (2026-10-24)

The figures a paper quotes. Body sections state the same values; a different value elsewhere is marked superseded
and listed under Superseded figures. Intervals are 95%. Change = held-out error with − without (negative = better).

**Selection rule (authors, 2026-10-24).** A term is kept only by a joint test:

1. the adopted set beats the baseline held out, with a county-paired bootstrap 95% interval on the change excluding
   zero (baseline: travel, home and destination effects only; spillover, intercept only);
2. each adopted coefficient's 95% interval excludes zero (travel: two-way clustered by home and destination county;
   spillover: county-cluster bootstrap);
3. candidate additions are tested one at a time against the adopted set and kept only if their paired held-out change
   has an interval excluding zero;
4. ties go to fewer terms.

A nested test — the procedure repeated inside each training set and scored on the held-out counties — guards against
searching many candidates. Held out: each home county (travel, public model), newsroom county (coverage) or county's
outlets (spillover) predicted by a fit without it.

**Travel** — doubly-constrained gravity, PPML; home and destination fixed effects + 8 pair terms
(`gravity_terms.FACTORS`):

| Measure | Value | Script |
|---|---|---|
| Held-out R² of shares (1 − SSE/SST) | 93.8% [92.4, 94.9] | `travel_model.py` |
| Held-out share-weighted error, points | 3.26 [2.93, 3.59] | `travel_model.py` |
| — small rural (56) / independent towns (32) / commuter (18) / hubs (9) | 3.44 / 2.83 / 3.85 / 2.47 | `travel_model.py` |
| Big flows (forecast 5%+, 483 pairs): error; within 0.8–1.25× | 3.45 [3.17, 3.74]; 49% [45, 54] | `travel_model.py` |
| Top forecast destination, actual ÷ forecast | 1.02× (middle half 0.88–1.18) | `travel_model.py` |
| Joint test: adopted vs fixed effects only | 16.76 → 3.26; change −13.50 [−15.14, −11.69] | `travel_model_dc_test.py selection` |
| Commuting out and in, added to the pre-commuting model | 3.71 → 3.26; change −0.45 [−0.70, −0.21] | `travel_commute_pair_test.py` |
| Nested search of 24 candidates | 3.259 → 3.218; change −0.041 [−0.173, +0.112]: none adopted | `combined_marginal_test.py travel_nested_all` |
| Distance elasticity at 25 mi, mean-size home county: metro / nonmetro | −0.89 (s.e. 0.08) / −0.46 (0.14) | `travel_model.py` |
| Commuting out / in (two-way s.e.) | +0.284 (0.051) / +0.192 (0.036) | `travel_model.py` |
| Stability, Jul–Sep from Jan–Jun: model / persistence error | 3.01 / 1.51 | `travel_model.py` |
| Kansas share of out-of-county visits: all Missouri / 14 border counties / Jackson | 11.6% / 37.7% / 52.5% | `travel_model.py` |
| Pass-through discount | removes 2.3% of out-of-county visits | `travel_model.py` |

**Coverage** — PPML of March story-county pairs; shared gravity terms, newsroom-county and covered-county fixed
effects, log visits (where > 0), zero-visit indicator, log visits × nonmetro newsroom county (RUCC 4–9); errors
clustered by newsroom county:

| Measure | All outlets | Print and digital | Script |
|---|---|---|---|
| Stories / newsroom counties / out-of-county story-county pairs | 14,877 / 88 / 10,282 | 8,301 / 88 / 6,674 | `coverage_model.py` |
| Elasticity of stories to visits, metro newsroom counties (27) | 0.49 (s.e. 0.066; 0.36–0.62) | 0.51 (0.081; 0.35–0.67) | `coverage_model.py` |
| Elasticity, nonmetro newsroom counties (61) | 0.25 (s.e. 0.061; 0.13–0.37) | 0.25 (0.060; 0.14–0.37) | `coverage_model.py` |
| Difference, nonmetro − metro | −0.235 (s.e. 0.039, p < 0.001) | −0.253 (0.058, p < 0.001) | `coverage_model.py` |
| Twice the visits, metro / nonmetro | 1.40× / 1.19× the stories | 1.42× / 1.19× | `coverage_model.py` |
| Commuting in / out | +0.42 (s.e. 0.073) / −0.02 (n.s.) | +0.38 (0.071) / −0.03 (n.s.) | `coverage_model.py` |
| Held-out error, all destinations / destinations with 1%+ of visits | 0.913 [0.844, 0.982] / 4.42 [4.00, 4.91] | 0.939 [0.873, 1.003] / 4.53 [4.08, 4.97] | `coverage_saturation_test.py` |
| Nonmetro interaction against pooled, change on 1%+ / all destinations | −0.143 [−0.221, −0.068] / +0.002 [−0.006, +0.009] | −0.111 [−0.191, −0.030] / −0.000 [−0.008, +0.008] | `coverage_saturation_test.py` |
| Saturation (log visits × destination's own stories) | −0.007 (s.e. 0.008, p 0.34): not supported | | `coverage_saturation_test.py` |
| Pooled elasticity, no nonmetro interaction (sensitivity) | 0.36 (s.e. 0.060) | 0.35 (0.064) | `coverage_model.py` |

**Spillover** — outlet-level logistic: spillover ~ broadcaster + log(1 + print and digital outlets in the county)
(`spillover_common.FINAL`); mention 0.5 and Sports 0.5 are definitions:

| Measure | Value | Script |
|---|---|---|
| Outlets with 10+ placed stories | 128 in 72 counties (27 broadcasters), 12,192 stories | `spillover_outlets.py` |
| Fitted (well collected, 20+ placed stories, not Three Rivers Publishing) | 85 outlets, 48 counties (24 broadcasters) | `spillover_outlets.py` |
| Broadcaster | +0.667 (clustered s.e. 0.135; bootstrap CI +0.388 to +0.939) | `spillover_outlets.py` |
| Print and digital outlets in the county, log(1 + count) | −0.387 (0.089; CI −0.655 to −0.232) | `spillover_outlets.py` |
| Held-out error, mean / median, points | 5.98 / 4.66 (intercept only 7.49 / 6.23); skill +0.202; out-of-sample R² +0.360 | `spillover_outlets.py` |
| Joint test: adopted vs intercept only | change −1.51 [−2.61, −0.32]; no addition passes | `spillover_rule_selection.py` |
| Nested: rule applied inside each fold | 6.27 / 4.76; adopted set chosen in 47 of 48 folds | `spillover_rule_selection.py` |
| Scored on all 94 well-collected outlets with 10+ | 6.43 / 4.81 | `spillover_outlets.py` |
| Actual / expected: Audrain, Boone, Osage, Cole, Jackson | 20 / 22%, 29 / 26%, 26 / 25%, 23 / 25%, 22 / 21% | `spillover_outlets.py` |
| Leave one TV market out (7 markets with 3+ outlets) | in sample 5.9, held out 6.2, intercept only 7.4 | `spillover_dma_holdout.py` |
| Springfield region (Greene, Webster, Barry) held out | 8.0; region 24% actual, 26% expected | `spillover_outlets.py` |
| Mean spillover rate | 24.7% | `spillover_outlets.py` |

**Public-data travel model** — the study's question is how close a model built from public data gets to the
Advan-fitted model, and how much of the gap Advan-learned corrections close. The public model is not claimed to beat
the Advan-fitted model, and does not in any class. Common destination set per state; every score out of sample for
the county scored:

| Model | Missouri (115): share-weighted error | log-ratio error | Kansas (105): share-weighted error | log-ratio error |
|---|---:|---:|---:|---:|
| Advan-fitted (counties held out) | 3.34 | 0.35 | 3.27 | 0.36 |
| Public (Missouri: setting chosen nested; Kansas: Missouri settings, nothing tuned) | 4.85 | 0.53 | 4.29 | 0.50 |
| + Advan-learned segment corrections (C, transferable; Missouri outer loop; Kansas learned in Missouri) | 3.97 | 0.45 | 4.27 | 0.54 |
| + one factor per destination county (A, Missouri only; outer loop) | 3.47 | 0.39 | — | — |
| Public − Advan-fitted | +1.50 [+1.02, +2.01] | +0.17 [+0.14, +0.20] | +1.03 [+0.53, +1.52] | +0.14 [+0.11, +0.17] |
| Corrected (C) − Advan-fitted | +0.63 [+0.19, +1.07] | +0.10 [+0.07, +0.12] | +1.01 [+0.47, +1.51] | +0.17 [+0.14, +0.20] |
| Corrected (C) − public | −0.88 [−1.26, −0.49] | −0.08 [−0.09, −0.06] | −0.02 [−0.38, +0.34] | +0.03 [+0.02, +0.05] |
| Gap to the Advan-fitted model closed by corrections | C 58%, A 91% | | no net gain | |
| Advan share outside the common destination set, per county | 1.37% (max 8.5%) | | 9.13% (max 40.7%, Thomas) | |

Scripts: `public_stage1_nested.py`, `public_adjusted_nested.py`, `score_segments.py`, `public_vs_advan_compare.py`
(Missouri); `score_ks.py`, `ks_advan_fitted.py`, `transfer_adjustments.py` (Kansas); metrics in `public_scoring.py`.

**Civic interest areas** — travel patterns by non-negative matrix factorization per TV market (`flows/travel_patterns.py`),
areas per town (`flows/market_patterns.py`). **K rule (user, 2026-10-24, option A):** K = the largest K at which
every pattern holds 10%+ and 1,000+ of the residents and 10%+ of the travel of at least one study town in the market
(the same town for all three), and replicates at matched cosine 0.9+ across random starts and between odd and even
months. A share of the market was rejected (it depends on which home counties form the market); a 5% level was
rejected; held-out month error is a persistence diagnostic only.

| Market | K | K + 1 fails on |
|---|---:|---|
| Columbia-Jefferson City | 3 | months (0.55) |
| Springfield | 7 | starts (0.20), months (0.25) |
| Paducah-Cape Girardeau | 3 | months (0.72) |
| Ottumwa-Kirksville | 3 | town (Lancaster 917 residents), starts (0.86), months (0.54) |
| Joplin | 4 | town (best: Webb City 4%, 467 residents) |
| Kansas City | 3 | starts (0.63) |
| St. Joseph | 3 | months (0.81) |

57 areas in 36 study towns (`flows/market_patterns.py`).

| Measure | Columbia | Mexico | Linn | Script |
|---|---:|---:|---:|---|
| Areas | 1 ("Columbia's civic interest area") | 1 | 1 | `flows/market_patterns.py` |
| Residents in the area (share of the town's) | ~97,020 (91%) | ~6,530 (92%) | ~1,270 (71%) | `flows/market_patterns.py` |
| Area (outline), km² | 1,363 | 1,691 | 1,176 | `flows/market_patterns.py` |
| Replicability, odd vs even months, home excluded (Jaccard) | 0.76 | 0.75 | 0.58 | `analysis/selection_sensitivity.py` |
| Shown hexagons holding in both halves | 0.95 | 0.98 | 0.75 | `analysis/market_stability.py` |
| Coverage density: frequent / regular / sporadic / none | 44 / 8 / 48 / 0% | 32 / 4 / 64 / 0% | 21 / 8 / 71 / 0% | `analysis/area_coverage_alignment.py` |
| Balanced diet (share of hexagons; mean categories met) | 44%; 4.4 | 15%; 2.4 | 16%; 1.8 | `analysis/cin_diet.py` |
| Boone hexagons in the area | — | 95 | — | `flows/market_patterns.py` |
| Tie-market accuracy, public vs Advan (town) | 0.13 | 0.41 | 0.82 | `analysis/tie_footprint.py` |

Tie markets, 36 towns: accuracy median 0.61 (mean 0.610), replicability median 0.88 (`analysis/tie_footprint.py`;
2026-10-18: 0.70 / 0.91, scored with home units unmasked and the market scored whole).

## Measurement corrections

| Change | Why |
|---|---|
| Stories credited to the **Missouri School of Journalism analysis**, never LNIC | Attribution |
| **The Maneater and CoMoBuzz** excluded from Boone's coverage | Decision for these analyses |
| **Statewide outlets are no county's local news** (2026-10-17): Missouri Business Alert (filed under Boone); The Missouri Independent, Missouri Net, Missouri Scout, The Missouri Times (filed under Cole) (`excluded_outlets.EXCLUDE`) | They cover the state, not a county |
| **Campus newspapers are not local news anywhere** (2026-10-24): the 11 student newspapers owned by a college or university (`CAMPUS`, part of `EXCLUDE` in `excluded_outlets.py`) are out of coverage, the spillover outcome and fit, and every county outlet count | Same footing as The Maneater. University-licensed public broadcasters (KBIA, KCUR, KRCU, KSMU, KXCV, STL Public Radio) and the School of Journalism's community newsrooms (Columbia Missourian, Boone County Journal, KOMU) stay |
| **Mid Rivers Newsmagazine → St. Charles; Greene County Commonwealth → Greene** (2026-10-24; `excluded_outlets.HOME_COUNTY`, `home_fips`), in coverage and spillover, both fitted | Each is published outside the county it covers |
| **St. Louis city and county treated as one unit** for spillover | Every St. Louis outlet is registered in St. Louis County, so city stories counted as "another county" (St. Louis print spillover read 85%; merged, 25% — 2026-10-16 measure, not rerun) |
| **Other-state counties within 60 miles count as spillover** | Kansas City print outlets read 18% on Missouri counties only and 44% with Kansas (2026-10-16 measure, not rerun); border regions cross the state line |
| **One home rule for every outlet** (spillover, 2026-10-24): the county filed under, every other county holding part of its registry city, and Kansas City, Kansas (Wyandotte) for Kansas City, Missouri outlets | A story about another part of the outlet's own city is not spillover |
| **Home county excluded from every travel–coverage comparison** | Residents live in their home county all of the time; a share of visits says nothing about how much it matters to them. Home and away story counts are reported for reference only |
| **Coverage counts a story's central place as well as the places it mentions** | The story map's county layer omits each story's central place; Osage had 13 placed stories on that layer against 40 with both |
| **Hospital indicator removed** | It was a facility count from a CMS file, not travel data, incomplete (it missed Capital Region Medical Center), and read as a healthcare finding the data cannot support |
| **One travel outcome in every travel script** (2026-10-24): calibrated visits × pass-through discount | Several scripts had used undiscounted or uncalibrated visits |

## Population calibration (adopted)

Advan Neighborhood Patterns Plus is "normalized against panel size and country population" (Dewey's Advan page): a
national scaling, not a local one. Residents seen in their own home block group therefore do not match population.

- Factor (county, month) = residents seen in their own block group ÷ ACS 2020–2024 population. Across Missouri
  county-months: median 1.94, middle 80% 1.09–3.18. Audrain 1.19–2.54, Boone 1.58–2.52, Osage 2.19–4.26. Median by
  month: Jan 1.78, Feb 1.76, Mar 2.08, Apr 2.54, May 2.20, Jun 2.17, Jul 1.71, Aug 1.73, Sep 1.65 — no break at the
  change from 2020 to 2010 block groups (Jul → Aug).
- Every count of a county's residents that month is divided by its factor before months are added
  (`build_calibration.py` → `calibration_county_month.csv`; `od_mo_2026.csv` keeps raw counts as `visits_recorded`).
  Township shares and alignment data apply the same factors.
- County, not tract: August–September use 2010 block groups, whose tracts differ from the 2020 tracts that carry ACS
  populations.
- Effect: shares within a county barely move (one factor per county-month). Distance elasticity at 25 miles,
  mean-size home county (`travel_model.py`):

| Visits | Metro home | Nonmetro home | Held-out error |
|---|---:|---:|---:|
| Uncalibrated (recorded) | −0.952 (0.113) | −0.450 (0.168) | 3.29 |
| Calibrated (adopted) | −0.887 (0.083) | −0.460 (0.136) | 3.26 |

  Calibration moves the elasticity by less than one standard error. The adopted spillover model has no travel term.
- Unexplained: the median factor is about 2, not 1, so the over-count is not only local variation around a correct
  national figure; the spring rise (April 2.54) is also unexplained. Question for Advan.
- Rule: never pool months or compare absolute counts across areas without this calibration; work with shares within a
  month.

## Device IDs (tested)

`device_id_test.py`: for 424 block groups dominated by one business, monthly distinct devices (Neighborhood Patterns)
against that business's weekly visitors summed over March's four weeks (Weekly Patterns). Monthly can only be lower if
the same devices were recognised in more than one week. It was lower in 71, 62 of them also passing a same-scale check
(monthly at least any single week) — mostly workplaces (auto dealers 39%, printing plants 37%). IDs are therefore
stable at least week to week. Daily resets cannot be tested: no product reports homes by day.

## Travel model

**Adopted: doubly-constrained gravity model, Poisson pseudo-maximum likelihood** (`travel_model.py`; terms and
scoring in `gravity_terms.py`).

- A fixed effect for every home county (its total travel) and every destination (its overall draw: capital,
  university, hospitals, shopping — measured from the data, not proxied)
- Pair terms (8, `gravity_terms.FACTORS`): log distance and its square; both again for nonmetropolitan home counties;
  log home-county population × log distance (larger counties travel farther); shared border; commuting out and
  commuting in between the two counties (LODES 2023)
- Distance centred at 25 miles (the visit-weighted geometric mean out-of-county trip is 26 miles), home-county log
  population at its mean (geometric mean 21,980): the log-distance coefficient is the distance elasticity at 25 miles
  for a metropolitan home county of mean size. Centring changes no prediction (`od_predicted.csv` identical to 1e-13)
- Outcome: calibrated visits × (1 − max(0, highway-stop share − 12.5%)), the highway-stop share being the county pair's
  share of store-level visits at gas stations, convenience stores and fast food. The discount removes 2.3% of
  out-of-county visits (3,314 pairs)
- Inference: standard errors clustered two ways, by home county and by destination county
- Validation: each home county held out (8 folds, seed 7), its Jan–Sep destination shares predicted from the other
  counties' travel; intervals from 1,000 bootstrap resamples of home counties, predictions held fixed. The Jan–Jun →
  Jul–Sep split is a stability check, not validation: persistence (Jan–Jun observed shares) beats the model on it

### Validation

| Measure | Value |
|---|---|
| Held-out R² of shares (1 − SSE/SST) | 93.8% [92.4, 94.9] |
| Held-out share-weighted error (points) | 3.26 [2.93, 3.59] |
| — small rural (56) / independent towns (32) / commuter (18) / hubs (9) | 3.44 [2.96, 3.95] / 2.83 [2.32, 3.36] / 3.85 [3.04, 4.71] / 2.47 [1.54, 3.67] |
| Big flows (forecast 5%+; 483 pairs): absolute share error | 3.45 points [3.17, 3.74] |
| — within 0.8–1.25× of the forecast | 49% [45, 54] |
| — actual ÷ forecast, 10th–90th percentile | 0.57×–1.51× (median 1.01×) |
| Top FORECAST destination, actual ÷ forecast | 1.02× (middle half 0.88–1.18) |
| Same, top OBSERVED destination (selected on the outcome) | 1.11× |
| Reference: destination effects + log distance only | 6.13 [5.52, 6.73]; adopted change −2.87 [−3.43, −2.31] |
| In-sample: R² of shares; deviance | 94.7%; 68.8M |
| Stability, Jul–Sep from Jan–Jun: model | R² 93.8%; error 3.01; big flows 3.20, 55% within 0.8–1.25× |
| Stability: persistence (Jan–Jun observed shares) | R² 98.6%; error 1.51; big flows 1.43, 92% within |
| Stability: model − persistence, error | +1.49 [+1.20, +1.78] |

Coefficients, Jan–Sep (two-way clustered s.e.):

| Term | Coef | s.e. | p |
|---|---:|---:|---:|
| log distance (elasticity at 25 mi, metro home) | −0.887 | 0.083 | < 0.001 |
| log distance² | −0.282 | 0.029 | < 0.001 |
| nonmetro × log distance | +0.427 | 0.109 | < 0.001 |
| nonmetro × log distance² | −0.273 | 0.051 | < 0.001 |
| log home population × log distance | +0.160 | 0.025 | < 0.001 |
| shared border | +0.501 | 0.064 | < 0.001 |
| commuting out | +0.284 | 0.051 | < 0.001 |
| commuting in | +0.192 | 0.036 | < 0.001 |

Distance elasticity of visits, home county of mean population (two-way s.e.):

| Distance | Metro home | Nonmetro home |
|---|---:|---:|
| 10 mi | −0.37 (0.11) | +0.56 (0.19) |
| 25 mi | −0.89 (0.08) | −0.46 (0.14) |
| 50 mi | −1.28 (0.08) | −1.23 (0.12) |
| 100 mi | −1.67 (0.09) | −2.00 (0.13) |

Travel from nonmetropolitan counties barely falls off over the first 25 miles and falls off faster than metro travel
beyond about 50. The positive value at 10 miles is the quadratic's end point (the closest county pair is 7.5 miles
apart), not a finding.

With no travel data for a county, the model places its destination shares to within 3.3 points (share-weighted) and
its top destination without bias (1.02×). For a county whose own travel is observed, the observed shares are the
better figure: the model is not a forecasting improvement on them.

### Steps that led there

`travel_model_compare.py`, `travel_model_dc_test.py`; held out = each home county left out:

| Version | In-sample deviance | Held-out R² | Held-out error [95%] | Top forecast destination, actual ÷ forecast | Big flows within 0.8–1.25× |
|---|---:|---:|---:|---:|---:|
| Plain gravity: population + distance (origin effects) | 358.2M | 64.8% | 9.62 [8.64, 10.58] | 1.15× | 15% |
| + border, rural home × distance, metro, stores (singly constrained, `gravity_terms.SINGLY`) | 258.1M | 77.7% | 7.25 [6.37, 8.17] | 1.19× | 26% |
| Singly + area centre + curved distance | 167.0M | 84.2% | 5.79 [5.05, 6.54] | 1.14× | 33% |
| Doubly constrained: distance, rural × distance, border | 124.4M | 87.6% | 5.03 [4.42, 5.63] | 1.10× | 36% |
| + curved distance | 93.3M | 90.4% | 4.24 [3.76, 4.76] | 1.05× | 40% |
| + larger home counties travel farther (adopted before 2026-10-18) | 77.4M | 92.2% | 3.71 [3.32, 4.10] | 1.00× | 44% |
| **+ commuting out and in (adopted)** | **68.8M** | **93.8%** | **3.26 [2.93, 3.59]** | **1.02×** | **49%** |

The singly-constrained model was abandoned on held-out error (7.25 against 3.26; R² 77.7% against 93.8%). (Superseded
2026-10-24: "under-predicted every county's main destination by 1.6×" — an in-sample ratio selected on the observed
share; selected on the forecast and held out it is 1.19×.) The "Osage residents go to Jefferson City twice as often as
expected" figure came from that model and stays withdrawn: under the adopted model Osage → Cole is 1.09 in-sample,
1.14 held out. In the singly-constrained model, metro destination (p = 0.75), stores per resident (p = 0.19) and jobs
per resident (p = 0.69; two-way) add nothing measurable; the doubly-constrained model absorbs all three.

### Selection tests (`travel_model_dc_test.py selection`)

| Test | Result |
|---|---|
| Adopted set against home and destination effects only | 16.76 → 3.26; change −13.50 [−15.14, −11.69]: passes |

| Adopted term | Coefficient [95%, two-way] | Change in held-out error when dropped [95%] |
|---|---:|---:|
| log distance | −0.887 [−1.051, −0.724] | +0.174 [−0.086, +0.452] |
| log distance² | −0.282 [−0.340, −0.224] | +0.281 [+0.008, +0.553] |
| nonmetro × log distance | +0.427 [+0.213, +0.641] | +0.130 [−0.013, +0.277] |
| nonmetro × log distance² | −0.273 [−0.372, −0.174] | +0.184 [+0.038, +0.328] |
| log home population × log distance | +0.160 [+0.111, +0.208] | +0.149 [−0.079, +0.394] |
| shared border | +0.501 [+0.376, +0.626] | +0.187 [−0.055, +0.423] |
| commuting out | +0.284 [+0.184, +0.384] | +0.377 [+0.204, +0.552] |
| commuting in | +0.192 [+0.122, +0.262] | +0.056 [−0.098, +0.198] |

Every coefficient interval excludes zero: all eight terms are kept. Five drop-one intervals span zero; the distance
terms are collinear, so dropping one lets the others absorb it.

| Candidate added | Change [95%] |
|---|---:|
| same metro/micro area | +0.003 [−0.062, +0.073] |
| nearest area centre | −0.014 [−0.077, +0.047] |
| adjacent area centre | +0.003 [−0.032, +0.039] |
| destination size × distance | +0.011 [−0.094, +0.115] |

Every other candidate is in the rejected table below, scored the same way.

### Out-of-state travel: Kansas

`od_mo_2026.csv` holds Missouri destinations only. Advan's Kansas destination files (`neighborhood/raw_ks/`) record
Missouri residents' visits there; calibrated the same way, Jan–Sep (`travel_model.py`):

| Home county | Kansas share of out-of-county visits (Missouri + Kansas) |
|---|---:|
| Jackson | 52.5% |
| Platte | 30.4% |
| Cass | 28.8% |
| Clay | 26.9% |
| Buchanan | 24.9% |
| Bates | 22.7% |
| Vernon | 22.2% |
| Jasper | 20.0% |
| Barton | 19.9% |
| Andrew | 9.5% |
| Holt | 8.8% |
| Newton | 8.1% |
| McDonald | 7.3% |
| Atchison | 7.0% |
| 14 border counties | 37.7% |
| All Missouri | 11.6% |

- Every travel share in this log is a share of **out-of-county visits to Missouri counties**. For Jackson that is
  under half its observed out-of-county travel; a Missouri destination's share of all its travel is the stated share ×
  0.475. Illinois, Iowa, Arkansas, Oklahoma and Nebraska destinations are not in the data, so the eastern and southern
  border counties (St. Louis area included) are understated by an unmeasured amount.
- The adopted outcome is not renormalised. With home-county fixed effects the fit is conditional on each county's
  Missouri total, so the coefficients are those of travel among Missouri counties; renormalising would rescale every
  Missouri share of a border county by a constant and change no comparison within that county. Comparisons across
  counties of a share's size (e.g. Kansas City-area counties against interior ones) must use the Kansas-inclusive
  denominator or say they exclude Kansas.

### Rejected

Each scored held out against the adopted model; change in held-out error [95%]; coefficient (two-way p):

| Tested | Result | Script |
|---|---|---|
| Jobs per resident; metro destination; stores per resident | Singly-constrained model only (above); absorbed by destination effects | `travel_model_compare.py` |
| Hospital indicator | See measurement corrections; hospital terms under County characteristics | — |
| Area-centre term in the doubly-constrained model | Absorbed by destination fixed effects | `travel_model_hub_test.py` |
| Same metro/micro area | +0.00 [−0.06, +0.07]; −0.112 (p = 0.09) | `travel_model_hub_test.py` |
| Nearest area centre | −0.01 [−0.08, +0.05]; +0.077 (p = 0.18) | `travel_model_hub_test.py` |
| Adjacent area centre | +0.00 [−0.03, +0.04]; p = 0.30 | `travel_model_hub_test.py` |
| Intervening opportunities (population closer than the destination) | +0.03 [−0.04, +0.08]; p = 0.20 | `travel_model_hub_test.py` |
| All four together | +0.05 [−0.04, +0.14] | `travel_model_hub_test.py` |
| Destination size × distance (in the pre-commuting model) | 3.74 with both size terms against 3.71 with origin size × distance alone | `travel_model_dc_test.py` |
| Adjacent centre + nearest centre | −0.01 [−0.08, +0.05]; p = 0.68, 0.29 | `travel_model_dc_test.py` |
| Driving time between main towns (OpenStreetMap routes) in place of straight-line distance | +0.07 [−0.14, +0.31]; in-sample deviance 68.8M → 65.6M | `travel_model_drive_test.py` |
| Driving time + on the way to a bigger centre (destination lies on the route to a larger centre) | −0.05 [−0.27, +0.22]; +0.171 (p < 0.001) | `travel_model_drive_test.py` |
| Driving time + on-the-way weight | −0.06 [−0.31, +0.19]; p = 0.12 | `travel_model_drive_test.py` |
| Competing destinations: nearest comparable alternative (log distance to the nearest destination with as many places ÷ distance to this one) | −0.051 [−0.100, −0.002]; −0.065 (p = 0.04); fails the nested test (below) | `travel_competing_test.py` |
| — the same, other directions only (60°+ off the bearing) | −0.01 [−0.04, +0.02]; p = 0.41 | `travel_competing_test.py` |
| — Fotheringham C_ij = Σ(k≠i,j) W_k/d_jk (Haynes & Fotheringham 1985) | +0.02 [−0.08, +0.14]; −1.04 (p < 0.001); in-sample deviance 68.8M → 67.2M | `travel_competing_test.py` |
| Business gaps (CBP 2022), one at a time and all six | Not testable: log(dest + 1) − log(origin + 1) is a destination term minus an origin term, absorbed exactly by the two sets of fixed effects (rank-deficient design; every score unchanged). The earlier result was this artefact | `travel_business_test.py` |
| Origin-class-specific pair terms (k = 4) | all +0.17 [+0.00, +0.35]; hubs −0.11 [−0.67, +0.46]; independent towns +0.51 [+0.17, +0.87] | `travel_county_class_model.py` |
| Origin-class-specific, k = 2 / k = 3 | +0.08 [−0.06, +0.22] / +0.09 [−0.08, +0.27] | `travel_county_class_model.py` |
| Work and non-work modelled apart (non-work with commuting) | −0.00 [−0.01, +0.01] | `travel_purpose_split_test.py` |
| — non-work without commuting | +0.41 [+0.19, +0.65]; Audrain → Marion 2.40× → 1.96× in-sample | `travel_purpose_split_test.py` |
| Pass-through as recorded (no discount) | held-out error 3.18 against its own outcome (3.26 discounted); not comparable as a change: the outcomes differ | `travel_model_stop_discount_test.py` |

The nearest-comparable-alternative term passes one at a time and fails the nested test, the guard against choosing
among many candidates (`combined_marginal_test.py travel_nested_all`; 24 candidates — the eight route/area terms alone
and together, the three competing-destination terms, ten home-county ACS measures × distance, the two hospital terms —
chosen inside each outer training set, 7 inner folds):

| Procedure | Held-out error | Change vs adopted [95%, county-paired, 1,000 draws] |
|---|---:|---:|
| Adopted (same folds) | 3.259 | |
| Nested: lowest inner error | 3.209 | −0.050 [−0.232, +0.145] |
| Nested: selection rule applied inside the training counties | 3.218 | −0.041 [−0.173, +0.112] |
| One at a time, not nested: + nearest comparable alternative | 3.208 | −0.051 [−0.100, −0.002] |

Inner choices by the rule: "+ on the way to a bigger centre" in 4 of 8 outer folds, the nearest comparable
alternative in 1, all eight route/area terms in 1, the adopted set in 2. **Rejected: passes one at a time at 5% among
about 30 candidates; fails the nested test.** The Fotheringham term shows in the fit (deviance, p) and not in
prediction; the destination fixed effects already measure each centre's draw.

Main destinations, actual ÷ expected share, adopted model (in-sample / held out; `travel_model_dc_test.py`): Osage →
Cole 1.09 / 1.14, Osage → Boone 1.64 / 1.59, Audrain → Boone 0.97 / 1.01, Audrain → Callaway 1.39 / 1.30, Audrain →
Marion 2.40 / 2.21, Boone → Cole 0.70 / 0.68, Boone → St. Louis County 1.33 / 1.29.

The routing (`build_drive_routes.py` → `drive_od.csv`) is kept: it confirms, for example, that Mexico → Columbia
(38 minutes) runs through Callaway County. Half of Audrain residents' Callaway visits are in Kingdom City, but the
pass-through discount removes only 20% of that pair's visits (2026-10-16 figure, not rerun); the rest (Fulton is 22
minutes from Mexico) is ordinary local travel.

### Small counties and pair-level commuting

The pooled travel model fits large counties best: Poisson weights by count, so big flows drive the fit. Tested for the
counties it serves worst, public data only. Tiers: k-means on log population (ACS 2020–2024) and commuting outflow
(LODES 2023) (`county_class_k4.csv`): small rural 56 (median 10,600, 67% commute out), independent towns 32, commuter
18, hubs 8. The file has 114 rows, with no row for St. Louis city; scored, St. Louis city is a ninth hub and St.
Louis city and county are scored apart (115 home counties: hubs 9).

| Tested (held out; share-weighted error, change vs the model it modifies [95%]) | Result | Script |
|---|---|---|
| **Commuting out and in, added to the pre-commuting model (adopted 2026-10-18)** | **all 3.71 → 3.26 (−0.45 [−0.70, −0.21]); small rural 3.94 → 3.44 (−0.50 [−0.88, −0.08]); independent towns 3.18 → 2.83 (−0.35 [−0.61, −0.08]); commuter 4.28 → 3.85 (−0.42 [−1.16, +0.27]); hubs 3.04 → 2.47 (−0.57 [−1.58, +0.40]); small rural top-3 (forecast) 4.86 → 4.31** | `travel_commute_pair_test.py` |
| Commuting out alone | all 3.31 (+0.06 [−0.10, +0.20] vs both) | `travel_commute_pair_test.py` |
| Separate model for small origins (< 15,000; 48 counties) into larger counties | best (size rank within 60 mi) 3.76 [3.21, 4.35] against the pooled model's 3.32 [2.78, 3.93] on the same pairs | `travel_small_origin_model.py` |
| Destination draw from measured attributes + Fotheringham in place of destination effects | small origins +0.94 [+0.53, +1.36]; others +1.33 [+0.60, +2.17] | `travel_small_county_test.py` |
| Destination effects shrunk toward that theory model (alpha 1e-4 to 1e-2, all shown) | Jul–Sep 3.11 against 3.05 (small origins); no gain at any alpha | `travel_small_county_test.py` |
| Tier-specific and county-by-county pull of destination jobs and retail (LODES; CBP 2022); small rural counties held out, share error / top-3 error | pooled 3.86 / 4.80, tier pull 3.81 / 4.72, theory (no destination effects) 4.40 / 5.28, county pull 3.82 / 4.70, tier + local 3.88 / 4.78 (standardised on training rows per fold) | `travel_tier_pull_cv.py` |
| Distance to the destination's job hub (worker-weighted mean, median; nearest, farthest edge) | small rural held out: 3.35 centroid against 3.40–3.48 (+0.05 to +0.13, every interval spans zero) | `travel_distance_variants.py` |
| Blend of the county's own Jan–Jun shares with the model (k = 300, chosen on Jan–Apr → May–Jun) | Jul–Sep 1.51, equal to persistence (−0.00 [−0.01, +0.01]): the blend is the observed shares | `travel_blend_test.py` |

Pair-level commuting is the first public measure that predicts a county's travel markedly better without its own
travel data, and is in the shared gravity terms (`gravity_terms.py`), so the travel and coverage models both carry it.
Travel: out +0.284 (s.e. 0.051), in +0.192 (0.036), both p < 0.001 (two-way). The gain is clear for all counties
together, small rural counties and independent towns; for commuter counties and hubs (18 and 9 counties) the
intervals include zero. Coverage: commuting in +0.42 (s.e. 0.073, clustered by newsroom county), out −0.02 (n.s.):
newsrooms cover the counties whose workers commute into theirs. Commuting explains Osage's travel to Jefferson City
(Osage → Cole 1.09 in-sample); travel to Columbia, where few Osage residents work, is for shopping, health care and the
university and stands out (Osage → Boone 1.64). Spillover does not use the travel model.

### Public-data travel model (Stage 1) and Advan-learned corrections (Stage 2), 2026-10-18; revised 2026-10-24

Question: how close a travel model built from public data alone gets to the Advan-fitted model, and how much of the
gap Advan-learned corrections close. Outcome: the adopted Advan outcome (`gravity_terms.travel_visits`), each home
county's out-of-county Missouri destination shares, January–September 2026. Every score is out of sample for the
county scored:

| Element | Rule (2026-10-24) |
|---|---|
| Destination set | One set for every model: the public model's destinations (counties within 200 miles of the tract). Advan and the Advan-fitted model are renormalised over it. Outside it: 2,968 pairs, 1.37% of Advan share per county on average (max 8.5%) |
| Metrics | Share-weighted error, 100 × Σ a\|p − a\| (points); log-ratio error, mean \|ln(p/a)\| over pairs with Advan share ≥ 1% (p floored at 0.01%). The first scales with concentration (r × HHI for a uniform relative miss r); the second is scale-free, symmetric, and counts the 1–5% pairs. exp(0.41) = ×1.5 typical miss. `public_scoring.py` |
| Averaging | County mean (each home county weighs the same); St. Louis city and county scored apart (115 homes) |
| Intervals | County-paired bootstrap, 2,000 draws, 95% percentile; the all-county interval resamples within each class. "Worse" or "better" only where the interval excludes zero (*) |
| Benchmark | Advan-fitted: the adopted model (`gravity_terms.FACTORS`), each county held out, 8 folds, seed 7 (`public_vs_advan_compare.py` → `compare_shares.csv`) |
| Stage 1 | Each class's public setting chosen by Advan error with the scored county left out (nested). No Advan in any parameter; Advan chose among settings |
| Stage 2 | Corrections learned on other counties (8 folds); their structure chosen inside an outer loop (below) |

Classes (`score_segments.py`): the k-means tiers above; commuter counties split by the OMB 2023 delineation into rings
of the Kansas City and St. Louis metros (9) and rings of regional hubs or outside any metro (9).

**Public model** (`public_work_model.py`, `public_travel_tiers.py`, `assemble_public_by_class.py`), tract origins
(CenPop2020 tract centres), destinations every county within 200 miles in Missouri and the eight neighbouring states:

| Part | Public data and calculation |
|---|---|
| Work | LODES 2023 tract → county, Missouri main OD plus the IL, KS, IA, AR, OK, NE, TN, KY auxiliary files (33,990 Missouri residents work in Illinois); observed flows within 90 miles, a gravity fit (conditional Poisson on distance, CBP employment, population, state line) beyond, where LODES carries employers' imputed establishment assignments |
| Retail | Trade area analysis: 2025 Missouri DOR taxable sales by county; pull factor; income-adjusted trade area capture (ACS per-capita income); leakage = 1 − capture; Huff allocation on taxable sales (hubs: on sales beyond the county's own expected, Reilly's exponent 2) |
| Chained errands | Errand trips starting at work (2022 NHTS, WHYFROM 3–5): 1.3 (urban) and 2.0 (rural) a month per worker, sent to the work counties |
| Medical, specialty | CBP 2022 health care; furniture, electronics, clothing, sporting goods, department stores (central place: higher-order goods) |
| Recreation, visiting | 2022 NHTS long-distance file (vacation; visiting family or friends), weighted by days away; draws CBP arts and recreation employment, 2020 population |
| Decay | Calibrated to the NHTS trip-length distribution (maximum likelihood over distance bands), rural and urban households |

Settings tested on the reference build (2026-10-18, old outcome, in-sample; not rerun; `public_default_sensitivity.py`):
work-from-home (ACS B08006), circuity 1.0/1.4, shopping rate ×0.5, medical and specialty ×0.5/×2, long-distance trips
not days — each within ±0.15 to 0.40 of the reference; the weight on commuting moved most (more work days better up to
40 in three classes). Rejected then: the visitation law's exponent 2 for every kind (small rural +1.38; rural decay is
steeper, about 4–6), Huff attraction exponent 0.5 (+0.42), establishment counts and employment as the shopping draw
(zero weight once taxable sales are in), non-work decay by income, degree or tenure (−0.17 to −0.18, kept out for the
survey's thin subgroups), metro-size survey classes (+0.52).

**Stage 1, setting per class** (`public_stage1_nested.py`). Candidates: the 53 Missouri builds of
`public_travel_tiers.py` (by-class assemblies, Kansas builds and regular-travel builds excluded). Rule: lowest mean
share-weighted error over the class's other counties.

| Class | Setting chosen on all counties (used in Kansas) | Leave-one-out picks |
|---|---|---|
| Small rural (56) | observed LODES within 90 mi, 40 work days per out-of-county commuter, chained errands, Huff on sales (`_g_40_sales`) | the same, 56 of 56 |
| Independent towns (32) | the same with decay 6 for retail, medical, specialty (`_c_40_l6all`) | 23; Huff on surplus sales (`_g_40_surplus`) 9 |
| Commuter: major metro (9) | reference build, Huff attraction exponent 1.5 (`_s_alpha15`) | 4 different settings: `_s_ruralset` 3, `_s_alpha15` 3, `_s_circ14` 2, `_c_10_l6all` 1 |
| Commuter: regional hub (9) | reference build, gross leakage (Huff home share), commuter classes on urban decay (`_s_commset`) | 9 of 9 |
| Hubs (9) | observed LODES within 90 mi, 15 work days, Huff on surplus sales (`_g_15_surplus`) | 6; `_g_25_surplus` 3 |

The major-metro rings have no stable setting: four settings among nine leave-one-out choices, and the nested error
(6.96) is 1.60 above the in-sample one (5.36).

**Where the gap is** (2026-10-18, in-sample, old outcome, against the 5.35 reference; `public_gap_diagnosis.py`,
`public_gap_corrections.py`; not rerun): one Advan correction at a time, destination pull closes 46% of the gap, the
shape of distance decay 21%, adjacency 12%, together 68%. The public model overstates the metro cores (St. Louis City
0.23×, St. Louis County 0.50×, Jackson 0.65×) and understates regional centres and small rural destinations (Greene
1.42×; Knox, Scotland, Schuyler, Shannon 2.2–3.0×); its single power law sends twice too much to the nearest counties
and, for hubs, half the travel beyond 120 miles.

**Stage 2, Advan-learned corrections** (`public_adjusted_model.py`, applied to tract shares and rolled up):
multiplicative factors, fitted in turn and iterated, for distance band by class (learned apart for each home county's
dominant and secondary LODES commuting counties), adjacency by class, LODES commuting rank by class, destination order
by class, destination class by class. Destination order follows the central place hierarchy from public data
(transferable definitions): metro core = central county of a metro area of 1,000,000 or more (OMB 2023; Census 2024
CBSA population); rest of such a metro; regional centre = pull factor ≥ 1 and at least 60,000 trade-area customers
(taxable sales ÷ the state's per-capita taxable sales — about $1 billion in Missouri); sub-regional town = pull factor
≥ 1; resort = marinas plus RV parks and recreational camps per resident in the top tenth of U.S. counties (CBP 2022);
local; a core or big-metro county within 50 miles of home is its own order. Pull factor, trade area capture and miles
are already relative or universal. Modes: C segment factors only (transferable); B + destination factor from public
measures (log sales, log population, nonmetro, log arts employment); A + one factor per destination county (Missouri
only).

**Outer loop** (`public_adjusted_nested.py`). For each of the 8 folds of home counties: (1) Stage 1 is chosen on the
other 7 folds; (2) each of 245 candidate structures is scored by inner cross-validation on the other 7 folds only; (3)
the lowest inner error is learned on the 7 folds and applied to the held-out fold. Each mode chooses its own structure.
Candidates: the full factorial of the refinement choices — commuter split (none; split; split learned as independent
towns; split learned as small rural) × distance by commuting rank (0/1) × near-core order (0/1) × destination-order
definitions (Missouri, regional centre at pull factor 1.1; at 1.0; transferable) × group sets (none; commuting out and
in; destination order; + commuting rank; + destination class) = 240 — plus the five rejected variants on the adopted
structure (rank × order cell; destination class × band; pooled hub factor; hub distance bands; metro-core factor).

Structure chosen per outer fold, mode C: the adopted structure with a metro-core factor (folds 2, 4, 7) or a pooled hub
factor (0, 1); the adopted structure on Missouri definitions, pull factor 1.0 (3, 6); split learned as small rural,
pull factor 1.1, no destination class (5). Mode A: a different structure in nearly every fold (destination order only;
no groups; no split with commuting rank). Stage 1 per outer fold: the hub-ring setting changes in fold 1 (Lawrence, Polk
and Pulaski held out: `_c_hyb40_40`), the major-metro setting in folds 0, 1, 6, the independent-town setting in folds
1, 2, 4, 7, the hub setting in folds 2 and 7 (`public_adjusted_nested_choices.csv`).

#### Missouri (115 home counties)

Share-weighted error, points:

| Model | Small rural (56) | Indep. towns (32) | Commuter: major metro (9) | Commuter: regional hub (9) | Hubs (9) | All (115) |
|---|---:|---:|---:|---:|---:|---:|
| Advan-fitted (counties held out) | 3.51 | 2.95 | 4.36 | 3.41 | 2.61 | 3.34 |
| **Public, setting chosen nested** | 4.38 | 4.78 | 6.96 | 5.47 | 5.25 | **4.85** |
| Public, setting chosen in-sample (not out of sample) | 4.38 | 4.64 | 5.36 | 5.47 | 5.11 | 4.67 |
| **+ segment corrections, outer loop (C, transferable)** | 3.53 | 3.97 | 4.05 | 6.12 | 4.54 | **3.97** |
| + destination factor from public measures, outer loop (B) | 3.58 | 3.99 | 3.88 | 5.65 | 4.52 | 3.95 |
| + one factor per destination county, outer loop (A, Missouri only) | 3.10 | 3.52 | 4.31 | 5.91 | 2.35 | 3.47 |
| + segment corrections, structure chosen in-sample (not out of sample) | 3.53 | 3.80 | 3.51 | 4.27 | 4.10 | 3.71 |

| Log-ratio error, mean \|ln(p/a)\| | Small rural | Indep. towns | Commuter: major metro | Commuter: regional hub | Hubs | All |
|---|---:|---:|---:|---:|---:|---:|
| Advan-fitted | 0.36 | 0.40 | 0.29 | 0.28 | 0.28 | 0.35 |
| **Public, nested** | 0.48 | 0.56 | 0.64 | 0.43 | 0.66 | **0.53** |
| **+ corrections, outer loop (C)** | 0.43 | 0.50 | 0.36 | 0.44 | 0.51 | **0.45** |
| + public destination factor, outer loop (B) | 0.43 | 0.50 | 0.35 | 0.42 | 0.51 | 0.45 |
| + per-destination factor, outer loop (A) | 0.38 | 0.44 | 0.36 | 0.37 | 0.37 | 0.39 |

Differences, 95% intervals (share-weighted / log-ratio; * = excludes zero):

| Difference | Small rural | Indep. towns | Commuter: major metro | Commuter: regional hub | Hubs | All |
|---|---|---|---|---|---|---|
| Public nested − Advan-fitted | +0.87 [+0.20, +1.59]* / +0.12 [+0.09, +0.15]* | +1.83 [+1.17, +2.57]* / +0.16 [+0.11, +0.21]* | +2.60 [+0.36, +4.80]* / +0.35 [+0.22, +0.51]* | +2.05 [−0.34, +4.63] / +0.15 [+0.05, +0.25]* | +2.64 [+0.86, +4.82]* / +0.38 [+0.22, +0.59]* | +1.50 [+1.02, +2.01]* / +0.17 [+0.14, +0.20]* |
| C outer − Advan-fitted | +0.02 [−0.54, +0.57] / +0.06 [+0.04, +0.09]* | +1.01 [+0.53, +1.51]* / +0.11 [+0.07, +0.14]* | −0.31 [−2.72, +2.29] / +0.07 [−0.02, +0.18] | +2.71 [+0.30, +5.41]* / +0.16 [+0.06, +0.27]* | +1.93 [+0.43, +3.43]* / +0.23 [+0.09, +0.37]* | +0.63 [+0.19, +1.07]* / +0.10 [+0.07, +0.12]* |
| B outer − Advan-fitted | +0.07 [−0.50, +0.62] / +0.06 [+0.04, +0.09]* | +1.04 [+0.56, +1.55]* / +0.10 [+0.07, +0.14]* | −0.48 [−2.91, +2.10] / +0.06 [−0.02, +0.17] | +2.24 [−0.03, +4.79] / +0.14 [+0.04, +0.26]* | +1.91 [+0.40, +3.37]* / +0.23 [+0.10, +0.38]* | +0.61 [+0.17, +1.05]* / +0.09 [+0.07, +0.12]* |
| A outer − Advan-fitted | −0.41 [−0.93, +0.10] / +0.01 [−0.01, +0.04] | +0.56 [+0.06, +1.09]* / +0.04 [+0.02, +0.07]* | −0.05 [−1.61, +1.59] / +0.06 [−0.01, +0.15] | +2.50 [+0.28, +4.98]* / +0.09 [+0.01, +0.18]* | −0.26 [−1.81, +1.11] / +0.08 [+0.02, +0.15]* | +0.13 [−0.26, +0.54] / +0.04 [+0.02, +0.05]* |
| C outer − public nested (gain from Advan) | −0.85 [−1.31, −0.38]* / −0.06 [−0.08, −0.04]* | −0.82 [−1.51, −0.15]* / −0.06 [−0.10, −0.01]* | −2.90 [−5.31, −0.92]* / −0.28 [−0.35, −0.21]* | +0.66 [−0.71, +1.93] / +0.01 [−0.03, +0.05] | −0.71 [−2.66, +1.16] / −0.15 [−0.24, −0.06]* | −0.88 [−1.26, −0.49]* / −0.08 [−0.09, −0.06]* |
| A outer − public nested | −1.28 [−1.91, −0.65]* / −0.11 [−0.13, −0.08]* | −1.27 [−2.07, −0.44]* / −0.12 [−0.16, −0.07]* | −2.65 [−4.87, −0.11]* / −0.28 [−0.39, −0.19]* | +0.45 [−2.21, +3.45] / −0.06 [−0.12, −0.00]* | −2.90 [−5.47, −0.93]* / −0.30 [−0.54, −0.12]* | −1.37 [−1.89, −0.88]* / −0.14 [−0.16, −0.11]* |

- Public data alone: 1.50 points [1.02, 2.01] above the Advan-fitted model on the share-weighted error, worse in every
  class on the log-ratio error.
- With transferable corrections the difference from the Advan-fitted model is not detectable in small rural counties
  (+0.02 [−0.54, +0.57]) and major-metro rings (−0.31 [−2.72, +2.29]) on the share-weighted error; on the log-ratio
  error it remains in every class but the major-metro rings.
- With one factor per destination county (Missouri only) the difference is not detectable overall on the
  share-weighted error (+0.13 [−0.26, +0.54]) and remains on the log-ratio error (+0.04 [+0.02, +0.05]).
- The corrections help small rural counties, independent towns and major-metro rings (both metrics); hubs on the
  log-ratio error only; regional-hub rings on neither (+0.66 [−0.71, +1.93]).
- Out of sample the corrections close 58% of the gap between the nested public model and the Advan-fitted model
  (4.85 → 3.97 against 3.34); per-destination factors 91%.
- Regional-hub rings: the outer loop costs 1.85 points against the in-sample structure (4.27 → 6.12), four-fifths of
  it in fold 1, whose Stage 1 takes a different setting once Lawrence, Polk and Pulaski are held out (Lawrence 1.97 →
  8.96, Polk 6.33 → 12.42). Nine counties are too few to choose a setting reliably.
- Destination-order factors (Advan / public; 2026-10-18, all counties): metro core 0.65–0.99, regional centre
  1.35–1.51, sub-regional town 1.09–1.42, local 0.88–0.98, resort 0.84–1.11 — the public model's draw is too steep in
  size and too flat in the hierarchy.

**Commuter counties.** One class held two behaviours. Major-metro rings spread travel over several metro counties and
commute to the core while visiting the nearest large county (St. Charles → St. Louis County: LODES 75%, Advan 57%;
Warren → St. Charles 34% vs 47%). Regional-hub rings send 65–73% to one hub (Polk, Newton, Christian). Split, the
metro-ring corrections close the gap to the Advan-fitted model (3.88–4.31 out of sample against 4.36, intervals
include zero); the regional-hub rings are not improved by any correction out of sample, because the near-hub relation
(Jasper is 14 miles from Newton) is learned elsewhere as an overstated small neighbour. Population is not the cause
(2026-10-18: under 50k 4.37, over 100k 4.09; not rerun).

**Refinements, 2026-10-18** (`public_adjusted_model.py`, `score_segments.py`; in-sample structure selection, old
outcome, full destination set — superseded by the outer loop above, kept as the record of what was tried):

| Change | Small rural | Indep. towns | Commuter: major metro | Commuter: regional hub | Hubs | All |
|---|---:|---:|---:|---:|---:|---:|
| Segment corrections | 3.43 | 3.52 | 3.93 | 6.40 | 3.48 | 3.73 |
| Regional centre at pull factor ≥ 1.0 (was 1.1): Jasper's pull factor is 1.08 because its own metro includes Newton | 3.41 | 3.51 | 3.94 | 6.12 | 3.48 | 3.69 |
| + a metro core within 50 miles of home is its own order | 3.35 | 3.43 | 3.88 | 5.81 | 3.68 | 3.63 |
| Transferable definitions + near core | 3.40 | 3.46 | 3.81 | 5.62 | 3.49 | 3.63 |

Every choice in this table is one of the outer loop's 245 candidates. Rejected 2026-10-18, also candidates in the
outer loop: a pooled hub relation; hub pairs with their own distance bands; a metro-core factor per class; a commuting
rank × destination order cell; destination class × distance band. The outer loop chose the pooled hub factor in folds
0–1 and the metro-core factor in folds 2, 4, 7: the rejections were within noise. Fitting the mixture weights of the
public parts to Advan by class (`public_segment_weights.py`, 4.49 in-sample) remains parked.

Regional-hub rings, county by county (2026-10-18): Newton (Jasper labelled sub-regional), Johnson (the core factor
learned from distant homes cut Jackson from 37% to 26%; the near-core order), Polk (Greene 52% vs 68%), Lawrence
(Barry 20% vs 9%), Stone (Taney 25% vs 19%); Webster and Callaway right on the public base.

#### Transfer test: Kansas (2026-10-18; revised 2026-10-24)

Advan Neighborhood Patterns Plus, Kansas destination block groups, January–September 2026 (`neighborhood/raw_ks/`),
plus Kansans' visits to Missouri from the Missouri files (`build_ks_od.py` → `od_ks_2026.csv`); Kansas outcome not
pass-through discounted (no Kansas road-stop shares). Kansas public inputs: LODES 2023 Kansas main OD and the MO, NE,
OK, CO auxiliary files; CenPop2020 Kansas tracts; ACS 2020–2024 tract and county (B19301) tables; Kansas Department of
Revenue County Trade Pull Factors FY2025 (`build_ks_pull_factors.py`). County classes by nearest Missouri class centre
on log population and commuting outflow (`build_ks_county_classes.py`), population ACS 2020–2024 B01003 in both states:
30 small rural, 63 independent towns, 4 commuter, 8 hubs.

Applied unchanged from Missouri: each class's Stage 1 setting chosen on all Missouri counties
(`assemble_public_by_class.py STATE=20`), and the transferable structure with the lowest 8-fold score on all Missouri
counties — the adopted structure plus a metro-core factor per class (3.71) — learned on all Missouri counties
(`public_adjusted_nested.py` → `segment_corrections_mo.pkl`; `transfer_adjustments.py`). Kansas is held out entirely,
so both choices are out of sample for it. Benchmark: `ks_advan_fitted.py`, the adopted model's form fitted to Kansas
Advan, counties held out (8 folds), destinations within 250 miles. Scored by `score_ks.py` on the common destination
set: pairs every model covers (public: within 200 miles of a tract, about 220 miles county to county; benchmark: 250
miles). Outside it: 9.13% of Advan share per county on average, max 40.7% (Thomas) — western Kansas travel to Wichita,
Topeka and Kansas City beyond the public model's 200 miles. Classes with fewer than 5 counties are not reported as
classes: the four commuter counties are listed one by one and pooled only for the interval.

| Kansas, share-weighted error | Small rural (30) | Indep. towns (63) | Hubs (8) | All (105) | Butler (Wichita ring) | Leavenworth (KC metro) | Miami (KC metro) | Wyandotte (KC metro) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Advan-fitted in Kansas | 4.15 | 3.06 | 1.78 | 3.27 | 2.50 | 1.75 | 6.42 | 0.35 |
| **Public model, Missouri settings, nothing tuned in Kansas** | 4.10 | 4.59 | 2.94 | **4.29** | 5.38 | 2.42 | 5.72 | 1.79 |
| + corrections learned in Missouri | 3.83 | 4.16 | 4.95 | 4.27 | 7.37 | 7.24 | 10.98 | 6.61 |

| Kansas, log-ratio error | Small rural | Indep. towns | Hubs | All | Butler | Leavenworth | Miami | Wyandotte |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Advan-fitted in Kansas | 0.39 | 0.37 | 0.25 | 0.36 | 0.16 | 0.23 | 0.28 | 0.18 |
| **Public model, Missouri settings** | 0.49 | 0.53 | 0.44 | **0.50** | 0.27 | 0.35 | 0.33 | 0.22 |
| + corrections learned in Missouri | 0.51 | 0.56 | 0.46 | 0.54 | 0.61 | 0.59 | 0.47 | 0.53 |

| Kansas difference, 95% interval (share-weighted / log-ratio) | Small rural | Indep. towns | Hubs | All | Commuter (4, pooled) |
|---|---|---|---|---|---|
| Public − Advan-fitted | −0.06 [−1.10, +0.90] / +0.09 [+0.05, +0.14]* | +1.52 [+0.88, +2.18]* / +0.16 [+0.12, +0.20]* | +1.16 [+0.33, +2.07]* / +0.19 [+0.10, +0.28]* | +1.03 [+0.53, +1.52]* / +0.14 [+0.11, +0.17]* | +1.07 [−0.16, +2.33] / +0.08 [+0.04, +0.12]* |
| Corrected − Advan-fitted | −0.32 [−1.51, +0.82] / +0.12 [+0.06, +0.17]* | +1.09 [+0.55, +1.65]* / +0.18 [+0.14, +0.23]* | +3.17 [+0.50, +6.28]* / +0.21 [+0.12, +0.30]* | +1.01 [+0.47, +1.51]* / +0.17 [+0.14, +0.20]* | +5.29 [+4.72, +5.91]* / +0.34 [+0.23, +0.42]* |
| Corrected − public | −0.27 [−0.77, +0.34] / +0.02 [−0.00, +0.06] | −0.43 [−0.88, −0.02]* / +0.03 [+0.01, +0.04]* | +2.01 [−0.18, +4.59] / +0.02 [−0.04, +0.07] | −0.02 [−0.38, +0.34] / +0.03 [+0.02, +0.05]* | +4.22 [+2.70, +5.15]* / +0.26 [+0.18, +0.32]* |

- The public model transfers at about the distance it keeps in Missouri: +1.03 [+0.53, +1.52] above the Kansas
  Advan-fitted model (Missouri, nested: +1.50 [+1.02, +2.01]). In small rural counties the share-weighted difference is
  not detectable (−0.06 [−1.10, +0.90]); the log-ratio error is worse.
- The Missouri corrections give no net gain in Kansas (−0.02 [−0.38, +0.34]; log-ratio +0.03, worse). They help
  independent towns (−0.43 [−0.88, −0.02]) — the rural-to-regional-centre relation transfers (Harper 11.50 → 3.23,
  Cowley 11.74 → 5.87, Barber 5.99 → 2.70, Lane 7.08 → 4.55; ties to Wichita and Garden City) — and hurt the commuter
  counties (+4.22 [+2.70, +5.15]), the Kansas City-side hubs (Johnson 4.18 → 10.77, Douglas 2.25 → 10.21) and
  Doniphan (1.59 → 6.52): the core and near-dominant-county factors were learned from St. Louis and Kansas City as seen
  from Missouri, and in Kansas the 1M+ metro-core definition takes in Johnson County and Wyandotte.

#### Changes, 2026-10-24 (peer review)

| Defect | Fix | Files |
|---|---|---|
| Stage 1 setting per class chosen and scored on the same counties (4.30–4.34) | Leave-one-county-out choice within the class; nested figure reported, in-sample stated as such | `public_stage1_nested.py`, `assemble_public_by_class.py` (reads the choice) |
| Stage 2 structure chosen on the score it reported | Outer loop, 8 folds; Stage 1 and the structure chosen on the other 7 folds; full factorial of 240 + 5 rejected variants | `public_adjusted_nested.py`; `public_adjusted_model.py` refactored into `keys/learn/apply/cv` (identical output to 1e-15 on the old inputs) |
| No uncertainty on comparisons | County-paired bootstrap, 2,000 draws, per class and all, Missouri and Kansas | `public_scoring.py`, `score_segments.py`, `score_ks.py` |
| Class cells of 3 and 1 counties (Kansas) | Not reported as classes; the four commuter counties listed one by one, pooled for the interval | `score_ks.py` |
| Share-weighted error scales with concentration (HHI) | Log-ratio error beside it everywhere | `public_scoring.py`, `score_segments.py`, `score_ks.py`, `public_adjusted_model.py`, `public_stage1_nested.py`, `public_vs_advan_compare.py` |
| Destination sets differ (public 200 mi = 0 elsewhere, benchmark 250 mi, Advan uncapped) | One common set per state, Advan and every model renormalised; Advan share outside reported; Missouri corrections also learned on the common set | `public_adjusted_model.py`, `score_segments.py`, `score_ks.py` |
| `travel_tier_pull_cv.py`: standardisation used held-out counties' means and spreads | Means and spreads of the training rows, per fold (models 3–5) | `travel_tier_pull_cv.py` |
| Kansas classes on 2020 Census population, Missouri on ACS 2020–2024 | ACS 2020–2024 B01003 for Kansas (`census_dl/acs_tract/b01003.dat`); no county moved class | `build_ks_county_classes.py` |
| Outcome | The adopted outcome and benchmark (`gravity_terms.FACTORS`, `loco`) from the travel model's current code | `public_vs_advan_compare.py` (no longer execs `travel_commute_pair_test.py`'s old body) |

Also: `public_travel_tiers.py` reads the home state's classes for `URBAN_CLASSES` (was Missouri's in every state);
Kansas builds added for `_s_alpha15`, `_s_commset`, `_s_hr`, `_g_15_surplus`, `_g_40_surplus` (the `_s_` recipes
rebuilt with today's code differ from the 2026-10-18 Missouri files by 0.02% of share); `transfer_adjustments.py`
applies whatever structure the pickle carries; `compare_shares.csv` loses the parked `public_segment` column.
`public_adjusted_pairs_trnear.csv` (the 2026-10-18 structure, read by `tie_footprint.py`, `public_activity_space.py`,
`directions_per_tract.py`) regenerated on the new outcome and destination set: segment corrections 3.84 all counties.
Outputs: `public_stage1_choice.csv`, `public_stage1_nested_pairs.csv`, `public_adjusted_nested_pairs.csv`,
`public_adjusted_nested_choices.csv`, `public_adjusted_nested_configs.csv`, `public_transfer_choice.csv`,
`mo_scores_nested.csv`, `ks_scores.csv`, `ks_predictions.csv`, `segment_corrections_mo.pkl`,
`public_model_pairs_tiers[_20]_byclass_nested.csv`; cache `public_stage1_variants.npz`; logs `logs/adj_nested.log`,
`logs/score_segments_nested.log`, `logs/score_ks.log`.

**Audrain's north/south split** is one tract (950100, Vandalia-Laddonia): 16.9% of its out-of-county visits go to
Marion against 1.4–5.0% from the other tracts; under 1% of its workers work there. Its schools (Van-Far) play in the
Eastern Missouri conference with Pike, Ralls, Lincoln and Montgomery. The tract model gives 6.2% (2026-10-18 public
build); county-level corrections cannot move one tract.

**Athletic conferences** (datadesk visuals 34–36, Boone, Audrain, Osage; FIPS corrected: Cooper 29053, Howard 29089):
destinations within 80 miles that share a conference get 14% more travel than the Advan-fitted model predicts,
relative to the rest (pooled log ratio +0.06 vs −0.08; Audrain 1.14 vs 0.92, Osage 1.11 vs 0.95, Boone 0.89 vs 0.92;
against the 2026-10-18 Advan-fitted model, in-sample; not rerun). Conferences are assigned by enrollment and geography
and produce recurring travel and sports coverage: a central place channel between places of the same order. Statewide
test pending (school-level: MSHSAA conference and class, NCES locations, TIGER school districts).

### Changes, 2026-10-24 (peer review): travel model

| Change | Why |
|---|---|
| Primary validation is each home county held out (8 folds, seed 7), in `travel_model.py` and every travel script | The Jan–Jun → Jul–Sep split is beaten by persistence (R² 98.6% against 93.8%; error 1.51 against 3.01): it measures stability, not prediction |
| Persistence printed beside every Jul–Sep score | As above |
| R² = 1 − SSE/SST of shares; the old "% predicted" was a squared correlation | A squared correlation ignores bias and scale |
| Deviance labelled in-sample; top-destination ratio and big-flow scores computed on held-out predictions | The old table columns were in-sample |
| Big flows and each county's top destination selected on the FORECAST share | Selecting on the observed share biases the ratio upward (held out: 1.11× observed-selected, 1.02× forecast-selected) |
| Two-way clustered errors (home, destination) for every travel coefficient; naive Poisson and HC1 p-values removed | Pairs sharing a home or destination county are not independent |
| Distance terms centred at 25 miles, home log population at its mean | The uncentred log-distance coefficient was not an elasticity at any stated point |
| 95% bootstrap intervals over home counties for every held-out error and every difference | Differences such as 3.58 against 3.39 had no interval |
| Nested held-out choice of rejected terms (`combined_marginal_test.py`) | The factor-addition decision was scored on the same split that chose it |
| Every travel script uses the adopted outcome and the 8 adopted terms | `travel_model_dc_test.py`, the commuting, competing, class, small-county, distance, blend, business, purpose, civic and hospital scripts used undiscounted visits, uncalibrated visits (purpose split) or the 6 pre-commuting terms |
| Kansas destinations quantified | Missouri-only shares understate border counties' out-of-county travel |
| Singly-constrained reference defined explicitly (`gravity_terms.SINGLY`) | `travel_model_dc_test.py`'s "singly constrained" row and `travel_model_hub_test.py`'s "current" row had become the doubly-constrained pair terms without destination effects |

### Activity spaces and tie markets: the footprint of potential local news interest (2026-10-18; tie markets rescored 2026-10-24)

Claim: where residents live, work and travel regularly is their definition of local, and the activity-space footprint
of a place's population, strengthened by news ties, is a market within which they have an interest in news and
information. Activity space after Yuan & Xu (2022): external indicators (size, shape, orientation -- standard
deviational ellipse, radius of gyration, convex hull) and internal ones (regularly visited places, entropy). Advan
reports aggregates by home area, so these are the collective activity spaces of a home area's residents.

**Observed** (`activity_space.py`, 2026-10-18): Advan, January-July 2026 (2020 block groups), home tract -> destination
block group (`od_tract_bg_mo_2026_janjul.parquet`); regular = the block group in 4+ of 7 months; home county included
(where residents go, not how much each place matters). 3 km hexagons; footprint = the fewest hexagons holding 80% of
regular visits; market = the footprint closed over gaps of 2 hexagons, holes filled; separate markets = parts holding
5%+ of its area. Tracts, median: small rural 549 km2, 3 lobes, 79% of visits outside the home county; hubs 433 km2, 1
lobe, 24%. Replicability (odd vs even months, 1,653 tracts): market overlap (Jaccard) 0.78, same number of markets 74%.
Places (`place_activity_space.py`): Columbia's population is the primary activity space of 250,502 residents outside
the city at 10%+ of their regular visits (140,632 at 20%+): Boone, Callaway, Cole, Randolph, Audrain, Cooper, Saline,
Macon, Howard. Jefferson City 102,095 (Cole, Callaway, Moniteau, Miller, Osage); Moberly 22,355; Mexico 4,791.
Radius of gyration and convex hull computed over all regular visits are inflated by a few distant destinations; the
hexagon market is the robust measure.

**Tie market** (`tie_footprint.py`): the network tie of the market maps (`flows/market_patterns.py`) -- travel x (1 +
0.3 out + 0.3 in + 0.7 shared places + 0.7 shared coverage), gate, spatial lag and direction, home 100 -- from four
travel sources (Advan all months, odd months, even months; public); market = hexagons with a tie of 5+, closed. Public
travel: the regular-travel public model (`public_travel_tiers.py REGULAR=1`: long-distance business, specialty,
visiting and vacation trips dropped), per-class settings, Missouri segment corrections (mode C), LODES home-county
share, spread within counties by jobs, OpenStreetMap destinations and 2020 block-group population at distance^-0.5,
and Advan's regularity as a rule (`regularity_rule.csv`: logit of 4+ of 7 months on log share and log tract
population, 85.7% agreement; a block group counts at P >= 0.5 -- about 0.011% of a 4,000-person tract's visits).
Scoring (2026-10-24): the home county is in every market and the score is taken beyond it; the town's own units are
masked before ties are scaled. Run: `ATTRPOP=1 REGRULE=1 BETA_IN=0.5 PUBCOL=adjusted_C OUTTAG=_pop tie_footprint.py
<region>`; settings printed at the start of every run. Replicability = Advan odd vs even months; accuracy = public vs
Advan; both median Jaccard overlap over the market's study towns.

Current results (2026-10-24; `logs/tie_<region>.log`):

| 36 study towns, 7 markets | Replicability (Advan, odd vs even) | Accuracy (public vs Advan) |
|---|---:|---:|
| Kansas City (6) | 0.98 | 0.93 |
| Joplin (5) | 0.97 | 0.77 |
| Springfield (6) | 0.935 | 0.575 |
| St. Joseph (3) | 0.88 | 0.62 |
| Columbia (8) | 0.81 | 0.615 (travel alone 0.49) |
| Cape Girardeau (5) | 0.80 | 0.36 |
| Kirksville (3) | 0.74 | 0.59 |
| **All (median)** | **0.88** | **0.61** (mean 0.610) |

Towns: Columbia replicability 0.88, accuracy 0.13 (public area 0.16 of Advan's); Mexico 0.82, 0.41; Linn 0.88, 0.82.
The network terms raise public accuracy over travel alone (Columbia market 0.615 against 0.49): coverage ties and
shared third places are public data and pull the predicted market toward the observed one.

**The drop from 0.70, isolated** (`tie_footprint.py` diagnostics `CAMPUS_IN`, `REHOME`, `SCORE=2026-10-18`,
`MASKHOME`, `PUBFILE`). The 2026-10-18 state (public file as saved before its regeneration; campus papers counted; no
re-homing; market scored whole; home units not masked) reproduces the 2026-10-18 table: median 0.70 / mean 0.705
(published 0.70 / 0.707); Columbia 0.69, Mexico 0.46, Linn 0.68 exactly; 4 of 36 towns differ by more than 0.02. Each
change alone, from that state (36 towns, network tie):

| Change alone | Accuracy median / mean | Replicability median | Columbia (town) accuracy | Columbia public / Advan area |
|---|---:|---:|---:|---:|
| none (2026-10-18 state) | 0.70 / 0.705 | 0.91 | 0.69 | 1.20 |
| (1) public model file regenerated | 0.70 / 0.705 | 0.91 | 0.69 | 1.20 |
| (2) campus papers excluded | 0.70 / 0.703 | 0.91 | 0.69 | 1.20 |
| (3) two outlets re-homed | 0.70 / 0.705 | 0.91 | 0.69 | 1.20 |
| (4a) home county in every market, scored beyond it | 0.68 / 0.635 | 0.905 | 0.00 | 15.0 |
| (4b) the town's own units masked before scaling | 0.68 / 0.658 | 0.90 | 0.31 | 0.33 |
| (4a) + (4b), the scoring change in the script | 0.625 / 0.613 | 0.88 | 0.15 | 0.17 |
| all (current) | 0.61 / 0.610 | 0.88 | 0.13 | 0.16 |

By market (accuracy median, 2026-10-18 state -> current): Columbia 0.68 -> 0.62; Springfield 0.74 -> 0.57; Cape
Girardeau 0.49 -> 0.36 (campus exclusion alone 0.38: The Arrow); Kirksville 0.62 -> 0.59; Joplin 0.87 -> 0.77; Kansas
City 0.92 -> 0.93; St. Joseph 0.85 -> 0.62.

Cause: the scoring change (4a + 4b) accounts for 0.70 -> 0.625 of the median; the public file, campus exclusion and
re-homing move it by 0.00 alone (Cape Girardeau excepted) and 0.015 together with the scoring change. Columbia's 0.69
was an artifact of the old scoring: with home units unmasked, Columbia city was the town's busiest unit, every other
tie scaled against it, and both markets were the city and its edge (292 km2). 0.13 is not a code bug: with home masked
and the score taken beyond Boone, Advan's market beyond Boone is 518 hexagons and the public one 77. The public model
sends Columbia's out-of-county travel overwhelmingly to Jefferson City (the busiest non-home unit, 1.0; next Fulton
0.18), so Kansas City, Springfield and Moberly -- 0.70, 0.47, 0.32 of the busiest in Advan -- fall under the tie cut
of 5. Units at 0.05+ of the busiest outside Boone: Advan 37, public 6. The patterns refit (K rule, below) does not
enter the tie market: it reads the travel sources directly.

**History of the tie-market settings (2026-10-18, old scoring; figures superseded, see appendix).** Columbia's eight
towns: within-county exponent 0.5 and the regularity rule were adopted on small gains. Audrain: Vandalia's public
markets became the two Advan shows (northeast toward Hannibal, and Columbia; Vandalia now 0.55); the false Kansas City
and St. Louis markets came from the 2026-10-18 public build overdrawing metros for a small town (Jackson 3.3% of
out-of-county travel against Advan's ~0.2%; St. Louis County 11.8% vs ~4.5%; Marion 2.2% vs ~17%), amplified by Kansas
City being one map unit. Mexico keeps one false market (Jefferson City, 1.1% of observed travel): LODES gives Audrain
residents 398 jobs in Cole, 78% in "all other services" (which includes government), while Advan shows 1.4% of their
out-of-county work-behaviour visits there -- consistent with LEHD's imputed establishment assignment of state jobs to
the capital; observed LODES only within 45 miles did not remove it. Rejected: long-distance kinds in activity spaces
(create false metro markets); hexagon-level scoring of visited cells (the market is the region, not the cells).
Cape Girardeau: the public markets were in the right places (79-100% inside Advan's) but too compact -- Jackson 608
km2 against 1,404, Scott City 427 against 1,170, Marble Hill 913 against 2,644: regular visits in this farm region
spread over rural block groups that jobs and listed destinations miss. **ADOPTED (2026-10-18):** where people live
(2020 Census block group population, CenPop2020_Mean_BG29) as a third of the within-county spread, with jobs and OSM
destinations (`ATTRPOP=1`), for every tract (a nonmetro-only rule missed Cape Girardeau and Bollinger, metro counties
whose residents travel like rural ones). Thresholds by density (< 50/km2, < 200/km2) were not adopted.

**Transfer test of the markets: Kansas, travel only** (2026-10-18; `activity_market_score.py 29|20`; not rerun
2026-10-24, so the scoring change above has not been applied to it). Kansas has no outlets in the story collection,
so no news terms. Same settings in both states: regular-travel public model by class without corrections; LODES
home-county share; within-county spread of jobs, OpenStreetMap destinations and population at distance^-0.5; the
Missouri-fitted regularity rule; every tract's 80% market, closed. Kansas inputs: `build_ks_tract_bg.py` (Advan
Kansas destinations + Kansans' Missouri visits), `flows/build_destinations.py STATE=20` (65,171 OSM destinations),
Kansas WAC, block-group boundaries and population centres.

| Travel markets, every tract | Missouri replicability | Missouri accuracy | Kansas replicability | Kansas accuracy |
|---|---:|---:|---:|---:|
| Small rural | 0.71 | 0.49 | 0.70 | 0.49 |
| Independent towns | 0.73 | 0.50 | 0.67 | 0.42 |
| Commuter | 0.81 | 0.57 | 0.80 | 0.61 |
| Hubs | 0.79 | 0.53 | 0.78 | 0.59 |
| **All** (1,647 / 816 tracts) | **0.78** | **0.53** | **0.74** | **0.56** |
| Same number of markets / within one | | 56% / 90% | | 61% / 84% |

The method transfers: with nothing tuned in Kansas the public model reaches 0.56, about three-quarters of the data's
own replicability (Missouri about two-thirds). Weakest: Kansas independent towns (0.42; predicted markets 58% of the
observed area) -- mostly western frontier counties, small and self-contained yet travelling far, which Missouri barely
has.

Against the conventional definitions of a local market (same tracts, 2026-10-18; overlap = median Jaccard with Advan's
market; recall = share of Advan's market covered; precision = share of the definition that is Advan's market):

| Market definition | Missouri overlap / recall / precision | Kansas overlap / recall / precision |
|---|---|---|
| Advan, odd vs even months (ceiling) | 0.78 | 0.74 |
| Public model | 0.53 / 83% / 66% | 0.56 / 78% / 77% |
| Commuting shed (LODES alone, spread by jobs) | 0.45 / 77% / 57% | 0.45 / 76% / 57% |
| Circle of the class's median observed area | 0.34 / 45% / 55% | 0.28 / 46% / 45% |
| Home county | 0.25 / 29% / 76% | 0.28 / 31% / 80% |

The home county -- the usual unit of a local market -- holds under a third of residents' regular market; the public
model holds about four-fifths of it, twice the county's overlap.

Related: Bisiani, Gulyas & Heravi (2025) derive outlets' coverage footprints from place mentions (convex hull and
radius of the top 75% of places, LSOA count, Gini, entropy, Moran's I, distance decay; six outlet types) with no test
against where audiences live or travel; this work supplies the audience side. Coverage places here are after the
grounding gate (PR #595, 2026-09-16; March corpus regrounded) -- every stored place is named in the article text.

### Information needs markets: name, certainty, minimum size (2026-10-18; evidence rerun 2026-10-24)

Named **local information needs areas** on 2026-10-18 (from "information needs market"), **civic interest areas**
from 2026-10-20 (below). Map title "<Town>'s civic interest area", no direction in the title, numbered I, II, III only
when a town has more than one. Columbia has one since 2026-10-24: "Columbia's civic interest area" (formerly I and II).
Certainty layer on the approved maps (`market_pattern_print.html &conf=1&outline=1`; `analysis/confidence_layer.py`,
`flows/pattern_halves.py`): the same network tie from odd and from even months; a shown hexagon is lighter when it
clears the map's floor in one half only; the area is drawn as one connected area (confident cells joined by closing,
small clusters kept within 5 hexagons, lone far cells dropped, smoothed ~5 km, gaps filled with empty hexagons, nothing
drawn outside it, no outline line).

**Minimum size, ADOPTED (2026-10-18, unchanged):** a secondary or tertiary area needs 10%+ of the town's residents AND
1,000+ residents (`market_patterns.py`; primary always kept). Evidence, current (`analysis/market_stability.py`, 57
areas, all passing the rule; home hexagons excluded): share of shown hexagons holding in both halves, median 0.93; 0.83
at 500-1,000 residents (1 area), 0.855 at 1,000-2,000 (8), 0.91 at 2,000-5,000 (15), 0.94 above 5,000 (33); Spearman
(residents, share holding) 0.31. Lowest: Kansas City suburbs (Harrisonville 0.35, Grain Valley 0.61, Lexington 0.65),
Lancaster 0.72, Republic III 0.74, Carthage I 0.75; Linn 0.75. Columbia 0.95, Mexico 0.98. A stability threshold is not
adopted.

## Coverage model

**Adopted (2026-10-24): the travel model's gravity terms plus residents' visits, with a separate response for
nonmetropolitan newsroom counties** (`coverage_model.py`). PPML of March story-county pairs from each newsroom county
i to each other Missouri county j:

- the shared gravity terms (`gravity_terms.py`) and a fixed effect for every newsroom county and every county covered
- log visits i → j (Jan–Sep 2026, the travel outcome) where visits > 0, and an indicator for pairs with no recorded
  visits
- log visits × nonmetropolitan newsroom county (USDA RUCC 4–9), adopted 2026-10-24 on held-out error: on destinations
  with 1%+ of visits, change −0.143 [−0.221, −0.068] against the pooled model; on all destinations a tie (+0.002
  [−0.006, +0.009]); difference coefficient −0.235 (s.e. 0.039)
- the shared gravity terms are carried from the travel model, not selected for coverage (commuting out −0.02, n.s.,
  here)

A newsroom's county is `excluded_outlets.home_fips` (Mid Rivers Newsmagazine with St. Charles, Greene County
Commonwealth with Greene; 29 stories each). `excluded_outlets.EXCLUDE` is left out, including the 11 campus newspapers
(`CAMPUS`). The elasticity is the percentage difference in stories associated with 1% more visits, holding distance,
border, commuting and both sets of fixed effects fixed: an association, not an effect of travel on coverage. A story
counts once for each county it names, so pairs from one newsroom county are not independent: standard errors are
clustered by newsroom county (88 clusters).

### Results

| | All outlets | Print and digital |
|---|---:|---:|
| Stories / newsroom counties / out-of-county story-county pairs | 14,877 / 88 / 10,282 | 8,301 / 88 / 6,674 |
| **Elasticity, metro newsroom counties (27)** | **0.49** (s.e. 0.066; 95% CI 0.36–0.62) | **0.51** (0.081; 0.35–0.67) |
| **Elasticity, nonmetro newsroom counties (61)** | **0.25** (s.e. 0.061; 95% CI 0.13–0.37) | **0.25** (0.060; 0.14–0.37) |
| Difference, nonmetro − metro | −0.235 (s.e. 0.039, p < 0.001) | −0.253 (0.058, p < 0.001) |
| Twice the visits, metro / nonmetro | 1.40 / 1.19 × the stories | 1.42 / 1.19 × |
| s.e., clustered by county pair, metro / nonmetro (sensitivity) | 0.048 / 0.048 | 0.052 / 0.048 |
| s.e., two-way newsroom county × county covered (sensitivity) | 0.078 / 0.068 | 0.093 / 0.067 |
| s.e., HC1, pairs independent (reference only) | 0.047 / 0.046 | 0.051 / 0.047 |
| Leave one newsroom county out, metro (88 fits) | 0.45 (without St. Louis County, 1,812 pairs) to 0.53 (without Jackson, 677) | 0.45 (without St. Louis County, 846) to 0.55 (without Franklin, 379) |
| Leave one newsroom county out, nonmetro | 0.23 (without St. Louis County) to 0.29 (without Jackson) | 0.21 (without St. Louis County) to 0.28 (without Taney, 43) |
| Pooled elasticity, no nonmetro interaction (sensitivity) | 0.36 (s.e. 0.060) | 0.35 (0.064) |
| Commuting in (workers of j who work in i) | +0.42 (s.e. 0.073) | +0.38 (0.071) |
| Commuting out | −0.02 (n.s.) | −0.03 (n.s.) |
| Fitted vs observed pairs, r² | 0.97 | 0.95 |

- Stories follow visits less than proportionally, and about half as strongly from nonmetro newsroom counties: 1% more
  visits, 0.49% more stories from metro newsroom counties, 0.25% from nonmetro ones.
- No single newsroom county drives either elasticity. St. Louis County, the largest (1,812 of 10,282 pairs), moves
  both the most: 0.49 → 0.45 and 0.25 → 0.23.
- "Travel beyond gravity", log(visits ÷ travel-model prediction), is the same quantity as log visits given the same
  gravity terms and fixed effects, because the prediction is a function of them (pooled: 0.355 against 0.352 for log
  visits with the same 1e-3 floor). Replaced by log visits.

Zero-visit pairs (137 in the fitted sample, 1 story-county pair on them), elasticity metro / nonmetro:

| Treatment | All outlets | Print and digital |
|---|---|---|
| **Indicator + log visits where > 0 (adopted)** | **0.486 / 0.252** | **0.507 / 0.254** |
| Zeros at log(1e-3) = −6.9 (before 2026-10-24) | 0.482 / 0.246 | 0.502 / 0.247 |
| log(visits + 1) | 0.488 / 0.254 | 0.509 / 0.257 |
| log(visits + 10) | 0.488 / 0.255 | 0.509 / 0.258 |
| log(visits + 100) | 0.479 / 0.249 | 0.496 / 0.247 |
| Zero-visit pairs dropped | 0.486 / 0.251 | 0.507 / 0.254 |

Specifications not adopted (`coverage_model.py` prints them so earlier figures can be traced; not to be quoted).
Without the full gravity terms, distance loads onto visits (pooled elasticities):

| Specification | All outlets | Print and digital |
|---|---:|---:|
| Fixed effects + log(1 + visits), no distance terms (`border_coverage_test.py` family) | 0.75 (s.e. 0.015) | 0.72 |
| Fixed effects + log(1 + visits) + log distance + border | 0.53 (s.e. 0.065) | 0.51 |
| Pooled, without the two commuting terms | 0.43 | 0.40 |
| Pooled, all gravity terms (sensitivity) | 0.36 | 0.35 |

### Held-out error

`coverage_saturation_test.py`: each newsroom county left out in turn, its out-of-county story shares predicted from
the other 87; mean absolute share error per county, averaged, 95% bootstrap over newsroom counties (2,000 draws).
Change = paired difference from the adopted model. Neither destination set is chosen by the held-out county's stories.

| Model, all outlets | All destinations (points) | Change | Destinations with 1%+ of visits | Change |
|---|---:|---:|---:|---:|
| **Adopted (log visits × nonmetro home)** | **0.913** [0.844, 0.982] | — | **4.42** [4.00, 4.91] | — |
| Pooled, no nonmetro interaction (adopted before 2026-10-24) | 0.911 | −0.002 [−0.009, +0.006] | 4.56 | +0.143 [+0.068, +0.221] |
| × destination's own stories | 0.910 | −0.003 [−0.005, −0.001] | 4.40 | −0.021 [−0.046, +0.002] |
| × destination's newsrooms | 0.913 | +0.000 [−0.000, +0.001] | 4.42 | +0.003 [−0.005, +0.012] |
| × destination has broadcaster | 0.912 | −0.001 [−0.002, +0.001] | 4.42 | −0.004 [−0.024, +0.018] |
| × own stories, × own stories × nonmetro home | 0.910 | −0.002 [−0.005, −0.000] | 4.40 | −0.019 [−0.045, +0.006] |
| × own stories + × broadcaster | 0.911 | −0.002 [−0.004, +0.001] | 4.41 | −0.012 [−0.040, +0.016] |

Print and digital: adopted 0.939 [0.873, 1.003] / 4.53 [4.08, 4.97]. The pooled model scores +0.000 [−0.008, +0.008]
/ +0.111 [+0.030, +0.191] against it. × own stories: −0.005 [−0.008, −0.002] / −0.032 [−0.071, +0.007].

### Rejected or not supported

| Tested | Result | Script |
|---|---|---|
| Separate factor lists for travel and coverage | Replaced by one shared term set (`gravity_terms.py`) | — |
| Non-bordering destinations get less coverage than travel predicts | Raw comparison: at the same travel share, ring-2 and ring-3+ counties get less story share than bordering ones (10%+ of visits: 6.7% and 7.8% against 15.8%). The border-test specification (fixed effects, rings, log(1 + visits) × not bordering, errors clustered by newsroom county) has no distance terms and is not the adopted model; in it the slope difference beyond the border is +0.04 (95% CI −0.04 to +0.12; print +0.06, −0.05 to +0.17), not detectable; ring 3+ level −1.16 (s.e. 0.52) | `border_coverage_test.py` |
| **Saturation**: stories follow visits less to destinations that already have their own coverage | Not supported on the adopted specification. Log visits × the destination's own stories: −0.007 (s.e. 0.008, p 0.34). × the destination's newsrooms: −0.005 (p 0.82). × broadcaster: −0.033 (p 0.28). × own stories × nonmetro home: −0.001 (p 0.83; print 0.80). Held-out error changes by 0.003 points or less on all destinations and by 0.004–0.021 on 1%+ of visits, every 1%+ interval spanning zero (table above). The level version (rural newsrooms cover saturated centres less regardless of travel) was tested only within the all-factors model | `coverage_saturation_test.py` |

### Changes, 2026-10-24 (peer review)

| Change | Before | After |
|---|---|---|
| Travel term | log(visits ÷ travel-model prediction) | log visits; identical given the same terms and fixed effects |
| Nonmetro newsroom county × log visits | not in the model | adopted: metro 0.49, nonmetro 0.25; held-out error on 1%+ of visits 4.56 → 4.42 |
| Zero-visit pairs (201 of 13,110; 137 fitted) | set to log(1e-3) = −6.9, high leverage | indicator + log visits where > 0; elasticities move ≤ 0.006 |
| Standard errors | HC1, pairs independent | clustered by newsroom county; pair and two-way as sensitivity |
| Headline elasticity | "0.7–0.8% more stories per 1% more visits" (no distance terms) | metro 0.49 (s.e. 0.066), nonmetro 0.25 (0.061) |
| HOME_COUNTY outlets | counted under the county filed | Mid Rivers Newsmagazine → St. Charles, Greene County Commonwealth → Greene (`home_fips`) |
| Campus newspapers (`CAMPUS`, 11) | in their county's coverage | left out, as The Maneater; with HOME_COUNTY, out-of-county pairs 10,406 → 10,282 |
| Saturation test | own 2-outlet exclusion list; separate log1p-visits + log distance + border model; HC1; scored on destinations with 1%+ of visits **or 2+ held-out stories**; no interval | `excluded_outlets.EXCLUDE`; adopted specification; clustered s.e.; scored on all destinations and on 1%+ of visits; bootstrap intervals |
| Border test | HC1; specification unlabelled | clustered by newsroom county; printed as the border-test specification, not the adopted model |
| `home_county_decay.py` | county-wide variant (OWN_TOWN=0) took the outlet's county from `publisher_county` | `home_fips` via `market_patterns.home_of`. Default own-town result 1.68 → 1.64 (s.e. 0.02), from upstream changes (CAMPUS, shared libraries), not from this change |

## Spillover model, 2026-10-16 (replaced)

Historical record: earlier measure (any story touching another county) and pre-re-run data. Every figure in this
section is superseded (2026-10-24: Spillover model, current).

**Adopted 2026-10-16: outlet-level logistic model** (`spillover_outlets.py`).

- One observation per outlet with ≥ 10 placed stories (128 outlets, 27 broadcasters), each counted once; errors
  clustered by county
- spillover ~ broadcaster + residents' share of visits outside the county
- Broadcaster +0.70 (p < 0.001); residents' travel out +1.47 (p < 0.001)
- A county's expected spillover is its outlets' expectations weighted by their stories

Leave-one-county-out error (predicting a county's outlets from all others):

| Version | Mean absolute error (points) |
|---|---:|
| Broadcaster only | 15.5 |
| **Broadcaster + residents' travel out (adopted 2026-10-16)** | **14.5** |
| + population | 14.5 |
| Full: cohort, border, population, travel out | 15.3 |

### Rejected (2026-10-16)

| Tested | Why rejected |
|---|---|
| County-level spillover with every story counted (`spillover_v2.py`) | Broadcasters' volume dominated it: a county's result mostly said whether it had a TV station. Its cohort effects shifted between specifications |
| Eight cohorts (OMB types × hub split) | Too many groups for 68 counties; replaced by four cohorts, then by the outlet model |
| Four cohorts (Top 50 metro, regional hub, metro suburban, rural) | Not significant once outlets are the unit and broadcasting is a factor; did worse out of sample (15.3) |
| Number of newsrooms in the county (`spillover_newsrooms_test.py`) | For print and digital it adds about one point; in the all-outlets version it only stood in for having a broadcaster |
| Population | No gain out of sample |

## Comparisons withdrawn

| Withdrawn | Why |
|---|---|
| "Newsrooms over-cover their home county relative to where residents spend their time" | Invalid: residents live in their home county; visit share is not a measure of its importance |
| Article text comparing residents' share of visits outside the county (~76% rural) with stories reaching beyond it (~42%) | Same error |
| "Visits × expected" figures from the singly-constrained model (e.g. 2.2×) | That model's held-out error is 7.25 against the adopted 3.26 (superseded 2026-10-24: "under-predicted main destinations by 1.6×", in-sample and selected on the observed share; held out and forecast-selected, 1.19×) |
| "Beyond gravity" maps | Category colours carried four model-based outcomes; unreadable as maps. The model comparison is a table (`three_counties_table.csv`) |
| Alignment maps with the home county compared | Replaced by out-of-county comparison with home and away story counts for reference |

## All marginal factors together

Each factor above was first tested alone. To check whether many small effects add up, every factor that showed any
effect was added at once and scored only on counties the model was not fitted on (`combined_marginal_test.py`,
`combined_all_factors_test.py`). Each home county held out (8 folds); 95% intervals over counties:

| Travel model | Terms | Held-out R² | Share-weighted error | Change vs adopted | Big flows (forecast 5%+): error | Change vs adopted | Within 0.8–1.25× |
|---|---:|---:|---:|---:|---:|---:|---:|
| Adopted | 8 | 93.8% [92.4, 94.9] | 3.26 [2.93, 3.59] | | 3.45 [3.17, 3.74] | | 49% |
| + all 8 rejected pair terms | 16 | 93.9% [92.5, 95.0] | 3.15 [2.81, 3.51] | −0.11 [−0.31, +0.10] | 3.44 [3.16, 3.76] | −0.01 [−0.18, +0.17] | 50% |
| Nested: terms chosen inside each training set | chosen | 93.8% [92.4, 94.9] | 3.21 [2.86, 3.57] | −0.05 [−0.23, +0.14] | 3.47 [3.18, 3.78] | +0.02 [−0.14, +0.19] | 50% |
| Origin effects + every destination factor + every pair term (no destination effects; `combined_all_factors_test.py`) | 21 | 91.4% [89.6, 93.0] | 3.84 [3.38, 4.30] | +0.58 [+0.14, +1.06] | 3.96 [3.61, 4.26] | +0.51 [+0.15, +0.87] | 43% |

- Nested choice (among adopted, adopted + each rejected term alone, adopted + all; inner held-out error on 7 folds of
  the training counties): "+ on the way to a bigger centre" in 4 outer folds, "+ all" in 4, the adopted set in none.
  The chosen sets' inner gains (0.10–0.29 points) do not carry to the held-out counties: −0.05 [−0.23, +0.14].
- Under the selection rule none of the eight rejected terms is added, alone or together.
- Stores, jobs, metro and area centre cannot replace each destination's measured draw: without destination effects
  travel is worse (91.4% against 93.8%; +0.58 [+0.14, +1.06]).
- Stability check, Jul–Sep from Jan–Jun: adopted error 3.01, + all rejected 2.84, persistence 1.51.

Coverage, adopted specification, each newsroom county held out, destination sets as under Coverage model, Held-out
error (scratch rerun of the coverage section of `combined_marginal_test.py`):

| Coverage model | Adopted (11 terms) | + every rejected factor (26 terms) | Change [95%] |
|---|---:|---:|---:|
| All outlets, all destinations | 0.91 | 0.91 | −0.005 [−0.016, +0.008] |
| All outlets, destinations with 1%+ of visits | 4.42 | 4.39 | −0.03 [−0.18, +0.16] |
| Print and digital, all destinations | 0.94 | 0.93 | −0.006 [−0.018, +0.006] |
| Print and digital, 1%+ of visits | 4.53 | 4.50 | −0.03 [−0.19, +0.15] |

- The marginal factors do not add up for coverage: held-out error moves by less than its interval on both destination
  sets, while in-sample deviance falls from 7,257 to 7,017 (over-fitting).
- The scripts as run score coverage on the outcome-selected destination set (2+ held-out stories), mean absolute share
  error: adopted 3.47 [2.99, 4.02] (print and digital 3.78 [3.31, 4.27]); + all rejected (25 terms) +0.03 [−0.07,
  +0.17]; + every rejected term incl. saturation level (26) −0.01 [−0.09, +0.06]; origin effects + destination factors
  + every pair term (34) +0.08 [−0.03, +0.20] (print +0.05 [−0.05, +0.17]). Same conclusion; scoring to be moved to the
  reviewed destination sets (Open).

Spillover, adopted model (`spillover_common.FINAL`; fitted on 85 outlets, scored on 94), each county held out, mean
absolute error (points):

| Spillover model | Error [95%] | Change vs adopted [95%] | Script |
|---|---:|---:|---|
| Adopted | 6.43 [5.54, 7.64] | | both |
| + cohort, border, population, newsrooms, log stories, travel out | 7.00 | +0.56 [−0.00, +1.16] | `combined_marginal_test.py` |
| — ridge 0.05 / 0.2 | 7.02 / 7.46 | +0.58 [−0.06, +1.27] / +1.02 [+0.11, +1.86] | `combined_marginal_test.py` |
| + every county factor (also one newsroom, travel balance, broadcaster × travel out) | 7.66 | +1.23 [+0.51, +1.97] | `combined_all_factors_test.py` |
| — ridge 0.05 / 0.2 | 7.05 / 7.44 | +0.62 [−0.00, +1.28] / +1.01 [+0.13, +1.83] | `combined_all_factors_test.py` |

- No combination of rejected factors improves coverage or spillover held out; for spillover every combination is
  worse. (Superseded 2026-10-24: "ridge 0.05 is 0.3 points better", on the earlier measure and model.)

## Crossover: distinct people (adopted)

Crossover is the share of a county's residents observed outside it in a month, counted as distinct people
(`build_unique_od.py`, `crossover_compare.py`); it is the potential demand in Revealed media market by travel pattern and
not a term in the adopted spillover model. Advan reports distinct people per destination block group by home block group; people
from different home block groups are distinct, and for each home block group the people seen in its single
most-visited outside block group are all distinct. Summing those over the county's block groups gives a lower bound on
residents who left, capped at the residents seen at home in each block group. Averaged January–September 2026; March
matches the three-county check (Audrain 42%, Boone 29%, Osage 44%).

| Measure | Audrain | Boone | Osage | Missouri median |
|---|---:|---:|---:|---:|
| Summed block-group share (replaced) | 66% | 33% | 82% | 77% |
| Distinct residents seen outside, lower bound (adopted) | 41% | 24% | 45% | 52% |
| Employed residents working in another county ÷ population (LODES) | 23% | 11% | 33% | 23% |

The lower bound includes commuters and is the higher of the two people-based floors in 112 of 114 counties. The summed
share overstated leaving in rural counties and understated it in large ones (St. Louis 22% summed, at least 46% as
people), because residents of large counties are seen in many block groups at home. De-duplicating further was tested:
treating block groups as independent gives implausible figures (90% of Audrain residents in Boone County in a month),
so only the lower bound is used.

## Spillover model, current (2026-10-24)

`spillover_outlets.py`; definitions in `spillover_common.py`; selection in `spillover_rule_selection.py`.

| | Value |
|---|---|
| Outlets with 10+ placed stories | 128 in 72 counties (27 broadcasters), 12,192 stories |
| Fitted (well collected, 20+ placed stories, not Three Rivers Publishing) | 85 outlets, 48 counties (24 broadcasters) |
| Model | spillover ~ broadcaster + log(1 + print and digital outlets in the county) |

| Term | Coefficient | Clustered s.e. | p (clustered, t, 47 df) | Bootstrap 95% CI (county clusters, 1,999 draws) |
|---|---:|---:|---:|---|
| Intercept | −0.812 | 0.111 | < 0.001 | −1.019 to −0.556 |
| Broadcaster | +0.667 | 0.135 | < 0.001 | +0.388 to +0.939 |
| Print and digital outlets in the county (log of 1 + count) | −0.387 | 0.089 | < 0.001 | −0.655 to −0.232 |

Selection rule (Current results): joint test of the adopted set, and candidate additions. Change = held-out error with
− without (points, each county left out; negative helps; county-paired bootstrap 95% interval, 1,999 draws):

| Test | Change | 95% interval | Median with / without | Passes |
|---|---:|---|---|---|
| 1. Adopted set (broadcaster + print outlets) vs intercept only | −1.51 | −2.61 to −0.32 | 4.66 / 6.23 | yes |
| 2. Coefficient CIs: broadcaster +0.388 to +0.939; print outlets −0.655 to −0.232 | | | | yes |
| 3. + outlets per 10,000 | −0.28 | −0.87 to +0.16 | 4.74 / 4.66 | no |
| 3. + border, print and digital | −0.08 | −0.45 to +0.33 | 4.64 / 4.66 | no |
| 3. + miles to a town of 25,000+ | −0.05 | −0.36 to +0.25 | 4.78 / 4.66 | no |
| 3. + border, every outlet | −0.01 | −0.36 to +0.36 | 4.78 / 4.66 | no |
| 3. + all outlets in the county | +0.09 | −0.02 to +0.20 | | no |
| 3. + crowded weekly | +0.09 | −0.05 to +0.27 | 4.65 / 4.66 | no |
| 3. + TV stations | +0.14 | −0.02 to +0.33 | 4.53 / 4.66 | no |

Term by term: broadcaster against print outlets only −1.55 (−2.69 to −0.34); print outlets against broadcaster only
−1.04 (−1.88 to +0.03). Rejected forms' coefficients: outlets per 10,000 +0.191 (CI −0.154 to +0.329); border (print
and digital) −0.110 (CI −0.209 to −0.011). The rule applied inside each fold without the held-out county keeps
broadcaster + print outlets in 47 of 48 folds (intercept only in 1): nested 6.27 / 4.76.

Held-out error: each county's outlets predicted by a fit without that county; mean / median absolute error in points;
skill = 1 − error / error(intercept only); R² out of sample, against intercept only.

| Model | Scored on | n | Mean | Median | Skill | OOS R² |
|---|---|---:|---:|---:|---:|---:|
| **Adopted** | fitted (20+) | 85 | **5.98** | **4.66** | +0.202 | +0.360 |
| Adopted | all well collected, 10+ | 94 | 6.43 | 4.81 | +0.204 | +0.350 |
| Nested: selection rule inside each fold | fitted (20+) | 85 | 6.27 | 4.76 | +0.163 | — |
| Nested: full searches A / B (lowest-error selection) | fitted (20+) | 85 | 6.27 / 6.57 | 4.71 / 5.50 | +0.163 / +0.123 | — |
| + outlets per 10,000 | fitted (20+) | 85 | 5.70 | 4.74 | +0.239 | +0.426 |
| + border (print and digital) | fitted (20+) | 85 | 5.89 | 4.64 | +0.213 | +0.375 |
| Intercept only | fitted (20+) | 85 | 7.49 | 6.23 | 0 | 0 |
| Intercept only | all well collected, 10+ | 94 | 8.08 | 6.32 | 0 | 0 |
| Broadcaster only | fitted (20+) | 85 | 7.02 | 5.11 | +0.063 | +0.129 |
| Broadcaster only | all well collected, 10+ | 94 | 7.63 | 5.35 | +0.056 | +0.117 |

| County | Actual | Expected | Stories |
|---|---:|---:|---:|
| Audrain | 20% | 22% | 123 |
| Boone | 29% | 26% | 1,152 |
| Boone, print and digital | 18% | 19% | |
| Osage | 26% | 25% | 40 |
| Cole (Jefferson City News Tribune) | 23% | 25% | 325 |
| Jackson | 22% | 21% | 2,316 |
| Jackson, print and digital | 23% | 14% | |

County figures are outlets' spillover and expectations weighted by stories.

Quality selection: 95 of 128 outlets are well collected; their mean spillover is 24.5% against 17.5% for the others
(point-biserial r +0.26, p 0.003; print and digital 22.2% against 15.5%). The fit, its coefficients and its errors
describe well-collected outlets; expectations for the other 33 are extrapolations.

### Definitions

- **Spillover**: weighted share of an outlet's placed stories about another county — another Missouri county, or an
  other-state county within 60 miles. Centred in another county 1; centred at home, or with no centre, and mentioning
  another county 0.5; home only 0. A Sports story (CIN) counts half of that (0.5 centred, 0.25 mention).
- **Weights**: mention 0.5 and Sports 0.5 are definitions set by the authors, not selected or fitted: a mention is half
  a story about that county; a game is between two teams, usually from different places, so a Sports story reaches
  another county by its nature. Other weights appear only in the sensitivity table below.
- **Denominator**: every placed story. The 2,700 stories with no central county and the 163 centred out of state more
  than 60 miles away (23.5% of stories) stay in it; they count only through mentions.
- **Home** (one rule for every outlet): the county the outlet is filed under (St. Louis city and county one unit),
  every other county holding part of its registry city (Census 2020 base population > 0, place-in-county rows of
  `census_dl/ref/sub-est2024_29.csv`), and Kansas City, Kansas (Wyandotte) for Kansas City, Missouri outlets — a
  same-named city adjoining across the state line; no other Missouri city has one. Kansas City → Jackson, Clay,
  Platte, Cass; Joplin → Jasper, Newton; Sikeston → Scott, New Madrid; Springfield → Greene, Christian; Jefferson
  City → Cole, Callaway; Excelsior Springs → Clay, Ray; Osage Beach, Hannibal, Lee's Summit, Mountain Grove, Belle,
  Cameron likewise. Johnson County, Kansas and St. Clair and Madison counties, Illinois are home for no outlet.
  HOME_COUNTY outlets take only the county they cover.
- **Mid Rivers Newsmagazine** (St. Charles) and **Greene County Commonwealth** (Greene) are fitted with the county they
  cover as home (`excluded_outlets.HOME_COUNTY`); both are published outside it, so their border distance is 0. Three
  Rivers Publishing (three newspapers under one name) stays out of the fit.
- **Not local news**: `EXCLUDE`, including the campus newspapers (`CAMPUS`, in `excluded_outlets.py`;
  `spillover_common.NOT_LOCAL = EXCLUDE`): student newspapers owned by a college or university — Griffon News, The
  Arrow, Drury Mirror, The Standard, UMKC Roo News, The Chart, The Daily BURG, North West Missourian, Student Life, The
  Journal/The Webster Journal, The University News. Out of the outcome, the fit and every county count.
  University-licensed public broadcasters (KBIA, KCUR, KRCU, KSMU, KXCV, STL Public Radio) and the School of
  Journalism's community newsrooms (Columbia Missourian, Boone County Journal, KOMU) stay.
- **Market counts** (print and digital outlets in the county, the crowded-county test, every search candidate): pinned
  registry, status active or closed but publishing in March, not `EXCLUDE`. One rule in every script.
- **Crowded weekly** (candidate, not adopted): a print weekly (registry type print/newspaper) in a county whose market
  has a print daily and a TV station. Nine counties: Adair, Boone, Buchanan, Callaway, Cape Girardeau, Greene,
  Jackson, Jasper, St. Louis. Fitted crowded weeklies: Boone County Journal, Greene County Commonwealth, North East
  News, St. Louis American, The Cash-Book Journal, The Pitch, Webster Kirkwood Times.
- **Border distance** (candidate, in the border form): miles from the registry point to the nearest edge of the home
  county, logged, floored at half a mile. 68 of 85 fitted outlets are at a street address, 15 at a town centroid
  (location_basis). Set to 0 for broadcasters (a station's reach is its signal, not its office) and for an outlet
  outside its home county.
- **Well collected**: March local news with body text ≥ 95%, full length (600+ characters) ≥ 80%, placed ≥ 60%.

### Measure sensitivity (weights are definitions; this is not a selection)

Same 85 outlets, adopted terms. Each row is a different outcome, so rows compare by skill and out-of-sample R², not by
the error in points. County columns actual / expected.

| Mention | Sports | Mean rate | Held-out mean | Intercept-only mean | Skill | OOS R² | Audrain | Boone | Osage |
|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| 0.25 | 1 | 21.3% | 6.76 | 8.59 | +0.213 | +0.334 | 25% / 19% | 24% / 23% | 18% / 22% |
| 0.25 | 0.5 | 17.8% | 5.62 | 7.43 | +0.244 | +0.393 | 14% / 15% | 22% / 20% | 16% / 17% |
| 0.25 | 0 | 14.2% | 5.59 | 7.25 | +0.228 | +0.404 | 2% / 11% | 20% / 18% | 14% / 12% |
| 0.5 | 1 | 29.9% | 7.32 | 9.19 | +0.204 | +0.346 | 34% / 29% | 32% / 30% | 29% / 33% |
| **0.5** | **0.5** | 24.7% | 5.98 | 7.49 | +0.202 | +0.360 | 20% / 22% | 29% / 27% | 26% / 25% |
| 0.5 | 0 | 19.6% | 6.60 | 7.96 | +0.171 | +0.320 | 5% / 16% | 26% / 23% | 22% / 17% |
| 1.0 | 1 | 47.2% | 9.91 | 12.56 | +0.212 | +0.379 | 53% / 49% | 47% / 45% | 50% / 55% |
| 1.0 | 0.5 | 38.7% | 8.01 | 9.21 | +0.129 | +0.291 | 31% / 38% | 42% / 39% | 45% / 42% |
| 1.0 | 0 | 30.3% | 9.87 | 10.57 | +0.066 | +0.168 | 10% / 27% | 37% / 33% | 40% / 29% |

Sports weight 0 removes real spillover with the errors (Audrain's was 76% Sports on the 2026-10-17 data: the Mexico
Ledger's Centralia and Community R-VI coverage).

### Search history and nested test

The terms were first found by search (`spillover_saturation_test.py`: base broadcaster + crowded weekly, 13 candidates
added one at a time). `spillover_nested_selection.py` repeats the search inside each fold, without the held-out county:

| Search | Models | Non-nested best (mean) | Nested mean / median | Chosen in the folds |
|---|---:|---|---|---|
| A: broadcaster + crowded weekly + up to 2 of 13 | 92 | + outlets per 10,000 + print outlets (5.80) | 6.27 / 4.71 | outlets per 10,000 + print outlets 44 of 48; border (print) + hub 2; print outlets + border (print) 2 |
| B: broadcaster + up to 3 of 15 (adds crowded weekly, town population) | 576 | + outlets per 10,000 + print outlets + daily × print outlets (5.64) | 6.57 / 5.50 | + outlets per 10,000 + print outlets + daily × print outlets 31 of 48; + outlets per 10,000 + print outlets + border (print) 13; other 4 |

Against intercept only (7.49 / 6.23) the nested searches keep a skill of +0.16 (A) and +0.12 (B); against the border
form's non-nested 5.92 / 4.64 they give up 0.35 (A) and 0.65 (B) points of mean (adopted model, non-nested: 5.98 /
4.66). The wider the search, the larger the gap.

Single additions to broadcaster + crowded weekly (6.98 / 5.35), mean / median, coefficient (clustered-t p): print
outlets 6.07 / 4.65, −0.36 (0.001); miles to a town of 25,000+ 6.06 / 5.10, +0.28 (< 0.001); outlets 6.37 / 5.14,
−0.22 (< 0.001); outlets per 10,000 6.54 / 5.48, +0.26 (< 0.001); TV stations 6.71 / 5.21, −0.25 (0.024); border,
every outlet 7.10 / 5.81, −0.03 (0.54); border, print and digital 6.95 / 5.32, −0.07 (0.13). No daily-only form
improves on its base. Border and print outlets together: every outlet 6.02 / 5.06; print and digital 5.92 / 4.64.
The border form (crowded weekly + border for print and digital + print outlets, 5.92 / 4.64) replaced the 2026-10-17
form (`spillover_common.FINAL_ALL_BORDER`, 6.02 / 5.06) under a rule fixed before the comparison — lower mean and
median — and was then replaced by the joint test, under which neither crowded weekly nor border passes.

### Robustness

Leave one TV market out (`spillover_dma_holdout.py` → `spillover_dma_holdout.csv`), adopted model, markets with 3+
fitted outlets: in sample 5.9, held out 6.2, intercept only held out 7.4. Columbia–Jefferson City 3.2 in sample, 3.3
held out (intercept only 5.5). Two markets do worse than intercept only: St. Joseph (13.5 against 8.7, 5 outlets) and
Quincy–Hannibal (2 outlets).

Springfield region (Greene, Webster, Barry) held out — out of sample for the coefficients only; the terms were chosen
with the region's outlets in the data: 78 outlets fitted outside it predict its 10: mean error 8.0 points (well
collected 8.4); broadcaster + crowded weekly 9.0; broadcaster + town population 8.8. Region 24% actual, 26% expected.
Webster is the largest miss (36% actual, 23% expected).

Market position (`spillover_market_test.py`, on the border form): other outlets nearer the county line, or nearer the
neighbour the outlet is closest to, add nothing (p 0.31–0.70) and replace the border term worse (mean 6.03–6.07
against 5.90).

### Outlets

Mid Rivers Newsmagazine 17% actual, 27% expected (border 0); Greene County Commonwealth 18% / 18%; The Cash-Book
Journal 23% / 18%; KC Beacon 17% / 15%. The Kansas City Star 26% / 15% and The Pitch 24% / 13% are the largest
Jackson print misses. Vandalia Leader 4% / 26% (5% of stories full length; actual a lower bound).

### Changes from the 2026-10-17 model

| Change | Effect |
|---|---|
| Mid Rivers Newsmagazine → St. Charles, Greene County Commonwealth → Greene; both fitted | +2 fitted outlets; the Commonwealth becomes a crowded weekly (Greene) |
| Campus newspapers out (11 outlets; 5 had 10+ stories: Griffon News, The Arrow, North West Missourian, Student Life, The Standard) | −5 outlets; three of them (The Arrow 7%, The Standard 5%, Griffon News 15%) were crowded weeklies |
| Print-outlet count: `EXCLUDE` (incl. `CAMPUS`) out; one market rule (active, or closed but publishing in March) in every script | Counts change in Boone, Cole, Buchanan, Cape Girardeau, Greene, Jackson, Jasper, Nodaway, St. Louis; Mid Rivers counted in St. Charles |
| Crowded weekly requires a print outlet | KC Beacon (digital native) out of the term |
| Frequency codes filled from the Missouri Official Manual 2025–2026 where blank (14 outlets; `coverage/source_frequency.csv`) | The Cash-Book Journal (Cape Girardeau) becomes a crowded weekly |
| One home rule (city counties + Kansas City, Kansas) for every outlet | 31 outlets gain home counties; 330 centred stories move to home (213 beyond the 2026-10-17 Kansas City rule: Kansas City outlets' Clay, Platte and Cass stories; Joplin's Newton; Sikeston's New Madrid; Springfield's Christian), 434 mention-only stories lose their mention credit |
| Joint selection rule | Adopted: broadcaster + print outlets; crowded weekly and border distance not adopted |
| Inference: clustered s.e. with small-cluster correction and t(47); county-cluster bootstrap | Replaces clustered z |
| Baselines, 10+ scoring, nested selection, quality-selection line | Reported every run |
| `spillover_outlets.csv` written once, after every column; `SPILL_DRY=1` writes nothing; weight sensitivity cannot overwrite outputs (environment weights removed) | Reproducibility |
| `spillover_saturation_test.py`: fitted set and 20-story floor of the adopted model; candidates computed once in `spillover_outlets.py` (crash on NaN cluster groups gone) | |
| `spillover_dma_holdout.py`: table from code, with intercept-only skill; written to CSV | |

Attribution of the crowded-weekly change (each step added to the previous; clustered-t p):

| Step | Crowded weekly | p |
|---|---:|---:|
| 2026-10-17 model as logged | −0.56 | 0.008 (z) |
| + HOME_COUNTY reassignment (reviewer rerun) | −0.49 | 0.005 (z) |
| + market-count rule, border 0 outside home, clustered t | −0.35 | 0.002 |
| + campus newspapers out | −0.13 | 0.48 |
| + print outlets only (KC Beacon out) | −0.25 | 0.19 |
| + frequency codes filled (Cash-Book Journal in) | −0.35 | 0.040 |
| + one home rule | −0.18 | 0.31 |
| + border for print and digital only (border form) | −0.20 | 0.27 |

Frequency codes: The Maryville Daily Forum and The Daily/Dexter Statesman were checked against the Official Manual
and kept as weeklies (Manual: "Maryville Forum", Thursdays; "The Statesman", Wednesdays); Richmond Daily News likewise
(Fridays). Neither county has a TV station, so neither code reaches the term. Codes filled where blank, weekly: The
Banner Press, The Cash-Book Journal, Aurora Advertiser, St. Louis Business Journal, Tribune and Times, Cedar County
Republican and Stockton Journal, Chariton Marquee, Kahoka Hometown Journal, Clinton County Leader (Plattsburg),
Springfield Business Journal, Hermitage Index, Tipton Times, Community News; bi-weekly: West & Mid Rivers
Newsmagazine. Sensitivity, not adopted: the Manual's print schedule for every outlet it lists (20 codes change;
Kirksville Daily Express, The Mexico Ledger, The Fulton Sun, Daily Journal and Constitution-Tribune become weeklies;
Southeast Missourian tri-weekly): crowded counties fall from nine to six (Adair, Callaway, Cape Girardeau leave);
crowded weekly −0.28 (p 0.14); held-out 5.85 / 4.54. Frequency codes are kept as filled; moot without the
crowded-weekly term.

### Data: March enrichment re-run and Sports (2026-10-17)

**Re-run of the March enrichment.** 4,669 articles were re-enriched after five crawler fixes: the model is told where
the publication is (#736); a game is centred on the publication's own team (#738); a statewide story is filed under
its own state and state-named places stay local (#738, #739); a long partial story is enriched rather than skipped,
and the TownNews premium-content notice is removed (#739); 970 March bodies stored as ROT47 ciphertext were decoded
(#736, #737). The story map and the quality table were rebuilt from production (`coverage/rerun_2026_10_17/REPORT.md`).
ROT47 ciphertext was tested as a quality criterion and withdrawn: place enrichment read `raw`, which holds the decoded
body for the six affected outlets.

**Sports re-run.** The 1,837 enriched March Sports stories (CIN) were re-run under focus-v4, the rule that centres a
game on the publication's own team; 1,827 completed (four hang on one LLM call every run and stay unenriched). The
re-run mostly placed stories that had no centre: 679 gained one (506 home, 173 away). Of stories placed before, 23
moved away → home and 4 home → away; the away share of placed Sports stories is 18.0% for print/digital (17.0%
before) and 34.3% for broadcast (35.7%). In a sample of 45 away-centred re-run stories about 13 were the outlet's own
team centred on the game site or the opponent (Mizzou softball → Champaign, the SEC tournament → Nashville, Bunker's
archer → Dent), about 28 correct, 4 unclear (`sports_home_away_audit.py`;
`coverage/rerun_2026_10_17/sports_still_away.csv`). Undiscounted, about 40% of print outlets' Sports stories count as
spillover, against 23–29% for every other category; broadcast Sports (about 34%) is not inflated.

Share of spillover by CIN category, well-collected outlets, mention 0.5 and Sports 0.5 (2026-10-17 outlets, before
`CAMPUS` and the one home rule; not rerun):

| | Print/digital | Broadcast |
|---|---:|---:|
| Spillover | 23.8% | 33.8% |
| Sports share of stories / of spillover | 29% / 25% | 14% / 7% |
| Emergencies and Public Safety share of spillover | 11% | 43% |
| Spillover with Sports stories removed | 25.2% | 36.4% |

**Measure history.** The 2026-10-16 measure counted any story that touched another county, so a passing mention
counted the same as a story about that county. Under it a small-town weekly and a regional TV station looked alike
(print median 40%, broadcast 45%); by central county they differ (6% and 25%). The Mexico Ledger had 8 of 90 stories
centred in another county and 43 that only mention one; KOMU had 83 of 263 and 36 (2026-10-16 data).

### 2026-10-17 model (replaced 2026-10-24)

Historical record; every figure in this subsection is superseded (Superseded figures). spillover ~ broadcaster + weekly
in a county with a daily and a TV station + log miles from the outlet's town to its county edge + log(1 + print and
digital outlets in the county). Fitted on well-collected outlets with 20+ placed stories; Mid Rivers Newsmagazine,
Greene County Commonwealth and Three Rivers Publishing left out of the fit. Border and print-outlet terms found by
trying 11 additions on held-out error, with a nested figure reported beside it. Tests run on that model and not rerun
(text in git, commit `63f915f`): a weekly alone in its county, the terms by outlet type and for non-weeklies only,
market position, fits on all 128 outlets before the quality restriction, outlet-profile terms (`spillover_profile.py`),
mention weight 0.1–1.0 under broadcaster + town population, leave-one-market-out by weight combination.

### Previous (2026-10-16, replaced)

Historical record on the earlier measure; every figure here is superseded. spillover ~ broadcaster + urban share +
concentration (outlet level, `spillover_outlets.py`):

| Term | Coefficient | p | Meaning |
|---|---:|---:|---|
| Broadcaster | +0.65 | < 0.001 | TV and radio cover beyond their county more |
| Urban share | −0.81 | < 0.001 | Share of the county's population in Census 2020 urban areas; outlets in urban counties stay local |
| Concentration | +1.17 | 0.12 | Sum of squared shares of residents' out-of-county visits by destination county; high where one hub takes most travel (Webster 69% to Greene). Adopted at the authors' direction; small and not significant on its own |

Held-out error (leave one county out): broadcaster + crossover 15.6 points; + urban share 15.3; broadcaster + urban
share 15.0; + concentration 15.0 (all outlets), 14.3 → 14.1 (well-collected outlets). Crossover was dropped: with urban
share in the model it adds nothing (0.51, p = 0.42), and across counties it is not correlated with spillover.

Urban share was chosen over measures that predicted slightly better on their own (ACS foreign-born share 14.7; Civic
Information Index rent share 14.8) because those stand in for the same urban–rural difference (foreign-born and urban
share correlate 0.74); urban share names it directly.

## Crossover and spillover: correlation

Share of residents seen outside the county (distinct people, lower bound) against the share of print and digital
stories about another county, across counties (`collection_quality_robustness.py`):

| Outlets | Counties | r, unweighted (p) | r, weighted by stories (p) |
|---|---:|---:|---:|
| All | 72 | +0.11 (0.36) | −0.01 (0.93) |
| Well-collected outlets | 53 | +0.35 (0.010) | +0.15 (0.27) |
| Outlets in well-collected counties | 29 | +0.35 (0.061) | +0.20 (0.31) |

The positive relationship appears only unweighted and only where collection is good; weighted by stories it is not
distinguishable from zero.

## Collection quality (sensitivity)

`county_collection_quality.py` (pinned registry; `EXCLUDE` not counted as known newsrooms): 33 counties meet every
test. Adopted spillover model by subset (`collection_quality_robustness.py`), held-out mean error:

| Outlets | n (counties) | Held-out | Broadcaster (p) | Print outlets (p) |
|---|---|---:|---|---|
| All, 10+ | 128 (72) | 7.5 | +0.82 (< 0.001) | −0.42 (< 0.001) |
| Well-collected, 10+ | 95 (54) | 6.6 | +0.68 (< 0.001) | −0.44 (< 0.001) |
| In well-collected counties | 40 (29) | 8.9 | +0.51 (0.042) | +0.08 (0.88) |

Outlets in well-collected counties (40) are too few to estimate the model. Coverage, pooled specification (travel
beyond gravity; not the adopted metro/nonmetro form), all newsroom counties → well-collected counties: 0.36 → 0.26
(all outlets), 0.34 → 0.25 (print and digital).

## Springfield comparison

Greene (hub), Webster (Springfield metro) and Barry (rural) against Boone, Osage and Audrain
(`springfield_vs_columbia.py`; 2026-10-16 measure and models, not rerun). The hubs match each other: crossover 24% and
34%. Spillover on the 2026-10-16 measure: 41% and 40% (print 26% and 25%), both below the Missouri medians (44%, print
43%); Webster the largest miss (actual 68%, predicted 46%, 31 stories). (Superseded 2026-10-24: Springfield region
held out, 24% actual, 26% expected; Webster 36% / 23%; Spillover model, current, Robustness.) Webster → Greene travel
was predicted almost exactly by the 2026-10-16 travel model (0.96×; not rerun): Greene has the strongest overall draw
in Missouri, is 23 miles away, shares a border, and half of Webster's employed residents work there.

## County characteristics tested

Crossover and spillover columns: leave one county out, 2026-10-16 measure and models (spillover figures not comparable
with the current 5.98). Coverage column: 2026-10-16 specification, outcome-selected destination set (not rerun).
Travel: table below (2026-10-24).

| Source | Crossover (12.9 points baseline) | Spillover (15.6) | Coverage (4.00) |
|---|---|---|---|
| ACS 2020–2024 (24 measures, `civic_variables_test.py`) | Commute time, race, 65+: 12.0 | Foreign-born 14.7 (urban proxy) | — |
| Civic Information Index 2026 (`civic_index_test.py`, `civic_index_test_v2.py`) | Environmental resilience alone 12.2; census response rate alone 12.3* | Against the 2026-10-16 model (15.0): rent share of income alone 14.6 (urban proxy); several indicators chosen without seeing the held-out county 15.3 (worse) | — |
| Newsroom bylines and volume, March 2026 (`spillover_bylines_test.py`) | — | Print outlets (101), against the earlier travel-out model (16.1): distinct bylines 16.3 (p = 0.95), local stories 16.2 (p = 0.38), stories per byline 16.2; no gain, and none on the 68 outlets with half or more stories bylined | — |
| Census Business Dynamics Statistics, 2021–2023 average (`business_dynamics_test.py`) | Openings per 100 establishments 12.2 (+0.16, p = 0.03); turnover (openings + closings) 12.2 (p = 0.004); net openings 13.2 (no gain) | Against the 2026-10-16 model (15.0): closings 14.8 (p = 0.07); well collected (14.1): turnover 13.9 (p = 0.16); no consistent gain | — |
| Hospitals (`hospital_test.py`) | Has a hospital: 12.2 (−0.54, p = 0.006) | 15.7 (no gain) | 4.01 (no gain) |
| Hub dominance (concentration of travel) | — | 15.0 (all), 14.1 (well collected); adopted 2026-10-16, replaced | — |

\* Single indicators, each scored with the county left out. Combinations chosen by searching against the same error
are not reported. The index's journalists per 100,000 (MuckRack) is not used: newsroom staffing is measured directly
from bylines in the stories collected, and adds nothing to spillover (row above). Indicators that do not vary
across Missouri counties were excluded (the volunteer rate is one state figure, 29.8%, for every county; library visits
and mental-health providers are missing for some counties). An earlier run kept the volunteer rate: merging St. Louis
city and county left a rounding difference that standardizing turned into a variable singling out St. Louis, and its
apparent effect (spillover 13.4 points with four indicators) was an artifact. With it removed and selection made
without seeing the held-out county, adding several indicators makes spillover predictions worse (15.3 against 15.0 for
all outlets; 15.4 against 14.1 for well-collected outlets).

Travel, adopted model held out (each home county left out): share-weighted error 3.26, big-flow error 3.45. Each
candidate added to the adopted set; change in held-out error [95%], coefficient (two-way p):

| Candidate | Share-weighted error | Big-flow error | Coefficient | Script |
|---|---:|---:|---:|---|
| Median household income × distance | +0.00 [−0.04, +0.06] | +0.01 [−0.03, +0.05] | +0.038 (0.12) | `civic_variables_test.py` |
| Per-capita income × distance | +0.06 [−0.02, +0.15] | +0.08 [+0.01, +0.14] (worse) | +0.081 (0.01) | `civic_variables_test.py` |
| Median age × distance | +0.06 [−0.00, +0.13] | +0.09 [+0.03, +0.16] (worse) | +0.076 (0.13) | `civic_variables_test.py` |
| Age 65+ × distance | +0.07 [−0.02, +0.15] | +0.11 [+0.04, +0.18] (worse) | +0.096 (0.04) | `civic_variables_test.py` |
| Households with broadband × distance | +0.03 [−0.06, +0.14] | +0.02 [−0.06, +0.10] | +0.109 (0.006) | `civic_variables_test.py` |
| Mean travel time to work × distance | +0.02 [−0.06, +0.12] | +0.06 [−0.02, +0.14] | −0.082 (0.001) | `civic_variables_test.py` |
| Below poverty × distance | +0.00 [−0.04, +0.05] | +0.01 [−0.04, +0.05] | −0.027 (0.29) | `civic_variables_test.py` |
| Bachelor's degree or higher × distance | −0.00 [−0.09, +0.09] | +0.03 [−0.03, +0.09] | +0.078 (< 0.001) | `civic_variables_test.py` |
| In labour force × distance | +0.01 [−0.00, +0.03] | +0.01 [−0.01, +0.02] | +0.004 (0.93) | `civic_variables_test.py` |
| Owner-occupied × distance | +0.01 [−0.01, +0.03] | +0.02 [−0.00, +0.06] | +0.005 (0.88) | `civic_variables_test.py` |
| Unemployment rate × distance | no estimates in `mo_county_acs_2024.csv`; not tested | | | `civic_variables_test.py` |
| Nearest hospital county | +0.01 [−0.03, +0.05] | +0.01 | −0.01 (0.86) | `hospital_test.py` |
| Nearest hospital county, and when home has none | −0.05 [−0.23, +0.13] | −0.04 | nearest_x_none −0.32 (< 0.001) | `hospital_test.py` |

None passes the selection rule. Several coefficients are clearly non-zero (degree, travel time, broadband, home
without a hospital) and improve nothing held out: they describe the fit, not a transferable pattern. (Superseded
2026-10-24: "degree × distance 3.43 against 3.51", a Jul–Sep big-flow error selected on the outcome, on undiscounted
visits.)

Hospitals: CMS Hospital General Information, general acute, critical access, children's, VA and DoD hospitals (no
psychiatric hospitals, no clinics), with Capital Region Medical Center added (it reports under MU Health Care's CMS
number since 2024): 107 hospitals in 67 counties (`build_hospitals.py`). Counties without a hospital have more
residents leaving; hospital terms do not improve held-out travel once each county's overall draw is measured
(coverage: 2026-10-16 specification, not rerun). To confirm: Cooper County Memorial Hospital (Boonville) and Southeast
Health Center of Ripley County (Doniphan) appear in OpenStreetMap but not in CMS.

## Revealed media market by travel pattern (2026-10-17; K rule 2026-10-24)

A town's revealed media market is (1) crossover of its residents into other counties, the potential demand, and (2)
spillover between the county pair in both directions, the supply. Residents do not share one travel pattern, so the
market is the most common pattern among them; secondary and tertiary patterns are separate maps. From 2026-10-20 each
mapped pattern is a **civic interest area**.

**Patterns** (`flows/travel_patterns.py`). Advan Neighborhood Patterns Plus, January-July 2026 (the months on 2020
block groups): for each home block group and each destination, reach = residents seen in the destination's busiest
block group / residents seen at home. Destinations: towns (2020 places), rural block groups outside towns, Missouri
counties outside the TV market; a block group's own town left out (masked). Travel is decomposed by non-negative
matrix factorization (mixed membership): each block group's travel is a weighted mix of K recurring patterns. Final
fit: lowest loss of 10 starts; masked multiplicative updates computed as the full product less the masked cells
(identical to 1e-14, ~6x faster).

**K rule (user, 2026-10-24, option A).** K = the largest K (grid 1-12, extended while its last K passes) at which every
pattern passes both:

| Test | Measure | Threshold |
|---|---|---|
| Town | at least one of the market's study towns (`flows/regions.json`) for which the pattern holds the threshold share of the town's residents, 1,000+ of them, and the threshold share of the town's travel -- the same town for all three | 10%, 1,000, 10% |
| Replicability, starts | median over 9 other random starts of the pattern's matched cosine (Hungarian) to the kept, lowest-loss fit of 10 | 0.9+ |
| Replicability, months | fitted to odd months (Jan, Mar, May, Jul) and to even months (Feb, Apr, Jun) separately, best of 5 starts each; odd and even patterns matched (Hungarian): every pair's cosine | 0.9+ |

Residents: devices at home / county-month calibration factor, split by each block group's membership (the areas'
allocation). Travel: residents x reconstructed reach, the sum over the town's block groups h and destinations u (own
town masked) of residents(h) W[h,k] H[k,u]. Per town, not per market: a share of the market depends on which home
counties form the market (Kansas City's 4th pattern, 64,348 residents, failed at 7.4% of 865,064 while Springfield's
5th, 39,488, passed at 10.4% of 378,908), and the area rule already requires 10% and 1,000 of a town's residents. A
5% level was rejected. Held-out month error (all 105 4 / 2 / 1 month partitions, every K on the same splits) is
printed as a persistence diagnostic only and does not choose K. Every K's tests, town by town, are in each market's
`patterns.json` (`criteria`, `sensitivity`, `stability.carrier_town_by_pattern`).

| Market | K | Carrying town of each pattern | K + 1 fails on | Fails by K (1-12) |
|---|---:|---|---|---|
| Columbia-Jefferson City | 3 | Ashland, Mexico, Vandalia | months (0.55) | 1-3 pass; 4-5 months; 6-8, 10 no town + months; 9, 11-12 no town + starts + months |
| Springfield | 7 | Springfield, Republic, Seymour, Republic, Springfield, Marshfield, Cassville | starts (0.20), months (0.25) | 1-7 pass; 8-11 starts + months; 12 no town + starts + months |
| Paducah-Cape Girardeau | 3 | Sikeston, Marble Hill, Jackson | months (0.72) | 1-3 pass; 4 months; 5-7 no town; 8-12 no town + replicability |
| Ottumwa-Kirksville | 3 | Macon, Kirksville, Lancaster | no town (Lancaster 917 residents), starts (0.86), months (0.54) | 1-3 pass; 4-12 no town + replicability |
| Joplin | 4 | Neosho, Webb City, Lamar, Carthage | no town (best: Webb City 4%, 467 residents) | 1-2 pass; 3 starts; 4 pass; 5-7 no town; 8-12 no town + replicability |
| Kansas City | 3 | Lexington, Independence, Harrisonville | starts (0.63) | 1-3 pass; 4-5 starts; 6 no town; 7-12 no town + replicability |
| St. Joseph | 3 | Maryville, St. Joseph, St. Joseph | months (0.81) | 1-3 pass; 4-6 months; 7-12 no town + starts + months |

The carrying town is the one where the pattern holds the most of the residents among the towns that pass. No market
passes at 12. Replicability binds in five markets; the town test binds alone in Joplin and with replicability in
Kirksville. Joplin's K is not the first failure: K = 3 fails replicability across starts (0.75), K = 4 passes.

Sensitivity -- K picked (town threshold for residents and travel x cosine threshold; 1,000 residents kept):

| Market | 10%: 0.85 / 0.90 / 0.95 | 15%: 0.85 / 0.90 / 0.95 | 20%: 0.85 / 0.90 / 0.95 |
|---|---|---|---|
| Columbia | 3 / **3** / 2 | 3 / 3 / 2 | 3 / 3 / 2 |
| Springfield | 7 / **7** / 7 | 7 / 7 / 7 | 5 / 5 / 5 |
| Cape Girardeau | 3 / **3** / 3 | 3 / 3 / 3 | 3 / 3 / 3 |
| Kirksville | 3 / **3** / 3 | 3 / 3 / 3 | 3 / 3 / 3 |
| Joplin | 4 / **4** / 4 | 4 / 4 / 4 | 4 / 4 / 4 |
| Kansas City | 3 / **3** / 3 | 3 / 3 / 3 | 3 / 3 / 3 |
| St. Joseph | 6 / **3** / 2 | 5 / 3 / 2 | 3 / 3 / 2 |

K holds from 10% to 20% in five markets; Springfield falls to 5 at 20%. At cosine 0.95 Columbia and St. Joseph fall
to 2; at 0.85 St. Joseph rises to 6. Stability of the kept fit, Columbia: 6 of 10 starts reach the same lowest loss;
matched cosine 1.00 for all three patterns; odd/even cosine 0.996, 0.918, 0.984. Persistence diagnostic (held-out
month error, points; K = 1 / 3 / 12): Columbia 0.701 / 0.613 / 0.594; error falls with every added pattern to 12 in six
markets.

**Residents** Each block group's estimated residents (devices seen at home / the county-month calibration factor, as
for crossover) are allocated to patterns in proportion to the travel each carries, and ranked: primary, secondary,
tertiary.

| Town | Estimated residents | Area | Main counties of the area's travel |
|---|---:|---|---|
| Columbia (82 block groups) | ~106,900 | 91%, ~97,020 (one area) | Boone 50% |
| Mexico (7) | ~7,130 | 92%, ~6,530 | Audrain 48%, Boone 16%, Callaway 10% |
| Linn (1 block group, holding the town) | ~1,790 | 71%, ~1,270 | Cole 25%, Osage 17%, Boone 11% |

Published areas (outline): Columbia 1,363 km2, Mexico 1,691, Linn 1,176. Mexico's area holds 95 Boone hexagons, with
Audrain 143, Callaway 71, Montgomery 2. Direction named on the maps: Columbia Jefferson City; Mexico Columbia,
Centralia; Linn Jefferson City.

**Market test** (`flows/market_patterns.py`). For each county in a pattern: crossover = the town's residents in the
pattern x the county's share of the pattern's travel; spillover both ways, March 2026, local outlets only, weighted as
the adopted measure. Mexico-Boone: 1,037 residents crossing, Audrain outlets' stories about Boone 10.0%, Boone outlets'
about Audrain 0.5% -- demand and one-way supply. Linn-Cole: 319 crossing, 8.1% and 0.2%. Columbia's area is
Boone-centred: no county outside Boone at 5%+ of its travel.

**Outlet homes** (user, 2026-10-24): an outlet's home county is the county it is filed under, except Mid Rivers
Newsmagazine (St. Charles) and Greene County Commonwealth (Greene) (`excluded_outlets.HOME_COUNTY`); their home town
for the incoming tie and the outlet circles is the covered county's seat, St. Charles city (not O'Fallon, the larger)
and Springfield. Registry: the pinned copy (`excluded_outlets.registry()`). Campus papers (`excluded_outlets.CAMPUS`)
are out of every coverage term. Neither change moves a Columbia-region figure.

**Local index, by 3 km hexagon** (adopted 2026-10-17; replaced the same day by the network tie). A place is local to a
resident through crossover (travel there), spillover out (home outlets' news located there) and spillover in (its
outlets' news located in home): local = travel x [(1 + out + in) / 3] ^ s, s = 1. Travel is THE TOWN'S OWN travel in
its pattern, not the pattern itself: a pattern is fitted across all the market's block groups, so it carries other
places' trips; each of the town's block groups' observed travel to a place is split across the patterns by the share
each explains there (the mixture's responsibilities), and the town's map is its travel attributed to its pattern
(busiest place = 1). Home is 100: the town's hexagons and every hexagon of its residents' own block groups. Coverage is
LOCATED, not counted by county: each March story's weight goes where it is -- a precise point to its hexagon, a town
(central place or named place) spread evenly over the town's hexagons, a county-only location spread evenly over the
county's hexagons; central 1, each other named location 0.5, Sports half, local outlets only. out = home outlets'
coverage of the hexagon's town (or rural block group) / their coverage of the home town; in = the share of the coverage
by outlets based in the hexagon's town (registry city) located in the home county / the same share for the home
county's own outlets; both capped at 1. A place travelled to with no coverage either way keeps a third of its travel
value; rural places the county's news does not locate stories in are dimmed, at home too. Values (out / in,
coverage only, 2026-10-17): Columbia -> Jefferson City 0.22 / 0.27; Mexico -> Columbia 0.10 / 0.03; Linn -> Jefferson
City 0.25 / 0.01.

**Network tie** (adopted 2026-10-17; replaces the local index). A town's market is a network: its residents tie to a
place by travelling there, and news ties strengthen that tie. "Local" is defined by travel; coverage amplifies a travel
tie and never creates one.

  tie(H, X) = travel(H -> X) x (1 + 0.3 out + 0.3 in + 0.7 shared places + 0.7 shared coverage), capped at home = 100

| Term | Measure (0-1) |
|---|---|
| travel | H's own travel to X in this market (busiest place = 1; rural block groups spread by destinations) |
| out | H's outlets' coverage located at X / their coverage of home |
| in | X's outlets' share of coverage located in H's county / H's own outlets' share |
| shared places | overlap coefficient sum_Y min(H's travel share at Y, X's outlets' coverage share at Y), third places only |
| shared coverage | overlap coefficient between H's outlets' and X's outlets' coverage, third places only |

Travel is worth more than coverage: the coverage weights sum to 2 (raised from 1 on 2026-10-17, when at 1 news ties
lifted a typical tie only 5-15% and barely showed), so coverage at its strongest triples a travel tie and a place
travelled to a third as often can at most tie it. Where news ties lift a tie by 10%+, the map marks the hexagon with an
orange dot sized by the lift (10%, 25%, 50%+). The overlaps (network closure: two places embedded in the same third
places) carry 0.7 of it, the single direct ties 0.3. A third place strengthens the pair, not itself -- Columbia
residents in Centralia, which the Mexico Ledger covers, strengthens Columbia-Mexico; Centralia's own tie is its own
travel and coverage -- so no coverage is counted twice. KRCG (registry town New Bloomfield) overlaps nearly every
town's coverage, but almost no one travels to New Bloomfield, so it stays faint: news is made there, but it is not
local to most residents. Weight sensitivity and the tie values quoted on 2026-10-17 were computed on the K = 6 areas
and are not rerun (appendix).

**Areas per town** (adopted 2026-10-17, rule unchanged): a pattern is mapped as an area only if 10%+ of the town's
residents follow it AND, beyond the primary, 1,000+ residents; the primary is always kept; at most three. A stated
threshold, like the hexagon floor of 5; held-out error does not test it. All 36 study towns, K = 6 (superseded
2026-10-24) -> current:

| Market | Town | K | Areas | Shares, % | Residents |
|---|---|---|---|---|---|
| columbia | Columbia | 6 -> 3 | 2 -> 1 | 72 / 16 -> 91 | 76,912 / 17,513 -> 97,020 |
| columbia | Mexico | 6 -> 3 | 1 -> 1 | 74 -> 92 | 5,241 -> 6,532 |
| columbia | Linn | 6 -> 3 | 1 -> 1 | 92 -> 71 | 1,641 -> 1,267 |
| columbia | Ashland | 6 -> 3 | 2 -> 1 | 79 / 19 -> 100 | 13,219 / 3,141 -> 16,625 |
| columbia | Centralia | 6 -> 3 | 2 -> 2 | 50 / 26 -> 60 / 40 | 2,937 / 1,516 -> 3,558 / 2,378 |
| columbia | Vandalia | 6 -> 3 | 1 -> 1 | 88 -> 89 | 3,064 -> 3,120 |
| columbia | Hallsville | 6 -> 3 | 1 -> 1 | 68 -> 64 | 1,216 -> 1,146 |
| columbia | Belle | 6 -> 3 | 1 -> 1 | 100 -> 57 | 1,099 -> 626 |
| springfield | Springfield | 6 -> 7 | 3 -> 3 | 31 / 31 / 18 -> 28 / 24 / 17 | 47,874 / 46,689 / 27,425 -> 42,590 / 35,891 / 25,417 |
| springfield | Republic | 6 -> 7 | 2 -> 3 | 48 / 31 -> 39 / 16 / 16 | 9,997 / 6,475 -> 8,243 / 3,356 / 3,294 |
| springfield | Marshfield | 6 -> 7 | 2 -> 2 | 52 / 46 -> 53 / 45 | 5,827 / 5,231 -> 5,957 / 5,075 |
| springfield | Monett | 6 -> 7 | 1 -> 1 | 84 -> 83 | 5,435 -> 5,380 |
| springfield | Cassville | 6 -> 7 | 1 -> 1 | 93 -> 92 | 3,259 -> 3,256 |
| springfield | Seymour | 6 -> 7 | 1 -> 1 | 82 -> 83 | 2,530 -> 2,549 |
| cape | Cape Girardeau | 6 -> 3 | 3 -> 2 | 36 / 28 / 18 -> 70 / 20 | 13,587 / 10,397 / 6,611 -> 26,202 / 7,438 |
| cape | Sikeston | 6 -> 3 | 1 -> 1 | 78 -> 94 | 11,037 -> 13,213 |
| cape | Jackson | 6 -> 3 | 2 -> 2 | 61 / 16 -> 81 / 16 | 7,582 / 2,025 -> 10,102 / 2,000 |
| cape | Scott City | 6 -> 3 | 2 -> 2 | 47 / 33 -> 65 / 31 | 1,647 / 1,156 -> 2,249 / 1,064 |
| cape | Marble Hill | 6 -> 3 | 1 -> 1 | 33 -> 62 | 743 -> 1,414 |
| kirksville | Kirksville | 6 -> 3 | 2 -> 2 | 72 / 14 -> 85 / 13 | 14,301 / 2,781 -> 16,864 / 2,541 |
| kirksville | Macon | 6 -> 3 | 1 -> 1 | 70 -> 86 | 3,842 -> 4,717 |
| kirksville | Lancaster | 6 -> 3 | 1 -> 1 | 50 -> 97 | 541 -> 1,048 |
| joplin | Joplin | 6 -> 4 | 3 -> 2 | 58 / 17 / 16 -> 74 / 24 | 31,491 / 9,291 / 8,940 -> 40,333 / 12,978 |
| joplin | Carthage | 6 -> 4 | 3 -> 3 | 43 / 35 / 12 -> 40 / 35 / 22 | 4,335 / 3,545 / 1,221 -> 4,008 / 3,499 / 2,207 |
| joplin | Webb City | 6 -> 4 | 2 -> 1 | 63 / 20 -> 89 | 7,780 / 2,511 -> 11,029 |
| joplin | Neosho | 6 -> 4 | 1 -> 1 | 80 -> 87 | 8,305 -> 9,080 |
| joplin | Lamar | 6 -> 4 | 1 -> 1 | 73 -> 88 | 3,870 -> 4,659 |
| kansascity | Independence | 6 -> 3 | 3 -> 3 | 40 / 27 / 10 -> 59 / 30 / 11 | 43,227 / 29,383 / 10,741 -> 63,153 / 32,565 / 11,518 |
| kansascity | Lee's Summit | 6 -> 3 | 3 -> 3 | 51 / 22 / 13 -> 51 / 32 / 17 | 86,012 / 36,956 / 21,724 -> 85,593 / 54,511 / 28,471 |
| kansascity | Blue Springs | 6 -> 3 | 1 -> 2 | 72 -> 80 / 11 | 54,202 -> 60,403 / 8,304 |
| kansascity | Grain Valley | 6 -> 3 | 2 -> 1 | 72 / 20 -> 93 | 16,597 / 4,587 -> 21,441 |
| kansascity | Harrisonville | 6 -> 3 | 2 -> 1 | 80 / 14 -> 92 | 9,932 / 1,710 -> 11,440 |
| kansascity | Lexington | 6 -> 3 | 1 -> 1 | 81 -> 98 | 5,020 -> 6,027 |
| stjoseph | St. Joseph | 6 -> 3 | 3 -> 2 | 34 / 22 / 17 -> 56 / 39 | 17,542 / 11,560 / 9,055 -> 29,100 / 20,062 |
| stjoseph | Savannah | 6 -> 3 | 2 -> 3 | 37 / 25 -> 50 / 28 / 22 | 1,971 / 1,301 -> 2,627 / 1,469 / 1,181 |
| stjoseph | Maryville | 6 -> 3 | 2 -> 1 | 77 / 14 -> 89 | 6,740 / 1,184 -> 7,794 |

Areas: 57 (63 at K = 6); the count changed for 12 of 36 towns: Columbia 2 -> 1, Ashland 2 -> 1, Cape Girardeau 3 -> 2,
Joplin 3 -> 2, Webb City 2 -> 1, Grain Valley 2 -> 1, Harrisonville 2 -> 1, St. Joseph 3 -> 2, Maryville 2 -> 1 (fewer);
Republic 2 -> 3, Blue Springs 1 -> 2, Savannah 2 -> 3 (more). Most towns have one dominant area (Columbia 91, Mexico 92,
Sikeston 94, Lancaster 97); Springfield (K = 7) keeps a three-way split (28 / 24 / 17).

**Rural shading, dasymetric** (adopted 2026-10-17): Advan locates travel no finer than a block group, and a rural one
covers 30-60 hexagons (Barton County outside Lamar: 5 block groups). Within a rural block group, travel is spread by
OpenStreetMap destinations (115,453 statewide, `flows/build_destinations.py`): a hexagon's weight is (destinations +
0.25) / the block group's mean of the same, so the block group's average is kept, farmland falls and destinations rise;
travel capped at 1. Towns keep one value. A floor of 1 left sparse rural counties one flat band.

**Network tie, revised** (2026-10-17, Columbia first; other markets after the weights settle):
- Home county: home outlets' market is their county, so every home-county hexagon carries their outgoing tie (1.0).
  Before, outgoing coverage was compared with the home town, and rural home-county hexagons got almost none.
- Shared coverage counts only places in the town's own market (travel 0.05+ of the busiest). Two newsrooms both
  reporting statewide news (the capital, the university) had tied Columbia to Kansas City.
- Spatial network effect: adjacency tie' = tie + 0.25 x ring-weighted mean of neighbours (rings 1-3 at 1/2, 1/4, 1/8),
  only where residents travel; direction x (1 + 0.5 R cos(bearing - the market's mean bearing)), R the tie-weighted
  resultant length -- a market's direction strengthens, the opposite side weakens. On a hexagon grid queen and rook
  contiguity coincide (6 neighbours).
- Gate on the shared ties: shared places and shared coverage count only when the pair already covers each other (out +
  in of 0.10+ of home). Without it, Columbia's heavy coverage of Jefferson City, where Linn residents go, tied Linn to
  Columbia although the two barely cover each other.
- Dots only outside the home county: home outlets' coverage of their own county is the baseline of local news and
  stays in the blue shade; dotting it buried the ties between places under a uniform blanket.
- Headroom: travel is scaled so a town's busiest destination is 50; home stays 100. At 100 the top destination started
  at the cap and its news ties could not show (Linn's paper covering Jefferson City, Linn's busiest destination).
- Orange dots mark what news coverage alone adds (before the spatial effect): 10%, 25%, 50%+.
- ONE SCALE (adopted 2026-10-17; replaces a TV-market frame and a zoom rule): every map is a fixed frame about 190 x 180
  km -- the size of the Columbia-Jefferson City TV market, some 12-16 counties -- centred on the town's area (the
  tie-weighted centre of its hexagons of 10+), shifted only to keep the home county in view. Three counties (St.
  Joseph's, Kirksville's TV markets) was too close; 26-27 (Springfield's) too far. The TV-market outline stays
  as a reference line. Travel data and county lines cover Missouri only: across a state line the frame is blank.
- Display selectivity: each map shows only the hexagons holding the strongest 50% of its ties outside home (floor never
  below 5; isolated hexagons need up to twice it). Cuts the long tail so compact and diffuse areas read alike. At 80%
  the floor fell to 3-4 and cut nothing. Hexagons shown beyond home, current: Columbia 108, Mexico 123, Linn 122.

**Frame and display** (adopted 2026-10-17): destinations are all of Missouri (towns and rural block groups) so travel
across a TV-market border is measured. Hexagons show at 5+ inside the TV market and 10+ outside it, so one-off distant
trips and rural destination clusters stay off. Labels: home town bold; up to 8 towns on shaded hexagons in ink; up to 4
unshaded towns of 20,000+ in small grey.

**Markets fitted separately** (`flows/regions.json`; `build_homes.py`, `travel_patterns.py <region>`,
`market_patterns.py <region>`): each TV market's patterns are fitted on its own home counties only, so adding a market
never changes another's maps (Columbia's fit verified identical after the change, 2026-10-17). Seven: Columbia-Jefferson City (Audrain, Boone, Osage), Springfield (Greene, Webster,
Barry), Paducah-Cape Girardeau (Cape Girardeau, Scott, Bollinger), Ottumwa-Kirksville (Adair, Macon, Schuyler), Joplin
(Jasper, Newton, Barton), Kansas City (Jackson, Cass, Lafayette), St. Joseph (Buchanan, Andrew, Nodaway). K by market
under the K rule above (3-7). Advan covers Missouri destinations only: trips into Kansas, Illinois, Iowa and Arkansas
are not seen (largest for Kansas City). Macon County had no local stories in March: no outgoing coverage there.

**Figure** (`flows/market_pattern_print.html`; title "<Town>'s civic interest area" since 2026-10-20, earlier "<town>'s
revealed news market"): a modelled map on the hexagon grid; hexagons of 5+ shaded, one ring of empty hexagons as a
border, labels never on a dark (20+) hexagon. A shaded rural block group or tract can cover half a county; the grid
marks the figure as a model.

Superseded on the way (kept in `flows/`): tract reach maps (`build_reach_map.py`, a shrunk logistic model chosen on
held-out months, corridor term adopted, direction and home-town terms no gain) and a travel x coverage interest index
(`build_interest_map.py`, w = 0.5/1/2, with road corridors from `build_transit_lines.py`).

### Selection rule: sensitivity test (2026-10-18; rerun 2026-10-24)

`analysis/selection_sensitivity.py` -> `analysis/selection_sensitivity.csv`. The three published areas (Columbia,
Mexico, Linn), each drawn under eight variants of the selection rule. Criterion: **split-half replicability**, the
Jaccard overlap of the hexagons the same rule draws from odd months (Jan, Mar, May, Jul) and from even months (Feb, Apr,
Jun), home hexagons (value 100) excluded (as in `market_stability.py`; home is in every draw and inflated the overlap).
Replicability, not validity: the rule draws the same area from either half of the year; that does not show the area is
the right one. Same pattern weights in both halves.

Replicability (hexagons beyond home drawn from odd / even months):

| Variant | Columbia | Mexico | Linn | Mean |
|---|---:|---:|---:|---:|
| **Adopted: 50%, 2x at 4 hexagons** | 0.76 (128 / 99) | 0.75 (136 / 110) | 0.58 (150 / 125) | 0.70 |
| Selectivity 40% | **0.86** (107 / 94) | 0.63 (88 / 60) | 0.54 (71 / 69) | 0.68 |
| Selectivity 60% | 0.68 (169 / 117) | 0.68 (235 / 180) | 0.56 (222 / 173) | 0.64 |
| No distance rule | 0.86 (233 / 202) | 0.77 (165 / 148) | 0.57 (164 / 145) | **0.73** |
| Distance 1.5x | 0.80 (137 / 112) | 0.76 (150 / 126) | 0.58 (154 / 132) | 0.71 |
| Distance 3x | 0.86 (111 / 97) | 0.65 (117 / 79) | 0.54 (144 / 117) | 0.68 |
| Distance reach 2 hexagons | 0.82 (119 / 99) | **0.78** (132 / 106) | 0.57 (147 / 123) | 0.72 |
| Distance reach 6 hexagons | 0.74 (134 / 101) | 0.70 (147 / 111) | **0.59** (153 / 126) | 0.67 |

Hexagons shown beyond home under the adopted rule (all months): Columbia 108, Mexico 123, Linn 122; share holding in
both halves 0.95, 0.98, 0.75. The adopted values are within 0.03 of the best mean; no distance rule scores 0.73 but in
Columbia draws 218 hexagons of which 58% hold in both halves (adopted 95%). Area overlap with the published area (IoU):
Columbia 0.53-1.0 (lowest without the distance rule), Mexico 0.52-1.0 (distance 1.5x), Linn 0.45-1.0 (60%
selectivity). The adopted values were set for legibility, not tuned to replicability.

### Coverage density: the supply into a civic interest area (2026-10-20; rerun 2026-10-24)

**Coverage density** (name set by the user) is the supply side of the assessment: for each 3 km hexagon of a published
civic interest area (the footprint: hexagons whose centres lie inside its outline; every hexagon counts the same), the
local news stories in a month whose area includes it. Central focus counts 1, a mention 0.5, Sports half. A story's
area follows its geographic scope (the enrichment's scope classification): neighbourhood 3 km around its point; town
the 2020 place and 3 km around it (5 km around a point outside any town); regional 40 km; a county-only point or a
county mention the whole county; statewide, national and international stories none. Local outlets statewide;
statewide and campus outlets excluded. Tiers (user; names from 2026-10-20, first written "daily" and "weekly"):
frequent 9+ a month (2-3 a week), regular 2-8 (2-3 a month as the floor), sporadic under 2, none.
`analysis/area_coverage_alignment.py` -> `analysis/area_coverage_alignment.csv`, `flows/reach/coverage_columbia.json`;
map: `market_pattern_print.html?measure=coverage` (`&cov=local` leaves out county-level stories and county mentions).
Whether a county mention counts across every hexagon of the county is settled by the attribution rule below.

### Name: civic interest areas (2026-10-20)

The local information needs areas are renamed **civic interest areas** (user): residents' activity areas of news
interest. Map titles: "<Town>'s civic interest area", numbered I, II, III only when a town has more than one
(Columbia, one area since 2026-10-24: no numeral). Earlier sections keep the name they were written under. Supply into
an area: coverage density. Units of analysis: county -> civic interest area -> each outlet's zone of service; no
statewide measure is a finding.

### Coverage density: attribution by region size (2026-10-20, adopted; rerun 2026-10-24)

City, county and region claims apply to the whole region, diluted by its size (user): weight per hexagon = story weight
(central 1, mention 0.5) x (7 / the region's hexagons) ^ 0.5, full weight at 7 hexagons or fewer (a neighbourhood, a
town the size of Linn); counties and regions spread by 2020 block-group population. **Revised the same day (user: the
square root "overvalues mentions and county-wide coverage"; the region "looks well-covered, which it is not").**
Counties and regions are counted once (alpha = 1, spread by population); towns and neighbourhoods keep the square
root. Current results (`area_coverage_alignment.py`):

| Area | Hexagons | Frequent | Regular | Sporadic | None | Newsrooms for 80% of regular / frequent |
|---|---:|---:|---:|---:|---:|---|
| Columbia | 259 | 44% | 8% | 48% | 0% | 2 / 1 |
| Mexico | 311 | 32% | 4% | 64% | 0% | 2 / 3 |
| Linn | 219 | 21% | 8% | 71% | 0% | 2 / 2 |

Sensitivity, towns also counted once (`ALPHA=1` -> `*_alpha1` outputs), frequent / regular / sporadic: Columbia 44 / 8 /
48; Mexico 29 / 7 / 64; Linn 20 / 9 / 71. Frequent coverage barely moves with alpha (it is place-specific reporting);
the regular tier is what county-wide stories supply. The count for 100% of a tier is not reported: the last hexagons
are reached by fractions of distant outlets' county mentions.

**Map (user decisions, 2026-10-20).** Tiers in separate colours first, then the scale stops at frequent (9+ a month)
as one colour: the volume steps above it (30-99, 100+) peaked in the population centres and showed population size.
Stories stay a monthly count, not per capita (user). A blurred surface beneath the grid was tried and rejected (user:
the blur "just does not work" beside the civic interest area maps; `?surface=1` keeps it): each hexagon is filled with
the continuous green (log scale, capped at 9+ a month) with white gaps, as the area maps; the key is a word-only
gradient from "rarely" to "several a week or more"; the subtitle keeps the tier shares. Lines step back on the coverage
map (lighter grid, county borders, home county and TV market).

### Balanced diet of civic information (2026-10-20; rerun 2026-10-24)

`analysis/cin_diet.py`. The ten CIN categories of the codebook (the eight critical information needs, Friedland et al.
2012, plus Civic Life and Sports). A hexagon has a **balanced diet** when any 8 of the 10 reach 1 story a month each by
coverage density (user: "8 of 10 served, but any 8"). The coverage density map is filtered by it (user: "volume is not
enough, balance is also required"): coverage is shaded only where the diet is balanced; elsewhere pale (`?balance=0`
turns the filter off). Sports at half weight in coverage density from 2026-10-20 (user).

| Area | Hexagons | Balanced | Mean categories met | Home town | Outlets for the balanced share |
|---|---:|---:|---:|---|---:|
| Columbia | 259 | 44% | 4.4 | Columbia balanced (10 of 10) | 3 |
| Mexico | 311 | 15% | 2.4 | Mexico 6 of 10 | 3 |
| Linn | 219 | 16% | 1.8 | Linn 6 of 10 | 2 |

Only Columbia and Jefferson City carry a balanced diet. Outlets required for the balanced share are exact, every
combination of the top 24. Economic Development is the scarcest category: none in Linn's area, 14% of Mexico's. The
earlier outlets-required calculation on volume alone (`outlets_required.py`) is superseded: one broadcaster and one
weekly cannot supply a balanced diet.
**Map: volume as colour, breadth as size (user, 2026-10-20).** The binary balance filter was "too flat", and the shade
graded by volume x balance did not show volume without breadth. Each hexagon's colour is its stories a month; its size
is its breadth, full at 8+ of the 10 categories and shrinking to 40% with fewer, on a pale full-size grid -- a small
dark hexagon is plenty of news of a narrow kind (Moberly, Mexico, Boonville); only Columbia and Jefferson City are full
size.

## Open

- One month of coverage limits every story-count comparison; counts per county pair are small.
- Coverage, saturation: the level version (rural home × destination's own stories) was tested only within the
  all-factors model; it was not tested alone.
- Coverage under the joint selection rule: the adopted set against fixed effects alone is not reported, and the
  shared gravity terms are carried from the travel model (commuting out −0.02, n.s., in coverage).
- Coverage figures not rerun on the adopted specification and reviewed destination sets: `combined_marginal_test.py`
  and `combined_all_factors_test.py` still score coverage on the outcome-selected destination set (2+ held-out
  stories), and the all-factors column without destination effects is not re-scored; County characteristics,
  coverage column (4.00 baseline, hospitals 4.01); collection-quality coverage response (pooled specification only).
- Out-of-state travel: Kansas is measured (11.6% of Missouri residents' out-of-county visits; 37.7% for the 14 border
  counties). Illinois, Iowa, Arkansas, Oklahoma and Nebraska destinations are not in the data; eastern and southern
  border counties are understated by an unmeasured amount.
- Calibration: the median factor is about 2, not 1, and rises in spring (April 2.54). Question for Advan.
- Travel: unemployment rate × distance not tested (no estimates in `mo_county_acs_2024.csv`). Athletic conferences:
  statewide test pending; the three-county figure is against the 2026-10-18 model, not rerun.
- Spillover: the Centralia Fireside Guard and Vandalia Leader have no usable spillover figure (short texts).
  Expectations for the 33 outlets that are not well collected are extrapolations. Held out, St. Joseph and
  Quincy–Hannibal do worse than intercept only.
- Public travel model: no setting or correction is stable for the 9-county commuter classes — the major-metro rings'
  Stage 1 choice changes with the county left out (nested 6.96 vs in-sample 5.36), the regional-hub rings' with fold 1
  (outer-loop corrections 6.12 vs 4.27 in-sample); the destination pull needs public measures beyond sales and
  population (hospital, four-year college, supercenter, interstate, lakes and parks, county seat).
- Public travel model, not rerun on the adopted outcome and common destination set: the gap decomposition
  (`public_gap_corrections.py`), the setting sensitivity (`public_default_sensitivity.py`), and Missouri corrections
  applied to Kansas small rural counties only.
- Kansas: the public model's 200-mile destination radius leaves 9.1% of Kansans' Advan share (max 40.7%, Thomas)
  outside every score; a wider radius for the Kansas builds is untested. The Kansas outcome is not pass-through
  discounted.
- Civic interest areas: network-tie values, weight sensitivity and display floors were computed on the K = 6 areas
  and are not rerun on the K-rule areas. Linn's area replicates least (0.58; 0.75 of shown hexagons hold in both
  halves).
- Tie markets: Columbia's public market reaches 0.13 of Advan's beyond Boone: the public model sends Columbia's
  out-of-county travel overwhelmingly to Jefferson City. The Kansas transfer of travel markets and the comparison with
  conventional market definitions (2026-10-18) have not been rescored with home masked and the score taken beyond the
  home county.
- Hospitals: Cooper County Memorial Hospital (Boonville) and Southeast Health Center of Ripley County (Doniphan) are in
  OpenStreetMap but not in CMS.

## Sources

- U.S. Census Bureau. (2025). *Annual estimates of the resident population for incorporated places and minor civil divisions in Missouri: April 1, 2020 to July 1, 2024* (SUB-EST2024_29) [Data set]. https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/cities/totals/sub-est2024_29.csv (place-in-county rows and 2020 base population: outlets' home counties)

- U.S. Census Bureau. (2025). *Business Dynamics Statistics: 2023 release, establishment characteristics by state and county* [Data set]. https://www2.census.gov/programs-surveys/bds/tables/time-series/2023/bds2023_st_cty.csv

- Advan Research. (2026). *Foot Traffic / Neighborhood Patterns Plus* [Data set]. Dewey Data. January–September 2026,
  Missouri and Kansas destinations. [DOI to add from the Dewey dataset page.]
- Advan Research. (2025). *Foot Traffic / Weekly Patterns Plus* [Data set]. Dewey Data.
  https://doi.org/10.82551/C103-N851. Weeks of March 2–30, 2026, Missouri.
- Missouri School of Journalism. (2026). Analysis of local news stories, March 2026: stories and their places from the
  Missouri School of Journalism local news collection.
- Missouri Secretary of State. (2025). *Official manual, State of Missouri, 2025–2026*. Newspaper listings (publication
  frequency codes).
- U.S. Census Bureau. (2025). *American Community Survey 2020–2024 5-year estimates*, county population and 24
  demographic measures; county per-capita income (B19301), Missouri and Kansas.
- U.S. Census Bureau. (2025). *LEHD Origin-Destination Employment Statistics (LODES 8)*, Missouri and Kansas, 2023.
- U.S. Census Bureau. (2021). *2020 Census centers of population by county* (CenPop2020).
- U.S. Census Bureau. (2023). *2020 Census urban areas: county-level urban and rural information* (2020_UA_COUNTY).
- U.S. Census Bureau. *Cartographic boundary files*: 2020 counties, county subdivisions, places and block groups;
  2010 block groups.
- U.S. Census Bureau. (2025). *Metropolitan and micropolitan statistical area population estimates, Vintage 2024*.
- U.S. Office of Management and Budget. (2023). *Core-based statistical area delineation file* (list1_2023).
- U.S. Department of Agriculture, Economic Research Service. (2023). *Rural-Urban Continuum Codes*.
- Centers for Medicare & Medicaid Services. *Hospital General Information* (Provider Data Catalog), Missouri.
- Internews Listening Post Collective and Brown University Information Futures Lab. (2026). *Civic Information Index*.
  https://civicinfoindex.org
- OpenStreetMap contributors. Missouri extract via Geofabrik (road network for driving times; hospital check). Open
  Database License.
- Nielsen. Designated Market Area boundaries (Columbia–Jefferson City).
- U.S. Census Bureau. (2024). *County Business Patterns 2022* (cbp22co) [Data set].
- U.S. Census Bureau. (2025). *American Community Survey 2020–2024 5-year estimates, table-based summary file*, tracts:
  B19013, B19001, B15003, B25003, B08006; B01003 (Missouri and Kansas).
- U.S. Census Bureau. (2025). *LODES 8 auxiliary origin-destination files*, 2023: IL, KS, IA, AR, OK, NE, TN, KY (for
  Missouri); MO, NE, OK, CO (for Kansas).
- U.S. Census Bureau. (2021). *2020 Census centers of population by census tract*, Missouri and Kansas.
- Federal Highway Administration. (2024). *2022 NextGen National Household Travel Survey*, public use files v2 (trip,
  long-distance) and codebook. https://nhts.ornl.gov
- Missouri Department of Revenue. (2026). *Public taxable sales reports, 2025*: by county (DI60IT15_SLS_CNTY) and by
  county and NAICS (DI60IL08_SLS_SICCNTY). https://dor.mo.gov/public-reports
- Kansas Department of Revenue. (2025). *County trade pull factors, FY2025*.
- Christaller, W. (1933/1966). *Central places in southern Germany*. Prentice-Hall.
- Reilly, W. J. (1931). *The law of retail gravitation*. Knickerbocker Press.
- Huff, D. L. (1964). Defining and estimating a trading area. *Journal of Marketing, 28*(3), 34–38.
- Yuan, Y., & Xu, Y. (2022). Modeling activity spaces using big geo-data: Progress and challenges. *Geography
  Compass*, e12663. https://doi.org/10.1111/gec3.12663
- Bisiani, S., Gulyas, A., & Heravi, B. (2025). Mapping news geography: A computational framework for classifying local
  media through geographic coverage patterns. *Computational Humanities Research 2025*, Anthology of Computers and the
  Humanities 3, 860–881. https://doi.org/10.63744/PmuIcNvSnDuo
- U.S. Census Bureau. (2025). *LODES 8 workplace area characteristics*, Missouri and Kansas, 2023
  (mo_wac_S000_JT00_2023).
- U.S. Census Bureau. (2023). *County adjacency file* (county_adjacency2023).
- Schläpfer, M., et al. (2021). The universal visitation law of human mobility. *Nature, 593*, 522–527.
- Simini, F., González, M. C., Maritan, A., & Barabási, A.-L. (2012). A universal model for mobility and migration
  patterns. *Nature, 484*, 96–100.
- Friedland, L., Napoli, P., Ognyanova, K., Weil, C., & Wilson, E. J., III. (2012). *Review of the literature regarding
  critical information needs of the American public*. Federal Communications Commission.
- Software: Python, statsmodels, pandas, shapely, SciPy, pyosmium; D3 for figures.


## Superseded figures

Every figure replaced on 2026-10-24, with what replaced it and why. "Not rerun" = no replacement figure; the old one
stands only as dated history.

| Model | Figure (where) | Was | Now | Why |
|---|---|---|---|---|
| Travel | Predicts Jul–Sep shares (Travel model; calibration; commuting) | 93%; 94% with commuting | Held-out R² 93.8% [92.4, 94.9]; Jul–Sep stability R² 93.8% against persistence 98.6% | Squared correlation, not R²; the Jul–Sep split is beaten by persistence |
| Travel | Steps table | Deviance 480M / 359M / 275M / 165M / 137M; Jul–Sep 76% / 81% / 86% / 92% / 93%; top destination 1.63× / 1.42× / 1.22× / 1.15× | Steps table: in-sample deviance 358.2M … 68.8M; held-out R², error, forecast-selected top destination | Old columns in-sample and selected on the observed share |
| Travel | Singly-constrained model's main destinations | Under-predicted by 1.6× (also Comparisons withdrawn) | 1.19× held out, forecast-selected; held-out error 7.25 against 3.26 | Selected on the outcome; in-sample |
| Travel | Osage → Cole, adopted model | 1.15–1.2× | 1.09 in-sample, 1.14 held out | Commuting terms; held out |
| Travel | Top destination, actual ÷ forecast | 1.15–1.2× | 1.02× held out, forecast-selected (1.11× observed-selected) | Selection on the outcome |
| Travel | Big flows, actual ÷ predicted, middle 80% | 0.73×–1.88× | 0.57×–1.51× (median 1.01×), held out, forecast-selected | In-sample, observed-selected |
| Travel | Calibration effect on log distance | −2.14 → −1.58 | Elasticity at 25 mi: metro −0.95 → −0.89, nonmetro −0.45 → −0.46 | Uncentred coefficient was not an elasticity at any point |
| Travel | Calibration, outlet model | "Unchanged (broadcaster 0.70, crossover 1.47)" | Adopted spillover model has no travel term | Spillover model replaced |
| Travel | Pass-through discount | Removes 3.0% of out-of-county visits | 2.3% (3,314 pairs) | Recomputed on the adopted outcome |
| Travel | Commuting gains, held out | Small rural 3.76 → 3.28, top-3 4.81 → 4.25; independent towns 3.05 → 2.79; commuter 4.13 → 3.82; hubs 2.43 → 2.11 | 3.94 → 3.44, 4.86 → 4.31; 3.18 → 2.83; 4.28 → 3.85; 3.04 → 2.47 (with intervals) | Adopted outcome; forecast-selected top-3 |
| Travel | Driving time | Deviance 137M → 136M; Jul–Sep 93.0% → 92.3% | +0.07 [−0.14, +0.31] held out | Held-out validation |
| Travel | "On the way" factor | Deviance 134M, no change in prediction | +0.171 (p < 0.001); −0.05 [−0.27, +0.22] held out | Held-out validation |
| Travel | Competing destinations: alternatives | −0.05 and 0.00; deviance 80.0M → 79.5M / 80.0M | Nearest comparable −0.065 (p = 0.04), −0.051 [−0.100, −0.002], fails the nested test; other directions −0.01 [−0.04, +0.02] | Adopted model; held out; nested test |
| Travel | Fotheringham C_ij | −0.83; deviance 80.0M → 78.9M; big pairs within 46% → 44%; Osage → Cole 1.28× → 1.21× | −1.04; 68.8M → 67.2M; +0.02 [−0.08, +0.14] held out; within 49% → 50%; Osage → Cole 1.09× → 1.02× in-sample | Adopted outcome and terms |
| Travel | Tier-specific decay | Hubs 2.02 → 1.77 | Hubs 2.47 → 2.36 (−0.11 [−0.67, +0.46]); all tiers +0.17 [+0.00, +0.35] | Adopted model; intervals |
| Travel | Tier and county pull of jobs and retail | 3.75 → 3.70 / 4.79 → 4.68; jobs pull 1.60 (small rural) vs 1.39 (hubs) | `travel_tier_pull_cv.py`: pooled 3.86 / 4.80, tier pull 3.81 / 4.72, county pull 3.82 / 4.70; pull coefficients not reported | Outcome then not discounted; standardisation used held-out counties |
| Travel | Job-hub distances | All worse (3.93–4.60) | 3.40–3.48 against 3.35; every interval spans zero | Adopted model; intervals |
| Travel | Separate model for small origins; tier decay | "No gain except hubs" | 3.76 [3.21, 4.35] against pooled 3.32 [2.78, 3.93] on the same pairs | Held out with intervals |
| Travel | Jobs per resident; metro destination; nearest area centre | p = 0.44; p = 0.27; p = 0.74 | Singly constrained only: jobs p = 0.69, metro p = 0.75 (two-way); nearest centre in the adopted model p = 0.18 | Two-way clustering; model stated |
| Travel | Same metro/micro; intervening opportunities; destination size × distance; adjacent centre | Deviance unchanged; small gain; small gain; deviance −3M | Held-out changes with intervals (Rejected) | Held-out validation |
| Travel | All marginal factors | 3.58 / 3.39 / 4.04; 93.1% / 93.6% / 90.4%; within ±25% 49% / 49% / 42%; "about 5% gain with all eight" | 3.26 / 3.15 / 3.84; 93.8% / 93.9% / 91.4%; 49% / 50% / 43%; −0.11 [−0.31, +0.10] | Held out; intervals; nested choice |
| Travel | County characteristics, travel column | Baseline 3.51; degree × distance 3.43; hospitals 3.48 | Baseline 3.26 / 3.45; degree −0.00 [−0.09, +0.09]; hospitals +0.01 and −0.05 (County characteristics) | Jul–Sep big-flow error selected on the outcome; undiscounted visits |
| Travel | Tier sizes | Hubs 8 | Hubs 8 in `county_class_k4.csv` (114 counties); scored, 9 with St. Louis city (115 homes) | St. Louis city and county scored apart |
| Coverage | Headline elasticity | "About 0.7–0.8% more stories per 1% more visits" | Metro 0.49, nonmetro 0.25 | No distance terms: distance loaded onto visits |
| Coverage | Response to travel (calibration; commuting) | 0.52; "falls from 0.52 to 0.36" with commuting; twice the travel → 1.4×, then 1.3× | Metro 0.49 (1.40×), nonmetro 0.25 (1.19×); pooled 0.36 (sensitivity) | 0.52 was log distance + border only; log visits replaces travel beyond gravity; nonmetro interaction adopted |
| Coverage | Commuting terms | In +0.51 (p < 0.001), out +0.04 | In +0.42 (s.e. 0.073, clustered), out −0.02 (n.s.) | Adopted specification; clustered s.e. |
| Coverage | Saturation | Response 0.67 → 0.50 between none and 500 own stories; p = 0.004 all, < 0.001 print; "real and in the predicted direction" | Own stories −0.007 (p 0.34); × nonmetro p 0.83 (print 0.80): not supported | Separate non-adopted model; HC1 on non-independent pairs |
| Coverage | Saturation held-out error | 4.15 → 4.12 | Adopted 0.913 (all destinations), 4.42 (1%+ of visits); changes ≤ 0.021, intervals span zero | Destination set chosen partly by the held-out county's own stories |
| Coverage | Border test | "Not detectable (±60% at 95%)"; raw "about half the story share" | Slope difference +0.04 (95% CI −0.04 to +0.12); raw 6.7% and 7.8% against 15.8% | HC1; specification labelled |
| Coverage | All marginal factors | 4.15 / 4.14 / 4.18; print 4.50 / 4.58 / 4.52 | 0.91 / 0.91 (all destinations), 4.42 / 4.39 (1%+); print 0.94 / 0.93, 4.53 / 4.50; third column not re-scored | Outcome-selected destinations; prior specification |
| Coverage | Collection quality | 0.52 → 0.48 (all), 0.50 → 0.42 (print) | Pooled specification: 0.36 → 0.26, 0.34 → 0.25; adopted metro/nonmetro form not rerun | Old specification |
| Coverage | County characteristics column; hospitals | 4.00; 4.01 | Not rerun | Outcome-selected destinations; old specification |
| Coverage | Zero-visit pairs | At log(1e-3) | Indicator + log visits where > 0 (elasticities move ≤ 0.006) | Leverage |
| Spillover | 2026-10-16 models (whole section) | Broadcaster +0.70, travel out +1.47, held-out 14.5 (broadcaster only 15.5; full 15.3); urban-share model 15.0, well collected 14.1, coefficients +0.65 / −0.81 / +1.17 | Broadcaster + print outlets: +0.667, −0.387; held-out 5.98 / 4.66 | Earlier measure (any story touching another county); earlier data |
| Spillover | 2026-10-17 intermediate re-run | 83 outlets, 46 counties; held-out 7.1 (8.6 before); broadcaster +0.58, crowded weekly −0.47, border −0.17, print outlets −0.42; Cole 30% / 33% (36% with statewide outlets); Jackson 29% / 29%; KC Beacon 37% → 23%, The Pitch 28% → 26%; Boone print 23% / 20% | Current model; Cole 23% / 25%, Jackson 22% / 21%, Boone print 18% / 19%, KC Beacon 17% / 15%, The Pitch 24% / 13% | CAMPUS, HOME_COUNTY, market-count rule, one home rule, joint test |
| Spillover | 2026-10-17 model: fitted outlets, counties | 87, 47 (also 83, 43 in the model description) | 85, 48 | HOME_COUNTY, CAMPUS |
| Spillover | Outlets with 10+ stories | 133 | 128 | CAMPUS |
| Spillover | Broadcaster | +0.68 (p < 0.001, z); +0.71 | +0.667 (< 0.001, t); CI +0.388 to +0.939 | Clustered t, bootstrap |
| Spillover | Weekly in a daily-and-TV county | −0.56 (0.008); −0.37 (0.05) | Not adopted (change +0.09, −0.05 to +0.27) | Joint test |
| Spillover | Miles to the county edge (log) | −0.14 (< 0.001), every outlet; −0.17 (0.001) | Not adopted (change −0.08, −0.45 to +0.33) | Joint test |
| Spillover | Print outlets in the county | −0.28 (0.001); −0.41 (0.01) | −0.387 (< 0.001); CI −0.655 to −0.232 | Market-count rule; joint test |
| Spillover | Held-out error | 6.0; 8.62 / 7.20 (83-outlet fit) | 5.98 / 4.66 | Current model |
| Spillover | Nested | 9.18 / 7.81 (pre-rerun data); same pair in 38 of 43 folds | 6.27 / 4.76; same set in 47 of 48 folds | Selection rule inside each fold |
| Spillover | Alternative models (83-outlet fit) | Broadcaster + crowded weekly 9.39 / 7.05; + town population 9.45 / 8.24; broadcaster + town population 9.79 / 8.64 | Broadcaster + crowded weekly 6.98 / 5.35; broadcaster + town population 6.33 / 5.19 (`spillover_outlets.py`); broadcaster only 7.02 / 5.11 | Current data and definitions |
| Spillover | Audrain / Boone / Osage | 20% / 23%; 29% / 24% (print 18% / 16%); 26% / 24% | 20% / 22%; 29% / 26% (print 18% / 19%); 26% / 25% | Current model |
| Spillover | Springfield region held out | 10.9 (crowded 11.7, town population 11.9), 28% / 29%, Webster 44% / 26%; then 8.6, 27% / 27% | 8.0 (crowded 9.0, town population 8.8), 24% / 26%, Webster 36% / 23% | Current model |
| Spillover | Weight table | Rates 30.6% / 25.6% / 20.5% / 22.1% / 18.6% / 15.1%; held-out 7.1 / 6.0 / 6.8 / 6.7 / 5.5 / 5.6; "held-out ÷ mean" ranking; "best combination uses mention 0.5" | Measure sensitivity table: skill and out-of-sample R² against intercept only; weights are definitions | No code for the ranking; weights are not selected |
| Spillover | Leave one market out | Weight combinations per market, mean 23.1 vs 23.4 (24.2 vs 23.7 without Columbia–Jefferson City) | Adopted model per market: 5.9 in sample, 6.2 held out, intercept only 7.4 | No code; weights are definitions |
| Spillover | By outlet type; non-weeklies only; Vandalia Leader 34% expected; Boone County Journal 15%, Centralia Fireside Guard 17% | 10.03 → 7.86 etc.; 9.40; 34%; 15%, 17% | Not rerun; Vandalia Leader 4% / 26% | Model replaced |
| Spillover | Weekly alone in its county | −0.16 (p 0.28), −0.14, −0.18; nested 7.41 vs 7.36 | Not rerun | Crowded weekly not adopted |
| Spillover | Market position | p = 0.35 / 0.82 / 0.24; mean 9.3 against 8.6 | p 0.31–0.70; mean 6.03–6.07 against 5.90 (border form) | Current data |
| Spillover | Crowded-county weeklies' median | 11% against 24% for other weeklies | Not rerun | Model replaced |
| Spillover | Fits on all 128 outlets; mention weight under town population | 11.5 / 11.1 / 11.2; Boone County Journal 2–21% … Mexico Ledger 14–57% | Not rerun | Model replaced |
| Spillover | Mid Rivers Newsmagazine, Greene County Commonwealth | Left out of the fit | Fitted with the covered county as home | HOME_COUNTY |
| Spillover | Quality selection | Not stated | 24.5% vs 17.5% (r +0.26, p 0.003) | Reported every run |
| Spillover | All marginal factors | 14.5; 14.9; 14.2 with ridge 0.05; 14.5 with ridge 0.2; "ridge 0.05 is 0.3 points better" | 6.43; 7.00 / 7.66; every combination worse | Current measure and model |
| Spillover | Crossover–spillover correlation | 68 counties r = 0.10 (p = 0.43), urban share fixed 0.08; well collected 44 counties r = 0.30 (p = 0.05) (53 counties, p 0.02 on 2026-10-17 data) | All 72 counties +0.11 (0.36), weighted −0.01; well collected 53 counties +0.35 (0.010), weighted +0.15 (0.27) | Current data; weighted form added |
| Spillover | Collection quality | Urban share −1.09; 15.0 → 14.1; 28 counties, 36 outlets | 7.5 / 6.6 / 8.9; 33 counties, 40 outlets | Current model; `EXCLUDE` in the newsroom count |
| Spillover | County characteristics column | 15.6 baseline; 15.0; 14.1 | Not rerun; not comparable with 5.98 | Earlier measure and model |
| Spillover | Springfield comparison | Spillover 41% / 40% (print 26% / 25%); medians 44% / 43%; Webster 68% / 46% | Region held out 24% / 26%; Webster 36% / 23% | Earlier measure |
| Public | Public, best setting per class, all | 4.34 (4.30 reviewer rerun); classes 3.99 / 4.06 / 5.56 / 5.48 / 5.08 | 4.85 nested (4.67 in-sample); 4.38 / 4.78 / 6.96 / 5.47 / 5.25 | Nested selection; adopted outcome; common set |
| Public | Public reference (start of 2026-10-18) | 5.22 / 4.78 / 6.05 / 6.72; 5.35 | Not rerun | Superseded by per-class settings |
| Public | + segment corrections (transferable) | 3.73 (classes 3.43 / 3.52 / 3.93 / 6.40 / 3.48); refined 3.63 (regional-hub rings 5.62) | 3.97 outer loop (3.53 / 3.97 / 4.05 / 6.12 / 4.54); 3.71 in-sample structure | Outer loop |
| Public | + destination factor from public measures | 3.76 (3.50 / 3.51 / 3.86 / 6.67 / 3.30) | 3.95 (3.58 / 3.99 / 3.88 / 5.65 / 4.52) | Outer loop |
| Public | + one factor per destination county | 3.40 (2.94 / 3.07 / 4.44 / 6.33 / 3.52) | 3.47 (3.10 / 3.52 / 4.31 / 5.91 / 2.35) | Outer loop |
| Public | Advan-fitted, Missouri | 3.13 (3.28 / 2.79 / 4.38 / 3.26 / 2.11) | 3.34 (3.51 / 2.95 / 4.36 / 3.41 / 2.61) | Adopted outcome (pass-through discounted); common set |
| Public | "Beats the Advan-fitted model in major-metro rings (3.93 vs 4.38)" | Claim | Deleted: 4.05 vs 4.36, −0.31 [−2.72, +2.29], no difference | Never a claim of the study; intervals |
| Public | "With destination factors, beats it in small rural counties (2.94 vs 3.28)" | Claim | Deleted: 3.10 vs 3.51, −0.41 [−0.93, +0.10], no difference | Never a claim of the study; intervals |
| Public | Gap decomposition 46% / 21% / 12% / 68% | 5.35 reference, in-sample | Not rerun | `public_gap_corrections.py` unchanged; read as in-sample |
| Public | Kansas public, all | 3.74 (classes 3.80 / 3.83 / 4.42 / 3.01 / 2.62) | 4.29 (4.10 / 4.59 / — / — / 2.94) | Common destination set (9.1% of Advan share had been scored against zero); Missouri setting choice |
| Public | Kansas + Missouri corrections | 3.98 (3.64 / 3.83 / 8.82 / 4.16 / 4.61) | 4.27 (3.83 / 4.16 / — / — / 4.95) | Common set; structure chosen out of sample for Kansas |
| Public | Kansas Advan-fitted | 3.05 (4.12 / 2.74 / 2.84 / 3.09 / 1.55) | 3.27 (4.15 / 3.06 / — / — / 1.78) | Common set |
| Public | Kansas: public "better than the benchmark for small rural counties" (3.80 vs 4.12) | Claim | Deleted: 4.10 vs 4.15, −0.06 [−1.10, +0.90], no difference | Never a claim of the study; intervals |
| Public | Kansas gap to the benchmark | 0.69 (Missouri 1.21) | +1.03 [+0.53, +1.52] (Missouri +1.50 [+1.02, +2.01]) | All of the above |
| Public | Kansas class cells "Commuter, KC metro (3)", "Wichita ring (1)" | 2.84–8.82 | County by county (Butler, Leavenworth, Miami, Wyandotte) | n < 5 |
| Public | Kansas counties under the corrections | Cowley 10.19 → 5.41, Harper 8.77 → 5.34, Kearny 7.57 → 3.72, Barber 4.70 → 2.29, Greenwood 3.84 → 1.69; Johnson 4.32 → 10.06, Douglas 1.70 → 9.62, Doniphan 1.32 → 7.45 | Harper 11.50 → 3.23, Cowley 11.74 → 5.87, Barber 5.99 → 2.70, Lane 7.08 → 4.55; Johnson 4.18 → 10.77, Douglas 2.25 → 10.21, Doniphan 1.59 → 6.52 | Common set; structure chosen out of sample |
| Public | Corrections applied to Kansas small rural counties only | About 3.69 | Not rerun | — |
| Public | Kansas county classes | 2020 Census population | ACS 2020–2024 B01003; no county moved | One population source in both states |
| Areas | Number of patterns K | K = 6 in every market, chosen on held-out months (10 random splits: 2.87 points at K = 1, 2.30 at K = 6, 2.42 at K = 8); "held-out months chose six patterns in every market" | K rule (option A): 3 Columbia, 7 Springfield, 3 Cape Girardeau, 3 Kirksville, 4 Joplin, 3 Kansas City, 3 St. Joseph | Splits drawn inside the K loop, so each K was scored on different months; held-out error now a persistence diagnostic |
| Areas | K rules superseded the same day | Paired one-SE rule on held-out months (K = 5-18; Columbia 11, three areas); population and volume per market (K = 2-5; Columbia 2) | Option A (per town) | One-SE kept adding patterns to the top of the grid; a market share depends on which home counties form the market |
| Areas | Columbia's areas | Two: Columbia I and II (primary 42% on 2026-10-17, then 72% / 16%; 76,912 / 17,513 residents) | One: "Columbia's civic interest area", 91%, ~97,020 | K rule |
| Areas | Mexico, Linn share of residents | Mexico 79%, then 74% (5,241); Linn 93%, then 92% (1,641) | Mexico 92% (~6,530); Linn 71% (~1,270) | K rule |
| Areas | Estimated town residents | Columbia ~107,000; Mexico ~7,100; Linn ~1,800 | ~106,900; ~7,130; ~1,790 | Refit; calibration as before |
| Areas | Published area (outline) | Columbia I 1,158 km², II 4,165; Mexico 1,930; Linn 1,264 | Columbia 1,363; Mexico 1,691; Linn 1,176 | K rule |
| Areas | Mexico's Boone hexagons | 99 | 95 | K rule |
| Areas | Market test | Mexico-Boone 893 crossing; Columbia-Cole 2,682 (11.6% / 16.3%); Linn-Cole 522 | Mexico-Boone 1,037; Columbia Boone-centred; Linn-Cole 319 | K rule |
| Areas | Areas per town | 63 areas; "hubs split (Columbia 42/36/12, Springfield 31/30/18, St. Joseph 26/22/20); isolated towns have one (Linn 93, Belle 95, Cassville 92, Sikeston 78, Neosho 79)" | 57 areas; Areas per town table (left of each arrow = K = 6) | K rule |
| Areas | Local index reach, Linn | Rural Osage 0.15 against the pattern's 0.31; Maries 0.02 against 0.11 | Not rerun | K = 6 pattern |
| Areas | Network tie values | Columbia's strongest ties (shared places / shared coverage) Ashland 0.38 / 0.61, Jefferson City 0.19 / 0.34, Mexico 0.16 / 0.26; weight sensitivity rank correlation 0.988-1.000, at most 25 of 608 hexagons change band; gate: Linn-Columbia shared places 0.32 (0.05 out, 0.02 in), kept Linn-Jefferson City 0.26, Mexico-Columbia 0.12, Columbia-Mexico 0.22; statewide shared coverage 244 of 267 lifted hexagons | Not rerun | K = 6 areas |
| Areas | Display selectivity floors | Columbia primary 15.9 (239 hexagons), secondary 15.0 (398) | Not rerun; hexagons beyond home: Columbia 108, Mexico 123, Linn 122 | K = 6 areas |
| Areas | Minimum size evidence | 75 markets; Spearman 0.37; median 0.84 under 500, 0.85 at 500-1,000, 0.89 at 1,000-2,000, 0.93 at 2,000-5,000, 0.95 above; Mexico's secondary (729 residents) 389 hexagons, 72% holding; dropped Mexico 2, Vandalia 2, Hallsville 2, Lancaster 2, Lexington 2, Savannah 3, Centralia 3, Macon 2; 63 remain; Harrisonville 1 0.44, Grain Valley 1 0.53; stability threshold would drop Lee's Summit 2 (36,956) | 57 areas; median 0.93; 0.83 / 0.855 / 0.91 / 0.94 by size; Spearman 0.31; Harrisonville 0.35, Grain Valley 0.61; Lee's Summit 2 54,511 | K rule; home hexagons excluded |
| Areas | Selection-rule sensitivity ("split-half agreement") | Home hexagons included, K = 6: adopted 0.896 / 0.880 / 0.941 / 0.734 (Columbia I, II, Mexico, Linn), mean 0.863, "the highest mean agreement; no variant beats them by more than 0.011"; area sensitivity Columbia I 0.77-1.0, Mexico 0.44 (40%) / 0.50 (3x) | Replicability, home excluded: adopted 0.76 / 0.75 / 0.58, mean 0.70; within 0.03 of the best mean (no distance rule 0.73); IoU Columbia 0.53-1.0, Mexico 0.52-1.0, Linn 0.45-1.0 | Home inflated the overlap; K rule; "agreement" renamed replicability (not validity) |
| Areas | Coverage density, first table | Columbia II place-specific 24 / 5 / 26 / 45%, with county-level stories 83 / 17 / 0 / 0% | Current table (Columbia, Mexico, Linn) | Columbia II no longer exists; attribution rule |
| Areas | Coverage density, square root for all regions | Columbia I 58 / 38 / 4 / 0, II 25 / 25 / 50 / 0, Mexico 32 / 15 / 53 / 0, Linn 25 / 54 / 21 / 0 (alpha 1: 53 / 4 / 43, 23 / 4 / 73, 30 / 3 / 67, 22 / 5 / 73); newsrooms for 80% (weekly / daily) 3 / 2, 6 / 5, 5 / 2, 2 / 3 | Columbia 44 / 8 / 48 / 0 (2 / 1); Mexico 32 / 4 / 64 / 0 (2 / 3); Linn 21 / 8 / 71 / 0 (2 / 2) | Revised the same day (counties once); K rule |
| Areas | Coverage density, revised rule | Columbia I 53 / 4 / 43 / 0, 1 / 1 (221 hexagons; rerun before the refit 51 / 6 / 43 / 0); II 23 / 4 / 73 / 0, 2 / 6 (733); Mexico 30 / 3 / 67 / 0, 2 / 2 (347); Linn 22 / 5 / 73 / 0, 2 / 2 (236) | As above (259, 311, 219 hexagons) | K rule |
| Areas | Balanced diet | Columbia I 51%, 5.0, 3 outlets; II 10%, 1.5, 4; Mexico 14%, 2.2, 3; Linn 14%, 1.7, 2 | Columbia 44%, 4.4, 3; Mexico 15%, 2.4, 3; Linn 16%, 1.8, 2 | K rule |
| Tie markets | Accuracy by market (2026-10-18) | Kansas City 1.00 / 0.92, St. Joseph 0.96 / 0.84, Joplin 0.94 / 0.84, Springfield 0.90 / 0.80, Columbia 0.85 / 0.67, Kirksville 0.87 / 0.53, Cape Girardeau 0.86 / 0.36 (replicability / accuracy); all 0.91 / 0.70 (travel alone 0.67); same number of markets 53%, within one 97% | 0.98 / 0.93, 0.88 / 0.62, 0.97 / 0.77, 0.935 / 0.575, 0.81 / 0.615 (travel alone 0.49), 0.74 / 0.59, 0.80 / 0.36; all 0.88 / 0.61; market counts not reported | Scoring change: home county in every market, scored beyond it; town's own units masked |
| Tie markets | Population in the within-county spread | Cape Girardeau 0.36 -> 0.49, Kirksville 0.53 -> 0.62, Columbia 0.67 -> 0.69, Springfield 0.80 -> 0.74; all 0.70 / 0.687 -> 0.70 / 0.707; density thresholds 0.72 / 0.703, 0.71 / 0.706; nonmetro-only rule 0.697 | Adopted setting in the current run (Cape Girardeau 0.36); alternatives not rerun | Old scoring |
| Tie markets | Columbia's eight towns, steps | 0.655 -> 0.665 -> 0.67 | Not rerun (Columbia market 0.615) | Old scoring |
| Tie markets | Vandalia; Mexico with LODES within 45 miles | 0.44 -> 0.57; 0.65 | Vandalia 0.55; Mexico 0.41 | Old scoring |
| Tie markets | Within-county spread (footprint overlap) | Jobs 0.49, OSM 0.50, half each 0.53; exponent 1: 0.59, 3: 0.37 | Not rerun | Old scoring |
| Tie markets | Columbia, Mexico, Linn (town accuracy) | 0.69, 0.46, 0.68 | 0.13, 0.41, 0.82 | Old scoring: Columbia's 0.69 came from unmasked home units |
