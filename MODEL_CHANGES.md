# Model changes — travel, coverage and spillover

Log of the modelling decisions from 2026-10-16: what was adopted, what was tested and rejected, and the evidence for
each. Two peer reviews on 2026-10-24 restate every model's figures: current figures are under **Current results**,
replaced ones under **Superseded figures** (end). Scripts are in `analysis/` unless noted; `make_visuals.sh` rebuilds
every figure from the adopted models.

## Data and periods

| Item | Setting |
|---|---|
| Travel | Advan Neighborhood Patterns Plus (Dewey), Missouri destinations, January–September 2026; summed to home county × destination county (`build_calibration.py`, then `build_statewide_od.py` → `od_mo_2026.csv`; nothing rewrites the file afterwards). Columns: `visits` (÷ county factor, 2026-10-16), `visits_recorded`, `visits_statewide` (÷ statewide units per resident; the adopted scale), `visits_trimmed` (÷ county factor without phantom home block groups); work-hours columns alike. Outcome in every travel script: `gravity_terms.travel_visits` (`visits_statewide` × (1 − highway-stop discount)) |
| Travel, capped destinations | Advan keeps at most 2,000 home block groups per destination row. Capped destination block groups: 275–904 per month (5.5–18% of rows), holding 19.5% (January) to 43.3% (July) of Missouri out-of-county device-visits. Flag: `dest_bg_capped_mo_2026.csv`; pairs counted in uncapped destinations only: `od_mo_2026_uncapped.csv` |
| Travel, distinct people | `od_people_mo_2026.csv` (`build_unique_od.py`): per home county × destination county × month, St. Louis city and county one unit, Missouri and Kansas destinations: people from each home block group in the destination's busiest block group, capped at the block group's calibrated denominator D and converted to people by its ACS population ÷ D, summed (`people_lower`; sensitivity columns `people_lower_recorded`, `people_lower_b1`, `people_lower_calibrated`) |
| Travel, Kansas | Advan Neighborhood Patterns Plus, Kansas destination block groups, January–September 2026 (`neighborhood/raw_ks/`): Missouri residents' visits to Kansas, and the Kansas transfer test (`build_ks_od.py` → `od_ks_2026.csv`; `visits` recorded, `visits_calibrated` and `visits_statewide` added; factors in `calibration_county_month_ks.csv`) |
| Destinations not observed | Illinois, Iowa, Arkansas, Oklahoma and Nebraska block groups are not in the data. A Missouri resident seen only there is not counted as leaving; border counties' crossover is low by that much |
| Tracts | Tract outputs use January–July only (2020 block groups), as `activity_space.py` does: August–September home codes are 2010 block groups, whose tract codes name different areas (`build_tract_od.py` → `od_tract_mo_2026.csv`) |
| Population | ACS 2020–2024 B01003: counties (`free/mo_county_population.csv`), block groups (`census_dl/acs_tract/b01003.dat` → `bg_acs_population.csv`; 2010 block groups by area-weighted overlay of the 2020 block groups, Missouri total preserved to 1 person in 6.19 million) |
| Commuting | LODES 2023, primary jobs (JT01) in the travel and coverage terms, the crossover scripts and the public model. `free/od_2023.csv.gz` is JT00 (all jobs) and is read by `build_county_covariates.py` and for the Kansas class centres |
| Coverage | Missouri School of Journalism analysis of local news stories, March 2026 (the only month enriched); a story is placed in every county it is centred in or mentions |
| Store-level visits | Advan Weekly Patterns Plus, Missouri, weeks of 2026-03-02 to 03-23. Places keyed by `PERSISTENT_ID_STORE`; `PERSISTENT_ID` is shared by unrelated places (2,225 values for 100,596 places in a week). NAICS codes are the 2017 vintage (gas 447110 / 447190, convenience 445120; 4571xx and 445131 do not occur) |
| Highways | OpenStreetMap `osm/missouri-latest.osm.pbf`: motorway / trunk / primary ways (and links) whose ref is an Interstate or US route number; business routes, loops and spurs excluded (10,976 ways) |
| Boundaries | Advan reports 2020 block groups for Jan–Jul and 2010 block groups for Aug–Sep; county codes are the same, and the township maps use one area crosswalk per vintage |
| Smallest count | Every Advan count is a whole number of panel devices × one monthly scale; the smallest value (one panel device) is 14–20 in 2026. It is not a privacy floor |

## Current results (2026-10-24)

The figures a paper quotes. Body sections state the same values; a different value elsewhere is marked superseded
and listed under Superseded figures. Intervals are 95%, county-paired bootstrap unless stated. **Gain** = held-out
error without a block or hypothesis term − with it (positive: the term lowers error). **Change** = held-out error
with an exploratory addition − without it (negative: the addition lowers error).

**Selection procedure (user, 2026-10-24), one procedure for every model:**

1. Core terms by theory, tested as blocks (distance, border, commuting), never one term at a time; kept by theory.
2. Hypothesis terms stated in advance and reported whatever the result: spillover, broadcaster and print and digital
   outlets in the county; coverage, the metro / nonmetro split (log visits × nonmetro newsroom county). Travel has
   none.
3. Exploratory additions only through the nested guard: the search repeated inside each training set and scored on
   the held-out counties; adopted only if the nested change has an interval excluding zero. None passes in any model.
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
| Crossover: distinct residents seen outside the county, calibrated denominator (b = 0.51 [0.43, 0.59]) | Audrain 44%, Boone 26%, Osage 57%, Missouri median 58%, St. Louis (city + county) 35% | `crossover_compare.py` |
| — bounds (÷ Σ max(own, E), ÷ Σ min(own, E)) | 34–53%, 20–31%, 43–69%, 44–69%, 18–46% | `crossover_compare.py` |
| Pass-through (highway-stop) discount | removes 1.74% of out-of-county visits (county-factor weighting; 2.2% on the statewide scale) | `build_road_stop_share.py` |
| Device IDs | stability across weeks not established (claim withdrawn) | `device_id_test.py` |

**Travel** — doubly-constrained gravity, PPML; home and destination fixed effects + 8 core pair terms in three blocks
(`gravity_terms.FACTORS`):

| Measure | Value | Script |
|---|---|---|
| Held-out share-weighted error, all Missouri destinations (primary) | 3.31 [2.96, 3.64] | `travel_model.py` |
| — small rural (56) / independent towns (32) / commuter (18) / hubs (9) | 3.57 / 2.87 / 3.68 / 2.45 | `travel_model.py` |
| Held-out R² of shares | 93.7% [92.4, 94.9] (fixed effects only: error 16.16, R² 0.9%) | `travel_model.py` |
| Big flows (forecast 5%+, 484 pairs): error; within 0.8–1.25× | 3.44 [3.16, 3.73]; 51% [46, 55] | `travel_model.py` |
| Top forecast destination, actual ÷ forecast | 1.03× (middle half 0.87–1.20) | `travel_model.py` |
| Block gains: distance / border / commuting | +0.994 [+0.605, +1.370] / +0.185 [−0.048, +0.411] / +0.474 [+0.266, +0.718] | `travel_model_dc_test.py selection` |
| Nested guard, 24 exploratory candidates | change −0.061 [−0.205, +0.096]: none adopted | `combined_marginal_test.py travel_nested_all` |
| Distance elasticity at 25 mi, mean-size home county: metro / nonmetro | −0.98 (s.e. 0.11) / −0.47 (0.17) | `travel_model.py` |
| Commuting out / in | +0.284 [+0.194, +0.373] / +0.200 [+0.127, +0.273] | `travel_model.py` |
| Stability, Jul–Sep from Jan–Jun: model / persistence error | 2.95 / 1.46 | `travel_model.py` |
| Kansas share of observed out-of-county visits: all Missouri / 14 border counties / Jackson | 12.3% / 34.9% / 52.5% | `travel_model.py` |

The border block's held-out gain interval includes zero; it is kept as a core term by theory (coefficient +0.465
[+0.337, +0.594]).

**Coverage** — PPML of March story-county pairs; core gravity blocks, newsroom-county and covered-county fixed
effects, log visits (where > 0), zero-visit indicator; hypothesis term log visits × nonmetro newsroom county (RUCC
4–9); errors clustered by newsroom county:

| Measure | All outlets | Print and digital | Script |
|---|---|---|---|
| Stories / newsroom counties / out-of-county story-county pairs | 14,877 / 88 / 10,282 | 8,301 / 88 / 6,674 | `coverage_model.py` |
| Elasticity of stories to visits, metro newsroom counties (27) | 0.49 (s.e. 0.070; 0.36–0.63) | 0.52 (0.086; 0.35–0.69) | `coverage_model.py` |
| Elasticity, nonmetro newsroom counties (61) | 0.25 (s.e. 0.063; 0.13–0.38) | 0.26 (0.064; 0.14–0.39) | `coverage_model.py` |
| Hypothesis term, nonmetro − metro | −0.241 (s.e. 0.040, p < 0.001) | −0.258 (0.059, p < 0.001) | `coverage_model.py` |
| Hypothesis term, gain on the primary metric | +0.125 [+0.048, +0.202] | +0.090 [+0.006, +0.173] | `coverage_model.py` |
| Twice the visits, metro / nonmetro | 1.41× / 1.19× the stories | 1.43× / 1.20× | `coverage_model.py` |
| Commuting in / out | +0.41 (s.e. 0.073) / −0.03 (n.s.) | +0.38 / −0.03 | `coverage_model.py` |
| Held-out error, destinations with 1%+ of visits (primary) | 4.49 [4.04, 4.98] | 4.59 [4.13, 5.06] | `coverage_model.py` |
| Held-out error, all destinations (beside) | 0.915 [0.846, 0.982] | 0.941 [0.874, 1.004] | `coverage_model.py` |
| Saturation, nested guard | change +0.011 [−0.005, +0.027]: not supported | change −0.002 [−0.032, +0.026] | `coverage_saturation_test.py` |
| Pooled elasticity, no hypothesis term (sensitivity) | 0.36 (s.e. 0.064) | 0.35 (0.069) | `coverage_model.py` |

**Spillover** — outlet-level logistic: spillover ~ broadcaster + log(1 + print and digital outlets in the county),
both hypothesis terms (`spillover_common.FINAL`); mention 0.5 and Sports 0.5 are definitions:

| Measure | Value | Script |
|---|---|---|
| Outlets with 10+ placed stories | 128 in 72 counties (27 broadcasters), 12,192 stories | `spillover_outlets.py` |
| Fitted (well collected, 20+ placed stories, not Three Rivers Publishing) | 85 outlets, 48 counties (24 broadcasters) | `spillover_outlets.py` |
| Broadcaster | +0.667 (CRV3 s.e. 0.148, p < 0.001; bootstrap CI +0.388 to +0.939); gain +1.55 [+0.36, +2.70] | `spillover_outlets.py` |
| Print and digital outlets in the county, log(1 + count) | −0.387 (CRV3 s.e. 0.124, p 0.003; CI −0.655 to −0.232); gain +1.04, interval lower bound −0.05 to +0.01 by bootstrap seed | `spillover_outlets.py` |
| Held-out error, mean / median (primary: mean), honest: nested search B | 6.57 / 5.50 | `spillover_nested_selection.py` |
| — fitted model, not nested | 5.98 / 4.66 (intercept only 7.49 / 6.23); skill +0.202; out-of-sample R² +0.360 | `spillover_outlets.py` |
| Nested guard from the hypothesis pair | 6.05 / 5.05; change +0.07 [−0.38, +0.60]: none adopted | `spillover_rule_selection.py` |
| Actual / held-out expected: Audrain, Boone, Osage, Cole, Jackson | 19.5 / 22.5%, 28.7 / 26.4%, 25.6 / 25.3%, 23.1 / 25.4%, 21.9 / 19.1% | `spillover_outlets.py` (`spillover_quoted_rows.csv`) |
| Leave one TV market out (7 markets with 3+ outlets) | in sample 5.9, held out 6.2, intercept only 7.4 | `spillover_dma_holdout.py` |
| Springfield region (Greene, Webster, Barry) held out | 8.0; region 24% actual, 26% expected | `spillover_outlets.py` |
| Mean spillover rate | 24.7% | `spillover_outlets.py` |

**Public-data travel model** — the study's question is how close a model built from public data gets to the
Advan-fitted model, and how much of the gap Advan-learned corrections close. The public model is not claimed to beat
the Advan-fitted model, and does not in any class. Every score out of sample for the county scored:

| Model | Missouri (115): all Advan destinations (primary) | common set | log-ratio | Kansas (105): all destinations | common set |
|---|---:|---:|---:|---:|---:|
| Advan-fitted (counties held out) | 3.31 | 3.38 | 0.35 | 3.06 | — |
| Public (Missouri: Stage 1 nested; Kansas: Missouri settings, nothing tuned) | 4.64 | 4.75 | 0.58 | 3.78 | — |
| Public, Stage 1 per outer fold (base of the corrections) | 4.67 | 4.77 | 0.58 | — | — |
| + Advan-learned segment corrections (C, transferable; outer loop; Kansas: learned in Missouri) | 4.07 | 4.16 | 0.51 | 4.05 | — |
| + one factor per destination county (A, Missouri only; outer loop) | 3.46 | 3.53 | 0.44 | — | — |
| Public − Advan-fitted | +1.34 [+0.87, +1.82] | +1.37 [+0.90, +1.87] | +0.23 [+0.19, +0.27] | +0.72 [+0.30, +1.15] | +1.04 [+0.53, +1.54] |
| Corrected (C) − fold base | −0.60 [−0.96, −0.25] | −0.61 [−0.98, −0.26] | −0.07 [−0.09, −0.05] | +0.27 [−0.03, +0.58] (vs public) | — |
| Share of the gap closed by corrections | C 44% [22, 67]; A 89% [63, 117] | C 44% [22, 66] | C 30% [21, 37]; A 60% [50, 70] | none (−37% [−124, 4]) | — |
| Advan share outside the common set, per county | 1.34% (max 8.2%) | | | 9.08% (max 40.7%, Thomas) | |

Scripts: `public_stage1_nested.py`, `public_adjusted_nested.py`, `score_segments.py`, `public_vs_advan_compare.py`
(Missouri); `score_ks.py`, `ks_advan_fitted.py`, `transfer_adjustments.py` (Kansas); metrics in `public_scoring.py`.

**Civic interest areas** — travel patterns by non-negative matrix factorization per TV market
(`flows/travel_patterns.py`); the paper's map is the network-tie area drawn as a probability surface over a 432-member
settings ensemble (`flows/area_ensemble.py`); the area as stated is the core, p ≥ 0.5. **K rule (user, 2026-10-24,
option A, per town):** K = the largest K at which every pattern holds 10%+ and 1,000+ of the residents and 10%+ of
the travel of at least one study town in the market (the same town for all three), and replicates at matched cosine
0.9+ across random starts and between independently refitted odd and even months. A share of the market was
rejected (it depends on which home counties form the market); a 5% level was rejected; held-out month error is a
persistence diagnostic only.

| Market | K | K + 1 fails on |
|---|---:|---|
| Columbia-Jefferson City | 2 | odd/even months (0.87) |
| Springfield | 7 | starts (0.20), months (0.25) |
| Paducah-Cape Girardeau | 3 | no town (best: Marble Hill, 643 residents), months (0.72) |
| Ottumwa-Kirksville | 2 | no town (best: Lancaster, 695 residents) |
| Joplin | 4 | no town (best: Neosho 4%) |
| Kansas City | 5 | no town (best: Independence 10% of residents, 9% of travel), months (0.87) |
| St. Joseph | 5 | months (0.87) |

58 areas in 36 study towns (`flows/market_patterns.py`).

