# Civic interest areas

Replication code for "Beyond Counties: Mapping Civic Interest Areas" (Missouri School of Journalism). The analysis
measures where county residents travel, where local news outlets report, and how the two align. The travel, coverage and spillover models
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

`SUPPLEMENT.md` holds the article's supplementary material; its S2 sets out the calculation for each measure: the question it answers, the equation, its
terms with fitted values and its output (`RESULTS.md` names the script that prints each value).

## Results

`RESULTS.md` lists every number, table and figure in the article with the step and script that produce it. The
repository holds only the code those results need. The factors tested and not adopted, which the article's Methods
summarize, are in `analysis/factor_search/` with their own README.

## Requirements

- Python 3.11 with the packages in `requirements.txt`, installed in `.venv/`:
  `python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
- zsh (macOS default) for `scripts/reproduce.sh`; bash for `scripts/public_model.sh`.
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

`scripts/reproduce.sh` rebuilds every result in `RESULTS.md` in dependency order and writes one log per step to
`logs/reproduce/`.

```sh
zsh scripts/reproduce.sh                       # every stage
STAGES="travel coverage" zsh scripts/reproduce.sh
```

| Stage | Steps | Reads |
|---|---|---|
| `data` | Visits by home and destination county, population calibration, distinct residents, pass-through discount, crossover; county covariates, the study counties' block-group flows, boundaries, OpenStreetMap destinations | Advan files, public data |
| `travel` | County classes, gravity model of travel | `data` |
| `coverage` | Coverage model | `travel`, story data |
| `spillover` | Outlet model, outlet type and print outlets, crossover-spillover correlation, county story counts (Table 2) | `data`, story data |
| `factors` | Factors tested and not adopted (`analysis/factor_search/`) | `travel`, `coverage`, `spillover` |
| `public` | Public-data travel model, nested Stage 1 score against the Advan-fitted model (`scripts/public_model.sh`) | `travel`, public data |
| `areas` | Travel patterns, network tie, 6,912-version drawing ensemble, multi-part areas, coverage density and balanced diet with their story-resampling intervals and threshold sensitivity | Advan files, story data |
| `figures` | Figures 1–5 (`flows/print/`) | `spillover`, `areas` |

A full run takes about 6 hours on one processor core per process. The travel patterns and the drawing ensembles take
most of the time. Every random step uses a fixed seed; repeated runs produce identical outputs.

## Repository layout

| Folder | Contents |
|---|---|
| `analysis/` | Data build, travel, coverage, spillover and public-data models, coverage density and balanced diet |
| `analysis/factor_search/` | Factors tested and not adopted |
| `flows/` | Travel patterns, drawing ensemble, area outlines, figure pages |
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
`market_pattern_print.html?town=Columbia&rank=1`.

## Credentials

Scripts that read the story database or call a model application programming interface (API) take credentials from
the environment (`PGPASSWORD`, `OPENROUTER_API_KEY`) or from Google Secret Manager. The repository stores none.
