# Civic interest areas

Code for the Missouri School of Journalism analysis of local news in Missouri. The analysis measures where county
residents travel, where local news outlets report, and how the two align. The travel, coverage and spillover models
are fitted on all Missouri counties; results are reported for Audrain, Boone and Osage counties. Civic interest areas
cover the Columbia–Jefferson City television market. Results cover January–September 2026 for travel and March 2026
for news stories.

## Measures

| Measure | Definition | Main script |
|---|---|---|
| Travel | Expected visits by residents of one county to another, from a doubly constrained gravity model | `analysis/travel_model.py` |
| Crossover | Share of a county's residents seen outside the county in a month | `analysis/crossover_compare.py` |
| Coverage | Expected stories by one county's newsrooms about another county, given travel between them | `analysis/coverage_model.py` |
| Spillover | Share of an outlet's stories about counties other than its own | `analysis/spillover_outlets.py` |
| Civic interest area | Places a town's residents share through travel, strengthened by news ties; each place shaded by how likely it is to be part of the area | `flows/area_ensemble.py`, `flows/area_core.py` |

`flows/model_diagram_print.html` renders the calculation for each measure: the question it answers, the equation,
the inputs and the output.

## Method record

`MODEL_CHANGES.md` records the method. The section "Current results" lists every figure with the script that
prints it. The remaining sections record the selection procedure, every specification tested, every sensitivity
analysis and every figure that a later version replaced (appendix "Superseded figures").

## Requirements

- Python 3.11 with the packages in `requirements.txt`, installed in `.venv/`:
  `python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
- zsh (macOS default) for `scripts/reproduce.sh` and `make_visuals.sh`; bash for `scripts/public_model.sh`.
- Google Chrome for the figures (path set by the `CHROME` environment variable).
- The datadesk style sheets and fonts in `flows/dd/` for the map pages (copied from datadesk's `static/css` and
  `static/fonts`; not in this repository).

## Inputs

The repository does not contain these inputs, apart from the story data for three counties and the pinned outlet
registry checksums. Each input is obtained from its source and placed in the folder the scripts read. `.gitignore`
excludes every one of these folders' data files.

| Input | Place in folder (not committed) | Source |
|---|---|---|
| Advan Neighborhood Patterns Plus, Missouri destinations and Kansas destinations of Missouri residents, January–September 2026 | `neighborhood/raw/`, `neighborhood/raw_ks/` | Dewey Data, academic licence |
| Advan Weekly Patterns Plus, Missouri, March 2026 | `weekly/raw/` | Dewey Data, academic licence |
| Census boundary, population, American Community Survey (ACS), County Business Patterns, Business Dynamics Statistics and National Household Travel Survey (NHTS) files; state taxable sales | `census_dl/` | Public; cited in `CITATIONS.md` |
| LEHD Origin-Destination Employment Statistics (LODES), 2023 | `free/` | Public; cited in `CITATIONS.md` |
| OpenStreetMap extract, Missouri | `osm/` | Geofabrik |
| Outlet registry and television market assignments | `data/registry/` | Missouri School of Journalism outlet registry; checksums committed in `data/registry/README.md` |
| News stories and their places, March 2026 | `coverage/`, `flows/reach/` | Missouri School of Journalism local news database; exported by `coverage/storymap/export_statewide_2026_03.sh` and `coverage/export_source_quality.sh` (database credentials required) |
| Story data, Audrain, Boone and Osage counties | `data/stories/` (committed) | Missouri School of Journalism (CC BY 4.0); described in `data/stories/README.md` |

## Reproducing the results

`scripts/reproduce.sh` rebuilds every result in "Current results" in dependency order and writes one log per step to
`logs/reproduce/`.

```sh
zsh scripts/reproduce.sh                       # every stage
STAGES="travel coverage" zsh scripts/reproduce.sh
```

| Stage | Steps | Reads |
|---|---|---|
| `data` | Visits by home and destination county, population calibration, distinct residents, pass-through discount, crossover | Advan files, ACS population |
| `travel` | Gravity model, block tests, nested test of exploratory terms | `data` |
| `coverage` | Coverage model, saturation test, border test | `travel`, story data |
| `spillover` | Outlet model, nested selection, television-market and regional holdouts, collection-quality subsets | `data`, story data |
| `public` | Public-data travel model and its Advan-learned corrections (`scripts/public_model.sh`) | `travel`, public data |
| `areas` | Travel patterns, network tie, 1,728-version drawing ensemble, multi-part areas, tie-market accuracy | Advan files, story data, `public` |
| `qa` | Coverage density and balanced diet on the travel-only footprint (diagnostics for later work) | `areas` |
| `figures` | Area table, calculation diagram, area maps for Columbia, Mexico and Linn (`flows/print/`) | `areas` |

A full run takes about 6 hours on one processor core per process. The travel patterns and the drawing ensembles take
most of the time. Every random step uses a fixed seed; repeated runs produce identical outputs.

`make_visuals.sh` rebuilds the county-level figures: travel maps, alignment maps and outlet spillover charts.

## Repository layout

| Folder | Contents |
|---|---|
| `analysis/` | Data build, travel, coverage, spillover and public-data models, tests of candidate terms, tie markets |
| `flows/` | Travel patterns, network tie, drawing ensemble, area outlines, map pages and figure exports |
| `coverage/` | Story exports and collection-quality tables |
| `scripts/` | `reproduce.sh`, `public_model.sh`, and the pre-commit data guard `check_commit.sh` |
| `data/` | Committed story data and the pinned outlet registry |

## Data and licences

`.gitignore` admits code and documentation only. `scripts/check_commit.sh` (installed by `make hooks`) refuses any
staged data file not listed in `PUBLIC_DATA.txt` and any file over 1 MB.

| Data | Committed | Reason |
|---|---|---|
| Story data, Audrain, Boone and Osage outlets, March 2026 (outlet, date, URL, place, scope, civic information category) | Yes | Headlines and article text remain their publishers' copyright and are omitted |
| Advan Neighborhood Patterns Plus and Weekly Patterns Plus | No | The academic licence prohibits redistribution of the data and of significant derivatives |
| Results derived from Advan at fine grain (hexagon values, tract and block-group flows) | No | Treated as licensed data |
| Public data | No | Available from each source cited in `CITATIONS.md` |

Code: MIT (`LICENSE`). Data created by the project: CC BY 4.0 (`LICENSE-DATA.md`).

## Map pages

`make serve` serves the map pages at `http://127.0.0.1:8765`. The civic interest area map for a town:
`market_pattern_print.html?town=Columbia&rank=1`. The calculation diagram: `model_diagram_print.html`.

## Credentials

Scripts that read the story database or call a model application programming interface (API) take credentials from
the environment (`PGPASSWORD`, `OPENROUTER_API_KEY`) or from Google Secret Manager. The repository stores none.