| Measure | Columbia | Mexico | Linn | Script |
|---|---:|---:|---:|---|
| Areas | 1 ("Columbia's civic interest area") | 1 | 1 | `flows/market_patterns.py` |
| Residents allocated to the area (ACS; share of the town's) | 103,086 (93%) | 5,685 (86%) | 1,172 (85%) | `flows/travel_patterns.py` |
| Core, p ≥ 0.5: km² / people inside | 1,380 / 224,723 | 1,000 / 141,850 | 1,122 / 167,069 | `flows/area_ensemble.py` |
| p ≥ 0.8: km² / people inside | 696 / 182,057 | 374 / 13,233 | 468 / 46,550 | `flows/area_ensemble.py` |
| Replicability, independent halves: r(p); Jaccard of the core (home excluded) | 0.99; 0.90 | 0.96; 0.85 | 0.86; 0.66 | `flows/area_ensemble.py` |
| Adopted-setting drawing: km²; share in the core; outline replicability | 1,146; 90%; 0.85 | 807; 88%; 0.74 | 754; 90%; 0.55 | `flows/area_ensemble.py`, `analysis/confidence_layer.py` |
| Boone hexagons: core / p ≥ 0.8 / adopted-setting outline | — | 34 / 1 / 114 | (core 32) | `flows/area_ensemble.py` |
| Tie-market accuracy, public vs Advan (town) | 0.13 | 0.41 | 0.75 | `analysis/tie_footprint.py` |

Tie markets, 36 towns: accuracy median 0.62 (mean 0.614), replicability median 0.89 (`analysis/tie_footprint.py`).
Supply (coverage density, balanced diet) is not a result of this paper: see Supply (QA only; next paper).

## Measurement corrections

| Change | Why |
|---|---|
| Stories credited to the **Missouri School of Journalism analysis**, never LNIC | Attribution |
| **The Maneater and CoMoBuzz** excluded from Boone's coverage | Decision for these analyses |
| **Statewide outlets are no county's local news** (2026-10-17): Missouri Business Alert (filed under Boone); The Missouri Independent, Missouri Net, Missouri Scout, The Missouri Times (filed under Cole) (`excluded_outlets.EXCLUDE`) | They cover the state, not a county |
| **Campus newspapers are not local news anywhere** (2026-10-24): the 11 student newspapers owned by a college or university (`CAMPUS`, part of `EXCLUDE` in `excluded_outlets.py`) are out of coverage, the spillover outcome and fit, and every county outlet count | Same footing as The Maneater. University-licensed public broadcasters (KBIA, KCUR, KRCU, KSMU, KXCV, STL Public Radio) and the School of Journalism's community newsrooms (Columbia Missourian, Boone County Journal, KOMU) stay |
| **Dos Mundos Bilingual Newspaper and KHQA 7 excluded** (user, 2026-10-24; `EXCLUDE`): Dos Mundos (filed in Wyandotte County, Kansas; 4 March stories) is mostly Spanish-language, outside the English-language corpus the models describe; KHQA 7 (Quincy, Illinois; 45 stories; licensed to Hannibal) is an Illinois newsroom (51 of its 65 March county mentions are Illinois counties) | Both were already outside every fit as out-of-state filings; no figure moves |
| **Mid Rivers Newsmagazine → St. Charles; Greene County Commonwealth → Greene** (2026-10-24; `excluded_outlets.HOME_COUNTY`, `home_fips`), in coverage, spillover and the area maps, both fitted | Each is published outside the county it covers (19 of 26 and 20 of 23 March stories centred in the covered county) |
| **St. Louis city and county treated as one unit** for spillover and crossover (crossover: before the left-the-county test, 2026-10-24) | Every St. Louis outlet is registered in St. Louis County, so city stories counted as "another county" (St. Louis print spillover read 85%; merged, 25% — 2026-10-16 measure, not rerun) |
| **Other-state counties within 60 miles count as spillover** | Kansas City print outlets read 18% on Missouri counties only and 44% with Kansas (2026-10-16 measure, not rerun); border regions cross the state line |
| **One home rule for every outlet** (spillover, 2026-10-24): the county filed under, every other county holding part of its registry city, and Kansas City, Kansas (Wyandotte) for Kansas City, Missouri outlets | A story about another part of the outlet's own city is not spillover |
| **Home county excluded from every travel–coverage comparison** | Residents live in their home county all of the time; a share of visits says nothing about how much it matters to them. Home and away story counts are reported for reference only |
| **Coverage counts a story's central place as well as the places it mentions** | The story map's county layer omits each story's central place; Osage had 13 placed stories on that layer against 40 with both |
| **Hospital indicator removed** | It was a facility count from a CMS file, not travel data, incomplete (it missed Capital Region Medical Center), and read as a healthcare finding the data cannot support |
| **One travel outcome in every script** (2026-10-24): `visits_statewide` × (1 − highway-stop discount) | Several scripts had used undiscounted or uncalibrated visits; the county factor measured home detection |
| **Commuting from LODES primary jobs (JT01)** (2026-10-24) | JT00 counts a worker once per job |

## Population calibration

Advan Neighborhood Patterns Plus is "normalized against panel size and country population" (Dewey's Advan page): a
national scaling, not a local one. The 2026-10-16 factor — residents seen in their own block group ÷ ACS population —
measures home detection as well as panel size, and is replaced as the device → person scale.

| Factor (`calibration_county_month.csv`) | Definition | County-months: median, middle 80%, range | County medians |
|---|---|---|---|
| `factor` (2026-10-16; kept, not adopted) | seen at home ÷ ACS county population | 1.94; 1.09–3.18; 0.19–12.73 | 0.24 (St. Louis city) – 10.78 (Scotland) |
| `factor_trimmed` (sensitivity) | as `factor`, phantom home block groups left out | 1.82; 1.06–2.71; 0.19–6.86 | 0.24–3.85 |
| **`factor_statewide` (adopted)** | Missouri sum over home block groups of the largest count of their residents in any one block group ÷ Missouri ACS population; one value per month | Jan 1.84, Feb 1.90, Mar 2.01, Apr 2.32, May 2.09, Jun 2.04, Jul 1.75, Aug 1.73, Sep 1.70 | one value per month |

- **Phantom home block groups** (`home_bg_month_mo_2026.csv`, `phantom`): residents seen at home above 3× the block
  group's expected residents (ACS population × the month's statewide units per resident). 1,469 of 44,229 block
  group-months (3.3%), holding 10.7% of all devices seen at home; 84 of them have no ACS population. Scotland: 4 of
  its 6–7 block groups each month (291994801001 at 7.9×, 4802002 at 7.7×, 4801003 at 6.1×); its factor is 10.78 as
  published, 3.39 trimmed. Phantom devices are seen at home and rarely elsewhere, so they enlarge any denominator
  taken from seen-at-home.
- **Under-detection at home:** St. Louis city's factor is 0.19–0.25; in 82–87% of its block groups more residents are
  seen in one other block group than at home. St. Louis city and county together are seen at 0.33× the statewide rate
  per ACS resident (0.44× counting the busiest block group anywhere).
- **Home block groups with no own key** (residents never reported at home), logged by `build_calibration.py`: Jan 15,
  Feb 11, Mar 14, Apr 9, May 9, Jun 6, Jul 12, Aug 20, Sep 14; mostly St. Louis city (29510), with the same few
  elsewhere every month (290370612003, 290950102033, 291650303064, 291892131022). Kept with `own` = 0 and `own_key` = 0.
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
| Lancaster | 1 | 1,079 | 1,079 | 509 | 716 |
| Webb City | 8 | 12,402 | 13,442 | 16,613 | 12,388 |

  Linn's block group is seen at home at 2.0× the statewide rate and Lancaster's at 0.7×, so Advan-based counts of
  single-block-group towns stay unreliable under any factor. Lancaster has 716 residents by ACS and cannot hold a
  1,000-resident pattern.
- **Kansas** (`calibration_county_month_ks.csv`, same definitions): `factor` median 2.29, middle 80% 1.29–4.60, county
  medians 0.53–8.12; units per resident 1.92–2.73 by month. The Kansas transfer test uses `visits_statewide`.
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

## Pass-through discount

`build_road_stop_share.py` → `road_stop_share.csv`. Share of out-of-county calibrated visits (January–September)
removed, pairs with 200+ store-level visitors:

| Definition | Out-of-county road-stop share (within home county) | Visits removed | Pairs discounted |
|---|---:|---:|---:|
| Old codes (4471, 4571, 445131, 722513), statewide 12.5% (`discount_old`) | 12.5% (13.8%) | 2.32% | 3,313 |
| Codes fixed: + convenience stores 445120, statewide norm (`discount_codes`) | 16.5% (18.2%) | 3.35% | 3,578 |
| Highway stops: codes fixed, within 1 km of an Interstate or US highway, statewide norm (`discount_highway_statewide`) | 11.6% (11.1%) | 2.98% | 3,203 |
| **Highway stops, expected share from the destination's own store mix (`discount`, adopted)** | | **1.74%** | **2,619** |

57.2% of 12,094 road-stop stores are within 1 km of an Interstate or US highway. Expected share for destination j =
the highway-stop share of j's residents' visits to j's places × the statewide ratio of out-of-county to within-county
highway share (1.04). On the statewide scale the adopted discount removes 2.2% of out-of-county visits. Switch:
`gravity_terms.travel_visits(..., discounted=False)` is the undiscounted outcome (the primary sensitivity); `disc=`
takes any `discount_*` column.

## Travel model

**Adopted: doubly-constrained gravity model, Poisson pseudo-maximum likelihood** (`travel_model.py`; terms, outcome,
scoring in `gravity_terms.py`).

- A fixed effect for every home county (its total travel) and every destination (its overall draw: capital,
  university, hospitals, shopping — measured from the data, not proxied)
- Pair terms (8, `gravity_terms.FACTORS`), core gravity terms by theory in three blocks: **distance** (log distance
  and its square; both again for nonmetropolitan home counties; log home population × log distance), **border**,
  **commuting** (out and in, LODES 2023 JT01)
- Distance centred at 25 miles (the visit-weighted geometric mean out-of-county trip is 26 miles), home log population
  at its mean (geometric mean 21,980): the log-distance coefficient is the distance elasticity at 25 miles for a
  metropolitan home county of mean size. Centring changes no prediction
- Outcome: `visits_statewide` × (1 − `discount`) (Pass-through discount); the discount removes 2.2% of out-of-county
  visits on this scale
- Inference: standard errors clustered by home county and by destination county
- Validation and primary metric: each home county held out (8 folds, seed 7), share-weighted absolute error of its
  destination shares over all Missouri destinations; intervals from 1,000 county bootstrap resamples, predictions held
  fixed; differences county-paired. R² against uniform shares (1 − SSE/SST) and against the fixed-effects-only model
- Selection: blocks tested as blocks; no hypothesis terms; exploratory additions only through the nested guard
- The Jan–Jun → Jul–Sep split is a stability check, not validation: persistence beats the model on it

### Validation

| Measure | Value |
|---|---|
| Held-out share-weighted error (points), primary | 3.31 [2.96, 3.64] |
| — small rural (56) / independent towns (32) / commuter (18) / hubs (9) | 3.57 [3.12, 4.07] / 2.87 [2.35, 3.41] / 3.68 [2.86, 4.59] / 2.45 [1.64, 3.47] |
| Held-out R² of shares, uniform reference | 93.7% [92.4, 94.9] |
| Held-out R² against fixed effects only | 93.7% (fixed effects only: error 16.16, R² 0.9%) |
| Big flows (forecast 5%+; 484 pairs): error; within 0.8–1.25×; actual ÷ forecast 10th–90th percentile | 3.44 [3.16, 3.73]; 51% [46, 55]; 0.61×–1.51× |
| Top FORECAST destination, actual ÷ forecast | 1.03× (middle half 0.87–1.20); 1.13× if selected on the observed share |
| Reference: destination effects + log distance only | 5.66 [5.12, 6.19]; adopted lower by 2.35 [1.86, 2.85] |
| In-sample: R² of shares; deviance | 94.7%; 62.0M |
| Stability, Jul–Sep from Jan–Jun: model / persistence | R² 93.9% / 98.7%; error 2.95 / 1.46; model − persistence +1.49 [+1.17, +1.79] |

Coefficients, Jan–Sep (two-way clustered):

| Term | Coef [95%] |
|---|---:|
| log distance (elasticity at 25 mi, metro home) | −0.978 [−1.196, −0.759] |
| log distance² | −0.265 [−0.326, −0.205] |
| nonmetro × log distance | +0.505 [+0.278, +0.732] |
| nonmetro × log distance² | −0.258 [−0.393, −0.123] |
| log home population × log distance | +0.182 [+0.129, +0.234] |
| shared border | +0.465 [+0.337, +0.594] |
| commuting out | +0.284 [+0.194, +0.373] |
| commuting in | +0.200 [+0.127, +0.273] |

Distance elasticity, home county of mean population (two-way s.e.): metro −0.49 (0.15) at 10 mi, −0.98 (0.11) at 25,
−1.35 (0.10) at 50, −1.71 (0.11) at 100; nonmetro +0.49 (0.25), −0.47 (0.17), −1.20 (0.14), −1.92 (0.17). Travel from
nonmetropolitan counties barely falls off over the first 25 miles and falls off faster than metro travel beyond about
50. The positive nonmetro value at 10 miles is the quadratic's end point (closest pair 7.5 miles), not a finding.

With no travel data for a county, the model places its destination shares to within 3.3 points (share-weighted) and
its top destination without bias (1.03×). For a county whose own travel is observed, the observed shares are the
better figure: the model is not a forecasting improvement on them.

### Selection

Blocks, each removed from the adopted model (`travel_model_dc_test.py selection`; held out, county-paired):

| Block removed | Held-out error | Gain from the block [95%] |
|---|---:|---:|
| none (adopted) | 3.307 | |
| distance (five terms) | 4.301 | +0.994 [+0.605, +1.370] |
| border | 3.492 | +0.185 [−0.048, +0.411] |
| commuting (out and in) | 3.781 | +0.474 [+0.266, +0.718] |
| all pair terms (fixed effects only) | 16.159 | +12.852 [+11.110, +14.489] |

The border block's gain interval includes zero (coefficient +0.465 [+0.337, +0.594]); it is kept as a core term by
theory and is the one block whose predictive contribution is not established.

Exploratory additions, nested guard (`combined_marginal_test.py travel_nested_all`; 24 candidates — eight route and
area terms alone and together, three competing-destination terms, ten home-county ACS measures × distance, two
hospital terms — chosen inside each outer training set on 7 inner folds):

| Procedure | Held-out error | Change vs adopted [95%] |
|---|---:|---:|
| Adopted (same folds) | 3.307 | |
| **Nested, lowest inner error (deciding)** | 3.246 | −0.061 [−0.205, +0.096] |
| Nested, interval rule applied inside the training counties | 3.276 | −0.031 [−0.157, +0.124] |
| One at a time, not nested (reference only): nearest comparable alternative | 3.260 | −0.047 [−0.085, −0.009] |

Inner choices: "on the way to a bigger centre" in 5 of 8 outer folds, "on-the-way weight" 1, all eight route/area
terms 2. **No addition adopted.** The one-at-a-time test is not a criterion; the nearest-alternative term is rejected
by the nested guard like every other candidate.

### Sensitivities

`travel_model.py`; distance elasticity at 25 mi, mean-size home county (two-way s.e.); held out:

| Outcome | Metro | Nonmetro | Error | R² | R² vs fixed effects |
|---|---:|---:|---:|---:|---:|
| **Adopted: `visits_statewide`, highway discount** | −0.978 (0.111) | −0.473 (0.168) | 3.31 | 93.7% | 93.7% |
| County factor (`visits`, 2026-10-16) | −0.904 (0.083) | −0.475 (0.135) | 3.28 | 93.7% | 94.8% |
| Undiscounted (primary sensitivity) | −0.971 (0.109) | −0.484 (0.165) | 3.21 | 93.8% | 93.7% |
| Old discount (`discount_old`) | −0.963 (0.112) | −0.462 (0.168) | 3.30 | 93.9% | 93.8% |
| Uncapped destinations only | −1.051 (0.118) | −0.634 (0.158) | 3.15 | 94.5% | 94.6% |
| Distinct people (`people_lower`; St. Louis one unit; undiscounted) | −0.658 (0.107) | −0.567 (0.134) | 1.74 | 89.2% | 88.8% |

- The elasticity moves by less than one standard error across scales and discounts.
- Uncapped destinations: decay steeper, nonmetro −0.63 against −0.47. Capped destination block groups (Advan keeps
  2,000 home block groups per row) are the busiest, mostly reached from far away; capping drops distant homes, and
  leaving them out removes part of the long-distance tail.
- Distinct people: decay flatter for metro homes (−0.66) — a visit count weights frequent nearby trips, a person count
  does not. The lower held-out error (1.74) is on a different, smoother outcome, not a better model.
- Discount definitions (`travel_model_stop_discount_test.py`, each against its own outcome): undiscounted 3.21, old
  3.30 (removes 3.04%), codes fixed 3.38 (4.38%), highway at the statewide norm 3.38 (3.86%), adopted 3.31 (2.23%).
  Discounting does not make the outcome easier to predict; it is a measurement correction, not a fit choice.

### Out-of-state travel: Kansas

Missouri residents' visits to Kansas block groups (`neighborhood/raw_ks/`), statewide scale, undiscounted, Jan–Sep
(`travel_model.py`), share of observed out-of-county visits (Missouri + Kansas): Jackson 52.5%, Platte 30.3%, Cass
28.7%, Clay 26.9%, Buchanan 24.9%, Bates 22.6%, Vernon 22.3%, Jasper 20.1%, Barton 19.8%, Andrew 9.5%, Holt 8.8%,
Newton 8.0%, Atchison 7.2%, McDonald 7.0%; the 14 border counties 34.9%; all Missouri 12.3%.

- Every travel share in this log is a share of out-of-county visits to **Missouri** counties. For Jackson that is under
  half of its observed out-of-county travel. Illinois, Iowa, Arkansas, Oklahoma and Nebraska are not in the data, so
  the eastern and southern border counties are understated by an unmeasured amount.
- The outcome is not renormalised: with home-county fixed effects renormalising only rescales each county's shares by a
  constant. Comparisons of a share's size across counties use the Kansas-inclusive denominator or say they exclude
  Kansas.

### Steps that led there

Held out (`travel_model_compare.py`, `travel_model_dc_test.py`):

| Version | In-sample deviance | Held-out R² | Held-out error [95%] | Top forecast destination (held out) | Big flows within 0.8–1.25× |
|---|---:|---:|---:|---:|---:|
| Plain gravity: population + distance (origin effects) | 246.3M | 72.3% | 8.13 [7.29, 8.99] | 1.26× | 18% |
| + border, rural home × distance, metro, stores (singly constrained, `gravity_terms.SINGLY`) | 184.3M | 80.5% | 6.46 [5.77, 7.17] | 1.15× | 29% |
| Singly + area centre + curved distance | 140.1M | 85.4% | 5.52 [4.91, 6.16] | 1.16× | 33% |
| Doubly constrained: distance, rural × distance, border | 103.3M | 88.0% | 4.86 [4.35, 5.38] | 1.06× | 37% |
| + curved distance | 83.8M | 90.6% | 4.22 [3.81, 4.68] | 1.05× | 40% |
| + larger home counties travel farther (adopted before 2026-10-18) | 69.4M | 92.1% | 3.78 [3.41, 4.15] | 1.00× | 43% |
| **+ commuting out and in (adopted)** | **62.0M** | **93.7%** | **3.31 [2.96, 3.64]** | **1.03×** | **51%** |

The singly-constrained model was abandoned on held-out error (6.46 against 3.31; R² 80.5% against 93.7%); the 1.6×
under-prediction once given as the reason is superseded (appendix). The "Osage residents go to Jefferson City twice as
often as expected" figure came from that model and stays withdrawn: under the adopted model Osage → Cole is 1.04
in-sample, 1.13 held out. In the singly-constrained model, metro destination −0.08 (p = 0.57) and jobs per resident
(p = 0.71) add nothing; stores per resident +0.73 (p = 0.002). The doubly-constrained model absorbs all destination
attributes.

### Rejected

Each added to the adopted model; change in held-out error [95%]; coefficient (two-way p). All are also inside the
nested guard above, which is the deciding test.

| Tested | Result | Script |
|---|---|---|
| Hospital indicator | See measurement corrections; hospital terms under County characteristics | — |
| Same metro/micro area | +0.008 [−0.068, +0.089]; −0.136 (p = 0.06) | `travel_model_hub_test.py` |
| Nearest area centre | −0.015 [−0.079, +0.048]; p = 0.12 | `travel_model_hub_test.py` |
| Adjacent area centre | −0.005 [−0.036, +0.026]; p = 0.33 | `travel_model_hub_test.py` |
| Intervening opportunities (population closer than the destination) | +0.032 [−0.014, +0.076]; p = 0.38 | `travel_model_hub_test.py` |
| All four | +0.034 [−0.063, +0.129] | `travel_model_hub_test.py` |
| Driving time between main towns (OpenStreetMap routes) in place of straight-line distance | +0.079 [−0.113, +0.310] | `travel_model_drive_test.py` |
| Driving time + on the way to a bigger centre / weighted | −0.055 [−0.268, +0.209] / −0.075 [−0.320, +0.184] | `travel_model_drive_test.py` |
| Nearest comparable alternative / in another direction (60°+ off the bearing) | −0.047 [−0.085, −0.009] / −0.035 [−0.069, +0.001] | `travel_competing_test.py` |
| Fotheringham C_ij = Σ(k≠i,j) W_k/d_jk (Haynes & Fotheringham 1985) | +0.031 [−0.063, +0.140]; −1.07 (p < 0.001) | `travel_competing_test.py` |
| Business gaps (CBP 2022) | Not identifiable: log(dest + 1) − log(origin + 1) is absorbed by the two sets of fixed effects (design rank 237 of 243) | `travel_business_test.py` |
| Origin-class-specific pair terms, k = 2 / 3 / 4 | −0.00 [−0.14, +0.12] / +0.04 [−0.13, +0.20] / +0.09 [−0.09, +0.26]; k = 4 independent towns +0.40 [+0.06, +0.74], hubs −0.32 [−0.69, +0.01] | `travel_county_class_model.py` |
| Work and non-work apart: non-work with / without commuting | −0.00 [−0.01, +0.01] / +0.44 [+0.24, +0.67] | `travel_purpose_split_test.py` |
| All eight route/area terms together | −0.11 [−0.31, +0.09] | `combined_marginal_test.py` |

Main destinations, actual ÷ expected share, adopted (in-sample / held out; `travel_competing_test.py`): Osage → Cole
1.04 / 1.13, Osage → Boone 1.64 / 1.56, Audrain → Boone 1.02 / 1.03, Audrain → Callaway 1.44 / 1.35, Audrain → Marion
2.21 / 2.13, Boone → Cole 0.71 / 0.67, Boone → St. Louis County 1.28 / 1.29.

The routing (`build_drive_routes.py` → `drive_od.csv`) is kept: it confirms, for example, that Mexico → Columbia
(38 minutes) runs through Callaway County. Half of Audrain residents' Callaway visits are in Kingdom City; the share of
that pair's visits the discount removes was 20% under the 2026-10-16 definition (not rerun); the rest (Fulton is 22
minutes from Mexico) is ordinary local travel.

### Small counties and pair-level commuting

The pooled travel model fits large counties best: Poisson weights by count, so big flows drive the fit. Tested for the
counties it serves worst, public data only. Tiers: k-means on log population (ACS 2020–2024) and commuting outflow
(LODES 2023) (`county_class_k4.csv`): small rural 56 (median 10,600, 67% commute out), independent towns 32, commuter
18, hubs 8. The file has 114 rows, with no row for St. Louis city; scored, St. Louis city is a ninth hub and St.
Louis city and county are scored apart (115 home counties: hubs 9).

| Tested (held out; share-weighted error, change [95%]) | Result | Script |
|---|---|---|
| **Commuting block, added to the pre-commuting model** | **all 3.78 → 3.31 (−0.47 [−0.72, −0.27]); small rural 4.06 → 3.57 (−0.49 [−0.83, −0.13]); independent towns 3.33 → 2.87 (−0.46 [−0.73, −0.17]); commuter 4.22 → 3.68 (−0.54 [−1.19, +0.04]); hubs 2.78 → 2.45 (−0.33 [−1.39, +0.55]); small rural top-3 (forecast-ranked) 4.97 → 4.36** | `travel_commute_pair_test.py` |
| Separate model for small origins (< 15,000) into larger counties | best (size rank within 60 mi) 3.77 [3.22, 4.34] against the pooled model's 3.46 [2.91, 4.08] on the same pairs | `travel_small_origin_model.py` |
| Measured destination draw + Fotheringham in place of destination effects | small origins +0.60 [+0.20, +1.02]; others +1.18 [+0.51, +1.94] | `travel_small_county_test.py` |
| Destination effects shrunk toward that model (alpha 1e-4 to 1e-2, all shown) | Jul–Sep 3.20 against 3.14 (small origins) | `travel_small_county_test.py` |
| Tier and county pull of destination jobs and retail (LODES; CBP 2022), nested guard | change +0.045 [−0.087, +0.199] all counties; small rural −0.115 [−0.247, +0.019]: none adopted (table below) | `travel_tier_pull_cv.py` |
| Distance to the destination's job hub (JT01) from where workers live; nearest, farthest edge | small rural: 3.47 centroid against 3.48–3.51 (every interval spans zero) | `travel_distance_variants.py` |
| Blend of the county's own Jan–Jun shares with the model (k chosen on Jan–Apr → May–Jun) | Jul–Sep 1.46, equal to persistence (−0.01 [−0.03, +0.02]) | `travel_blend_test.py` |

`travel_tier_pull_cv.py` (every county held out, 8 folds; all Missouri destinations; top-3 = each small rural county's
three largest forecast destinations; 320 fits from full-data start values, all converged):

| Model | All counties (115) | Small rural (56) | Top-3, small rural | Change vs adopted, all [95%] |
|---|---:|---:|---:|---|
| Adopted (8 FACTORS) | 3.307 | 3.572 | 4.36 | |
| + tier pull (one at a time, not nested) | 3.260 | 3.478 | 4.08 | −0.047 [−0.141, +0.053] |
| + county pull (one at a time) | 3.339 | 3.483 | 4.14 | +0.032 [−0.109, +0.186] |
| + tier + local (one at a time) | 3.380 | 3.510 | 4.10 | +0.074 [−0.069, +0.229] |
| Theory, no destination effects (one at a time) | 3.865 | 3.986 | 4.76 | +0.558 [+0.162, +0.957] |
| **Nested (lowest inner error; tier pull in 6 folds, county pull 1, adopted 1)** | 3.351 | 3.456 | 4.07 | **+0.045 [−0.087, +0.199]** |

Pair-level commuting is the first public measure that predicts a county's travel markedly better without its own
travel data; it is a core block in the shared gravity terms (`gravity_terms.py`), so the travel and coverage models
both carry it. Travel: out +0.284 [+0.194, +0.373], in +0.200 [+0.127, +0.273] (two-way). The gain is clear for all
counties together, small rural counties and independent towns; for commuter counties and hubs (18 and 9 counties) the
intervals include zero. Coverage: commute in +0.41 (s.e. 0.073, clustered by newsroom county), out −0.03 (n.s.):
newsrooms cover the counties whose workers commute into theirs; the block is a control kept by theory (gain −0.017
[−0.124, +0.087]; Wald χ² 36.5, p < 0.001). Commuting explains Osage's travel to Jefferson City (Osage → Cole 1.04
in-sample); travel to Columbia, where few Osage residents work, is for shopping, health care and the university and
stands out (Osage → Boone 1.64). Spillover does not use the travel model.

### Public-data travel model (Stage 1) and Advan-learned corrections (Stage 2), 2026-10-18; revised 2026-10-24

Question: how close a travel model built from public data alone gets to the Advan-fitted model, and how much of the
gap Advan-learned corrections close; both with intervals. The public model is not claimed to beat the Advan-fitted
model. Outcome: the travel model's (`gravity_terms.travel_visits`), each home county's out-of-county Missouri
destination shares, January–September 2026. Every score is out of sample for the county scored:

