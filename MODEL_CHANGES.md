# Model changes — travel, coverage and spillover

Log of the modelling decisions from 2026-10-16: what was adopted, what was tested and rejected, and the evidence for
each. Three internal audit rounds by the authors (2026-10-24 and 10-25) restate every model's figures: current
figures are under **Current results**, replaced ones under **Superseded figures** (end). The log reports the target
counties, Audrain, Boone and Osage (and the Columbia–Jefferson City television market for the civic interest areas),
and model-level statistics; figures for other counties and markets are kept outside the repository. Scripts are in `analysis/` unless noted; `make_visuals.sh` rebuilds
every figure from the adopted models.

## Data and periods

| Item | Setting |
|---|---|
| Travel | Advan Neighborhood Patterns Plus (Dewey), Missouri destinations, January–September 2026; summed to home county × destination county (`build_calibration.py`, then `build_statewide_od.py` → `od_mo_2026.csv`; nothing rewrites the file afterwards). Columns: `visits` (÷ county factor, 2026-10-16), `visits_recorded`, `visits_statewide` (÷ statewide units per resident; the adopted scale), `visits_trimmed` (÷ county factor without phantom home block groups); work-hours columns alike. Outcome in every travel script: `gravity_terms.travel_visits` (`visits_statewide` × (1 − shrunken highway-stop discount)) |
| Travel, capped destinations | Advan keeps at most 2,000 home block groups per destination row. Capped destination block groups: 275–904 per month (5.5–18% of rows), holding 19.5% (January) to 43.3% (July) of Missouri out-of-county device-visits. Flag: `dest_bg_capped_mo_2026.csv`; pairs counted in uncapped destinations only: `od_mo_2026_uncapped.csv` |
| Travel, distinct people | `od_people_mo_2026.csv` (`build_unique_od.py`): per home county × destination county × month, the independent city and its county one unit, Missouri and Kansas destinations: people from each home block group in the destination's busiest block group, capped at the block group's calibrated denominator D and converted to people by its ACS population ÷ D, summed (`people_lower`; sensitivity columns `people_lower_recorded`, `people_lower_b1`, `people_lower_calibrated`) |
| Travel, Kansas destinations | Advan Neighborhood Patterns Plus, Kansas destination block groups, January–September 2026 (`neighborhood/raw_ks/`): Missouri residents' visits to Kansas, used in crossover and in the Kansas share of travel |
| Destinations not observed | Illinois, Iowa, Arkansas, Oklahoma and Nebraska block groups are not in the data. A Missouri resident seen only there is not counted as leaving; border counties' crossover is low by that much |
| Tracts | Tract outputs use January–July only (2020 block groups), as `activity_space.py` does: August–September home codes are 2010 block groups, whose tract codes name different areas (`build_tract_od.py` → `od_tract_mo_2026.csv`) |
| Population | ACS 2020–2024 B01003: counties (`free/mo_county_population.csv`), block groups (`census_dl/acs_tract/b01003.dat` → `bg_acs_population.csv`; 2010 block groups by area-weighted overlay of the 2020 block groups, Missouri total preserved to 1 person in 6.19 million) |
| Commuting | LODES 2023, primary jobs (JT01). Missouri residents' jobs anywhere observed: `free/mo_residents_od_JT01_2023.csv.gz` = the Missouri main JT01 file + the Missouri-home rows of the KS, IL, IA, AR, OK, NE, TN and KY aux JT01 files (built by `crossover_compare.py`), read by the travel and coverage terms (`gravity_terms.py`), the public model and the crossover scripts. `free/od_2023.csv.gz` is JT00 (all jobs; byte-identical to LEHD's `mo_od_main_JT00_2023.csv.gz`), read by `build_county_covariates.py` |
| Coverage | Missouri School of Journalism analysis of local news stories, March 2026 (the only month enriched); a story is placed in every county it is centred in or mentions |
| Store-level visits | Advan Weekly Patterns Plus, Missouri, weeks of 2026-03-02 to 03-23. Places keyed by `PERSISTENT_ID_STORE`; `PERSISTENT_ID` is shared by unrelated places (2,225 values for 100,596 places in a week). NAICS codes are the 2017 vintage (gas 447110 / 447190, convenience 445120; 4571xx and 445131 do not occur) |
| Highways | OpenStreetMap `osm/missouri-latest.osm.pbf`: ways of any highway class (proposed, construction, abandoned excluded) whose ref is an Interstate or US route number; business routes, loops and spurs excluded (11,070 ways). TIGER primary roads are not on disk |
| Boundaries | Advan reports 2020 block groups for Jan–Jul and 2010 block groups for Aug–Sep; county codes are the same, and the township maps use one area crosswalk per vintage |
| Smallest count | Every Advan count is a whole number of panel devices × one monthly scale; the smallest value (one panel device) is 14–20 in 2026. It is not a privacy floor |

## Current results (2026-10-25)

The figures a paper quotes, each with the script that prints it. Body sections state the same values; a different
value elsewhere is marked superseded and listed under Superseded figures. Intervals are 95%, county-paired bootstrap
unless stated. **Gain** (one convention in every model) = held-out error without the term(s) or addition − with it,
points; positive: it lowers error. Tables of rejected candidates report **change** = with − without, the negative of
the gain.

**Selection procedure (authors, 2026-10-24), one procedure for every model:**

1. Core terms by theory, tested as blocks (distance, border, commuting), never one term at a time; kept by theory.
2. Hypothesis terms stated in advance and reported whatever the result: spillover, broadcaster and print and digital
   outlets in the county; coverage, the urban / rural split (log visits × rural newsroom county). Travel has none.
3. Exploratory additions only through the nested guard: the search repeated inside each training set and scored on
   the held-out counties; adopted only if the nested gain has an interval excluding zero. None passes in any model.
4. One declared primary metric per model: travel, share-weighted error over all Missouri destinations; coverage,
   destinations with 1%+ of the newsroom county's visits; spillover, mean held-out error on the fitted outlets (the
   honest error is the nested figure of the search that found the terms, search B, 6.57); public model,
   share-weighted error over all Advan destinations, the common destination set beside it.

Disclosure: these rules were set during an internal audit on 2026-10-24, after earlier results had been seen. The
earlier specifications and their figures are in Superseded figures.

**Data and crossover:**

| Measure | Value | Script |
|---|---|---|
| Device → person scale | statewide units per resident by month, 1.70–2.32 (`factor_statewide`); the county factor (county medians 0.24–10.78) is not used | `build_calibration.py` |
| Detection slope b (2SLS: detection instrumented by another month's) | 0.621 [0.534, 0.708] (reduced form 0.510, first stage 0.822; county-clustered first-stage F 4,082, 1,391–9,131 by lag; just-identified) | `build_unique_od.py` |
| Advan coverage by block-group composition (detection ratio): ×1.08 per +10 points aged 65+, ×1.28 per doubling of median income, ×0.87 per +10 points below poverty, ×0.87 per doubling of density; R² 0.21 (device rate 0.19) | 5,014 block groups, 114 county clusters | `advan_representativeness.py` |
| Crossover: distinct residents seen outside the county, calibrated denominator (b = 0.62): Audrain / Boone / Osage | 44% / 26% / 59% | `crossover_compare.py` |
| — bounds: range of the county figure over b in [0, 1] | 40–44%, 24–26%, 45–66% | `crossover_compare.py` |
| — range over b's 95% interval | 43–44%, 26–26%, 57–61% | `crossover_compare.py` |
| Pass-through (highway-stop) discount, empirical-Bayes shrunken excess | removes 1.81% of out-of-county visits (`visits_statewide`-weighted); signed mean excess −0.02% (+0.43% unshrunk) | `travel_model.py` (removed share); `build_road_stop_share.py` (excess) |
| Device IDs | stability across weeks not established (claim withdrawn) | `device_id_test.py` |

Homebody caveat: b mixes phantom phones homed in a block group and residents who stay home more (seen at home more,
out less); the second biases b upward as a phantom share, the opposite direction to the attenuation the instrument
removes.

**Travel** — doubly-constrained gravity, PPML; home and destination fixed effects + 8 core pair terms in three blocks
(`gravity_terms.FACTORS`); rural home county = under 50% of its 2020 population in Census urban areas (Rural flag,
below):

| Measure | Value | Script |
|---|---|---|
| Held-out share-weighted error, all Missouri destinations (primary) | 3.28 [2.96, 3.59] | `travel_model.py` |
| — small rural (56) / independent towns (32) / commuter (18) / hubs (9) | 3.41 / 2.84 / 4.28 / 2.06 | `travel_model.py` |
| Held-out R² of shares | 93.7% [92.4, 94.8] (fixed effects only: error 16.04, R² 0.9%) | `travel_model.py` |
| Big flows (forecast 5%+, 485 pairs): error; within 0.8–1.25× | 3.44 [3.19, 3.71]; 49% [45, 53] | `travel_model.py` |
| Top forecast destination, actual ÷ forecast | 1.00× (middle half 0.86–1.19) | `travel_model.py` |
| Block gains: distance / border / commuting | +1.047 [+0.653, +1.433] / +0.125 [−0.105, +0.347] / +0.457 [+0.245, +0.676] | `travel_model_dc_test.py selection` |
| Nested guard, 24 exploratory candidates | gain +0.106 [−0.045, +0.263]: none adopted | `combined_marginal_test.py travel_nested_all` |
| Distance elasticity at 25 mi, mean-size home county: urban / rural | −0.88 (s.e. 0.13) / −0.70 (0.15) | `travel_model.py` |
| Rural × log distance / rural × log distance² | +0.177 (s.e. 0.120, p = 0.14) / −0.210 (0.054, p < 0.001); the first is not distinguishable from zero alone and is tested only within the distance block | `travel_model.py` |
| Commuting out / in | +0.277 (s.e. 0.045) / +0.189 (0.036) | `travel_model.py` |
| Stability, Jul–Sep from Jan–Jun: model / persistence error | 2.96 / 1.46 | `travel_model.py` |
| Moran's I of held-out error by home county / signed residual by destination (115 counties, 999 permutations) | +0.007 (p 0.763) / +0.139 (p 0.014: under-predicted destinations cluster) | `residual_autocorrelation.py` |
| Distance form: restricted cubic spline, change in held-out error (knots at pair / visit-weighted quantiles) | +0.150 [−0.084, +0.392] / −0.012 [−0.129, +0.123]: quadratic kept | `travel_distance_spline.py` |

The border block's held-out gain interval includes zero; it is kept as a core term by theory (coefficient +0.440
[+0.309, +0.572], `travel_model_dc_test.py selection`).

**Coverage** — PPML of March story-county pairs; core gravity blocks, newsroom-county and covered-county fixed
effects, log visits (where > 0), zero-visit indicator; hypothesis term log visits × rural newsroom county (under 50%
of 2020 population in Census urban areas); errors clustered by newsroom county:

| Measure | All outlets | Print and digital | Script |
|---|---|---|---|
| Stories / newsroom counties / out-of-county story-county pairs | 14,877 / 88 / 10,282 | 8,301 / 88 / 6,674 | `coverage_model.py` |
| Elasticity of stories to visits, urban newsroom counties (23) | 0.47 (s.e. 0.069; 0.33–0.60) | 0.48 (0.086; 0.31–0.64) | `coverage_model.py` |
| Elasticity, rural newsroom counties (65) | 0.24 (s.e. 0.059; 0.13–0.36) | 0.26 (0.058; 0.14–0.37) | `coverage_model.py` |
| Hypothesis term, rural − urban | −0.225 (s.e. 0.047, p < 0.001) | −0.220 (0.067, p < 0.001) | `coverage_model.py` |
| Hypothesis term, gain on the primary metric | +0.128 [+0.045, +0.213] | +0.081 [+0.004, +0.161] | `coverage_model.py` |
| Twice the visits, urban / rural | 1.38× / 1.18× the stories | 1.39× / 1.19× | `coverage_model.py` |
| Commuting in / out | +0.42 (s.e. 0.069) / −0.02 (0.087, n.s.) | +0.36 (0.064) / −0.03 (0.084, n.s.) | `coverage_model.py` |
| Distance block, gain on the primary metric (kept by theory) | −0.125 [−0.255, −0.001] | −0.188 [−0.381, −0.010] | `coverage_model.py` |
| Held-out error, destinations with 1%+ of visits (primary; per-county mean, 8 folds) | 4.54 [4.09, 5.04] | 4.63 [4.18, 5.12] | `coverage_model.py` |
| Held-out error, all destinations (beside) | 0.922 [0.852, 0.988] | 0.947 [0.881, 1.009] | `coverage_model.py` |
| Rurality and newsroom size: × rural beside × outlets, daily and TV; that model against the adopted, held out | −0.166 (s.e. 0.043); change −0.017 [−0.072, +0.039] | — | `coverage_newsroom_size_test.py` |
| Saturation, nested guard | gain +0.001 [−0.016, +0.021]: not supported | −0.001 [−0.030, +0.032] | `coverage_saturation_test.py` |
| Moran's I of in-sample error by newsroom county (88 counties) | −0.044 (p 0.679) | −0.070 (p 0.425; no broadcasters) | `residual_autocorrelation.py` |
| Pooled elasticity, no hypothesis term (sensitivity) | 0.38 (s.e. 0.060) | 0.37 (0.066) | `coverage_model.py` |

The distance block's held-out gain interval lies below zero: leaving it out would lower primary held-out error. It is
kept as a core term by theory (Wald χ² 115.3, df 5, p < 0.001). Rurality is the main explanation of the urban–rural
coverage gap; newsroom size contributes; held-out prediction cannot separate the two (Coverage model, Rurality and
newsroom size).

**Spillover** — outlet-level logistic: spillover ~ broadcaster + log(1 + print and digital outlets in the county),
both hypothesis terms (`spillover_common.FINAL`); mention 0.5 and Sports 0.5 are definitions:

| Measure | Value | Script |
|---|---|---|
| Outlets with 10+ placed stories | 128 in 72 counties (27 broadcasters), 12,192 stories | `spillover_outlets.py` |
| Fitted (well collected, 20+ placed stories, not Three Rivers Publishing) | 85 outlets, 48 counties, 24 broadcasters | `spillover_outlets.py` |
| Broadcaster | +0.667 (CRV3 s.e. 0.148, p < 0.001; bootstrap CI +0.388 to +0.939); gain +1.55 [+0.36, +2.70] | `spillover_outlets.py` |
| Print and digital outlets in the county, log(1 + count) | −0.387 (CRV3 s.e. 0.124, p 0.003; CI −0.655 to −0.232); gain +1.04, interval lower bound −0.05 to +0.01 by bootstrap seed | `spillover_outlets.py` |
| Held-out error, mean / median (primary: mean), honest: nested search B | 6.57 / 5.50 | `spillover_nested_selection.py` |
| — fitted model, not nested | 5.98 / 4.66 (intercept only 7.49 / 6.23); skill +0.202; out-of-sample R² +0.360 | `spillover_outlets.py` |
| Nested guard from the hypothesis pair | 6.05 / 5.05; gain −0.07 [−0.60, +0.38]: none adopted | `spillover_rule_selection.py` |
| Actual / held-out expected: Audrain, Boone, Osage | 19.5 / 22.5%, 28.7 / 26.4%, 25.6 / 25.3% | `spillover_outlets.py` (`spillover_quoted_rows.csv`) |
| Leave one TV market out (7 markets with 3+ outlets) | in sample 5.9, held out 6.2, intercept only 7.4 | `spillover_dma_holdout.py` |
| Mean spillover rate | 24.7% | `spillover_outlets.py` |

**Public-data travel model** — the study's question is how close a model built from public data gets to the
Advan-fitted model, and how much of the gap Advan-learned corrections close. The public model is not claimed to beat
the Advan-fitted model, and does not in any class. Every score out of sample for the county scored:

| Model | Missouri (115): all Advan destinations (primary) | common set | log-ratio |
|---|---:|---:|---:|
| Advan-fitted (counties held out) | 3.28 | 3.36 | 0.34 |
| Public (Stage 1 nested) | 4.60 | 4.70 | 0.58 |
| Public, Stage 1 per outer fold (base of the corrections) | 4.63 | 4.73 | 0.58 |
| + Advan-learned segment corrections (C, transferable; outer loop) | 4.05 | 4.15 | 0.51 |
| + one factor per destination county (A; outer loop) | 3.45 | 3.51 | 0.44 |
| Public − Advan-fitted | +1.32 [+0.84, +1.83] | +1.35 [+0.86, +1.87] | +0.24 [+0.20, +0.28] |
| Corrected (C) − fold base | −0.58 [−0.94, −0.23] | −0.58 [−0.96, −0.20] | −0.08 [−0.09, −0.05] |
| Share of the gap closed by corrections | C 43% [21, 68]; A 88% [60, 118] | C 42% [18, 66] | C 32% [24, 39]; A 60% [51, 70] |
| Advan share outside the common set, per county | 1.34% (max 8.2%) | | |

Scripts: `score_segments.py` (scores, gaps, shares closed), `public_stage1_nested.py`, `public_adjusted_nested.py`,
`public_vs_advan_compare.py`; metrics in `public_scoring.py`.

