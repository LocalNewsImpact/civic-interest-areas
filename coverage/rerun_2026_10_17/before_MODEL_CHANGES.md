# Model changes — travel, coverage and spillover

Log of the modelling decisions made on 2026-10-16: what was adopted, what was tested and rejected, and the evidence
for each. Scripts are in `analysis/` unless noted; `make_visuals.sh` rebuilds every figure from the adopted models.

## Data and periods

| Item | Setting |
|---|---|
| Travel | Advan Neighborhood Patterns Plus (Dewey), Missouri destinations, January–September 2026; summed to home county × destination county (`build_statewide_od.py` → `od_mo_2026.csv`) |
| Coverage | Missouri School of Journalism analysis of local news stories, March 2026 (the only month enriched); a story is placed in every county it is centred in or mentions |
| Store-level visits | Advan Weekly Patterns Plus, Missouri, weeks of 2026-03-02 to 03-23 |
| Boundaries | Advan reports 2020 block groups for Jan–Jul and 2010 block groups for Aug–Sep; county codes are the same, and the township maps use one area crosswalk per vintage |

## Measurement corrections

| Change | Why |
|---|---|
| Stories credited to the **Missouri School of Journalism analysis**, never LNIC | Attribution |
| **The Maneater and CoMoBuzz** excluded from Boone's coverage | Decision for these analyses |
| **St. Louis city and county treated as one unit** for spillover | Every St. Louis outlet is registered in St. Louis County, so city stories counted as "another county" (St. Louis print spillover read 85%; merged, 25%) |
| **Other-state counties within 60 miles count as spillover** | Kansas City print outlets read 18% on Missouri counties only and 44% with Kansas; border regions cross the state line |
| **Home county excluded from every travel–coverage comparison** | Residents live in their home county all of the time; a share of visits says nothing about how much it matters to them. Home and away story counts are reported for reference only |
| **Coverage counts a story's central place as well as the places it mentions** | The story map's county layer omits each story's central place; Osage had 13 placed stories on that layer against 40 with both |
| **Hospital indicator removed** | It was a facility count from a CMS file, not travel data, incomplete (it missed Capital Region Medical Center), and read as a healthcare finding the data cannot support |

## Population calibration (adopted)

