# Results: where each figure in the article comes from

Every number, table and figure the article reports, with the `scripts/reproduce.sh` step that prints or draws it. Each
step writes its log to `logs/reproduce/<step>.log`; figures are written to `flows/print/`.

## Methods

| Result in the article | Value | Step | Script |
|---|---|---|---|
| Share-of-travel error, public-data model against the Advan-fitted model (counties held out) | 4.6 / 3.3 points | `public_model` (step 4) / `travel_model` | `analysis/public_stage1_nested.py` / `analysis/travel_model.py` |
| Spillover weights (Table 1): centred 1, mention 0.5, sports half | definitions | — | `analysis/spillover_common.py` |
| Newsroom comparisons: well-collected outlets (95% body text, 80% full length, 60% and 20+ geolocated) | 85 outlets, 48 counties | `spillover_outlets` | `analysis/spillover_outlets.py` |
| Rural county: under half of its 2020 population in Census urban areas | Audrain, Osage rural; Boone urban | `coverage_model` | `analysis/gravity_terms.py`, `analysis/coverage_model.py` |
| Factors tested and not adopted ("more than a hundred factors") | none improves held-out error | stage `factors` | `analysis/factor_search/` (its README lists each test) |
| Broadcasters cover other counties more; more print outlets in the county, less | outlet model terms | `spillover_outlets` | `analysis/spillover_outlets.py` |
| Rural newsrooms' coverage follows travel less | coverage model term | `coverage_model` | `analysis/coverage_model.py` |
| Road stops (gas stations, convenience stores, fast food) at half weight | Weekly Patterns Plus, March 2026 | `stop_weights` | `flows/build_stop_weights.py` |
| Travel patterns: non-negative matrix factorization; patterns of 10%+ and 1,000+ residents and 10%+ of travel, stable across starts and alternate months | one area per town | `patterns_columbia`, `market_columbia` | `flows/travel_patterns.py`, `flows/market_patterns.py` |
| News ties (home outlets report on a place, its outlets on the home town, shared third places) | network tie | `confidence_columbia`, `ensemble_columbia` | `analysis/network_tie.py` |
| Versions of the map | 6,912 | `ensemble_columbia` | `flows/area_ensemble.py` |
| Regular-travel distance (90% of trips to places visited every month, January–July 2026) | 15 / 30 / 44 miles | `regular_distance` | `flows/regular_distance.py` |
| Civic interest area: places in half or more of the versions; disconnected clusters within the regular-travel distance; towns whole | — | `area_core` | `flows/area_core.py` |
| Coverage density tiers (frequent 9+, regular 2–8, infrequent under 2 stories a month); balanced diet (8 of 10 CIN categories) | — | `coverage_density_columbia`, `diet_columbia` | `analysis/area_coverage_alignment.py`, `analysis/cin_diet.py` |

## Findings

| Result in the article | Value | Step | Script |
|---|---|---|---|
| Stories reaching another county, counted in full: Audrain, Osage, Boone, all three | 65 of 123; 20 of 40; 546 of 1,152; 631 of 1,315 | `alignment` | `coverage/build_alignment.py` |
| Spillover, weighted: Audrain, Osage, Boone | 20%, 26%, 29% | `spillover_outlets` | `analysis/spillover_outlets.py` (`analysis/spillover_quoted_rows.csv`) |
| Spillover 95% intervals (Table 2): Audrain, Osage, Boone; Boone print and digital | [16, 23], [17, 35], [27, 31]; 18% [16, 20] | `county_intervals` | `analysis/county_intervals.py` |
| Crossover ÷ spillover ("roughly twice"): Audrain, Osage | 2.3 [1.9, 2.7], 2.3 [1.6, 3.6] | `county_intervals` | `analysis/county_intervals.py` |
| Broadcasters against print and digital outlets | 31% / 22%; term 0.67 (SE 0.15), p < 0.001 | `spillover_population` | `analysis/spillover_population_test.py` |
| Print and digital outlets by outlets in the county: four or more, one | 16% / about a quarter; term −0.39 (SE 0.12), p = 0.003 | `spillover_population` | `analysis/spillover_population_test.py` |
| Boone without KOMU, KMIZ and KBIA | 29% → 18% | `spillover_outlets` | `analysis/spillover_outlets.py` |
| Crossover, residents seen outside the county in a typical month: Osage, Audrain, Boone | 59%, 44%, 26% | `crossover_compare` | `analysis/crossover_compare.py` |
| Crossover against print and digital spillover, 47 counties with fitted outlets | r = 0.33 [0.05, 0.57], p = 0.02 | `spillover_quality`, `county_intervals` | `analysis/collection_quality_robustness.py`, `analysis/county_intervals.py` |
| Stories when travel doubles: urban, rural newsrooms | +38% [26, 52], +18% [9, 28] | `coverage_model` | `analysis/coverage_model.py` |
| Places in both odd-month and even-month areas: Columbia, Mexico, Linn | 86%, 92%, 67% | `area_core` | `flows/area_core.py` (`flows/reach/probability_columbia.json`, `core50_area_month_split`) |
| Places kept when areas are drawn from travel alone | 91–95% | `ensemble_columbia` | `flows/area_ensemble.py` |
| Frequent coverage: Columbia, Mexico, Linn; infrequent, Mexico and Linn | 60%, 44%, 41%; 54% each | `coverage_density_columbia` | `analysis/area_coverage_alignment.py` |
| Balanced diet: Columbia, Linn, Mexico | 56%, 36%, 21% | `diet_columbia` | `analysis/cin_diet.py` |