| Element | Rule (2026-10-24) |
|---|---|
| Primary metric (declared) | Share-weighted error, 100 × Σ a\|p − a\| (points), over ALL Advan destinations in Missouri: a pair outside a model's support counts with model share 0 |
| Beside it | The same on the common destination set (the public model's destinations, counties within 200 miles of the tract; Advan and the Advan-fitted model renormalised over it; outside it 2,968 pairs, 1.34% of Advan share per county, max 8.2%); log-ratio error, mean \|ln(p/a)\| over pairs with Advan share ≥ 1% (p floored at 0.01%; scale-free, where the share-weighted error scales with concentration, r × HHI for a uniform relative miss r). `public_scoring.py` |
| Averaging | County mean (each home county weighs the same); St. Louis city and county scored apart (115 homes) |
| Intervals | County-paired bootstrap, 2,000 draws, 95% percentile; the all-county interval resamples within each class. * = interval excludes zero |
| Benchmark | Advan-fitted: the adopted travel model (`gravity_terms.FACTORS`), each county held out, 8 folds, seed 7 (`gravity_terms.loco`; `public_vs_advan_compare.py` → `compare_shares.csv`): 3.31 on all destinations |
| Commuting | LODES 2023 primary jobs (JT01) in every public-model script: work model (Missouri main + IL, KS, IA, AR, OK, NE, TN, KY aux; Kansas main + MO, NE, OK, CO aux), corrections, Kansas transfer and benchmark |
| Stage 1 | Each class's public setting chosen by Advan error (primary metric) with the scored county left out (nested). No Advan in any parameter; Advan chose among settings |
| Stage 2 | Corrections learned on other counties (8 folds); their structure chosen inside an outer loop; compared with the Stage 1 base of the same outer fold |

Classes (`score_segments.py`): the k-means tiers above; commuter counties split by the OMB 2023 delineation into rings
of the Kansas City and St. Louis metros (9) and rings of regional hubs or outside any metro (9).

**Public model** (`public_work_model.py`, `public_travel_tiers.py`, `assemble_public_by_class.py`), tract origins
(CenPop2020 tract centres), destinations every county within 200 miles in Missouri and the eight neighbouring states:

| Part | Public data and calculation |
|---|---|
| Work | LODES 2023 primary jobs (JT01) tract → county, Missouri main OD plus the eight neighbouring states' auxiliary files; observed flows within 90 miles, a gravity fit (conditional Poisson on distance, CBP employment, population, state line) beyond, where LODES carries employers' imputed establishment assignments |
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
`public_travel_tiers.py`, all rebuilt 2026-10-24 on the JT01 work model (recipes in `public_commands.sh`). Rule: lowest
mean share-weighted error (all destinations) over the class's other counties.

| Class | Setting chosen on all counties (used in Kansas) | Leave-one-out picks |
|---|---|---|
| Small rural (56) | observed LODES within 90 mi, 40 work days per out-of-county commuter, chained errands, Huff on sales (`_g_40_sales`) | 56 of 56 |
| Independent towns (32) | the same with decay 6 for retail, medical, specialty (`_c_40_l6all`) | 21; `_g_40_surplus` 10; `_c_hyb40_40` 1 |
| Commuter: major metro (9) | reference build, gross leakage (Huff home share), recreation and visiting ×0.5 (`_s_hr`) | 4 settings: `_s_hr` 4, `_s_ruralset` 2, `_s_circ14` 2, `_s_recvis05` 1 |
| Commuter: regional hub (9) | reference build, gross leakage, commuter classes on urban decay (`_s_commset`) | 7; `_c_hyb40_40` 2 |
| Hubs (9) | observed LODES within 90 mi, 15 work days, Huff on surplus sales (`_g_15_surplus`) | 8; `_g_25_surplus` 1 |

**Where the gap is** (2026-10-18, in-sample, old outcome, against the 5.35 reference; `public_gap_diagnosis.py`,
`public_gap_corrections.py`; not rerun): one Advan correction at a time, destination pull closes 46% of the gap, the
shape of distance decay 21%, adjacency 12%, together 68%. The public model overstates the metro cores (St. Louis City
0.23×, St. Louis County 0.50×, Jackson 0.65×) and understates regional centres and small rural destinations (Greene
1.42×; Knox, Scotland, Schuyler, Shannon 2.2–3.0×); its single power law sends twice too much to the nearest counties
and, for hubs, half the travel beyond 120 miles.

**Stage 2, Advan-learned corrections** (`public_adjusted_model.py`, applied to tract shares and rolled up):
multiplicative factors, fitted in turn and iterated, for distance band by class (learned apart for each home county's
dominant and secondary LODES commuting counties), adjacency by class, LODES commuting rank by class, destination order
by class, destination class by class; learned on the common destination set. Destination order follows the central
place hierarchy from public data (transferable definitions): metro core = central county of a metro area of 1,000,000
or more (OMB 2023; Census 2024 CBSA population); rest of such a metro; regional centre = pull factor ≥ 1 and at least
60,000 trade-area customers (taxable sales ÷ the state's per-capita taxable sales — about $1 billion in Missouri);
sub-regional town = pull factor ≥ 1; resort = marinas plus RV parks and recreational camps per resident in the top
tenth of U.S. counties (CBP 2022); local; a core or big-metro county within 50 miles of home is its own order. Modes: C
segment factors only (transferable); B + destination factor from public measures (log sales, log population,
nonmetro, log arts employment); A + one factor per destination county (Missouri only).

**Outer loop** (`public_adjusted_nested.py`). For each of the 8 folds of home counties: (1) Stage 1 is chosen on the
other 7 folds (the fold base); (2) each of 245 candidate structures is scored by inner cross-validation on the other 7
folds only (primary metric); (3) the lowest inner error is learned on the 7 folds and applied to the held-out fold, on
its fold base. Each mode chooses its own structure. Candidates: the full factorial of the refinement choices —
commuter split (none; split; split learned as independent towns; split learned as small rural) × distance by commuting
rank (0/1) × near-core order (0/1) × destination-order definitions (Missouri, regional centre at pull factor 1.1; at
1.0; transferable) × group sets (none; commuting out and in; destination order; + commuting rank; + destination class)
= 240 — plus the five rejected variants on the adopted structure (rank × order cell; destination class × band; pooled
hub factor; hub distance bands; metro-core factor).

Structure chosen per outer fold, mode C: split learned as small rural, Missouri definitions at pull factor 1.1,
commuting rank + destination order (folds 0, 1, 5; fold 2 the same on transferable definitions); the adopted structure
on Missouri definitions at 1.0 (3; 4 without the near-core order); the adopted structure with destination class × band
(6) or a metro-core factor (7). Mode A: a different structure in nearly every fold. Fold bases: the major-metro setting
differs from the all-county one in folds 0–2, the independent-town setting in 1–2 and 5–7, the hub-ring setting in
fold 1 (`_c_hyb40_40`), the hub setting in fold 7 (`_c_40_l6`) (`public_adjusted_nested_choices.csv`).

#### Missouri (115 home counties)

Share-weighted error, points, all Advan destinations (primary):

| Model | Small rural (56) | Indep. towns (32) | Commuter: major metro (9) | Commuter: regional hub (9) | Hubs (9) | All (115) |
|---|---:|---:|---:|---:|---:|---:|
| Advan-fitted (counties held out) | 3.57 | 2.87 | 4.12 | 3.25 | 2.45 | **3.31** |
| **Public, Stage 1 nested (leave one county out)** | 4.15 | 4.48 | 6.05 | 6.28 | 5.25 | **4.64** |
| Public, Stage 1 per outer fold (base of the outer loop) | 4.15 | 4.39 | 5.81 | 6.28 | 6.11 | 4.67 |
| **+ segment corrections, outer loop (C, transferable)** | 3.70 | 3.87 | 4.41 | 5.58 | 5.18 | **4.07** |
| + destination factor from public measures, outer loop (B) | 3.56 | 3.91 | 3.91 | 5.72 | 4.86 | 3.96 |
| + one factor per destination county, outer loop (A, Missouri only) | 3.12 | 3.25 | 4.44 | 6.32 | 2.53 | 3.46 |
| Public, Stage 1 in-sample (not out of sample) | 4.15 | 4.25 | 5.15 | 5.11 | 5.12 | 4.41 |
| + segment corrections, structure chosen in-sample (not out of sample) | 3.44 | 3.58 | 3.73 | 4.38 | 3.93 | 3.61 |

Gap to the Advan-fitted model, all destinations, share-weighted error [95%]:

| Model − Advan-fitted | Small rural | Indep. towns | Commuter: major metro | Commuter: regional hub | Hubs | All |
|---|---|---|---|---|---|---|
| Public nested | +0.58 [−0.00, +1.18] | +1.61 [+1.05, +2.21]* | +1.93 [+0.11, +3.76]* | +3.03 [+0.02, +6.23]* | +2.80 [+1.03, +4.94]* | +1.34 [+0.87, +1.82]* |
| Public fold base | +0.58 [−0.00, +1.18] | +1.51 [+0.96, +2.10]* | +1.69 [+0.04, +3.39]* | +3.03 [+0.02, +6.23]* | +3.66 [+1.41, +6.53]* | +1.36 [+0.89, +1.85]* |
| C outer | +0.13 [−0.40, +0.65] | +1.00 [+0.46, +1.55]* | +0.28 [−1.57, +2.41] | +2.33 [+0.33, +4.69]* | +2.73 [+1.29, +4.21]* | +0.76 [+0.36, +1.16]* |
| B outer | −0.01 [−0.57, +0.52] | +1.04 [+0.56, +1.55]* | −0.22 [−2.49, +2.17] | +2.47 [−0.13, +5.48] | +2.41 [+1.03, +3.87]* | +0.65 [+0.20, +1.07]* |
| A outer | −0.46 [−0.93, −0.03]* | +0.38 [−0.07, +0.86] | +0.32 [−1.39, +2.18] | +3.08 [+1.26, +5.03]* | +0.08 [−1.41, +1.45] | +0.15 [−0.21, +0.50] |

Corrections against their own fold base, all destinations [95%]; share of the fold base's gap to the Advan-fitted
model they close:

| Corrections − fold base | Small rural | Indep. towns | Commuter: major metro | Commuter: regional hub | Hubs | All |
|---|---|---|---|---|---|---|
| C, change | −0.45 [−0.84, −0.04]* | −0.52 [−1.18, +0.12] | −1.40 [−3.44, +0.22] | −0.70 [−2.26, +0.89] | −0.93 [−2.76, +0.82] | **−0.60 [−0.96, −0.25]*** |
| C, share of the gap closed | 77% [−46, 336] | 34% [−11, 68] | 83% [−44, 455] | 23% [−95, 100] | 25% [−49, 53] | **44% [22, 67]** |
| B, change | −0.59 [−0.98, −0.17]* | −0.48 [−1.10, +0.15] | −1.90 [−4.48, +0.12] | −0.56 [−2.52, +1.27] | −1.25 [−3.24, +0.58] | −0.71 [−1.10, −0.33]* |
| B, share of the gap closed | 101% [−52, 495] | 32% [−14, 61] | 113% [−49, 622] | 19% [−131, 130] | 34% [−38, 62] | 52% [29, 81] |
| A, change | −1.03 [−1.63, −0.44]* | −1.14 [−1.87, −0.41]* | −1.37 [−3.70, +0.83] | +0.05 [−2.39, +2.86] | −3.58 [−7.12, −0.84]* | −1.20 [−1.71, −0.73]* |
| A, share of the gap closed | 179% [14, 778] | 75% [35, 105] | 81% [−181, 303] | −2% [−397, 55] | 98% [45, 149] | 89% [63, 117] |

Shares of the gap are unstable where the gap itself is small (small rural +0.58) or the class has nine counties.

Beside the primary metric (all classes, all counties):

| | Common set, share-weighted | All destinations, log-ratio |
|---|---|---|
| Advan-fitted | 3.38 | 0.35 |
| Public nested | 4.75; gap +1.37 [+0.90, +1.87]* | 0.58; gap +0.23 [+0.19, +0.27]* |
| Public fold base | 4.77; gap +1.39 [+0.91, +1.90]* | 0.58; gap +0.23 [+0.19, +0.27]* |
| C outer | 4.16; gap +0.78 [+0.37, +1.18]*; vs fold base −0.61 [−0.98, −0.26]*, 44% [22, 66] of the gap | 0.51; gap +0.16 [+0.13, +0.20]*; vs fold base −0.07 [−0.09, −0.05]*, 30% [21, 37] |
| B outer | 4.07; gap +0.69 [+0.24, +1.11]* | 0.50; gap +0.15 [+0.12, +0.19]* |
| A outer | 3.53; gap +0.15 [−0.22, +0.51] | 0.44; gap +0.09 [+0.06, +0.13]*; vs fold base 60% [50, 70] of the gap |

- Public data alone, nothing learned from Advan but the choice among settings: 1.34 [0.87, 1.82] points from the
  Advan-fitted model on all destinations (4.64 against 3.31); the gap is largest in the regional-hub rings (+3.03) and
  hubs (+2.80), and its interval includes zero only in small rural counties (+0.58 [−0.00, +1.18]).
- The transferable corrections, structure chosen out of sample, close 44% [22, 67] of the fold base's gap (4.67 →
  4.07); with one factor per destination county (Missouri only), 89% [63, 117] (→ 3.46; remaining gap +0.15 [−0.21,
  +0.50]). On the log-ratio error the corrections close 30% [21, 37] and 60% [50, 70].
- Against the fold base the corrections reduce the error in small rural counties (both metrics) and, on the log-ratio
  error only, in major-metro rings and hubs; in regional-hub rings on neither metric (−0.70 [−2.26, +0.89]).
- Choosing out of sample costs 0.23 points at Stage 1 (in-sample 4.41 → nested 4.64) and 0.46 at Stage 2 (in-sample
  structure 3.61 → outer loop 4.07); in the nine-county classes 0.90–1.17 at Stage 1 and 0.68–1.25 at Stage 2.
- Destination-order factors (Advan / public; 2026-10-18, all counties): metro core 0.65–0.99, regional centre
  1.35–1.51, sub-regional town 1.09–1.42, local 0.88–0.98, resort 0.84–1.11 — the public model's draw is too steep in
  size and too flat in the hierarchy.

**Commuter counties.** One class held two behaviours. Major-metro rings spread travel over several metro counties and
commute to the core while visiting the nearest large county (St. Charles → St. Louis County: LODES 75%, Advan 57%;
Warren → St. Charles 34% vs 47%). Regional-hub rings send 65–73% to one hub (Polk, Newton, Christian). Split, the
metro-ring corrections bring the error within the interval of the Advan-fitted model's (C +0.28 [−1.57, +2.41], B
−0.22 [−2.49, +2.17]); the regional-hub rings are not improved by any correction out of sample, because the near-hub
relation (Jasper is 14 miles from Newton) is learned elsewhere as an overstated small neighbour.

**Refinements, 2026-10-18** (`public_adjusted_model.py`, `score_segments.py`; in-sample structure selection, outcome and
commuting of 2026-10-18, full destination set — superseded by the outer loop above, kept as the record of what was
tried):

| Change | Small rural | Indep. towns | Commuter: major metro | Commuter: regional hub | Hubs | All |
|---|---:|---:|---:|---:|---:|---:|
| Segment corrections | 3.43 | 3.52 | 3.93 | 6.40 | 3.48 | 3.73 |
| Regional centre at pull factor ≥ 1.0 (was 1.1): Jasper's pull factor is 1.08 because its own metro includes Newton | 3.41 | 3.51 | 3.94 | 6.12 | 3.48 | 3.69 |
| + a metro core within 50 miles of home is its own order | 3.35 | 3.43 | 3.88 | 5.81 | 3.68 | 3.63 |
| Transferable definitions + near core | 3.40 | 3.46 | 3.81 | 5.62 | 3.49 | 3.63 |

Every choice in this table is one of the outer loop's 245 candidates. Rejected 2026-10-18, also candidates in the
outer loop: a pooled hub relation; hub pairs with their own distance bands; a metro-core factor per class; a commuting
rank × destination order cell; destination class × distance band. The outer loop chose destination class × band (fold
6) and the metro-core factor (fold 7): the rejections were within noise. The 2026-10-18 structure rebuilt on the
current outcome and JT01 (`public_adjusted_pairs_trnear.csv`, read by `tie_footprint.py`, `public_activity_space.py`,
`directions_per_tract.py`): public base 4.47, segment corrections 3.71, + per-destination 3.54 (all destinations;
in-sample choices). Fitting the mixture weights of the public parts to Advan by class (`public_segment_weights.py`)
remains parked.

Regional-hub rings, county by county (2026-10-18): Newton (Jasper labelled sub-regional), Johnson (the core factor
learned from distant homes cut Jackson from 37% to 26%; the near-core order), Polk (Greene 52% vs 68%), Lawrence
(Barry 20% vs 9%), Stone (Taney 25% vs 19%); Webster and Callaway right on the public base.

#### Transfer test: Kansas (2026-10-18; revised 2026-10-24)

Advan Neighborhood Patterns Plus, Kansas destination block groups, January–September 2026 (`neighborhood/raw_ks/`),
plus Kansans' visits to Missouri from the Missouri files (`build_ks_od.py` → `od_ks_2026.csv`). Outcome:
`visits_statewide`, calibrated with the Kansas factors (`calibration_county_month_ks.csv`, `factor_statewide`) on the
same statewide device → person basis as Missouri; not pass-through discounted (no Kansas road-stop shares). Kansas
public inputs: LODES 2023 JT01, Kansas main OD and the MO, NE, OK, CO auxiliary files; CenPop2020 Kansas tracts; ACS
2020–2024 tract and county (B19301) tables; Kansas Department of Revenue County Trade Pull Factors FY2025
(`build_ks_pull_factors.py`). County classes by nearest Missouri class centre on log population and commuting outflow
(`build_ks_county_classes.py`): population ACS 2020–2024 B01003 in both states; outflow on all jobs (JT00), as the
Missouri class centres were built: 30 small rural, 63 independent towns, 4 commuter, 8 hubs.

Applied unchanged from Missouri: each class's Stage 1 setting chosen on all Missouri counties, built for Kansas
(`public_travel_tiers.py STATE=20`, `assemble_public_by_class.py STATE=20 OUTTAG=_nested`), and the transferable
structure with the lowest 8-fold score on all Missouri counties — the adopted structure with destination class ×
distance band (3.62) — learned on all Missouri counties (`public_adjusted_nested.py` → `segment_corrections_mo.pkl`;
`transfer_adjustments.py`). Kansas is held out entirely, so both choices are out of sample for it. Benchmark:
`ks_advan_fitted.py`, the adopted model's eight terms fitted to Kansas Advan, counties held out (8 folds), destinations
within 250 miles, every fold converged. Scored by `score_ks.py`. Advan share outside the common destination set
(public: within 200 miles of a tract; benchmark: 250 miles): 9.08% per county on average, max 40.7% (Thomas) —
western Kansas travel to Wichita, Topeka and Kansas City beyond the public model's 200 miles. Classes with fewer than 5
counties are not reported as classes: the four commuter counties are listed one by one and pooled only for the
intervals.

| Kansas, share-weighted error, all destinations (primary) | Small rural (30) | Indep. towns (63) | Hubs (8) | All (105) | Butler (Wichita ring) | Leavenworth (KC metro) | Miami (KC metro) | Wyandotte (KC metro) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Advan-fitted in Kansas | 4.12 | 2.76 | 1.55 | **3.06** | 3.12 | 1.69 | 6.30 | 0.42 |
| **Public model, Missouri settings, nothing tuned in Kansas** | 3.86 | 3.85 | 2.64 | **3.78** | 6.72 | 4.14 | 5.91 | 0.79 |
| + corrections learned in Missouri | 3.65 | 4.03 | 3.68 | 4.05 | 8.19 | 7.24 | 12.47 | 4.37 |

| Kansas [95%] | Small rural | Indep. towns | Hubs | All | Commuter (4, pooled) |
|---|---|---|---|---|---|
| Public − Advan-fitted, all destinations | −0.26 [−1.15, +0.55] | +1.09 [+0.54, +1.64]* | +1.08 [+0.17, +2.19]* | **+0.72 [+0.30, +1.15]*** | +1.50 [−0.01, +3.02] |
| Corrected − Advan-fitted | −0.47 [−1.50, +0.59] | +1.27 [+0.77, +1.77]* | +2.13 [−0.10, +4.97] | +0.99 [+0.50, +1.46]* | +5.19 [+4.35, +5.90]* |
| Corrected − public | −0.20 [−0.80, +0.46] | +0.18 [−0.14, +0.48] | +1.05 [−0.62, +3.18] | +0.27 [−0.03, +0.58] | +3.68 [+2.00, +5.70]* |
| Share of the public model's gap the corrections close | −78% [−908, 867] | −16% [−66, 10] | −97% [−423, 127] | **−37% [−124, 4]** | n < 5 |
| Public − Advan-fitted, common set | −0.04 [−1.09, +0.91] | +1.51 [+0.85, +2.18]* | +1.19 [+0.30, +2.15]* | +1.04 [+0.53, +1.54]* | +1.59 [+0.29, +2.89]* |
| Public − Advan-fitted, log-ratio, all destinations | +0.21 [+0.14, +0.29]* | +0.37 [+0.30, +0.45]* | +0.28 [+0.15, +0.41]* | +0.31 [+0.26, +0.37]* | +0.11 [+0.09, +0.13]* |
| Corrected − public, log-ratio | +0.04 [+0.01, +0.07]* | +0.04 [+0.02, +0.05]* | +0.03 [−0.05, +0.09] | +0.04 [+0.02, +0.06]* | +0.17 [+0.08, +0.27]* |

- The public model's gap to the Advan-fitted model in Kansas is +0.72 [+0.30, +1.15] on all destinations (+1.04 [+0.53,
  +1.54] on the common set; Missouri, nested: +1.34 [+0.87, +1.82]); in small rural counties the interval includes zero
  on both destination sets, and the log-ratio gap does not (+0.21).
- The Missouri corrections close none of the gap in Kansas (−37% [−124, 4]; error +0.27 [−0.03, +0.58]; log-ratio
  +0.04, worse). They help counties tied to a regional centre (Cowley 10.01 → 5.04, Kearny 8.07 → 4.86, Kingman 7.19 →
  4.55, Lincoln 4.21 → 1.90, Greenwood 3.83 → 1.54: ties to Wichita, Garden City and Salina) and hurt the commuter
  counties (+3.68 [+2.00, +5.70]), the Kansas City-side hubs (Johnson 4.55 → 9.15, Douglas 1.95 → 8.24), Doniphan
  (1.28 → 7.89) and Morton (2.98 → 6.51): the core and near-dominant-county factors were learned from St. Louis and
  Kansas City as seen from Missouri, and in Kansas the 1M+ metro-core definition takes in Johnson County and Wyandotte.

#### Changes, 2026-10-24 (peer review, two rounds): public model

| Defect | Fix | Files |
|---|---|---|
| Stage 1 setting per class chosen and scored on the same counties (4.30–4.34) | Leave-one-county-out choice within the class; nested figure reported, in-sample stated as such | `public_stage1_nested.py`, `assemble_public_by_class.py` (reads the choice) |
| Stage 2 structure chosen on the score it reported | Outer loop, 8 folds; Stage 1 and the structure chosen on the other 7 folds; full factorial of 240 + 5 rejected variants | `public_adjusted_nested.py`; `public_adjusted_model.py` split into `keys/learn/apply/cv` (identical output to 1e-15 on the old inputs) |
| Corrections compared with a base they were not learned on | Compared with the fold base (`public_foldbase`) they act on | `score_segments.py` |
| No uncertainty | County-paired bootstrap, 2,000 draws, per class and all; gap and share of the gap closed with intervals | `public_scoring.py`, `score_segments.py`, `score_ks.py` |
| Class cells of 3 and 1 counties (Kansas) | Not reported as classes; listed county by county, pooled for intervals | `score_ks.py` |
| Share-weighted error scales with concentration | Log-ratio error beside it everywhere | `public_scoring.py` and every scorer |
| Destination sets differ; pairs outside a model's support dropped or renormalised away | Primary: all Advan destinations, model share 0 outside its support; the common set beside it; Advan share outside reported | `score_segments.py`, `score_ks.py`, `public_stage1_nested.py`, `public_adjusted_nested.py` (selection on the primary metric), `public_vs_advan_compare.py` |
| LODES all jobs (JT00) | Primary jobs (JT01) in the work model (both states; all 53 Missouri builds and the Kansas builds rebuilt), the corrections, the Kansas transfer and benchmark | `public_work_model.py` (`JT`), `public_adjusted_model.py`, `transfer_adjustments.py`, `ks_advan_fitted.py` |
| Outcome | Missouri: the travel model's (`gravity_terms.travel_visits`); Kansas: `visits_statewide` (Kansas factors) | `public_vs_advan_compare.py`, `ks_advan_fitted.py`, `score_ks.py` |
| `ks_advan_fitted.py`: shares from exp(lin − global max) | Each origin's own maximum; every fold's convergence asserted | `ks_advan_fitted.py` |
| `travel_tier_pull_cv.py`: standardisation on held-out counties; 6-term pre-commuting baseline; top-3 by observed share; tier ratios collinear with the destination effects | Training-fold standardisation; the adopted 8 FACTORS; top-3 by forecast; ratios dropped, hubs the reference tier; nested guard; convergence checked from full-data start values | `travel_tier_pull_cv.py` |
| Kansas classes on 2020 Census population | ACS 2020–2024 B01003 (`census_dl/acs_tract/b01003.dat`); no county moved | `build_ks_county_classes.py` |
| Runs not reproducible from the scripts | Every environment setting in the docstrings and printed at start; commands in `public_commands.sh` | `public_adjusted_model.py`, `assemble_public_by_class.py`, `transfer_adjustments.py`, `public_work_model.py` |

Also: `public_travel_tiers.py` reads the home state's classes for `URBAN_CLASSES` (was Missouri's in every state);
`transfer_adjustments.py` applies whatever structure the pickle carries; `compare_shares.csv` loses the parked
`public_segment` column; the Audrain tract print in `public_adjusted_model.py` reads `od_tract_mo_2026.csv`, now
January–July. Outputs: `public_stage1_choice.csv`, `public_stage1_nested_pairs.csv`, `public_adjusted_nested_pairs.csv`,
`public_adjusted_nested_choices.csv`, `public_adjusted_nested_configs.csv`, `public_transfer_choice.csv`,
`mo_scores_nested.csv`, `ks_scores.csv`, `ks_predictions.csv`, `ks_advan_fitted.csv`, `segment_corrections_mo.pkl`,
`public_model_pairs_tiers[_20]_byclass_nested.csv`, `public_adjusted_pairs_trnear.csv`; logs in `logs/`.

**Audrain's north/south split** is one tract (950100, Vandalia-Laddonia): 16.9% of its out-of-county visits go to
Marion against 1.4–5.0% from the other tracts; under 1% of its workers work there (2026-10-18 figures, not rerun on
January–July tracts). Its schools (Van-Far) play in the Eastern Missouri conference with Pike, Ralls, Lincoln and
Montgomery. The tract model gave 6.2% (2026-10-18 public build); county-level corrections cannot move one tract.

**Athletic conferences** (datadesk visuals 34–36, Boone, Audrain, Osage; FIPS corrected: Cooper 29053, Howard 29089):
destinations within 80 miles that share a conference got 14% more travel than the Advan-fitted model predicted,
relative to the rest (pooled log ratio +0.06 vs −0.08; Audrain 1.14 vs 0.92, Osage 1.11 vs 0.95, Boone 0.89 vs 0.92;
against the 2026-10-18 Advan-fitted model, in-sample; not rerun). Conferences are assigned by enrollment and geography
and produce recurring travel and sports coverage: a central place channel between places of the same order. Statewide
test pending (school-level: MSHSAA conference and class, NCES locations, TIGER school districts).

### Changes, 2026-10-24 (peer review, two rounds): travel model