**Civic interest areas** — Columbia–Jefferson City TV market only (authors' decision, 2026-10-25); areas drawn and
reported for Columbia, Mexico and Linn. Travel patterns by non-negative matrix factorization (`flows/travel_patterns.py`).
The network-tie map is drawn in 6,912 equally weighted versions: the full factorial of seven drawing choices (1,728
combinations) × the news weight ω ∈ {0, ½, 1, 2} (`flows/area_ensemble.py`; a multiverse analysis, Steegen et al.
2016). Each hexagon's **p** is the probability, under equal weighting of the versions, that the place is part of the
area, conditional on the range of the choices; it varies drawing choices, not data (data uncertainty is month-split
stability). The **area** is **multi-part** (authors' decision, 2026-10-25; `flows/area_core.py`): the home body plus
every core piece (p ≥ 0.5) of 3 or more hexagons whose nearest hexagon lies within **D90** of the town's centre of
population; 1–2-hexagon specks keep their shading but are not outlined; non-home parts are labelled by their largest
town. **D90** (`flows/regular_distance.py`) = the distance from the town's centre of population within which 90% of its
residents' regular travel lies; regular = a destination block group seen from the home block group in all 7 months
(January–July). The limit applies to separate parts only, not to the home body (authors' decision, 2026-10-25). No
single version is drawn or exported as a map. **K rule** (authors' decision, 2026-10-24, per town): K = the largest K
at which every pattern holds 10%+ and 1,000+ of the residents and 10%+ of the travel of at least one study town in the
market (the same town for all three), and is stable at matched cosine 0.9+ across random starts and between
independently refitted odd and even months: K = 2 (K = 3 fails on the odd/even months, 0.87). 9 areas in the market's
8 study towns (`analysis/market_stability.py`).

| Measure | Columbia | Mexico | Linn | Script |
|---|---:|---:|---:|---|
| Areas | 1 ("Columbia's civic interest area") | 1 | 1 | `flows/market_patterns.py` |
| Residents allocated to the area's pattern (ACS; share of the town's) | 103,086 (93%) | 5,685 (86%) | 1,172 (85%) | `flows/market_patterns.py` |
| D90 (7 of 7 months), km | 23.9 | 48.1 | 70.5 | `flows/regular_distance.py` |
| **Area (multi-part): km² / people** | **979 / 161,321** | **802 / 123,946** | **896 / 139,001** | `flows/area_core.py` |
| — home body: hexagons, km², people | 168, 979, 161,321 (reaches 32.3 km; 18 hexagons beyond D90) | 109, 634, 15,968 | 134, 785, 56,509 (includes Jefferson City) | `flows/area_core.py` |
| — other parts (hexagons, km², km from the home body, people) | none | **Columbia 20, 117, 33.8, 102,884**; Fulton 3, 17, 10.4, 2,065; Centralia 3, 17, 7.8, 2,925; rural Audrain 3, 17, 5.2, 104 | Columbia 13, 76, 36.4, 82,353; rural Osage 6, 35, 7.8, 140 | `flows/area_core.py` |
| — beyond D90, a distant tie | Jefferson City: 10 hexagons, 59 km², 41.2 km from the centre, 32,125 people | none | none | `flows/area_core.py` |
| — specks left out of the outline (1–2 hexagons) | 5 (6 hexagons) | 4 (5 hexagons) | 9 (10 hexagons) | `flows/area_core.py` |
| All core hexagons (p ≥ 0.5): km² / people | 1,073 / 194,485 | 831 / 124,228 | 955 / 139,992 | `flows/area_ensemble.py` |
| People at p 0.5–0.8 / p ≥ 0.8 | 47,491 / 146,994 | 111,976 / 12,252 | 100,435 / 39,557 | `flows/area_ensemble.py` |
| p ≥ 0.8: km² | 536 | 320 | 346 | `flows/area_ensemble.py` |
| Month-split stability: r(p) all / contested; mean \|p_odd − p_even\|; core Jaccard (home left out; K was selected on the same split) | 0.995 / 0.990; 0.014; 0.86 | 0.978 / 0.955; 0.030; 0.87 | 0.895 / 0.732; 0.056; 0.72 | `flows/area_ensemble.py` |
| Boone hexagons: likely 20%+ / 50%+ / 80%+ | — | 51 / 24 (20 in the Columbia part) / 1 | — | `flows/area_ensemble.py` |
| Towns drawn in 50%+ of versions with no hexagon at p ≥ 0.5, inside the TV market (share of versions drawing the town) | Moberly 0.87, Centralia 0.82, Fulton 0.74, Boonville 0.73 | Moberly 0.73 | Ashland 0.79 | `flows/area_ensemble.py` |
| Network-tie core against the travel-only core (Jaccard) | 0.93 | 0.91 | 0.95 | `flows/area_ensemble.py` |
| Tie-market accuracy, public vs Advan (town) | 0.14 | 0.47 | 0.69 | `analysis/tie_footprint.py` |

All figures from unrounded p. A town counts toward a hexagon's p only where it falls inside a version's area, and
versions draw different hexagons of it, so each hexagon can stay under 0.5 while the town is drawn in most versions.
Jefferson City leaves Columbia's area (nearest hexagon 41.2 km from the centre, beyond 23.9 km) and is reported as a
distant tie; Moberly forms no core part (highest hexagon p 0.44). Columbia stays a part of Mexico's area (40.5 km from
Mexico's centre, against 48.1) and of Linn's (64.0 km, against 70.5).

Why multi-part: Columbia is Mexico's dominant destination (Audrain → Boone 39% of out-of-county visits, 43% of
work-hours visits, 34% of out-commuters, LODES JT01) but lies 33.8 km (nearest hexagons) from Mexico's home body; a
rule keeping only the body would cut it out.

Tie markets, the market's 8 study towns: accuracy median 0.505 (printed 0.51; mean 0.526), month-split stability median
0.79, travel alone 0.52 (`analysis/tie_footprint.py SUMMARY=1`, from the settings each run recorded). Supply (coverage
density, balanced diet) is not a result of this paper: see Supply (QA only; next paper).

### Rural flag: Census settlement replaces RUCC (2026-10-25)

**Adopted (authors' decision, 2026-10-25):** a county is rural when under 50% of its 2020 population lives in Census
urban areas (`analysis/county_urban_share.csv`, `pct_urban` < 0.5, Census "mostly or completely rural"; the
independent city takes its county's value; `gravity_terms.cov.rural`). 89 counties are rural and 26 urban; of the 88 newsroom
counties in the coverage model, 65 are rural and 23 urban. Audrain (45% urban) and Osage (0%) are rural; Boone (77%)
is urban. The flag replaces USDA RUCC nonmetro (codes 4–9) in the travel model's distance terms
(`rural_i_x_log_dist`, `rural_i_x_log_dist_sq`) and in the coverage model's hypothesis term (`log_visits_x_rural`).

Why: RUCC classes a county by commuting to a metro core, not by settlement. Osage was RUCC metro because it is in the
Jefferson City metro area by commuting, and it has no urban population. Of the 89 rural counties, 20 were RUCC metro;
of the 26 urban counties, 11 were RUCC nonmetro (`gravity_terms.py`). Disclosure: the flag was changed after the
RUCC-flag results had been seen; both sets of figures are reported.

| Figure | RUCC flag (audit round 3) | Rural flag (adopted) | Script |
|---|---:|---:|---|
| **Travel coefficients** (two-way s.e.) | | | `travel_model.py` |
| log distance (elasticity at 25 mi, metro / urban home) | −0.983 (0.110) | −0.875 (0.126) | `travel_model.py` |
| log distance² | −0.265 (0.031) | −0.259 (0.032) | `travel_model.py` |
| flag × log distance (nonmetro / rural) | +0.505 (0.115) | +0.177 (0.120; p = 0.14) | `travel_model.py` |
| flag × log distance² | −0.261 (0.069) | −0.210 (0.054) | `travel_model.py` |
| log home population × log distance | +0.181 (0.027) | +0.133 (0.031) | `travel_model.py` |
| shared border | +0.464 (0.066) | +0.440 (0.067) | `travel_model.py` |
| commuting out | +0.284 (0.045) | +0.277 (0.045) | `travel_model.py` |
| commuting in | +0.197 (0.037) | +0.189 (0.036) | `travel_model.py` |
| Elasticity at 25 mi, mean-size home county: metro / nonmetro → urban / rural | −0.98 (0.11) / −0.48 (0.17) | −0.88 (0.13) / −0.70 (0.15) | `travel_model.py` |
| Held-out error (primary) | 3.28 [2.94, 3.61] | 3.28 [2.96, 3.59] | `travel_model.py` |
| Held-out R² of shares | 93.7% [92.4, 94.9] | 93.7% [92.4, 94.8] | `travel_model.py` |
| Block gain: distance | +1.043 [+0.652, +1.426] | +1.047 [+0.653, +1.433] | `travel_model_dc_test.py selection` |
| Block gain: border | +0.199 [−0.033, +0.426] | +0.125 [−0.105, +0.347] | `travel_model_dc_test.py selection` |
| Block gain: commuting | +0.465 [+0.262, +0.706] | +0.457 [+0.245, +0.676] | `travel_model_dc_test.py selection` |
| Nested guard gain, 24 exploratory candidates | +0.062 [−0.097, +0.203] | +0.106 [−0.045, +0.263] | `combined_marginal_test.py travel_nested_all` |
| **Coverage** (all outlets; print and digital) | | | `coverage_model.py` |
| Elasticity, metro → urban newsroom counties | 0.50 (0.067), 27 counties; 0.52 (0.083) | 0.47 (0.069), 23 counties; 0.48 (0.086) | `coverage_model.py` |
| Elasticity, nonmetro → rural newsroom counties | 0.26 (0.061), 61 counties; 0.26 (0.060) | 0.24 (0.059), 65 counties; 0.26 (0.058) | `coverage_model.py` |
| Hypothesis term (log visits × flag) | −0.244 (0.040); −0.262 (0.059) | −0.225 (0.047); −0.220 (0.067) | `coverage_model.py` |
| Hypothesis term, held-out gain (primary) | +0.125 [+0.048, +0.203]; +0.088 [+0.004, +0.170] | +0.128 [+0.045, +0.213]; +0.081 [+0.004, +0.161] | `coverage_model.py` |
| Held-out error, primary | 4.46 [4.02, 4.93]; 4.56 [4.11, 5.02] | 4.54 [4.09, 5.04]; 4.63 [4.18, 5.12] | `coverage_model.py` |
| Held-out error, primary: change, county-paired | — | +0.085 [−0.024, +0.197]; +0.078 [−0.029, +0.198] | `coverage_flag_compare.py` |
| Distance block, held-out gain (primary) | +0.004 [−0.115, +0.125]; −0.082 [−0.243, +0.070] | −0.125 [−0.255, −0.001]; −0.188 [−0.381, −0.010] | `coverage_model.py` |

- Travel: rural × log distance alone is no longer distinguishable from zero (+0.177, s.e. 0.120, p = 0.14). It sits
  in the distance block, which passes as a block (gain +1.047 [+0.653, +1.433]); terms in a block are never tested
  one at a time. Rural × log distance² is clearly non-zero (−0.210, s.e. 0.054).
- Travel: held-out error and R² are unchanged at the stated precision. The urban–rural gap in the 25-mile elasticity
  narrows from 0.50 to 0.18: Osage and the 19 other RUCC-metro rural counties had been in the metro group.
- Coverage: the hypothesis term is little changed (−0.244 → −0.225) and still lowers held-out error by about 0.13
  points (print 0.08), both intervals excluding zero. The adopted model's held-out error is 0.085 points higher
  (4.543 against 4.458), county-paired +0.085 [−0.024, +0.197], 48 counties worse and 40 better; print +0.078
  [−0.029, +0.198] (`coverage_flag_compare.py`). The flag does not measurably change prediction. The 14 newsroom
  counties RUCC metro and settlement rural are predicted better (mean −0.217; Osage 5.77 → 5.06), the others
  slightly worse (+0.142). The distance block's held-out gain is now below zero with an interval
  excluding zero (all outlets and print); it stays by theory.
- Rerun under the rural flag: `travel_model.py`, `travel_model_dc_test.py selection`, `travel_distance_spline.py`,
  `combined_marginal_test.py travel_nested_all`, `coverage_model.py`, `coverage_saturation_test.py`,
  `border_coverage_test.py` (no flag term; unchanged), `coverage_newsroom_size_test.py`; then the travel steps table
  (`travel_model_compare.py`, `travel_model_dc_test.py`), rejected terms (`travel_model_hub_test.py`,
  `travel_model_drive_test.py`, `travel_competing_test.py`, `travel_business_test.py`, `travel_county_class_model.py`,
  `travel_purpose_split_test.py`), main-destination ratios, small counties (`travel_commute_pair_test.py`,
  `travel_small_origin_model.py`, `travel_small_county_test.py`, `travel_tier_pull_cv.py`,
  `travel_distance_variants.py`, `travel_blend_test.py`), residual autocorrelation (`residual_autocorrelation.py`), All
  marginal factors together (`combined_marginal_test.py`, `combined_all_factors_test.py`; the coverage interaction
  switched from RUCC nonmetro to the rural flag), County characteristics (`civic_variables_test.py`, `hospital_test.py`,
  coverage interaction switched likewise) and the public model's Advan-fitted benchmark (`public_vs_advan_compare.py`,
  `score_segments.py`, `public_gap_corrections.py`, `public_default_sensitivity.py`). The County characteristics
  crossover and spillover columns are rerun on the current specifications (crossover baseline with the rural flag in
  place of RUCC nonmetro; the adopted spillover model). The Limitation test's nonmetro indicator is
  RUCC by its own definition. Replaced figures: Superseded figures.
- Conclusions that changed with the flag: without destination effects travel error is higher by +0.42 [−0.01, +0.85],
  an interval now including zero (RUCC +0.51 [+0.09, +0.95]); the public model's gap to the Advan-fitted model now
  excludes zero in small rural counties (+0.70 [+0.04, +1.43]) and includes it in both commuter rings; the
  singly-constrained step's held-out error is 5.84 (RUCC 6.40); Osage → Cole is 1.16 in-sample (RUCC 1.05).

## Measurement corrections

| Change | Why |
|---|---|
| Stories credited to the **Missouri School of Journalism analysis**, never LNIC | Attribution |
| **The Maneater and CoMoBuzz** excluded from Boone's coverage | Decision for these analyses |
| **Statewide outlets are no county's local news** (2026-10-17): Missouri Business Alert (filed under Boone); The Missouri Independent, Missouri Net, Missouri Scout, The Missouri Times (filed under Cole) (`excluded_outlets.EXCLUDE`) | They cover the state, not a county |
| **Campus newspapers are not local news anywhere** (2026-10-24): the 11 student newspapers owned by a college or university (`CAMPUS`, part of `EXCLUDE` in `excluded_outlets.py`) are out of coverage, the spillover outcome and fit, and every county outlet count | Same footing as The Maneater. University-licensed public broadcasters (KBIA, KCUR, KRCU, KSMU, KXCV, STL Public Radio) and the School of Journalism's community newsrooms (Columbia Missourian, Boone County Journal, KOMU) stay |
| **The two outlets filed outside Missouri excluded** (authors' decision, 2026-10-24; `EXCLUDE`, named in `analysis/excluded_outlets.py`): one is mostly Spanish-language, outside the English-language corpus the models describe; the other is an out-of-state broadcast newsroom licensed to a Missouri town | Both were already outside every fit as out-of-state filings |
| **Two outlets homed with the county they cover** (2026-10-24; `excluded_outlets.HOME_COUNTY`, `home_fips`), in coverage, spillover and the area maps, both fitted | Each is published outside the county it covers |
| **Missouri's independent city and its county treated as one unit** for spillover and crossover (crossover: before the left-the-county test, 2026-10-24) | Every outlet of the city is registered in the county, so city stories counted as "another county" |
| **Other-state counties within 60 miles count as spillover** | Border regions cross the state line |
| **One home rule for every outlet** (spillover, 2026-10-24): the county filed under, every other county holding part of its registry city, and, for the one Missouri city with a same-named city across the state line, that city's county | A story about another part of the outlet's own city is not spillover |
| **Home county excluded from every travel–coverage comparison** | Residents live in their home county all of the time; a share of visits says nothing about how much it matters to them. Home and away story counts are reported for reference only |
| **Coverage counts a story's central place as well as the places it mentions** | The story map's county layer omits each story's central place; Osage had 13 placed stories on that layer against 40 with both |
| **Hospital indicator removed** | It was a facility count from a CMS file, not travel data, incomplete (it missed Capital Region Medical Center), and read as a healthcare finding the data cannot support |
| **One travel outcome in every script** (2026-10-24; discount shrunken 2026-10-25): `visits_statewide` × (1 − highway-stop discount) | Several scripts had used undiscounted or uncalibrated visits; the county factor measured home detection |
| **Commuting from LODES primary jobs (JT01), residents' jobs in and out of state** (2026-10-24; out-of-state jobs 2026-10-25) | JT00 counts a worker once per job; Missouri-only denominators left out residents working in Kansas or Illinois |

## Population calibration

Advan Neighborhood Patterns Plus is "normalized against panel size and country population" (Dewey's Advan page): a
national scaling, not a local one. The 2026-10-16 factor — residents seen in their own block group ÷ ACS population —
measures home detection as well as panel size, and is replaced as the device → person scale.

| Factor (`calibration_county_month.csv`) | Definition | County-months: median, middle 80%, range | County medians |
|---|---|---|---|
| `factor` (2026-10-16; kept, not adopted) | seen at home ÷ ACS county population | 1.94; 1.09–3.18; 0.19–12.73 | 0.24–10.78 |
| `factor_trimmed` (sensitivity) | as `factor`, phantom home block groups left out | 1.82; 1.06–2.71; 0.19–6.86 | 0.24–3.85 |
| **`factor_statewide` (adopted)** | Missouri sum over home block groups of the largest count of their residents in any one block group ÷ Missouri ACS population; one value per month | Jan 1.84, Feb 1.90, Mar 2.01, Apr 2.32, May 2.09, Jun 2.04, Jul 1.75, Aug 1.73, Sep 1.70 | one value per month |

- **Phantom home block groups** (`home_bg_month_mo_2026.csv`, `phantom`): residents seen at home above 3× the block
  group's expected residents (ACS population × the month's statewide units per resident). 1,469 of 44,229 block
  group-months (3.3%), holding 10.7% of all devices seen at home; 84 of them have no ACS population. Phantom devices
  are seen at home and rarely elsewhere, so they enlarge any denominator taken from seen-at-home.
- **Under-detection at home:** in some block groups more residents are seen in one other block group than at home.
- **Home block groups with no own key** (residents never reported at home), logged by `build_calibration.py`: Jan 15,
  Feb 11, Mar 14, Apr 9, May 9, Jun 6, Jul 12, Aug 20, Sep 14. Kept with `own` = 0 and `own_key` = 0.
- **Adopted (2026-10-24):** counts ÷ `factor_statewide` (`visits_statewide`; `people_lower` converts at the calibrated
  denominator, see Crossover) and, where a resident count is needed, the ACS population of the block groups. No county
  term is taken from residents seen at home. Within-month shares of a home county are unchanged by any of the three
  factors; pooling months and absolute counts are not.
- **Study towns, estimated residents** (mean over January–July; block groups from `flows/reach/*/homes.csv`):

| Town | Block groups | Seen at home ÷ `factor` (2026-10-16) | ÷ `factor_trimmed` | ÷ `factor_statewide` | ACS population of the block groups |
|---|---:|---:|---:|---:|---:|
| Columbia | 82 | 106,922 | 110,416 | 102,803 | 111,055 |
| Mexico | 7 | 7,126 | 7,242 | 6,742 | 6,619 |
| Linn | 1 | 1,793 | 1,906 | 2,802 | 1,381 |

  Linn's block group is seen at home at 2.0× the statewide rate, so Advan-based counts of single-block-group towns stay
  unreliable under any factor.
- Effect on the travel model: Travel model, Sensitivities (the elasticity moves by less than one standard error).

## Device IDs (not established)

`device_id_test.py`, places keyed by `PERSISTENT_ID_STORE`: for 376 block groups dominated by one business, monthly
distinct devices (Neighborhood Patterns) against that business's weekly visitors summed over March's four weeks
(Weekly Patterns). Monthly was lower in 55 (15%); 48 of them also pass the same-scale check (monthly at least the
busiest single week); in 7 block groups monthly is below the busiest week, so the two products' scales differ.
Automobile dealers 38% below 1, printing plants 29%. The two products are normalized separately, so a lower monthly
count does not show that IDs persist. A within-product test is not possible: no Advan product on disk reports distinct
devices over more than one week for one place. **The claim that IDs are stable week to week is withdrawn.** Daily
resets cannot be tested either.

## Limitation test: Advan coverage by age, income and rurality (2026-10-25)

`advan_representativeness.py` → `advan_representativeness.csv`. Across 5,014 Missouri home block groups (January–July, 2020 block groups; 114 county
clusters), the log2 detection ratio (residents seen at home ÷ expected units, 1 = the statewide rate) and the log2
device rate (residents in the busiest single block group ÷ expected units, which does not depend on home detection)
are regressed on ACS 2020–2024 block-group shares aged 65+ (B01001), log2 median household income (B19013) or the
share below the poverty line (C17002), log2 population density, and a nonmetro-county indicator (RUCC 4–9);
ACS-population weights, county-clustered 95% intervals. B01001 and C17002 come from the Census table-based summary files
(`census_dl/acs_tract/`).

| Term | Detection ratio, × on the ratio [95% interval of the log2 coefficient] | Device rate |
|---|---|---|
| +10 points aged 65+ | 1.08 [+0.035, +0.190] | 1.06 [+0.006, +0.149] |
| ×2 median household income | 1.28 [+0.076, +0.630] | 1.07 [−0.057, +0.252] |
| +10 points below poverty (model with poverty in place of income) | 0.87 [−0.348, −0.055] | 0.94 [−0.157, −0.007] |
| ×2 population density | 0.87 [−0.337, −0.051] | 0.91 [−0.243, −0.036] |
| Nonmetro county | 1.21 [−0.098, +0.655] | 1.07 [−0.179, +0.379] |

R² 0.21 (detection) and 0.19 (device rate). Advan sees residents of sparser, older, better-off block groups at higher
rates, and poorer block groups at lower rates; the density gradient holds for the device rate as well, so it is panel
coverage, not only home detection. Within-county shares are unaffected by a county-wide rate, but block groups of
different kinds within one county are not weighted equally: the crossover and the travel shares lean toward older,
higher-income, lower-density block groups, by up to about a quarter per doubling of income in the detection ratio.

Target counties, population-weighted mean ratios (detection / device rate; block groups) by statewide tercile:

| County | Tercile of | Low | Middle | High |
|---|---|---|---|---|
| Audrain | aged 65+ (cuts 13.8%, 21.5%) | 0.61 / 0.71 (7) | 0.76 / 0.96 (7) | 1.46 / 1.54 (10) |
| Audrain | median income (cuts $57,083, $82,500) | 1.20 / 1.32 (12) | 0.60 / 0.76 (8) | 1.24 / 1.31 (4) |
| Boone | aged 65+ | 0.86 / 0.94 (62) | 1.06 / 1.09 (35) | 1.10 / 1.13 (26) |
| Boone | median income | 0.92 / 1.02 (33) | 0.94 / 1.00 (37) | 1.01 / 1.03 (43) |
| Osage | aged 65+ | 1.41 / 1.41 (3) | 1.80 / 1.80 (4) | 1.54 / 1.56 (4) |
| Osage | median income | 2.13 / 2.15 (3) | 1.77 / 1.78 (5) | 1.09 / 1.09 (3) |

Boone's block groups are seen within about 15% of the statewide rate in every tercile; Audrain's oldest block groups
are seen at more than twice the rate of its youngest; Osage is seen above the statewide rate throughout, most in its
lower-income block groups. Cells hold 3–62 block groups.

## Pass-through discount

`build_road_stop_share.py` → `road_stop_share.csv`. Highways: OpenStreetMap ways of any highway class (proposed,
construction and abandoned excluded) whose ref is an Interstate or US route number — US 69 and US 56 are tagged
`secondary` in places — business routes, loops and spurs excluded (11,070 ways); 57.2% of 12,094 road-stop stores lie
within 1 km. **Adopted (authors' decision, 2026-10-25):** each out-of-county pair's highway-stop excess (share − the
destination's expected share) shrunk toward zero by empirical Bayes; discount = max(0, shrunken excess). Sampling
variance of a pair's share is computed with stores as clusters (per-visitor binomial variance understates it about
tenfold: mean squared excess is 0.13 at 25–50 visitors against a binomial 0.004); prior variance by method of moments.
Between-pair s.d. of the true excess 0.178; median sampling s.d. 0.068; shrinkage factor median 0.87 (0.89 at 200+
visitors, 0.20 under 50). Shares weighted by the adopted outcome (`visits_statewide`), January–September:

| Definition | Out-of-county road-stop share (within home county) | Visits removed | Pairs discounted |
|---|---:|---:|---:|
| Old codes (4471, 4571, 445131, 722513), statewide 12.5%, 200+ visitors (`discount_old`) | 12.5% (13.8%) | 3.04% | 3,313 |
| Codes fixed: + convenience stores 445120, statewide norm, 200+ (`discount_codes`) | 16.5% (18.2%) | 4.38% | 3,578 |
| Highway stops within 1 km, statewide norm, 200+ (`discount_highway_statewide`) | 11.6% (11.1%) | 3.86% | 3,203 |
| Highway stops, destination's own store mix, 200+, unshrunk (`discount_unshrunk`; adopted 2026-10-24) | | 2.23% | 2,619 |
| **Highway stops, own store mix, empirical-Bayes shrunken, every pair (`discount`, adopted)** | | **1.81%** | **3,320** |

Signed mean highway-stop excess, `visits_statewide`-weighted: +0.43% raw, −0.02% shrunken. Expected share for
destination j = the highway-stop share of j's residents' visits to j's places × the statewide ratio of out-of-county
to within-county highway share (1.04). Switch: `gravity_terms.travel_visits(..., discounted=False)` is the
undiscounted outcome (the primary sensitivity); `disc=` takes any `discount_*` column.

## Travel model

**Adopted: doubly-constrained gravity model, Poisson pseudo-maximum likelihood** (`travel_model.py`; terms, outcome,
scoring in `gravity_terms.py`).

- A fixed effect for every home county (its total travel) and every destination (its overall draw: capital,
  university, hospitals, shopping — measured from the data, not proxied)
- Pair terms (8, `gravity_terms.FACTORS`), core gravity terms by theory in three blocks: **distance** (log distance
  and its square; both again for rural home counties; log home population × log distance), **border**,
  **commuting** (out and in)
- Rural home county (2026-10-25): under 50% of its 2020 population in Census urban areas (`county_urban_share.csv`):
  89 rural, 26 urban. It replaces USDA RUCC nonmetro, a commuting definition under which Osage (0% urban) was metro.
  Audrain (45% urban) and Osage are rural; Boone (77%) is urban (Rural flag, under Current results)
- Commuting: LODES 2023 primary jobs (JT01) of Missouri residents (`free/mo_residents_od_JT01_2023.csv.gz`: Missouri
  main + the Missouri-home rows of the KS, IL, IA, AR, OK, NE, TN, KY aux files). The pair terms are Missouri pairs; the
  denominator, workers living in the county, includes out-of-state jobs
- Distance centred at 25 miles (the visit-weighted geometric mean out-of-county trip is 26 miles), home log population
  at its mean (geometric mean 21,980): the log-distance coefficient is the distance elasticity at 25 miles for an
  urban home county of mean size. Centring changes no prediction
- Outcome, every travel script: `visits_statewide` × (1 − `discount`) (Pass-through discount), which removes 1.81% of
  out-of-county visits. `od_predicted.csv`: `visits_recorded` renamed `visits_undiscounted` (statewide scale, before
  the discount; not Advan's recorded units)
- Inference: standard errors clustered by home county and by destination county
- Validation and primary metric: each home county held out (8 folds, seed 7), share-weighted absolute error of its
  destination shares over all Missouri destinations; intervals from 1,000 county bootstrap resamples, predictions held
  fixed; differences county-paired. R² against uniform shares (1 − SSE/SST) and against the fixed-effects-only model
- Selection: blocks tested as blocks; no hypothesis terms; exploratory additions only through the nested guard
- The Jan–Jun → Jul–Sep split is a stability check, not validation: persistence beats the model on it

### Validation

| Measure | Value |
|---|---|
| Held-out share-weighted error (points), primary | 3.28 [2.96, 3.59] |
| — small rural (56) / independent towns (32) / commuter (18) / hubs (9) | 3.41 [2.99, 3.87] / 2.84 [2.41, 3.28] / 4.28 [3.37, 5.19] / 2.06 [1.34, 2.91] |
| Held-out R², uniform reference / against fixed effects only | 93.7% [92.4, 94.8] / 93.7% (fixed effects only: error 16.04, R² 0.9%) |
| Big flows (forecast 5%+; 485 pairs): error; within 0.8–1.25×; actual ÷ forecast 10th–90th percentile | 3.44 [3.19, 3.71]; 49% [45, 53]; 0.60×–1.50× |
| Top FORECAST destination, actual ÷ forecast | 1.00× (middle half 0.86–1.19); 1.13× if selected on the observed share |
| Reference: destination effects + log distance only | 5.63 [5.09, 6.16]; adopted lower by 2.35 [1.85, 2.87] |
| In-sample: R² of shares; deviance | 94.8%; 62.3M |
| Stability, Jul–Sep from Jan–Jun: model / persistence | R² 93.8% / 98.7%; error 2.96 / 1.46; model − persistence +1.50 [+1.22, +1.78] |

All rows: `travel_model.py`.

Coefficients, Jan–Sep (two-way clustered; coefficient and interval `travel_model_dc_test.py selection`, s.e. and p
`travel_model.py`):

| Term | Coef [95%] | s.e. (p) |
|---|---:|---:|
| log distance (elasticity at 25 mi, urban home) | −0.875 [−1.123, −0.628] | 0.126 (< 0.001) |
| log distance² | −0.259 [−0.322, −0.196] | 0.032 (< 0.001) |
| rural × log distance | +0.177 [−0.060, +0.413] | 0.120 (0.14) |
| rural × log distance² | −0.210 [−0.316, −0.104] | 0.054 (< 0.001) |
| log home population × log distance | +0.133 [+0.072, +0.194] | 0.031 (< 0.001) |
| shared border | +0.440 [+0.309, +0.572] | 0.067 (< 0.001) |
| commuting out | +0.277 [+0.189, +0.366] | 0.045 (< 0.001) |
| commuting in | +0.189 [+0.118, +0.260] | 0.036 (< 0.001) |

Rural × log distance alone is not distinguishable from zero. It belongs to the distance block, which is tested as a
block (Selection) and passes; no term of a block is tested alone.

Distance elasticity, home county of mean population (two-way s.e.): urban −0.40 (0.15) at 10 mi, −0.88 (0.13) at 25,
−1.23 (0.13) at 50, −1.59 (0.14) at 100; rural +0.16 (0.21), −0.70 (0.15), −1.35 (0.12), −2.00 (0.11). By the point
estimates, rural travel falls off less steeply than urban travel within 25 miles and more steeply beyond 50 (the
curvature term, rural × log distance², −0.210, s.e. 0.054); at 25 miles the two do not differ distinguishably. The rural value
at 10 miles is the quadratic's end point (closest pair 7.5 miles), not a finding.

With no travel data for a county, the model places its destination shares to within 3.3 points (share-weighted) and
its top destination without bias (1.00×). For a county whose own travel is observed, the observed shares are the
better figure: the model is not a forecasting improvement on them.

### Selection

Blocks, each removed from the adopted model (`travel_model_dc_test.py selection`; held out, county-paired):

| Block removed | Held-out error | Gain from the block [95%] |
|---|---:|---:|
| none (adopted) | 3.279 | |
| distance (five terms) | 4.326 | +1.047 [+0.653, +1.433] |
| border | 3.404 | +0.125 [−0.105, +0.347] |
| commuting (out and in) | 3.737 | +0.457 [+0.245, +0.676] |
| all pair terms (fixed effects only) | 16.039 | +12.760 [+11.072, +14.329] |

The border block's gain interval includes zero (coefficient +0.440 [+0.309, +0.572]); it is kept as a core term by
theory and is the one block whose predictive contribution is not established. The distance block passes as a block
although rural × log distance alone is not distinguishable from zero (p = 0.14).

Exploratory additions, nested guard (`combined_marginal_test.py travel_nested_all`; 24 candidates — eight route and
area terms alone and together, three competing-destination terms, ten home-county ACS measures × distance, two
hospital terms — chosen inside each outer training set on 7 inner folds):

| Procedure | Held-out error | Gain vs adopted [95%] |
|---|---:|---:|
| Adopted (same folds) | 3.279 | |
| **Nested, lowest inner error (deciding)** | 3.173 | +0.106 [−0.045, +0.263] |
| Nested, interval rule applied inside the training counties | 3.175 | +0.104 [−0.036, +0.239] |
| One at a time, not nested (reference only): nearest comparable alternative | 3.222 | +0.057 [+0.022, +0.092] |

Inner choices: "on the way to a bigger centre" in 4 of 8 outer folds, all eight route/area terms 3, "on-the-way
weight" 1. **No addition adopted.** The one-at-a-time result is not a criterion; the nearest-alternative term is rejected by the
nested guard like every other candidate.

### Sensitivities

`travel_model.py`; distance elasticity at 25 mi, mean-size home county (two-way s.e.); held out:

| Outcome | Urban | Rural | Error | R² | R² vs fixed effects |
|---|---:|---:|---:|---:|---:|
| **Adopted: `visits_statewide`, shrunken highway discount** | −0.875 (0.126) | −0.699 (0.147) | 3.28 | 93.7% | 93.7% |
| Undiscounted (primary sensitivity) | −0.872 (0.123) | −0.690 (0.144) | 3.21 | 93.8% | 93.7% |
| Unshrunk discount (`discount_unshrunk`) | −0.870 (0.127) | −0.692 (0.148) | 3.31 | 93.7% | 93.6% |
| Old discount (`discount_old`) | −0.859 (0.127) | −0.690 (0.147) | 3.30 | 93.8% | 93.8% |
| County factor (`visits`, 2026-10-16) | −0.855 (0.087) | −0.703 (0.128) | 3.30 | 93.5% | 94.6% |
| Uncapped destinations only | −0.953 (0.140) | −0.799 (0.128) | 3.04 | 94.6% | 94.6% |
| Distinct people (`people_lower`; independent city and county one unit; undiscounted) | −0.662 (0.109) | −0.622 (0.138) | 1.80 | 88.5% | 88.2% |

- The elasticity moves by less than one standard error across scales and discount definitions.
- Uncapped destinations: decay steeper (rural −0.80). Capped destination block groups (Advan keeps 2,000 home block
  groups per row) are the busiest, reached from far away; capping drops distant homes.
- Distinct people: urban decay flatter (−0.66): a visit count weights frequent nearby trips, a person count does not.
  The lower error is on a different, smoother outcome, not a better model.
- Discount definitions (`travel_model_stop_discount_test.py`, each against its own outcome): undiscounted 3.21; old
  3.30 (removes 3.04%); codes fixed 3.38 (4.38%); highway at the statewide norm 3.38 (3.86%); unshrunk 3.31 (2.23%);
  adopted, shrunken 3.28 (1.81%). The discount is a measurement correction, not a fit choice.

Distance form against a restricted cubic spline in log distance, 4 knots, the rest of the model unchanged
(`travel_distance_spline.py`; held out, county-paired; knots in miles: pair quantiles 38.8, 112.5, 175.5, 279.4;
visit-weighted quantiles 7.5, 21.5, 37.4, 152.6):

| Distance form | Held-out error [95%] | Change vs adopted [95%] | R² | Elasticity at 25 mi, urban / rural (s.e.) | At 50 mi, urban / rural | In-sample deviance |
|---|---:|---:|---:|---:|---:|---:|
| **Adopted: quadratic in log distance** | 3.279 [2.96, 3.59] | | 93.7% | −0.88 (0.126) / −0.70 (0.147) | −1.23 / −1.35 | 62.3M |
| Spline, knots at pair quantiles | 3.429 [3.05, 3.82] | +0.150 [−0.084, +0.392] | 92.8% | −0.73 (0.153) / −0.77 (0.153) | −0.79 / −0.86 | 65.3M |
| Spline, knots at visit-weighted quantiles | 3.267 [2.92, 3.60] | −0.012 [−0.129, +0.123] | 93.8% | −0.64 (0.142) / −0.53 (0.153) | −1.24 / −1.45 | 61.7M |

Neither spline lowers held-out error; the quadratic is kept. The elasticity at 25 miles depends on the form (urban
−0.88 / −0.73 / −0.64, rural −0.70 / −0.77 / −0.53), so the 25-mile elasticity is quoted with its form; the
held-out shares, the primary metric, do not depend on it.

### Residual spatial autocorrelation

`residual_autocorrelation.py`: Moran's I on Missouri counties, queen contiguity (gravity_terms adjacency), row-
standardised; p from 999 permutations, two-sided. With both sets of fixed effects raw residuals sum to zero for every
home and destination county, so the measures are the held-out error per home county, the held-out signed residual per
destination (observed minus forecast share summed over held-out home counties) and coverage's in-sample error per
newsroom county on destinations with 1%+ of visits (`coverage_model.py` writes no held-out predictions):

| Residual | Counties | Moran's I | E[I] | p | Audrain | Boone | Osage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Travel, held-out error by home county | 115 | +0.007 | −0.009 | 0.763 | 0.88 | 1.36 | 3.13 |
| Travel, held-out signed residual by destination | 115 | +0.139 | −0.009 | 0.014 | 6.79 | 5.21 | 1.22 |
| Coverage (all outlets), in-sample error by newsroom county | 88 | −0.044 | −0.011 | 0.679 | 1.67 | 0.99 | 4.56 |
| Coverage (no broadcasters), in-sample error by newsroom county | 88 | −0.070 | −0.011 | 0.425 | 1.75 | 1.62 | 4.52 |

Home-county errors and coverage errors show no spatial clustering. **Limitation:** the destination residuals cluster
(I +0.139, p 0.014): neighbouring destinations are under- or over-predicted together, so the destination effects do
not absorb a regional component of destination draw. Audrain and Boone are under-predicted as destinations (+6.79 and
+5.21 points summed over home counties). Intervals that treat destinations as independent would be too narrow; the
travel intervals cluster by home and by destination county but not by region.

### Out-of-state travel: Kansas

Missouri residents' visits to Kansas block groups (`neighborhood/raw_ks/`) enter crossover. Share of out-of-county
visits that go to Kansas (`travel_model.py`): Audrain 1.2%, Boone 5.2%, Osage 1.1%.

- Every travel share in this log is a share of out-of-county visits to **Missouri** counties. Illinois, Iowa,
  Arkansas, Oklahoma and Nebraska are not in the data.
- The outcome is not renormalised: with home-county fixed effects renormalising only rescales each county's shares by a
  constant. Comparisons of a share's size across counties use the Kansas-inclusive denominator or say they exclude
  Kansas.

### Steps that led there

Held out (`travel_model_compare.py` first row, `travel_model_dc_test.py` the rest):

| Version | In-sample deviance | Held-out R² | Held-out error [95%] | Top forecast destination | Big flows within 0.8–1.25× |
|---|---:|---:|---:|---:|---:|
| Plain gravity: population + distance (origin effects) | 246.1M | 72.4% | 8.06 [7.23, 8.91] | 1.23× | 18% |
| + border, rural home × distance, stores (singly constrained, `gravity_terms.SINGLY`) | 169.4M | 83.0% | 5.84 [5.29, 6.44] | 1.10× | 30% |
| Singly + area centre + curved distance | 130.6M | 87.3% | 4.88 [4.40, 5.39] | 1.11× | 37% |
| Doubly constrained: distance, rural × distance, border | 93.9M | 88.9% | 4.62 [4.18, 5.12] | 1.01× | 38% |
| + curved distance | 75.8M | 91.4% | 3.82 [3.46, 4.21] | 0.99× | 39% |
| + larger home counties travel farther (adopted before 2026-10-18) | 69.0M | 92.0% | 3.74 [3.36, 4.09] | 0.98× | 41% |
| **+ commuting out and in (adopted)** | **62.3M** | **93.7%** | **3.28 [2.96, 3.59]** | **1.00×** | **49%** |

The singly-constrained model was abandoned on held-out error (5.84 against 3.28; R² 83.0% against 93.7%); the 1.6×
under-prediction once given as the reason is superseded (appendix). The "Osage residents go to Jefferson City twice as
often as expected" figure came from that model and stays withdrawn: under the adopted model Osage → Cole is 1.16
in-sample, 1.22 held out. In the singly-constrained model (`travel_model_compare.py`, its own steps), metro destination
and jobs per resident add nothing and stores per resident is significant (metro −0.165, p = 0.19; jobs p = 0.80;
stores +0.659, p = 0.003); the doubly-constrained model absorbs all destination attributes.

### Rejected

Each added to the adopted model; change in held-out error [95%] (= −gain); coefficient (two-way p). All are also inside
the nested guard above, which is the deciding test.

| Tested | Result | Script |
|---|---|---|
| Hospital indicator | See measurement corrections; hospital terms under County characteristics | — |
| Same metro/micro area | +0.008 [−0.048, +0.068]; −0.090 (p = 0.24) | `travel_model_hub_test.py` |
| Nearest area centre | −0.004 [−0.083, +0.078]; p = 0.06 | `travel_model_hub_test.py` |
| Adjacent area centre | +0.012 [−0.033, +0.055]; p = 0.17 | `travel_model_hub_test.py` |
| Intervening opportunities (population closer than the destination) | +0.023 [−0.027, +0.071]; p = 0.34 | `travel_model_hub_test.py` |
| All four | +0.059 [−0.036, +0.157] | `travel_model_hub_test.py` |
| Driving time between main towns (OpenStreetMap routes) in place of straight-line distance | +0.107 [−0.088, +0.329] | `travel_model_drive_test.py` |
| Driving time + on the way to a bigger centre / weighted | −0.034 [−0.241, +0.169] / −0.060 [−0.310, +0.182] | `travel_model_drive_test.py` |
| Nearest comparable alternative / in another direction (60°+ off the bearing) | −0.057 [−0.092, −0.022] / −0.023 [−0.049, +0.003] | `travel_competing_test.py` |
| Fotheringham C_ij = Σ(k≠i,j) W_k/d_jk (Haynes & Fotheringham 1985) | +0.047 [−0.020, +0.123]; −0.679 (p = 0.07) | `travel_competing_test.py` |
| Business gaps (CBP 2022) | Not identifiable: log(dest + 1) − log(origin + 1) is absorbed by the two sets of fixed effects (design rank 237 of 243) | `travel_business_test.py` |
| Origin-class-specific pair terms, k = 2 / 3 / 4 | +0.12 [−0.03, +0.29] / −0.02 [−0.15, +0.12] / +0.19 [+0.02, +0.36]; k = 4 independent towns +0.38 [+0.05, +0.72], hubs −0.06 [−0.34, +0.21] | `travel_county_class_model.py` |
| Work and non-work apart: non-work with / without commuting | −0.00 [−0.01, +0.01] / +0.42 [+0.21, +0.63] | `travel_purpose_split_test.py` |
| All eight route/area terms together | −0.18 [−0.40, +0.03] | `combined_marginal_test.py` |

Class-specific pair terms with k = 4 raise held-out error (+0.19 [+0.02, +0.36]).

Main destinations, actual ÷ expected share, adopted (in-sample / held out; `travel_competing_test.py`): Osage → Cole
1.16 / 1.22, Osage → Boone 1.43 / 1.38, Audrain → Boone 0.97 / 0.98, Audrain → Callaway 1.37 / 1.27, Audrain →
Marion 2.27 / 2.22, Boone → Cole 0.73 / 0.69, Boone → St. Louis County 1.26 / 1.27.

The routing (`build_drive_routes.py` → `drive_od.csv`) is kept: it confirms, for example, that Mexico → Columbia
(38 minutes) runs through Callaway County. Half of Audrain residents' Callaway visits are in Kingdom City; the adopted discount removes 15.9% of that pair's
visits (`build_road_stop_share.py`, `road_stop_share.csv` `discount`; 20.0% under the 2026-10-16 definition,
`discount_old`); the rest (Fulton is 22 minutes from Mexico) is ordinary local travel.

### Small counties and pair-level commuting

The pooled travel model fits large counties best: Poisson weights by count, so big flows drive the fit. Tested for the
counties it serves worst, public data only. Tiers: k-means on log population (ACS 2020–2024) and commuting outflow
(LODES 2023) (`county_class_k4.csv`): small rural 56 (median 10,600, 67% commute out), independent towns 32, commuter
18, hubs 8. The file has 114 rows, with no row for the independent city; scored, the independent city is a ninth hub
and it and its county are scored apart (115 home counties: hubs 9).

| Tested (held out; share-weighted error, change [95%]) | Result | Script |
|---|---|---|
| **Commuting block, added to the pre-commuting model** | **all 3.74 → 3.28 (−0.46 [−0.68, −0.24]); small rural 4.00 → 3.41 (−0.60 [−0.92, −0.25]); independent towns 3.26 → 2.84 (−0.42 [−0.72, −0.13]); commuter 4.27 → 4.28 (+0.00 [−0.55, +0.53]); hubs 2.69 → 2.06 (−0.63 [−1.68, +0.33]); small rural top-3 (forecast-ranked) 4.93 → 4.23** | `travel_commute_pair_test.py` |
| Separate model for small origins (< 15,000) into larger counties | best (size rank within 60 mi) 3.73 [3.18, 4.29] against the pooled model's 3.41 [2.91, 3.94] on the same pairs | `travel_small_origin_model.py` |
| Measured destination draw + Fotheringham in place of destination effects | small origins +0.58 [+0.18, +1.01]; others +1.15 [+0.50, +1.83] | `travel_small_county_test.py` |
| Destination effects shrunk toward that model (alpha 1e-4 to 1e-2, all shown) | Jul–Sep 3.19 against 3.12 (small origins) | `travel_small_county_test.py` |
| Tier and county pull of destination jobs and retail (LODES; CBP 2022), nested guard | gain +0.050 [−0.030, +0.130] all counties; small rural +0.045 [−0.071, +0.153]: none adopted (table below) | `travel_tier_pull_cv.py` |
| Distance to the destination's job hub (JT01) from where workers live; nearest, farthest edge | small rural: 3.28 centroid against 3.27–3.35 (every interval spans zero) | `travel_distance_variants.py` |
| Blend of the county's own Jan–Jun shares with the model (k chosen on Jan–Apr → May–Jun) | Jul–Sep 1.46, equal to persistence (−0.01 [−0.03, +0.02]) | `travel_blend_test.py` |

`travel_tier_pull_cv.py` (every county held out, 8 folds; all Missouri destinations; top-3 = each small rural county's
three largest forecast destinations; 320 fits from full-data start values, all converged by IRLS):

| Model | All counties (115) | Small rural (56) | Top-3, small rural | Gain vs adopted, all [95%] |
|---|---:|---:|---:|---|
| Adopted (8 FACTORS) | 3.279 | 3.406 | 4.23 | |
| + tier pull (one at a time, not nested) | 3.233 | 3.333 | 4.04 | +0.046 [−0.053, +0.141] |
| + county pull (one at a time) | 3.344 | 3.326 | 4.07 | −0.065 [−0.215, +0.062] |
| + tier + local (one at a time) | 3.400 | 3.377 | 4.09 | −0.121 [−0.313, +0.038] |
| Theory, no destination effects (one at a time) | 3.795 | 3.828 | 4.77 | −0.516 [−0.916, −0.140] |
| **Nested (lowest inner error)** | 3.229 | 3.361 | 4.06 | **+0.050 [−0.030, +0.130]** |

The nested guard chose tier pull in 6 of 8 outer folds; its gain is positive and its interval includes zero: none
adopted.

Pair-level commuting is the first public measure that predicts a county's travel markedly better without its own
travel data; it is a core block in the shared gravity terms (`gravity_terms.py`), so the travel and coverage models
both carry it. Travel (rural flag, `travel_model.py`): out +0.277 (s.e. 0.045), in +0.189 (0.036) (two-way); block
gain +0.457 [+0.245, +0.676] (`travel_model_dc_test.py selection`). By tier (table above) the gain is clear for all
counties together, small rural counties and independent towns; for commuter counties and hubs (18 and 9 counties) the
intervals include zero, and for commuter counties the point estimate is zero (+0.00 [−0.55, +0.53]). Coverage (rural flag, `coverage_model.py`): commute in +0.42 (s.e. 0.069,
clustered by newsroom county), out −0.02 (n.s.): newsrooms cover the counties whose workers commute into theirs; the
block is a core control kept by theory (gain −0.007 [−0.106, +0.087]; Wald χ² 46.0, p < 0.001). With commuting in the
model, Osage's travel to Jefferson City is close to expected but still above it (Osage → Cole 1.16 in-sample); travel
to Columbia, where few Osage residents work, is for shopping, health care and the university and stands out (Osage →
Boone 1.43).
Spillover does not use the travel model.

### Public-data travel model (Stage 1) and Advan-learned corrections (Stage 2), 2026-10-18; revised 2026-10-24/25

Question: how close a travel model built from public data alone gets to the Advan-fitted model, and how much of the
gap Advan-learned corrections close; both with intervals. The public model is not claimed to beat the Advan-fitted
model. Outcome: the travel model's (`gravity_terms.travel_visits`: `visits_statewide`, shrunken highway-stop
discount, 1.81%), each home county's out-of-county Missouri destination shares, January–September 2026. Every score
is out of sample for the county scored:

| Element | Rule (2026-10-25) |
|---|---|
| Primary metric (declared) | Share-weighted error, 100 × Σ a\|p - a\| (points), over ALL Advan destinations in Missouri: a pair outside a model's support counts with model share 0 |
| Beside it | The same on the common destination set (the public model's destinations, counties within 200 miles of the tract; Advan and the Advan-fitted model renormalised over it; outside it 2,968 pairs, 1.34% of Advan share per county, max 8.2%); log-ratio error, mean \|ln(p/a)\| over pairs with Advan share ≥ 1% (p floored at 0.01%; scale-free, where the share-weighted error scales with concentration, r × HHI for a uniform relative miss r). `public_scoring.py` |
| Averaging | County mean (each home county weighs the same); the independent city and its county scored apart (115 homes) |
| Intervals | County-paired bootstrap, 2,000 draws, 95% percentile; the all-county interval resamples within each class. * = interval excludes zero |
| Benchmark | Advan-fitted: the adopted model (`gravity_terms.FACTORS`, 8 terms centred at 25 miles), each county held out, 8 folds, seed 7 (`gravity_terms.loco`; `public_vs_advan_compare.py` → `compare_shares.csv`): 3.28 on all destinations |
| Commuting | LODES 2023 primary jobs (JT01) of residents, in and out of state, in every public-model script. Missouri: `free/mo_residents_od_JT01_2023.csv.gz` (Missouri main + the Missouri-home rows of the IL, KS, IA, AR, OK, NE, TN, KY aux files), read by the work model (out-of-state jobs are destinations) and the corrections (`public_adjusted_model.py`: pairs and commuting ranks are Missouri pairs; out-of-state jobs enter only the denominator, all workers living in i) |
| Stage 1 | Each class's public setting chosen by Advan error (primary metric) with the scored county left out (nested). No Advan in any parameter; Advan chose among settings (nested) |
| Stage 2 | Corrections learned on other counties (8 folds); their structure chosen inside an outer loop; compared with the Stage 1 base of the same outer fold |

Classes (`score_segments.py`): the k-means tiers above; commuter counties split by the OMB 2023 delineation into rings
of the state's two largest metros (9) and rings of regional hubs or outside any metro (9).

**Public model** (`public_work_model.py`, `public_travel_tiers.py`, `assemble_public_by_class.py`), tract origins
(CenPop2020 tract centres), destinations every county within 200 miles in Missouri and the eight neighbouring states:

| Part | Public data and calculation |
|---|---|
| Work | LODES 2023 primary jobs (JT01) tract → county, `mo_residents_od_JT01_2023.csv.gz` (the same rows as the Missouri main file plus the eight neighbouring states' auxiliary files, 2,621,217 jobs); observed flows within 90 miles, a gravity fit (conditional Poisson on distance, CBP employment, population, state line) beyond, where LODES carries employers' imputed establishment assignments |
| Retail | Trade area analysis: 2025 Missouri DOR taxable sales by county; pull factor; income-adjusted trade area capture (ACS per-capita income); leakage = 1 − capture; Huff allocation on taxable sales (hubs: on sales beyond the county's own expected, Reilly's exponent 2) |
| Chained errands | Errand trips starting at work (2022 NHTS, WHYFROM 3–5): 1.3 (urban) and 2.0 (rural) a month per worker, sent to the work counties |
| Medical, specialty | CBP 2022 health care; furniture, electronics, clothing, sporting goods, department stores (central place: higher-order goods) |
| Recreation, visiting | 2022 NHTS long-distance file (vacation; visiting family or friends), weighted by days away; draws CBP arts and recreation employment, 2020 population |
| Decay | Calibrated to the NHTS trip-length distribution (maximum likelihood over distance bands), rural and urban households |

Settings tested on the reference build, one default changed at a time (`public_default_sensitivity.py` on the builds of
`run_default_sensitivity.sh`; adopted outcome, all Advan destinations; reference build 5.44, Advan-fitted 3.28; change
in error, all counties): work from home (ACS B08006) +0.02, 15 work days +0.06, shopping ×0.5 +0.10, medical and
specialty ×0.5 / ×2 +0.06 / −0.07, circuity 1.0 / 1.4 +0.05 / −0.10, long-distance trips not days −0.19, Huff
attraction exponent 1.5 −0.02, commuter classes on urban decay −0.04 (commuter −0.30) — none moves any class by more
than 0.40. Recreation and visiting move most (×0.5 −0.24, ×2 +0.41), then gross leakage (Huff home share; −0.24, hubs
+0.60). Rejected: Huff attraction exponent 0.5 (+0.42); the visitation law's exponent 2 for every kind (small rural
+1.52 against the baseline public build, `public_vs_advan_compare.py`; rural decay is steeper, about 4–6). Non-work
variants (`public_nonwork_model.py`, `public_model.sh` step 9, work part the JT01 work model; scored on the adopted
outcome by `public_default_sensitivity.py`), one at a time against the first version (establishments as the draw,
population-centre distance, RUCC survey classes, squared loss; 5.74): employment as the draw −0.20, metro-size survey
classes +0.10 (hubs +0.81; rejected), likelihood loss −0.03, job-centre distance +1.04; against the base build
(employment draw, likelihood loss; 5.50), non-work decay by income, degree or tenure −0.18 to −0.19, kept out for
the survey's thin subgroups. With the
parts' weights fitted to Advan by class (`public_segment_weights.py`, parked), the employment-draw non-work part gets
zero weight in every class once taxable sales are in. More work days are better up to 40 in three classes (`_g_`
builds, Huff on sales, against 10 days: small rural −0.68, independent towns −0.48, hubs −0.62, commuter +0.08; Huff
on surplus: small rural, independent towns and commuter, hubs best at 15).

**Stage 1, setting per class** (`public_stage1_nested.py`). Candidates: the 53 Missouri builds of
`public_travel_tiers.py`, all rebuilt 2026-10-24 on the JT01 work model (recipes in `public_commands.sh`). Rule:
lowest mean share-weighted error (all destinations) over the class's other counties.

| Class | Setting chosen on all counties | Leave-one-out picks |
|---|---|---|
| Small rural (56) | observed LODES within 90 mi, 40 work days per out-of-county commuter, chained errands, Huff on sales (`_g_40_sales`) | 56 of 56 |
| Independent towns (32) | the same with decay 6 for retail, medical, specialty (`_c_40_l6all`) | 23; `_g_40_surplus` 8; `_c_hyb40_40` 1 |
| Commuter: major metro (9) | reference build, gross leakage (Huff home share), recreation and visiting x0.5 (`_s_hr`) | 5 settings: `_s_hr` 3, `_s_ruralset` 2, `_s_circ14` 2, `_s_commset` 1, `_s_recvis05` 1 |
| Commuter: regional hub (9) | reference build, gross leakage, commuter classes on urban decay (`_s_commset`) | 7; `_c_hyb40_40` 2 |
| Hubs (9) | observed LODES within 90 mi, 15 work days, Huff on surplus sales (`_g_15_surplus`) | 8; `_g_25_surplus` 1 |

**Where the gap is** (`public_gap_corrections.py`; reference build 5.44 against the Advan-fitted 3.28; one Advan
correction at a time, learned on other counties in 8 folds): destination pull closes 48% of the gap, the shape of
distance decay 23%, adjacency 12%, destination size −11%; destination pull, decay and adjacency together 69%. Its
single power law sends 1.1–1.5 times Advan's share to destinations within 15 miles (Advan / public 0.66–0.89 by class)
and, for hubs, half the travel beyond 120 miles (1.99); it understates the smallest destinations by taxable sales
(1.34–1.71) and overstates the largest (0.83–0.98). The 15 destinations carrying most of the public model's error
carry 71.8% of it; Advan's inflow to Boone is 1.19 times the public model's, to Audrain 1.30, to Osage 0.93
(`public_gap_diagnosis.py`). Taken apart, held out, the Advan-fitted model's error rises from 3.28 to 3.74 with public
destination measures in place of destination effects (the measures explain the effects with R² 0.907), to 3.74
without pair commuting, 3.40 without adjacency and 4.18 with log distance only.

**Stage 2, Advan-learned corrections** (`public_adjusted_model.py`, applied to tract shares and rolled up):
multiplicative factors, fitted in turn and iterated, for distance band by class (learned apart for each home county's
dominant and secondary LODES commuting counties), adjacency by class, LODES commuting rank by class, destination order
by class, destination class by class; learned on the common destination set. Destination order follows the central
place hierarchy from public data (transferable definitions): metro core = central county of a metro area of 1,000,000
or more (OMB 2023; Census 2024 CBSA population); rest of such a metro; regional centre = pull factor ≥ 1 and at least
60,000 trade-area customers; sub-regional town = pull factor ≥ 1; resort = marinas plus RV parks and recreational
camps per resident in the top tenth of U.S. counties (CBP 2022); local; a core or big-metro county within 50 miles of
home is its own order. Modes: C segment factors only (transferable); B + destination factor from public measures (log
sales, log population, nonmetro, log arts employment); A + one factor per destination county (Missouri only).

**Outer loop** (`public_adjusted_nested.py`). For each of the 8 folds of home counties: (1) Stage 1 is chosen on the
other 7 folds (the fold base); (2) each of 245 candidate structures is scored by inner cross-validation on the other 7
folds only (primary metric); (3) the lowest inner error is learned on the 7 folds and applied to the held-out fold, on
its fold base. Each mode chooses its own structure. Candidates: the full factorial of the Refinements choices —
commuter split (none; split; split learned as independent towns; split learned as small rural) × distance by commuting
rank (0/1) × near-core order (0/1) × destination-order definitions (Missouri, regional centre at pull factor 1.1; at
1.0; transferable) × group sets (none; commuting out and in; destination order; + commuting rank; + destination class)
= 240 — plus the five rejected variants on the adopted structure (rank × order cell; destination class × band; pooled
hub factor; hub distance bands; metro-core factor).

Structure chosen per outer fold, mode C: split learned as small rural, Missouri definitions at pull factor 1.1,
commuting rank + destination order (folds 0, 1, 5; fold 2 the same on transferable definitions); the adopted structure
on Missouri definitions at 1.0 (3; 4 without the near-core order; 6 with the commuters split on their own); the adopted
structure with a metro-core factor (7). Mode A: a different structure in nearly every fold. Fold bases: the major-metro setting differs from the
all-county one in folds 0-2, the independent-town setting in 1-2 and 5-7, the hub-ring setting in fold 1
(`_c_hyb40_40`), the hub setting in fold 7 (`_c_40_l6`) (`public_adjusted_nested_choices.csv`).

#### Missouri (115 home counties)

Share-weighted error, points, all Advan destinations (primary):

| Model | Small rural (56) | Indep. towns (32) | Commuter: major metro (9) | Commuter: regional hub (9) | Hubs (9) | All (115) |
|---|---:|---:|---:|---:|---:|---:|
| Advan-fitted (counties held out) | 3.41 | 2.84 | 4.75 | 3.80 | 2.06 | **3.28** |
| **Public, Stage 1 nested (leave one county out)** | 4.10 | 4.41 | 6.05 | 6.26 | 5.24 | **4.60** |
| Public, Stage 1 per outer fold (base of the outer loop) | 4.10 | 4.34 | 5.82 | 6.25 | 6.09 | 4.63 |
| **+ segment corrections, outer loop (C, transferable)** | 3.61 | 3.86 | 4.54 | 5.76 | 5.23 | **4.05** |
| + destination factor from public measures, outer loop (B) | 3.50 | 3.85 | 3.93 | 5.79 | 4.72 | 3.91 |
| + one factor per destination county, outer loop (A, Missouri only) | 3.09 | 3.23 | 4.45 | 6.29 | 2.55 | 3.45 |
| Public, Stage 1 in-sample (not out of sample) | 4.10 | 4.21 | 5.16 | 5.09 | 5.11 | 4.37 |
| + segment corrections, structure chosen in-sample (not out of sample) | 3.41 | 3.54 | 3.73 | 4.38 | 3.92 | 3.59 |

Gap to the Advan-fitted model, all destinations, share-weighted error [95%]:

| Model − Advan-fitted | Small rural | Indep. towns | Commuter: major metro | Commuter: regional hub | Hubs | All |
|---|---|---|---|---|---|---|
| Public nested | +0.70 [+0.04, +1.43]* | +1.57 [+1.01, +2.19]* | +1.30 [−0.27, +2.96] | +2.46 [−0.62, +5.79] | +3.18 [+1.33, +5.37]* | +1.32 [+0.84, +1.83]* |
| Public fold base | +0.70 [+0.04, +1.43]* | +1.50 [+0.95, +2.08]* | +1.07 [−0.37, +2.62] | +2.45 [−0.62, +5.79] | +4.03 [+1.71, +6.94]* | +1.35 [+0.85, +1.88]* |
| C outer | +0.20 [−0.41, +0.87] | +1.02 [+0.51, +1.55]* | −0.21 [−2.17, +2.08] | +1.96 [−0.12, +4.50] | +3.17 [+1.84, +4.61]* | +0.77 [+0.32, +1.20]* |
| B outer | +0.09 [−0.51, +0.70] | +1.01 [+0.56, +1.53]* | −0.82 [−3.32, +1.76] | +1.99 [−0.55, +5.06] | +2.66 [+1.30, +4.10]* | +0.63 [+0.15, +1.09]* |
| A outer | −0.31 [−0.81, +0.21] | +0.39 [−0.12, +0.98] | −0.30 [−2.45, +1.90] | +2.49 [+1.05, +4.21]* | +0.49 [−0.87, +1.86] | +0.17 [−0.21, +0.56] |

Corrections against their own fold base, all destinations, share-weighted error [95%]; share of the fold base's gap
to the Advan-fitted model they close:

| Corrections − fold base | Small rural | Indep. towns | Commuter: major metro | Commuter: regional hub | Hubs | All |
|---|---|---|---|---|---|---|
| C, change | −0.49 [−0.87, −0.09]* | −0.48 [−1.12, +0.13] | −1.29 [−3.22, +0.26] | −0.50 [−2.20, +1.49] | −0.86 [−2.77, +0.95] | **−0.58 [−0.94, −0.23]*** |
| C, share of the gap closed | 71% [9, 314] | 32% [−12, 64] | 120% [−677, 990] | 20% [−256, 215] | 21% [−48, 45] | **43% [21, 68]** |
| B, change | −0.60 [−0.99, −0.19]* | −0.49 [−1.08, +0.12] | −1.89 [−4.44, +0.13] | −0.47 [−2.35, +1.28] | −1.37 [−3.35, +0.50] | −0.72 [−1.10, −0.36]* |
| B, share of the gap closed | 86% [24, 394] | 32% [−11, 60] | 176% [−1023, 1408] | 19% [−228, 257] | 34% [−27, 59] | 53% [30, 85] |
| A, change | −1.01 [−1.59, −0.42]* | −1.11 [−1.81, −0.39]* | −1.37 [−3.69, +0.83] | +0.04 [−2.34, +2.81] | −3.54 [−7.10, −0.79]* | −1.18 [−1.68, −0.71]* |
| A, share of the gap closed | 145% [68, 590] | 74% [31, 110] | 128% [−618, 824] | −1% [−824, 555] | 88% [36, 123] | 88% [60, 118] |

Shares of the gap are unstable where the gap itself is small (small rural +0.70) or the class has nine counties.

Beside the primary metric (all classes, all counties):

| | Common set, share-weighted | All destinations, log-ratio |
|---|---|---|
| Advan-fitted | 3.36 | 0.34 |
| Public nested | 4.70; gap +1.35 [+0.86, +1.87]* | 0.58; gap +0.24 [+0.20, +0.28]* |
| Public fold base | 4.73; gap +1.37 [+0.86, +1.90]* | 0.58; gap +0.24 [+0.20, +0.28]* |
| C outer | 4.15; gap +0.79 [+0.35, +1.22]*; vs fold base −0.58 [−0.96, −0.20]*, 42% [18, 66] of the gap | 0.51; gap +0.16 [+0.13, +0.20]*; vs fold base −0.08 [−0.09, −0.05]*, 32% [24, 39] |
| B outer | 4.02; gap +0.66 [+0.19, +1.11]* | 0.50; gap +0.15 [+0.12, +0.19]* |
| A outer | 3.51; gap +0.16 [−0.23, +0.55] | 0.44; gap +0.10 [+0.06, +0.13]*; vs fold base 60% [51, 70] of the gap |

- Public data alone, nothing learned from Advan but the choice among settings: 1.32 [0.84, 1.83] points from the
  Advan-fitted model on all destinations (4.60 vs 3.28); the gap is largest in hubs (+3.18) and the regional-hub rings
  (+2.46), excludes zero in small rural counties (+0.70 [+0.04, +1.43]), and includes zero in both commuter rings
  (major metro +1.30 [−0.27, +2.96], regional hub +2.46 [−0.62, +5.79]), nine counties each.
- The transferable corrections, structure chosen out of sample, close 43% [21, 68] of the fold base's gap (4.63 ->
  4.05); with one factor per destination county (Missouri only), 88% [60, 118] (-> 3.45; remaining gap +0.17
  [−0.21, +0.56]). On the log-ratio error the corrections close 32% [24, 39] and 60% [51, 70].
- Against the fold base the corrections reduce the error in small rural counties (both metrics) and, on the log-ratio
  error only, in major-metro rings and hubs; in regional-hub rings in neither metric (−0.50 [−2.20, +1.49]).
- Choosing out of sample costs 0.23 points at Stage 1 (in-sample 4.37 → nested 4.60) and 0.46 at Stage 2 (in-sample
  structure 3.59 → outer loop 4.05); in the nine-county classes 0.89-1.17 at Stage 1 and 0.81-1.38 at Stage 2.
- Destination-order factors (Advan / public): metro core 0.65-0.99, regional centre 1.35-1.51, sub-regional town
  1.09-1.42, local 0.88-0.98, resort 0.84-1.11 (2026-10-18, all counties) — the public model's draw is too steep in
  size and too flat in the hierarchy.

**Commuter counties.** One class held two behaviours. Major-metro rings spread travel over several metro counties and
commute to the core while visiting the nearest large county; regional-hub rings send most of their travel to one hub.
Split, both rings' public errors lie within the interval of the Advan-fitted model's before any correction (major metro
+1.30 [−0.27, +2.96], regional hub +2.46 [−0.62, +5.79]): the Advan-fitted model itself does worst in these two
classes (4.75 and 3.80). The metro-ring corrections bring the point error below the Advan-fitted model's (C −0.21
[−2.17, +2.08], B −0.82 [−3.32, +1.76]), not distinguishably; the regional-hub rings are not improved by any
correction out of sample, because the near-hub relation is learned elsewhere as an overstated small neighbour.

**Refinements, 2026-10-18** (`public_adjusted_model.py`, `score_segments.py`; in-sample structure selection, outcome and
commuting of 2026-10-18, full destination set — superseded by the outer loop above, kept as the record of what was
tried):

| Change | Small rural | Indep. towns | Commuter: major metro | Commuter: regional hub | Hubs | All |
|---|---:|---:|---:|---:|---:|---:|
| Segment corrections | 3.43 | 3.52 | 3.93 | 6.40 | 3.48 | 3.73 |
| Regional centre at pull factor ≥ 1.0 (was 1.1) | 3.41 | 3.51 | 3.94 | 6.12 | 3.48 | 3.69 |
| + a metro core within 50 miles of home is its own order | 3.35 | 3.43 | 3.88 | 5.81 | 3.68 | 3.63 |
| Transferable definitions + near core | 3.40 | 3.46 | 3.81 | 5.62 | 3.49 | 3.63 |

Every choice in this table is one of the outer loop's 245 candidates. Rejected 2026-10-18, also candidates in the
outer loop: a pooled hub relation; hub pairs with their own distance bands; a metro-core factor per class; a commuting
rank × destination order cell; destination class × distance band. The outer loop chose the metro-core factor (fold 7),
and destination class × band is the transferable structure chosen on all counties: the rejections were within noise. The 2026-10-18 structure on the 2026-10-18
base (`public_adjusted_pairs_trnear.csv`, rebuilt on the current outcome and JT01; all destinations, printed by
`public_adjusted_model.py`, `logs/adj_trnear.log`): public base 4.43, segment corrections 3.69, + public destination
factor 3.70, + per-destination 3.53 (in-sample choices). Fitting the mixture weights of the
public parts to Advan by class (`public_segment_weights.py`) remains parked.

#### Changes, 2026-10-24/25 (internal audit, three rounds): public model

| Defect | Fix | Files |
|---|---|---|
| Stage 1 setting per class chosen and scored on the same counties (4.30-4.34) | Leave-one-county-out choice within the class; nested figure reported, in-sample stated as such | `public_stage1_nested.py`, `assemble_public_by_class.py` (reads the choice) |
| Stage 2 structure chosen on the score it reported | Outer loop, 8 folds; Stage 1 and the structure chosen on the other 7 folds; full factorial of 240 + 5 rejected variants | `public_adjusted_nested.py`; `public_adjusted_model.py` split into `keys/learn/apply/cv` (identical output to 1e-15 on the old inputs) |
| Corrections compared with a base they were not learned on | Compared with the fold base (`public_foldbase`) they act on | `score_segments.py` |
| No uncertainty | County-paired bootstrap, 2,000 draws, per class and all; gap and share of the gap closed with intervals | `public_scoring.py`, `score_segments.py` |
| Share-weighted error scales with concentration | Log-ratio error beside it everywhere | `public_scoring.py` and every scorer |
| Destination sets differ; pairs outside a model's support dropped or renormalised away | Primary: all Advan destinations, model share 0 outside its support; the common set beside it; Advan share outside reported | `score_segments.py`, `public_stage1_nested.py`, `public_adjusted_nested.py` (selection on the primary metric), `public_vs_advan_compare.py` |
| LODES all jobs (JT00) | Primary jobs (JT01) in the work model (all 53 Missouri builds rebuilt) and the corrections | `public_work_model.py` (`JT`), `public_adjusted_model.py` |
| Outcome | The travel model's (`gravity_terms.travel_visits`) | `public_vs_advan_compare.py` |
| `travel_tier_pull_cv.py`: standardisation on held-out counties; 6-term pre-commuting baseline; top-3 by observed share; tier ratios collinear with the destination effects | Training-fold standardisation; the adopted 8 FACTORS; top-3 by forecast; ratios dropped, hubs the reference tier; nested guard; convergence checked from full-data start values | `travel_tier_pull_cv.py` |
| Commuting denominators counted Missouri jobs only (round 3) | Residents' primary jobs in and out of state: `free/mo_residents_od_JT01_2023.csv.gz` (no row read twice). The work model's Missouri input is unchanged row for row, so the 53 builds stand | `public_work_model.py`, `public_adjusted_model.py` |
| `public_adjusted_pairs_trnear.csv` quoted on all destinations from an ad hoc run (round 3) | `public_adjusted_model.py` prints the all-destination table by segment (`logs/adj_trnear.log`) | `public_adjusted_model.py` |
| Runs not reproducible from the scripts | Every environment setting in the docstrings and printed at start; commands in `public_commands.sh` | `public_adjusted_model.py`, `assemble_public_by_class.py`, `public_work_model.py` |

Also: `compare_shares.csv` loses the parked
`public_segment` column; the Audrain tract print in `public_adjusted_model.py` reads `od_tract_mo_2026.csv`, now
January–July. Outputs: `public_stage1_choice.csv`, `public_stage1_nested_pairs.csv`, `public_adjusted_nested_pairs.csv`,
`public_adjusted_nested_choices.csv`, `public_adjusted_nested_configs.csv`, `mo_scores_nested.csv`,
`segment_corrections_mo.pkl`, `public_model_pairs_tiers_byclass_nested.csv`, `public_adjusted_pairs_trnear.csv`; logs in `logs/`.

**Audrain's north/south split** is one tract (950100, Vandalia-Laddonia): 17.3% of its out-of-county Missouri visits
go to Marion against 1.2–4.7% from the other tracts (January–July tracts; `public_adjusted_model.py`,
`logs/adj_trnear.log`); 0.4% of its workers work there (LODES JT01, `public_work_model_pairs_v1.csv`). Its schools
(Van-Far) play in the Eastern Missouri conference with Pike, Ralls, Lincoln and Montgomery. The public tract model
gives 3.2%, 3.9% with the public destination factor (B); county-level corrections cannot move one tract.

**Athletic conferences** (datadesk visuals 34–36, Boone, Audrain, Osage; FIPS corrected: Cooper 29053, Howard 29089):
destinations within 80 miles that share a conference got more travel than the Advan-fitted model predicted, relative
to the rest (`conference_ties_test.py`; Advan-fitted model, each county held out; pooled share-weighted log ratio
+0.07 vs −0.15; actual ÷ predicted Audrain 1.13 vs 0.89, Osage 1.12 vs 0.88, Boone 0.92 vs 0.85). Conferences are assigned by enrollment and geography
and produce recurring travel and sports coverage: a central place channel between places of the same order. Statewide
test pending (school-level: MSHSAA conference and class, NCES locations, TIGER school districts).

### Changes, 2026-10-24/25 (internal audit, three rounds): travel model

| Change | Why |
|---|---|
| Primary validation is each home county held out (8 folds, seed 7), in `travel_model.py` and every travel script | The Jan–Jun → Jul–Sep split is beaten by persistence (R² 98.7% against 93.8%; error 1.46 against 2.96): it measures stability, not prediction |
| Persistence printed beside every Jul–Sep score | As above |
| R² = 1 − SSE/SST of shares, also against fixed effects only; the old "% predicted" was a squared correlation | A squared correlation ignores bias and scale; the fixed-effects-only model is no better than uniform shares (R² 0.9%) |
| Deviance labelled in-sample; top-destination ratio and big-flow scores computed on held-out predictions | The old table columns were in-sample |
| Big flows and each county's top destination selected on the FORECAST share | Selecting on the observed share biases the ratio upward (held out: 1.13× observed-selected, 1.00× forecast-selected) |
| Two-way clustered errors (home, destination) for every travel coefficient; naive Poisson and HC1 p-values removed | Pairs sharing a home or destination county are not independent |
| Distance terms centred at 25 miles, home log population at its mean | The uncentred log-distance coefficient was not an elasticity at any stated point |
| 95% bootstrap intervals over home counties for every held-out error and every difference | Differences such as 3.58 against 3.39 had no interval |
| Core terms tested as blocks; exploratory additions only through the nested guard; one-at-a-time and drop-one tests withdrawn as criteria | Selection procedure (authors) |
| Outcome `visits_statewide` (one device → person scale per month) | The county factor measured home detection (county medians 0.24–10.78) |
| Pass-through discount `road_stop_share.discount`: highway stops above the destination's own store mix, empirical-Bayes shrunken (2026-10-25) | The old code list missed convenience stores and counted every road stop as a highway stop; unshrunk pair shares are noisy where store-level samples are small |
| Commuting from LODES JT01 (primary jobs), Missouri residents' jobs in and out of state in the denominator (2026-10-25) | JT00 counts a worker once per job; Missouri-only denominators left out residents working in Kansas or Illinois |
| `od_predicted.csv`: `visits_recorded` → `visits_undiscounted` | The column was statewide-scaled, not Advan's recorded units |
| Rural home county: under 50% of 2020 population in Census urban areas, in place of RUCC nonmetro (`rural_i_x_log_dist`, `rural_i_x_log_dist_sq`; 2026-10-25) | RUCC is a commuting definition: Osage, with no urban population, was metro (Rural flag, under Current results) |
| Every travel script uses the adopted outcome and the 8 adopted terms | Several scripts used undiscounted visits, uncalibrated visits or the 6 pre-commuting terms |
| Kansas destinations quantified | Missouri-only shares understate border counties' out-of-county travel |
| Singly-constrained reference defined explicitly (`gravity_terms.SINGLY`) | Two scripts' "singly constrained" or "current" rows had become the doubly-constrained pair terms without destination effects |
| Coverage rows of the all-factors test: newsroom counties held out in 8 folds, per-county mean error on destinations with 1%+ of visits, from repository code | Matches `coverage_model.py`'s primary metric (4.54); the 2+ stories rule selected on the outcome; the earlier tables came from a scratch run or pooled scoring |

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
lobe, 24%. Month-split stability (odd vs even months, 1,653 tracts): market overlap (Jaccard) 0.78, same number of markets 74%.
Places (`place_activity_space.py`): Columbia's population is the primary activity space of 250,502 residents outside
the city at 10%+ of their regular visits (140,632 at 20%+): Boone, Callaway, Cole, Randolph, Audrain, Cooper,
Howard and two counties outside the TV market. Jefferson City 102,095 (Cole, Callaway, Moniteau, Miller, Osage); Moberly 22,355; Mexico 4,791.
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
masked before ties are scaled. The network tie is the one of the market maps after the stage-3 and round-3 changes (Revealed
media market: town travel weighted by residents, no blanket home-county outgoing tie, statewide stories out of the
ties; towns spread, destinations capped at 99, lag in km). Run: `ATTRPOP=1 REGRULE=1 BETA_IN=0.5 PUBCOL=adjusted_C OUTTAG=_pop tie_footprint.py
<region>`; settings printed at the start of every run. Month-split stability = Advan odd vs even months; accuracy = public vs
Advan; both median Jaccard overlap over the market's study towns.

Current results (2026-10-25, audit round 3; `SUMMARY=1 OUTTAG=_pop analysis/tie_footprint.py columbia`, from the
settings each run recorded: ATTRPOP=1 BETA_IN=0.5 PUBCOL=adjusted_C REGRULE=1 CAMPUS_IN=0 REHOME=1 SCORE=current
MASKHOME=1). Audit round 3 changed the tie: towns of 2+ hexagons spread by destinations and population, destinations
capped at 99, the spatial lag in km. The market's 8 study towns, network tie: accuracy (public vs Advan) median 0.505
(printed 0.51), mean 0.526; month-split stability median 0.79; travel alone 0.52. By town:

| Town | Accuracy (public vs Advan) |
|---|---:|
| Columbia | 0.14 |
| Centralia | 0.32 |
| Hallsville | 0.43 |
| Mexico | 0.47 |
| Vandalia | 0.54 |
| Belle | 0.67 |
| Linn | 0.69 |
| Ashland | 0.95 |

Month-split stability (`logs8/tie_columbia.log`): Columbia 0.92, Mexico 0.80, Linn 0.79. Columbia's 0.14 is genuine:
the public model sends Columbia's out-of-county travel to Jefferson City (public area 0.16 of Advan's).

**The drop from 0.70, isolated** (before stage 3; the isolation stands; `tie_footprint.py` diagnostics `CAMPUS_IN`, `REHOME`, `SCORE=2026-10-18`,
`MASKHOME`, `PUBFILE`). The 2026-10-18 state (public file as saved before its regeneration; campus papers counted; no
re-homing; market scored whole; home units not masked) reproduces the 2026-10-18 table: median 0.70 / mean 0.705
(published 0.70 / 0.707); Columbia 0.69, Mexico 0.46, Linn 0.68 exactly; 4 of 36 towns differ by more than 0.02. Each
change alone, from that state (36 towns, network tie):

| Change alone | Accuracy median / mean | Month-split stability median | Columbia (town) accuracy | Columbia public / Advan area |
|---|---:|---:|---:|---:|
| none (2026-10-18 state) | 0.70 / 0.705 | 0.91 | 0.69 | 1.20 |
| (1) public model file regenerated | 0.70 / 0.705 | 0.91 | 0.69 | 1.20 |
| (2) campus papers excluded | 0.70 / 0.703 | 0.91 | 0.69 | 1.20 |
| (3) two outlets re-homed | 0.70 / 0.705 | 0.91 | 0.69 | 1.20 |
| (4a) home county in every market, scored beyond it | 0.68 / 0.635 | 0.905 | 0.00 | 15.0 |
| (4b) the town's own units masked before scaling | 0.68 / 0.658 | 0.90 | 0.31 | 0.33 |
| (4a) + (4b), the scoring change in the script | 0.625 / 0.613 | 0.88 | 0.15 | 0.17 |
| all (before stage 3) | 0.61 / 0.610 | 0.88 | 0.13 | 0.16 |

Columbia–Jefferson City market (accuracy median, 2026-10-18 state -> before stage 3 -> after stage 3 -> audit round 3):
0.68 -> 0.615 -> 0.625 -> 0.505.

Cause: the scoring change (4a + 4b) accounts for 0.70 -> 0.625 of the median; the public file, campus exclusion and
re-homing move it by 0.00 alone (one market outside the TV market excepted) and 0.015 together with the scoring change. Columbia's 0.69
was an artifact of the old scoring: with home units unmasked, Columbia city was the town's busiest unit, every other
tie scaled against it, and both markets were the city and its edge (292 km2). 0.13 is not a code bug: with home masked
and the score taken beyond Boone, Advan's market beyond Boone is 518 hexagons and the public one 77. The public model
sends Columbia's out-of-county travel overwhelmingly to Jefferson City (the busiest non-home unit, 1.0; next Fulton
0.18), so two metropolitan areas outside the TV market and Moberly -- 0.70, 0.47, 0.32 of the busiest in Advan -- fall under the tie cut
of 5. Units at 0.05+ of the busiest outside Boone: Advan 37, public 6. The patterns refit (K rule, below) does not
enter the tie market: it reads the travel sources directly.

**History of the tie-market settings (2026-10-18, old scoring; figures superseded, see appendix).** Columbia's eight
towns: within-county exponent 0.5 and the regularity rule were adopted on small gains. Audrain: Vandalia's public
markets became the two Advan shows (northeast, outside the TV market, and Columbia; Vandalia now 0.55); the false
markets in the state's two largest metropolitan areas came from the 2026-10-18 public build overdrawing metros for a
small town (the two metro counties 3.3% and 11.8% of out-of-county travel against Advan's ~0.2% and ~4.5%; the
county to the northeast 2.2% against ~17%), amplified by the larger metro being one map unit. Mexico kept one false market (Jefferson City, 1.1% of observed travel): LODES gave Audrain
residents 398 jobs in Cole, 78% in "all other services" (which includes government), while Advan shows 1.4% of their
out-of-county work-behaviour visits there -- consistent with LEHD's imputed establishment assignment of state jobs to
the capital; observed LODES only within 45 miles did not remove it. Rejected: long-distance kinds in activity spaces
(create false metro markets); hexagon-level scoring of visited cells (the market is the region, not the cells).
In a farm region outside the TV market the public markets were in the right places (79-100% inside Advan's) but two
to three times too compact: regular visits there spread over rural block groups that jobs and listed destinations miss. **ADOPTED (2026-10-18):** where people live
(2020 Census block group population, CenPop2020_Mean_BG29) as a third of the within-county spread, with jobs and OSM
destinations (`ATTRPOP=1`), for every tract (a nonmetro-only rule missed two metro counties whose
residents travel like rural ones). Thresholds by density (< 50/km2, < 200/km2) were not adopted. Rerun on the current
scoring (`tie_footprint.py`, the market's 8 study towns, accuracy median / mean): population in the spread raises
accuracy from 0.45 / 0.509 to 0.51 / 0.526; the nonmetro-only rule gives 0.51 / 0.522, density thresholds 0.45 / 0.515
(50) and 0.51 / 0.530 (200). Within-county exponent, on the adopted settings: 1 gives 0.53 / 0.529, 3 gives 0.46 /
0.371, against 0.51 / 0.526 at the adopted 0.5 -- a difference of 0.003 in mean score between 1 and 0.5; not tested for
significance; adopted value kept. Without population and the regularity rule, 0.5 gives 0.40 against 0.45 at 1. The
spread's destination part from jobs only gives 0.49 / 0.509, from OpenStreetMap destinations only 0.47 / 0.504
(`SPREAD`): half each is kept. Observed LODES within 45 miles in place of 90 (regular-travel builds,
`public_model.sh` step 10, PUBFILE `public_adjusted_pairs_reg45.csv`) gives Mexico 0.48 against 0.47 and still draws
the Jefferson City false market (47 km² against 53; `DETAIL=Mexico`).

Against the conventional definitions of a local market (Missouri tracts, 2026-10-18; overlap = median Jaccard with
Advan's market; recall = share of Advan's market covered; precision = share of the definition that is Advan's market):

| Market definition | Overlap / recall / precision |
|---|---|
| Advan, odd vs even months (ceiling) | 0.78 |
| Public model | 0.53 / 83% / 66% |
| Commuting shed (LODES alone, spread by jobs) | 0.45 / 77% / 57% |
| Circle of the class's median observed area | 0.34 / 45% / 55% |
| Home county | 0.25 / 29% / 76% |

The home county — the usual unit of a local market — holds under a third of residents' regular market; the public
model holds about four-fifths of it, twice the county's overlap.

Related: Bisiani, Gulyas & Heravi (2025) derive outlets' coverage footprints from place mentions (convex hull and
radius of the top 75% of places, LSOA count, Gini, entropy, Moran's I, distance decay; six outlet types) with no test
against where audiences live or travel; this work supplies the audience side. Coverage places here are after the
grounding gate (PR #595, 2026-09-16; March corpus regrounded) -- every stored place is named in the article text.

### Information needs markets: name, certainty, minimum size (2026-10-18; evidence rerun 2026-10-25)

Named **local information needs areas** on 2026-10-18 (from "information needs market"), **civic interest areas**
from 2026-10-20 (Name: civic interest areas). Map title "<Town>'s civic interest area", no direction in the title,
numbered I, II, III only when a town has more than one. Columbia has one since 2026-10-24: "Columbia's civic interest
area" (formerly I and II). The area is the multi-part ensemble core (Revealed media market, The civic interest
area). Superseded 2026-10-25: the certainty layer of the single-drawing map (`analysis/confidence_layer.py`), which drew
the area as one connected shape; no single-drawing map is produced. `flows/pattern_halves.py` remains a check.

**Minimum size, ADOPTED (2026-10-18, unchanged):** a secondary or tertiary area needs 10%+ of the town's residents AND
1,000+ residents (`market_patterns.py`; primary always kept). Evidence, current (`analysis/market_stability.py`, the
market's 9 areas in 8 towns -- a diagnostic of one drawing, the version at the reference levels, because the ensemble
is run for the three mapped towns only; independent halves, home left out): share of drawn hexagons holding in both
halves, median 0.90; 0.87 at 500-1,000 residents (1 area), 0.78 at 1,000-2,000 (2; Linn 0.63), 0.90 at 2,000-5,000
(3), 0.93 above 5,000 (3); Spearman (residents, share) 0.66. A stability threshold is not adopted.

## Coverage model

**Adopted (2026-10-24)** (`coverage_model.py`): PPML of March story-county pairs from each newsroom county i to each
other Missouri county j, on the final `gravity_terms.py` (outcome `visits_statewide`, shrunken highway-stop discount,
commuting from residents' JT01 jobs in and out of state, 8 terms centred at 25 miles). A fixed effect for every newsroom county and every county covered, plus:

| Role | Terms | Selection |
|---|---|---|
| Core (theory) | distance block: log_dist, log_dist_sq, rural × log_dist, rural × log_dist_sq, log population × log_dist; border: adjacent; commuting block: commute_out, commute_in (`gravity_terms.FACTORS`) | Tested only as blocks, never one term at a time. Hierarchy: log_dist is kept with its square and its interactions, and the distance block enters or leaves whole |
| Travel | log visits i → j (`gravity_terms.travel_visits`, Jan–Sep 2026) where visits > 0; indicator for no recorded visits | — |
| Hypothesis term (stated in advance) | log visits × rural newsroom county (`log_visits_x_rural`; under 50% of 2020 population in Census urban areas; USDA RUCC 4–9 until 2026-10-25) | Reported whatever the result |
| Exploratory | saturation terms (`coverage_saturation_test.py`) | Adopted only if the nested guard's gain has an interval excluding zero: none adopted |

- Newsroom county: `excluded_outlets.home_fips`. The two outlets published outside the county they cover count with the
  covered county.
- `excluded_outlets.EXCLUDE` is left out (547 stories), including the 11 campus student newspapers (`CAMPUS`) and
  the two outlets filed outside Missouri (named in `analysis/excluded_outlets.py`). No
  story is dropped silently: the output lists any outlet filed outside Missouri (none remain).
- The elasticity is the percentage difference in stories associated with 1% more visits, holding the core terms and
  both sets of fixed effects fixed. It is an association, not an effect of travel on coverage.
- A story counts once for each county it names, so the pairs from one newsroom county are not independent. Errors are
  clustered by newsroom county (88 clusters).
- Held out: newsroom counties are held out in 8 folds (`gravity_terms.loco`, seed 7). The score is the mean absolute
  error of each county's out-of-county story shares, a per-county mean averaged over counties (not pooled over pairs), with a 95% interval from 1,000 county
  draws (county-paired for differences).
- **Primary metric: destinations with 1%+ of the county's visits** (1,185 pairs). These are chosen by travel, not by
  the held-out stories, and 39% of them have no stories. The all-destinations score is reported beside it but is
  dominated by zero pairs: 81% of all pairs have no stories, and their share error is near zero for any model.

### Results

| | All outlets | Print and digital |
|---|---:|---:|
| Stories / newsroom counties / out-of-county story-county pairs | 14,877 / 88 / 10,282 | 8,301 / 88 / 6,674 |
| **Elasticity, urban newsroom counties (23)** | **0.47** (s.e. 0.069; 95% CI 0.33–0.60) | **0.48** (0.086; 0.31–0.64) |
| **Elasticity, rural newsroom counties (65)** | **0.24** (s.e. 0.059; 95% CI 0.13–0.36) | **0.26** (0.058; 0.14–0.37) |
| Hypothesis term, rural − urban | −0.225 (s.e. 0.047, p < 0.001) | −0.220 (0.067, p < 0.001) |
| Twice the visits, urban / rural | 1.38 / 1.18 × the stories | 1.39 / 1.19 × |
| s.e., clustered by county pair, urban / rural (sensitivity) | 0.052 / 0.049 | 0.056 / 0.051 |
| s.e., two-way newsroom county × county covered (sensitivity) | 0.076 / 0.068 | 0.093 / 0.067 |
| s.e., HC1, pairs independent (reference only) | 0.050 / 0.047 | 0.055 / 0.049 |
| Leave one newsroom county out, urban (88 fits) | 0.417 to 0.505 | 0.405 to 0.520 |
| Leave one newsroom county out, rural | 0.209 to 0.278 | 0.202 to 0.290 |
| Pooled elasticity, no hypothesis term (sensitivity) | 0.38 (s.e. 0.060) | 0.37 (0.066) |
| Commuting in / out | +0.42 (s.e. 0.069) / −0.02 (s.e. 0.087, n.s.) | +0.36 (0.064) / −0.03 (0.084, n.s.) |
| Held-out error, primary (1%+ of visits) | 4.54 [4.09, 5.04] | 4.63 [4.18, 5.12] |
| Held-out error, all destinations | 0.922 [0.852, 0.988] | 0.947 [0.881, 1.009] |
| Fitted vs observed pairs, r² | 0.97 | 0.94 |

All rows: `coverage_model.py`.

Blocks and the hypothesis term, each left out of the adopted model (gain = error without it − adopted):

| Left out | Role | Primary: gain [95%] | All destinations: gain | Wald, clustered |
|---|---|---:|---:|---|
| Distance block (5 terms) | core | −0.125 [−0.255, −0.001] | +0.004 [−0.007, +0.016] | χ² 115.3, df 5, p < 0.001 |
| Border | core | −0.010 [−0.031, +0.011] | +0.000 [−0.002, +0.002] | χ² 3.5, df 1, p 0.061 |
| Commuting block (out + in) | core | −0.007 [−0.106, +0.087] | +0.003 [−0.008, +0.014] | χ² 46.0, df 2, p < 0.001 |
| **Log visits × rural (hypothesis)** | hypothesis | **+0.128 [+0.045, +0.213]** | −0.001 [−0.009, +0.008] | χ² 23.1, df 1, p < 0.001 |

Print and digital: distance −0.188 [−0.381, −0.010]; border −0.003 [−0.010, +0.003] (Wald p 0.79); commuting −0.009
[−0.105, +0.081]; hypothesis term +0.081 [+0.004, +0.161], all destinations −0.002 [−0.010, +0.006].

- The core terms stay in by theory. Border and commuting do not change held-out share error detectably, because the
  destination effects and visits carry the same geography. The distance block raises primary held-out error (gain
  −0.125 [−0.255, −0.001]; print −0.188 [−0.381, −0.010]) although it is jointly significant in the fit. Commuting
  is jointly significant; border is not at the 5% level (p 0.061; print 0.79).
- The hypothesis term lowers primary held-out error by 0.13 points (print 0.08), and both intervals exclude zero. On
  all destinations the gain is −0.001, a tie. Stories from rural newsroom counties are associated with visits about
  half as strongly as stories from urban ones.
- Zero-visit pairs (137, 1 story-county pair on them), urban / rural: adopted 0.466 / 0.241. With zeros at
  log(1e-3), 0.461 / 0.235; with log(visits + 1 / 10 / 100), 0.467–0.471 / 0.243–0.249; dropped, 0.465 / 0.241.
- "Travel beyond gravity", log(visits ÷ travel-model prediction), is the same quantity as log visits given the same
  terms and fixed effects (pooled 0.381 against 0.373). It is replaced by log visits.

Specifications not adopted (`coverage_model.py` prints them so earlier figures can be traced; not to be quoted).
Without the core terms, distance loads onto visits (pooled):

| Specification | All outlets | Print and digital |
|---|---:|---:|
| Fixed effects + log(1 + visits), no distance terms (`border_coverage_test.py` family) | 0.74 (s.e. 0.015) | 0.71 |
| Fixed effects + log(1 + visits) + log distance + border | 0.53 (s.e. 0.066) | 0.51 |
| Pooled, without the commuting block | 0.46 | 0.43 |
| Pooled, all core terms (sensitivity) | 0.38 | 0.37 |

### Exploratory additions: saturation (`coverage_saturation_test.py`), none adopted

Saturation hypothesis: stories follow visits less to destinations that already have their own coverage. The nested
guard works inside each of 8 outer training sets. An inner leave-county-out (7 folds) scores the adopted model
and each addition on the primary metric, and the chosen candidate scores the outer held-out counties.

| Procedure / addition, all outlets | Primary: gain [95%] | All destinations: gain | Coefficient (clustered s.e., p) |
|---|---:|---:|---|
| **Nested guard, lowest inner error** | **+0.001 [−0.016, +0.021]** | +0.001 | — |
| Nested, interval rule inside the folds | **−0.007 [−0.018, +0.002]** | −0.000 | — |
| One at a time: × destination's own stories | +0.006 [−0.013, +0.028] | +0.002 | −0.007 (0.008, p 0.38) |
| One at a time: × destination's newsrooms | −0.014 [−0.026, −0.004] | −0.001 | −0.001 (0.021, p 0.96) |
| One at a time: × destination has broadcaster | −0.002 [−0.020, +0.013] | +0.000 | −0.025 (0.030, p 0.42) |
| One at a time: × own stories, × own stories × rural home | −0.004 [−0.027, +0.022] | +0.001 | own × rural +0.000 (0.004, p 0.95) |
| One at a time: × own stories, × broadcaster | −0.001 [−0.023, +0.020] | +0.001 | — |

Print and digital: nested lowest inner error −0.001 [−0.030, +0.032]; selection rule −0.009 [−0.021, +0.002];
own stories −0.013 (p 0.12). Neither nested interval excludes zero: saturation is not supported. The level version
(rural newsrooms cover saturated centres less regardless of travel) was tested only within the all-factors model.

### Rurality and newsroom size (`coverage_newsroom_size_test.py`)

**Result: rurality is the main explanation of the coverage gap; newsroom size contributes; held-out prediction cannot
separate the two.** Rural newsroom counties have fewer and smaller newsrooms, so log visits × rural could measure
newsroom size or type instead of rurality. Newsroom-county measures, each interacted with log visits (levels absorbed
by the newsroom-county effects): log(1 + active registry outlets), has a daily, has a TV station, and, secondary
because it is built from the outcome, log(1 + March stories). Data, controls, fixed effects, clustering and held-out
scoring are `coverage_model.py`'s; all outlets.

Rural (65) / urban (23) newsroom counties: median active outlets 1 / 2; has a daily 23% / 70%; has TV 2% / 35%;
median out-of-county story pairs 33 / 170. Correlation with rural: log outlets −0.49, daily −0.43, TV −0.48, log
stories −0.54.

Interactions with log visits (clustered s.e.); held-out change = model − adopted on the primary metric, county-paired
(negative = lower error than adopted):

| Model | × rural | × log outlets | × daily | × TV | Primary | Change [95%] |
|---|---:|---:|---:|---:|---:|---:|
| **Adopted: × rural** | −0.225 (0.047) | | | | 4.543 | — |
| × log outlets | | +0.135 (0.036) | | | 4.567 | +0.024 [−0.074, +0.116] |
| × has daily | | | +0.080 (0.040) | | 4.636 | +0.093 [+0.004, +0.181] |
| × has TV | | | | +0.138 (0.043) | 4.563 | +0.021 [−0.076, +0.118] |
| × outlets + daily + TV (no rural) | | +0.111 (0.041) | +0.008 (0.038) | +0.040 (0.045) | 4.571 | +0.028 [−0.076, +0.124] |
| × rural + outlets + daily + TV | −0.166 (0.043) | +0.082 (0.033) | −0.027 (0.036) | +0.030 (0.040) | 4.525 | −0.017 [−0.072, +0.039] |

Secondary, × log stories in place of rural: +0.065 (0.014), primary 4.451, change −0.092 [−0.215, +0.013]; not used in
the combined model.

- Beside size and type, × rural keeps about three quarters of its value (−0.225 → −0.166, s.e. 0.043) and outlets
  stays (+0.082, s.e. 0.033); daily and TV add nothing once both are in. Rurality carries most of the gap; size
  contributes.
- Held out, size in place of rural (+0.028 [−0.076, +0.124]) and size beside rural (−0.017 [−0.072, +0.039]) are not
  distinguishable from the adopted model; only a daily in place of rural is worse (+0.093 [+0.004, +0.181]).
  Prediction cannot separate rurality from newsroom size.
- Full model, implied elasticity for a county with one weekly only (4 urban, 38 rural counties): urban 0.40 (0.07),
  rural 0.23 (0.06).
- Outlet as the source unit (146 outlets with out-of-county stories; outlet and destination fixed effects), rural −
  urban within type: non-daily print −0.23 (0.06), daily print −0.22 (0.06), broadcast −0.27 (0.05), each p < 0.001.
  The gap holds within outlet type.
- Matched on output (adopted model refitted on the overlap): out-of-county story pairs 5–469 (19 urban / 52 rural),
  × rural −0.142 (0.050, p 0.004); registry outlets 1–3 (16 / 65), −0.118 (0.050, p 0.017). Among counties of
  comparable output the gap is smaller and remains.
- Target counties, implied elasticity (adopted / size and type / full model): Audrain 0.24 / 0.34 / 0.24; Boone 0.47 /
  0.48 / 0.51; Osage 0.24 / 0.28 / 0.23.

### Rejected or not supported

| Tested | Result | Script |
|---|---|---|
| Separate factor lists for travel and coverage | Replaced by one shared term set (`gravity_terms.py`) | — |
| Non-bordering destinations get less coverage than travel predicts | Raw comparison, at 10%+ of visits: ring 2 and ring 3+ get 6.8% and 7.7% of story share, against 16.0% for bordering counties. Border-test specification (no distance terms, not the adopted model; clustered by newsroom county): slope difference beyond the border +0.04 (95% CI −0.04 to +0.13; print +0.07, −0.04 to +0.18), not detectable; ring 3+ level −1.23 (s.e. 0.55) | `border_coverage_test.py` |
| Saturation (above) | Nested gain intervals include zero | `coverage_saturation_test.py` |

### Changes, 2026-10-24/25 (internal audit, three rounds): coverage

| Change | Before | After |
|---|---|---|
| Visits | `od_predicted.csv` visits (county factor) | `gravity_terms.travel_visits`, the travel model's adopted outcome |
| Travel term | log(visits ÷ travel-model prediction) | log visits; identical given the same terms and fixed effects |
| Hypothesis term | — | log visits × nonmetro newsroom county (RUCC): metro 0.50, nonmetro 0.26; primary held-out gain +0.13 |
| Rural flag (2026-10-25) | USDA RUCC nonmetro (4–9) | under 50% of 2020 population in Census urban areas: log visits × rural newsroom county, urban 0.47, rural 0.24; primary held-out gain +0.13 |
| Selection | terms one at a time, in-sample p | core terms as blocks; hypothesis term reported; exploratory terms through the nested procedure only |
| Held-out scoring | 88 single-county folds; destinations with 1%+ of visits **or 2+ held-out stories**; no interval; then pooled scoring in the all-factors script (4.25) | `gravity_terms.loco` folds; per-county mean; primary = 1%+ of visits; all destinations beside; county-paired bootstrap intervals; one scoring in every script |
| Zero-visit pairs (137 fitted) | log(1e-3) = −6.9, high leverage | indicator + log visits where > 0; elasticities move ≤ 0.006 |
| Standard errors | HC1 | clustered by newsroom county; pair and two-way as sensitivity |
| HOME_COUNTY, CAMPUS | counted under the county filed; campus papers in | `home_fips`; `CAMPUS` excluded; out-of-county pairs 10,406 → 10,282 |
| Out-of-state outlets | dropped silently | The two outlets filed outside Missouri in `EXCLUDE` (2026-10-25); any outlet filed outside Missouri is listed in the output |
| `home_county_decay.py` | county-wide variant took `publisher_county` | `home_fips` (`market_patterns.home_of`). Default result 1.68 → 1.64 (s.e. 0.02), from upstream changes |

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
| Article text comparing residents' share of visits outside the county with stories reaching beyond it | Same error |
| "Visits × expected" figures from the singly-constrained model (e.g. 2.2×) | That model's held-out error is 5.84 against the adopted 3.28; the 1.6× under-prediction once given as the reason is superseded (appendix) |
| "Beyond gravity" maps | Category colours carried four model-based outcomes; unreadable as maps. The model comparison is a table (`three_counties_table.csv`) |
| Alignment maps with the home county compared | Replaced by out-of-county comparison with home and away story counts for reference |

## All marginal factors together

Spillover rows do not use the rural flag. The travel nested guard over all 24 candidates is in Travel model, Selection
(gain +0.106 [−0.045, +0.263]).

Each factor above was first tested alone. To check whether many small effects add up, every factor that showed any
effect was added at once and scored only on counties the model was not fitted on (`combined_marginal_test.py`,
`combined_all_factors_test.py`; each model's primary metric; change = with − without). Coverage: the
`coverage_model.py` specification (gravity terms + log visits + zero-visit indicator + log visits × rural newsroom
county; `excluded_outlets.EXCLUDE` incl. CAMPUS; `home_fips`); newsroom counties held out in 8
folds (seed 7); error = mean absolute share error on the destinations with 1%+ of the county's visits, per newsroom
county, averaged over counties (the declared primary metric). Spillover: `spillover_common.FINAL`, fitted on 85
outlets, scored on 94.

| Model | Travel error | Change [95%] | Coverage, all / no broadcast | Change [95%] | Spillover | Change [95%] |
|---|---:|---:|---:|---:|---:|---:|
| Adopted | 3.28 [2.96, 3.59] | | 4.54 [4.09, 5.04] / 4.63 [4.18, 5.12] | | 6.43 [5.54, 7.64] | |
| + all rejected terms | 3.10 | −0.18 [−0.40, +0.03] | 4.55 / 4.63 | +0.00 [−0.17, +0.17] / −0.00 [−0.16, +0.14] | 7.18 | +0.75 [+0.18, +1.27] |
| — spillover ridge 0.05 / 0.2 | | | | | 7.01 / 7.46 | +0.58 [−0.06, +1.27] / +1.02 [+0.11, +1.86] |
| Nested choice of travel terms | 3.17 | −0.11 [−0.26, +0.04] | | | | |
| + every rejected term incl. saturation level (coverage); every county factor (spillover) | | | 4.54 / 4.65 | −0.00 [−0.18, +0.17] / +0.01 [−0.14, +0.16] | 7.40 | +0.97 [+0.26, +1.74] |
| — spillover ridge 0.05 / 0.2 | | | | | 7.05 / 7.44 | +0.62 [−0.00, +1.28] / +1.01 [+0.12, +1.83] |
| Origin effects + every destination factor + every pair term (no destination effects) | 3.70 | +0.42 [−0.01, +0.85] | 4.55 / 4.64 | +0.01 [−0.18, +0.19] / +0.01 [−0.15, +0.16] | | |

No combination of rejected factors improves any model held out; for spillover every combination is worse. Stores, jobs,
metro and area centre do not replace each destination's measured draw: without destination effects travel error is
higher by +0.42 [−0.01, +0.85], an interval that just includes zero, and big-flow error by +0.37 [+0.06, +0.68]
(`combined_all_factors_test.py`). Earlier coverage rows (a scratch table, then pooled scoring) are superseded (appendix).

## Crossover: distinct people (adopted; revised 2026-10-24 and 10-25)

Crossover is the share of a county's residents observed outside it in a month, counted as distinct people
(`build_unique_od.py`, `crossover_compare.py` → `crossover_compare.csv`); it is the potential demand in Revealed media
market by travel pattern and not a term in the adopted spillover model. Advan reports distinct people per destination
block group by home block group; people from different home block groups are distinct, and for each home block group
the people seen in its single most-visited block group outside the county (Missouri or Kansas) are all distinct.
The independent city and its county are one unit before the left-the-county test.

**Detection test (b by 2SLS, audit round 3, 2026-10-25).** Within a county, block groups where Advan sees more
phones at home than the ACS predicts (d = own ÷ E, E = ACS population × the month's statewide units per resident) show
lower leaving rates (busiest outside block group ÷ own). Model: log leaving rate in month m2 = −b × log d in m2 +
county × month-pair effect. Same-month d shares own with the leaving rate, so log d in m2 is instrumented by log d in
another month m1 of the same block-group vintage; every ordered month pair stacked (44 pairs, 218,955 block-group
pairs), ACS-population weights, county-clustered (the independent city and its county one cluster), `build_unique_od.py`:

| Estimate | Value |
|---|---|
| **2SLS b (adopted)** | **0.621 [0.534, 0.708]** |
| Reduced form (leaving m2 on detection m1; the 2026-10-24 estimate, attenuated) | −0.510 [−0.588, −0.433] |
| First stage (detection m2 on detection m1) | +0.822 [+0.797, +0.847]; county-clustered first-stage F 4,082 |
| 2SLS by lag 1 / 2 / 3 / 4 / 5 / 6 months | 0.631 / 0.620 / 0.616 / 0.613 / 0.612 / 0.617 |
| First-stage F by lag 1 / 2 / 3 / 4 / 5 / 6 months | 9,131 / 5,489 / 3,352 / 2,689 / 1,391 / 1,575 |

The first-stage F is the county-clustered Wald F on the excluded instrument; with one endogenous regressor and one
excluded instrument it equals the Kleibergen-Paap rk Wald F, far above any weak-instrument threshold. The model is
just-identified (one excluded instrument), so no overidentification test applies.

**Homebody caveat.** b mixes two things that both raise detection and lower leaving: phantom phones homed in the
block group, and residents who stay home more (seen at home more, out less). The second biases b upward as a phantom
share — the opposite direction to the attenuation the instrument removes.

**Denominator (adopted, authors' decision 2026-10-24):** per home block group D = E × d^(1 − b)
= own^(1 − b) × E^b, b = 0.621 (D = E where own = 0; D = 0 where the block group has no ACS residents); each block
group's leavers capped at D, summed over the county, divided by the sum of D, averaged January–September.

**Bounds.** The county figure R(b) on a grid of b from 0 to 1 (step 0.01, plus b and its interval ends;
`crossover_b_grid.csv`): `dedup_bound_low` / `dedup_bound_high` = its minimum / maximum over [0, 1], `dedup_band_low` /
`dedup_band_high` = over the 95% interval of b. Sums at b = 0 and b = 1, or over Σ max(own, E) and Σ min(own, E), are
not bounds: R(b) need not be monotone in b, and capping leavers at D breaks the box argument. `crossover_compare.py`
asserts that the adopted value lies inside the grid range (114 of 114 counties) and that the grid at b reproduces it.
b = 1 and b = 0 are named sensitivity columns (b = 0 lies outside the grid range in two counties, because it keeps
block groups with no ACS residents).

| County | Calibrated, b = 0.62 (adopted) | Range over b in [0, 1] | Range over the b interval | b = 1 (sensitivity) | b = 0 (sensitivity) | Linear split, (1 − b) own + b E (sensitivity) |
|---|---:|---:|---:|---:|---:|---:|
| Audrain | 44% | 40–44% | 43–44% | 40% | 41% | 42% |
| Boone | 26% | 24–26% | 26–26% | 24% | 25% | 25% |
| Osage | 59% | 45–66% | 57–61% | 66% | 45% | 57% |

Denominators compared (Spearman across 114 counties):

| Denominator | with calibration factor | with commuters out ÷ employed (JT01) | with commuters out ÷ population |
|---|---:|---:|---:|
| Seen at home, as published (city ↔ county counted as leaving) | −0.64 | +0.54 | +0.37 |
| Seen at home, city-county unit fixed | −0.63 | +0.55 | +0.38 |
| (i) Residents in the busiest block group anywhere | −0.66 | +0.55 | +0.37 |
| (ii) Seen at home, phantom block groups at E | −0.49 | +0.51 | +0.31 |
| b = 1 (iii) E, Missouri and Kansas destinations (sensitivity) | +0.14 | +0.46 | +0.33 |
| b = 0, seen at home, Missouri and Kansas destinations (sensitivity) | −0.65 | +0.54 | +0.37 |
| **Calibrated, b = 0.62 (adopted)** | **−0.28** | **+0.53** | **+0.37** |
| Linear split (sensitivity) | −0.29 | +0.54 | +0.40 |
| Summed block-group share (replaced 2026-10-16) | −0.46 | +0.69 | +0.53 |

The adopted lower bound is above the commuting floor (employed residents working in another Missouri county ÷
population, LODES JT01: Audrain 21%, Boone 11%, Osage 31%) in 113 of 114 counties. Counting jobs in the eight
neighbouring states as well (`commute_pop_all`, `free/mo_residents_od_JT01_2023.csv.gz`): Audrain 22%, Boone 11%,
Osage 32%. The three-county and tract scripts use the calibrated denominator (old forms kept as
sensitivity columns; D per block group-month in `crossover_bg_month_mo_2026.csv`): `residents_leaving.py` Audrain 44%,
Boone 25%, Osage 59% (seen at home 41 / 24 / 45%, b = 1 40 / 24 / 66%); `residents_leaving_tracts.py`, January–July,
population-weighted conservative floor 44 / 26 / 59%; `unique_people_by_county.py`, March, Audrain → Boone 35.5%
(seen at home 34.0%, b = 1 31.8%). `unique_people_by_county.py` now sums its E and D denominators over the same block
groups the numerator uses (seen at home in the month); in March every Audrain, Boone and Osage block group with an E
is seen at home, so no figure changes. Treating block
groups as independent still gives implausible figures (90% of Audrain residents in Boone County in March), so only
the lower bound is used.

## Spillover model, current (2026-10-24)

`spillover_outlets.py`; definitions and the model procedure in `spillover_common.py`; nested guard in
`spillover_rule_selection.py`.

| | Value |
|---|---|
| Outlets with 10+ placed stories | 128 in 72 counties (27 broadcasters), 12,192 stories |
| Well collected | 95 outlets; 94 scored (Three Rivers Publishing is well collected but not fitted) |
| Fitted (well collected, 20+ placed stories, not Three Rivers Publishing) | 85 outlets, 48 counties, 24 broadcasters |
| Model | spillover ~ broadcaster + log(1 + print and digital outlets in the county) |
| Terms | hypothesis terms stated in advance (TV and radio reach beyond their county; saturation of a county's print market), reported whatever the result; not selected by any rule here |
| Primary metric | mean held-out error on the fitted outlets (each county's outlets predicted by a fit without that county); median beside. Honest error: the nested figure of the search that found the terms (search B), 6.57 / 5.50 |

| Term | Coefficient | CRV3 s.e. (cluster jackknife) | p (CRV3, t, 47 df) | CRV1 s.e. | Bootstrap 95% CI (county clusters, 1,999 draws) |
|---|---:|---:|---:|---:|---|
| Intercept | −0.812 | 0.133 | < 0.001 | 0.111 | −1.019 to −0.556 |
| Broadcaster | +0.667 | 0.148 | < 0.001 | 0.135 | +0.388 to +0.939 |
| Print and digital outlets in the county (log of 1 + count) | −0.387 | 0.124 | 0.003 | 0.089 | −0.655 to −0.232 |

Hypothesis terms, gain (held-out mean error without the term − with it, points), county-paired bootstrap 95%
interval. Folds are the counties, so they have no seed; the only randomness is the county bootstrap, shown over five
seeds (1,999 draws each):

| Term | Against | Gain | 95% interval, seeds 1–5 | Median with / without |
|---|---|---:|---|---|
| Broadcaster | print outlets only | +1.55 | +0.36/+2.70; +0.37/+2.72; +0.41/+2.67; +0.36/+2.65; +0.37/+2.69 | 4.66 / 6.55 |
| Print outlets | broadcaster only | +1.04 | +0.01/+1.92; −0.00/+1.93; −0.04/+1.88; −0.05/+1.87; −0.03/+1.92 | 4.66 / 5.11 |
| Block: both | intercept only | +1.51 | +0.31/+2.58; +0.32/+2.64; +0.35/+2.57; +0.32/+2.59; +0.27/+2.64 | 4.66 / 6.23 |

The print-outlet term's interval touches zero (lower bound −0.05 to +0.01 by seed); reported, not removed: it is a
hypothesis term.

| Model | Scored on | n | Mean | Median | Skill | OOS R² |
|---|---|---:|---:|---:|---:|---:|
| **Search that found the terms, nested (search B: broadcaster + up to 3 of 15) — honest error** | fitted (20+) | 85 | **6.57** | **5.50** | | — |
| Search A, nested (broadcaster + crowded weekly + up to 2 of 13) | fitted (20+) | 85 | 6.27 | 4.71 | | — |
| Adopted (hypothesis terms), not nested | fitted (20+) | 85 | 5.98 | 4.66 | +0.202 | +0.360 |
| Adopted | all well collected, 10+ | 94 | 6.43 | 4.81 | +0.204 | +0.350 |
| Nested guard from the hypothesis pair | fitted (20+) | 85 | 6.05 | 5.05 | | — |
| Intercept only | fitted (20+) | 85 | 7.49 | 6.23 | 0 | 0 |
| Intercept only | all well collected, 10+ | 94 | 8.08 | 6.32 | 0 | 0 |
| Broadcaster only | fitted (20+) | 85 | 7.02 | 5.11 | +0.063 | +0.129 |
| Broadcaster only | all well collected, 10+ | 94 | 7.63 | 5.35 | +0.056 | +0.117 |

The fitted model's 5.98 / 4.66 is optimistic for having searched: the honest error of the search that found its terms
is search B's nested 6.57 / 5.50.

Exploratory additions (`spillover_rule_selection.py`). Forward search from the hypothesis pair on lowest held-out mean
(ties to fewer terms) adds outlets per 10,000, border (print and digital), miles to a town of 25,000+ and crowded
weekly (5.53, not nested). Repeated inside each fold: 6.05 / 5.05. Nested guard: gain −0.07 [−0.60, +0.38] (seeds
1–5: lower bound −0.58 to −0.60): no addition adopted.

One at a time against the adopted model (descriptive; adoption only through the guard; gain = without − with):

| Candidate | Gain | 95% interval | Median with / without | Coefficient (CRV3 p; bootstrap CI) |
|---|---:|---|---|---|
| Outlets per 10,000 | +0.28 | −0.16 to +0.87 | 4.74 / 4.66 | +0.191 (< 0.001; −0.154 to +0.329) |
| Border, print and digital | +0.08 | −0.33 to +0.45 | 4.64 / 4.66 | −0.110 (0.041; −0.209 to −0.011) |
| Miles to a town of 25,000+ | +0.05 | −0.25 to +0.36 | 4.78 / 4.66 | +0.164 (0.027; +0.032 to +0.295) |
| Border, every outlet | +0.01 | −0.36 to +0.36 | 4.78 / 4.66 | −0.089 (0.050; −0.167 to −0.004) |
| All outlets | −0.09 | −0.20 to +0.02 | 4.67 / 4.66 | +0.128 (0.50; −0.266 to +0.418) |
| Crowded weekly | −0.09 | −0.27 to +0.05 | 4.65 / 4.66 | −0.200 (0.35; −0.629 to +0.184) |
| TV stations | −0.14 | −0.33 to +0.02 | 4.53 / 4.66 | +0.132 (0.53; −0.295 to +0.431) |

County and outlet figures are held out: each county's outlets predicted by the adopted model fitted without that
county; one computation feeds the county table, the sensitivity table, the chart and `spillover_quoted_rows.csv`.

| County | Actual | Expected (held out) | Stories |
|---|---:|---:|---:|
| Audrain | 19.5% | 22.5% | 123 |
| Boone | 28.7% | 26.4% | 1,152 |
| Boone, print and digital | 18.3% | 19.3% | 476 |
| Osage | 25.6% | 25.3% | 40 |

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
- **Home** (one rule for every outlet): the county the outlet is filed under (the independent city and its county one
  unit), every other county holding part of its registry city (Census 2020 base population > 0, place-in-county rows
  of `census_dl/ref/sub-est2024_29.csv`), and, for the one Missouri city with a same-named city adjoining across the
  state line, that city's county. In the TV market: Jefferson City → Cole, Callaway; Belle likewise; every outlet with
  extra home counties is printed by `analysis/spillover_outlets.py`. Other counties across the state line are home for
  no outlet (`analysis/spillover_common.py`). HOME_COUNTY outlets take only the county they cover.
- **The two outlets published outside the county they cover** are fitted with the covered county as home
  (`excluded_outlets.HOME_COUNTY`), so their border distance is 0. One registry entry holding three newspapers under one
  name stays out of the fit.
- **Not local news**: `EXCLUDE` (`spillover_common.NOT_LOCAL = EXCLUDE`): the statewide outlets, the two outlets filed
  outside Missouri and the 11 campus newspapers (`CAMPUS`) — student newspapers owned by a college or university, all
  named in `analysis/excluded_outlets.py`. Out of the outcome, the fit and every county count. University-licensed
  public broadcasters (six, KBIA among them) and the School of Journalism's community newsrooms (Columbia Missourian,
  Boone County Journal, KOMU) stay.
- **Market counts** (print and digital outlets in the county, the crowded-county test, every search candidate): pinned
  registry, status active or closed but publishing in March, not `EXCLUDE`. One rule in every script.
- **Crowded weekly** (candidate, not adopted): a print weekly (registry type print/newspaper) in a county whose market
  has a print daily and a TV station. Nine counties, Boone and Callaway among them. Seven fitted crowded weeklies,
  Boone County Journal among them (counted by `analysis/spillover_outlets.py`).
- **Border distance** (candidate, in the border form): miles from the registry point to the nearest edge of the home
  county, logged, floored at half a mile. 68 of 85 fitted outlets are at a street address, 15 at a town centroid
  (location_basis). Set to 0 for broadcasters (a station's reach is its signal, not its office) and for an outlet
  outside its home county.
- **Well collected**: March local news with body text ≥ 95%, full length (600+ characters) ≥ 80%, placed ≥ 60%.
- **Inference**: CRV3 (cluster jackknife) standard errors with t(47); CRV1 beside; county-cluster bootstrap CIs.

### Measure sensitivity (weights are definitions; this is not a selection)

Same 85 outlets, adopted terms. Each row is a different outcome, so rows compare by skill and out-of-sample R², not by
the error in points. County columns actual / held-out expected.

| Mention | Sports | Mean rate | Held-out mean | Intercept-only mean | Skill | OOS R² | Audrain | Boone | Osage |
|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| 0.25 | 1 | 21.3% | 6.76 | 8.59 | +0.213 | +0.334 | 25% / 19% | 24% / 23% | 18% / 22% |
| 0.25 | 0.5 | 17.8% | 5.62 | 7.43 | +0.244 | +0.393 | 14% / 15% | 22% / 20% | 16% / 17% |
| 0.25 | 0 | 14.2% | 5.59 | 7.25 | +0.228 | +0.404 | 2% / 11% | 20% / 18% | 14% / 12% |
| 0.5 | 1 | 29.9% | 7.32 | 9.19 | +0.204 | +0.346 | 34% / 29% | 32% / 30% | 29% / 33% |
| **0.5** | **0.5** | 24.7% | 5.98 | 7.49 | +0.202 | +0.360 | 20% / 22% | 29% / 26% | 26% / 25% |
| 0.5 | 0 | 19.6% | 6.60 | 7.96 | +0.171 | +0.320 | 5% / 16% | 26% / 23% | 22% / 17% |
| 1.0 | 1 | 47.2% | 9.91 | 12.56 | +0.212 | +0.379 | 53% / 48% | 47% / 44% | 50% / 55% |
| 1.0 | 0.5 | 38.7% | 8.01 | 9.21 | +0.129 | +0.291 | 31% / 38% | 42% / 39% | 45% / 42% |
| 1.0 | 0 | 30.3% | 9.87 | 10.57 | +0.066 | +0.168 | 10% / 28% | 37% / 33% | 40% / 29% |

Sports weight 0 removes real spillover with the errors (Audrain's was 76% Sports on the 2026-10-17 data: the Mexico
Ledger's Centralia and Community R-VI coverage).

### Search history

The hypothesis terms were first found by search (`spillover_saturation_test.py`: base broadcaster + crowded weekly,
candidates added one at a time; `spillover_nested_selection.py` repeats the search inside each fold, ties toward fewer
terms): nested A 6.27 / 4.71, nested B 6.57 / 5.50. They are now stated as hypothesis terms and reported whatever the
result; the search's nested figure is the honest error of how they were found. Single additions to broadcaster +
crowded weekly (6.98 / 5.35), mean / median: print outlets 6.07 / 4.65; miles to a town of 25,000+ 6.06 / 5.10; outlets
6.37 / 5.14; outlets per 10,000 6.54 / 5.48; TV stations 6.71 / 5.21; border, every outlet 7.10 / 5.81; border, print
and digital 6.95 / 5.32. The border form (crowded weekly + border for print and digital + print outlets, 5.92 / 4.64)
replaced the 2026-10-17 form (`spillover_common.FINAL_ALL_BORDER`, 6.02 / 5.06) under a rule fixed before the
comparison (lower mean and median), and was then replaced by the hypothesis pair.

### Robustness

Leave one TV market out (`spillover_dma_holdout.py` → `spillover_dma_holdout.csv`), adopted model, markets with 3+
fitted outlets: in sample 5.9, held out 6.2, intercept only held out 7.4; two markets do worse than intercept only.

Market position (`spillover_market_test.py`, on the border form): other outlets nearer the county line, or nearer the
neighbour the outlet is closest to, add nothing (CRV3 p 0.34–0.75) and replace the border term worse (mean 6.03–6.07
against 5.90).

Side tests of the 2026-10-17 model, rerun on the adopted model (`spillover_side_tests.py`; held-out mean miss, points):

- By outlet type: broadcasters 6.13 (24 scored outlets), print dailies 5.72 (18), print weeklies 6.64 (45), other print
  and digital 7.96 (7); all 6.43. The print-outlet term for non-weeklies only: all 7.37 (broadcasters 8.57, dailies 5.56,
  weeklies 7.54, other 6.84), coefficient −0.133 (CRV3 p 0.050): the shared form is kept.
- A print weekly alone in its county, added to the adopted model: by the registry −0.019 (p 0.89), gain −0.06 [−0.11,
  −0.03]; by the outlets collected −0.080 (p 0.53), gain −0.08 [−0.22, +0.04]; any print weekly −0.144 (p 0.17), gain
  −0.10 [−0.34, +0.11]. None adopted.
- Weeklies in a county with a daily and a TV station (7 fitted): median spillover 14.7% against 24.1% for the other
  fitted outlets. The adopted model fitted and scored on all 128 outlets, without the quality restriction: 7.48 (6.43
  on the adopted outlets); broadcaster only 8.51 (7.63).

### Outlets (actual / held-out expected, `spillover_quoted_rows.csv`)

| Outlet | Actual | Expected | Stories |
|---|---:|---:|---:|
| Boone County Journal | 14.7% | 19.3% | 138 |
| Centralia Fireside Guard | 5.0% | 19.3% | 20 |
| Columbia Daily Tribune | 16.6% | 19.3% | 86 |
| Columbia Missourian | 22.3% | 19.3% | 232 |
| The Mexico Ledger | 22.1% | 22.5% | 105 |
| Vandalia Leader | 4.2% | 22.5% | 18 |

Vandalia Leader and Centralia Fireside Guard are not well collected (5% and 0% of stories full length): actual a lower
bound.

### Changes from the 2026-10-17 model

| Change | Effect |
|---|---|
| Two outlets homed with the county they cover (`HOME_COUNTY`); both fitted | +2 fitted outlets; one becomes a crowded weekly |
| Campus newspapers out (11 outlets; 5 had 10+ stories) | −5 outlets; three of them were crowded weeklies |
| Print-outlet count: `EXCLUDE` (incl. `CAMPUS`) out; one market rule (active, or closed but publishing in March) in every script | Counts change in nine counties; the re-homed outlets counted in the county they cover |
| Crowded weekly requires a print outlet | One digital-native outlet out of the term |
| Frequency codes filled from the Missouri Official Manual 2025–2026 where blank (14 outlets; `coverage/source_frequency.csv`) | One more outlet becomes a crowded weekly |
| One home rule (city counties + the same-named city across the state line) for every outlet | 31 outlets gain home counties; 330 centred stories move to home (213 beyond the 2026-10-17 rule for that one city); 434 mention-only stories lose their mention credit |
| Selection procedure: hypothesis terms broadcaster + print outlets; exploratory additions through the nested guard | Crowded weekly and border distance not adopted (the border form was adopted 2026-10-24 under a rule fixed beforehand, then replaced) |
| Inference: CRV3 standard errors with t(47); county-cluster bootstrap | Replaces clustered z |
| County and outlet expectations held out (fit without the county) | One computation feeds the county table, the sensitivity table, the chart and `spillover_quoted_rows.csv` |
| Baselines, 10+ scoring, nested figures, quality-selection line | Reported every run |
| `spillover_outlets.csv` written once, after every column; `SPILL_DRY=1` writes nothing; weight sensitivity cannot overwrite outputs (environment weights removed) | Reproducibility |
| `spillover_saturation_test.py`: fitted set and 20-story floor of the adopted model; candidates computed once in `spillover_outlets.py` (crash on NaN cluster groups gone) | |
| `spillover_dma_holdout.py`: table from code, with intercept-only skill; written to CSV | |

Attribution of the crowded-weekly change (each step added to the previous; CRV1 clustered-t p, as run then):

| Step | Crowded weekly | p |
|---|---:|---:|
| 2026-10-17 model as logged | −0.56 | 0.008 (z) |
| + HOME_COUNTY reassignment (audit rerun) | −0.49 | 0.005 (z) |
| + market-count rule, border 0 outside home, clustered t | −0.35 | 0.002 |
| + campus newspapers out | −0.13 | 0.48 |
| + print outlets only (KC Beacon out) | −0.25 | 0.19 |
| + frequency codes filled (Cash-Book Journal in) | −0.35 | 0.040 |
| + one home rule | −0.18 | 0.31 |
| + border for print and digital only (border form) | −0.20 | 0.27 |

Frequency codes: three outlets with "Daily" in their names were checked against the Official Manual and kept as
weeklies (the Manual lists one print day each); two of them are in counties with no TV station, so their codes do not
reach the term. Codes filled where blank (`coverage/source_frequency.csv`): 13 weekly, 1 bi-weekly. Sensitivity, not
adopted: the Manual's print schedule for every outlet it lists (20 codes change; five outlets, The Mexico Ledger and
The Fulton Sun among them, change from daily to weekly, one to tri-weekly): crowded counties fall from nine to six
(Callaway and two others leave); crowded weekly −0.28 (p 0.14); held-out 5.85 / 4.54. Frequency codes are kept as
filled; moot without the crowded-weekly term. Border distance 0 for an outlet outside its home county is kept (comment
in `spillover_outlets.py`).

### Data: March enrichment re-run and Sports (2026-10-17)

**Re-run of the March enrichment.** 4,669 articles were re-enriched after five crawler fixes: the model is told where
the publication is (#736); a game is centred on the publication's own team (#738); a statewide story is filed under
its own state and state-named places stay local (#738, #739); a long partial story is enriched rather than skipped,
and the TownNews premium-content notice is removed (#739); 970 March bodies stored as ROT47 ciphertext were decoded
(#736, #737). The story map and the quality table were rebuilt from production (`coverage/rerun_2026_10_17/REPORT.md`).
ROT47 ciphertext was tested as a quality criterion and withdrawn: place enrichment read `raw`, which holds the decoded
body for the six affected outlets.

**Sports re-run.** The 1,837 enriched March Sports stories (CIN) were re-run under focus-v4, the rule that centres a
game on the publication's own team; 1,827 completed (four hang on one language-model call every run and stay unenriched). The
re-run mostly placed stories that had no centre: 679 gained one (506 home, 173 away). Of stories placed before, 23
moved away → home and 4 home → away; the away share of placed Sports stories is 18.0% for print/digital (17.0%
before) and 34.3% for broadcast (35.7%). In a sample of 45 away-centred re-run stories about 13 were the outlet's own
team centred on the game site or the opponent (Mizzou softball → Champaign, the SEC tournament → Nashville, Bunker's
archer → Dent), about 28 correct, 4 unclear (`sports_home_away_audit.py`;
`coverage/rerun_2026_10_17/sports_still_away.csv`).

**Measure history.** The 2026-10-16 measure counted any story that touched another county, so a passing mention
counted the same as a story about that county, so a small-town weekly and a regional TV station looked alike. The
Mexico Ledger had 8 of 90 stories
centred in another county and 43 that only mention one; KOMU had 83 of 263 and 36 (2026-10-16 data).

### 2026-10-17 model (replaced 2026-10-24)

Historical record; every figure in this subsection is superseded (Superseded figures). spillover ~ broadcaster + weekly
in a county with a daily and a TV station + log miles from the outlet's town to its county edge + log(1 + print and
digital outlets in the county). Fitted on well-collected outlets with 20+ placed stories; the two outlets published
outside the county they cover and one three-paper registry entry left out of the fit. Border and print-outlet terms found by
trying 11 additions on held-out error, with a nested figure reported beside it. Tests run on that model (text in git,
commit `63f915f`): a weekly alone in its county, the terms by outlet type and for non-weeklies only, and fits on all
128 outlets are rerun on the adopted model (Spillover model, current: Robustness); market position is rerun on the
border form (same section). Not rerun, their models replaced: outlet-profile terms (`spillover_profile.py`), mention
weight 0.1–1.0 under broadcaster + town population (weights are definitions: Measure sensitivity),
leave-one-market-out by weight combination (now by the adopted model: Robustness).

### Previous (2026-10-16, replaced)

Historical record on the earlier measure; every figure here is superseded. spillover ~ broadcaster + urban share +
concentration (outlet level, `spillover_outlets.py`):

| Term | Coefficient | p | Meaning |
|---|---:|---:|---|
| Broadcaster | +0.65 | < 0.001 | TV and radio cover beyond their county more |
| Urban share | −0.81 | < 0.001 | Share of the county's population in Census 2020 urban areas; outlets in urban counties stay local |
| Concentration | +1.17 | 0.12 | Sum of squared shares of residents' out-of-county visits by destination county; high where one hub takes most travel. Adopted at the authors' direction; small and not significant on its own |

Held-out error (leave one county out): broadcaster + crossover 15.6 points; + urban share 15.3; broadcaster + urban
share 15.0; + concentration 15.0 (all outlets), 14.3 → 14.1 (well-collected outlets). Crossover was dropped: with urban
share in the model it adds nothing (0.51, p = 0.42), and across counties it is not correlated with spillover.

Urban share was chosen over measures that predicted slightly better on their own (ACS foreign-born share 14.7; Civic
Information Index rent share 14.8) because those stand in for the same urban–rural difference (foreign-born and urban
share correlate 0.74); urban share names it directly.

## Crossover and spillover: correlation

Share of residents seen outside the county (crossover, `crossover_compare.csv`: `dedup_lower`, the adopted measure,
b = 0.62 by 2SLS; sensitivity at the ends of b's 95% range, `dedup_band_low` / `dedup_band_high`) against the share of
print and digital stories about another county, across counties (`collection_quality_robustness.py`, rerun 2026-10-25,
commit 8aad9c4); p from the (weighted) least-squares slope:

| Crossover | Outlets | Counties | r, unweighted (p) | r, weighted by stories (p) |
|---|---|---:|---:|---:|
| adopted (b = 0.62) | all outlets | 72 | +0.18 (0.120) | +0.17 (0.142) |
| adopted (b = 0.62) | well-collected outlets | 53 | +0.41 (0.003) | +0.40 (0.003) |
| adopted (b = 0.62) | outlets in well-collected counties | 29 | +0.40 (0.034) | +0.34 (0.067) |
| low end of b's range | all outlets | 72 | +0.20 (0.101) | +0.19 (0.114) |
| low end of b's range | well-collected outlets | 53 | +0.42 (0.002) | +0.42 (0.002) |
| low end of b's range | outlets in well-collected counties | 29 | +0.42 (0.022) | +0.37 (0.046) |
| high end of b's range | all outlets | 72 | +0.17 (0.142) | +0.16 (0.172) |
| high end of b's range | well-collected outlets | 53 | +0.39 (0.004) | +0.38 (0.005) |
| high end of b's range | outlets in well-collected counties | 29 | +0.37 (0.051) | +0.32 (0.094) |

A positive relationship appears where collection is good: well-collected outlets r +0.38 to +0.42 (p ≤ 0.005),
weighted or not, at the adopted crossover and both ends of b's range; across all outlets it is not distinguishable from
zero (r +0.16 to +0.20, p ≥ 0.10).

## Collection quality (sensitivity)

`county_collection_quality.py` (pinned registry; `EXCLUDE`, which includes `CAMPUS`, not counted as known newsrooms):
33 counties meet every test. Adopted spillover model by subset (`collection_quality_robustness.py`), held-out mean
error, coefficients with CRV3 p:

| Outlets | n (counties) | Held-out | Broadcaster | Print outlets |
|---|---|---:|---|---|
| All, 10+ | 128 (72) | 7.5 | +0.82 (< 0.001) | −0.42 (< 0.001) |
| Well-collected, 10+ | 95 (54) | 6.6 | +0.68 (< 0.001) | −0.44 (< 0.001) |
| In well-collected counties | 40 (29) | 8.9 | +0.51 (0.077) | +0.08 (0.90) |

Confirmed by the rerun of 2026-10-25 (`collection_quality_robustness.py`, after commit 8aad9c4): the subset figures
are unchanged by the crossover rebuild, because the spillover model has no crossover term.
Outlets in well-collected counties (40) are too few to estimate the model. Coverage, pooled specification (travel
beyond gravity; not the adopted urban / rural form), all newsroom counties → well-collected counties: 0.36 → 0.25
(all outlets), 0.35 → 0.26 (print and digital).

## County characteristics tested

Crossover column: the county's distinct residents seen outside it (`crossover_compare.csv` `dedup_lower`, b = 0.62) ~
log population + rural (settlement flag) + commuting share [+ one measure], OLS on the logit, each county left out;
error in points. Spillover column: the adopted model (`spillover_common.FINAL`) + one county measure, fitted on its 85
outlets, each county's 94 scored outlets held out (`spillover_common.heldout_error`; 6.43 without a measure);
coefficient p clustered by county. Coverage column: `coverage_model.py`'s primary metric (4.54). Travel: table below.

| Source | Crossover (9.8 points baseline) | Spillover (6.43) | Coverage (4.54) |
|---|---|---|---|
| ACS 2020–2024 (24 measures, `civic_variables_test.py`) | Median age alone 9.55 (p 0.11); forward selection (median age, share Black non-Hispanic) 9.4, selected on the same error | No gain: best per-capita income 6.45 | — |
| Civic Information Index 2026 (`civic_index_test.py`, `civic_index_test_v2.py`) | Active voters alone 9.70; census response rate alone 9.76 (p 0.048)* | No gain: best public-good Facebook pages 6.44 (p 0.002); several indicators chosen without seeing the held-out county 6.52 (worse) | — |
| Newsroom bylines and volume, March 2026 (`spillover_bylines_test.py`) | — | Print and digital outlets (61 fitted, 70 scored), against the adopted print-outlet term (6.59): distinct bylines 6.68 (p 0.86), local stories 6.78 (p 0.38), stories per byline 6.73; no gain. On the 43 scored outlets with half or more stories bylined (7.23): stories per byline 7.16 (p 0.16), the others worse | — |
| Census Business Dynamics Statistics, 2021–2023 average (`business_dynamics_test.py`) | Jobs created by openings per 100 jobs 9.10 (+0.31, p 0.002); turnover (openings + closings) 9.16 (p < 0.001); openings per 100 establishments 9.24 (+0.18, p 0.001); net openings 9.96 (no gain) | No gain: jobs created by openings 6.43 (p 0.09); jobs lost by closings 6.55 (worse; p 0.005) | — |
| Hospitals (`hospital_test.py`) | Has a hospital: 9.4 (−0.45, p < 0.001) | 6.44 (no gain; p 0.25) | 4.54 → 4.56 (no gain) |

\* Single indicators, each scored with the county left out. Combinations chosen by searching against the same error
are not reported. The index's journalists per 100,000 (MuckRack) is not used: newsroom staffing is measured directly
from bylines in the stories collected, and adds nothing to spillover (row above). Indicators that do not vary
across Missouri counties were excluded (the volunteer rate is one state figure, 29.8%, for every county; library visits
and mental-health providers are missing for some counties). An earlier run kept the volunteer rate: merging the independent
city with its county left a rounding difference that standardizing turned into a variable singling out that unit, and its
apparent effect (spillover 13.4 points with four indicators, 2026-10-16 model) was an artifact. With it removed and
selection made without seeing the held-out county, adding several indicators makes the adopted model's spillover
predictions worse (6.52 against 6.43).

Travel, adopted model held out (each home county left out): share-weighted error 3.28, big-flow error 3.44. Each
candidate added to the adopted set; change in held-out error [95%] (= −gain), coefficient (two-way p). All are also in the nested guard, which adopts none.

| Candidate | Weighted share error | Big-flow error | Coefficient | Script |
|---|---:|---:|---:|---|
| Median household income × distance | +0.02 [−0.00, +0.04] | +0.01 [−0.01, +0.04] | +0.014 (0.65) | `civic_variables_test.py` |
| Per-capita income × distance | +0.05 [−0.01, +0.11] | +0.04 [−0.01, +0.09] | +0.051 (0.18) | `civic_variables_test.py` |
| Median age × distance | +0.09 [−0.02, +0.20] | +0.14 [+0.04, +0.24] (worse) | +0.132 (0.009) | `civic_variables_test.py` |
| Age 65+ × distance | +0.09 [−0.03, +0.21] | +0.15 [+0.05, +0.26] (worse) | +0.151 (0.002) | `civic_variables_test.py` |
| Households with broadband × distance | +0.02 [−0.07, +0.10] | +0.00 [−0.06, +0.07] | +0.092 (0.009) | `civic_variables_test.py` |
| Mean travel time to work × distance | +0.01 [−0.04, +0.05] | +0.00 [−0.04, +0.05] | −0.042 (0.11) | `civic_variables_test.py` |
| Below poverty × distance | +0.02 [−0.00, +0.04] | +0.01 [−0.01, +0.04] | −0.014 (0.65) | `civic_variables_test.py` |
| Bachelor's degree or higher × distance | +0.00 [−0.06, +0.08] | −0.01 [−0.06, +0.05] | +0.057 (0.025) | `civic_variables_test.py` |
| In labour force × distance | +0.03 [−0.02, +0.10] | +0.04 [−0.01, +0.09] | −0.057 (0.32) | `civic_variables_test.py` |
| Owner-occupied × distance | +0.02 [−0.02, +0.06] | +0.02 [−0.01, +0.05] | +0.026 (0.36) | `civic_variables_test.py` |
| Unemployment rate × distance | no estimates in `mo_county_acs_2024.csv`; not tested | | | `civic_variables_test.py` |
| Nearest hospital county | +0.03 [+0.00, +0.05] | 3.46 against 3.44 | −0.00 (0.94) | `hospital_test.py` |
| Nearest hospital county, and when home has none | −0.05 [−0.22, +0.12] | 3.38 against 3.44 | nearest_x_none −0.32 (< 0.001) | `hospital_test.py` |

Several coefficients are clearly non-zero (median age, 65+, broadband, degree, home without a hospital) and improve
nothing held out: they describe the fit, not a transferable pattern. No candidate lowers either held-out error with an
interval excluding zero; median age and 65+ raise big-flow error.
Coverage with the hospital terms (`hospital_test.py`, coverage primary metric): all outlets 4.54 → 4.56 (change +0.02
[−0.02, +0.05]); no broadcasters 4.63 → 4.64 (change +0.00 [−0.05, +0.06]).

Hospitals: CMS Hospital General Information, general acute, critical access, children's, VA and DoD hospitals (no
psychiatric hospitals, no clinics), with Capital Region Medical Center added (it reports under MU Health Care's CMS
number since 2024): 107 hospitals in 67 counties (`build_hospitals.py`). Counties without a hospital have more
residents leaving; hospital terms do not improve held-out travel once each county's overall draw is measured
(coverage: `hospital_test.py` 4.54 → 4.56).

## Revealed media market by travel pattern (2026-10-17; K rule 2026-10-24; civic interest area 2026-10-25)

A town's revealed media market is (1) crossover of its residents into other counties, the potential demand, and (2)
spillover between the county pair in both directions, the supply. Residents do not share one travel pattern, so the
market is the most common pattern among them; secondary and tertiary patterns are separate maps. From 2026-10-20 each
mapped pattern is a **civic interest area**; this paper's area is the multi-part core of a 6,912-version ensemble of the
network-tie map (The civic interest area, below).

**Scope** (authors' decision, 2026-10-25). Civic interest areas are drawn for the Columbia–Jefferson City television
market only: its eight study towns enter the K rule and the minimum-size evidence, and areas are drawn and reported for
Columbia, Mexico and Linn. The travel, coverage and spillover models stay statewide.

**Patterns** (`flows/travel_patterns.py`). Advan Neighborhood Patterns Plus, January–July 2026 (the months on 2020
block groups): for each home block group and destination, reach = residents seen in the destination's busiest block
group / residents seen at home, mean over the months the block group is observed (50+ residents at home). A missing
home-month is missing, not zero: left out of every mean and masked in every fit and score (4 of 1,106 home-months).
Destinations: towns (2020 places), rural block groups, Missouri counties outside the TV market; own town masked. Travel
is decomposed by non-negative matrix factorization (mixed membership): each block group's travel is a weighted mix of K
recurring patterns. Final fit: lowest loss of 10 starts; masked multiplicative updates computed as the full product
less the masked cells (identical to 1e-14, ~6x faster). The patterns are fitted on the market's home counties
(Audrain, Boone, Osage; `flows/regions.json`), on Missouri destinations.

**Residents** (2026-10-24): each block group's ACS 2020–2024 population (B01003), through the calibrated
per-block-group denominator of crossover (`analysis/crossover_bg_month_mo_2026.csv`: people = devices × ACS
population / D), mean over January–July, allocated to patterns by the travel each carries and ranked: primary,
secondary, tertiary.

**K rule** (authors' decision, 2026-10-24, per town). K = the largest K (grid 1–12, extended while its last K passes;
the script stops with an error if none passes) at which every pattern passes:

| Test | Measure | Threshold |
|---|---|---|
| Town | some study town (`flows/regions.json`) for which the pattern holds 10%+ AND 1,000+ of the town's residents AND 10%+ of the town's travel (residents × reconstructed reach, the town's own units masked as on the maps), the same town for all three | 10%, 1,000, 10% |
| Stability across starts | median over 9 other starts of the pattern's matched cosine (Hungarian) to the kept, lowest-loss fit of 10 | 0.9 |
| Month-split stability | W and H refitted on odd and on even months (best of 5 starts each; odd seeds 0–4, even 100–104), each half matched to the KEPT patterns; for every kept pattern, the cosine between its odd and its even match | 0.9 |

K is selected on this odd/even split, so the areas' month-split stability below is not an independent test of K.

Result: **K = 2** (carrying towns Vandalia and Ashland: the town where the pattern holds the most residents among the
towns that pass); K = 3 fails on the odd/even months (0.87). Per town, not per market: the area rule is per town, and a
market's share depends on which home counties form it (rejected). A 5% level was rejected. Held-out month error (all
105 4 / 2 / 1 month partitions) is printed as a persistence diagnostic only and does not choose K. Every K's tests,
town by town, are in the market's `patterns.json`. K is unchanged by the disjoint seeds of audit round 3. Sensitivity
(town threshold 10 / 15 / 20% × cosine 0.85 / 0.90 / 0.95): K = 3 / 2 / 2 at every town threshold (audit round 2).
Kept fit (audit round 2): all 10 starts reach the same loss; matched cosine 1.00; kept-to-half cosines 0.99 / 0.99 and
1.00 / 1.00; odd/even 0.95 and 1.00.

| Town | Residents allocated to the area (ACS) | Share of the town's residents |
|---|---:|---:|
| Columbia (82 block groups) | 103,086 | 93% (one area) |
| Mexico (7) | 5,685 | 86% |
| Linn (1 block group, holding the town) | 1,172 | 85% |

**Market test** (`flows/market_patterns.py`). For each county in a pattern: crossover = the town's residents in the
pattern × the county's share of the pattern's travel; spillover both ways, March 2026, local outlets only, weighted as
the adopted measure (printed by `tie_footprint.py`, `logs8/tie_columbia.log`). Mexico-Boone: ~832 residents crossing,
Audrain outlets' stories about Boone 10.0%, Boone outlets' about Audrain 0.5% -- demand and one-way supply. Linn-Cole:
~289 crossing, 8.1% and 0.2%. Columbia's area is Boone-centred (Boone 45% of its travel; the next county, outside the
TV market, 6%).

**Outlet homes** (authors' decision, 2026-10-24): an outlet's home county is the county it is filed under, except two
outlets published outside the county they cover, which are homed with the covered county (`excluded_outlets.HOME_COUNTY`);
their home town for the incoming tie and the outlet circles is the covered county's seat. Neither is in the TV market.
Registry: the pinned copy (`excluded_outlets.registry()`). `EXCLUDE` (campus papers, statewide outlets and the two
outlets filed outside Missouri) is out of every coverage term.

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

  tie(H, X) = travel(H -> X) x (1 + ω (0.3 out + 0.3 in + 0.7 shared places + 0.7 shared coverage)), capped at home = 100

| Term | Measure (0-1) |
|---|---|
| travel | H's own travel to X in this market (busiest place = 1; rural block groups spread by destinations) |
| out | H's outlets' coverage located at X / their coverage of home |
| in | X's outlets' share of coverage located in H's county / H's own outlets' share |
| shared places | overlap coefficient sum_Y min(H's travel share at Y, X's outlets' coverage share at Y), third places only |
| shared coverage | overlap coefficient between H's outlets' and X's outlets' coverage, third places only |

ω is the news weight, 1 in the 2026-10-17 tie and one of the ensemble's choices (0, ½, 1, 2) since 2026-10-25. Travel
is worth more than coverage: the coverage weights sum to 2 (raised from 1 on 2026-10-17, when at 1 news ties lifted a
typical tie only 5-15% and barely showed), so at ω = 1 coverage at its strongest triples a travel tie and a place
travelled to a third as often can at most tie it. The overlaps (network closure: two places embedded in the same third
places) carry 0.7 of it, the single direct ties 0.3. A third place strengthens the pair, not itself -- Columbia
residents in Centralia, which the Mexico Ledger covers, strengthens Columbia-Mexico; Centralia's own tie is its own
travel and coverage -- so no coverage is counted twice. KRCG (registry town New Bloomfield) overlaps nearly every
town's coverage, but almost no one travels to New Bloomfield, so it stays faint: news is made there, but it is not
local to most residents. From 2026-10-17 to 10-24 the single-drawing map marked with an orange dot each hexagon where
news ties lift a tie by 10%+; the published map carries no dots. Tie values on the K = 2 patterns
(`flows/market_patterns.py`, ω = 1; shared places / shared coverage): Columbia's strongest in the market Ashland 0.36 /
0.66, New Bloomfield 0.34 / 0.66, Jefferson City 0.20 / 0.38; Mexico → Columbia 0.21 / 0.31; Linn → Columbia 0.33 /
0.13, gated out (out 0.05 + in 0.02 under 0.10); out / in Columbia → Mexico 0.01 / 0.18, Mexico → Columbia 0.10 /
0.03. Weight sensitivity, each of the four coverage weights halved and doubled, the market's 8 study towns: rank
correlation 0.978–1.000, at most 69 of 541 hexagons change band (Columbia, Mexico, Linn 0.997–1.000, at most 14 of
563), every alternative map with the adopted map's spatial lag (2026-10-25: before, the alternatives were compared
without it, 0.86–0.96).

**Areas per town** (adopted 2026-10-17, rule unchanged): a pattern is mapped as an area only if 10%+ of the town's
residents follow it AND, beyond the primary, 1,000+ residents; the primary is always kept; at most three. A stated
threshold, like the hexagon floor of 5; held-out error does not test it. The market's eight study towns, K = 6
(superseded 2026-10-24) -> current (residents ACS):

| Town | Areas | Shares, % | Residents |
|---|---|---|---|
| Columbia | 2 -> 1 | 72 / 16 -> 93 | 76,912 / 17,513 -> 103,086 |
| Mexico | 1 -> 1 | 74 -> 86 | 5,241 -> 5,685 |
| Linn | 1 -> 1 | 92 -> 85 | 1,641 -> 1,172 |
| Ashland | 2 -> 1 | 79 / 19 -> 100 | 13,219 / 3,141 -> 9,089 |
| Centralia | 2 -> 2 | 50 / 26 -> 58 / 42 | 2,937 / 1,516 -> 3,296 / 2,380 |
| Vandalia | 1 -> 1 | 88 -> 100 | 3,064 -> 3,238 |
| Hallsville | 1 -> 1 | 68 -> 64 | 1,216 -> 1,360 |
| Belle | 1 -> 1 | 100 -> 74 | 1,099 -> 965 |

Areas: 11 -> 9 in 8 towns (printed by `analysis/market_stability.py`: "areas in all: 9 in 8 towns").

### The civic interest area: the multi-part core of a 6,912-version ensemble (2026-10-25)

**Tie.** The paper's map is the network-tie area (`market_patterns.py` idx["net"]: travel × (1 + ω (0.3 out + 0.3 in +
0.7 shared places + 0.7 shared coverage)), gate, spatial lag and direction; home 100, flagged explicitly; destinations
capped at 99; the busiest place 50). Towns of 2+ hexagons are spread like rural block groups: half by OpenStreetMap
destinations ((destinations + DFLOOR) / the town's mean), half by 2020 population, the town's mean kept; a city is no
longer one value over all its hexagons. The busiest place's mean is 50 (the authors' rule); its dense hexagons rise
above it, to the cap.

**Ensemble** (`flows/area_ensemble.py`): a multiverse analysis (Steegen et al. 2016). Every version draws the map under
one combination of seven drawing choices and the news weight ω; same K, patterns and data. Full factorial: 1,728
combinations of the drawing choices (3 × 2 × 4 × 3 × 3 × 2 × 4) × 4 news weights = **6,912 versions**, weighted
equally. The reference level of each choice ("ref.") is used only by the one-drawing diagnostics and carries no extra
weight.

| Choice | Levels | n |
|---|---|---:|
| Hexagon size (grid rebuilt) | 2, 3 (ref.), 4 km | 3 |
| TRAVEL_TOP | 0.5 (busiest place 50, ref.), 1.0 | 2 |
| Dasymetric spread (rural block groups and towns) | off, DFLOOR 0.1, 0.25 (ref.), 1 | 4 |
| LAMBDA (spatial lag; rings in km) | 0, 0.25 (ref.), 0.5 | 3 |
| Display selectivity | 40, 50 (ref.), 60% | 3 |
| Distance rule (in km) | on (ref.), off | 2 |
| Reach: drawn pieces join the version's body within this distance; D90: every drawn piece starting within the town's D90 of its centre | 10, 15 (ref.), 25 km, D90 | 4 |
| News weight ω: the four news weights (out 0.3, in 0.3, shared places 0.7, shared coverage 0.7) multiplied together | 0 (travel only), ½, 1 (ref.), 2 | 4 |

The D90 level of the reach replaces the level "none", and the news weight enters as a choice (authors' decision,
2026-10-25). A full factorial weights every level of every choice equally, so the uniform weighting and the
marginal-balanced one coincide; the script checks that both give the same p. Held at their reference values: GAMMA 0.5,
the tie cut 1, the floor 5 (never binding). Every distance is in km on every grid (the lag's rings at 2.6 / 5.2 / 7.8
km, the distance rule over 10.4 km inside the TV market and 5.2 km outside, the reach). A version's 2 or 4 km hexagons
are mapped onto the published 3 km grid by fractional overlap: each 3 km hexagon takes the fraction of its area the
version draws. Check: the version at the reference levels reproduces the drawing those levels give (Jaccard 1.000).

**p** = the mean over versions: the **probability**, under equal weighting of the 6,912 versions, that the place is part
of the area -- "how likely the place is part of the area" -- conditional on the range of the choices. It is not a
confidence: it varies drawing choices and the news weight, not data; data uncertainty is month-split stability
(below). No single version is drawn or exported as a map.

**The area is multi-part** (authors' decision, 2026-10-25; `flows/area_core.py`; p ≥ 0.8 also reported): the home body
(the core piece holding home) plus every other core piece (p ≥ 0.5) of 3 or more hexagons whose nearest hexagon lies
within the town's regular-travel distance D90 of its centre of population, each outlined and labelled by its largest
town. Core specks of 1–2 hexagons leave the outline but keep their shading. A piece of 3+ hexagons beyond D90 is not a
part: it is reported as a distant tie. Reason for parts: Columbia is Mexico's dominant destination (Audrain → Boone 39%
of out-of-county visits, 43% of work-hours visits, 34% of out-commuters, LODES JT01) and lies 33.8 km (nearest
hexagons) from Mexico's home body; a rule keeping only the body would cut it out. km² on the ground: 5.85 ×
cos(latitude) / cos(38.7°) per hexagon (the hexagon plane is scaled at 38.7° N). People inside = 2020 population of the
area's hexagons (block-group population over the hexagons whose centres lie in it), by p band and split into the home
town, the other towns of 2,500+ the core takes in, and the rest -- beside the residents allocated to the area's travel
pattern (Columbia 103,086, Mexico 5,685, Linn 1,172).

**Month-split stability** (data uncertainty; not validity; K was selected on the same split): the whole network-tie
ensemble on each half of the year, each half on its own fit (W and H refitted on odd or even months, disjoint seeds,
matched to the kept patterns) and its travel: r(p) between halves over every hexagon drawn in either, and over the
contested ones (0.1 ≤ p ≤ 0.9); the mean |p_odd − p_even|; the Jaccard of the halves' p ≥ 0.5 cores. Home left out.

### The regular-travel distance D90 (2026-10-25)

`flows/regular_distance.py`: per study town, Dq = the distance from the town's **centre of population** (the
2020-population-weighted mean of its home block groups' Census population centres) within which q% of its residents'
regular travel lies. **Regular** = a destination block group seen from the home block group in all 7 months
(January–July 2026; authors' decision, 2026-10-25), tested per home block group, the patterns' home unit. Weight =
residents seen there (device home counts), summed over the months and the town's home block groups (the visit weight of
`analysis/activity_space.py`). The home block group's own row (residents seen at home) is not travel; travel inside the
town counts. Data: the January–July 2026 block-group flows the patterns are fitted on. Not adopted: regularity per town
(every destination of a large town passes). The earlier rule, 4+ of 7 months (`analysis/activity_space.py`), is shown
beside it:

| Town | Home block groups | D80 km: 4+ of 7 → 7 of 7 | D90 km | D95 km | Regular destinations |
|---|---:|---|---|---|---|
| Columbia | 82 | 37.1 → 7.4 | 103.0 → **23.9** | 165.1 → 46.2 | 31,675 → 10,619 |
| Mexico | 7 | 47.5 → 45.6 | 51.8 → **48.1** | 71.2 → 49.8 | 1,573 → 641 |
| Linn | 1 | 71.1 → 64.7 | 101.5 → **70.5** | 122.6 → 84.4 | 677 → 233 |
| Ashland | 4 | 26.7 → 24.3 | 68.4 → 31.1 | 109.4 → 59.7 | 2,053 → 942 |
| Centralia | 4 | 40.6 → 35.5 | 67.7 → 44.3 | 105.7 → 64.9 | 1,681 → 816 |
| Vandalia | 3 | 55.0 → 45.7 | 77.8 → 57.2 | 85.5 → 77.4 | 695 → 274 |
| Hallsville | 1 | 39.8 → 30.1 | 72.8 → 44.5 | 115.2 → 64.8 | 500 → 229 |
| Belle | 1 | 54.0 → 49.1 | 69.2 → 62.7 | 93.7 → 67.0 | 267 → 98 |

Under 7 of 7 every D90 is under 60 miles (97 km). Columbia's falls most (103.0 → 23.9 km): its residents' travel seen
in every month lies mostly inside the city.

**The 7-of-7 rule and detection.** Advan sees a sample of devices, so a rarely visited distant destination can fail
"every month" through detection as well as behaviour: the rule leans toward busy, nearby places. Mexico's and Linn's
areas are the same under 4+ of 7 and 7 of 7; Columbia's changes (it loses Jefferson City and Moberly; appendix).

**The limit applies to separate parts, not to the home body** (authors' decision, 2026-10-25). Columbia's home body
reaches 32.3 km from the town's centre: 18 of its 168 hexagons lie beyond 23.9 km. Clipping a continuous body at a
radius would draw an artificial edge. No body hexagon of Mexico or Linn lies beyond its D90.

Parts kept and dropped under each limit (7 of 7; 6,912 versions; distance = the part's nearest hexagon from the town's
centre):

| Area | Limit | Parts kept (km from centre) | Dropped (km from centre) | Area km² / people |
|---|---|---|---|---|
| Columbia | D80 7.4 km | -- | Jefferson City (41.2) | 979 / 161,321 |
| Columbia | **D90 23.9 km** | -- | **Jefferson City (41.2; 10 hexagons, 32,125 people)** | **979 / 161,321** |
| Columbia | D95 46.2 km | Jefferson City (41.2) | -- | 1,038 / 193,446 |
| Mexico | D80 45.6 km | Columbia (40.5), Fulton (32.3), Centralia (21.7), rural Audrain (14.0) | -- | 802 / 123,946 |
| Mexico | **D90 48.1 km** | the same | -- | **802 / 123,946** |
| Mexico | D95 49.8 km | the same | -- | 802 / 123,946 |
| Linn | D80 64.7 km | Columbia (64.0), rural Osage (16.5) | -- | 896 / 139,001 |
| Linn | **D90 70.5 km** | the same | -- | **896 / 139,001** |
| Linn | D95 84.4 km | the same | -- | 896 / 139,001 |

Jefferson City leaves Columbia's area: its nearest core hexagon lies 41.2 km from Columbia's centre, beyond 23.9 km, and
it is reported as a distant tie. Moberly forms no core part: it is drawn inside the version's area in 54% of the
versions, and its highest hexagon likelihood is 0.44. Columbia stays a part of Mexico's area (40.5 km against 48.1) and
of Linn's (64.0 km against 70.5). Towns outside the TV market lie beyond every version's area (drawn only beyond D90 or
the reach).

### Results (6,912 versions)

All figures printed by `flows/area_ensemble.py` and `flows/area_core.py` from unrounded p.

| Area | The area (parts kept): km² / people | All core hexagons (p ≥ 0.5): km² / people | People by p band: 0.5–0.8 / ≥ 0.8 | p ≥ 0.8: km² | Month-split r(p): all / contested (n) | Mean \|p_odd − p_even\| | Core Jaccard odd / even |
|---|---|---|---|---:|---|---:|---:|
| **Columbia** | 979 / 161,321 | 1,073 / 194,485 | 47,491 / 146,994 | 536 | 0.995 / 0.990 (394) | 0.014 | 0.86 |
| **Mexico** | 802 / 123,946 | 831 / 124,228 | 111,976 / 12,252 | 320 | 0.978 / 0.955 (371) | 0.030 | 0.87 |
| **Linn** | 896 / 139,001 | 955 / 139,992 | 100,435 / 39,557 | 346 | 0.895 / 0.732 (368) | 0.056 | 0.72 |

| Area | Parts (hexagons, km², km from the home body, people) | Specks left out of the outline |
|---|---|---|
| Columbia | Columbia (home) 168, 979, --, 161,321. Beyond D90, not a part: Jefferson City 10 hexagons, 59 km², 41.2 km from the centre, 32,125 | 5 (6 hexagons) |
| Mexico | Mexico (home) 109, 634, --, 15,968; **Columbia 20, 117, 33.8, 102,884**; Fulton 3, 17, 10.4, 2,065; Centralia 3, 17, 7.8, 2,925; rural Audrain 3, 17, 5.2, 104 | 4 (5 hexagons) |
| Linn | Linn (home; Jefferson City inside) 134, 785, --, 56,509; Columbia 13, 76, 36.4, 82,353; rural Osage 6, 35, 7.8, 140 | 9 (10 hexagons) |

People inside count everyone living in the area's hexagons, the destination cities included. **Mexico's Boone
hexagons: 51 likely 20%+, 24 likely 50%+ (20 of them the Columbia part, kept), 1 likely 80%+.** Linn's thin
one-block-group travel is the least stable of the three (contested r 0.732, core Jaccard 0.72).

**Towns drawn often but outside the area** (towns of 2,500+ that half or more of the versions draw somewhere, inside
their area or beyond its reach, yet with no hexagon likely 50% or more; share of versions drawing the town anywhere /
inside the version's area / its highest hexagon likelihood): Columbia -- Moberly 0.87 / 0.54 / 0.44, Centralia 0.82 /
0.54 / 0.43, Fulton 0.74 / 0.39 / 0.30, Boonville 0.73 / 0.47 / 0.37; Mexico -- Moberly 0.73 / 0.17 / 0.12; Linn --
Ashland 0.79 / 0.67 / 0.37. Towns outside the TV market drawn this often (five for Columbia, one for Linn) fall inside a
version's area in at most 14% of the versions. A town counts toward a hexagon's likelihood only where it falls inside a
version's area, and versions draw different hexagons of it (grid size, spread), so each hexagon can stay under 0.5
while the town is drawn in most versions.

**Distant ties** (share of versions drawing the town beyond their area): Columbia -- rural Monroe 0.44, Moberly 0.32,
Fulton 0.32; Mexico -- Moberly 0.42, Columbia 0.26; towns outside the TV market: three for Columbia (0.39–0.93), one for
Linn (0.68). Jefferson City, beyond Columbia's D90, is a distant tie of the core (10 hexagons likely 50%+, 32,125
people).

**The news weight alone** (each level = the 1,728 versions of the seven drawing choices; mean and largest |p_level − p|
over the hexagons either draws, home left out):

| Area | ω | Area km² / people | Parts | Mean / max \|p_level − p\| | Core Jaccard vs all | Month-split r: all / contested |
|---|---|---|---|---|---:|---|
| Columbia | 0 (travel only) | 1,049 / 162,809 | rural Boone | 0.008 / 0.09 | 0.92 | 0.995 / 0.988 |
| Columbia | ½ | 991 / 161,529 | -- | 0.003 / 0.03 | 0.99 | 0.995 / 0.989 |
| Columbia | 1 | 956 / 160,738 | -- | 0.002 / 0.02 | 0.97 | 0.995 / 0.990 |
| Columbia | 2 | 939 / 160,401 | -- | 0.009 / 0.10 | 0.94 | 0.995 / 0.990 |
| Mexico | 0 | 820 / 109,941 | Columbia (16 hexagons), rural Callaway, rural Audrain, Centralia | 0.011 / 0.09 | 0.91 | 0.975 / 0.950 |
| Mexico | ½ | 820 / 120,524 | Columbia (19), rural Callaway, rural Audrain, Fulton, Centralia | 0.004 / 0.04 | 0.98 | 0.977 / 0.953 |
| Mexico | 1 | 785 / 123,873 | Columbia (20), rural Audrain (2), Fulton, Centralia | 0.003 / 0.03 | 0.96 | 0.979 / 0.956 |
| Mexico | 2 | 738 / 129,772 | Columbia (22), rural Audrain (2), Fulton, Centralia | 0.013 / 0.10 | 0.85 | 0.981 / 0.960 |
| Linn | 0 | 931 / 146,208 | Columbia (16), rural Osage | 0.007 / 0.05 | 0.95 | 0.885 / 0.699 |
| Linn | ½ | 902 / 140,935 | Columbia (14), rural Osage | 0.002 / 0.02 | 0.98 | 0.891 / 0.721 |
| Linn | 1 | 890 / 132,531 | Columbia (12), rural Osage | 0.002 / 0.02 | 0.99 | 0.896 / 0.738 |
| Linn | 2 | 855 / 120,161 | Columbia (10), rural Osage | 0.007 / 0.06 | 0.94 | 0.904 / 0.768 |

Stronger news ties shrink every area (selectivity holds the share of ties fixed, so amplified hexagons crowd out
others) and move Mexico's area toward Columbia and Linn's away from it. Against the ω = 1 level alone, the 6,912
versions add 23 km² to Columbia's area, 17 to Mexico's and 6 to Linn's; month-split r is unchanged to the second
decimal (core Jaccard odd/even 0.88 → 0.86, 0.88 → 0.87, 0.72 → 0.72).

**Busiest hexagon instead of busiest place** (sensitivity, BUSIEST=hexagon; the 6,912 versions, regular travel 7 of 7
months, D90 limit on separate parts, multi-part rule; `flows/reach/probability_columbia_busiest_hexagon.json`, written
beside the adopted ensemble, never over it). Scaling so the busiest HEXAGON is 50 avoids the cap but lowers every other
hexagon by the busiest town's peak weight, and the floor of 5 then cuts most rural hexagons. Areas: Columbia 705 km²,
152,057 people (the home body only; Jefferson City a distant tie, 6 hexagons, 41.2 km from the centre); Mexico 273 km²,
11,871 (the home body only, no Columbia part); Linn 252 km², 36,492 (home body 117 km²; Jefferson City a part, 11
hexagons, 64 km², 32,697 people, 10.4 km from the body; three rural Osage parts; no Columbia part). All core hexagons
(p ≥ 0.5): 764 / 285 / 275 km², 176,025 / 12,068 / 36,736 people. Every hexagon of these areas lies inside the adopted
area, so the busiest-hexagon choice only removes ground: the area shrinks by 28% (Columbia), 66% (Mexico) and 72%
(Linn), and Mexico and Linn lose their Columbia parts. Not adopted: the authors' rule is the busiest place.

**Map** (`flows/market_pattern_print.html`; renders `flows/print/civic_area_<town>.png`; authors' decision,
2026-10-25): hexagons shaded by p, keyed **"How likely the place is part of the area"** (10%, 20%, 40%, 60%, 80%+, with
"under 10%" on one line), every hexagon at p ≥ 0.1 shaded; the area's parts outlined in plain mid-grey ink (#6f6d66 at
0.8; an indicator, no casing), each non-home part labelled by its largest town. Subtitle: **"Across 6,912 equally
plausible ways of drawing the map; outlined: the area, places likely 50% or more (N km²)"**. The note under the map
gives the residents and the tie; the drawing choices and the news weight, weighted equally, so that the likelihood is
conditional on that range of choices; and the rule with its limit: "... provided it starts within N km of the town's
centre -- the distance within which 90% of its residents' regular travel (places visited in every one of the seven
months) lies". No selectivity, distance rule or outline step outside the ensemble (they are in it). `?measure=lift`:
the network tie against the travel-only tie (news alone). Exports carry p and the multi-part area only:
`flows/civic_interest_areas.csv` (1,251 rows: every hexagon at p ≥ 0.1 of the three areas, with p, in_area, part,
home) and the civic grid (`areas_p`: p and the parts); p is derived from Advan travel at the hexagon level (Open:
licence).

**Rural shading, dasymetric** (adopted 2026-10-17): Advan locates travel no finer than a block group, and a rural one
covers 30-60 hexagons. Within a rural block group, travel is spread by OpenStreetMap destinations (115,453 in Missouri,
`flows/build_destinations.py`): a hexagon's weight is (destinations + 0.25) / the block group's mean of the same, so the
block group's average is kept, farmland falls and destinations rise; travel capped at 1. Towns kept one value until
audit round 3; towns of 2+ hexagons are now spread the same way, half by destinations and half by population (Tie,
above). A floor of 1 left sparse rural counties one flat band.

**Network tie, revised** (2026-10-17):
- (Removed 2026-10-24.) Home county: home outlets' market is their county, so every home-county hexagon carried their
  outgoing tie (1.0). Before, outgoing coverage was compared with the home town, and rural home-county hexagons got
  almost none.
- Shared coverage counts only places in the town's own market (travel 0.05+ of the busiest). Two newsrooms both
  reporting statewide news (the capital, the university) had tied Columbia to distant metropolitan areas outside the TV
  market.
- Spatial network effect: adjacency tie' = tie + 0.25 x ring-weighted mean of neighbours (rings 1-3 at 1/2, 1/4, 1/8),
  only where residents travel; direction x (1 + 0.5 R cos(bearing - the market's mean bearing)), R the tie-weighted
  resultant length -- a market's direction strengthens, the opposite side weakens. On a hexagon grid queen and rook
  contiguity coincide (6 neighbours).
- Gate on the shared ties: shared places and shared coverage count only when the pair already covers each other (out +
  in of 0.10+ of home). Without it, Columbia's heavy coverage of Jefferson City, where Linn residents go, tied Linn to
  Columbia although the two barely cover each other.
- Headroom: travel is scaled so a town's busiest destination is 50 (from 2026-10-24, after the town's own units are
  masked; from audit round 3 the busiest place's mean, destinations capped at 99); home stays 100. At 100 the top
  destination started at the cap and its news ties could not show (Linn's paper covering Jefferson City, Linn's busiest
  destination).
- Orange dots (2026-10-17 to 10-24, single-drawing map only): what news coverage alone adds, before the spatial effect,
  outside the home county.
- ONE SCALE (adopted 2026-10-17; replaces a TV-market frame and a zoom rule): every map is a fixed frame about 190 x 180
  km -- the size of the Columbia-Jefferson City TV market, some 12-16 counties -- centred on the town's area (the
  tie-weighted centre of its hexagons of 10+), shifted only to keep the home county in view. A three-county frame was
  too close, a 26-27-county frame too far. The TV-market outline stays as a reference line. Travel data and county
  lines cover Missouri only: across a state line the frame is blank.
- Display selectivity: each drawing shows only the hexagons holding the strongest 50% of its ties outside home (floor
  never below 5; isolated hexagons need up to twice it). Cuts the long tail so compact and diffuse areas read alike. At
  80% the floor fell to 3-4 and cut nothing. In the published map selectivity is one of the ensemble's drawing choices
  (40, 50, 60%).

**Frame and display** (adopted 2026-10-17): destinations are all of Missouri (towns and rural block groups) so travel
across a TV-market border is measured. Hexagons show at 5+ inside the TV market and 10+ outside it, so one-off distant
trips and rural destination clusters stay off. Labels: home town bold; up to 8 towns on shaded hexagons in ink; up to 4
unshaded towns of 20,000+ in small grey. The patterns use Missouri destinations only: trips into Kansas, Illinois, Iowa
and Arkansas are not in them.

**Figure** (`flows/market_pattern_print.html`; the probability map with the multi-part area outlined (Map, above); title
"<Town>'s civic interest area" since 2026-10-20, earlier "<town>'s revealed news market"): a modelled map on the
hexagon grid; one ring of empty hexagons as a border, labels never on a dark (20+) hexagon. A shaded rural block group
or tract can cover half a county; the grid marks the figure as a model.

Superseded on the way (kept in `flows/`): tract reach maps (`build_reach_map.py`, a shrunk logistic model chosen on
held-out months, corridor term adopted, direction and home-town terms no gain) and a travel x coverage interest index
(`build_interest_map.py`, w = 0.5/1/2, with road corridors from `build_transit_lines.py`).

### Changes, 2026-10-24/25: civic interest areas

| Change | Script |
|---|---|
| Columbia–Jefferson City TV market only: every default, list and loop over markets (authors' decision, 2026-10-25) | `flows/area_ensemble.py`, `flows/export_figures.py`, `flows/export_civic_grid.py`, `flows/regular_distance.py`, `analysis/market_stability.py`, `analysis/tie_footprint.py` |
| Area = ensemble core (p ≥ 0.5) kept as parts: home body + every piece of 3+ hexagons within D90; specks keep their shading, out of the outline; parts labelled by largest town; QA on the travel-only core; no single-version map or export | `flows/area_ensemble.py`, `flows/area_core.py`, `analysis/area_coverage_alignment.py`, `analysis/cin_diet.py`, `analysis/market_evidence.py`, `flows/market_pattern_print.html`, `flows/export_area_table.py`, `flows/export_civic_grid.py` |
| Regular-travel distance D80 / D90 / D95 per study town (regular = seen in all 7 months); the D90 limit on parts, not on the home body; the reach's level "none" replaced by D90 | `flows/regular_distance.py` (new), `flows/area_core.py`, `flows/area_ensemble.py`, `flows/market_pattern_print.html` |
| News weight ω (0, ½, 1, 2) as a choice: 6,912 versions; each level's core and stability reported | `flows/area_ensemble.py`, `flows/area_core.py`, `flows/market_pattern_print.html` |
| p stated as a probability under equal weighting of the versions (multiverse); key, subtitle and grey outline (#6f6d66, 0.8) | `flows/area_ensemble.py`, `flows/market_pattern_print.html`, `flows/export_area_table.py` |
| K rule per town with independent-half month-split stability; carrying town and failing test printed; sensitivity table; held-out month error a persistence diagnostic only | `flows/travel_patterns.py` |
| Residents: ACS population through the calibrated per-block-group denominator; used by the K rule's 1,000 test | `flows/travel_patterns.py` |
| Missing home-months NaN-masked in every mean, fit and score | `flows/travel_patterns.py` |
| Month-split stability on independent halves: W and H refitted per half, matched to the kept patterns (the odd fit's order had been reported as the kept order); half fits written to `patterns_halves.json` | `flows/travel_patterns.py`, `analysis/confidence_layer.py`, `flows/pattern_halves.py` (now a check) |
| Month-split stability: relabelled; disjoint seeds; r on contested hexagons and mean absolute difference; K-selection caveat | `flows/travel_patterns.py`, `analysis/confidence_layer.py`, `flows/area_ensemble.py`, `analysis/selection_sensitivity.py` |
| Town's own units masked before the busiest place is set to 50 and before county shares; town travel weighted by residents (people's visits) | `flows/market_patterns.py`, `analysis/confidence_layer.py`, `analysis/market_evidence.py` |
| Blanket home-county outgoing tie (out = 1) removed | `flows/market_patterns.py` |
| Hexagon county from the block group holding its centre | `flows/market_patterns.py` |
| Statewide / national / international stories out of the ties, as in coverage density | `flows/market_patterns.py` |
| Travel-only index (idx["travel"]) beside the network tie | `flows/market_patterns.py`, `analysis/confidence_layer.py` |
| `?measure=lift`: network tie against the travel-only tie (news alone) | `flows/market_pattern_print.html` |
| Towns spread by destinations and population; reach a drawing choice within each version; distant pieces reported as separate ties | `flows/market_patterns.py`, `flows/area_ensemble.py` |
| Home from `home_hexes_of` everywhere; destinations capped at 99 | `flows/market_patterns.py`, `analysis/tie_footprint.py`, `analysis/confidence_layer.py`, `analysis/selection_sensitivity.py`, `analysis/market_stability.py`, `analysis/market_evidence.py`, `analysis/area_coverage_alignment.py`, `flows/area_ensemble.py` |
| 2 and 4 km versions onto the 3 km grid by fractional overlap; lag rings, distance rule and reach in km | `flows/area_ensemble.py`, `flows/market_patterns.py` |
| People by p band and by town; marginal-balanced weighting checked | `flows/area_ensemble.py` |
| `pick()` stops when no K passes; the town test masks own units | `flows/travel_patterns.py` |
| News terms' cell-level effect disclosed | `analysis/confidence_layer.py`, `flows/area_ensemble.py` |
| Hexagon area corrected by latitude | `flows/area_ensemble.py`, `flows/area_core.py`, `analysis/area_coverage_alignment.py` |
| Quoted numbers printed by their scripts (Boone hexagons, area count, tie median with the settings the runs recorded, D values) | `flows/area_ensemble.py`, `flows/area_core.py`, `analysis/market_stability.py`, `analysis/tie_footprint.py` (SUMMARY=1), `flows/regular_distance.py` |
| BUSIEST=hexagon sensitivity on the 6,912 versions, to its own file (`OUT`; the adopted path refused) and its multi-part areas (`PROB`) | `flows/market_patterns.py`, `flows/area_ensemble.py`, `flows/area_core.py`, `scripts/reproduce.sh` |
| Sensitivity table of the travel-only area | `analysis/selection_sensitivity.py` |
| County-story weight per hexagon capped at the story's weight; town buffer on the km plane; people inside; "none" stated structural; QA label | `analysis/area_coverage_alignment.py`, `analysis/cin_diet.py` |
| Outlet home county by `excluded_outlets.home_fips`; home town of the two re-homed outlets = covered county's seat; pinned registry | `flows/market_patterns.py`, `analysis/tie_footprint.py`, `analysis/area_coverage_alignment.py` |
| Library cut point fixed (`if __name__ == "__main__":`) | `analysis/market_evidence.py`, `analysis/market_stability.py` |
| Tie-footprint run settings printed and documented; diagnostics CAMPUS_IN, REHOME, SCORE, MASKHOME, OUTDIR; market file no longer rewritten by a tie run | `analysis/tie_footprint.py` |
| Fast masked NMF stated in the docstring; `build_flows.py` reads the repository's `free/` | `flows/travel_patterns.py`, `flows/build_flows.py` |

### Name: civic interest areas (2026-10-20)

The local information needs areas are renamed **civic interest areas** (authors): residents' activity areas of news
interest. Map titles: "<Town>'s civic interest area", numbered I, II, III only when a town has more than one
(Columbia, one area since 2026-10-24: no numeral). Earlier sections keep the name they were written under. Units of
analysis: county -> civic interest area -> each outlet's zone of service; no statewide measure is a finding.

## Supply (QA only; next paper)

Coverage density and the balanced diet are not results of this paper. They are measured on the **travel-only core**:
the ensemble's travel-only level, news weight ω = 0 (1,728 versions; idx["travel"]: travel, spatial lag and direction,
home 100, no news term), core p_travel ≥ 0.5 under the same multi-part rule and D90 limit (home body plus every part of
3+ hexagons within D90; specks out: Columbia 2, Mexico 4, Linn 9), so that no news term shapes the area the supply is
measured in. The figures below are QA diagnostics for the next paper and are kept out of Current results
(`analysis/area_coverage_alignment.py`, `cin_diet.py`):

| Area (travel-only core, multi-part) | km² | People inside | Frequent / regular / sporadic / none (QA) | Balanced diet (QA) |
|---|---:|---:|---|---:|
| Columbia | 1,049 | 162,809 | 49 / 6 / 45 / 0 | 49% |
| Mexico | 820 | 109,941 | 35 / 4 / 61 / 0 | 12% |
| Linn | 931 | 146,208 | 34 / 6 / 60 / 0 | 28% |

"None" cannot occur: every hexagon lies in a county whose county-level stories reach all its hexagons. County-story
weight per hexagon is capped at the story's weight; statewide, national and international stories add nothing, in the
ties as in coverage density. The network-tie core against the travel-only core: Jaccard Columbia 0.93, Mexico 0.91,
Linn 0.95.

### Coverage density (2026-10-20; QA rerun 2026-10-25)

**Coverage density** (name set by the authors) is the supply into an area: for each 3 km hexagon of the footprint
(the travel-only core; every hexagon counts the same), the local news stories in a month whose
area includes it. Central focus counts 1, a mention 0.5, Sports half. A story's area follows its geographic scope (the
enrichment's scope classification): neighbourhood 3 km around its point; town the 2020 place and 3 km around it (5 km
around a point outside any town; buffers on the km plane); regional 40 km; a county-only point or a county mention the
whole county; statewide, national and international stories none. Local outlets statewide; `EXCLUDE` left out. Tiers
(authors; names from 2026-10-20, first written "daily" and "weekly"): frequent 9+ a month (2–3 a week), regular 2–8 (2–3
a month as the floor), sporadic under 2, none. `analysis/area_coverage_alignment.py` →
`analysis/area_coverage_alignment.csv`, `flows/reach/coverage_columbia.json`; map:
`market_pattern_print.html?measure=coverage` (`&cov=local` leaves out county-level stories and county mentions).

**Attribution by region size (2026-10-20, adopted).** City, county and region claims apply to the whole region,
diluted by its size (authors): weight per hexagon = story weight × (7 / the region's hexagons) ^ 0.5, full weight at 7
hexagons or fewer (a neighbourhood, a town the size of Linn). Revised the same day (authors: the square root "overvalues
mentions and county-wide coverage"; the region "looks well-covered, which it is not"): counties and regions are counted
once (alpha = 1, spread by 2020 block-group population); towns and neighbourhoods keep the square root. `ALPHA=1`
(towns also counted once) is the sensitivity. Frequent coverage barely moves with alpha (it is place-specific
reporting); the regular tier is what county-wide stories supply.

**Map (authors' decisions, 2026-10-20).** Tiers in separate colours first, then the scale stops at frequent (9+ a month) as
one colour: the volume steps above it (30–99, 100+) peaked in the population centres and showed population size.
Stories stay a monthly count, not per capita (authors). A blurred surface beneath the grid was tried and rejected (authors:
the blur "just does not work" beside the civic interest area maps; `?surface=1` keeps it): each hexagon is filled with
the continuous green (log scale, capped at 9+ a month) with white gaps; the key is a word-only gradient from "rarely"
to "several a week or more"; the subtitle keeps the tier shares. Lines step back on the coverage map (lighter grid,
county borders, home county and TV market).

### Balanced diet of civic information (2026-10-20; QA rerun 2026-10-25)

`analysis/cin_diet.py`. The ten CIN categories of the codebook (the eight critical information needs, Friedland et al.
2012, plus Civic Life and Sports). A hexagon has a **balanced diet** when any 8 of the 10 reach 1 story a month each by
coverage density (authors: "8 of 10 served, but any 8"). The coverage density map is filtered by it (authors: "volume is not
enough, balance is also required"): coverage is shaded only where the diet is balanced; elsewhere pale (`?balance=0`
turns the filter off). Sports at half weight from 2026-10-20 (authors). Outlets required for the balanced share are
computed exactly over every combination of the top 24; the earlier outlets-required calculation on volume alone
(`outlets_required.py`) is superseded: one broadcaster and one weekly cannot supply a balanced diet.
**Map: volume as colour, breadth as size (authors, 2026-10-20).** The binary balance filter was "too flat", and the shade
graded by volume × balance did not show volume without breadth. Each hexagon's colour is its stories a month; its size
is its breadth, full at 8+ of the 10 categories and shrinking to 40% with fewer, on a pale full-size grid -- a small
dark hexagon is plenty of news of a narrow kind (Moberly, Mexico, Boonville); only Columbia and Jefferson City are full
size.

## Open

- One month of coverage limits every story-count comparison; counts per county pair are small.
- Coverage: the level version of saturation is tested only within the all-factors model, not alone.
- Out-of-state travel: Kansas destinations are observed and enter crossover; the Kansas share of Audrain, Boone and
  Osage residents' travel is not yet printed. Illinois, Iowa, Arkansas, Oklahoma and Nebraska destinations are not in
  the data, so crossover is understated by an unmeasured amount where residents travel there.
- Calibration: Advan's scale is about two units per resident (statewide 1.70–2.32 by month), not one; phantom home
  block groups (3.3% of block group-months, 10.7% of devices seen at home) and under-detection at home are
  unexplained. Question for Advan.
- Crossover: b = 0.62 carries the homebody bias (residents who stay home more lower leaving as phantoms do), which
  pushes b upward; its size is not measured.
- Advan coverage varies with block-group composition (detection ×1.28 per doubling of income, ×0.87 per doubling of
  density, ×1.08 per +10 points aged 65+): the crossover and travel shares lean toward older, higher-income,
  lower-density block groups within each county (Audrain's oldest block groups are seen at more than twice the rate of
  its youngest).
- Travel: destination residuals cluster spatially (Moran's I +0.139, p 0.014): neighbouring destinations are under- or over-predicted together, a regional component the destination
  effects do not absorb; intervals do not cluster by region. The 25-mile elasticity depends on the distance form
  (quadratic −0.88, splines −0.73 and −0.64 for urban homes) although held-out error does not.
- Travel: the border block's held-out gain is not established (+0.125 [−0.105, +0.347]); kept by theory. Rural × log
  distance alone is not distinguishable from zero (p = 0.14); the distance block passes as a block.
- Coverage: the distance block's held-out gain is below zero (−0.125 [−0.255, −0.001]; print −0.188 [−0.381,
  −0.010]); kept by theory.
- Unemployment rate × distance not tested (no estimates in `mo_county_acs_2024.csv`). Athletic conferences: statewide
  test pending; the three-county figure is for Boone, Audrain and Osage only.
- Spillover: the Centralia Fireside Guard and
  Vandalia Leader have no usable spillover figure (short texts). Expectations for the 33 outlets that are not well
  collected are extrapolations. Held out, two TV markets do worse than intercept only. The
  print-outlet hypothesis term's gain interval touches zero.
- Public travel model: no setting or correction is stable for the 9-county commuter classes — the major-metro rings'
  Stage 1 choice changes with the county left out (nested 6.05 vs in-sample 5.16), the regional-hub rings' with fold 1
  (outer-loop corrections 5.76 vs 4.38 in-sample); the destination pull needs public measures beyond sales and
  population (hospital, four-year college, supercenter, interstate, lakes and parks, county seat).
- Civic interest areas: the regular-travel rule (a destination seen in all 7 months) leans toward busy, nearby places,
  because Advan's device sample can miss a rarely visited distant destination in a month. Columbia's D90 (23.9 km) and its area
  depend on the rule; Mexico's and Linn's areas do not.
- Civic interest areas: the minimum-size evidence is a one-drawing diagnostic at the reference levels; the ensemble is
  run for Columbia, Mexico and Linn only.
- Civic interest areas: p is conditional on the range of the seven drawing choices and the news weight; a wider or
  narrower range would change it. The specks rule (pieces under 3 hexagons leave the outline) is a stated threshold,
  not tested.
- Civic interest areas: the civic grid carries p, derived from Advan travel at the hexagon level, where it had held
  public Census geography only — check against the Advan licence before it ships to datadesk.
- Civic interest areas: Linn's surface is the least stable (contested r 0.732).
- Tie markets: Columbia's public market reaches 0.14 of Advan's beyond Boone (the public model sends Columbia's
  out-of-county travel to Jefferson City); with the audit-round-3 tie the network terms no longer raise accuracy over
  travel alone (market median 0.505 against 0.52). The comparison with conventional market definitions (2026-10-18)
  has not been rescored with home masked and the score taken beyond the home county.

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
  demographic measures; county per-capita income (B19301); block-group B01001, B19013, C17002.
- U.S. Census Bureau. (2025). *LEHD Origin-Destination Employment Statistics (LODES 8)*, Missouri, 2023.
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
  B19013, B19001, B15003, B25003, B08006; B01003.
- U.S. Census Bureau. (2025). *LODES 8 auxiliary origin-destination files*, 2023: IL, KS, IA, AR, OK, NE, TN, KY.
- U.S. Census Bureau. (2021). *2020 Census centers of population by census tract*, Missouri.
- Federal Highway Administration. (2024). *2022 NextGen National Household Travel Survey*, public use files v2 (trip,
  long-distance) and codebook. https://nhts.ornl.gov
- Missouri Department of Revenue. (2026). *Public taxable sales reports, 2025*: by county (DI60IT15_SLS_CNTY) and by
  county and NAICS (DI60IL08_SLS_SICCNTY). https://dor.mo.gov/public-reports
- Christaller, W. (1933/1966). *Central places in southern Germany*. Prentice-Hall.
- Reilly, W. J. (1931). *The law of retail gravitation*. Knickerbocker Press.
- Huff, D. L. (1964). Defining and estimating a trading area. *Journal of Marketing, 28*(3), 34–38.
- Yuan, Y., & Xu, Y. (2022). Modeling activity spaces using big geo-data: Progress and challenges. *Geography
  Compass*, e12663. https://doi.org/10.1111/gec3.12663
- Bisiani, S., Gulyas, A., & Heravi, B. (2025). Mapping news geography: A computational framework for classifying local
  media through geographic coverage patterns. *Computational Humanities Research 2025*, Anthology of Computers and the
  Humanities 3, 860–881. https://doi.org/10.63744/PmuIcNvSnDuo
- U.S. Census Bureau. (2025). *LODES 8 workplace area characteristics*, Missouri, 2023
  (mo_wac_S000_JT00_2023).
- U.S. Census Bureau. (2023). *County adjacency file* (county_adjacency2023).
- Schläpfer, M., et al. (2021). The universal visitation law of human mobility. *Nature, 593*, 522–527.
- Simini, F., González, M. C., Maritan, A., & Barabási, A.-L. (2012). A universal model for mobility and migration
  patterns. *Nature, 484*, 96–100.
- Friedland, L., Napoli, P., Ognyanova, K., Weil, C., & Wilson, E. J., III. (2012). *Review of the literature regarding
  critical information needs of the American public*. Federal Communications Commission.
- Steegen, S., Tuerlinckx, F., Gelman, A., & Vanpaemel, W. (2016). Increasing transparency through a multiverse
  analysis. *Perspectives on Psychological Science, 11*(5), 702–712.
- Moran, P. A. P. (1950). Notes on continuous stochastic phenomena. *Biometrika, 37*(1/2), 17–23.
- Software: Python, statsmodels, pandas, shapely, SciPy, pyosmium; D3 for figures.

## Superseded figures

Every replaced figure, with what replaced it and why. "Was" gives the earlier values in order: 2026-10-16 to 10-18,
then "audit round 1" and "audit round 2" (2026-10-24). "Now" is the current value (2026-10-25, after audit round 3
and the rural flag); "round 3 (RUCC flag)" in "Was" is the value just before the rural flag replaced RUCC nonmetro.
"Not rerun" = no replacement figure; the old one stands only as dated history. Figures for places outside the
Columbia–Jefferson City TV market are kept outside the repository; model-level statistics over all Missouri counties
stay.

| Model | Figure (where) | Was | Now | Why |
|---|---|---|---|---|
| Data | Calibration factor as the device → person scale | Median 1.94, middle 80% 1.09–3.18; Audrain 1.19–2.54, Boone 1.58–2.52, Osage 2.19–4.26; monthly medians Jan 1.78 … Sep 1.65 (audit round 1) | Kept as `factor`, not adopted; adopted `factor_statewide` 1.70–2.32 by month; trimmed Audrain 1.19–2.40, Boone 1.50–2.44, Osage 2.19–3.72 | The county factor measures home detection (county medians 0.24–10.78) |
| Data | Calibration effect on the travel model | Log-distance term −2.14 → −1.58; "still predicts 93%"; audit round 1: elasticity at 25 mi metro −0.95 → −0.89, nonmetro −0.45 → −0.46; held-out 3.29 → 3.26; audit round 2 county factor −0.904 / −0.475, error 3.28; statewide −0.978 / −0.473, error 3.31; round 3 (RUCC flag) county factor −0.906 / −0.477, error 3.25; statewide −0.983 / −0.478, error 3.28 | Urban / rural: county factor −0.855 / −0.703, error 3.30; adopted statewide scale −0.875 / −0.699, error 3.28 (Travel model, Sensitivities) | Statewide scale; centred terms; rural flag (2026-10-25) |
| Data | Calibration, other models | "Outlet model unchanged (broadcaster 0.70, crossover 1.47)"; "coverage's response to travel 0.52"; coverage metro 0.49, nonmetro 0.25 (audit round 1); metro 0.50, nonmetro 0.26 (round 3, RUCC flag) | Adopted spillover model has no travel term; coverage urban 0.47, rural 0.24 | Models replaced; rural flag (2026-10-25) |
| Data | Estimated town residents | Columbia ~107,000 / ~106,900; Mexico ~7,100 / ~7,130; Linn ~1,800 / ~1,790 | ACS population of the block groups 111,055; 6,619; 1,381 (statewide factor 102,803; 6,742; 2,802); allocated to the area 103,086; 5,685; 1,172 | The county factor carried home over-detection |
| Data | Device IDs "stable at least week to week" | 424 block groups, monthly lower in 71, 62 passing the same-scale check | Withdrawn: 376 block groups, lower in 55, 48 passing; 7 show the products' scales differ | Places merged by `PERSISTENT_ID`; cross-product scales unknown; no within-product test |
| Data | Pass-through discount | Removes 3.0% (2026-10-16); 2.3% (audit round 1); audit round 2 1.74% (county-factor weighting; 2.2% on the statewide scale; old codes 2.32%, codes fixed 3.35%, highway at the statewide norm 2.98%) | 1.81%, empirical-Bayes shrunken, `visits_statewide`-weighted (same weights: old codes 3.04%, codes fixed 4.38%, highway at the statewide norm 3.86%, own store mix unshrunk 2.23%); signed mean excess −0.02% | Convenience stores missing (2017 NAICS); every road stop counted as a highway stop; small pairs unshrunk; weights not the adopted outcome (round 3) |
| Data | Kingdom City share discounted (Audrain → Callaway) | 20% | 15.9% (adopted shrunken discount, `road_stop_share.csv`) | Discount redefined |
| Travel | Athletic conferences, actual ÷ Advan-fitted (shared vs not shared, within 80 miles) | 2026-10-18 model, in-sample: pooled log ratio +0.06 vs −0.08 ("14% more"); Audrain 1.14 vs 0.92, Osage 1.11 vs 0.95, Boone 0.89 vs 0.92 | Adopted model, held out: +0.07 vs −0.15; Audrain 1.13 vs 0.89, Osage 1.12 vs 0.88, Boone 0.92 vs 0.85 (`conference_ties_test.py`) | Adopted travel model; held out; rural flag (2026-10-25) |
| Crossover | Distinct residents seen outside, lower bound | Audrain 41%, Boone 24%, Osage 45%; audit round 2 b = 0.51: 44%, 26%, 57% (bounds 34–53%, 20–31%, 43–69%) | 44%, 26%, 59% (range over b in [0, 1]: 40–44%, 24–26%, 45–66%; over b's interval 43–44%, 26–26%, 57–61%) | Calibrated denominator, b by 2SLS; Kansas destinations; city-county unit before the leaving test |
| Crossover | Detection slope b | — | 0.51 [0.43, 0.59] (reduced form, audit round 2) → 0.621 [0.534, 0.708] (2SLS) | Reduced form attenuated by month-to-month detection noise (first stage 0.82) |
| Crossover | Bounds | — | Audit round 2: leavers ÷ Σ max(own, E) and ÷ Σ min(own, E) (e.g. Audrain 34–53%) → range of the county figure over a b grid in [0, 1] and over b's interval | R(b) need not be monotone; capping leavers at D breaks the box argument |
| Crossover | Three-county scripts | — | Audit round 2: `residents_leaving.py` Osage 57%; `unique_people_by_county.py` Audrain → Boone 36.0% → Osage 59%; 35.5% | b by 2SLS |
| Crossover | Denominators compared | — | Audit round 2: calibrated Spearman −0.37 / +0.54 / +0.37, linear split −0.38 → −0.28 / +0.53 / +0.37, linear split −0.29 | b by 2SLS; bounds over a b grid |
| Crossover | March three-county check | Audrain 42%, Boone 29%, Osage 44% | Not restated for the calibrated form; b = 1: 39%, 27%, 66% | Denominator |
| Crossover | Lower bound above commuting | 112 of 114 counties | 113 of 114 | As above; JT01 |
| Crossover | Employed residents working in another county ÷ population (LODES) | Audrain 23%, Boone 11%, Osage 33% | 21%, 11%, 31% | JT01; JT00 counted multiple jobholders twice |
| Crossover | Tract floors, population-weighted conservative | Audrain 43%, Boone 28%, Osage 50%; audit round 2 44%, 27%, 57% | 44%, 26%, 59% | January–July tracts only; calibrated denominator; JT01 |
| Data | Regular travel per tract (`directions_per_tract.py`): 1 / 2 / 3+ directions; count right, public / corrected | 8 / 29 / 63%; 77% / 78% | 8 / 30 / 63%; 78% / 77% (first direction 78% / 83%, unchanged) | January–July tracts only; 6 of 7 months |
| Travel | Share of July–September shares predicted | 93%; 94% with commuting; audit round 1: held-out R² 93.8% [92.4, 94.9], Jul–Sep stability 93.8% vs persistence 98.6%; round 3 (RUCC flag) held-out R² 93.7% [92.4, 94.9]; stability R² 93.9% vs persistence 98.7% | Held-out R² 93.7% [92.4, 94.8]; stability R² 93.8% vs persistence 98.7% | Squared correlation, not R²; the Jul–Sep split is beaten by persistence; rural flag (2026-10-25) |
| Travel | Held-out error | Audit round 1 3.26 [2.93, 3.59]; classes 3.44 / 2.83 / 3.85 / 2.47; audit round 2 3.31 [2.96, 3.64]; 3.57 / 2.87 / 3.68 / 2.45; round 3 (RUCC flag) 3.28 [2.94, 3.61]; 3.54 / 2.86 / 3.70 / 2.39 | 3.28 [2.96, 3.59]; 3.41 / 2.84 / 4.28 / 2.06 | Statewide scale; shrunken highway discount; JT01 residents' jobs in and out of state; rural flag (2026-10-25) |
| Travel | Steps table | Deviance 480M / 359M / 275M / 165M / 137M; 76% / 81% / 86% / 92% / 93%; top destination 1.63× / 1.42× / 1.22× / 1.15×; audit round 1: deviance 358.2M … 68.8M, held-out R² 64.8% … 93.8%, errors 9.62 / 7.25 / 5.79 / 5.03 / 4.24 / 3.71 / 3.26, top destination 1.15× … 1.02×, within 15% … 49%; audit round 2 246.3M … 62.0M, 72.3% … 93.7%, 8.13 … 3.31, 1.26× … 1.03×, 18% … 51%; round 3 (RUCC flag) deviance 246.1M / 184.1M / 140.2M / 103.3M / 83.8M / 69.3M / 62.0M, held-out R² 72.4% / 80.6% / 85.4% / 87.9% / 90.6% / 92.2% / 93.7%, errors 8.06 / 6.40 / 5.48 / 4.83 / 4.19 / 3.75 / 3.28, top destination 1.23× / 1.15× / 1.17× / 1.06× / 1.06× / 0.99× / 1.03×, within 18% / 28% / 32% / 37% / 39% / 43% / 49% | Steps table: 246.1M / 169.4M / 130.6M / 93.9M / 75.8M / 69.0M / 62.3M; 72.4% / 83.0% / 87.3% / 88.9% / 91.4% / 92.0% / 93.7%; 8.06 / 5.84 / 4.88 / 4.62 / 3.82 / 3.74 / 3.28; 1.23× / 1.10× / 1.11× / 1.01× / 0.99× / 0.98× / 1.00×; 18% / 30% / 37% / 38% / 39% / 41% / 49% | In-sample, observed-selected; then the second-round outcome; rural flag (2026-10-25) |
| Travel | Singly-constrained model's main destinations | Under-predicted by 1.6× (also Comparisons withdrawn); audit round 1 1.19×, held-out error 7.25; audit round 2 held-out error 6.46 against 3.31; round 3 (RUCC flag) 1.15× held out, held-out error 6.40 against 3.28 | 1.10× held out, forecast-selected; held-out error 5.84 against 3.28 | Selected on the outcome; in-sample; rural flag (2026-10-25) |
| Travel | Top destination, actual ÷ forecast | 1.15–1.2×; audit round 1 1.02× (1.11× observed-selected); round 3 (RUCC flag) 1.03× (1.13× observed-selected) | 1.00× (1.13× observed-selected) | Held out, forecast-selected; rural flag (2026-10-25) |
| Travel | Big flows | Middle 80% 0.73×–1.88×; audit round 1 483 pairs, error 3.45 [3.17, 3.74], 49% within, 0.57×–1.51×; audit round 2 484 pairs, 3.44 [3.16, 3.73], 51% [46, 55], 0.61×–1.51×; round 3 (RUCC flag) 483 pairs, 3.44 [3.16, 3.72], 49% [45, 54], 0.60×–1.51× | 485 pairs, 3.44 [3.19, 3.71], 49% [45, 53], 0.60×–1.50× | In-sample, observed-selected; second-round outcome; rural flag (2026-10-25) |
| Travel | Main destinations, actual ÷ expected | Osage → Cole 2× (singly constrained), 1.15–1.2×, 1.28 → 1.09 with commuting; Osage → Boone 1.30 → 1.64; Audrain → Boone 0.99 → 0.97; Audrain → Callaway 1.68 → 1.39; Audrain → Marion 1.83 → 2.40; Boone → Cole 0.73 → 0.70; Boone → St. Louis 1.47 → 1.33; audit round 1 held out 1.14, 1.59, 1.01, 1.30, 2.21, 0.68, 1.29; audit round 2 in-sample 1.04, 1.64, 1.02, 1.44, 2.21, 0.71, 1.28; round 3 (RUCC flag) in-sample / held out 1.05 / 1.13, 1.65 / 1.56, 1.02 / 1.03, 1.45 / 1.35, 2.20 / 2.13, 0.71 / 0.67, 1.29 / 1.29 | In-sample / held out: 1.16 / 1.22, 1.43 / 1.38, 0.97 / 0.98, 1.37 / 1.27, 2.27 / 2.22, 0.73 / 0.69, 1.26 / 1.27 | Commuting; held out; second-round outcome; rural flag (2026-10-25) |
| Travel | Coefficients and elasticities | Audit round 1: −0.887, −0.282, +0.427, −0.273, +0.160, +0.501, +0.284, +0.192; metro −0.37 / −0.89 / −1.28 / −1.67, nonmetro +0.56 / −0.46 / −1.23 / −2.00 at 10 / 25 / 50 / 100 mi; audit round 2 −0.978, −0.265, +0.505, −0.258, +0.182, +0.465, +0.284, +0.200; metro −0.49 / −0.98 / −1.35 / −1.71, nonmetro +0.49 / −0.47 / −1.20 / −1.92; round 3 (RUCC flag) −0.983, −0.265, +0.505, −0.261, +0.181, +0.464, +0.284, +0.197; metro −0.50 / −0.98 / −1.35 / −1.72, nonmetro +0.49 / −0.48 / −1.21 / −1.94 | −0.875, −0.259, +0.177 (p = 0.14), −0.210, +0.133, +0.440, +0.277, +0.189; urban −0.40 / −0.88 / −1.23 / −1.59, rural +0.16 / −0.70 / −1.35 / −2.00 at 10 / 25 / 50 / 100 mi | Second-round outcome; JT01; rural flag (2026-10-25) |
| Travel | Selection | Audit round 1 joint test: adopted vs fixed effects 16.76 → 3.26 (−13.50); drop-one gains +0.056 to +0.377; candidates same metro +0.003, nearest centre −0.014, adjacent +0.003, size × distance +0.011; nested −0.050 / −0.041, one at a time −0.051 [−0.100, −0.002]; audit round 2 blocks distance +0.994, border +0.185 [−0.048, +0.411], commuting +0.474, all +12.852; nested guard reported as change −0.061 [−0.205, +0.096] / −0.031; one at a time change −0.047; round 3 (RUCC flag) block gains distance +1.043, border +0.199 [−0.033, +0.426], commuting +0.465, all pair terms +12.756; nested guard gain +0.062 [−0.097, +0.203] / +0.031; one at a time gain +0.045 [+0.010, +0.081] | Block gains: distance +1.047, border +0.125 [−0.105, +0.347], commuting +0.457, all pair terms +12.760; nested guard gain +0.106 [−0.045, +0.263] / +0.104; one at a time gain +0.057 [+0.022, +0.092] (reference only) | Selection procedure (authors); one gain convention (round 3); rural flag (2026-10-25) |
| Travel | Commuting gains | Small rural 3.76 → 3.28, top-3 4.81 → 4.25, independent towns 3.05 → 2.79, commuter 4.13 → 3.82, hubs 2.43 → 2.11; audit round 1 all 3.71 → 3.26 (−0.45 [−0.70, −0.21]), 3.94 → 3.44, 4.86 → 4.31, 3.18 → 2.83, 4.28 → 3.85, 3.04 → 2.47; audit round 2 all 3.78 → 3.31 (−0.47 [−0.72, −0.27]); 4.06 → 3.57; top-3 4.97 → 4.36; 3.33 → 2.87; 4.22 → 3.68; 2.78 → 2.45; round 3 (RUCC flag) all 3.75 → 3.28 (−0.46 [−0.71, −0.26]); 4.02 → 3.54; top-3 4.92 → 4.34; 3.30 → 2.86; 4.21 → 3.70 (−0.51 [−1.15, +0.06]); 2.73 → 2.39 | All 3.74 → 3.28 (−0.46 [−0.68, −0.24]); 4.00 → 3.41; top-3 4.93 → 4.23; 3.26 → 2.84; 4.27 → 4.28 (+0.00 [−0.55, +0.53]); 2.69 → 2.06 | Second-round outcome; JT01; forecast-ranked top-3; rural flag (2026-10-25) |
| Travel | Commuting coefficients | +0.28 / +0.19; audit round 1 +0.284 (0.051) / +0.192 (0.036); audit round 2 +0.284 [+0.194, +0.373] / +0.200 [+0.127, +0.273]; round 3 (RUCC flag) +0.284 [+0.197, +0.371] / +0.197 [+0.125, +0.269] | +0.277 [+0.189, +0.366] / +0.189 [+0.118, +0.260] | JT01; out-of-state jobs in the denominator; rural flag (2026-10-25) |
| Travel | Driving time | Deviance 137M → 136M; Jul–Sep 93.0% → 92.3%; audit round 1 +0.07 [−0.14, +0.31]; audit round 2 +0.079 [−0.113, +0.310]; round 3 (RUCC flag) +0.078 [−0.115, +0.309] | +0.107 [−0.088, +0.329] | Held out; second-round outcome; rural flag (2026-10-25) |
| Travel | "On the way" factor | Deviance 134M; audit round 1 −0.05 [−0.27, +0.22], weighted −0.06 [−0.31, +0.19]; audit round 2 −0.055 [−0.268, +0.209]; weighted −0.075 [−0.320, +0.184]; round 3 (RUCC flag) −0.052 [−0.265, +0.204]; weighted −0.079 [−0.321, +0.177] | −0.034 [−0.241, +0.169]; weighted −0.060 [−0.310, +0.182] | As above |
| Travel | Competing destinations | −0.05 and 0.00, deviance 80.0M → 79.5M / 80.0M; audit round 1 nearest alternative −0.051 [−0.100, −0.002], −0.065 (p 0.04), "passes one at a time"; other directions −0.01 [−0.04, +0.02]; audit round 2 −0.047 [−0.085, −0.009]; other direction −0.035 [−0.069, +0.001]; round 3 (RUCC flag) −0.045 [−0.081, −0.010]; other direction −0.033 [−0.066, +0.001] | −0.057 [−0.092, −0.022], rejected by the nested guard; other direction −0.023 [−0.049, +0.003] | Nested guard; second-round outcome; rural flag (2026-10-25) |
| Travel | Fotheringham C_ij | −0.83, deviance 80.0M → 78.9M, within 46% → 44%, Osage → Cole 1.28× → 1.21×; audit round 1 −1.04, +0.02 [−0.08, +0.14]; audit round 2 −1.07; +0.031 [−0.063, +0.140]; round 3 (RUCC flag) −1.10 (p < 0.001); +0.025 [−0.070, +0.137] | −0.679 (p = 0.07); +0.047 [−0.020, +0.123] | As above |
| Travel | Area-centre and similar terms | Same metro/micro "deviance unchanged", nearest centre p 0.74, intervening "small gain", adjacent "deviance −3M"; audit round 1 +0.00 / −0.01 / +0.00 / +0.03, all four +0.05; audit round 2 +0.008 / −0.015 / −0.005 / +0.032; all four +0.034; round 3 (RUCC flag) +0.004 / −0.016 / −0.006 / +0.032; all four +0.030; same metro/micro −0.137 (p = 0.06) | +0.008 / −0.004 / +0.012 / +0.023; all four +0.059; same metro/micro −0.090 (p = 0.24) | Held out; second-round outcome; rural flag (2026-10-25) |
| Travel | Singly-constrained destination attributes | Jobs per resident p 0.44, metro p 0.27; audit round 1 jobs p 0.69, metro p 0.75, stores p 0.19; audit round 2 metro −0.08 (p 0.57), jobs p 0.71, stores +0.73 (p 0.002); not restated in round 3 | Metro −0.165 (p 0.19), jobs +0.091 (p 0.80), stores +0.659 (p 0.003) (`travel_model_compare.py`) | Two-way clustering; second-round outcome; rural flag (2026-10-25) |
| Travel | Origin-class-specific terms | Hubs 2.02 → 1.77; audit round 1 k = 4 all +0.17 [+0.00, +0.35], hubs −0.11, independent towns +0.51; k = 2 / 3 +0.08 / +0.09; audit round 2 −0.00 / +0.04 / +0.09; independent towns +0.40; round 3 (RUCC flag) −0.00 / +0.03 / +0.09 [−0.08, +0.26]; independent towns +0.39, hubs −0.32 | k = 2 / 3 / 4: +0.12 / −0.02 / +0.19 [+0.02, +0.36]; independent towns +0.38, hubs −0.06 | As above; rural flag (2026-10-25) |
| Travel | Work and non-work apart | Audit round 1 −0.00; without commuting +0.41 [+0.19, +0.65], Audrain → Marion 2.40× → 1.96×; audit round 2 +0.44 [+0.24, +0.67]; round 3 (RUCC flag) −0.00; +0.43 [+0.23, +0.66] | −0.00; +0.42 [+0.21, +0.63] | As above |
| Travel | Tier and county pull | 3.75 → 3.70 / 4.79 → 4.68; jobs pull 1.60 vs 1.39; audit round 1 pooled 3.86 / 4.80, tier pull 3.81 / 4.72, theory 4.40 / 5.28, county 3.82 / 4.70, tier + local 3.88 / 4.78; audit round 2 adopted 3.307 (small rural 3.572), nested reported as change +0.045 [−0.087, +0.199]; round 3 (RUCC flag) adopted 3.283 (small rural 3.538, top-3 4.34); nested gain −0.048 [−0.199, +0.081], small rural +0.114 [−0.017, +0.243] | `travel_tier_pull_cv.py` table: adopted 3.279 (small rural 3.406, top-3 4.23); nested gain +0.050 [−0.030, +0.130], small rural +0.045 [−0.071, +0.153]; none adopted | Held-out standardisation; 8 terms; forecast top-3; nested guard; rural flag (2026-10-25) |
| Travel | Small origins; measured draw; shrinkage | Audit round 1 3.76 vs 3.32; +0.94 / +1.33; 3.11 vs 3.05; audit round 2 3.77 vs 3.46; +0.60 / +1.18; 3.20 vs 3.14; round 3 (RUCC flag) 3.73 vs 3.43; +0.58 / +1.13; 3.16 vs 3.10 | 3.73 vs 3.41; +0.58 / +1.15; 3.19 vs 3.12 | Second-round outcome; rural flag (2026-10-25) |
| Travel | Job-hub distances | "All worse (3.93–4.60)"; audit round 1 3.40–3.48 vs 3.35; audit round 2 3.48–3.51 vs 3.47; round 3 (RUCC flag) 3.45–3.47 vs 3.44 | 3.27–3.35 vs 3.28 | As above; JT01; rural flag (2026-10-25) |
| Travel | Blend with own shares; pass-through as recorded | Audit round 1 1.51 (−0.00); 3.18 against 3.26; audit round 2 1.46; undiscounted 3.21 against 3.31; round 3 (RUCC flag) blend 1.45 | 1.46 (−0.01 [−0.03, +0.02]); undiscounted 3.21 against 3.28 | As above; rural flag (2026-10-25) |
| Travel | Sensitivities table | Audit round 2: county factor −0.904 / −0.475, 3.28; undiscounted −0.971 / −0.484, 3.21; old discount −0.963 / −0.462, 3.30; uncapped −1.051 / −0.634, 3.15 (94.5%); distinct people −0.658 / −0.567, 1.74 (89.2%); round 3 (RUCC flag) −0.906 / −0.477, 3.25; −0.972 / −0.482, 3.21; −0.964 / −0.461, 3.30; −1.057 / −0.639, 3.13 (94.6%); −0.670 / −0.619, 1.77 (88.7%); unshrunk discount −0.979 / −0.471, 3.31 | Urban / rural: county factor −0.855 / −0.703, 3.30; undiscounted −0.872 / −0.690, 3.21; old discount −0.859 / −0.690, 3.30; uncapped −0.953 / −0.799, 3.04 (94.6%); distinct people −0.662 / −0.622, 1.80 (88.5%); unshrunk discount −0.870 / −0.692, 3.31 | Shrunken discount; JT01 residents; rural flag (2026-10-25) |
| Travel | Stability and references | Audit round 1: Jul–Sep error 3.01, persistence 1.51, big flows 3.20 / 55% and 1.43 / 92%, model − persistence +1.49 [+1.20, +1.78]; destination effects + log distance 6.13 (−2.87); in-sample deviance 68.8M; audit round 2 2.95, model − persistence +1.49 [+1.17, +1.79]; 5.66; round 3 (RUCC flag) 2.94, 1.46, model − persistence +1.47 [+1.16, +1.77]; 5.63 (adopted lower by 2.35 [1.86, 2.83]); 62.0M | 2.96, 1.46, model − persistence +1.50 [+1.22, +1.78]; 5.63 (adopted lower by 2.35 [1.85, 2.87]); 62.3M | Second-round outcome; rural flag (2026-10-25) |
| Travel, coverage | Rural flag | USDA RUCC nonmetro (codes 4–9): 61 nonmetro of the 88 newsroom counties | Under 50% of 2020 population in Census urban areas: 89 rural, 26 urban counties; 65 rural, 23 urban newsroom counties (Rural flag, under Current results) | RUCC is a commuting definition: Osage (0% urban) was metro |
| Travel | Distance form (restricted cubic spline) | Round 3 (RUCC flag): change in held-out error +0.175 [−0.007, +0.384] / +0.000 [−0.154, +0.209]; 25-mile elasticity metro −0.98 / −0.83 / −0.77, nonmetro −0.48 / −0.66 / −0.24 | +0.150 [−0.084, +0.392] / −0.012 [−0.129, +0.123]; urban −0.88 / −0.73 / −0.64, rural −0.70 / −0.77 / −0.53 | Rural flag (2026-10-25) |
| Travel, coverage | Residual spatial autocorrelation (Moran's I) | Round 3 (RUCC flag): travel home-county error +0.057 (p 0.266), destination residual +0.175 (p 0.005), Audrain and Boone under-predicted +6.72 / +6.35; coverage −0.093 (p 0.265), no broadcasters −0.116 (p 0.147) | Travel +0.007 (p 0.763), destination +0.139 (p 0.014), Audrain and Boone +6.79 / +5.21; coverage −0.044 (p 0.679), no broadcasters −0.070 (p 0.425) | Rural flag (2026-10-25) |
| Travel | Singly-constrained model as the steps table's second row | Round 3 (RUCC flag): described as "+ border, rural home × distance, metro, stores" | "+ border, rural home × distance, stores" (`gravity_terms.SINGLY` has no metro term) | Label matched to the specification |
| Travel | All marginal factors | 3.58 / 3.39 / 4.04, 93.1% / 93.6% / 90.4%, within 49% / 49% / 42%, "about 5% gain with all eight"; audit round 1 3.26 / 3.15 / 3.21 / 3.84, −0.11 [−0.31, +0.10], −0.05, +0.58; audit round 2 3.31 / 3.19 / 3.25 / 3.83; −0.11 [−0.31, +0.09]; +0.53 [+0.09, +0.97]; round 3 (RUCC flag) 3.28 / 3.17 / 3.22 / 3.79; −0.12 [−0.31, +0.09]; −0.06 [−0.20, +0.10]; +0.51 [+0.09, +0.95] | 3.28 / 3.10 / 3.17 / 3.70; −0.18 [−0.40, +0.03]; −0.11 [−0.26, +0.04]; +0.42 [−0.01, +0.85] | Held out; intervals; second-round outcome; rural flag (2026-10-25) |
| Travel | County characteristics, travel column | Baseline 3.51; degree × distance 3.43; hospitals 3.48; audit round 1 baseline 3.26 / 3.45; audit round 2 baseline 3.31 / 3.44; round 3 (RUCC flag) baseline 3.28 / 3.44, median age +0.07 [+0.00, +0.14] and in labour force +0.02 [+0.00, +0.04] (worse), nearest hospital +0.01 [−0.03, +0.05], with home without one −0.05 [−0.22, +0.10] (nearest_x_none −0.29) | Baseline 3.28 / 3.44; median age +0.09 [−0.02, +0.20], in labour force +0.03 [−0.02, +0.10]; nearest hospital +0.03 [+0.00, +0.05], with home without one −0.05 [−0.22, +0.12] (nearest_x_none −0.32); County characteristics table | Jul–Sep big-flow error selected on the outcome; second-round outcome; rural flag (2026-10-25) |
| Travel | Tier sizes | Hubs 8 | Hubs 8 in `county_class_k4.csv` (114 counties); scored, 9 with the independent city (115 homes) | The independent city and its county scored apart |
| Coverage | Headline elasticity | "About 0.7–0.8% more stories per 1% more visits"; metro 0.49, nonmetro 0.25 (audit round 1); metro 0.50, nonmetro 0.26 (round 3, RUCC flag) | Urban 0.47, rural 0.24 | No distance terms: distance loaded onto visits; rural flag (2026-10-25) |
| Coverage | Response to travel (calibration; commuting) | 0.52; "falls from 0.52 to 0.36"; twice the travel → 1.4×, then 1.3×; round 3 (RUCC flag) metro 0.50 (1.42×), nonmetro 0.26 (1.19×); pooled 0.37 | Urban 0.47 (1.38×), rural 0.24 (1.18×); pooled 0.38 | Log distance + border only; log visits; hypothesis term; rural flag (2026-10-25) |
| Coverage | Elasticities | Audit round 1: metro 0.49 (0.066; 0.36–0.62), nonmetro 0.25 (0.061; 0.13–0.37); print 0.51 / 0.25; difference −0.235 (0.039); 1.40× / 1.19×; leave-one-out 0.45–0.53; pooled 0.36 (0.060); audit round 2 0.49 (0.070; 0.36–0.63), 0.25 (0.063; 0.13–0.38); print 0.52 / 0.26; −0.241 (0.040); 1.41× / 1.19×; 0.46–0.54; pooled 0.36 (0.064); round 3 (RUCC flag) 0.50 (0.067; 0.37–0.63), 0.26 (0.061; 0.14–0.38); print 0.52 / 0.26; −0.244 (0.040); 1.42× / 1.19×; leave one out 0.47–0.54; pooled 0.37 (0.061) | Urban 0.47 (0.069; 0.33–0.60), rural 0.24 (0.059; 0.13–0.36); print 0.48 / 0.26; −0.225 (0.047); 1.38× / 1.18×; leave one out 0.417–0.505; pooled 0.38 (0.060) | Second-round outcome; rural flag (2026-10-25) |
| Coverage | Commuting terms | In +0.51 (p < 0.001), out +0.04; audit round 1 in +0.42 (0.073), out −0.02; audit round 2 in +0.41 (0.073), out −0.03; round 3 (RUCC flag) in +0.41 (0.072), out −0.04 (0.085) | In +0.42 (0.069), out −0.02 (0.087) | Adopted specification; JT01; rural flag (2026-10-25) |
| Coverage | Held-out error | 4.15 → 4.12; audit round 1 0.913 [0.844, 0.982] / 4.42 [4.00, 4.91] (print 0.939 / 4.53); audit round 2 4.49 [4.04, 4.98] (print 4.59); all destinations 0.915 (print 0.941); round 3 (RUCC flag) primary 4.46 [4.02, 4.93] (print 4.56); all destinations 0.915 (print 0.942) | Primary 4.54 [4.09, 5.04] (print 4.63), per-county mean over 8 folds; all destinations 0.922 (print 0.947) | Destination set chosen partly by the held-out stories; loco folds; second-round outcome; rural flag (2026-10-25) |
| Coverage | Primary destination set; excluded stories | — | Audit round 2 1,174 pairs; 498 stories in `EXCLUDE` → 1,185 pairs; 547 stories (the two out-of-state outlets added) | Outcome; exclusions |
| Coverage | Hypothesis term (nonmetro → rural interaction) | Audit round 1: adopted on held-out error, change −0.143 [−0.221, −0.068] vs pooled; audit round 2 gain +0.125 [+0.048, +0.202] (print +0.090); round 3 (RUCC flag) gain +0.125 [+0.048, +0.203] (print +0.088) | Hypothesis term log visits × rural, gain +0.128 [+0.045, +0.213] (print +0.081) | Selection procedure; rural flag (2026-10-25) |
| Coverage | Saturation | Response 0.67 → 0.50, p 0.004 / < 0.001, "real and in the predicted direction"; audit round 1 own stories −0.007 (p 0.34), changes ≤ 0.021; audit round 2 nested guard reported as change +0.011 [−0.005, +0.027]; own stories −0.006 (p 0.43); round 3 (RUCC flag) nested guard gain −0.010 [−0.024, +0.004]; own stories −0.006 (p 0.48) | Nested guard gain +0.001 [−0.016, +0.021]: not supported; own stories −0.007 (p 0.38) | Separate non-adopted model; HC1; nested guard; rural flag (2026-10-25) |
| Coverage | Border test | "±60% at 95%"; raw "about half"; audit round 1 +0.04 [−0.04, +0.12] (print +0.06), raw 6.7% / 7.8% / 15.8%, ring −1.16 (0.52); audit round 2 6.7% / 7.7% / 15.9%, ring −1.22 (0.54) | +0.04 [−0.04, +0.13] (print +0.07); 6.8% / 7.7% / 16.0%; ring −1.23 (0.55) | HC1; specification labelled; second-round outcome |
| Coverage | Zero-visit treatment | Audit round 1 adopted 0.486 / 0.252, at log(1e-3) 0.482 / 0.246; audit round 2 0.494 / 0.254; at log(1e-3) 0.490 / 0.248; round 3 (RUCC flag) metro / nonmetro 0.501 / 0.257; at log(1e-3) 0.497 / 0.252 | Urban / rural 0.466 / 0.241; at log(1e-3) 0.461 / 0.235 | Second-round outcome; rural flag (2026-10-25) |
| Coverage | Core blocks left out (gain, primary) | Round 3 (RUCC flag): distance +0.004 [−0.115, +0.125] (print −0.082), border −0.012 [−0.045, +0.020], commuting −0.017 [−0.122, +0.085]; Wald χ² 77.3 / 9.0 (p 0.003) / 37.0 | Distance −0.125 [−0.255, −0.001] (print −0.188 [−0.381, −0.010]), border −0.010 [−0.031, +0.011], commuting −0.007 [−0.106, +0.087]; Wald χ² 115.3 / 3.5 (p 0.061) / 46.0 | Rural flag (2026-10-25) |
| Coverage | Not-adopted specifications, pooled | Round 3 (RUCC flag): without the commuting block 0.43 (print 0.40); all core terms 0.37 (print 0.35); travel beyond gravity 0.362 against 0.359 | 0.46 (0.43); 0.38 (0.37); 0.381 against 0.373 | Rural flag (2026-10-25) |
| Coverage | All marginal factors | 4.15 / 4.14 / 4.18; print 4.50 / 4.58 / 4.52; audit round 1 scratch 0.91 / 0.91, 4.42 / 4.39 (print 0.94 / 0.93, 4.53 / 4.50); scripts on outcome-selected destinations 3.47 / 3.78; audit round 2 pooled over pairs: 4.25 / 4.24 / 4.23 / 4.34 (no broadcast 4.37 / 4.38 / 4.36 / 4.41); round 3 (RUCC flag) per-county mean over 8 folds on 1%+ of visits 4.46 / 4.46 / 4.44 / 4.51 (no broadcast 4.56 / 4.54 / 4.57 / 4.58) | Per-county mean over 8 folds on 1%+ of visits: 4.54 / 4.55 / 4.54 / 4.55 (no broadcast 4.63 / 4.63 / 4.65 / 4.64) | Outcome-selected destinations; scratch table; then pooled scoring, not `coverage_model.py`'s per-county mean (round 3); rural flag (2026-10-25) |
| Coverage | Collection quality | 0.52 → 0.48 (all), 0.50 → 0.42 (print); audit round 1 0.36 → 0.26, 0.34 → 0.25 | Pooled specification 0.36 → 0.25 (all), 0.35 → 0.25 (print and digital); 88 → 33 newsroom counties (rerun 2026-10-25) | Old specification; rerun |
| Coverage | County characteristics column; hospitals | 4.00; 4.01; audit round 2 `hospital_test.py` 4.25 → 4.26 (no broadcasters 4.37 → 4.36), pooled; round 3 (RUCC flag) 4.46 → 4.45, change −0.01 [−0.06, +0.04] (no broadcasters 4.56 → 4.54) | Column on `coverage_model.py`'s primary metric (4.54); `hospital_test.py` 4.54 → 4.56, change +0.02 [−0.02, +0.05] (no broadcasters 4.63 → 4.64); the other sources have no coverage test | Outcome-selected destinations; old specification; rural flag (2026-10-25) |
| Coverage | Out-of-state stories (two outlets filed outside Missouri) | Dropped silently (49 stories); audit round 1: open (re-home or exclude) | Excluded (`EXCLUDE`, authors; 547 stories in `EXCLUDE`) | Spanish-language; out-of-state newsroom |
| Spillover | 2026-10-16 models (whole section) | Broadcaster +0.70, travel out +1.47, held-out 14.5 (broadcaster only 15.5; full 15.3); urban-share model 15.0, well collected 14.1, coefficients +0.65 / −0.81 / +1.17 | Hypothesis terms broadcaster + print outlets: +0.667, −0.387; honest error 6.57 / 5.50 (fitted model 5.98 / 4.66) | Earlier measure (any story touching another county); earlier data |
| Spillover | 2026-10-17 intermediate re-run | 83 outlets, 46 counties; held-out 7.1 (8.6 before); broadcaster +0.58, crowded weekly −0.47, border −0.17, print outlets −0.42; Boone print 23% / 20% | Boone print 18.3% / 19.3% (held out) | CAMPUS, HOME_COUNTY, market-count rule, one home rule, selection procedure, held-out expectations |
| Spillover | Fitted outlets, counties | 87, 47 (also 83, 43) | 85, 48 | HOME_COUNTY, CAMPUS |
| Spillover | Outlets with 10+ stories | 133 | 128 | CAMPUS |
| Spillover | Broadcaster | +0.68 (p < 0.001, z); +0.71; audit round 1 CRV1 s.e. 0.135 | +0.667 (CRV3 s.e. 0.148); CI +0.388 to +0.939 | CRV3, t(47) |
| Spillover | Weekly in a daily-and-TV county | −0.56 (0.008); −0.37 (0.05) | Not adopted (gain −0.09, −0.27 to +0.05) | Nested guard |
| Spillover | Miles to the county edge (log) | −0.14 (< 0.001), every outlet; −0.17 (0.001) | Not adopted (gain +0.08, −0.33 to +0.45) | Nested guard |
| Spillover | Print outlets in the county | −0.28 (0.001); −0.41 (0.01); audit round 1 s.e. 0.089 (CRV1), p < 0.001 | −0.387 (CRV3 s.e. 0.124, p 0.003); CI −0.655 to −0.232 | Market-count rule; CRV3 |
| Spillover | Held-out error | 6.0; 8.62 / 7.20 (83-outlet fit) | Honest error (nested search B) 6.57 / 5.50; fitted model 5.98 / 4.66 | Selection procedure: the search's nested figure |
| Spillover | Nested figure | 9.18 / 7.81 (pre-rerun data), same pair in 38 of 43 folds; audit round 1 6.27 / 4.76 (joint rule inside each fold; adopted set in 47 of 48 folds) | Search B 6.57 / 5.50; nested guard from the hypothesis pair 6.05 / 5.05 | Selection procedure |
| Spillover | Joint test (audit round 1) | Adopted set vs intercept only −1.51 [−2.61, −0.32]; term by term −1.55, −1.04 | Hypothesis-term gains +1.51 [+0.31, +2.58], broadcaster +1.55 [+0.36, +2.70], print +1.04 (lower bound −0.05 to +0.01 by seed) | Selection procedure |
| Spillover | Alternative models (83-outlet fit) | Broadcaster + crowded weekly 9.39 / 7.05; + town population 9.45 / 8.24; broadcaster + town population 9.79 / 8.64 | Broadcaster + crowded weekly 6.98 / 5.35; broadcaster only 7.02 / 5.11 | Current data and definitions |
| Spillover | Audrain / Boone / Osage, actual / expected | 20% / 23%; 29% / 24% (print 18% / 16%); 26% / 24%; audit round 1 20% / 22%, 29% / 26% (18% / 19%), 26% / 25% | Held out: 19.5% / 22.5%, 28.7% / 26.4% (18.3% / 19.3%), 25.6% / 25.3% | Expectations held out |
| Spillover | Weight table | Rates 30.6% / 25.6% / 20.5% / 22.1% / 18.6% / 15.1%; held-out 7.1 / 6.0 / 6.8 / 6.7 / 5.5 / 5.6; "held-out ÷ mean" ranking; "best combination uses mention 0.5"; audit round 1 held-out expected Boone 27% (adopted row), Audrain 49% / 27% (mention 1.0) | Measure sensitivity table (Boone 26%, Audrain 48% / 28%): skill and out-of-sample R² against intercept only; weights are definitions | No code for the ranking; weights are not selected; held-out expectations |
| Spillover | Leave one market out | Weight combinations per market, mean 23.1 vs 23.4 (24.2 vs 23.7 without Columbia–Jefferson City) | Adopted model per market: 5.9 in sample, 6.2 held out, intercept only 7.4 | No code; weights are definitions |
| Spillover | By outlet type; non-weeklies only; Vandalia Leader 34%; Boone County Journal 15%, Centralia Fireside Guard 17% expected | 10.03 → 7.86 etc.; 9.40; 34%; 15%, 17% | Adopted model by type: broadcasters 6.13, dailies 5.72, weeklies 6.64, other 7.96; non-weeklies only 7.37 against 6.43 (`spillover_side_tests.py`); held out: Vandalia Leader 22.5%, Boone County Journal 19.3%, Centralia Fireside Guard 19.3% | Model replaced; rerun on the adopted model |
| Spillover | Weekly alone in its county | −0.16 (p 0.28), −0.14, −0.18; nested 7.41 vs 7.36 | On the adopted model: −0.019 (p 0.89), −0.080 (p 0.53), −0.144 (p 0.17); gains −0.06 [−0.11, −0.03], −0.08, −0.10; none adopted (`spillover_side_tests.py`) | Crowded weekly not adopted; rerun on the adopted model |
| Spillover | Market position | p 0.35 / 0.82 / 0.24; mean 9.3 against 8.6; audit round 1 p 0.31–0.70 | CRV3 p 0.34–0.75; mean 6.03–6.07 against 5.90 (border form) | Current data; CRV3 |
| Spillover | Crowded-county weeklies' median; fits on all 128 outlets; mention weight under town population | 11% vs 24%; 11.5 / 11.1 / 11.2; Boone County Journal 2–21% … Mexico Ledger 14–57% | 14.7% vs 24.1% (7 fitted crowded weeklies); adopted model on all 128 outlets 7.48, broadcaster only 8.51 (`spillover_side_tests.py`); mention weight: Measure sensitivity table (weights are definitions) | Model replaced; rerun on the adopted model |
| Spillover | Two outlets published outside the county they cover | Left out of the fit | Fitted with the covered county as home | HOME_COUNTY |
| Spillover | Quality selection | Not stated | 24.5% vs 17.5% (r +0.26, p 0.003) | Reported every run |
| Spillover | All marginal factors | 14.5; 14.9; 14.2 with ridge 0.05; 14.5 with ridge 0.2; "ridge 0.05 is 0.3 points better" | 6.43; 7.00 / 7.66; every combination worse | Current measure and model |
| Spillover | Crossover–spillover correlation | 68 counties r 0.10 (p 0.43), urban share fixed 0.08; well collected 44 counties r 0.30 (p 0.05) (53 counties, p 0.02 on 2026-10-17 data); audit round 1 all 72 +0.11 (0.36), weighted −0.01 (0.93); well collected 53 +0.35 (0.010), weighted +0.15 (0.27); well-collected counties 29 +0.35 (0.061), +0.20 (0.31); audit round 2 (b = 0.51): +0.18 (0.138) / +0.14 (0.225); +0.41 (0.002) / +0.37 (0.007); +0.40 (0.030) / +0.32 (0.095) | Crossover b = 0.62 (rerun 2026-10-25): all 72 +0.18 (0.120) / +0.17 (0.142); well collected 53 +0.41 (0.003) / +0.40 (0.003); well-collected counties 29 +0.40 (0.034) / +0.34 (0.067) | Crossover rebuilt (b by 2SLS) |
| Spillover | Collection quality | Urban share −1.09; 15.0 → 14.1; 28 counties, 36 outlets; audit round 1 in well-collected counties broadcaster p 0.042, print p 0.88 | 7.5 / 6.6 / 8.9 held-out miss (all 128 outlets, 72 counties / well collected 95, 54 / well-collected counties 40, 29); clustered-t p 0.077, 0.90 in well-collected counties (rerun 2026-10-25, unchanged) | Current model; `EXCLUDE` in the newsroom count; CRV3 |
| Spillover | County characteristics: hub dominance (concentration of travel) | 15.0 (all outlets), 14.1 (well collected); adopted 2026-10-16, replaced | No current equivalent: the adopted spillover model has no travel term | History of the 2026-10-16 model |
| Spillover | County characteristics column | 15.6 baseline; 15.0; 14.1; ACS foreign-born 14.7; index rent share 14.6, several indicators 15.3 / 15.4; bylines 16.1 → 16.2–16.3; business closings 14.8, turnover 13.9; hospital 15.7 | Adopted model 6.43: no measure lowers it (best 6.43–6.45); several indicators 6.52; bylines 6.59 → 6.68–6.78 (`civic_variables_test.py`, `civic_index_test*.py`, `spillover_bylines_test.py`, `business_dynamics_test.py`, `hospital_test.py`) | Earlier measure and model; rerun on the adopted model |
| Crossover | County characteristics column | Baseline 12.9 (log population + RUCC nonmetro + commuting; 2026-10-16 measure); ACS 12.0; index 12.2 / 12.3; business openings 12.2 (+0.16, p 0.03), turnover 12.2; hospital 12.2 (−0.54) | Baseline 9.8 (rural flag; distinct residents, b = 0.62); ACS median age 9.55, selection 9.4; index active voters 9.70, census response 9.76; business jobs by openings 9.10 (+0.31), turnover 9.16, openings 9.24 (+0.18); hospital 9.4 (−0.45) | Crossover rebuilt (b by 2SLS); rural flag (2026-10-25) |
| All | Selection rule | Audit round 1 joint test (adopted set beats baseline; each coefficient's interval excludes zero; candidates one at a time) | Selection procedure: core blocks, hypothesis terms, nested guard, one primary metric | Authors, 2026-10-24 |
| Public | Public, best setting per class, Missouri all | 4.34 (4.30 rerun), classes 3.99 / 4.06 / 5.56 / 5.48 / 5.08; audit round 1 nested 4.85 (4.38 / 4.78 / 6.96 / 5.47 / 5.25), in-sample 4.67; audit round 2 nested 4.64 (4.15 / 4.48 / 6.05 / 6.28 / 5.25), in-sample 4.41 | Nested 4.60 (4.10 / 4.41 / 6.05 / 6.26 / 5.24); in-sample 4.37 | Nested selection; outcome; JT01; all destinations |
| Public | Public reference (start of 2026-10-18) | 5.22 / 4.78 / 6.05 / 6.72; 5.35 | 5.36 / 4.87 / 6.01 / 6.78; 5.44 (`public_gap_corrections.py`, `public_default_sensitivity.py`) | Superseded by per-class settings; adopted outcome |
| Public | Default-weight sensitivity | 2026-10-18 (old outcome, in-sample): each setting within ±0.15 to 0.40 of the reference; "the weight on commuting moved most"; Huff attraction exponent 0.5 +0.42; visitation law's exponent 2, small rural +1.38; non-work decay by income, degree or tenure −0.17 to −0.18; metro-size survey classes +0.52; establishment counts and employment as the draw, zero weight once taxable sales are in; more work days better up to 40 in three classes | Work from home +0.02, 15 work days +0.06, shopping ×0.5 +0.10, medical and specialty +0.06 / −0.07, circuity +0.05 / −0.10, trips −0.19; recreation and visiting move most (−0.24 / +0.41), gross leakage −0.24; Huff exponent 0.5 +0.42; visitation law small rural +1.52; non-work subgroups −0.18 to −0.19; metro-size survey classes +0.10 (hubs +0.81); employment draw −0.20 against establishments, zero weight in every class; 40 work days better than 10 in three classes (−0.48 to −0.68); base build 5.50 | Adopted outcome; JT01 builds (non-work variants rebuilt by `public_model.sh` step 9); Advan-fitted benchmark under the rural flag (2026-10-25) |
| Public | Gap diagnosis (`public_gap_diagnosis.py`) | 2026-10-18: the public model overstates the metro cores and understates regional centres and small rural destinations (named ratios for places outside the TV market) | Script prints the study counties only: Advan / public inflow Boone 1.19, Audrain 1.30, Osage 0.93; 15 destinations carry 71.8% of the error; Advan-fitted taken apart 3.28 → 3.74 / 3.74 / 3.40 / 4.18 | Scope (places outside the market removed); adopted outcome; rural flag (2026-10-25) |
| Public | + segment corrections (C) | 3.73 (3.43 / 3.52 / 3.93 / 6.40 / 3.48); refined 3.63 (regional-hub rings 5.62); audit round 1 outer loop 3.97 (3.53 / 3.97 / 4.05 / 6.12 / 4.54), in-sample structure 3.71; audit round 2 outer loop 4.07 (3.70 / 3.87 / 4.41 / 5.58 / 5.18), in-sample structure 3.61 | Outer loop 4.05 (3.61 / 3.86 / 4.54 / 5.76 / 5.23); in-sample structure 3.59 | Outer loop; fold base; all destinations |
| Public | + destination factor from public measures (B) | 3.76 (3.50 / 3.51 / 3.86 / 6.67 / 3.30); audit round 1 3.95 (3.58 / 3.99 / 3.88 / 5.65 / 4.52); audit round 2 3.96 (3.56 / 3.91 / 3.91 / 5.72 / 4.86) | 3.91 (3.50 / 3.85 / 3.93 / 5.79 / 4.72) | As above |
| Public | + one factor per destination county (A) | 3.40 (2.94 / 3.07 / 4.44 / 6.33 / 3.52); audit round 1 3.47 (3.10 / 3.52 / 4.31 / 5.91 / 2.35); audit round 2 3.46 (3.12 / 3.25 / 4.44 / 6.32 / 2.53) | 3.45 (3.09 / 3.23 / 4.45 / 6.29 / 2.55) | As above |
| Public | Advan-fitted, Missouri | 3.13 (3.28 / 2.79 / 4.38 / 3.26 / 2.11); audit round 1 3.34 (3.51 / 2.95 / 4.36 / 3.41 / 2.61) on the common set; audit round 2 3.31 (3.57 / 2.87 / 4.12 / 3.25 / 2.45), common set 3.38; round 3 (RUCC flag) 3.28 (3.54 / 2.86 / 4.14 / 3.25 / 2.39), common set 3.36, log-ratio 0.35 | 3.28 (3.41 / 2.84 / 4.75 / 3.80 / 2.06) on all destinations; 3.36 on the common set; log-ratio 0.34 | Outcome; JT01; primary metric; rural flag (2026-10-25) |
| Public | Gap and share closed | Audit round 1: public − Advan +1.50 [+1.02, +2.01] (log-ratio +0.17); C − Advan +0.63; corrected − public −0.88 [−1.26, −0.49]; closed 58% (C), 91% (A) without interval; audit round 2 +1.34 [+0.87, +1.82] (log-ratio +0.23); C − Advan +0.76 [+0.36, +1.16]; C − fold base −0.60 [−0.96, −0.25]; closed 44% [22, 67] (C), 89% [63, 117] (A); round 3 (RUCC flag) +1.31 [+0.85, +1.79] (log-ratio +0.24), small rural +0.56 [−0.01, +1.16], major-metro rings +1.91 [+0.08, +3.72], regional-hub rings +3.01 [+0.07, +6.20]; C − Advan +0.76 [+0.34, +1.16]; closed 43% [21, 66] (C), 88% [62, 116] (A); log-ratio closed 33% [25, 40] / 61% [52, 71] | +1.32 [+0.84, +1.83] (log-ratio +0.24), small rural +0.70 [+0.04, +1.43], major-metro rings +1.30 [−0.27, +2.96], regional-hub rings +2.46 [−0.62, +5.79]; C − Advan +0.77 [+0.32, +1.20]; C − fold base −0.58 [−0.94, −0.23]; closed 43% [21, 68] (C), 88% [60, 118] (A); log-ratio closed 32% [24, 39] / 60% [51, 70] | Fold base; intervals; all destinations; rural flag (2026-10-25) |
| Public | Log-ratio errors | Audit round 1 0.35 / 0.53 / 0.45 / 0.39; round 3 (RUCC flag) Advan-fitted 0.35 | 0.34 / 0.58 / 0.51 / 0.44 | As above; rural flag (2026-10-25) |
| Public | Advan share outside the common set | 1.37% (max 8.5%) | 1.34% (max 8.2%) | Outcome |
| Public | "Beats the Advan-fitted model in major-metro rings (3.93 vs 4.38)" | Claim; audit round 1 4.05 vs 4.36; audit round 2 4.41 vs 4.12, gap +0.28 [−1.57, +2.41]; round 3 (RUCC flag) 4.54 vs 4.14, gap +0.39 [−1.35, +2.48] | Deleted: 4.54 vs 4.75, gap −0.21 [−2.17, +2.08], no difference; the corrected model (C) is not the public model | Never a claim of the study; intervals; rural flag (2026-10-25) |
| Public | "With destination factors, beats it in small rural counties (2.94 vs 3.28)" | Claim; audit round 1 3.10 vs 3.51; audit round 2 3.12 vs 3.57, gap −0.46 [−0.93, −0.03]; round 3 (RUCC flag) 3.09 vs 3.54, gap −0.44 [−0.91, −0.02] | Deleted: 3.09 vs 3.41, gap −0.31 [−0.81, +0.21], no difference — model A carries one Advan-learned factor per destination; it is not the public model | Never a claim of the study; intervals |
| Public | Commuter-class instability | Audit round 1: major-metro rings nested 6.96 vs in-sample 5.36 (cost 1.60); regional-hub rings outer loop 6.12 vs 4.27 (cost 1.85); audit round 2 6.05 vs 5.15; 5.58 vs 4.38 | 6.05 vs 5.16; 5.76 vs 4.38; out-of-sample cost 0.23 (Stage 1) and 0.46 (Stage 2) overall | Second-round rerun |
| Public | Stage 1 picks and fold structures | Audit round 1: independent towns 23 / 9; major metro `_s_alpha15`; hubs 6 / 3; mode C folds 2, 4, 7 metro-core, 0, 1 pooled hub | Stage 1 table and fold structures (Public-data travel model) | JT01 rebuilds; primary metric |
| Public | 2026-10-18 structure rebuilt (`public_adjusted_pairs_trnear.csv`) | Audit round 1 segment corrections 3.84; audit round 2 public base 4.47, segment corrections 3.71, + per-destination 3.54 (ad hoc run) | Public base 4.43, segment corrections 3.69, + public destination factor 3.70, + per-destination 3.53 (all destinations; printed by `public_adjusted_model.py`, `logs/adj_trnear.log`) | Outcome; JT01; printed by the script, not an ad hoc run |
| Public | "Destination pull closes 46% of the gap … together 68%" | 5.35 reference, in-sample, old outcome: destination 46%, decay 21%, adjacency 12%, together 68%; "twice too much to the nearest counties" | 5.44 reference against 3.28: destination 48%, decay 23%, adjacency 12%, size −11%, together 69%; 1.1–1.5 times Advan's share within 15 miles; hubs beyond 120 miles half (1.99) | Adopted outcome; JT01 builds; rural flag (2026-10-25) |
| Areas | Number of patterns K | K = 6, chosen on held-out months (2.87 points at K = 1, 2.30 at K = 6, 2.42 at K = 8); same day: paired one-SE rule (Columbia 11), per-market population and volume (Columbia 2); audit round 1 per town with county-factor residents and the odd fit's order: 3 | Columbia–Jefferson City market 2 | Splits drawn inside the K loop; a market share depends on which home counties form the market; ACS residents; independent halves |
| Areas | Columbia's areas | Two: Columbia I and II (primary 42% on 2026-10-17, then 72% / 16%; 76,912 / 17,513 residents); audit round 1 one area, 91%, ~97,020 | One: "Columbia's civic interest area", 93%, 103,086 (ACS) | K rule; ACS residents |
| Areas | Mexico, Linn share of residents | Mexico 79%, then 74% (5,241); Linn 93%, then 92% (1,641); audit round 1 Mexico 92% (~6,530), Linn 71% (~1,270) | Mexico 86% (5,685); Linn 85% (1,172) | As above |
| Areas | Area size | Published outline Columbia I 1,158 km², II 4,165, Mexico 1,930, Linn 1,264; audit round 1 1,363 / 1,691 / 1,176; audit round 2 core p ≥ 0.5 (432 versions) 1,380 / 1,000 / 1,122 km²; single-drawing outline 3,607 / 3,660 / 1,292 (hexagons × 5.85 km²); round 3 core p ≥ 0.5 (unconnected, all hexagons) 1,166 / 802 / 949 km²; 1,728 versions, multi-part with no distance limit (2026-10-25 draft): 1,079 / 785 / 890 km²; 6,912 versions, regular travel 4+ of 7 months: Columbia 1,090 km² / 208,213 people (Jefferson City and Moberly kept), Mexico 802 / 123,946, Linn 896 / 139,001 | 6,912 versions, regular travel 7 of 7, D90 limit on parts: 979 / 802 / 896 km²; all core hexagons (p ≥ 0.5) 1,073 / 831 / 955 km² | Multi-part area (authors' decision, 2026-10-25); news weight as a choice; D90 limit; latitude correction; outline is the area, not a closed drawing |
| Areas | Ensemble size | 432 versions (audit round 2); 1,728, seven drawing choices (round 3 and the 2026-10-25 draft) | 6,912: the seven drawing choices × the news weight ω ∈ {0, ½, 1, 2} | News weight as a choice (authors' decision, 2026-10-25) |
| Areas | Regular travel and the distance limit | 4+ of 7 months (`analysis/activity_space.py`): D90 Columbia 103.0 km, Mexico 51.8, Linn 101.5 (D80 37.1 / 47.5 / 71.1; D95 165.1 / 71.2 / 122.6) | 7 of 7 months: D90 23.9 / 48.1 / 70.5 km (D80 7.4 / 45.6 / 64.7; D95 46.2 / 49.8 / 84.4) | Authors' decision, 2026-10-25: regular travel is travel seen every month |
| Areas | Parts of each area | 1,728 versions, no limit: Columbia home body 165 hexagons, 962 km², 160,816; Jefferson City 13, 76 km², 7.8 km from the body, 35,606; Moberly 7, 41 km², 33.8 km, 11,460; 12 specks. Mexico home 92, 535 km², 15,507; rural Audrain 14 and 3; Centralia 18.2 km from the body; 2 specks. Linn's Columbia part 12 hexagons, 70 km², 75,883. 6,912 versions under 4+ of 7: Moberly a part of Columbia's area (50.2 km from the centre) | Columbia home body 168, 979 km², 161,321, no other part, Jefferson City a distant tie (10 hexagons, 41.2 km from the centre, 32,125), 5 specks; Mexico home 109, 634 km², 15,968, Centralia 7.8 km, 4 specks; Linn's Columbia part 13, 76 km², 82,353 | 6,912 versions; 7 of 7; D90 limit |
| Areas | Mexico's Boone hexagons | 99; audit round 1 95; audit round 2 34 in the core, 1 at p ≥ 0.8, 114 in the single-drawing outline; round 3: 29 in the reference-level drawing; 1,728 versions: 51 / 23 / 1 at p ≥ 0.2 / 0.5 / 0.8 | 51 likely 20%+, 24 likely 50%+ (20 in the Columbia part), 1 likely 80%+ (`area_ensemble.py`) | Probability surface; 6,912 versions |
| Areas | People inside the core; p ≥ 0.8 | —; round 3 all p ≥ 0.5: 212,133 / 124,002 / 133,522; 1,728 versions: multi-part area 207,883 / 123,873 / 132,531 (all core 212,133 / 124,002 / 133,522); by p band 38,714 / 173,419; 111,840 / 12,163; 93,965 / 39,557; p ≥ 0.8 583 / 308 / 346 km² | Multi-part area 161,321 / 123,946 / 139,001 people (all core 194,485 / 124,228 / 139,992); by p band 47,491 / 146,994; 111,976 / 12,252; 100,435 / 39,557; p ≥ 0.8 536 / 320 / 346 km² | 6,912 versions; 7 of 7; D90 limit |
| Areas | Areas outside the Columbia–Jefferson City market | Six areas in three other TV markets built and reported (2026-10-25 draft) | Not drawn or reported | Scope: the Columbia–Jefferson City market only (authors' decision, 2026-10-25) |
| Areas | Connected-body rule | —; round 3: reach factor 10 / 15 / 25 km / none, distant pieces outside the area as separate ties; 2026-10-25 draft: home body + every p ≥ 0.5 piece of 3+ hexagons, wherever it lies | Home body + every p ≥ 0.5 piece of 3+ hexagons whose nearest hexagon lies within D90 of the town's centre; the reach's level "none" replaced by D90 | A connected-within-reach rule cut out Columbia, Mexico's dominant destination (33.8 km from the home body; Audrain → Boone 39% of out-of-county visits, 43% of work-hours visits, 34% of out-commuters); no limit at all let pieces far beyond regular travel join (authors' decision, 2026-10-25) |
| Areas | p, wording | "Share of settings" that draw a hexagon, "not a probability" (round 3); the probability under equal weighting of the 1,728 versions (2026-10-25 draft) | The probability, under equal weighting of the 6,912 versions, that the place is part of the area ("how likely the place is part of the area"), conditional on the range of the choices; not a confidence | Authors' decision, 2026-10-25 ("share of settings" obtuse); multiverse analysis, Steegen et al. 2016 |
| Areas | Single-drawing map | Published as `?prob=0` with its outline, certainty layer and orange news dots, reproduced by the reference-level version (Jaccard 1.000); that drawing in the core 86% / 86% / 88%; exports carried its rows | Not produced or exported | One version is a small core that does not depict the area |
| Areas | News terms on the single drawing and the closed outlines | Single drawing: Columbia 245 / 15 / 17 hexagons (11% differ), Mexico 137 / 4 / 4 (6%), Linn 132 / 2 / 11 (10%); closed outlines Columbia 587 / 125 / 53 (23%), Mexico 444 / 16 / 175 (30%), Linn identical; 1,728-version core comparison Jaccard 0.91 / 0.88 / 0.95 | Network-tie core against the travel-only core (6,912 versions): Jaccard 0.93 / 0.91 / 0.95; the news weight ω is a choice (Results, The news weight alone) | Single drawing and closed outline dropped; news weight in the ensemble |
| Areas | Distant ties, Mexico | — | Columbia as a separate tie in 27% of settings (round 3) → Columbia is a part of Mexico's area (20 hexagons, 117 km², 102,884 people) | Multi-part area |
| Areas | Multi-part figures from rounded p (draft, 2026-10-25) | — | Mexico area 791 km², 123,900 people, 136 hexagons; home body 107 hexagons, 622 km², 15,923; Centralia 7.8 km; rural Audrain 3 hexagons; specks rural Audrain 1, rural Callaway 2; all core 808 km², 124,030, 139 hexagons → 785 km², 123,873; home body 92, 535 km², 15,507; rural Audrain 14 and 3; Centralia 18.2 km; 2 specks (3 hexagons); all core 802 km², 124,002 | Unrounded p (single source `flows/reach/probability_columbia.json`) |
| Areas | Distant ties | "Pieces drawn beyond the reach, share of settings" as the tie list (round 3); 1,728 versions: towns drawn in 50%+ of versions with no hexagon at p ≥ 0.5, Columbia: Fulton 0.76 / 0.58 / 0.45 and four towns outside the TV market; Mexico: Moberly 0.74 / 0.35 / 0.23; Linn: Ashland 0.78 / 0.67 / 0.36 and one town outside the TV market | Towns drawn often but outside the area (Results); Jefferson City a distant tie of Columbia beyond D90 | A town drawn in most versions can have every hexagon under 0.5; D90 limit |
| Areas | Map key and outline | "Share of settings that draw the place"; core outlined; 2026-10-25 draft subtitle "Across 1,728 equally plausible ways of drawing the map; …" | "How likely the place is part of the area" (10–80%+); subtitle "Across 6,912 equally plausible ways of drawing the map; outlined: the area, places likely 50% or more"; outline grey #6f6d66 at 0.8 | Authors' decision, 2026-10-25 |
| Areas | "Replicability" of the areas | — | Term replaced by month-split stability (K was selected on the same split) | Not validity; not independent of K |
| Areas | Market test | Mexico-Boone 893 crossing; Columbia-Cole 2,682 (11.6% / 16.3%); Linn-Cole 522; audit round 1 Mexico-Boone 1,037, Linn-Cole 319 | Mexico-Boone ~832 (10.0% / 0.5%); Columbia Boone-centred (Boone 45%); Linn-Cole ~289 (8.1% / 0.2%) | K rule; ACS residents |
| Areas | Areas per town | K = 6: "hubs split (Columbia 42/36/12)", "isolated towns have one (Linn 93, Belle 95)"; 11 areas in the market's 8 towns | 9 in 8 towns (Areas per town table, left of each arrow = K = 6) | K rule |
| Areas | Local index reach, Linn | Rural Osage 0.15 against the pattern's 0.31; Maries 0.02 against 0.11 | Local index replaced by the network tie and the area's p. K = 2: Linn's pattern sends 25% of its travel to Cole, 18% to rural Osage and 10% to Boone, Maries under 5% (not listed) (`flows/market_patterns.py`); Linn's area has a rural Osage part (6 hexagons, p ≥ 0.5) and no Maries part (`flows/area_core.py`) | K = 6 pattern; definition replaced |
| Areas | Network tie values | Columbia's strongest ties Ashland 0.38 / 0.61, Jefferson City 0.19 / 0.34, Mexico 0.16 / 0.26; weight sensitivity rank correlation 0.988–1.000, at most 25 of 608 hexagons change band; gate: Linn-Columbia shared places 0.32 (0.05 out, 0.02 in), kept Linn-Jefferson City 0.26, Mexico-Columbia 0.12, Columbia-Mexico 0.22; statewide shared coverage 244 of 267 lifted hexagons; Columbia "primary south, secondary north" | K = 2 (`flows/market_patterns.py`): Ashland 0.36 / 0.66, Jefferson City 0.20 / 0.38; Mexico → Columbia 0.21 / 0.31; weight sensitivity 0.978–1.000, at most 69 of 541 hexagons (every alternative map with the adopted map's spatial lag; without it, as compared before 2026-10-25, 0.86–0.96); Linn-Columbia shared places 0.33 (out 0.05, in 0.02), gated out; one pattern per town (no primary / secondary); statewide count and display floors not rerun (the market only; floors are an ensemble drawing choice) | K = 6 areas; K = 2 rerun |
| Areas | Display selectivity floors; hexagons shown | Columbia primary 15.9 (239 hexagons), secondary 15.0 (398); audit round 1 hexagons beyond home 108 / 123 / 122, share holding 0.95 / 0.98 / 0.75; audit round 2 single drawing 1,146 / 807 / 754 km², 88–90% in the core; round 3: reference-level drawing 86% / 86% / 88% in the core | No single-version drawing is produced; selectivity is a drawing choice in the ensemble (40 / 50 / 60%) | Probability surface |
| Areas | Minimum size evidence | All study towns: 75 markets; Spearman 0.37; median 0.84 under 500 … 0.95 above; Mexico's secondary 729 residents, 389 hexagons, 72% holding; 63 remain; audit round 1 57 areas, median 0.93, 0.83 / 0.855 / 0.91 / 0.94, Spearman 0.31, Mexico 0.98; audit round 2 0.76 / 0.835 / 0.89 / 0.92, Spearman 0.19, Columbia 0.95; round 3 58 areas, median 0.92, 0.76 / 0.84 / 0.89 / 0.93, Spearman 0.39 | The market's 9 areas in 8 towns: median 0.90; 0.87 / 0.78 / 0.90 / 0.93 by size (Linn 0.63); Spearman 0.66 | Independent halves; ACS residents; K rule; scope |
| Areas | Selection-rule sensitivity ("split-half agreement") | Home included, K = 6: 0.896 / 0.880 / 0.941 / 0.734, mean 0.863, "highest mean agreement"; area sensitivity Columbia I 0.77–1.0, Mexico 0.44 / 0.50; audit round 1 home excluded 0.76 / 0.75 / 0.58, mean 0.70, IoU 0.53–1.0 / 0.52–1.0 / 0.45–1.0; audit round 2 432-version ensemble r(p) 0.99 / 0.96 / 0.86, core Jaccard 0.90 / 0.85 / 0.66 (p ≥ 0.8: 0.95 / 0.96 / 0.58), single-drawing outline 0.85 / 0.74 / 0.55; 1,728 versions r(p) 0.994 / 0.978 / 0.901 (contested 0.990 / 0.956 / 0.734), core Jaccard 0.85 / 0.88 / 0.72 | 6,912 versions, month-split stability: r(p) 0.995 / 0.978 / 0.895 (contested 0.990 / 0.955 / 0.732); core Jaccard 0.86 / 0.87 / 0.72 | Settings enter the ensemble; "agreement" is month-split stability, not validity |
| Areas | Busiest-hexagon sensitivity (BUSIEST=hexagon) | 1,728 versions at ω = 1, all core hexagons (p ≥ 0.5): Columbia 811 km², 188,276 people; Mexico 285, 12,068; Linn 270, 36,695 | 6,912 versions, 7 of 7, D90 limit, multi-part area: 705 / 273 / 252 km², 152,057 / 11,871 / 36,492 people (all core 764 / 285 / 275 km², 176,025 / 12,068 / 36,736) | Rerun on the current ensemble and area rule |
| Supply | Coverage density | Columbia II place-specific 24 / 5 / 26 / 45%, with county-level stories 83 / 17 / 0 / 0%; square root for all: Columbia I 58 / 38 / 4 / 0, II 25 / 25 / 50 / 0, Mexico 32 / 15 / 53 / 0, Linn 25 / 54 / 21 / 0; revised: Columbia I 53 / 4 / 43 / 0, II 23 / 4 / 73 / 0, Mexico 30 / 3 / 67 / 0, Linn 22 / 5 / 73 / 0, newsrooms 1 / 1, 2 / 6, 2 / 2, 2 / 2; audit round 1 on the network-tie areas: 44 / 8 / 48 / 0 (newsrooms 2 / 1), 32 / 4 / 64 / 0 (2 / 3), 21 / 8 / 71 / 0 (2 / 2), 259 / 311 / 219 hexagons, alpha 1: 44 / 8 / 48, 29 / 7 / 64, 20 / 9 / 71; audit round 2 QA on the travel-only area: 34 / 9 / 57 / 0, 18 / 5 / 77 / 0, 22 / 9 / 69 / 0 (travel-only area 3,502 / 3,613 / 1,292 km²) ; round 3 unconnected travel-only core: 53 / 6 / 41 / 0, 35 / 4 / 61 / 0, 34 / 6 / 60 / 0 (1,264 / 849 / 990 km²); 1,728-version travel-only core, multi-part, no distance limit: 52 / 5 / 43 / 0, 35 / 4 / 61 / 0, 34 / 6 / 60 / 0 (1,195 / 820 / 931 km²; Columbia 209,594 people) | QA only, travel-only core (ω = 0 of the 6,912 versions; multi-part, D90 limit): 49 / 6 / 45 / 0, 35 / 4 / 61 / 0, 34 / 6 / 60 / 0 (1,049 / 820 / 931 km²; Columbia 162,809 people) | Supply is the next paper's; travel-only core with the multi-part rule and D90 limit (2026-10-25) |
| Supply | Balanced diet | Columbia I 51%, 5.0, 3 outlets; II 10%, 1.5, 4; Mexico 14%, 2.2, 3; Linn 14%, 1.7, 2; audit round 1 44%, 4.4, 3; 15%, 2.4, 3; 16%, 1.8, 2; Economic Development 14% of Mexico's; audit round 2 QA on the travel-only area 22%, 9%, 17% ; round 3 unconnected core 46%, 12%, 28% | QA only, travel-only core (ω = 0; multi-part, D90 limit): 49%, 12%, 28% | As above |
| Tie markets | Month-split stability / accuracy, Columbia–Jefferson City market | 2026-10-18: 0.85 / 0.67; audit round 1 (before stage 3) 0.81 / 0.615 (travel alone 0.49); audit round 2 (stage 3) 0.82 / 0.625; round 3 accuracy 0.50 | Accuracy median 0.505 (printed 0.51; mean 0.526), month-split stability 0.79, travel alone 0.52 (8 study towns; settings recorded by each run) | Scoring change (home masked, beyond the home county); stage-3 and round-3 tie changes; scope |
| Tie markets | Columbia, Mexico, Linn (town) | 2026-10-18 accuracy 0.69, 0.46, 0.68; audit round 1 0.13, 0.41, 0.82, month-split stability 0.88, 0.82, 0.88; audit round 2 accuracy 0.13, 0.41, 0.75; month-split stability 0.89, 0.84, 0.89 | Accuracy 0.14, 0.47, 0.69; month-split stability 0.92, 0.80, 0.79 | Old scoring (Columbia's 0.69 from unmasked home units); stage 3 |
| Tie markets | Population in the within-county spread | Columbia market 0.67 → 0.69; all study towns 0.70 / 0.687 → 0.70 / 0.707; density thresholds 0.72 / 0.703, 0.71 / 0.706; nonmetro-only rule 0.697 | Current scoring, the market's 8 study towns (accuracy median / mean): without population 0.45 / 0.509 → with it, every tract (adopted) 0.51 / 0.526; nonmetro-only rule 0.51 / 0.522; density under 50 / 200 people per km² 0.45 / 0.515, 0.51 / 0.530 (`tie_footprint.py`, ATTRPOP) | Old scoring; rerun |
| Tie markets | Columbia's eight towns, steps; Vandalia; Mexico with LODES within 45 miles; within-county spread | 0.655 → 0.665 → 0.67; 0.44 → 0.57 (audit round 1 0.55); 0.65; jobs 0.49, OSM 0.50, half each 0.53, exponent 1 0.59, 3 0.37 | Current scoring, accuracy median (Vandalia): exponent 1, no regularity rule, no population 0.45 (0.45) → exponent 0.5 0.40 (0.35) → + regularity rule 0.45 (0.42) → + population (adopted) 0.51 (0.54); on the adopted settings exponent 1 0.53 (0.56; mean 0.529 against 0.526, a difference of 0.003, not tested for significance; 0.5 kept), exponent 3 0.46 (0.52). Mexico with observed LODES within 45 miles (regular-travel builds, `public_model.sh` step 10): Mexico 0.48 against 0.47 at 90 miles, the Jefferson City false market still drawn (47 km² against 53); market median 0.50 both. Spread's destination part (adopted settings; 0.51 / 0.526 with jobs and OSM half each): jobs only 0.49 / 0.509 (Vandalia 0.48), OSM only 0.47 / 0.504 (0.47); without population 0.41 / 0.474 and 0.46 / 0.484 (`tie_footprint.py` SPREAD) | Old scoring; rerun |