## Tables

| Table | Step | Script |
|---|---|---|
| Table 1. How a story counts as spillover | — | `analysis/spillover_common.py` |
| Table 2. Population; local outlets; stories analyzed (1,152 / 123 / 40); crossover; spillover | `alignment`, `crossover_compare`, `spillover_outlets` | `coverage/build_alignment.py`, `analysis/crossover_compare.py`, `analysis/spillover_outlets.py`; population: 2020 Census |
| Table 3. Area (432 / 346 / 420 square miles); regular-travel distance; continuous territory | `coverage_density_columbia`, `regular_distance`, `area_core` | `analysis/area_coverage_alignment.py`, `flows/regular_distance.py`, `flows/area_core.py` |
| Table S1. County spillover and held-out skill under alternative weights | `spillover_outlets` | `analysis/spillover_outlets.py` |
| Table S2. Civic interest areas with the constants set by judgment halved or doubled | stage `sensitivity` (`judgment_constants`) | `flows/area_ensemble.py` (`TIE_W`, `GAMMA`), `analysis/judgment_constants.py` |

## Figures

Figure 1, the locator map of the Columbia–Jefferson City DMA, reports no result and is not built here.

| Figure | Step | Page | Output (`flows/print/`) |
|---|---|---|---|
| Figure 2. From data to measures | `figures` | `flows/measures_flow_print.html` | `measures_flow.png`, `.pdf` |
| Figure 3. Civic interest areas | `area_core`, `figures` | `flows/market_pattern_print.html` | `civic_area_triptych.png` |
| Figure 4. Coverage density and balance | `coverage_density_columbia`, `diet_columbia`, `figures` | `flows/market_pattern_print.html?measure=coverage` | `civic_coverage_triptych.png` |

## Supplementary material S2: calculations

The fitted values S2 lists for each measure, and the step that prints them.

| Measure | Values | Step | Script |
|---|---|---|---|
| A. Travel | β₁–β₈, held-out R² and share-weighted error; elasticity at 25 miles (−0.88 / −0.70); 25 to 50 miles keeps 48% / 49% of visits | `travel_model` | `analysis/travel_model.py` |
| B. Crossover | b = 0.62 [0.53, 0.71], first-stage F; county shares and their range over the interval of b | `build_unique_od`, `crossover_compare` | `analysis/build_unique_od.py`, `analysis/crossover_compare.py` |
| C. Coverage | β₁–β₃ and β₁ + β₂, twice the visits with 95% intervals, held-out error with and without the rural term (4.54 / 4.67) | `coverage_model` | `analysis/coverage_model.py` |
| D. Spillover | β₀–β₂ with p; held-out error 5.98 against 7.49, skill 0.20 (also Table S1) | `spillover_outlets` | `analysis/spillover_outlets.py` |
| D. Spillover | county spillover with 95% intervals; crossover ÷ spillover | `county_intervals` | `analysis/county_intervals.py` |
| D. Spillover | held-out error with the choice of terms repeated in each fold (6.57) | `spillover_nested` | `analysis/factor_search/spillover_nested_selection.py` |
| E. Civic interest area | K, versions, regular-travel distance | `patterns_columbia`, `ensemble_columbia`, `regular_distance` | `flows/travel_patterns.py`, `flows/area_ensemble.py`, `flows/regular_distance.py` |
| E. Civic interest area | Sensitivity: 94–100% of places kept, frequent coverage within 3 points (Table S2) | `judgment_constants` | `analysis/judgment_constants.py` |

## Supplementary material S3

| Result | Value | Step | Script |
|---|---|---|---|
| Frequent coverage before whole towns are added: Columbia, Mexico, Linn | 54%, 38%, 34% | `coverage_density_columbia` | `analysis/area_coverage_alignment.py` (last lines of its log) |
| The same, areas drawn from travel alone | 51%, 35%, 35% | `coverage_density_columbia` | `analysis/area_coverage_alignment.py` (last lines of its log) |