| Change | Why |
|---|---|
| Primary validation is each home county held out (8 folds, seed 7), in `travel_model.py` and every travel script | The Jan–Jun → Jul–Sep split is beaten by persistence (R² 98.7% against 93.9%; error 1.46 against 2.95): it measures stability, not prediction |
| Persistence printed beside every Jul–Sep score | As above |
| R² = 1 − SSE/SST of shares, also against fixed effects only; the old "% predicted" was a squared correlation | A squared correlation ignores bias and scale; the fixed-effects-only model is no better than uniform shares (R² 0.9%) |
| Deviance labelled in-sample; top-destination ratio and big-flow scores computed on held-out predictions | The old table columns were in-sample |
| Big flows and each county's top destination selected on the FORECAST share | Selecting on the observed share biases the ratio upward (held out: 1.13× observed-selected, 1.03× forecast-selected) |
| Two-way clustered errors (home, destination) for every travel coefficient; naive Poisson and HC1 p-values removed | Pairs sharing a home or destination county are not independent |
| Distance terms centred at 25 miles, home log population at its mean | The uncentred log-distance coefficient was not an elasticity at any stated point |
| 95% bootstrap intervals over home counties for every held-out error and every difference | Differences such as 3.58 against 3.39 had no interval |
| Core terms tested as blocks; exploratory additions only through the nested guard; one-at-a-time and drop-one tests withdrawn as criteria | Selection procedure (user) |
| Outcome `visits_statewide` (one device → person scale per month) | The county factor measured home detection (county medians 0.24–10.78) |
| Pass-through discount `road_stop_share.discount` (highway stops above the destination's own store mix) | The old code list missed convenience stores and counted every road stop as a highway stop |
| Commuting from LODES JT01 (primary jobs) | JT00 counts a worker once per job |
| Every travel script uses the adopted outcome and the 8 adopted terms | Several scripts used undiscounted visits, uncalibrated visits or the 6 pre-commuting terms |
| Kansas destinations quantified | Missouri-only shares understate border counties' out-of-county travel |
| Singly-constrained reference defined explicitly (`gravity_terms.SINGLY`) | Two scripts' "singly constrained" or "current" rows had become the doubly-constrained pair terms without destination effects |
| Coverage rows of the all-factors test scored on destinations with 1%+ of visits, from repository code | The 2+ stories rule selected on the outcome; the earlier table came from a scratch run |

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
masked before ties are scaled. The network tie is the one of the market maps after the stage-3 changes (Revealed media
market: town travel weighted by residents, no blanket home-county outgoing tie, statewide stories out of the ties). Run: `ATTRPOP=1 REGRULE=1 BETA_IN=0.5 PUBCOL=adjusted_C OUTTAG=_pop tie_footprint.py
<region>`; settings printed at the start of every run. Replicability = Advan odd vs even months; accuracy = public vs
Advan; both median Jaccard overlap over the market's study towns.

Current results (2026-10-24, after stage 3; `logs5/tie_<region>.log`):

| 36 study towns, 7 markets | Replicability (Advan, odd vs even) | Accuracy (public vs Advan) |
|---|---:|---:|
| Kansas City (6) | 0.99 | 0.965 |
| Joplin (5) | 0.97 | 0.79 |
| Springfield (6) | 0.94 | 0.55 |
| St. Joseph (3) | 0.88 | 0.63 |
| Columbia (8) | 0.82 | 0.625 |
| Cape Girardeau (5) | 0.78 | 0.37 |
| Kirksville (3) | 0.74 | 0.61 |
| **All (median)** | **0.89** | **0.62** (mean 0.614) |

Towns: Columbia replicability 0.89, accuracy 0.13 (public area 0.16 of Advan's); Mexico 0.84, 0.41; Linn 0.89, 0.75.
Before stage 3 the network terms raised public accuracy over travel alone (Columbia market 0.615 against 0.49):
coverage ties and shared third places are public data and pull the predicted market toward the observed one. The
stage-3 run has no travel-alone row.

**The drop from 0.70, isolated** (before stage 3; the isolation stands; `tie_footprint.py` diagnostics `CAMPUS_IN`, `REHOME`, `SCORE=2026-10-18`,
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
| all (before stage 3) | 0.61 / 0.610 | 0.88 | 0.13 | 0.16 |

By market (accuracy median, 2026-10-18 state -> before stage 3 -> current): Columbia 0.68 -> 0.615 -> 0.625;
Springfield 0.74 -> 0.575 -> 0.55; Cape Girardeau 0.49 -> 0.36 -> 0.37 (campus exclusion alone 0.38: The Arrow);
Kirksville 0.62 -> 0.59 -> 0.61; Joplin 0.87 -> 0.77 -> 0.79; Kansas City 0.92 -> 0.93 -> 0.965; St. Joseph 0.85 ->
0.62 -> 0.63.

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
markets became the two Advan shows (northeast toward Hannibal, and Columbia; Vandalia 0.55 before stage 3); the false Kansas City
and St. Louis markets came from the 2026-10-18 public build overdrawing metros for a small town (Jackson 3.3% of
out-of-county travel against Advan's ~0.2%; St. Louis County 11.8% vs ~4.5%; Marion 2.2% vs ~17%), amplified by Kansas
City being one map unit. Mexico kept one false market (Jefferson City, 1.1% of observed travel): LODES gave Audrain
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
from 2026-10-20 (Name: civic interest areas). Map title "<Town>'s civic interest area", no direction in the title,
numbered I, II, III only when a town has more than one. Columbia has one since 2026-10-24: "Columbia's civic interest
area" (formerly I and II). The published map is the probability surface (Revealed media market, The published map);
the certainty layer belongs to the single adopted-setting map (`?prob=0`; `market_pattern_print.html &conf=1&outline=1`;
`analysis/confidence_layer.py`, `flows/pattern_halves.py`, now a check): the same network tie from odd and from even
months, each half refitted; a shown hexagon is lighter when it clears the map's floor in one half only; the area is
drawn as one connected area (confident cells joined by closing, small clusters kept within 5 hexagons, lone far cells
dropped, smoothed ~5 km on the km plane, gaps filled with empty hexagons, nothing drawn outside it, no outline line).

**Minimum size, ADOPTED (2026-10-18, unchanged):** a secondary or tertiary area needs 10%+ of the town's residents AND
1,000+ residents (`market_patterns.py`; primary always kept). Evidence, current (`analysis/market_stability.py`, 58
areas, network-tie map, independent halves, home excluded): share of shown hexagons holding in both halves, median
0.76 at 500-1,000 residents (2 areas), 0.835 at 1,000-2,000 (8), 0.89 at 2,000-5,000 (15), 0.92 above 5,000 (33);
Spearman (residents, share holding) 0.19. Columbia 0.95. A stability threshold is not adopted.

## Coverage model

**Adopted (2026-10-24)** (`coverage_model.py`): PPML of March story-county pairs from each newsroom county i to each
other Missouri county j, on the final `gravity_terms.py` (outcome `visits_statewide`, highway-stop discount, commuting
JT01, 8 terms centred at 25 miles). A fixed effect for every newsroom county and every county covered, plus:

| Role | Terms | Selection |
|---|---|---|
| Core (theory) | distance block (log distance, its square, nonmetro × both, log population × log distance); border; commuting block (out, in) (`gravity_terms.FACTORS`) | Tested only as blocks; log distance is kept with its square and its interactions, and the distance block enters or leaves whole |
| Travel | log visits i → j (`gravity_terms.travel_visits`, Jan–Sep 2026) where visits > 0; indicator for no recorded visits | — |
| Hypothesis term (stated in advance) | log visits × nonmetropolitan newsroom county (USDA RUCC 4–9) | Reported whatever the result |
| Exploratory | saturation terms (`coverage_saturation_test.py`) | Adopted only if the nested guard's change has an interval excluding zero: none adopted |

- Newsroom county: `excluded_outlets.home_fips`. Mid Rivers Newsmagazine counts with St. Charles and Greene County
  Commonwealth with Greene (29 stories each).
- `excluded_outlets.EXCLUDE` is left out (498 stories), including the 11 campus newspapers (`CAMPUS`), Dos Mundos and
  KHQA 7 (the 49 stories of these two out-of-state filings were already outside the fit).
- The elasticity is the percentage difference in stories associated with 1% more visits, holding the core terms and
  both sets of fixed effects fixed: an association, not an effect of travel on coverage.
- A story counts once for each county it names, so the pairs from one newsroom county are not independent: errors are
  clustered by newsroom county (88 clusters).
- Held out: newsroom counties in 8 folds (`gravity_terms.loco`, seed 7). Score: mean absolute error of each county's
  out-of-county story shares, averaged over counties; 95% interval from 1,000 county draws (county-paired for
  differences).
- **Primary metric: destinations with 1%+ of the county's visits** (1,174 pairs): chosen by travel, not by the held-out
  stories; 39% of them have no stories. The all-destinations score is reported beside it but is dominated by zero
  pairs (81% of all pairs have no stories, and their share error is near zero for any model).

### Results

| | All outlets | Print and digital |
|---|---:|---:|
| Stories / newsroom counties / out-of-county story-county pairs | 14,877 / 88 / 10,282 | 8,301 / 88 / 6,674 |
| **Elasticity, metro newsroom counties (27)** | **0.49** (s.e. 0.070; 95% CI 0.36–0.63) | **0.52** (0.086; 0.35–0.69) |
| **Elasticity, nonmetro newsroom counties (61)** | **0.25** (s.e. 0.063; 95% CI 0.13–0.38) | **0.26** (0.064; 0.14–0.39) |
| Hypothesis term, nonmetro − metro | −0.241 (s.e. 0.040, p < 0.001) | −0.258 (0.059, p < 0.001) |
| Twice the visits, metro / nonmetro | 1.41 / 1.19 × the stories | 1.43 / 1.20 × |
| s.e., clustered by county pair, metro / nonmetro (sensitivity) | 0.049 / 0.049 | 0.053 / 0.049 |
| s.e., two-way newsroom county × county covered (sensitivity) | 0.081 / 0.070 | 0.098 / 0.070 |
| s.e., HC1, pairs independent (reference only) | 0.048 / 0.047 | 0.052 / 0.048 |
| Leave one newsroom county out, metro (88 fits) | 0.46 (without St. Louis County, 1,812 pairs) to 0.54 (without Jackson, 677) | 0.47 (without St. Louis County, 846) to 0.57 (without Franklin, 379) |
| Leave one newsroom county out, nonmetro | 0.23 (without St. Louis County) to 0.29 (without Jackson) | 0.21 (without St. Louis County) to 0.29 (without Taney, 43) |
| Pooled elasticity, no hypothesis term (sensitivity) | 0.36 (s.e. 0.064) | 0.35 (0.069) |
| Commuting in / out | +0.41 (s.e. 0.073) / −0.03 (n.s.) | +0.38 / −0.03 |
| Held-out error, primary (1%+ of visits) | 4.49 [4.04, 4.98] | 4.59 [4.13, 5.06] |
| Held-out error, all destinations | 0.915 [0.846, 0.982] | 0.941 [0.874, 1.004] |
| Fitted vs observed pairs, r² | 0.97 | 0.95 |

Blocks and the hypothesis term, each left out of the adopted model (gain = error without it − adopted):

| Left out | Role | Primary: gain [95%] | All destinations: gain | Wald, clustered |
|---|---|---:|---:|---|
| Distance block (5 terms) | core | +0.005 [−0.115, +0.125] | +0.006 [−0.006, +0.019] | χ² 78.3, df 5, p < 0.001 |
| Border | core | −0.013 [−0.045, +0.019] | +0.000 [−0.003, +0.003] | χ² 8.9, df 1, p 0.003 |
| Commuting block (out + in) | core | −0.017 [−0.124, +0.087] | −0.001 [−0.013, +0.010] | χ² 36.5, df 2, p < 0.001 |
| **Log visits × nonmetro (hypothesis)** | hypothesis | **+0.125 [+0.048, +0.202]** | −0.002 [−0.010, +0.006] | χ² 36.4, df 1, p < 0.001 |

Print and digital: distance −0.083 [−0.247, +0.071]; border −0.008 [−0.021, +0.007] (Wald p 0.21); commuting −0.029
[−0.137, +0.073]; hypothesis term +0.090 [+0.006, +0.173], all destinations −0.001 [−0.010, +0.008].

- The core terms stay in by theory. None of the three blocks changes held-out share error detectably, because the
  destination effects and visits carry the same geography, but each is jointly significant in the fit (border not
  significant for print).
- The hypothesis term lowers primary held-out error by 0.13 points (print 0.09), both intervals excluding zero; on all
  destinations a tie. Stories from nonmetro newsroom counties are associated with visits about half as strongly as
  stories from metro ones: 1% more visits, 0.49% more stories from metro newsroom counties, 0.25% from nonmetro ones.
- No single newsroom county drives either elasticity; St. Louis County, the largest (1,812 of 10,282 pairs), moves both
  the most (0.49 → 0.46, 0.25 → 0.23).
- Zero-visit pairs (137, 1 story-county pair on them), metro / nonmetro: adopted 0.494 / 0.254. With zeros at log(1e-3)
  0.490 / 0.248; with log(visits + 1 / 10 / 100) 0.488–0.496 / 0.253–0.258; dropped 0.494 / 0.253.
- "Travel beyond gravity", log(visits ÷ travel-model prediction), is the same quantity as log visits given the same
  terms and fixed effects (pooled 0.355 against 0.354); replaced by log visits.

Specifications not adopted (`coverage_model.py` prints them so earlier figures can be traced; not to be quoted).
Without the core terms, distance loads onto visits (pooled):

| Specification | All outlets | Print and digital |
|---|---:|---:|
| Fixed effects + log(1 + visits), no distance terms (`border_coverage_test.py` family) | 0.74 (s.e. 0.015) | 0.71 |
| Fixed effects + log(1 + visits) + log distance + border | 0.53 (s.e. 0.066) | 0.51 |
| Pooled, without the commuting block | 0.43 | 0.40 |
| Pooled, all core terms (sensitivity) | 0.36 | 0.35 |

### Exploratory additions: saturation (`coverage_saturation_test.py`), none adopted

Saturation hypothesis: stories follow visits less to destinations that already have their own coverage. The nested
guard works inside each of 8 outer training sets: an inner leave-county-out (7 folds) scores the adopted model and
each addition on the primary metric, and the chosen candidate scores the outer held-out counties.

| Procedure / addition, all outlets | Primary: change [95%] | All destinations: change | Coefficient (clustered s.e., p) |
|---|---:|---:|---|
| **Nested guard, lowest inner error** | **+0.011 [−0.005, +0.027]** | +0.001 | — |
| Nested, interval rule inside the folds (admitted in 1 of 8) | +0.002 [−0.006, +0.012] | −0.000 | — |
| One at a time: × destination's own stories | −0.003 [−0.024, +0.019] | −0.001 | −0.006 (0.008, p 0.43) |
| One at a time: × destination's newsrooms | +0.017 [+0.006, +0.029] | +0.001 | −0.001 (0.022, p 0.95) |
| One at a time: × destination has broadcaster | +0.004 [−0.013, +0.022] | +0.000 | −0.025 (0.033, p 0.45) |
| One at a time: × own stories, × own stories × nonmetro home | +0.001 [−0.022, +0.021] | −0.000 | own × nonmetro −0.000 (0.004, p 0.90) |
| One at a time: × own stories, × broadcaster | +0.004 [−0.019, +0.028] | −0.000 | — |

Print and digital: nested lowest inner error −0.002 [−0.032, +0.026]; interval rule +0.006 [−0.004, +0.021]; own
stories +0.011 (p 0.18). Neither nested interval excludes zero: saturation is not supported. The level version (rural
newsrooms cover saturated centres less regardless of travel) was tested only within the all-factors model.

### Rejected or not supported

| Tested | Result | Script |
|---|---|---|
| Separate factor lists for travel and coverage | Replaced by one shared term set (`gravity_terms.py`) | — |
| Non-bordering destinations get less coverage than travel predicts | Raw comparison, at 10%+ of visits: ring 2 and ring 3+ get 6.7% and 7.7% of story share, against 15.9% for bordering counties. Border-test specification (no distance terms, not the adopted model; clustered by newsroom county): slope difference beyond the border +0.04 (95% CI −0.04 to +0.13; print +0.07, −0.04 to +0.18), not detectable; ring 3+ level −1.22 (s.e. 0.54) | `border_coverage_test.py` |
| Saturation (above) | Nested intervals include zero | `coverage_saturation_test.py` |

### Changes, 2026-10-24 (peer review, two rounds): coverage

| Change | Before | After |
|---|---|---|
| Visits | `od_predicted.csv` visits (county factor) | `gravity_terms.travel_visits`, the travel model's adopted outcome |
| Travel term | log(visits ÷ travel-model prediction) | log visits; identical given the same terms and fixed effects |
| Hypothesis term | — | log visits × nonmetro newsroom county: metro 0.49, nonmetro 0.25; primary gain +0.125 |
| Selection | terms one at a time, in-sample p | core terms as blocks; hypothesis term reported; exploratory terms through the nested guard only |
| Held-out scoring | 88 single-county folds; destinations with 1%+ of visits **or 2+ held-out stories**; no interval | `gravity_terms.loco` folds; primary = 1%+ of visits; all destinations beside; county-paired bootstrap intervals |
| Zero-visit pairs (137 fitted) | log(1e-3) = −6.9, high leverage | indicator + log visits where > 0; elasticities move ≤ 0.006 |
| Standard errors | HC1 | clustered by newsroom county; pair and two-way as sensitivity |
| HOME_COUNTY, CAMPUS | counted under the county filed; campus papers in | `home_fips`; `CAMPUS` excluded; out-of-county pairs 10,406 → 10,282 |
| Out-of-state outlets | dropped silently (49 stories) | Dos Mundos and KHQA 7 in `EXCLUDE` (user) |
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
| Article text comparing residents' share of visits outside the county (~76% rural) with stories reaching beyond it (~42%) | Same error |
| "Visits × expected" figures from the singly-constrained model (e.g. 2.2×) | That model's held-out error is 6.46 against the adopted 3.31; the 1.6× under-prediction once given as the reason is superseded (appendix) |
| "Beyond gravity" maps | Category colours carried four model-based outcomes; unreadable as maps. The model comparison is a table (`three_counties_table.csv`) |
| Alignment maps with the home county compared | Replaced by out-of-county comparison with home and away story counts for reference |

## All marginal factors together

Each factor above was first tested alone. To check whether many small effects add up, every factor that showed any
effect was added at once and scored only on counties the model was not fitted on (`combined_marginal_test.py`,
`combined_all_factors_test.py`; each model's primary metric; change = with − without):

| Model | Travel error | Change [95%] | Coverage (all / no broadcast) | Change [95%] | Spillover | Change [95%] |
|---|---:|---:|---:|---:|---:|---:|
| Adopted | 3.31 [2.96, 3.64] | | 4.25 [3.83, 4.75] / 4.37 [3.95, 4.83] | | 6.43 [5.54, 7.64] | |
| + all rejected terms | 3.19 | −0.11 [−0.31, +0.09] | 4.24 / 4.38 | −0.02 [−0.12, +0.09] / +0.01 [−0.10, +0.11] | 7.00 | +0.56 [−0.00, +1.16] |
| + all rejected, ridge 0.05 / 0.2 | | | | | 7.02 / 7.46 | +0.58 [−0.06, +1.27] / +1.02 [+0.11, +1.86] |
| Nested choice of travel terms | 3.25 | −0.06 [−0.20, +0.10] | | | | |
| + every rejected term incl. saturation level (coverage); every county factor (spillover) | | | 4.23 / 4.36 | −0.02 [−0.12, +0.08] / −0.01 [−0.11, +0.09] | 7.66 | +1.23 [+0.51, +1.97] |
| — spillover ridge 0.05 / 0.2 | | | | | 7.05 / 7.44 | +0.62 [−0.00, +1.28] / +1.01 [+0.13, +1.83] |
| Origin effects + every destination factor + every pair term (no destination effects) | 3.83 | +0.53 [+0.09, +0.97] | 4.34 / 4.41 | +0.09 [−0.07, +0.25] / +0.04 [−0.10, +0.19] | | |

- Coverage: the final `coverage_model.py` specification, each newsroom county held out, scored on the destinations
  with 1%+ of its residents' visits (no longer also on destinations with 2+ stories, which selected on the outcome).
  This script's adopted figure is 4.25 against `coverage_model.py`'s 4.49 on the same metric (Open); the changes are
  paired within the script.
- Spillover: `spillover_common.FINAL`, fitted on 85 outlets, scored on 94.
- No combination of rejected factors improves any model held out; for spillover every combination is worse. Stores,
  jobs, metro and area centre cannot replace each destination's measured draw: without destination effects travel is
  worse (+0.53 [+0.09, +0.97]).

## Crossover: distinct people (adopted; revised 2026-10-24)

Crossover is the share of a county's residents observed outside it in a month, counted as distinct people
(`build_unique_od.py`, `crossover_compare.py` → `crossover_compare.csv`); it is the potential demand in Revealed media
market by travel pattern and not a term in the adopted spillover model. Advan reports distinct people per destination
block group by home block group; people from different home block groups are distinct, and for each home block group
the people seen in its single most-visited block group outside the county (Missouri or Kansas) are all distinct. St.
Louis city and county are one unit before the left-the-county test.

**Detection test.** Within a county, block groups where Advan sees more phones at home than the ACS predicts (d = own
÷ E, E = ACS population × the month's statewide units per resident) show lower leaving rates (busiest outside block
group ÷ own). Log leaving rate in one month regressed on log detection in another (same block-group vintage, so the
noise in own is not shared), county × month-pair fixed effects, ACS-population weights, intervals clustered by county:
March → June −0.552 [−0.622, −0.482], June → March −0.508 [−0.573, −0.442]; all 44 ordered month pairs stacked −0.510
[−0.588, −0.433] (218,955 block-group pairs, 114 counties). So b = 0.51 [0.43, 0.59]: about half the phones above E
behave as phantoms (never leave), half as residents.

**Denominator (adopted, user decision 2026-10-24, option A):** per home block group D = E × d^(1 − b) = own^(1 − b) ×
E^b, b = 0.51 (D = E where own = 0; D = 0 where the block group has no ACS residents); each block group's leavers
capped at D, summed over the county, divided by the sum of D, averaged January–September.

**Bounds.** For any b in [0, 1], D lies between min(own, E) and max(own, E) in every block group, so the county figure
is bounded by leavers over Σ max(own, E) (low) and leavers over Σ min(own, E) (high), each block group's leavers capped
at the denominator used (`dedup_bound_low`, `dedup_bound_high`). The b = 0 and b = 1 sums are not bounds: D moves with
b in opposite directions for over- and under-detected block groups, so they are named sensitivity columns only.
Containment (`crossover_compare.py` asserts it): the calibrated figure lies inside its bounds in 114 of 114 counties;
the linear split in 114; b = 0 in 113 (outside: Knox), b = 1 in 112 (Knox, Schuyler).

| County | Calibrated, b = 0.51 (adopted) | Low bound, ÷ Σ max(own, E) | High bound, ÷ Σ min(own, E) | b = 1 (sensitivity) | b = 0 (sensitivity) | Linear split, (1 − b) own + b E (sensitivity) |
|---|---:|---:|---:|---:|---:|---:|
| Audrain | 44% | 34% | 53% | 40% | 41% | 42% |
| Boone | 26% | 20% | 31% | 24% | 25% | 25% |
| Osage | 57% | 43% | 69% | 66% | 45% | 54% |
| Missouri median | 58% | 44% | 69% | 56% | 53% | 55% |
| St. Louis (city + county) | 35% | 18% | 46% | 18% | 43% | 27% |

| County population | Counties | Bounds width (high − low), median (middle 80%), points | Calibrated, median | Low, median | High, median |
|---|---:|---:|---:|---:|---:|
| Under 10,000 | 30 | 22.9 (19.0–34.3) | 65% | 52% | 76% |
| 10,000–20,000 | 30 | 25.0 (17.7–31.2) | 60% | 46% | 71% |
| 20,000–50,000 | 33 | 20.7 (18.0–25.0) | 54% | 43% | 64% |
| 50,000+ | 21 | 19.5 (13.6–23.9) | 44% | 32% | 53% |

Osage is 57% calibrated per block group; the same b applied to the county's detection ratio as a whole gives 52% (66%
÷ 1.64^0.49), which is not the estimated form.

Denominators compared (Spearman across 114 counties):

| Denominator | with calibration factor | with commuters out ÷ employed (JT01) | with commuters out ÷ population |
|---|---:|---:|---:|
| Seen at home, as published (city ↔ county counted as leaving) | −0.64 | +0.54 | +0.37 |
| Seen at home, St. Louis unit fixed | −0.63 | +0.55 | +0.38 |
| (i) Residents in the busiest block group anywhere | −0.66 | +0.55 | +0.37 |
| (ii) Seen at home, phantom block groups at E | −0.49 | +0.51 | +0.31 |
| b = 1 (iii) E, Missouri and Kansas destinations (sensitivity) | +0.14 | +0.46 | +0.33 |
| b = 0, seen at home, Missouri and Kansas destinations (sensitivity) | −0.65 | +0.54 | +0.37 |
| **Calibrated, b = 0.51 (adopted)** | **−0.37** | **+0.54** | **+0.37** |
| Linear split (sensitivity) | −0.38 | +0.55 | +0.39 |
| Summed block-group share (replaced 2026-10-16) | −0.46 | +0.69 | +0.53 |

The adopted lower bound is above the commuting floor (employed residents working in another Missouri county ÷
population, LODES JT01: Audrain 21%, Boone 11%, Osage 31%, median 21%, St. Louis 6%) in 113 of 114 counties (St.
Charles is set by commuting). Kansas destinations add 0.0 points at the median under the b = 1 denominator (Jackson
+6.7, Clay +3.2, Platte +2.7, Vernon +2.6). The three-county and tract scripts use the calibrated denominator (old forms
kept as sensitivity columns; D per block group-month in `crossover_bg_month_mo_2026.csv`): `residents_leaving.py`
Audrain 44%, Boone 25%, Osage 57% (seen at home 41 / 24 / 45%, b = 1 40 / 24 / 66%); `residents_leaving_tracts.py`,
January–July, population-weighted conservative floor 44 / 27 / 57%; `unique_people_by_county.py`, March, Audrain →
Boone 36.0% (seen at home 34.0%, b = 1 31.8%). Treating block groups as independent still gives implausible figures (90%
of Audrain residents in Boone County in March), so only the lower bound is used.

## Spillover model, current (2026-10-24)

`spillover_outlets.py`; definitions and the model procedure in `spillover_common.py`; nested guard in
`spillover_rule_selection.py`.

| | Value |
|---|---|
| Outlets with 10+ placed stories | 128 in 72 counties (27 broadcasters), 12,192 stories |
| Well collected | 95 outlets; 94 scored (Three Rivers Publishing is well collected but not fitted) |
| Fitted (well collected, 20+ placed stories, not Three Rivers Publishing) | 85 outlets, 48 counties (24 broadcasters) |
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
weekly (5.53, not nested). Repeated inside each fold: 6.05 / 5.05. Nested guard: change +0.07 [−0.38, +0.60] (seeds
1–5: upper bound +0.58 to +0.60): no addition adopted.

One at a time against the adopted model (descriptive; adoption only through the guard; change = with − without):

| Candidate | Change | 95% interval | Median with / without | Coefficient (CRV3 p; bootstrap CI) |
|---|---:|---|---|---|
| Outlets per 10,000 | −0.28 | −0.87 to +0.16 | 4.74 / 4.66 | +0.191 (< 0.001; −0.154 to +0.329) |
| Border, print and digital | −0.08 | −0.45 to +0.33 | 4.64 / 4.66 | −0.110 (0.041; −0.209 to −0.011) |
| Miles to a town of 25,000+ | −0.05 | −0.36 to +0.25 | 4.78 / 4.66 | +0.164 (0.027; +0.032 to +0.295) |
| Border, every outlet | −0.01 | −0.36 to +0.36 | 4.78 / 4.66 | −0.089 (0.050; −0.167 to −0.004) |
| All outlets | +0.09 | −0.02 to +0.20 | 4.67 / 4.66 | +0.128 (0.50; −0.266 to +0.418) |
| Crowded weekly | +0.09 | −0.05 to +0.27 | 4.65 / 4.66 | −0.200 (0.35; −0.629 to +0.184) |
| TV stations | +0.14 | −0.02 to +0.33 | 4.53 / 4.66 | +0.132 (0.53; −0.295 to +0.431) |

County and outlet figures are held out: each county's outlets predicted by the adopted model fitted without that
county; one computation feeds the county table, the sensitivity table, the chart and `spillover_quoted_rows.csv`.

| County | Actual | Expected (held out) | Stories |
|---|---:|---:|---:|
| Audrain | 19.5% | 22.5% | 123 |
| Boone | 28.7% | 26.4% | 1,152 |
| Boone, print and digital | 18.3% | 19.3% | 476 |
| Osage | 25.6% | 25.3% | 40 |
| Cole | 23.1% | 25.4% | 325 |
| Jackson | 21.9% | 19.1% | 2,316 |
| Jackson, print and digital | 22.8% | 11.7% | 657 |

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
- **Not local news**: `EXCLUDE` (`spillover_common.NOT_LOCAL = EXCLUDE`): the statewide outlets, Dos Mundos, KHQA 7 and
  the campus newspapers (`CAMPUS`, in `excluded_outlets.py`) — student newspapers owned by a college or university:
  Griffon News, The Arrow, Drury Mirror, The Standard, UMKC Roo News, The Chart, The Daily BURG, North West Missourian,
  Student Life, The Journal/The Webster Journal, The University News. Out of the outcome, the fit and every county
  count. University-licensed public broadcasters (KBIA, KCUR, KRCU, KSMU, KXCV, STL Public Radio) and the School of
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
fitted outlets: in sample 5.9, held out 6.2, intercept only held out 7.4. Columbia–Jefferson City 3.2 in sample, 3.3
held out (intercept only 5.5). St. Joseph (13.5 against 8.7, 5 outlets) and Quincy–Hannibal (11.9 against 9.5, 2
outlets) do worse than intercept only.

Springfield region (Greene, Webster, Barry) held out — out of sample for the coefficients only; the terms were chosen
with the region's outlets in the data: 78 outlets fitted outside it predict its 10: mean error 8.0 points (well
collected 8.4); broadcaster + crowded weekly 9.0; broadcaster + town population 8.8. Region 24% actual, 26% expected.
Webster is the largest miss (36% actual, 23% expected).

Market position (`spillover_market_test.py`, on the border form): other outlets nearer the county line, or nearer the
neighbour the outlet is closest to, add nothing (CRV3 p 0.34–0.75) and replace the border term worse (mean 6.03–6.07
against 5.90).

### Outlets (actual / held-out expected, `spillover_quoted_rows.csv`)

| Outlet | Actual | Expected | Stories |
|---|---:|---:|---:|
| Boone County Journal | 14.7% | 19.3% | 138 |
| Centralia Fireside Guard | 5.0% | 19.3% | 20 |
| Columbia Daily Tribune | 16.6% | 19.3% | 86 |
| Columbia Missourian | 22.3% | 19.3% | 232 |
| Greene County Commonwealth | 18.5% | 17.4% | 27 |
| KC Beacon | 17.3% | 11.7% | 39 |
| Mid Rivers Newsmagazine | 17.3% | 22.6% | 26 |
| The Cash-Book Journal | 22.5% | 22.3% | 20 |
| The Kansas City Star | 26.4% | 11.7% | 427 |
| The Mexico Ledger | 22.1% | 22.5% | 105 |
| The Pitch/Kansas City Pitch | 24.1% | 11.7% | 53 |
| Vandalia Leader | 4.2% | 22.5% | 18 |

Vandalia Leader and Centralia Fireside Guard are not well collected (5% and 0% of stories full length): actual a lower
bound.

### Changes from the 2026-10-17 model

| Change | Effect |
|---|---|
| Mid Rivers Newsmagazine → St. Charles, Greene County Commonwealth → Greene; both fitted | +2 fitted outlets; the Commonwealth becomes a crowded weekly (Greene) |
| Campus newspapers out (11 outlets; 5 had 10+ stories: Griffon News, The Arrow, North West Missourian, Student Life, The Standard) | −5 outlets; three of them (The Arrow 7%, The Standard 5%, Griffon News 15%) were crowded weeklies |
| Print-outlet count: `EXCLUDE` (incl. `CAMPUS`) out; one market rule (active, or closed but publishing in March) in every script | Counts change in Boone, Cole, Buchanan, Cape Girardeau, Greene, Jackson, Jasper, Nodaway, St. Louis; Mid Rivers counted in St. Charles |
| Crowded weekly requires a print outlet | KC Beacon (digital native) out of the term |
| Frequency codes filled from the Missouri Official Manual 2025–2026 where blank (14 outlets; `coverage/source_frequency.csv`) | The Cash-Book Journal (Cape Girardeau) becomes a crowded weekly |
| One home rule (city counties + Kansas City, Kansas) for every outlet | 31 outlets gain home counties; 330 centred stories move to home (213 beyond the 2026-10-17 Kansas City rule: Kansas City outlets' Clay, Platte and Cass stories; Joplin's Newton; Sikeston's New Madrid; Springfield's Christian), 434 mention-only stories lose their mention credit |
| Selection procedure: hypothesis terms broadcaster + print outlets; exploratory additions through the nested guard | Crowded weekly and border distance not adopted |
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
| + HOME_COUNTY reassignment (reviewer rerun) | −0.49 | 0.005 (z) |
| + market-count rule, border 0 outside home, clustered t | −0.35 | 0.002 |
| + campus newspapers out | −0.13 | 0.48 |
| + print outlets only (KC Beacon out) | −0.25 | 0.19 |
| + frequency codes filled (Cash-Book Journal in) | −0.35 | 0.040 |
| + one home rule | −0.18 | 0.31 |
| + border for print and digital only (border form) | −0.20 | 0.27 |

Frequency codes: The Maryville Daily Forum and The Daily/Dexter Statesman were checked against the Official Manual and
kept as weeklies (Manual: "Maryville Forum", Thursdays; "The Statesman", Wednesdays); Richmond Daily News likewise
(Fridays). Neither county has a TV station, so neither code reaches the term. Codes filled where blank, weekly: The
Banner Press, The Cash-Book Journal, Aurora Advertiser, St. Louis Business Journal, Tribune and Times, Cedar County
Republican and Stockton Journal, Chariton Marquee, Kahoka Hometown Journal, Clinton County Leader (Plattsburg),
Springfield Business Journal, Hermitage Index, Tipton Times, Community News; bi-weekly: West & Mid Rivers
Newsmagazine. Sensitivity, not adopted: the Manual's print schedule for every outlet it lists (20 codes change;
Kirksville Daily Express, The Mexico Ledger, The Fulton Sun, Daily Journal and Constitution-Tribune become weeklies;
Southeast Missourian tri-weekly): crowded counties fall from nine to six (Adair, Callaway, Cape Girardeau leave);
crowded weekly −0.28 (p 0.14); held-out 5.85 / 4.54. Frequency codes are kept as filled; moot without the
crowded-weekly term. Border distance 0 for an outlet outside its home county is kept (comment in
`spillover_outlets.py`).

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

Share of residents seen outside the county (crossover, `crossover_compare.csv`: `dedup_lower`, the calibrated measure,
b = 0.51; sensitivity on the bounds `dedup_bound_low` / `dedup_bound_high`) against the share of print and digital
stories about another county, across counties (`collection_quality_robustness.py`); p from the (weighted)
least-squares slope:

| Crossover | Outlets | Counties | r, unweighted (p) | r, weighted by stories (p) |
|---|---|---:|---:|---:|
| calibrated | all outlets | 72 | +0.18 (0.138) | +0.14 (0.225) |
| calibrated | well-collected outlets | 53 | +0.41 (0.002) | +0.37 (0.007) |
| calibrated | outlets in well-collected counties | 29 | +0.40 (0.030) | +0.32 (0.095) |
| low bound | all outlets | 72 | +0.16 (0.174) | +0.16 (0.191) |
| low bound | well-collected outlets | 53 | +0.40 (0.003) | +0.39 (0.004) |
| low bound | outlets in well-collected counties | 29 | +0.43 (0.021) | +0.35 (0.061) |
| high bound | all outlets | 72 | +0.18 (0.132) | +0.15 (0.200) |
| high bound | well-collected outlets | 53 | +0.39 (0.004) | +0.36 (0.009) |
| high bound | outlets in well-collected counties | 29 | +0.36 (0.057) | +0.30 (0.120) |

A positive relationship appears where collection is good: well-collected outlets r ≈ +0.4 (p < 0.01), weighted or
not, on every crossover variant; across all outlets it is not distinguishable from zero (r +0.14 to +0.18).

## Collection quality (sensitivity)

`county_collection_quality.py` (pinned registry; `EXCLUDE`, which includes `CAMPUS`, not counted as known newsrooms):
33 counties meet every test. Adopted spillover model by subset (`collection_quality_robustness.py`), held-out mean
error, coefficients with CRV3 p:

| Outlets | n (counties) | Held-out | Broadcaster | Print outlets |
|---|---|---:|---|---|
| All, 10+ | 128 (72) | 7.5 | +0.82 (< 0.001) | −0.42 (< 0.001) |
| Well-collected, 10+ | 95 (54) | 6.6 | +0.68 (< 0.001) | −0.44 (< 0.001) |
| In well-collected counties | 40 (29) | 8.9 | +0.51 (0.077) | +0.08 (0.90) |

Outlets in well-collected counties (40) are too few to estimate the model. Coverage, pooled specification (travel
beyond gravity; not the adopted metro / nonmetro form), all newsroom counties → well-collected counties: 0.36 → 0.25
(all outlets), 0.35 → 0.26 (print and digital).

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
Travel: table below (2026-10-24, second review).

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

Travel, adopted model held out (each home county left out): share-weighted error 3.31, big-flow error 3.44. Each
candidate added to the adopted set; change in held-out error [95%], coefficient (two-way p). All are also in the
nested guard, which adopts none.

| Candidate | Share-weighted error | Big-flow error | Coefficient | Script |
|---|---:|---:|---:|---|
| Median household income × distance | +0.01 [−0.05, +0.09] | +0.01 [−0.04, +0.07] | +0.059 (0.009) | `civic_variables_test.py` |
| Per-capita income × distance | +0.06 [−0.04, +0.16] | +0.07 [+0.00, +0.15] | +0.083 (0.01) | `civic_variables_test.py` |
| Median age × distance | +0.07 [+0.00, +0.15] (worse) | +0.11 [+0.03, +0.19] | +0.095 (0.04) | `civic_variables_test.py` |
| Age 65+ × distance | +0.07 [−0.03, +0.18] | +0.09 [+0.00, +0.18] | +0.117 (0.01) | `civic_variables_test.py` |
| Households with broadband × distance | +0.04 [−0.07, +0.16] | −0.00 [−0.08, +0.08] | +0.129 (0.004) | `civic_variables_test.py` |
| Mean travel time to work × distance | +0.01 [−0.05, +0.07] | −0.00 [−0.06, +0.05] | −0.056 (0.02) | `civic_variables_test.py` |
| Below poverty × distance | +0.01 [−0.06, +0.08] | +0.00 [−0.06, +0.05] | −0.053 (0.04) | `civic_variables_test.py` |
| Bachelor's degree or higher × distance | −0.01 [−0.11, +0.09] | −0.01 [−0.09, +0.06] | +0.080 (< 0.001) | `civic_variables_test.py` |
| In labour force × distance | +0.02 [+0.00, +0.04] (worse) | +0.01 [−0.02, +0.03] | +0.009 (0.84) | `civic_variables_test.py` |
| Owner-occupied × distance | +0.01 [−0.02, +0.05] | +0.01 [−0.03, +0.05] | +0.029 (0.32) | `civic_variables_test.py` |
| Unemployment rate × distance | no estimates in `mo_county_acs_2024.csv`; not tested | | | `civic_variables_test.py` |
| Nearest hospital county | +0.01 [−0.03, +0.05] | −0.02 | −0.03 (0.59) | `hospital_test.py` |
| Nearest hospital county, and when home has none | −0.03 [−0.21, +0.12] | −0.07 | nearest_x_none −0.29 (< 0.001) | `hospital_test.py` |

Several coefficients are clearly non-zero (degree, broadband, home without a hospital) and improve nothing held out:
they describe the fit, not a transferable pattern. Coverage with the hospital terms (`hospital_test.py`, destinations
with 1%+ of visits): 4.25 → 4.26 (all outlets), 4.37 → 4.36 (no broadcasters).

Hospitals: CMS Hospital General Information, general acute, critical access, children's, VA and DoD hospitals (no
psychiatric hospitals, no clinics), with Capital Region Medical Center added (it reports under MU Health Care's CMS
number since 2024): 107 hospitals in 67 counties (`build_hospitals.py`). Counties without a hospital have more
residents leaving; hospital terms do not improve held-out travel once each county's overall draw is measured
(coverage: `hospital_test.py` 4.25 → 4.26). To confirm: Cooper County Memorial Hospital (Boonville) and Southeast
Health Center of Ripley County (Doniphan) appear in OpenStreetMap but not in CMS.

## Revealed media market by travel pattern (2026-10-17; K rule and probability surface 2026-10-24)

A town's revealed media market is (1) crossover of its residents into other counties, the potential demand, and (2)
spillover between the county pair in both directions, the supply. Residents do not share one travel pattern, so the
market is the most common pattern among them; secondary and tertiary patterns are separate maps. From 2026-10-20 each
mapped pattern is a **civic interest area**; this paper's map is the network-tie area drawn as a probability surface
(The published map, below).

**Patterns** (`flows/travel_patterns.py`). Advan Neighborhood Patterns Plus, January–July 2026 (the months on 2020
block groups): for each home block group and destination, reach = residents seen in the destination's busiest block
group / residents seen at home, mean over the months the block group is observed (50+ residents at home). A missing
home-month is missing, not zero: left out of every mean and masked in every fit and score (Kansas City 229 of 5,236
home-months missing, Columbia 4 of 1,106, St. Joseph 1 of 756, none elsewhere). Destinations: towns (2020 places),
rural block groups, Missouri counties outside the TV market; own town masked. Travel is decomposed by non-negative
matrix factorization (mixed membership): each block group's travel is a weighted mix of K recurring patterns. Final
fit: lowest loss of 10 starts; masked multiplicative updates computed as the full product less the masked cells
(identical to 1e-14, ~6x faster).

**Residents** (2026-10-24): each block group's ACS 2020–2024 population (B01003), through the calibrated
per-block-group denominator of crossover (`crossover_bg_month_mo_2026.csv`: people = devices × ACS population / D),
mean over January–July, allocated to patterns by the travel each carries and ranked: primary, secondary, tertiary.
Lancaster (716 by ACS) cannot pass the 1,000-resident test.

**K rule (user, 2026-10-24, option A, per town).** K = the largest K (grid 1–12, extended while its last K passes) at
which every pattern passes:

| Test | Measure | Threshold |
|---|---|---|
| Town | some study town (`flows/regions.json`) for which the pattern holds 10%+ AND 1,000+ of the town's residents AND 10%+ of the town's travel (residents × reconstructed reach), the same town for all three | 10%, 1,000, 10% |
| Replicability, starts | median over 9 other starts of the pattern's matched cosine (Hungarian) to the kept, lowest-loss fit of 10 | 0.9 |
| Replicability, months | W and H refitted on odd and on even months (best of 5 starts each), each half matched to the KEPT patterns; for every kept pattern, the cosine between its odd and its even match | 0.9 |

Per town, not per market: the area rule is per town, and a market's share depends on which home counties form it
(rejected). A 5% level was rejected. Held-out month error (all 105 4 / 2 / 1 month partitions) is printed as a
persistence diagnostic only and does not choose K. Every K's tests, town by town, are in each market's
`patterns.json`.

| Market | K | Carrying town of each pattern | K + 1 fails on |
|---|---:|---|---|
| Columbia-Jefferson City | 2 | Vandalia, Ashland | odd/even months (0.87) |
| Springfield | 7 | Springfield, Republic, Seymour, Republic, Springfield, Marshfield, Cassville | starts (0.20), months (0.25) |
| Paducah-Cape Girardeau | 3 | Sikeston, Marble Hill, Jackson | no town (best: Marble Hill, 643 residents), months (0.72) |
| Ottumwa-Kirksville | 2 | Macon, Kirksville | no town (best: Lancaster, 695 residents) |
| Joplin | 4 | Neosho, Webb City, Lamar, Carthage | no town (best: Neosho 4%) |
| Kansas City | 5 | Lexington, Blue Springs, Independence, Independence, Harrisonville | no town (best: Independence 10% of residents, 9% of travel), months (0.87) |
| St. Joseph | 5 | St. Joseph, St. Joseph, St. Joseph, Savannah, Maryville | months (0.87) |

Not monotone: Joplin K = 3 fails starts (0.75) and K = 4 passes; Kansas City K = 2 and 4 fail, 3 and 5 pass; St.
Joseph K = 4 fails, 5 passes. Sensitivity (town threshold 10 / 15 / 20% × cosine 0.85 / 0.90 / 0.95): Columbia 3 / 2 /
2 at every town threshold; Springfield 7 (6 at 20%); Cape Girardeau 3; Kirksville 2; Joplin 4; Kansas City 5 (3 at
20%); St. Joseph 6 / 5 / 2 (5 / 5 / 2 at 20%). Kept fit, Columbia: all 10 starts reach the same loss; matched cosine
1.00; kept-to-half cosines 0.99 / 0.99 and 1.00 / 1.00; odd/even 0.95 and 1.00.

| Town | Residents allocated to the area (ACS) | Share of the town's residents |
|---|---:|---:|
| Columbia (82 block groups) | 103,086 | 93% (one area) |
| Mexico (7) | 5,685 | 86% |
| Linn (1 block group, holding the town) | 1,172 | 85% |

**Market test** (`flows/market_patterns.py`). For each county in a pattern: crossover = the town's residents in the
pattern × the county's share of the pattern's travel; spillover both ways, March 2026, local outlets only, weighted as
the adopted measure (current areas; printed by the stage-3 tie run, `logs5/tie_columbia.log`). Mexico-Boone: ~832
residents crossing, Audrain outlets' stories about Boone 10.0%, Boone outlets' about Audrain 0.5% -- demand and
one-way supply. Linn-Cole: ~289 crossing, 8.1% and 0.2%. Columbia's area is Boone-centred (Boone 45% of its travel;
St. Louis, the next county, 6%).

