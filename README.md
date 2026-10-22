# Civic interest areas

Code for the Missouri School of Journalism's analysis of local news crossover,
spillover and civic interest areas in Missouri: where residents travel, where their
local outlets report, and how the two line up.

- **Crossover:** how much of a county's residents' regular life happens in other
  counties.
- **Spillover:** the share of an outlet's stories about other counties.
- **Civic interest area:** the places a town's residents share through their travel,
  strengthened by news ties; **coverage density:** the local news reaching each part of it.

The method's history, every test and every decision is in
[MODEL_CHANGES.md](MODEL_CHANGES.md).

## Data

The repository holds code and documentation only. Data is kept beside it, in the same
folders, and is never committed by default: `.gitignore` is an allowlist of code and
documentation, and `scripts/check_commit.sh` (installed by `make hooks`) refuses any
staged data file not listed in [PUBLIC_DATA.txt](PUBLIC_DATA.txt).

| Data | Committed | Why |
|---|---|---|
| Public data (Census, LODES, County Business Patterns, NHTS, ACS, OpenStreetMap, state revenue) | No; obtained from source | Cited in [CITATIONS.md](CITATIONS.md); small tables built from it may be listed in PUBLIC_DATA.txt |
| Story data from the Local News Impact crawler (outlet, date, place, scope, CIN label) | No, pending a decision | Article text is the publishers' copyright and is never committed |
| Advan Neighborhood Patterns Plus and Weekly Patterns Plus (Dewey Data) | Never | Licensed for academic use; raw data and significant derivatives may not be shared |
| Results derived from Advan at fine grain (hexagon travel values, tract and block-group flows) | No | Treated as licensed data until the licence is confirmed |

Paths are relative to this folder (`root / "analysis/..."`); the data files sit where
the scripts expect them.

## Where things are

| Part | Main scripts |
|---|---|
| Travel from Advan | `analysis/build_statewide_od.py`, `build_calibration.py`, `build_unique_od.py`, `build_tract_od.py`, `build_ks_od.py` |
| Crossover | `analysis/crossover_compare.py`, `residents_leaving.py`, `unique_people_by_county.py` |
| Public-data travel model | `analysis/build_public_geography.py`, `public_work_model.py`, `public_travel_tiers.py`, `assemble_public_by_class.py`, `public_adjusted_model.py`, `score_segments.py`; Kansas transfer: `build_ks_*.py`, `score_ks.py`, `transfer_adjustments.py` |
| Advan-fitted travel model | `analysis/travel_model.py`, `travel_model_dc_test.py`, `travel_county_class_model.py` |
| Spillover | `analysis/spillover_outlets.py` (adopted), `county_collection_quality.py`, `excluded_outlets.py`, `spillover_dma_holdout.py`, `spillover_radius.py` |
| Civic interest areas | `flows/travel_patterns.py`, `flows/market_patterns.py`, `analysis/confidence_layer.py`, `selection_sensitivity.py`; the map page `flows/market_pattern_print.html` |
| Coverage density | `analysis/area_coverage_alignment.py`, `cin_diet.py` |
| For the datadesk builder | `flows/export_area_table.py`, `flows/export_civic_grid.py` |
| Tests of factors, kept and rejected | `analysis/*_test.py`, `combined_*_test.py`, `public_default_sensitivity.py`, `public_gap_*.py` |
| Story exports | `coverage/storymap/export_statewide_2026_03.sh`, `flows/export_march.py`, `coverage/export_coverage_places.py` |

## Running the map pages

`make serve`, then open `http://127.0.0.1:8765/market_pattern_print.html?town=Columbia&rank=2`
(add `&measure=coverage` for coverage density), or `swipe_area_coverage.html`. The pages
use datadesk's CSS and fonts: copy datadesk's `static/css` and `static/fonts` into
`flows/dd/`.

## Credentials

Scripts that read the crawler's database or call a model API take credentials from the
environment (`PGPASSWORD`, `OPENROUTER_API_KEY`) or Secret Manager; none is stored here.
