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
| Broadcasters against print and digital outlets | 31% / 22% | `spillover_population` | `analysis/spillover_population_test.py` |
| Print and digital outlets by outlets in the county: four or more, one | 16% / about a quarter | `spillover_population` | `analysis/spillover_population_test.py` |
| Boone without KOMU, KMIZ and KBIA | 29% → 18% | `spillover_outlets` | `analysis/spillover_outlets.py` |
| Crossover, residents seen outside the county in a typical month: Osage, Audrain, Boone | 59%, 44%, 26% | `crossover_compare` | `analysis/crossover_compare.py` |
| Crossover against print and digital spillover, 47 counties with fitted outlets | r = 0.33, p = 0.02 | `spillover_quality` | `analysis/collection_quality_robustness.py` |
| Stories when travel doubles: urban, rural newsrooms | +38%, +18% | `coverage_model` | `analysis/coverage_model.py` |
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

## Figures

Figure 1, the locator map of the Columbia–Jefferson City DMA, reports no result and is not built here.

| Figure | Step | Page | Output (`flows/print/`) |
|---|---|---|---|
| Figure 2. From data to measures | `figures` | `flows/measures_flow_print.html` | `measures_flow.png`, `.pdf` |
| Figure 3. Civic interest areas | `area_core`, `figures` | `flows/market_pattern_print.html` | `civic_area_triptych.png` |
| Figure 4. Coverage density and balance | `coverage_density_columbia`, `diet_columbia`, `figures` | `flows/market_pattern_print.html?measure=coverage` | `civic_coverage_triptych.png` |
| Figure S1. How the measures are calculated (fitted values from `travel_model`, `coverage_model`, `spillover_outlets`, `crossover_compare`) | `figures` | `flows/model_diagram_print.html` | `model_diagram.png`, `.pdf` |

## Supplementary material S3

| Result | Value | Step | Script |
|---|---|---|---|
| Frequent coverage before whole towns are added: Columbia, Mexico, Linn | 54%, 38%, 34% | `coverage_density_columbia` | `analysis/area_coverage_alignment.py` (last lines of its log) |
| The same, areas drawn from travel alone | 51%, 35%, 35% | `coverage_density_columbia` | `analysis/area_coverage_alignment.py` (last lines of its log) |