**Outlet homes** (user, 2026-10-24): an outlet's home county is the county it is filed under, except Mid Rivers
Newsmagazine (St. Charles) and Greene County Commonwealth (Greene) (`excluded_outlets.HOME_COUNTY`); their home town
for the incoming tie and the outlet circles is the covered county's seat, St. Charles city (not O'Fallon, the larger)
and Springfield. Registry: the pinned copy (`excluded_outlets.registry()`). `EXCLUDE` (campus papers, statewide
outlets, Dos Mundos, KHQA 7) is out of every coverage term.

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
2026-10-24) -> current (residents now ACS):

| Market | Town | K | Areas | Shares, % | Residents |
|---|---|---|---|---|---|
| columbia | Columbia | 6 -> 2 | 2 -> 1 | 72 / 16 -> 93 | 76,912 / 17,513 -> 103,086 |
| columbia | Mexico | 6 -> 2 | 1 -> 1 | 74 -> 86 | 5,241 -> 5,685 |
| columbia | Linn | 6 -> 2 | 1 -> 1 | 92 -> 85 | 1,641 -> 1,172 |
| columbia | Ashland | 6 -> 2 | 2 -> 1 | 79 / 19 -> 100 | 13,219 / 3,141 -> 9,089 |
| columbia | Centralia | 6 -> 2 | 2 -> 2 | 50 / 26 -> 58 / 42 | 2,937 / 1,516 -> 3,296 / 2,380 |
| columbia | Vandalia | 6 -> 2 | 1 -> 1 | 88 -> 100 | 3,064 -> 3,238 |
| columbia | Hallsville | 6 -> 2 | 1 -> 1 | 68 -> 64 | 1,216 -> 1,360 |
| columbia | Belle | 6 -> 2 | 1 -> 1 | 100 -> 74 | 1,099 -> 965 |
| springfield | Springfield | 6 -> 7 | 3 -> 3 | 31 / 31 / 18 -> 26 / 23 / 17 | 47,874 / 46,689 / 27,425 -> 44,074 / 38,491 / 28,196 |
| springfield | Republic | 6 -> 7 | 2 -> 3 | 48 / 31 -> 40 / 17 / 16 | 9,997 / 6,475 -> 5,945 / 2,526 / 2,349 |
| springfield | Marshfield | 6 -> 7 | 2 -> 2 | 52 / 46 -> 52 / 46 | 5,827 / 5,231 -> 4,823 / 4,236 |
| springfield | Monett | 6 -> 7 | 1 -> 1 | 84 -> 85 | 5,435 -> 5,817 |
| springfield | Cassville | 6 -> 7 | 1 -> 1 | 93 -> 93 | 3,259 -> 3,120 |
| springfield | Seymour | 6 -> 7 | 1 -> 1 | 82 -> 85 | 2,530 -> 6,288 |
| cape | Cape Girardeau | 6 -> 3 | 3 -> 2 | 36 / 28 / 18 -> 70 / 22 | 13,587 / 10,397 / 6,611 -> 27,274 / 8,443 |
| cape | Sikeston | 6 -> 3 | 1 -> 1 | 78 -> 94 | 11,037 -> 12,386 |
| cape | Jackson | 6 -> 3 | 2 -> 2 | 61 / 16 -> 82 / 16 | 7,582 / 2,025 -> 9,250 / 1,758 |
| cape | Scott City | 6 -> 3 | 2 -> 1 | 47 / 33 -> 65 | 1,647 / 1,156 -> 1,543 |
| cape | Marble Hill | 6 -> 3 | 1 -> 1 | 33 -> 64 | 743 -> 1,286 |
| kirksville | Kirksville | 6 -> 2 | 2 -> 2 | 72 / 14 -> 87 / 13 | 14,301 / 2,781 -> 14,898 / 2,221 |
| kirksville | Macon | 6 -> 2 | 1 -> 1 | 70 -> 92 | 3,842 -> 5,906 |
| kirksville | Lancaster | 6 -> 2 | 1 -> 1 | 50 -> 100 | 541 -> 716 |
| joplin | Joplin | 6 -> 4 | 3 -> 2 | 58 / 17 / 16 -> 72 / 25 | 31,491 / 9,291 / 8,940 -> 37,659 / 13,072 |
| joplin | Carthage | 6 -> 4 | 3 -> 3 | 43 / 35 / 12 -> 37 / 35 / 26 | 4,335 / 3,545 / 1,221 -> 5,015 / 4,675 / 3,413 |
| joplin | Webb City | 6 -> 4 | 2 -> 1 | 63 / 20 -> 87 | 7,780 / 2,511 -> 10,804 |
| joplin | Neosho | 6 -> 4 | 1 -> 1 | 80 -> 85 | 8,305 -> 9,590 |
| joplin | Lamar | 6 -> 4 | 1 -> 1 | 73 -> 88 | 3,870 -> 4,239 |
| kansascity | Independence | 6 -> 5 | 3 -> 3 | 40 / 27 / 10 -> 52 / 20 / 17 | 43,227 / 29,383 / 10,741 -> 62,939 / 24,076 / 20,952 |
| kansascity | Lee's Summit | 6 -> 5 | 3 -> 3 | 51 / 22 / 13 -> 50 / 26 / 16 | 86,012 / 36,956 / 21,724 -> 49,956 / 26,435 / 16,311 |
| kansascity | Blue Springs | 6 -> 5 | 1 -> 1 | 72 -> 78 | 54,202 -> 40,986 |
| kansascity | Grain Valley | 6 -> 5 | 2 -> 2 | 72 / 20 -> 76 / 20 | 16,597 / 4,587 -> 10,567 / 2,710 |
| kansascity | Harrisonville | 6 -> 5 | 2 -> 2 | 80 / 14 -> 84 / 11 | 9,932 / 1,710 -> 9,255 / 1,176 |
| kansascity | Lexington | 6 -> 5 | 1 -> 1 | 81 -> 82 | 5,020 -> 4,940 |
| stjoseph | St. Joseph | 6 -> 5 | 3 -> 3 | 34 / 22 / 17 -> 32 / 30 / 24 | 17,542 / 11,560 / 9,055 -> 21,854 / 20,122 / 16,335 |
| stjoseph | Savannah | 6 -> 5 | 2 -> 2 | 37 / 25 -> 48 / 26 | 1,971 / 1,301 -> 2,718 / 1,481 |
| stjoseph | Maryville | 6 -> 5 | 2 -> 2 | 77 / 14 -> 73 / 15 | 6,740 / 1,184 -> 6,844 / 1,432 |