Advan Neighborhood Patterns Plus is "normalized against panel size and country population" (Dewey's Advan page): a
national scaling, not a local one. Residents seen in their own home block group therefore do not match population.

- Factor (county, month) = residents seen in their own block group ÷ ACS 2020–2024 population. Across Missouri
  county-months: median 1.94, middle 80% 1.09–3.18. Audrain 1.19–2.54, Boone 1.58–2.52, Osage 2.19–4.26.
- Every count of a county's residents that month is divided by its factor before months are added
  (`build_calibration.py` → `calibration_county_month.csv`; `od_mo_2026.csv` keeps raw counts as `visits_recorded`).
  Township shares and alignment data apply the same factors.
- County, not tract: August–September use 2010 block groups, whose tracts differ from the 2020 tracts that carry ACS
  populations.
- Effect: shares within a county barely move (one factor per county-month); the travel model's log-distance term
  changes (−2.14 → −1.58) and it still predicts 93% of July–September shares. Outlet model unchanged (broadcaster 0.70,
  crossover 1.47); coverage's response to travel 0.52.
- Unexplained: the median factor is about 2, not 1, so the over-count is not only local variation around a correct
  national figure. Question for Advan.
- Rule: never pool months or compare absolute counts across areas without this calibration; work with shares within a
  month.

## Device IDs (tested)

`device_id_test.py`: for 424 block groups dominated by one business, monthly distinct devices (Neighborhood Patterns)
against that business's weekly visitors summed over March's four weeks (Weekly Patterns). Monthly can only be lower if
the same devices were recognised in more than one week. It was lower in 71, 62 of them also passing a same-scale check
(monthly at least any single week) — mostly workplaces (auto dealers 39%, printing plants 37%). IDs are therefore
stable at least week to week. Daily resets cannot be tested: no product reports homes by day.

## Travel model

**Adopted: doubly-constrained gravity model, Poisson pseudo-maximum likelihood** (`travel_model.py`, terms in
`gravity_terms.py`).

- A fixed effect for every home county (its total travel) and every destination (its overall draw: capital,
  university, hospitals, shopping — measured from the data, not proxied)
- Pair terms: log distance and its square; both again for nonmetropolitan home counties; log home-county population ×
  log distance (larger counties travel farther); shared border
- Pass-through discount: visits × (1 − max(0, highway-stop share − 12.5%)), where the highway-stop share is the county
  pair's share of store-level visits at gas stations, convenience stores and fast food. Removes 3.0% of out-of-county
  visits.
- Fit: Jan–Sep; checked by fitting Jan–Jun and predicting Jul–Sep shares: **93%**.

Steps that led there (each scored on months the model was not fitted on):

| Version | Lack of fit (deviance) | Predicts Jul–Sep | Each county's top destination, actual ÷ predicted (median) | Script |
|---|---:|---:|---:|---|
| Plain gravity: population + distance | 480M | 76% | — | `travel_model_compare.py` |
| + shared border, rural home, stores (singly constrained) | 359M | 81% | 1.63× | `travel_model_compare.py` |
| + area centre + curved distance | 275M | 86% | 1.42× | `travel_model_hub_test.py` |
| Doubly constrained + curved distance | 165M | 92% | 1.22× | `travel_model_dc_test.py` |
| **+ larger home counties travel farther (adopted)** | **137M** | **93%** | **1.15×** | `travel_model_dc_test.py` |

The singly-constrained model under-predicted every county's main destination by 1.6× — a model fault, not a finding.
That is why the "Osage residents go to Jefferson City twice as often as expected" figure was withdrawn: under the
adopted model it is 1.15–1.2×.

Typical error that remains: across big flows (≥ 5% of a county's out-of-county visits), the middle 80% run from
0.73× to 1.88× of the prediction. County figures are read against that range, not against 1.0×.

### Rejected

| Tested | Result | Why rejected |
|---|---|---|
| Jobs per resident | p = 0.44 once stores are in | Counties with many stores also have many jobs; the two cannot be separated |
| Metro-destination flag | p = 0.27 | Added nothing |
| Hospital indicator | — | See measurement corrections |
| Same metro/micro area | Deviance unchanged | Added nothing |
| Nearest area centre | p = 0.74 | Added nothing |
| Intervening opportunities (population closer than the destination) | Small gain, effect near zero | Not worth the term |
| Destination size × distance | Small gain | Absorbed by origin size × distance |
| Adjacent area centre | Deviance −3M | Negligible |
| Driving time between main towns (OpenStreetMap routes) in place of straight-line distance | Deviance 137M → 136M; Jul–Sep 93.0% → 92.3% | No improvement |
| "On the way" factor (destination lies on the route to a larger centre), simple and weighted | Deviance 134M; no change in prediction | No improvement; highway stops are handled by the pass-through discount instead |
| Area-centre term in the doubly-constrained model | Absorbed by destination fixed effects | Redundant |

The routing (`build_drive_routes.py` → `drive_od.csv`) is kept: it confirms, for example, that Mexico → Columbia
(38 minutes) runs through Callaway County. Half of Audrain residents' Callaway visits are in Kingdom City, but the
pass-through discount only removes 20% of that pair's visits; the rest (Fulton is 22 minutes from Mexico) is ordinary
local travel.

## Coverage model

**Adopted: the same model as travel** — same pair terms, same doubly-constrained fixed effects — fitted to March story-
county pairs from each newsroom county to each other Missouri county (`coverage_model.py`). A second version adds
log(residents' visits ÷ travel-model prediction) to test whether coverage follows travel beyond geography.

- Coverage follows residents' travel, less than proportionally: about 0.7–0.8% more stories per 1% more visits.

### Rejected or not supported

| Tested | Result | Script |
|---|---|---|
| Separate factor lists for travel and coverage | Replaced by one shared term set (`gravity_terms.py`) | — |
| Non-bordering destinations get less coverage than travel predicts | Raw comparison: about half the story share at the same travel; with newsroom-county and destination fixed effects the difference is not detectable (±60% at 95%) | `border_coverage_test.py` |
| **Saturation**: coverage follows travel less to destinations that already have their own coverage | Real and in the predicted direction (rural home × destination's own stories, p = 0.004 all outlets, < 0.001 print), but small: the response falls from 0.67 to 0.50 between no own coverage and 500 own stories. Held-out error 4.15 → 4.12 points. Destination newsroom count and broadcasters add nothing beyond own story volume. Not adopted; the level version (rural newsrooms cover saturated centres less regardless of travel) was tested only within the all-factors model below | `coverage_saturation_test.py` |

## Spillover model (share of an outlet's stories about another county)

**Adopted: outlet-level logistic model** (`spillover_outlets.py`).

- One observation per outlet with ≥ 10 placed stories (128 outlets, 27 broadcasters), each counted once; errors
  clustered by county
- spillover ~ broadcaster + residents' share of visits outside the county
- Broadcaster +0.70 (p < 0.001); residents' travel out +1.47 (p < 0.001)
- A county's expected spillover is its outlets' expectations weighted by their stories

Leave-one-county-out error (predicting a county's outlets from all others):

| Version | Mean absolute error (points) |
|---|---:|
| Broadcaster only | 15.5 |
| **Broadcaster + residents' travel out (adopted)** | **14.5** |
| + population | 14.5 |
| Full: cohort, border, population, travel out | 15.3 |

### Rejected

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
| "Visits × expected" figures from the singly-constrained model (e.g. 2.2×) | Model under-predicted main destinations by 1.6× |
| "Beyond gravity" maps | Category colours carried four model-based outcomes; unreadable as maps. The model comparison is a table (`three_counties_table.csv`) |
| Alignment maps with the home county compared | Replaced by out-of-county comparison with home and away story counts for reference |

## All marginal factors together

Each factor above was first tested alone. To check whether many small effects add up, every factor that showed any
effect was added at once and scored only on data the model was not fitted on
(`combined_marginal_test.py`, `combined_all_factors_test.py`).

| Model | Adopted | + every rejected factor | Every destination factor in place of destination effects |
|---|---|---|---|
| Travel: big flows' share error, Jul–Sep from Jan–Jun | 3.58 points (6 terms) | 3.39 (14 terms) | 4.04 (19 terms) |
| Travel: Jul–Sep shares explained | 93.1% | 93.6% | 90.4% |
| Travel: big flows within ±25% | 49% | 49% | 42% |
| Coverage, all outlets: held-out county error | 4.15 points | 4.14 (23 terms, incl. saturation level) | 4.18 (31 terms) |
| Coverage, print and digital | 4.50 | 4.58 | 4.52 |
| Spillover, outlets: held-out county error | 14.5 points | 14.9; 14.2 with ridge 0.05; 14.5 with ridge 0.2 | — |

- The marginal factors do not add up for coverage: held-out error is unchanged or worse, while in-sample fit improves
  (over-fitting).
- Travel gains about 5% on big flows' share error with all eight rejected pair terms together; the share of big flows
  within ±25% does not move.
- Stores, jobs, metro and area centre cannot replace each destination's measured draw: the model without destination
  effects is worse for travel (90.4% against 93.1%) and no better for coverage.
- Spillover: every county factor with light shrinkage (ridge 0.05) is 0.3 points better than the adopted model;
  without shrinkage it is 0.4 points worse, and with stronger shrinkage the same. The gain depends on the amount of
  shrinkage chosen, and no run measured how much held-out error varies, so it is not adopted.

## Crossover: distinct people (adopted)

Crossover in the spillover model is now the share of a county's residents observed outside it in a month, counted as
distinct people (`build_unique_od.py`, `crossover_compare.py`). Advan reports distinct people per destination block
group by home block group; people from different home block groups are distinct, and for each home block group the
people seen in its single most-visited outside block group are all distinct. Summing those over the county's block
groups gives a lower bound on residents who left, capped at the residents seen at home in each block group. Averaged
January–September 2026; March matches the three-county check (Audrain 42%, Boone 29%, Osage 44%).

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

## Spillover model, current (adopted 2026-10-17)

**Measure.** Spillover is the weighted share of an outlet's stories about another county (another Missouri county, or
an other-state county within 60 miles). A story centred in another county counts 1; a story centred at home that
mentions another county counts 0.5; a story about home only counts 0. The weight is a definition, set by the authors:
a mention is half a story about that county. It is not fitted, because changing it changes the outcome itself.

The earlier measure counted any story that touched another county, so a passing mention counted the same as a story
about that county. Under it a small-town weekly and a regional TV station looked alike (print median 40%, broadcast
45%); by central county they differ (6% and 25%). The Mexico Ledger had 8 of 90 stories centred in another county and
43 that only mention one; KOMU had 83 of 263 and 36.

**Model.** spillover ~ broadcaster + weekly in a county that also has a daily and a TV station + miles from the
outlet's town to its county edge (log) + print and digital outlets active in the county (log of 1 + count) (outlet
level, `spillover_outlets.py`). Each outlet's expectation comes from its own profile; a county's is its outlets' expectations
weighted by stories. The nine such counties, from active outlets in the registry: Adair, Boone, Buchanan, Callaway, Cape
Girardeau, Greene, Jackson, Jasper, St. Louis. Their weeklies' median spillover is 11%, against 24% for the other
weeklies.

Fitted on 83 well-collected outlets (43 counties), then applied to all 128. Well collected: March local news with body
text ≥ 95%, full length (600+ characters) ≥ 80%, placed by enrichment ≥ 60%. Three well-collected outlets are left out
of the fit at the authors' direction: the Greene County Commonwealth is published in Lawrence County but covers Greene
(20 of 23 stories centred there); the Mid Rivers Newsmagazine is published in St. Louis County but covers St. Charles
(19 of 26); Three Rivers Publishing carries three newspapers under one name. ROT47 ciphertext was tested as a quality
criterion and withdrawn: place enrichment read `raw`, which holds the decoded body for the six affected outlets.

| Term | Coefficient | p | Meaning |
|---|---:|---:|---|
| Broadcaster | +0.71 | < 0.001 | TV and radio cover beyond their county more |
| Weekly in a county with a daily and a TV station | −0.37 | 0.05 | Where a county already has a daily and a TV station, its weeklies keep to the home county |
| Miles from the town to the county edge (log) | −0.17 | 0.001 | Outlets near a county line cover across it more |
| Print outlets in the county (log of 1 + count) | −0.41 | 0.01 | Saturation: the more print outlets a county has, the less each covers beyond it |

Chosen on held-out error (each county's outlets predicted from the others):

| Model | Mean miss (points) | Median miss | Terms |
|---|---:|---:|---:|
| + border distance + print outlets in county (adopted) | 8.62 | 7.20 | 4 |
| Same search, terms chosen without the held-out county (nested) | 9.18 | 7.81 | — |
| Broadcaster + weekly in a daily-and-TV county | 9.39 | 7.05 | 2 |
| Broadcaster + town population + weekly in a daily-and-TV county | 9.45 | 8.24 | 3 |
| Broadcaster + population of the outlet's town (adopted earlier the same day) | 9.79 | 8.64 | 2 |

The border and saturation terms were found by trying 11 additions (`spillover_saturation_test.py`): outlets, print
outlets, TV stations and outlets per 10,000 residents in the county; miles to the county edge; miles to a town of
25,000+ in another county; each also as a daily-only term, which changed nothing (16 dailies). Because the pair was
chosen on the error it is scored on, the nested figure is the honest one: a 0.2-point gain in the mean, a 0.8-point
loss in the median, and the same pair chosen in 38 of 43 folds. It gives dailies their own expectations: the
Columbia dailies move from 28% to 19% (actual 17% and 12%).

Held-out region test (2026-10-17): refitted without any outlet in Greene, Webster or Barry counties (75 outlets),
then used to predict the region's 10 outlets. Mean miss: adopted 10.9 points; broadcaster + crowded weekly 11.7;
broadcaster + town population 11.9. Region total 28% actual, 29% expected (34% and 33% under the two smaller
models). Webster is the largest miss (44% actual, 26% expected), as before. Chart:
`flows/print/outlet_spillover_springfield_2026_03.png`, with these held-out expectations.

The two terms apply to every outlet, weeklies included. By outlet type, held-out mean miss (points), previous model →
adopted: broadcasters 10.03 → 7.86, dailies 9.07 → 8.10, weeklies 8.71 → 8.64, other print 11.24 → 11.71. Applying
the terms to non-weeklies only makes every group worse (all 9.40; weeklies 9.29, dailies 10.06) and neither term stays
significant (border p = 0.31, saturation p = 0.12), so the shared form is kept. The cost falls on single weeklies at
an extreme: the Vandalia Leader, under a mile from the county line, moves from 28% to 34% expected (actual 6%, a lower
bound: 5% of its stories are full length).

Tested, not adopted (`spillover_market_test.py`): whether other outlets in the same county sit nearer the county line,
or nearer the neighbouring county the outlet is closest to (registry towns; outlets within a mile of each other's
distance counted as tied, so outlets in one town are not ranked by address). Added to the adopted model none is
significant (any line: +0.14, p = 0.35; same neighbour, count: −0.02, p = 0.82; same neighbour, any: −0.19, p = 0.24)
and none lowers both mean and median miss. In place of border distance each loses the border gain (mean 9.3 against
8.6): the distance itself carries the effect, not the outlet's position among its county's outlets.

Fitted on all 128 outlets before the quality restriction: broadcaster only 11.5; broadcaster + town population 11.1;
the previous model (broadcaster + county urban share + concentration) 11.2. That model gave every print outlet in a
county the same expectation from county terms (Vandalia Leader and Mexico Ledger both 41%). Also tested on the
outlet's profile, no gain (`spillover_profile.py`): weekly vs daily alone, miles to the county edge, miles to a town of
25,000+ in another county, local story volume, and the county terms added back.

Mention weight, under broadcaster + town population fitted on all 128 outlets:

| Mention weight | 0.1 | 0.25 | 0.5 | 0.75 | 1.0 |
|---|---:|---:|---:|---:|---:|
| Boone County Journal, actual / expected | 2% / 14% | 5% / 19% | 10% / 28% | 16% / 36% | 21% / 45% |
| Vandalia Leader | 1% / 15% | 3% / 20% | 6% / 29% | 9% / 38% | 12% / 47% |
| The Mexico Ledger | 14% / 13% | 21% / 18% | 33% / 25% | 45% / 33% | 57% / 41% |

Three small-town weeklies (Boone County Journal, Centralia Fireside Guard, Vandalia Leader) were over-predicted at
every weight under the town-population model. The Vandalia Leader and Centralia Fireside Guard are not well collected
(5% and 0% of stories at full length), so their actual spillover is a lower bound. The Boone County Journal is well
collected (its stored `text` is partly ROT47, but enrichment read the decoded body), so its 10% stands. Under the
adopted model the Boone County Journal is expected at 15% and the Centralia Fireside Guard at 17% (actual 10%),
and the Vandalia Leader at 34% (actual 6%; its town is under a mile from the county line). Statewide, well-collected weeklies with 20+ placed
stories spill over 23–25% (30 weeklies), against 24% for all 60, so the other weeklies' data is not what separates them.

Tests of county characteristics below that used the spillover model were run on the earlier measure and model.

### Previous (2026-10-16, replaced)

spillover ~ broadcaster + urban share + concentration (outlet level, `spillover_outlets.py`):

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

Across the 68 counties with newsrooms, the share of residents seen outside the county and the share of print and
digital stories about another county: r = 0.10 (p = 0.43); holding urban share fixed 0.08. Among well-collected
outlets only (95%+ stories with text, 80%+ full length, 60%+ placed; 44 counties): r = 0.30 (p = 0.05) — poor
collection adds noise that hides a modest positive relationship (`collection_quality_robustness.py`).

## Collection quality (sensitivity)

Refitting on well-collected outlets and counties (`collection_quality_robustness.py`): coverage's response to travel
0.52 → 0.48 (all), 0.50 → 0.42 (print); the spillover model's broadcaster and urban-share effects hold (urban share
−1.09 on well-collected outlets), and its held-out error falls (15.0 → 14.1). Counties with every known newsroom
collected and high-quality text (28 counties) leave too few outlets (36) to estimate the model alone.

## Springfield comparison

Greene (hub), Webster (Springfield metro) and Barry (rural) against Boone, Osage and Audrain
(`springfield_vs_columbia.py`). The hubs match each other: crossover 24% and 34%, spillover 41% and 40% (print 26%
and 25%), both below the Missouri medians (52%; 44%, print 43%). Predicted with each county left out, the adopted model
is within 6 points for both hubs and Osage; Webster is the largest miss (actual 68%, predicted 46%, 31 stories). Webster
→ Greene travel is predicted almost exactly by the travel model (0.96×): Greene has the strongest overall draw in
Missouri, is 23 miles away, shares a border, and half of Webster's employed residents work there.

## County characteristics tested

All scored out of sample (leave one county out; travel: fit January–June, score July–September).

| Source | Crossover (12.9 points baseline) | Spillover (15.6) | Travel (big-flow error 3.51) | Coverage (4.00) |
|---|---|---|---|---|
| ACS 2020–2024 (24 measures, `civic_variables_test.py`) | Commute time, race, 65+: 12.0 | Foreign-born 14.7 (urban proxy) | Degree × distance 3.43 | — |
| Civic Information Index 2026 (`civic_index_test.py`, `civic_index_test_v2.py`) | Environmental resilience alone 12.2; census response rate alone 12.3* | Against the adopted model (15.0): rent share of income alone 14.6 (urban proxy); several indicators chosen without seeing the held-out county 15.3 (worse) | — | — |
| Newsroom bylines and volume, March 2026 (`spillover_bylines_test.py`) | — | Print outlets (101), against the earlier travel-out model (16.1): distinct bylines 16.3 (p = 0.95), local stories 16.2 (p = 0.38), stories per byline 16.2; no gain, and none on the 68 outlets with half or more stories bylined | — | — |
| Census Business Dynamics Statistics, 2021–2023 average (`business_dynamics_test.py`) | Openings per 100 establishments 12.2 (+0.16, p = 0.03); turnover (openings + closings) 12.2 (p = 0.004); net openings 13.2 (no gain) | Against the adopted model (15.0): closings 14.8 (p = 0.07); well collected (14.1): turnover 13.9 (p = 0.16); no consistent gain | — | — |
| Hospitals (`hospital_test.py`) | Has a hospital: 12.2 (−0.54, p = 0.006) | 15.7 (no gain) | 3.48 (no gain) | 4.01 (no gain) |
| Hub dominance (concentration of travel) | — | 15.0 (all), 14.1 (well collected); adopted | not needed (destination draw measured) | — |

\* Single indicators, each scored with the county left out. Combinations chosen by searching against the same error
are not reported. The index's journalists per 100,000 (MuckRack) is not used: newsroom staffing is measured directly
from bylines in the stories collected, and adds nothing to spillover (row above). Indicators that do not vary
across Missouri counties were excluded (the volunteer rate is one state figure, 29.8%, for every county; library visits
and mental-health providers are missing for some counties). An earlier run kept the volunteer rate: merging St. Louis
city and county left a rounding difference that standardizing turned into a variable singling out St. Louis, and its
apparent effect (spillover 13.4 points with four indicators) was an artifact. With it removed and selection made
without seeing the held-out county, adding several indicators makes spillover predictions worse (15.3 against 15.0 for
all outlets; 15.4 against 14.1 for well-collected outlets).

Hospitals: CMS Hospital General Information, general acute, critical access, children's, VA and DoD hospitals (no
psychiatric hospitals, no clinics), with Capital Region Medical Center added (it reports under MU Health Care's CMS
number since 2024): 107 hospitals in 67 counties (`build_hospitals.py`). Counties without a hospital have more
residents leaving; hospitals do not affect where residents go or what newsrooms cover once each county's overall draw
is measured. To confirm: Cooper County Memorial Hospital (Boonville) and Southeast Health Center of Ripley County
(Doniphan) appear in OpenStreetMap but not in CMS.

## Open

- One month of coverage limits every story-count comparison; counts per county pair are small.
- The level version of saturation (rural home × destination's own stories) was tested only within the
  all-factors model; it was not tested alone.
- Out-of-state travel is not observed (Missouri destinations only).
- Spillover: the Centralia Fireside Guard and Vandalia Leader have no usable spillover figure (short texts).

## Sources

- U.S. Census Bureau. (2025). *Annual estimates of the resident population for incorporated places and minor civil divisions in Missouri: April 1, 2020 to July 1, 2024* (SUB-EST2024_29) [Data set]. https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/cities/totals/sub-est2024_29.csv

- U.S. Census Bureau. (2025). *Business Dynamics Statistics: 2023 release, establishment characteristics by state and county* [Data set]. https://www2.census.gov/programs-surveys/bds/tables/time-series/2023/bds2023_st_cty.csv

- Advan Research. (2026). *Foot Traffic / Neighborhood Patterns Plus* [Data set]. Dewey Data. January–September 2026,
  Missouri. [DOI to add from the Dewey dataset page.]
- Advan Research. (2025). *Foot Traffic / Weekly Patterns Plus* [Data set]. Dewey Data.
  https://doi.org/10.82551/C103-N851. Weeks of March 2–30, 2026, Missouri.
- Missouri School of Journalism. (2026). Analysis of local news stories, March 2026: stories and their places from the
  Missouri School of Journalism local news collection.
- U.S. Census Bureau. (2025). *American Community Survey 2020–2024 5-year estimates*, county population and 24
  demographic measures.
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
- Software: Python, statsmodels, pandas, shapely, SciPy, pyosmium; D3 for figures.