Areas: 58 (63 at K = 6); the count changed for 7 of 36 towns: Columbia 2 -> 1, Ashland 2 -> 1, Cape Girardeau 3 -> 2,
Scott City 2 -> 1, Joplin 3 -> 2, Webb City 2 -> 1 (fewer); Republic 2 -> 3 (more).

### The published map: the network-tie area as a probability surface (2026-10-24)

The paper's map is the network-tie area (`market_patterns.py` idx["net"]: travel × (1 + 0.3 out + 0.3 in + 0.7 shared
places + 0.7 shared coverage), gate, spatial lag and direction, home 100; user 2026-10-24). A single drawing moved by
more than half under hexagon size, busiest-place scaling and the dasymetric spread (Jaccard 0.34–0.56 on the
travel-only area, table below), so the area is drawn under every combination of plausible settings
(`flows/area_ensemble.py`), and each published 3 km hexagon carries p = the share of members that draw it.

| Setting | Values | |
|---|---|---:|
| Hexagon size (grid rebuilt) | 2, 3, 4 km | 3 |
| TRAVEL_TOP | 0.5 (busiest place 50, adopted), 1.0 | 2 |
| Dasymetric spread | off, DFLOOR 0.1, 0.25 (adopted), 1 | 4 |
| LAMBDA (spatial lag) | 0, 0.25 (adopted), 0.5 | 3 |
| Display selectivity | 40, 50 (adopted), 60% | 3 |
| Distance rule | on (adopted), off | 2 |
| **Full factorial** | | **432** |

Same K, patterns, data and news weights in every member; GAMMA 0.5, the tie cut 1 and the floor 5 held (the floor
never binds: each area's selectivity threshold is above it). **Connected-body rule:** a member draws its shown
hexagons joined into the area's body (pieces holding home and every piece within 15 km of them, the published
outline's rule); a 3 km hexagon counts as drawn when 50%+ of its area lies under the member's hexagons. Without the
body rule a big city that is one travel unit (Kansas City, Springfield) was drawn whole far from home in every member
without the distance rule (Columbia's core had 120 Kansas City-area hexagons). **Core = p ≥ 0.5** (the area as
stated); p ≥ 0.8 also reported. km² = hexagons × 5.85 (one area measure: hexagons inside the outline × 5.85 km²);
people inside = 2020 population of those hexagons. Replicability: the whole ensemble on each half of the year, each
half on its own fit (W and H refitted, matched to the kept patterns): correlation of p between halves, Jaccard of the
cores (home excluded).

| Area | Core p ≥ 0.5: km² | people inside | Core p ≥ 0.8: km² | people inside | Adopted drawing km² | share in core | Outline km² / people | Replicability: r(p) | Jaccard core 0.5 / 0.8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Columbia** | 1,380 | 224,723 | 696 | 182,057 | 1,146 | 90% | 3,607 / 269,311 | 0.99 | 0.90 / 0.95 |
| **Mexico** | 1,000 | 141,850 | 374 | 13,233 | 807 | 88% | 3,660 / 188,284 | 0.96 | 0.85 / 0.96 |
| **Linn** | 1,122 | 167,069 | 468 | 46,550 | 754 | 90% | 1,292 / 65,023 | 0.86 | 0.66 / 0.58 |
| Springfield I | 778 | 272,591 | 450 | 221,671 | 602 | 97% | 941 / 307,775 | 0.98 | 0.83 / 0.71 |
| Springfield II | 1,152 | 277,823 | 655 | 234,572 | 941 | 91% | 1,982 / 346,838 | 0.95 | 0.81 / 0.81 |
| Springfield III | 918 | 320,472 | 655 | 286,571 | 859 | 88% | 2,116 / 379,026 | 0.89 | 0.71 / 0.75 |
| Joplin I | 538 | 113,347 | 327 | 96,535 | 450 | 95% | 713 / 119,954 | 0.99 | 0.85 / 0.95 |
| Joplin II | 1,158 | 115,739 | 544 | 83,804 | 871 | 89% | 2,221 / 132,445 | 0.97 | 0.88 / 0.83 |
| Kirksville I | 1,725 | 33,952 | 865 | 27,838 | 1,403 | 86% | 4,864 / 201,365 | 0.95 | 0.84 / 0.78 |
| Kirksville II | 2,724 | 199,275 | 1,146 | 153,137 | 2,134 | 82% | 6,963 / 248,911 | 0.78 | 0.56 / 0.50 |

"People inside" counts everyone living in the area's hexagons, the home town and the towns it reaches included:
Mexico's and Linn's cores take in part of Columbia (Mexico core 34 Boone hexagons; Linn core 32 Boone, 34 Cole) and so
hold far more people than their residents. **Mexico's Boone hexagons: 34 in the core (p ≥ 0.5), 1 at p ≥ 0.8, 114 in
the adopted-setting outline.** Core composition: Columbia Boone 187, Randolph 14, Cole 13, Callaway 10; Mexico Audrain
82, Callaway 52, Boone 34; Linn Osage 122, Cole 34, Boone 32. Linn's surface is the least replicable (r 0.86, core
Jaccard 0.66): its one block group's travel is thin. Adopted-setting outline replicability (network tie, independent
halves, home excluded): Columbia 0.85, Mexico 0.74, Linn 0.55.

Map (`market_pattern_print.html`, default): hexagons shaded by p, keyed "drawn in this share of settings" (10, 20, 40,
60, 80%+), every hexagon drawn in 10%+ of settings; no selectivity, distance rule or outline step (they are in the
ensemble); the orange news dots belong to the adopted-setting map. `?prob=0`: the single adopted-setting map.
`?measure=lift`: the network tie against the travel-only tie (news alone). Exports carry p: `flows/civic_interest_areas.csv`
(adopted map rows plus every hexagon with p ≥ 0.1; column p) and the civic grid (`areas_p`). p is derived from Advan
travel at the hexagon level, while the civic grid was public Census geography only (Open: licence).

Sensitivity that motivates the ensemble (travel-only area; Jaccard of the shown hexagons beyond home with the adopted
ones; range over Columbia, Mexico, Linn; `area_sensitivity.csv`, `selection_sensitivity.csv`):

| Change | Jaccard |
|---|---|
| Hexagon 2 km / 4 km (area IoU) | 0.41–0.43 / 0.34–0.43 |
| TRAVEL_TOP 1.0 | 0.37–0.56 |
| No dasymetric spread / DFLOOR 0.1 / DFLOOR 1 | 0.40–0.46 / 0.67–0.89 / 0.61–0.79 |
| LAMBDA 0 / 0.5 | 0.63–0.68 / 0.71–0.73 |
| GAMMA 0 / 1 | 0.88–0.94 / 0.86–0.95 |
| Tie cut 0.5 / 2 | 0.72–0.80 / 0.58–0.75 |
| Floor 3 / 8 | 1.00 / 1.00 (not binding) |
| Selectivity 40% / 60% | 0.53–0.72 / 0.38–0.57 |
| No distance rule / 1.5x / 3x | 0.49–0.76 / 0.82–0.91 / 0.61–0.95 |
| Distance reach 2 / 6 hexagons | 0.92–0.98 / 0.83–0.98 |

The 2026-10-18 selection-rule sensitivity test (eight variants of selectivity and the distance rule, scored on
split-half agreement) is superseded by this table and the ensemble (appendix). Split-half agreement is
**replicability**, not validity: the same rule drawing the same area from either half of the year does not show the
area is the right one.

**Rural shading, dasymetric** (adopted 2026-10-17): Advan locates travel no finer than a block group, and a rural one
covers 30-60 hexagons (Barton County outside Lamar: 5 block groups). Within a rural block group, travel is spread by
OpenStreetMap destinations (115,453 statewide, `flows/build_destinations.py`): a hexagon's weight is (destinations +
0.25) / the block group's mean of the same, so the block group's average is kept, farmland falls and destinations rise;
travel capped at 1. Towns keep one value. A floor of 1 left sparse rural counties one flat band.

**Network tie, revised** (2026-10-17, Columbia first; other markets after the weights settle):
- (Removed 2026-10-24, stage 3.) Home county: home outlets' market is their county, so every home-county hexagon carried their outgoing tie (1.0).
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
- Headroom: travel is scaled so a town's busiest destination is 50 (from stage 3, after the town's own units are masked); home stays 100. At 100 the top destination started
  at the cap and its news ties could not show (Linn's paper covering Jefferson City, Linn's busiest destination).
- Orange dots mark what news coverage alone adds (before the spatial effect): 10%, 25%, 50%+.
- ONE SCALE (adopted 2026-10-17; replaces a TV-market frame and a zoom rule): every map is a fixed frame about 190 x 180
  km -- the size of the Columbia-Jefferson City TV market, some 12-16 counties -- centred on the town's area (the
  tie-weighted centre of its hexagons of 10+), shifted only to keep the home county in view. Three counties (St.
  Joseph's, Kirksville's TV markets) was too close; 26-27 (Springfield's) too far. The TV-market outline stays
  as a reference line. Travel data and county lines cover Missouri only: across a state line the frame is blank.
- Display selectivity: each map shows only the hexagons holding the strongest 50% of its ties outside home (floor never
  below 5; isolated hexagons need up to twice it). Cuts the long tail so compact and diffuse areas read alike. At 80%
  the floor fell to 3-4 and cut nothing. In the published map selectivity is one of the ensemble's settings (40, 50, 60%).

**Frame and display** (adopted 2026-10-17): destinations are all of Missouri (towns and rural block groups) so travel
across a TV-market border is measured. Hexagons show at 5+ inside the TV market and 10+ outside it, so one-off distant
trips and rural destination clusters stay off. Labels: home town bold; up to 8 towns on shaded hexagons in ink; up to 4
unshaded towns of 20,000+ in small grey.

**Markets fitted separately** (`flows/regions.json`; `build_homes.py`, `travel_patterns.py <region>`,
`market_patterns.py <region>`): each TV market's patterns are fitted on its own home counties only, so adding a market
never changes another's maps (Columbia's fit verified identical after the change, 2026-10-17). Seven: Columbia-Jefferson City (Audrain, Boone, Osage), Springfield (Greene, Webster,
Barry), Paducah-Cape Girardeau (Cape Girardeau, Scott, Bollinger), Ottumwa-Kirksville (Adair, Macon, Schuyler), Joplin
(Jasper, Newton, Barton), Kansas City (Jackson, Cass, Lafayette), St. Joseph (Buchanan, Andrew, Nodaway). K by market
under the K rule above (2-7). Advan covers Missouri destinations only: trips into Kansas, Illinois, Iowa and Arkansas
are not seen (largest for Kansas City). Macon County had no local stories in March: no outgoing coverage there.

**Figure** (`flows/market_pattern_print.html`; default the probability surface, `?prob=0` the adopted-setting map; title
"<Town>'s civic interest area" since 2026-10-20, earlier "<town>'s revealed news market"): a modelled map on the hexagon grid; hexagons of 5+ shaded, one ring of empty hexagons as a
border, labels never on a dark (20+) hexagon. A shaded rural block group or tract can cover half a county; the grid
marks the figure as a model.

Superseded on the way (kept in `flows/`): tract reach maps (`build_reach_map.py`, a shrunk logistic model chosen on
held-out months, corridor term adopted, direction and home-town terms no gain) and a travel x coverage interest index
(`build_interest_map.py`, w = 0.5/1/2, with road corridors from `build_transit_lines.py`).

### Changes, 2026-10-24 (stage 3): civic interest areas

| Change | Script |
|---|---|
| K rule per town (option A) with independent-half replicability; carrying town and failing test printed; sensitivity table; held-out month error a persistence diagnostic only | `flows/travel_patterns.py` |
| Residents: ACS population through the calibrated per-block-group denominator; used by the K rule's 1,000 test | `flows/travel_patterns.py` |
| Missing home-months NaN-masked in every mean, fit and score | `flows/travel_patterns.py` |
| Replicability on independent halves: W and H refitted per half, matched to the kept patterns (the odd fit's order had been reported as the kept order); half fits written to `patterns_halves.json` | `flows/travel_patterns.py`, `analysis/confidence_layer.py`, `flows/pattern_halves.py` (now a check) |
| Town's own units masked before the busiest place is set to 50 and before county shares; town travel weighted by residents (people's visits) | `flows/market_patterns.py`, `analysis/confidence_layer.py`, `analysis/market_evidence.py` |
| Blanket home-county outgoing tie (out = 1) removed | `flows/market_patterns.py` |
| Hexagon county from the block group holding its centre | `flows/market_patterns.py` |
| Statewide / national / international stories out of the ties, as in coverage density | `flows/market_patterns.py` |
| Travel-only index (idx["travel"]) beside the network tie; two outlines (published network tie; travel-only footprint) | `flows/market_patterns.py`, `analysis/confidence_layer.py` |
| One area measure: hexagons inside the outline × 5.85 km²; smoothing buffer on the km plane (isotropic) | `analysis/confidence_layer.py` |
| Settings ensemble with the connected-body rule; probability surface; p in the exports | `flows/area_ensemble.py`, `flows/market_pattern_print.html`, `flows/export_area_table.py`, `flows/export_civic_grid.py` |
| `?measure=lift`: network tie against the travel-only tie (news alone) | `flows/market_pattern_print.html` |
| Sensitivity table of the travel-only area | `analysis/selection_sensitivity.py` |
| County-story weight per hexagon capped at the story's weight; town buffer on the km plane; people inside; "none" stated structural; QA label | `analysis/area_coverage_alignment.py`, `analysis/cin_diet.py` |
| Outlet home county by `excluded_outlets.home_fips`; home town of the two re-homed outlets = covered county's seat; pinned registry | `flows/market_patterns.py`, `analysis/tie_footprint.py`, `analysis/area_coverage_alignment.py` |
| Library cut point fixed (`if __name__ == "__main__":`) | `analysis/market_evidence.py`, `analysis/market_stability.py` |
| Tie-footprint run settings printed and documented; diagnostics CAMPUS_IN, REHOME, SCORE, MASKHOME, OUTDIR; market file no longer rewritten by a tie run | `analysis/tie_footprint.py` |
| Fast masked NMF stated in the docstring; `build_flows.py` reads the repository's `free/` | `flows/travel_patterns.py`, `flows/build_flows.py` |

### Name: civic interest areas (2026-10-20)

The local information needs areas are renamed **civic interest areas** (user): residents' activity areas of news
interest. Map titles: "<Town>'s civic interest area", numbered I, II, III only when a town has more than one
(Columbia, one area since 2026-10-24: no numeral). Earlier sections keep the name they were written under. Units of
analysis: county -> civic interest area -> each outlet's zone of service; no statewide measure is a finding.

## Supply (QA only; next paper)

Coverage density and the balanced diet are not results of this paper. They are measured on the **travel-only area**
(idx["travel"]: travel, spatial lag and direction, home 100, no news term; outline `confidence_layer.py`
outline_travel), so that no news term shapes the area the supply is measured in. The figures below are QA diagnostics
for the next paper; they are kept out of Current results.

| Area (travel-only) | km² | People inside | Residents allocated | Replicability (independent halves) | Frequent / regular / sporadic / none (QA) | Balanced diet (QA) |
|---|---:|---:|---:|---:|---|---:|
| Columbia | 3,502 | 268,372 | 103,086 | 0.735 | 34 / 9 / 57 / 0 | 22% |
| Mexico | 3,613 | 180,318 | 5,685 | 0.758 | 18 / 5 / 77 / 0 | 9% |
| Linn | 1,292 | 65,023 | 1,172 | 0.56 | 22 / 9 / 69 / 0 | 17% |

"None" cannot occur: every hexagon lies in a county whose county-level stories reach all its hexagons. County-story
weight per hexagon is capped at the story's weight; statewide, national and international stories add nothing, in the
ties as in coverage density.

### Coverage density (2026-10-20; QA rerun 2026-10-24)

**Coverage density** (name set by the user) is the supply into an area: for each 3 km hexagon of the footprint
(hexagons whose centres lie inside its outline; every hexagon counts the same), the local news stories in a month whose
area includes it. Central focus counts 1, a mention 0.5, Sports half. A story's area follows its geographic scope (the
enrichment's scope classification): neighbourhood 3 km around its point; town the 2020 place and 3 km around it (5 km
around a point outside any town; buffers on the km plane); regional 40 km; a county-only point or a county mention the
whole county; statewide, national and international stories none. Local outlets statewide; `EXCLUDE` left out. Tiers
(user; names from 2026-10-20, first written "daily" and "weekly"): frequent 9+ a month (2–3 a week), regular 2–8 (2–3
a month as the floor), sporadic under 2, none. `analysis/area_coverage_alignment.py` →
`analysis/area_coverage_alignment.csv`, `flows/reach/coverage_columbia.json`; map:
`market_pattern_print.html?measure=coverage` (`&cov=local` leaves out county-level stories and county mentions).

**Attribution by region size (2026-10-20, adopted).** City, county and region claims apply to the whole region,
diluted by its size (user): weight per hexagon = story weight × (7 / the region's hexagons) ^ 0.5, full weight at 7
hexagons or fewer (a neighbourhood, a town the size of Linn). Revised the same day (user: the square root "overvalues
mentions and county-wide coverage"; the region "looks well-covered, which it is not"): counties and regions are counted
once (alpha = 1, spread by 2020 block-group population); towns and neighbourhoods keep the square root. `ALPHA=1`
(towns also counted once) is the sensitivity. Frequent coverage barely moves with alpha (it is place-specific
reporting); the regular tier is what county-wide stories supply.

**Map (user decisions, 2026-10-20).** Tiers in separate colours first, then the scale stops at frequent (9+ a month) as
one colour: the volume steps above it (30–99, 100+) peaked in the population centres and showed population size.
Stories stay a monthly count, not per capita (user). A blurred surface beneath the grid was tried and rejected (user:
the blur "just does not work" beside the civic interest area maps; `?surface=1` keeps it): each hexagon is filled with
the continuous green (log scale, capped at 9+ a month) with white gaps; the key is a word-only gradient from "rarely"
to "several a week or more"; the subtitle keeps the tier shares. Lines step back on the coverage map (lighter grid,
county borders, home county and TV market).

### Balanced diet of civic information (2026-10-20; QA rerun 2026-10-24)

`analysis/cin_diet.py`. The ten CIN categories of the codebook (the eight critical information needs, Friedland et al.
2012, plus Civic Life and Sports). A hexagon has a **balanced diet** when any 8 of the 10 reach 1 story a month each by
coverage density (user: "8 of 10 served, but any 8"). The coverage density map is filtered by it (user: "volume is not
enough, balance is also required"): coverage is shaded only where the diet is balanced; elsewhere pale (`?balance=0`
turns the filter off). Sports at half weight from 2026-10-20 (user). Outlets required for the balanced share are
computed exactly over every combination of the top 24; the earlier outlets-required calculation on volume alone
(`outlets_required.py`) is superseded: one broadcaster and one weekly cannot supply a balanced diet.
**Map: volume as colour, breadth as size (user, 2026-10-20).** The binary balance filter was "too flat", and the shade
graded by volume × balance did not show volume without breadth. Each hexagon's colour is its stories a month; its size
is its breadth, full at 8+ of the 10 categories and shrinking to 40% with fewer, on a pale full-size grid -- a small
dark hexagon is plenty of news of a narrow kind (Moberly, Mexico, Boonville); only Columbia and Jefferson City are full
size.

## Open

- One month of coverage limits every story-count comparison; counts per county pair are small.
- Coverage: `combined_marginal_test.py` and `hospital_test.py` score the adopted coverage model at 4.25 (no
  broadcasters 4.37) on destinations with 1%+ of visits, `coverage_model.py` at 4.49 (print 4.59) on the same metric;
  not reconciled. Not rerun: County characteristics, coverage column (4.00 baseline, outcome-selected destinations);
  the level version of saturation alone (tested only within the all-factors model).
- Out-of-state travel: Kansas is measured (12.3% of Missouri residents' observed out-of-county visits; 34.9% for the
  14 border counties). Illinois, Iowa, Arkansas, Oklahoma and Nebraska destinations are not in the data; eastern and
  southern border counties' travel and crossover are understated by an unmeasured amount.
- Calibration: Advan's scale is about two units per resident (statewide 1.70–2.32 by month), not one; phantom home
  block groups (3.3% of block group-months, 10.7% of devices seen at home) and St. Louis city's under-detection are
  unexplained. Question for Advan.
- Travel: the border block's held-out gain is not established (+0.185 [−0.048, +0.411]); kept by theory. Unemployment
  rate × distance not tested (no estimates in `mo_county_acs_2024.csv`). Athletic conferences: statewide test pending;
  the three-county figure is against the 2026-10-18 model, not rerun.
- Spillover: the Centralia Fireside Guard and Vandalia Leader have no usable spillover figure (short texts).
  Expectations for the 33 outlets that are not well collected are extrapolations. Held out, St. Joseph and
  Quincy–Hannibal do worse than intercept only. The print-outlet hypothesis term's gain interval touches zero.
- Public travel model: no setting or correction is stable for the 9-county commuter classes — the major-metro rings'
  Stage 1 choice changes with the county left out (nested 6.05 vs in-sample 5.15), the regional-hub rings' with fold 1
  (outer-loop corrections 5.58 vs 4.38 in-sample); the destination pull needs public measures beyond sales and
  population (hospital, four-year college, supercenter, interstate, lakes and parks, county seat).
- Public travel model, not rerun on the adopted outcome: the gap decomposition (`public_gap_corrections.py`), the
  setting sensitivity (`public_default_sensitivity.py`), and Missouri corrections applied to Kansas small rural
  counties only.
- Kansas: the public model's 200-mile destination radius leaves 9.1% of Kansans' Advan share (max 40.7%, Thomas)
  outside its support; a wider radius for the Kansas builds is untested. The Kansas outcome is not pass-through
  discounted.
- Civic interest areas: the civic grid carries p, derived from Advan travel at the hexagon level, where it had held
  public Census geography only — check against the Advan licence before it ships to datadesk.
- Civic interest areas: the connected-body rule (pieces holding home and every piece within 15 km of them) was added
  to the ensemble after members without the distance rule drew Kansas City and Springfield whole far from home; its
  15 km is held fixed, not varied among the 432 members.
- Civic interest areas: Kansas City's persistence diagnostic (held-out month error over all 105 partitions, 229 missing
  home-months masked) is slow to run and is not reported.
- Civic interest areas: network-tie values, weight sensitivity and display floors quoted on 2026-10-17 were computed on
  the K = 6 areas and are not rerun. Linn's surface replicates least (r 0.86, core Jaccard 0.66).
- Tie markets: Columbia's public market reaches 0.13 of Advan's beyond Boone (the public model sends Columbia's
  out-of-county travel to Jefferson City). The Kansas transfer of travel markets and the comparison with conventional
  market definitions (2026-10-18) have not been rescored with home masked and the score taken beyond the home county.
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

Every replaced figure, with what replaced it and why. "Was" gives the earlier values in order: 2026-10-16 to 10-18,
then "first review" (2026-10-24, first round). "Now" is the current value (2026-10-24, after the second review).
"Not rerun" = no replacement figure; the old one stands only as dated history.

| Model | Figure (where) | Was | Now | Why |
|---|---|---|---|---|
| Data | Calibration factor as the device → person scale | Median 1.94, middle 80% 1.09–3.18; Audrain 1.19–2.54, Boone 1.58–2.52, Osage 2.19–4.26; monthly medians Jan 1.78 … Sep 1.65 (first review) | Kept as `factor`, not adopted; adopted `factor_statewide` 1.70–2.32 by month; trimmed Audrain 1.19–2.40, Boone 1.50–2.44, Osage 2.19–3.72 | The county factor measures home detection (county medians 0.24–10.78) |
| Data | Calibration effect on the travel model | Log-distance term −2.14 → −1.58; "still predicts 93%"; first review: elasticity at 25 mi metro −0.95 → −0.89, nonmetro −0.45 → −0.46; held-out 3.29 → 3.26 | County factor −0.904 / −0.475, error 3.28; adopted statewide scale −0.978 / −0.473, error 3.31 (Travel model, Sensitivities) | Statewide scale; centred terms |
| Data | Calibration, other models | "Outlet model unchanged (broadcaster 0.70, crossover 1.47)"; "coverage's response to travel 0.52" | Adopted spillover model has no travel term; coverage metro 0.49, nonmetro 0.25 | Models replaced |
| Data | Estimated town residents | Columbia ~107,000 / ~106,900; Mexico ~7,100 / ~7,130; Linn ~1,800 / ~1,790 | ACS population of the block groups 111,055; 6,619; 1,381 (statewide factor 102,803; 6,742; 2,802); allocated to the area 103,086; 5,685; 1,172 | The county factor carried home over-detection |
| Data | Device IDs "stable at least week to week" | 424 block groups, monthly lower in 71, 62 passing the same-scale check | Withdrawn: 376 block groups, lower in 55, 48 passing; 7 show the products' scales differ | Places merged by `PERSISTENT_ID`; cross-product scales unknown; no within-product test |
| Data | Pass-through discount | Removes 3.0% (2026-10-16); 2.3% (first review) | 1.74% under the adopted definition (2.2% on the statewide scale; old codes 2.32%, codes fixed 3.35%, highway at the statewide norm 2.98%) | Convenience stores missing (2017 NAICS); every road stop counted as a highway stop |
| Data | Kingdom City share discounted (Audrain → Callaway) | 20% | Not rerun | Discount redefined |
| Crossover | Distinct residents seen outside, lower bound | Audrain 41%, Boone 24%, Osage 45%, Missouri median 52% | 44%, 26%, 57%, 58% (bounds 34–53%, 20–31%, 43–69%, 44–69%) | Calibrated denominator (b = 0.51); Kansas destinations; St. Louis unit before the leaving test |
| Crossover | St. Louis | "22% summed, at least 46% as people" | 22% summed, at least 35% as people (bounds 18–46%) | Unit fix before the leaving test; calibrated denominator |
| Crossover | March three-county check | Audrain 42%, Boone 29%, Osage 44% | Not restated for the calibrated form; b = 1: 39%, 27%, 66% | Denominator |
| Crossover | Lower bound above commuting | 112 of 114 counties | 113 of 114 (St. Charles set by commuting) | As above; JT01 |
| Crossover | Employed residents working in another county ÷ population (LODES) | Audrain 23%, Boone 11%, Osage 33%, median 23% | 21%, 11%, 31%, 21% | JT01; JT00 counted multiple jobholders twice (commuters ÷ employed: median 61.6% → 61.7%) |
| Crossover | Tract floors, population-weighted conservative | Audrain 43%, Boone 28%, Osage 50% | 44%, 27%, 57% | January–July tracts only; calibrated denominator; JT01 |
| Data | Regular travel per tract (`directions_per_tract.py`): 1 / 2 / 3+ directions; count right, public / corrected | 8 / 29 / 63%; 77% / 78% | 8 / 30 / 63%; 78% / 77% (first direction 78% / 83%, unchanged) | January–July tracts only; 6 of 7 months |
| Travel | Share of July–September shares predicted | 93%; 94% with commuting; first review: held-out R² 93.8% [92.4, 94.9], Jul–Sep stability 93.8% vs persistence 98.6% | Held-out R² 93.7% [92.4, 94.9]; stability R² 93.9% vs persistence 98.7% | Squared correlation, not R²; the Jul–Sep split is beaten by persistence |
| Travel | Held-out error | First review 3.26 [2.93, 3.59]; classes 3.44 / 2.83 / 3.85 / 2.47 | 3.31 [2.96, 3.64]; 3.57 / 2.87 / 3.68 / 2.45 | Statewide scale, highway discount, JT01 |
| Travel | Steps table | Deviance 480M / 359M / 275M / 165M / 137M; 76% / 81% / 86% / 92% / 93%; top destination 1.63× / 1.42× / 1.22× / 1.15×; first review: deviance 358.2M … 68.8M, held-out R² 64.8% … 93.8%, errors 9.62 / 7.25 / 5.79 / 5.03 / 4.24 / 3.71 / 3.26, top destination 1.15× … 1.02×, within 15% … 49% | Steps table (246.3M … 62.0M; 72.3% … 93.7%; 8.13 … 3.31; 1.26× … 1.03×; 18% … 51%) | In-sample, observed-selected; then the second-round outcome |
| Travel | Singly-constrained model's main destinations | Under-predicted by 1.6× (also Comparisons withdrawn); first review 1.19×, held-out error 7.25 | 1.15× held out, forecast-selected; held-out error 6.46 against 3.31 | Selected on the outcome; in-sample |
| Travel | Top destination, actual ÷ forecast | 1.15–1.2×; first review 1.02× (1.11× observed-selected) | 1.03× (1.13× observed-selected) | Held out, forecast-selected |
| Travel | Big flows | Middle 80% 0.73×–1.88×; first review 483 pairs, error 3.45 [3.17, 3.74], 49% within, 0.57×–1.51× | 484 pairs, 3.44 [3.16, 3.73], 51% [46, 55], 0.61×–1.51× | In-sample, observed-selected; second-round outcome |
| Travel | Main destinations, actual ÷ expected | Osage → Cole 2× (singly constrained), 1.15–1.2×, 1.28 → 1.09 with commuting; Osage → Boone 1.30 → 1.64; Audrain → Boone 0.99 → 0.97; Audrain → Callaway 1.68 → 1.39; Audrain → Marion 1.83 → 2.40; Boone → Cole 0.73 → 0.70; Boone → St. Louis 1.47 → 1.33; first review held out 1.14, 1.59, 1.01, 1.30, 2.21, 0.68, 1.29 | In-sample / held out: 1.04 / 1.13, 1.64 / 1.56, 1.02 / 1.03, 1.44 / 1.35, 2.21 / 2.13, 0.71 / 0.67, 1.28 / 1.29 | Commuting; held out; second-round outcome |
| Travel | Coefficients and elasticities | First review: −0.887, −0.282, +0.427, −0.273, +0.160, +0.501, +0.284, +0.192; metro −0.37 / −0.89 / −1.28 / −1.67, nonmetro +0.56 / −0.46 / −1.23 / −2.00 at 10 / 25 / 50 / 100 mi | −0.978, −0.265, +0.505, −0.258, +0.182, +0.465, +0.284, +0.200; metro −0.49 / −0.98 / −1.35 / −1.71, nonmetro +0.49 / −0.47 / −1.20 / −1.92 | Second-round outcome; JT01 |
| Travel | Selection | First review joint test: adopted vs fixed effects 16.76 → 3.26 (−13.50); drop-one gains +0.056 to +0.377; candidates same metro +0.003, nearest centre −0.014, adjacent +0.003, size × distance +0.011; nested −0.050 / −0.041, one at a time −0.051 [−0.100, −0.002] | Blocks: distance +0.994, border +0.185 [−0.048, +0.411], commuting +0.474, all pair terms +12.852; nested guard −0.061 [−0.205, +0.096] / −0.031; one at a time −0.047 [−0.085, −0.009] (reference only) | Selection procedure (user) |
| Travel | Commuting gains | Small rural 3.76 → 3.28, top-3 4.81 → 4.25, independent towns 3.05 → 2.79, commuter 4.13 → 3.82, hubs 2.43 → 2.11; first review all 3.71 → 3.26 (−0.45 [−0.70, −0.21]), 3.94 → 3.44, 4.86 → 4.31, 3.18 → 2.83, 4.28 → 3.85, 3.04 → 2.47 | All 3.78 → 3.31 (−0.47 [−0.72, −0.27]); 4.06 → 3.57; top-3 4.97 → 4.36; 3.33 → 2.87; 4.22 → 3.68; 2.78 → 2.45 | Second-round outcome; JT01; forecast-ranked top-3 |
| Travel | Commuting coefficients | +0.28 / +0.19; first review +0.284 (0.051) / +0.192 (0.036) | +0.284 [+0.194, +0.373] / +0.200 [+0.127, +0.273] | JT01 |
| Travel | Kansas share of out-of-county visits | First review: border counties 37.7%, all Missouri 11.6%; Platte 30.4, Cass 28.8, Bates 22.7, Vernon 22.2, Jasper 20.0, Barton 19.9, Newton 8.1, McDonald 7.3, Atchison 7.0 | 34.9%, 12.3%; 30.3, 28.7, 22.6, 22.3, 20.1, 19.8, 8.0, 7.0, 7.2 | Statewide scale, undiscounted |
| Travel | Driving time | Deviance 137M → 136M; Jul–Sep 93.0% → 92.3%; first review +0.07 [−0.14, +0.31] | +0.079 [−0.113, +0.310] | Held out; second-round outcome |
| Travel | "On the way" factor | Deviance 134M; first review −0.05 [−0.27, +0.22], weighted −0.06 [−0.31, +0.19] | −0.055 [−0.268, +0.209]; weighted −0.075 [−0.320, +0.184] | As above |
| Travel | Competing destinations | −0.05 and 0.00, deviance 80.0M → 79.5M / 80.0M; first review nearest alternative −0.051 [−0.100, −0.002], −0.065 (p 0.04), "passes one at a time"; other directions −0.01 [−0.04, +0.02] | −0.047 [−0.085, −0.009], rejected by the nested guard; other direction −0.035 [−0.069, +0.001] | Nested guard; second-round outcome |
| Travel | Fotheringham C_ij | −0.83, deviance 80.0M → 78.9M, within 46% → 44%, Osage → Cole 1.28× → 1.21×; first review −1.04, +0.02 [−0.08, +0.14] | −1.07; +0.031 [−0.063, +0.140] | As above |
| Travel | Area-centre and similar terms | Same metro/micro "deviance unchanged", nearest centre p 0.74, intervening "small gain", adjacent "deviance −3M"; first review +0.00 / −0.01 / +0.00 / +0.03, all four +0.05 | +0.008 / −0.015 / −0.005 / +0.032; all four +0.034 | Held out; second-round outcome |
| Travel | Singly-constrained destination attributes | Jobs per resident p 0.44, metro p 0.27; first review jobs p 0.69, metro p 0.75, stores p 0.19 | Metro −0.08 (p 0.57), jobs p 0.71, stores +0.73 (p 0.002) | Two-way clustering; second-round outcome |
| Travel | Origin-class-specific terms | Hubs 2.02 → 1.77; first review k = 4 all +0.17 [+0.00, +0.35], hubs −0.11, independent towns +0.51; k = 2 / 3 +0.08 / +0.09 | k = 2 / 3 / 4: −0.00 / +0.04 / +0.09; independent towns +0.40, hubs −0.32 | As above |
| Travel | Work and non-work apart | First review −0.00; without commuting +0.41 [+0.19, +0.65], Audrain → Marion 2.40× → 1.96× | −0.00; +0.44 [+0.24, +0.67] | As above |
| Travel | Tier and county pull | 3.75 → 3.70 / 4.79 → 4.68; jobs pull 1.60 vs 1.39; first review pooled 3.86 / 4.80, tier pull 3.81 / 4.72, theory 4.40 / 5.28, county 3.82 / 4.70, tier + local 3.88 / 4.78 | `travel_tier_pull_cv.py` table: adopted 3.307 (small rural 3.572); nested change +0.045 [−0.087, +0.199]; none adopted | Held-out standardisation; 8 terms; forecast top-3; nested guard |
| Travel | Small origins; measured draw; shrinkage | First review 3.76 vs 3.32; +0.94 / +1.33; 3.11 vs 3.05 | 3.77 vs 3.46; +0.60 / +1.18; 3.20 vs 3.14 | Second-round outcome |
| Travel | Job-hub distances | "All worse (3.93–4.60)"; first review 3.40–3.48 vs 3.35 | 3.48–3.51 vs 3.47 | As above; JT01 |
| Travel | Blend with own shares; pass-through as recorded | First review 1.51 (−0.00); 3.18 against 3.26 | 1.46 (−0.01 [−0.03, +0.02]); undiscounted 3.21 against 3.31 | As above |
| Travel | Stability and references | First review: Jul–Sep error 3.01, persistence 1.51, big flows 3.20 / 55% and 1.43 / 92%, model − persistence +1.49 [+1.20, +1.78]; destination effects + log distance 6.13 (−2.87); in-sample deviance 68.8M | 2.95, 1.46, model − persistence +1.49 [+1.17, +1.79]; 5.66 (adopted lower by 2.35); 62.0M | Second-round outcome |
| Travel | All marginal factors | 3.58 / 3.39 / 4.04, 93.1% / 93.6% / 90.4%, within 49% / 49% / 42%, "about 5% gain with all eight"; first review 3.26 / 3.15 / 3.21 / 3.84, −0.11 [−0.31, +0.10], −0.05, +0.58 | 3.31 / 3.19 / 3.25 / 3.83; −0.11 [−0.31, +0.09]; −0.06 [−0.20, +0.10]; +0.53 [+0.09, +0.97] | Held out; intervals; second-round outcome |
| Travel | County characteristics, travel column | Baseline 3.51; degree × distance 3.43; hospitals 3.48; first review baseline 3.26 / 3.45 | Baseline 3.31 / 3.44; County characteristics table | Jul–Sep big-flow error selected on the outcome; second-round outcome |
| Travel | Tier sizes | Hubs 8 | Hubs 8 in `county_class_k4.csv` (114 counties); scored, 9 with St. Louis city (115 homes) | St. Louis city and county scored apart |
| Coverage | Headline elasticity | "About 0.7–0.8% more stories per 1% more visits" | Metro 0.49, nonmetro 0.25 | No distance terms: distance loaded onto visits |
| Coverage | Response to travel (calibration; commuting) | 0.52; "falls from 0.52 to 0.36"; twice the travel → 1.4×, then 1.3× | Metro 0.49 (1.41×), nonmetro 0.25 (1.19×); pooled 0.36 | Log distance + border only; log visits; hypothesis term |
| Coverage | Elasticities | First review: metro 0.49 (0.066; 0.36–0.62), nonmetro 0.25 (0.061; 0.13–0.37); print 0.51 / 0.25; difference −0.235 (0.039); 1.40× / 1.19×; leave-one-out 0.45–0.53; pooled 0.36 (0.060) | 0.49 (0.070; 0.36–0.63), 0.25 (0.063; 0.13–0.38); print 0.52 / 0.26; −0.241 (0.040); 1.41× / 1.19×; 0.46–0.54; pooled 0.36 (0.064) | Second-round outcome |
| Coverage | Commuting terms | In +0.51 (p < 0.001), out +0.04; first review in +0.42 (0.073), out −0.02 | In +0.41 (0.073), out −0.03 | Adopted specification; JT01 |
| Coverage | Held-out error | 4.15 → 4.12; first review 0.913 [0.844, 0.982] / 4.42 [4.00, 4.91] (print 0.939 / 4.53) | Primary 4.49 [4.04, 4.98] (print 4.59); all destinations 0.915 (print 0.941) | Destination set chosen partly by the held-out stories; loco folds; second-round outcome |
| Coverage | Nonmetro interaction | First review: adopted on held-out error, change −0.143 [−0.221, −0.068] vs pooled | Hypothesis term, gain +0.125 [+0.048, +0.202] (print +0.090) | Selection procedure |
| Coverage | Saturation | Response 0.67 → 0.50, p 0.004 / < 0.001, "real and in the predicted direction"; first review own stories −0.007 (p 0.34), changes ≤ 0.021 | Nested guard change +0.011 [−0.005, +0.027]: not supported; own stories −0.006 (p 0.43) | Separate non-adopted model; HC1; nested guard |
| Coverage | Border test | "±60% at 95%"; raw "about half"; first review +0.04 [−0.04, +0.12] (print +0.06), raw 6.7% / 7.8% / 15.8%, ring −1.16 (0.52) | +0.04 [−0.04, +0.13] (print +0.07); 6.7% / 7.7% / 15.9%; ring −1.22 (0.54) | HC1; specification labelled; second-round outcome |
| Coverage | Zero-visit treatment | First review adopted 0.486 / 0.252, at log(1e-3) 0.482 / 0.246 | 0.494 / 0.254; 0.490 / 0.248 | Second-round outcome |
| Coverage | All marginal factors | 4.15 / 4.14 / 4.18; print 4.50 / 4.58 / 4.52; first review scratch 0.91 / 0.91, 4.42 / 4.39 (print 0.94 / 0.93, 4.53 / 4.50); scripts on outcome-selected destinations 3.47 / 3.78 | 4.25 / 4.24 / 4.23 / 4.34 (no broadcast 4.37 / 4.38 / 4.36 / 4.41) on 1%+ of visits | Outcome-selected destinations; the scratch table came from no repository script |
| Coverage | Collection quality | 0.52 → 0.48 (all), 0.50 → 0.42 (print); first review 0.36 → 0.26, 0.34 → 0.25 | Pooled specification 0.36 → 0.25, 0.35 → 0.26 | Old specification; rerun |
| Coverage | County characteristics column; hospitals | 4.00; 4.01 | Not rerun; `hospital_test.py` 4.25 → 4.26 (no broadcasters 4.37 → 4.36) | Outcome-selected destinations; old specification |
| Coverage | Out-of-state stories (Dos Mundos, KHQA 7) | Dropped silently (49 stories); first review DECISION NEEDED (re-home or exclude) | Excluded (`EXCLUDE`, user) | Spanish-language; Illinois newsroom |
| Spillover | 2026-10-16 models (whole section) | Broadcaster +0.70, travel out +1.47, held-out 14.5 (broadcaster only 15.5; full 15.3); urban-share model 15.0, well collected 14.1, coefficients +0.65 / −0.81 / +1.17 | Hypothesis terms broadcaster + print outlets: +0.667, −0.387; honest error 6.57 / 5.50 (fitted model 5.98 / 4.66) | Earlier measure (any story touching another county); earlier data |
| Spillover | 2026-10-17 intermediate re-run | 83 outlets, 46 counties; held-out 7.1 (8.6 before); broadcaster +0.58, crowded weekly −0.47, border −0.17, print outlets −0.42; Cole 30% / 33% (36% with statewide outlets); Jackson 29% / 29%; KC Beacon 37% → 23%, The Pitch 28% → 26%; Boone print 23% / 20% | Cole 23.1% / 25.4%, Jackson 21.9% / 19.1%, Boone print 18.3% / 19.3%, KC Beacon 17.3% / 11.7%, The Pitch 24.1% / 11.7% (held out) | CAMPUS, HOME_COUNTY, market-count rule, one home rule, selection procedure, held-out expectations |
| Spillover | Fitted outlets, counties | 87, 47 (also 83, 43) | 85, 48 | HOME_COUNTY, CAMPUS |
| Spillover | Outlets with 10+ stories | 133 | 128 | CAMPUS |
| Spillover | Broadcaster | +0.68 (p < 0.001, z); +0.71; first review CRV1 s.e. 0.135 | +0.667 (CRV3 s.e. 0.148); CI +0.388 to +0.939 | CRV3, t(47) |
| Spillover | Weekly in a daily-and-TV county | −0.56 (0.008); −0.37 (0.05) | Not adopted (change +0.09, −0.05 to +0.27) | Nested guard |
| Spillover | Miles to the county edge (log) | −0.14 (< 0.001), every outlet; −0.17 (0.001) | Not adopted (change −0.08, −0.45 to +0.33) | Nested guard |
| Spillover | Print outlets in the county | −0.28 (0.001); −0.41 (0.01); first review s.e. 0.089 (CRV1), p < 0.001 | −0.387 (CRV3 s.e. 0.124, p 0.003); CI −0.655 to −0.232 | Market-count rule; CRV3 |
| Spillover | Held-out error | 6.0; 8.62 / 7.20 (83-outlet fit) | Honest error (nested search B) 6.57 / 5.50; fitted model 5.98 / 4.66 | Selection procedure: the search's nested figure |
| Spillover | Nested figure | 9.18 / 7.81 (pre-rerun data), same pair in 38 of 43 folds; first review 6.27 / 4.76 (joint rule inside each fold; adopted set in 47 of 48 folds) | Search B 6.57 / 5.50; nested guard from the hypothesis pair 6.05 / 5.05 | Selection procedure |
| Spillover | Joint test (first review) | Adopted set vs intercept only −1.51 [−2.61, −0.32]; term by term −1.55, −1.04 | Hypothesis-term gains +1.51 [+0.31, +2.58], broadcaster +1.55 [+0.36, +2.70], print +1.04 (lower bound −0.05 to +0.01 by seed) | Selection procedure |
| Spillover | Alternative models (83-outlet fit) | Broadcaster + crowded weekly 9.39 / 7.05; + town population 9.45 / 8.24; broadcaster + town population 9.79 / 8.64 | Broadcaster + crowded weekly 6.98 / 5.35; broadcaster only 7.02 / 5.11 | Current data and definitions |
| Spillover | Audrain / Boone / Osage / Cole / Jackson, actual / expected | 20% / 23%; 29% / 24% (print 18% / 16%); 26% / 24%; first review 20% / 22%, 29% / 26% (18% / 19%), 26% / 25%, 23% / 25%, 22% / 21% (print 23% / 14%) | Held out: 19.5% / 22.5%, 28.7% / 26.4% (18.3% / 19.3%), 25.6% / 25.3%, 23.1% / 25.4%, 21.9% / 19.1% (22.8% / 11.7%) | Expectations held out |
| Spillover | Outlets, actual / expected | First review: Mid Rivers 17% / 27%, Commonwealth 18% / 18%, Cash-Book Journal 23% / 18%, KC Beacon 17% / 15%, Kansas City Star 26% / 15%, The Pitch 24% / 13%, Vandalia Leader 4% / 26% | 17.3% / 22.6%, 18.5% / 17.4%, 22.5% / 22.3%, 17.3% / 11.7%, 26.4% / 11.7%, 24.1% / 11.7%, 4.2% / 22.5% | Expectations held out |
| Spillover | Springfield region held out | 10.9 (crowded 11.7, town population 11.9), 28% / 29%, Webster 44% / 26%; then 8.6, 27% / 27% | 8.0 (crowded 9.0, town population 8.8), 24% / 26%, Webster 36% / 23% | Current model |
| Spillover | Weight table | Rates 30.6% / 25.6% / 20.5% / 22.1% / 18.6% / 15.1%; held-out 7.1 / 6.0 / 6.8 / 6.7 / 5.5 / 5.6; "held-out ÷ mean" ranking; "best combination uses mention 0.5"; first review held-out expected Boone 27% (adopted row), Audrain 49% / 27% (mention 1.0) | Measure sensitivity table (Boone 26%, Audrain 48% / 28%): skill and out-of-sample R² against intercept only; weights are definitions | No code for the ranking; weights are not selected; held-out expectations |
| Spillover | Leave one market out | Weight combinations per market, mean 23.1 vs 23.4 (24.2 vs 23.7 without Columbia–Jefferson City) | Adopted model per market: 5.9 in sample, 6.2 held out, intercept only 7.4 | No code; weights are definitions |
| Spillover | By outlet type; non-weeklies only; Vandalia Leader 34%; Boone County Journal 15%, Centralia Fireside Guard 17% expected | 10.03 → 7.86 etc.; 9.40; 34%; 15%, 17% | Not rerun; held out: Vandalia Leader 22.5%, Boone County Journal 19.3%, Centralia Fireside Guard 19.3% | Model replaced |
| Spillover | Weekly alone in its county | −0.16 (p 0.28), −0.14, −0.18; nested 7.41 vs 7.36 | Not rerun | Crowded weekly not adopted |
| Spillover | Market position | p 0.35 / 0.82 / 0.24; mean 9.3 against 8.6; first review p 0.31–0.70 | CRV3 p 0.34–0.75; mean 6.03–6.07 against 5.90 (border form) | Current data; CRV3 |
| Spillover | Crowded-county weeklies' median; fits on all 128 outlets; mention weight under town population | 11% vs 24%; 11.5 / 11.1 / 11.2; Boone County Journal 2–21% … Mexico Ledger 14–57% | Not rerun | Model replaced |
| Spillover | Mid Rivers Newsmagazine, Greene County Commonwealth | Left out of the fit | Fitted with the covered county as home | HOME_COUNTY |
| Spillover | Quality selection | Not stated | 24.5% vs 17.5% (r +0.26, p 0.003) | Reported every run |
| Spillover | All marginal factors | 14.5; 14.9; 14.2 with ridge 0.05; 14.5 with ridge 0.2; "ridge 0.05 is 0.3 points better" | 6.43; 7.00 / 7.66; every combination worse | Current measure and model |
| Spillover | Crossover–spillover correlation | 68 counties r 0.10 (p 0.43), urban share fixed 0.08; well collected 44 counties r 0.30 (p 0.05) (53 counties, p 0.02 on 2026-10-17 data); first review all 72 +0.11 (0.36), weighted −0.01 (0.93); well collected 53 +0.35 (0.010), weighted +0.15 (0.27); well-collected counties 29 +0.35 (0.061), +0.20 (0.31) | Calibrated crossover: +0.18 (0.138) / +0.14 (0.225); +0.41 (0.002) / +0.37 (0.007); +0.40 (0.030) / +0.32 (0.095) | Calibrated crossover |
| Spillover | Collection quality | Urban share −1.09; 15.0 → 14.1; 28 counties, 36 outlets; first review in well-collected counties broadcaster p 0.042, print p 0.88 | 7.5 / 6.6 / 8.9; 33 counties, 40 outlets; CRV3 p 0.077, 0.90 | Current model; `EXCLUDE` in the newsroom count; CRV3 |
| Spillover | County characteristics column | 15.6 baseline; 15.0; 14.1 | Not rerun; not comparable with the current model | Earlier measure and model |
| Spillover | Springfield comparison | Spillover 41% / 40% (print 26% / 25%); medians 44% / 43%; Webster 68% / 46% | Region held out 24% / 26%; Webster 36% / 23% | Earlier measure |
| All | Selection rule | First review joint test (adopted set beats baseline; each coefficient's interval excludes zero; candidates one at a time) | Selection procedure: core blocks, hypothesis terms, nested guard, one primary metric | User, 2026-10-24 |
| Public | Public, best setting per class, Missouri all | 4.34 (4.30 reviewer rerun), classes 3.99 / 4.06 / 5.56 / 5.48 / 5.08; first review nested 4.85 (4.38 / 4.78 / 6.96 / 5.47 / 5.25), in-sample 4.67 | Nested 4.64 (4.15 / 4.48 / 6.05 / 6.28 / 5.25); in-sample 4.41 | Nested selection; outcome; JT01; all destinations |
| Public | Public reference (start of 2026-10-18) | 5.22 / 4.78 / 6.05 / 6.72; 5.35 | Not rerun | Superseded by per-class settings |
| Public | + segment corrections (C) | 3.73 (3.43 / 3.52 / 3.93 / 6.40 / 3.48); refined 3.63 (regional-hub rings 5.62); first review outer loop 3.97 (3.53 / 3.97 / 4.05 / 6.12 / 4.54), in-sample structure 3.71 | Outer loop 4.07 (3.70 / 3.87 / 4.41 / 5.58 / 5.18); in-sample structure 3.61 | Outer loop; fold base; all destinations |
| Public | + destination factor from public measures (B) | 3.76 (3.50 / 3.51 / 3.86 / 6.67 / 3.30); first review 3.95 (3.58 / 3.99 / 3.88 / 5.65 / 4.52) | 3.96 (3.56 / 3.91 / 3.91 / 5.72 / 4.86) | As above |
| Public | + one factor per destination county (A) | 3.40 (2.94 / 3.07 / 4.44 / 6.33 / 3.52); first review 3.47 (3.10 / 3.52 / 4.31 / 5.91 / 2.35) | 3.46 (3.12 / 3.25 / 4.44 / 6.32 / 2.53) | As above |
| Public | Advan-fitted, Missouri | 3.13 (3.28 / 2.79 / 4.38 / 3.26 / 2.11); first review 3.34 (3.51 / 2.95 / 4.36 / 3.41 / 2.61) on the common set | 3.31 (3.57 / 2.87 / 4.12 / 3.25 / 2.45) on all destinations; 3.38 on the common set | Outcome; JT01; primary metric |
| Public | Gap and share closed | First review: public − Advan +1.50 [+1.02, +2.01] (log-ratio +0.17); C − Advan +0.63; corrected − public −0.88 [−1.26, −0.49]; closed 58% (C), 91% (A) without interval | +1.34 [+0.87, +1.82] (log-ratio +0.23); C − Advan +0.76 [+0.36, +1.16]; C − fold base −0.60 [−0.96, −0.25]; closed 44% [22, 67] (C), 89% [63, 117] (A) | Fold base; intervals; all destinations |
| Public | Log-ratio errors | First review 0.35 / 0.53 / 0.45 / 0.39 | 0.35 / 0.58 / 0.51 / 0.44 | As above |
| Public | Advan share outside the common set | 1.37% (max 8.5%) | 1.34% (max 8.2%) | Outcome |
| Public | "Beats the Advan-fitted model in major-metro rings (3.93 vs 4.38)" | Claim; first review 4.05 vs 4.36 | Deleted: 4.41 vs 4.12, gap +0.28 [−1.57, +2.41], no difference | Never a claim of the study; intervals |
| Public | "With destination factors, beats it in small rural counties (2.94 vs 3.28)" | Claim; first review 3.10 vs 3.51 | Deleted: 3.12 vs 3.57, gap −0.46 [−0.93, −0.03] — model A carries one Advan-learned factor per destination; it is not the public model | Never a claim of the study; intervals |
| Public | Commuter-class instability | First review: major-metro rings nested 6.96 vs in-sample 5.36 (cost 1.60); regional-hub rings outer loop 6.12 vs 4.27 (cost 1.85; Lawrence 1.97 → 8.96, Polk 6.33 → 12.42) | 6.05 vs 5.15; 5.58 vs 4.38; out-of-sample cost 0.23 (Stage 1) and 0.46 (Stage 2) overall | Second-round rerun |
| Public | Stage 1 picks and fold structures | First review: independent towns 23 / 9; major metro `_s_alpha15`; hubs 6 / 3; mode C folds 2, 4, 7 metro-core, 0, 1 pooled hub | Stage 1 table and fold structures (Public-data travel model) | JT01 rebuilds; primary metric |
| Public | 2026-10-18 structure rebuilt (`public_adjusted_pairs_trnear.csv`) | First review segment corrections 3.84 | Public base 4.47, segment corrections 3.71, + per-destination 3.54 | Outcome; JT01 |
| Public | "Destination pull closes 46% of the gap … together 68%" | 5.35 reference, in-sample | Not rerun | `public_gap_corrections.py` unchanged |
| Public | Kansas public, all | 3.74 (3.80 / 3.83 / 4.42 / 3.01 / 2.62); first review 4.29 (4.10 / 4.59 / — / — / 2.94) | 3.78 (3.86 / 3.85 / 2.64 hubs) on all destinations | Primary metric; outcome; JT01 |
| Public | Kansas + Missouri corrections | 3.98 (3.64 / 3.83 / 8.82 / 4.16 / 4.61); first review 4.27 (3.83 / 4.16 / 4.95 hubs) | 4.05 (3.65 / 4.03 / 3.68 hubs) | Structure chosen out of sample for Kansas (destination class × band, 3.62; first review metro-core factor, 3.71) |
| Public | Kansas Advan-fitted | 3.05 (4.12 / 2.74 / 2.84 / 3.09 / 1.55); first review 3.27 (4.15 / 3.06 / 1.78 hubs) | 3.06 (4.12 / 2.76 / 1.55 hubs) | Per-origin maximum; outcome; JT01 |
| Public | Kansas: public "better than the benchmark for small rural counties" (3.80 vs 4.12) | Claim; first review 4.10 vs 4.15 | Deleted: 3.86 vs 4.12, gap −0.26 [−1.15, +0.55], no difference | Never a claim of the study; intervals |
| Public | Kansas gap to the benchmark | 0.69 (Missouri 1.21); first review +1.03 [+0.53, +1.52] (Missouri +1.50) | +0.72 [+0.30, +1.15] all destinations, +1.04 [+0.53, +1.54] common set (Missouri +1.34 [+0.87, +1.82]) | Primary metric |
| Public | Kansas corrections | "Corrections that encode the rural-to-regional-centre relation transfer"; first review corrected − public −0.02 [−0.38, +0.34], log-ratio +0.03 | +0.27 [−0.03, +0.58]; share of the gap closed −37% [−124, 4]: none; log-ratio +0.04 | As above |
| Public | Kansas counties under the corrections | Cowley 10.19 → 5.41, Harper 8.77 → 5.34, Kearny 7.57 → 3.72, Barber 4.70 → 2.29, Greenwood 3.84 → 1.69; Johnson 4.32 → 10.06, Douglas 1.70 → 9.62, Doniphan 1.32 → 7.45; first review Harper 11.50 → 3.23, Cowley 11.74 → 5.87, Barber 5.99 → 2.70, Lane 7.08 → 4.55; Johnson 4.18 → 10.77, Douglas 2.25 → 10.21, Doniphan 1.59 → 6.52 | Cowley 10.01 → 5.04, Kearny 8.07 → 4.86, Kingman 7.19 → 4.55, Lincoln 4.21 → 1.90, Greenwood 3.83 → 1.54; Johnson 4.55 → 9.15, Douglas 1.95 → 8.24, Doniphan 1.28 → 7.89, Morton 2.98 → 6.51 | As above |
| Public | Kansas commuter counties | "Commuter, KC metro (3)", "Wichita ring (1)" 2.84–8.82; first review Butler 2.50 / 5.38 / 7.37, Leavenworth 1.75 / 2.42 / 7.24, Miami 6.42 / 5.72 / 10.98, Wyandotte 0.35 / 1.79 / 6.61 | Butler 3.12 / 6.72 / 8.19, Leavenworth 1.69 / 4.14 / 7.24, Miami 6.30 / 5.91 / 12.47, Wyandotte 0.42 / 0.79 / 4.37 | n < 5; primary metric |
| Public | Kansas Advan share outside the common set | 9.13% | 9.08% | Outcome |
| Public | Corrections applied to Kansas small rural counties only | About 3.69 | Not rerun | — |
| Public | Kansas county classes | 2020 Census population | ACS 2020–2024 B01003; no county moved | One population source in both states |
| Areas | Number of patterns K | K = 6 in every market, chosen on held-out months (2.87 points at K = 1, 2.30 at K = 6, 2.42 at K = 8); same day: paired one-SE rule (K = 5–18; Columbia 11), per-market population and volume (K = 2–5; Columbia 2); first review per town with county-factor residents and the odd fit's order (Columbia 3, Springfield 7, Cape Girardeau 3, Kirksville 3, Joplin 4, Kansas City 3, St. Joseph 3) | Columbia 2, Springfield 7, Cape Girardeau 3, Kirksville 2, Joplin 4, Kansas City 5, St. Joseph 5 | Splits drawn inside the K loop; a market share depends on which home counties form the market; ACS residents; independent halves |
| Areas | Columbia's areas | Two: Columbia I and II (primary 42% on 2026-10-17, then 72% / 16%; 76,912 / 17,513 residents); first review one area, 91%, ~97,020 | One: "Columbia's civic interest area", 93%, 103,086 (ACS) | K rule; ACS residents |
| Areas | Mexico, Linn share of residents | Mexico 79%, then 74% (5,241); Linn 93%, then 92% (1,641); first review Mexico 92% (~6,530), Linn 71% (~1,270) | Mexico 86% (5,685); Linn 85% (1,172) | As above |
| Areas | Area size | Published outline Columbia I 1,158 km², II 4,165, Mexico 1,930, Linn 1,264; first review 1,363 / 1,691 / 1,176 | Core p ≥ 0.5: 1,380 / 1,000 / 1,122 km²; adopted-setting outline 3,607 / 3,660 / 1,292 (hexagons × 5.85 km²) | Probability surface; one area measure |
| Areas | Mexico's Boone hexagons | 99; first review 95 | 34 in the core, 1 at p ≥ 0.8, 114 in the adopted-setting outline | Probability surface |
| Areas | Market test | Mexico-Boone 893 crossing; Columbia-Cole 2,682 (11.6% / 16.3%); Linn-Cole 522; first review Mexico-Boone 1,037, Linn-Cole 319 | Mexico-Boone ~832 (10.0% / 0.5%); Columbia Boone-centred (Boone 45%); Linn-Cole ~289 (8.1% / 0.2%) | K rule; ACS residents |
| Areas | Areas per town | 63; "hubs split (Columbia 42/36/12, Springfield 31/30/18, St. Joseph 26/22/20); isolated towns have one (Linn 93, Belle 95, Cassville 92, Sikeston 78, Neosho 79)"; first review 57, changed for 12 of 36 towns | 58; changed for 7 of 36 (Areas per town table, left of each arrow = K = 6) | K rule |
| Areas | Local index reach, Linn | Rural Osage 0.15 against the pattern's 0.31; Maries 0.02 against 0.11 | Not rerun | K = 6 pattern |
| Areas | Network tie values | Columbia's strongest ties Ashland 0.38 / 0.61, Jefferson City 0.19 / 0.34, Mexico 0.16 / 0.26; weight sensitivity rank correlation 0.988–1.000, at most 25 of 608 hexagons change band; gate: Linn-Columbia shared places 0.32 (0.05 out, 0.02 in), kept Linn-Jefferson City 0.26, Mexico-Columbia 0.12, Columbia-Mexico 0.22; statewide shared coverage 244 of 267 lifted hexagons; Columbia "primary south, secondary north" | Not rerun | K = 6 areas |
| Areas | Display selectivity floors; hexagons shown | Columbia primary 15.9 (239 hexagons), secondary 15.0 (398); first review hexagons beyond home 108 / 123 / 122, share holding 0.95 / 0.98 / 0.75 | Adopted drawing 1,146 / 807 / 754 km², 88–90% of it in the core | Probability surface |
| Areas | Minimum size evidence | 75 markets; Spearman 0.37; median 0.84 under 500 … 0.95 above; Mexico's secondary 729 residents, 389 hexagons, 72% holding; 63 remain; Harrisonville 1 0.44, Grain Valley 1 0.53; Lee's Summit 2 36,956; first review 57 areas, median 0.93, 0.83 / 0.855 / 0.91 / 0.94, Spearman 0.31, Harrisonville 0.35, Grain Valley 0.61, Mexico 0.98 | 58 areas; 0.76 / 0.835 / 0.89 / 0.92 by size; Spearman 0.19; Columbia 0.95 | Independent halves; ACS residents; K rule |
| Areas | Selection-rule sensitivity ("split-half agreement") | Home included, K = 6: 0.896 / 0.880 / 0.941 / 0.734, mean 0.863, "highest mean agreement"; area sensitivity Columbia I 0.77–1.0, Mexico 0.44 / 0.50; first review home excluded 0.76 / 0.75 / 0.58, mean 0.70, IoU 0.53–1.0 / 0.52–1.0 / 0.45–1.0 | Replaced by the ensemble: r(p) 0.99 / 0.96 / 0.86; core Jaccard 0.90 / 0.85 / 0.66; adopted outline 0.85 / 0.74 / 0.55; travel-only sensitivity table | Settings enter the ensemble; "agreement" is replicability, not validity |
| Supply | Coverage density | Columbia II place-specific 24 / 5 / 26 / 45%, with county-level stories 83 / 17 / 0 / 0%; square root for all: Columbia I 58 / 38 / 4 / 0, II 25 / 25 / 50 / 0, Mexico 32 / 15 / 53 / 0, Linn 25 / 54 / 21 / 0; revised: Columbia I 53 / 4 / 43 / 0, II 23 / 4 / 73 / 0, Mexico 30 / 3 / 67 / 0, Linn 22 / 5 / 73 / 0, newsrooms 1 / 1, 2 / 6, 2 / 2, 2 / 2; first review on the network-tie areas: 44 / 8 / 48 / 0 (newsrooms 2 / 1), 32 / 4 / 64 / 0 (2 / 3), 21 / 8 / 71 / 0 (2 / 2), 259 / 311 / 219 hexagons, alpha 1: 44 / 8 / 48, 29 / 7 / 64, 20 / 9 / 71 | QA only, travel-only area: 34 / 9 / 57 / 0, 18 / 5 / 77 / 0, 22 / 9 / 69 / 0; newsrooms not reported | Supply is the next paper's; measured on the travel-only area; county-story weight capped |
| Supply | Balanced diet | Columbia I 51%, 5.0, 3 outlets; II 10%, 1.5, 4; Mexico 14%, 2.2, 3; Linn 14%, 1.7, 2; first review 44%, 4.4, 3; 15%, 2.4, 3; 16%, 1.8, 2; Economic Development 14% of Mexico's | QA only, travel-only area: 22%, 9%, 17%; mean categories and outlets not reported | As above |
| Tie markets | Replicability / accuracy by market | 2026-10-18: Kansas City 1.00 / 0.92, St. Joseph 0.96 / 0.84, Joplin 0.94 / 0.84, Springfield 0.90 / 0.80, Columbia 0.85 / 0.67, Kirksville 0.87 / 0.53, Cape Girardeau 0.86 / 0.36; all 0.91 / 0.70 (travel alone 0.67); same number of markets 53%, within one 97%; first review (before stage 3) 0.98 / 0.93, 0.88 / 0.62, 0.97 / 0.77, 0.935 / 0.575, 0.81 / 0.615 (travel alone 0.49), 0.74 / 0.59, 0.80 / 0.36; all 0.88 / 0.61 | 0.99 / 0.965, 0.88 / 0.63, 0.97 / 0.79, 0.94 / 0.55, 0.82 / 0.625, 0.74 / 0.61, 0.78 / 0.37; all 0.89 / 0.62 (mean 0.614); travel alone and market counts not reported | Scoring change (home masked, beyond the home county); stage-3 tie changes |
| Tie markets | Columbia, Mexico, Linn (town) | 2026-10-18 accuracy 0.69, 0.46, 0.68; first review 0.13, 0.41, 0.82, replicability 0.88, 0.82, 0.88 | Accuracy 0.13, 0.41, 0.75; replicability 0.89, 0.84, 0.89 | Old scoring (Columbia's 0.69 from unmasked home units); stage 3 |
| Tie markets | Population in the within-county spread | Cape Girardeau 0.36 → 0.49, Kirksville 0.53 → 0.62, Columbia 0.67 → 0.69, Springfield 0.80 → 0.74; all 0.70 / 0.687 → 0.70 / 0.707; density thresholds 0.72 / 0.703, 0.71 / 0.706; nonmetro-only rule 0.697 | Adopted setting in the current run (Cape Girardeau 0.37); alternatives not rerun | Old scoring |
| Tie markets | Columbia's eight towns, steps; Vandalia; Mexico with LODES within 45 miles; within-county spread | 0.655 → 0.665 → 0.67; 0.44 → 0.57 (first review 0.55); 0.65; jobs 0.49, OSM 0.50, half each 0.53, exponent 1 0.59, 3 0.37 | Not rerun (Columbia market 0.625; Mexico 0.41) | Old scoring |
