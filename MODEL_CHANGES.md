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
| Competing destinations (2026-10-18, `travel_competing_test.py`): nearest comparable alternative (log distance to the nearest destination with as many places ÷ distance to this one), the same counted only in other directions (60°+ off the bearing), and Fotheringham's C_ij = Σ(k≠i,j) W_k/d_jk (Haynes & Fotheringham 1985) | Alternatives: −0.05 and 0.00, deviance 80.0M → 79.5M / 80.0M. Fotheringham: −0.83 (p < 0.001), deviance 80.0M → 78.9M, but July–September 92.9% unchanged and large pairs within 0.8–1.25× 46% → 44% | The destination fixed effects already measure each centre's draw; competition shows in the fit, not in prediction. Osage → Cole 1.28× → 1.21× |

The routing (`build_drive_routes.py` → `drive_od.csv`) is kept: it confirms, for example, that Mexico → Columbia
(38 minutes) runs through Callaway County. Half of Audrain residents' Callaway visits are in Kingdom City, but the
pass-through discount only removes 20% of that pair's visits; the rest (Fulton is 22 minutes from Mexico) is ordinary
local travel.

### Small counties and pair-level commuting (2026-10-18)

The pooled travel model fits large counties best: Poisson weights by count, so big flows drive the fit. Tested for the
counties it serves worst, each county held out and predicted from all others (8 folds), public data only:
county tiers by k-means on log population (ACS 2020-2024) and commuting outflow (LODES 2023): small rural (56 counties,
median 10,600, 67% commute out), independent towns (32), commuter counties (18), regional hubs (8;
`analysis/county_class_k4.csv`).

| Tested (small rural counties held out, share error / top-3 error) | Result |
|---|---|
| Separate model for small origins; tier-specific distance decay | No gain except hubs (2.02 -> 1.77), and other tiers worse |
| Tier-specific and county-by-county pull of destination jobs and retail (LODES; County Business Patterns 2022) | 3.75 -> 3.70 / 4.79 -> 4.68: jobs pull hardest for small rural origins (1.60 vs hubs 1.39); retail adds nothing once jobs are in |
| Distance to the destination's job hub from where residents live (mean, median), nearest and farthest county edge | All worse (3.93-4.60): the population-centre distance already measures from where people live, and visits go anywhere in the destination county |
| Competing destinations (Fotheringham) | See above: no gain in prediction |
| **Commuting between the two specific counties (LODES 2023), out and in** | **3.76 -> 3.28 / 4.81 -> 4.25 (-13%); independent towns 3.05 -> 2.79; commuter counties 4.13 -> 3.82; hubs 2.43 -> 2.11** |

Pair-level commuting is the first public measure that predicts a county's travel markedly better without its own travel
data. **ADOPTED 2026-10-18** in the shared gravity terms (`gravity_terms.py`), so the travel and coverage models both
carry it. Travel model, all months: commute out +0.28, commute in +0.19 (both p < 0.001); July-September predicted
94% (93% before). Coverage model: commute in +0.51 (p < 0.001), commute out +0.04 (n.s.) -- newsrooms cover the
counties whose workers commute into theirs; travel beyond expected falls from 0.52 to 0.36 (twice the expected travel
-> about 1.3 times the stories, from 1.4), part of it now carried by commuting. Actual / expected for the study counties'
main destinations: Osage -> Cole 1.28 -> 1.09, Osage -> Boone 1.30 -> 1.64, Audrain -> Boone 0.99 -> 0.97, Audrain ->
Callaway 1.68 -> 1.39, Audrain -> Marion 1.83 -> 2.40, Boone -> Cole 0.73 -> 0.70, Boone -> St. Louis 1.47 -> 1.33.
Commuting explains Osage's travel to Jefferson City; travel to Columbia, where few Osage residents work, is for shopping,
health care and the university and now stands out more. Spillover is unchanged (it does not use the travel model).

### Public-data travel model (Stage 1) and Advan-learned corrections (Stage 2), 2026-10-18

Aim: a travel model built from public data only, then refined with Advan, the gain reported. All scores are the
share-weighted absolute error (points) of each home county's out-of-county Missouri destination shares against Advan,
January-September 2026; the Advan-fitted model (above) is scored with each county held out (8 folds), and every
Advan-learned correction below is learned on the other counties and applied to the held-out one. Classes: the k-means
tiers above; commuter counties split by the OMB 2023 delineation into rings of the Kansas City and St. Louis metros (9)
and rings of regional hubs or outside any metro (9).

**Public model** (`public_work_model.py`, `public_travel_tiers.py`, `assemble_public_by_class.py`), tract origins
(CenPop2020 tract centres), destinations every county within 200 miles in Missouri and the eight neighbouring states:

| Part | Public data and calculation |
|---|---|
| Work | LODES 2023 tract -> county, Missouri main OD plus the IL, KS, IA, AR, OK, NE, TN, KY auxiliary files (33,990 Missouri residents work in Illinois); observed flows within 90 miles, a gravity fit (conditional Poisson on distance, CBP employment, population, state line) beyond, where LODES carries employers' imputed establishment assignments |
| Retail | Trade area analysis: 2025 Missouri DOR taxable sales by county; pull factor; income-adjusted trade area capture (ACS per-capita income); leakage = 1 - capture; Huff allocation on taxable sales (hubs: on sales beyond the county's own expected, Reilly's exponent 2) |
| Chained errands | Errand trips starting at work (2022 NHTS, WHYFROM 3-5): 1.3 (urban) and 2.0 (rural) a month per worker, sent to the work counties |
| Medical, specialty | CBP 2022 health care; furniture, electronics, clothing, sporting goods, department stores (central place: higher-order goods) |
| Recreation, visiting | 2022 NHTS long-distance file (vacation; visiting family or friends), weighted by days away; draws CBP arts and recreation employment, 2020 population |
| Decay | Calibrated to the NHTS trip-length distribution (maximum likelihood over distance bands), rural and urban households |

Each class takes its best public setting (no Advan in any parameter; Advan scores the choice):

| Class | Setting |
|---|---|
| Small rural; regional-hub rings | observed LODES within 90 mi, 40 work days a month per out-of-county commuter, chained errands, Huff on sales |
| Independent towns | the same with decay 6 for retail, medical and specialty |
| Major-metro rings | gravity work part, 20 work days, chained errands |
| Hubs | observed LODES within 90 mi, 20 work days, Huff on surplus sales |

Defaults tested one at a time (`public_default_sensitivity.py`): work-from-home (ACS B08006), circuity 1.0/1.4,
shopping rate x0.5, medical and specialty x0.5/x2, long-distance trips not days -- each within +/-0.15 to 0.40 of the
reference; the weight on commuting moved most (more work days better up to 40 in three classes). Rejected: the
visitation law's exponent 2 for every kind (small rural +1.38; rural decay is steeper, about 4-6), Huff attraction
exponent 0.5 (+0.42), establishment counts and employment as the shopping draw (zero weight once taxable sales are in),
non-work decay by income, degree or tenure (-0.17 to -0.18, kept out for the survey's thin subgroups), metro-size
survey classes (+0.52).

**Where the gap to the Advan-fitted model is** (`public_gap_diagnosis.py`, `public_gap_corrections.py`): one Advan
correction at a time on the public reference (5.35): destination pull closes 46% of the gap, the shape of distance
decay 21%, adjacency 12%, together 68%. The public model overstates the metro cores (St. Louis City 0.23x, St. Louis
County 0.50x, Jackson 0.65x) and understates regional centres and small rural destinations (Greene 1.42x; Knox,
Scotland, Schuyler, Shannon 2.2-3.0x); its single power law sends twice too much to the nearest counties and, for
hubs, half the travel beyond 120 miles.

**Advan-learned corrections** (`public_adjusted_model.py`, applied to tract shares and rolled up; factors in
`public_adjustments.csv`): multiplicative factors, fitted in turn and iterated, for distance band by class (learned
apart for each home county's dominant and secondary LODES commuting counties), adjacency by class, LODES commuting rank
by class, destination order by class, destination class by class. Destination order follows the central place
hierarchy from public data: metro core (largest taxable sales: St. Louis County, Jackson, St. Charles); rest of the
Kansas City and St. Louis metros; regional centre (pull factor >= 1.1, sales > $1 billion); sub-regional town (pull
factor >= 1); resort (marinas and RV parks and recreational camps per resident, top decile: Barry, Benton, Camden,
Crawford, Hickory, Iron, McDonald, Miller, Ozark, Reynolds, Stone, Taney); local.

| Model | Small rural | Indep. towns | Commuter: major metro | Commuter: regional hub | Hubs | All |
|---|---:|---:|---:|---:|---:|---:|
| Public reference (start of the day) | 5.22 | 4.78 | 6.05 (both kinds) | — | 6.72 | 5.35 |
| **Public, best setting per class** | 3.99 | 4.06 | 5.56 | 5.48 | 5.08 | **4.34** |
| + segment corrections (transferable) | 3.43 | 3.52 | 3.93 | 6.40 | 3.48 | **3.73** |
| + corrections, destination factor from public measures | 3.50 | 3.51 | 3.86 | 6.67 | 3.30 | 3.76 |
| + corrections + one factor per destination county (Missouri only) | 2.94 | 3.07 | 4.44 | 6.33 | 3.52 | **3.40** |
| Advan-fitted | 3.28 | 2.79 | 4.38 | 3.26 | 2.11 | 3.13 |

With the segment corrections the public model beats the Advan-fitted model in major-metro rings (3.93 vs 4.38) and,
with destination factors, in small rural counties (2.94 vs 3.28). Destination-order factors (Advan / public): metro
core 0.65-0.99, regional centre 1.35-1.51, sub-regional town 1.09-1.42, local 0.88-0.98, resort 0.84-1.11 -- the
public model's draw is too steep in size and too flat in the hierarchy.

**Commuter counties.** One class held two behaviours. Major-metro rings spread travel over several metro counties and
commute to the core while visiting the nearest large county (St. Charles -> St. Louis County: LODES 75%, Advan 57%;
Warren -> St. Charles 34% vs 47%). Regional-hub rings send 65-73% to one hub (Polk, Newton, Christian). Split, the
metro rings are solved; the regional-hub rings are best on their public base (5.48): every correction learned from
other classes or from their own nine counties makes them worse (6.2-6.7), because the near-hub relation (Jasper is 14
miles from Newton) is learned elsewhere as an overstated small neighbour. Population is not the cause (under 50k 4.37,
over 100k 4.09; the 50-100k group is worst only because Newton, Pulaski, Johnson and Christian fall in it).

**Refinements, same day** (`public_adjusted_model.py`, scored with `score_segments.py`):

| Change | Small rural | Indep. towns | Commuter: major metro | Commuter: regional hub | Hubs | All |
|---|---:|---:|---:|---:|---:|---:|
| Segment corrections as above | 3.43 | 3.52 | 3.93 | 6.40 | 3.48 | 3.73 |
| Regional centre at pull factor >= 1.0 (was 1.1): Jasper's pull factor is 1.08 because its own metro includes Newton | 3.41 | 3.51 | 3.94 | 6.12 | 3.48 | 3.69 |
| + a metro core within 50 miles of home is its own order (cores pull their ring; overstated for distant homes) | 3.35 | 3.43 | 3.88 | 5.81 | 3.68 | 3.63 |
| **Transferable definitions + near core (adopted)** | 3.40 | 3.46 | 3.81 | 5.62 | 3.49 | **3.63** |

Transferable definitions (`TRANSFER=1`), so the corrections can be applied in another state: metro core = central
county of a metro area of 1,000,000 or more (OMB 2023; Census 2024 CBSA population); rest of such a metro = its outlying
counties; regional centre = pull factor >= 1 and at least 60,000 trade-area customers (taxable sales / the state's
per-capita taxable sales -- about $1 billion in Missouri); resort = marinas plus RV parks and recreational camps per
resident in the top tenth of all U.S. counties (CBP 2022). Pull factor, trade area capture and miles are already
relative or universal. Home classes for another state: nearest Missouri cluster centre on log population and commuting
outflow. The factors themselves are Missouri estimates; the transfer test is to fit in Missouri and score in a state
with Advan data (Illinois is obtainable).

Regional-hub rings, county by county: Newton (Jasper labelled sub-regional, fixed above), Johnson (the core factor
learned from distant homes cut Jackson from 37% to 26%; fixed by the near-core order), Polk (Greene 52% vs 68%),
Lawrence (Barry 20% vs 9%), Stone (Taney 25% vs 19%); Webster and Callaway are right on the public base.

**Transfer test: Kansas** (2026-10-18). Advan Neighborhood Patterns Plus, Kansas destination block groups,
January-September 2026 (`neighborhood/raw_ks/`, parquet), plus Kansans' visits to Missouri from the Missouri files
(`build_ks_od.py` -> `od_ks_2026.csv`). Kansas public inputs: LODES 2023 Kansas main OD and the MO, NE, OK, CO
auxiliary files; CenPop2020 Kansas tracts; ACS 2020-2024 tract and county (B19301) tables; Kansas Department of Revenue
County Trade Pull Factors FY2025 (`build_ks_pull_factors.py`: pull factor, trade area capture in customers); county
classes by nearest Missouri class centre (`build_ks_county_classes.py`: 30 small rural, 63 independent towns, 4
commuter, 8 hubs). The Missouri settings and the Missouri-learned corrections were applied unchanged
(`STATE=20` builds; `transfer_adjustments.py`; `score_ks.py`; benchmark `ks_advan_fitted.py`, the adopted model's form
fitted to Kansas Advan, each county held out).

| Kansas | Small rural (30) | Indep. towns (63) | Commuter, KC metro (3) | Commuter, Wichita ring (1) | Hubs (8) | All (105) |
|---|---:|---:|---:|---:|---:|---:|
| Advan-fitted in Kansas | 4.12 | 2.74 | 2.84 | 3.09 | 1.55 | 3.05 |
| **Public model, Missouri settings, nothing tuned in Kansas** | 3.80 | 3.83 | 4.42 | 3.01 | 2.62 | **3.74** |
| + corrections learned in Missouri | 3.64 | 3.83 | 8.82 | 4.16 | 4.61 | 3.98 |

The public model transfers: 0.69 points above the Kansas Advan-fitted model (Missouri: 1.21), and better than it for
small rural counties. Corrections that encode the rural-to-regional-centre relation transfer (Cowley 10.19 -> 5.41,
Harper 8.77 -> 5.34, Kearny 7.57 -> 3.72, Barber 4.70 -> 2.29, Greenwood 3.84 -> 1.69 -- ties to Wichita and Garden
City); corrections around metro cores and near dominant counties do not (Johnson KS 4.32 -> 10.06, Douglas 1.70 ->
9.62, Doniphan 1.32 -> 7.45): they were learned from St. Louis and Kansas City as seen from Missouri, and in Kansas the
1M+ metro-core definition takes in Johnson County and Wyandotte. Applied to small rural counties only, the corrections
give about 3.69.

Rejected: a pooled hub relation (dominant commuting county is a regional centre or core; factor under 15 miles 0.83 --
near hubs are overstated on average, Christian -> Greene, while Newton -> Jasper is understated); hub pairs with their
own distance bands (3.88); one factor per class for the core of the home county's own metro or micro area (Johnson County is its own
micro area; the St. Louis metro has several central counties); a commuting rank x destination order cell (up to 120
cells, overfit: 4.27-4.35); destination class x distance band (4.23); fitting the mixture weights of the public parts
to Advan by class (`public_segment_weights.py`, 4.49; parked as Stage 2).

**Audrain's north/south split** is one tract (950100, Vandalia-Laddonia): 16.9% of its out-of-county visits go to
Marion against 1.4-5.0% from the other tracts; under 1% of its workers work there. Its schools (Van-Far) play in the
Eastern Missouri conference with Pike, Ralls, Lincoln and Montgomery. The tract model gives 6.2%; county-level
corrections cannot move one tract.

**Athletic conferences** (datadesk visuals 34-36, Boone, Audrain, Osage; FIPS corrected: Cooper 29053, Howard 29089):
destinations within 80 miles that share a conference get 14% more travel than the Advan-fitted model predicts,
relative to the rest (pooled log ratio +0.06 vs -0.08; Audrain 1.14 vs 0.92, Osage 1.11 vs 0.95, Boone 0.89 vs 0.92).
Conferences are assigned by enrollment and geography and produce recurring travel and sports coverage: a central
place channel between places of the same order. Statewide test pending (school-level: MSHSAA conference and class,
NCES locations, TIGER school districts).

### Activity spaces and tie markets: the footprint of potential local news interest (2026-10-18)

Claim: where residents live, work and travel regularly is their definition of local, and the activity-space footprint
of a place's population, strengthened by news ties, is a market within which they have an interest in news and
information. Activity space after Yuan & Xu (2022): external indicators (size, shape, orientation -- standard
deviational ellipse, radius of gyration, convex hull) and internal ones (regularly visited places, entropy). Advan
reports aggregates by home area, so these are the collective activity spaces of a home area's residents.

**Observed** (`activity_space.py`): Advan, January-July 2026 (2020 block groups), home tract -> destination block
group (`od_tract_bg_mo_2026_janjul.parquet`); regular = the block group in 4+ of 7 months; home county included (where
residents go, not how much each place matters). 3 km hexagons; footprint = the fewest hexagons holding 80% of regular
visits; market = the footprint closed over gaps of 2 hexagons, holes filled; separate markets = parts holding 5%+ of
its area. Tracts, median: small rural 549 km2, 3 lobes, 79% of visits outside the home county; hubs 433 km2, 1 lobe,
24%. Replicability (odd vs even months, 1,653 tracts): market overlap (Jaccard) 0.78, same number of markets 74%.
Places (`place_activity_space.py`): Columbia's population is the primary activity space of 250,502 residents outside
the city at 10%+ of their regular visits (140,632 at 20%+): Boone, Callaway, Cole, Randolph, Audrain, Cooper, Saline,
Macon, Howard. Jefferson City 102,095 (Cole, Callaway, Moniteau, Miller, Osage); Moberly 22,355; Mexico 4,791.
Radius of gyration and convex hull computed over all regular visits are inflated by a few distant destinations; the
hexagon market is the robust measure.

**Tie market** (`tie_footprint.py`): the network tie of the market maps (`flows/market_patterns.py`, run unchanged) --
travel x (1 + 0.3 out + 0.3 in + 0.7 shared places + 0.7 shared coverage), gate, spatial lag and direction, home 100 --
from four travel sources (Advan all months, odd months, even months; public); market = hexagons with a tie of 5+,
closed. Public travel: the regular-travel public model (`public_travel_tiers.py REGULAR=1`: long-distance business,
specialty, visiting and vacation trips dropped), per-class settings, Missouri segment corrections, LODES home-county
share, spread within counties by jobs and OpenStreetMap destinations at distance^-0.5, and Advan's regularity as a rule
(`regularity_rule.csv`: logit of 4+ of 7 months on log share and log tract population, 85.7% agreement; a block group
counts at P >= 0.5 -- about 0.011% of a 4,000-person tract's visits).

| 36 study towns, 7 markets | Replicability (Advan, odd vs even) | Accuracy (public vs Advan) |
|---|---:|---:|
| Kansas City (6) | 1.00 | 0.92 |
| St. Joseph (3) | 0.96 | 0.84 |
| Joplin (5) | 0.94 | 0.84 |
| Springfield (6) | 0.90 | 0.80 |
| Columbia (8) | 0.85 | 0.67 |
| Kirksville (3) | 0.87 | 0.53 |
| Cape Girardeau (5) | 0.86 | 0.36 |
| **All (median)** | **0.91** | **0.70** (travel alone 0.67) |

Same number of markets 53%, within one 97%. The network terms raise public accuracy (travel alone 0.67): coverage
ties and shared third places are public data and pull the predicted market toward the observed one.

Steps (Columbia's eight towns, median accuracy): uncorrected public 0.655 -> corrected + within-county exponent 0.5
0.665 -> + regularity rule 0.67. Audrain: Vandalia's public markets are now the two Advan shows (northeast toward
Hannibal, and Columbia; accuracy 0.44 -> 0.57); the false Kansas City and St. Louis markets came from the public model
overdrawing metros for a small town (Jackson 3.3% of out-of-county travel against Advan's ~0.2%; St. Louis County 11.8%
vs ~4.5%; Marion 2.2% vs ~17%), amplified by Kansas City being one map unit. Mexico keeps one false market (Jefferson
City, 1.1% of observed travel): LODES gives Audrain residents 398 jobs in Cole, 78% in "all other services" (which
includes government), while Advan shows 1.4% of their out-of-county work-behaviour visits there -- consistent with
LEHD's imputed establishment assignment of state jobs to the capital; observed LODES only within 45 miles does not
remove it (0.65). Rejected: long-distance kinds in activity spaces (create false metro markets); hexagon-level scoring
of visited cells (the market is the region, not the cells).

Within-county spread tested (Advan's county shares, so only the spread differs; footprint overlap): jobs 0.49, OSM
destinations 0.50, half each 0.53; distance exponent 1: 0.59, 3: 0.37.

**Cape Girardeau market (0.36), diagnosed:** the public markets are in the right places (79-100% inside Advan's) but
too compact -- Jackson 608 km2 against 1,404, Scott City 427 against 1,170, Marble Hill 913 against 2,644: regular
visits in this farm region spread over rural block groups that jobs and listed destinations miss. **ADOPTED:** where
people live (2020 Census block group population, CenPop2020_Mean_BG29) as a third of the within-county spread, with
jobs and OSM destinations (`tie_footprint.py ATTRPOP=1`):

| Tie market accuracy (public vs Advan) | Jobs + OSM | + population, all tracts (adopted) | + population, tracts < 50/km2 | < 200/km2 |
|---|---:|---:|---:|---:|
| Cape Girardeau | 0.36 | 0.49 | 0.39 | 0.46 |
| Kirksville | 0.53 | 0.62 | 0.53 | 0.57 |
| Columbia | 0.67 | 0.69 | 0.68 | 0.69 |
| Joplin / St. Joseph / Kansas City | 0.84 / 0.84 / 0.92 | 0.85 / 0.85 / 0.92 | 0.84 / 0.85 / 0.92 | 0.84 / 0.85 / 0.92 |
| Springfield | 0.80 | 0.74 | 0.77 | 0.74 |
| All 36 towns, median / mean | 0.70 / 0.687 | 0.70 / 0.707 | 0.72 / 0.703 | 0.71 / 0.706 |

**Transfer test of the markets: Kansas, travel only** (`activity_market_score.py 29|20`; Kansas has no outlets in the
story collection, so no news terms). Same settings in both states: regular-travel public model by class without
corrections; LODES home-county share; within-county spread of jobs, OpenStreetMap destinations and population at
distance^-0.5; the Missouri-fitted regularity rule; every tract's 80% market, closed. Kansas inputs:
`build_ks_tract_bg.py` (Advan Kansas destinations + Kansans' Missouri visits), `flows/build_destinations.py STATE=20`
(65,171 OSM destinations), Kansas WAC, block-group boundaries and population centres.

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

Against the conventional definitions of a local market (same tracts; overlap = median Jaccard with Advan's market;
recall = share of Advan's market covered; precision = share of the definition that is Advan's market):

| Market definition | Missouri overlap / recall / precision | Kansas overlap / recall / precision |
|---|---|---|
| Advan, odd vs even months (ceiling) | 0.78 | 0.74 |
| Public model | 0.53 / 83% / 66% | 0.56 / 78% / 77% |
| Commuting shed (LODES alone, spread by jobs) | 0.45 / 77% / 57% | 0.45 / 76% / 57% |
| Circle of the class's median observed area | 0.34 / 45% / 55% | 0.28 / 46% / 45% |
| Home county | 0.25 / 29% / 76% | 0.28 / 31% / 80% |

The home county -- the usual unit of a local market -- holds under a third of residents' regular market; the public
model holds about four-fifths of it, twice the county's overlap.

Population for every tract: the best mean and no threshold; a county rule (nonmetro counties only, 0.697) misses
Cape Girardeau and Bollinger, metro counties whose residents travel like rural ones.

Related: Bisiani, Gulyas & Heravi (2025) derive outlets' coverage footprints from place mentions (convex hull and
radius of the top 75% of places, LSOA count, Gini, entropy, Moran's I, distance decay; six outlet types) with no test
against where audiences live or travel; this work supplies the audience side. Coverage places here are after the
grounding gate (PR #595, 2026-09-16; March corpus regrounded) -- every stored place is named in the article text.

### Information needs markets: name, certainty, minimum size (2026-10-18)

The revealed news market maps are named **local information needs areas** ("<Town>'s local information needs area";
numbered -- "Columbia's local information needs area I" and "II" -- only when a town has more than one; no direction in
the title; renamed 2026-10-18 from "information needs market"). Certainty layer on the approved maps (`market_pattern_print.html &conf=1&outline=1`;
`analysis/confidence_layer.py`, `flows/pattern_halves.py`): the same network tie from odd and from even months; a
shown hexagon is lighter when it clears the map's floor in one half only; the market is drawn as one connected area
(confident cells joined by closing, small clusters kept within 5 hexagons, lone far cells dropped, smoothed ~5 km,
gaps filled with empty hexagons, nothing drawn outside it, no outline line).

**Minimum size, ADOPTED:** a secondary or tertiary market needs 10%+ of the town's residents AND 1,000+ residents
(`market_patterns.py`; primary always kept). Evidence (`analysis/market_stability.py`, 75 markets): the share of a
market's shown hexagons holding in both halves rises with its residents (Spearman 0.37; median 0.84 under 500, 0.85 at
500-1,000, 0.89 at 1,000-2,000, 0.93 at 2,000-5,000, 0.95 above), and small markets spread thinly -- Mexico's
secondary (729 residents) showed 389 hexagons, 72% holding. Dropped among the study towns: Mexico 2, Vandalia 2,
Hallsville 2, Lancaster 2, Lexington 2, Savannah 3, Centralia 3, Macon 2; 63 markets remain. Large markets can be
unstable for another reason (Kansas City suburbs: Harrisonville 1 0.44, Grain Valley 1 0.53 -- ties near the floor
across the metro); a stability threshold was not adopted (it would drop Lee's Summit 2, 36,956 residents).

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

**Sports stories counted at half weight (2026-10-17, final).** The 1,837 enriched March Sports stories (CIN) were
re-run under focus-v4, the rule that centres a game on the publication's own team; 1,827 completed (four hang on
one LLM call every run and stay unenriched). The re-run mostly placed stories that had no centre: 679 gained one
(506 home, 173 away). Of stories placed before, 23 moved away -> home and 4 home -> away; the away share of placed
Sports stories is 18.0% for print/digital (17.0% before) and 34.3% for broadcast (35.7%). In a sample of 45
away-centred re-run stories about 13 were the outlet's own team centred on the game site or the opponent (Mizzou
softball -> Champaign, the SEC tournament -> Nashville, Bunker's archer -> Dent), about 28 correct, 4 unclear
(`analysis/sports_home_away_audit.py`; `coverage/rerun_2026_10_17/sports_still_away.csv`).

A Sports story counts half: 0.5 centred in another county, 0.25 as a mention. The reason is the category, not the
misattribution: a game is between two teams, usually from different places, so a Sports story reaches another county
by its nature and would inflate an outlet's spillover through a single category. Undiscounted, about 40% of print
outlets' Sports stories count as spillover, against 23-29% for every other category; broadcast Sports (about 34%) is
not inflated.

Leave-one-market-out under each counting choice (`analysis/spillover_dma_holdout.py`; held-out miss as a percentage of
the market's mean rate, markets with 3+ fitted outlets): the best combination in every market uses mention weight 0.5.
Sports at half weight is best in Columbia-Jefferson City (17 against 22 at full weight), Joplin, Springfield and St.
Louis (tied); full weight in Kansas City, Paducah-Cape Girardeau and St. Joseph. Mean over the seven markets 23.1 (half)
against 23.4 (full); without Columbia-Jefferson City 24.2 against 23.7. Leaving Columbia-Jefferson City out raises its
miss by 0.4-0.8 points under every choice, against 0.3-0.5 across all markets.

| Mention weight | Sports weight | Mean rate | Held-out | Held-out ÷ mean | Audrain | Boone | Osage |
|---:|---:|---:|---:|---:|---|---|---|
| 0.5 | 1 | 30.6% | 7.1 | 23% | 34% / 30% | 32% / 26% | 29% / 31% |
| **0.5** | **0.5** | 25.6% | 6.0 | 23% | 20% / 23% | 29% / 24% | 26% / 24% |
| 0.5 | 0 | 20.5% | 6.8 | 33% | 5% / 16% | 26% / 22% | 22% / 16% |
| 0.25 | 1 | 22.1% | 6.7 | 30% | 25% / 19% | 24% / 19% | 18% / 20% |
| 0.25 | 0.5 | 18.6% | 5.5 | 30% | 14% / 15% | 22% / 17% | 16% / 15% |
| 0.25 | 0 | 15.1% | 5.6 | 37% | 2% / 11% | 20% / 17% | 14% / 11% |

County columns are actual / expected. Each row is a different outcome, so held-out error is compared relative to the
mean rate. Mention weight 0.25 raises the relative miss at every sports weight; sports weight 0 removes real
spillover with the errors (Audrain's is 76% Sports: the Mexico Ledger's Centralia and Community R-VI coverage).
Final: 87 outlets in 47 counties, held-out error 6.0 points. Coefficients: broadcaster +0.68 (p < 0.001), weekly in
a daily-and-TV county −0.56 (0.008), miles to the county edge (log) −0.14 (< 0.001), print outlets in the county
(log of 1 + count) −0.28 (0.001). Audrain 20% actual, 23% expected; Boone 29% / 24% (print and digital 18% / 16%);
Osage 26% / 24%. Springfield region held out: mean miss 8.6 points; region 27% actual, 27% expected.

Share of spillover by CIN category, well-collected outlets, adopted weights:

| | Print/digital | Broadcast |
|---|---:|---:|
| Spillover | 23.8% | 33.8% |
| Sports share of stories / of spillover | 29% / 25% | 14% / 7% |
| Emergencies and Public Safety share of spillover | 11% | 43% |
| Spillover with Sports stories removed | 25.2% | 36.4% |

The figures below this paragraph in this section were written before the Sports re-run and the Sports weight.

**Re-run of the March enrichment (2026-10-17).** 4,669 articles were re-enriched after five crawler fixes:
the model is told where the publication is (#736); a game is centred on the publication's own team (#738);
a statewide story is filed under its own state and state-named places stay local (#738, #739); a long partial
story is enriched rather than skipped, and the TownNews premium-content notice is removed (#739); 970 March
bodies stored as ROT47 ciphertext were decoded (#736, #737). The story map and the quality table were rebuilt
from production. Full before/after: `coverage/rerun_2026_10_17/REPORT.md`.

The model was refitted on the rebuilt data, on well-collected outlets with **20 or more** placed stories
(scored on the same outlets, each county predicted from the others; floor 20 predicted better than floor 10).
Statewide outlets are not counted as any county's local news and are not in the fit
(`analysis/excluded_outlets.py`): the Missouri Business Alert (filed under Boone) and The Missouri Independent,
Missouri Net, Missouri Scout and The Missouri Times (filed under Cole), with The Maneater and CoMoBuzz. Cole's
spillover is now the Jefferson City News Tribune's: 30% actual, 33% expected (36% with the four statewide
outlets). Kansas City, Kansas is home for Kansas City, Missouri outlets: a story about
Wyandotte County is not spillover for them, in the model and the county figures alike (2026-10-17; Jackson
County 29% actual, 29% expected; KC Beacon 37% -> 23%, The Pitch 28% -> 26%). 83 outlets in 46 counties;
held-out error 7.1 points (8.6 before). Coefficients: broadcaster +0.58 (p < 0.001), weekly in a
daily-and-TV county −0.47 (0.020), miles to the county edge (log) −0.17 (< 0.001), print outlets in the
county (log of 1 + count) −0.42 (< 0.001).

A weekly alone in its county is already a factor through the print-outlet count (one outlet is the floor
of that term). An explicit term was tested and not adopted: alone by the registry −0.16 (p 0.28), alone by
the outlets collected −0.14 (p 0.28), any weekly −0.18 (p 0.13); chosen inside each fold without the held-out
county, the mean miss is 7.41 against 7.36 without (median 5.80 against 6.03), and the choice split 28 to 24
between two of the terms.
Boone's print and digital spillover is now 23% actual (20% expected), up from 14%: the Columbia
Missourian, Columbia Daily Tribune and Boone County Journal had been stored as ciphertext, and both Columbia
dailies now pass the quality tests.

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

## Revealed media market by travel pattern (2026-10-17)

A town's revealed media market is (1) crossover of its residents into other counties, the potential demand, and (2)
spillover between the county pair in both directions, the supply. Residents do not share one travel pattern, so the
market is the most common pattern among them; secondary and tertiary patterns are separate maps.

**Patterns** (`flows/travel_patterns.py`). Advan Neighborhood Patterns Plus, January-July 2026 (the months on 2020 block
groups): for each home block group of Audrain, Boone and Osage and each destination, reach = residents seen in the
destination's busiest block group / residents seen at home. Destinations are towns (2020 places), rural block groups
outside towns, and Missouri counties outside the Columbia-Jefferson City TV market; a block group's own town is left
out. Travel is decomposed by non-negative matrix factorization (a mixed-membership model): each block group's travel is
a weighted mix of K recurring patterns. K = 6, chosen on held-out months (fitted on four months, weights refitted on
two others, scored on the third; 10 random splits; fewest patterns within one standard error of the best): mean error
2.87 points at K = 1, 2.30 at K = 6, 2.42 at K = 8.

**Residents** Each block group's estimated residents (devices seen at home / the county-month calibration factor, as
for crossover) are allocated to patterns in proportion to the travel each carries, and ranked: primary, secondary,
tertiary.

| Town | Estimated residents | Primary pattern |
|---|---:|---|
| Columbia (82 block groups) | ~107,000 | Columbia, the US 63 corridor through Ashland, Jefferson City: 42% |
| Mexico (7) | ~7,100 | Mexico, rural Audrain, Columbia as a secondary focus: 79% |
| Linn (1 block group, holding the town) | ~1,800 | Jefferson City, rural Osage and Cole: 93% |

**Market test** (`flows/market_patterns.py`). For each county in a pattern: crossover = the town's residents in the
pattern x the county's share of the pattern's travel; spillover both ways, March 2026, local outlets only, weighted as
the adopted measure. Mexico's primary market: Boone 893 residents crossing, Audrain outlets' stories about Boone 10.0%,
Boone outlets' about Audrain 0.5% -- demand and one-way supply. Columbia's: Cole 2,682 crossing, 11.6% and 16.3% both
ways. Linn's: Cole 522 crossing, 8.1% and 0.2%.

**Local index, by 3 km hexagon** (adopted 2026-10-17). A place is local to a resident through three things: crossover
(travel there), spillover out (home outlets' news located there) and spillover in (its outlets' news located in home).

  local = travel x [(1 + out + in) / 3] ^ s,  s = 1 (demand and supply weigh equally; out and in equally within supply)

Travel is THE TOWN'S OWN travel in its pattern, not the pattern itself: a pattern is fitted across all 158 block
groups, so it carries other places' trips (Osage's pattern took southern Osage residents to Maries: Linn's own reach
to rural Osage averages 0.15 against the pattern's 0.31; to Maries 0.02 against 0.11). Each of the town's block groups'
observed travel to a place is split across the patterns by the share each explains there (the mixture's
responsibilities), and the town's map is its travel attributed to its pattern (busiest place = 1). The aim is the most
common pattern among the town's residents, not the county's movements. Home is 100: the town's hexagons and every
hexagon of its residents' own block groups (masked from their own travel, they would otherwise read 0). Coverage is LOCATED, not
counted by county: each March story's weight goes where it is -- a precise point to its hexagon, a town (central place or
named place) spread evenly over the town's hexagons, a county-only location spread evenly over the county's hexagons;
central 1, each other named location 0.5, Sports half, local outlets only. out = home outlets' coverage of the
hexagon's town (or rural block group) / their coverage of the home town; in = the share of the coverage by outlets based
in the hexagon's town (registry city) located in the home county / the same share for the home county's own outlets;
both capped at 1. The home town is 100. A place travelled to with no coverage either way keeps a third of its travel
value; rural places the county's news does not locate stories in are dimmed, at home too. Values (out / in): Columbia
-> Jefferson City 0.22 / 0.27; Mexico -> Columbia 0.10 / 0.03; Linn -> Jefferson City 0.25 / 0.01.

**Network tie** (adopted 2026-10-17; replaces the local index above). A town's market is a network: its residents tie to a
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
orange dot sized by the lift (10%, 25%, 50%+). The overlaps (network closure: two places embedded in the
same third places) carry 0.7 of it, the single direct ties 0.3. A third place strengthens the pair, not itself --
Columbia residents in Centralia, which the Mexico Ledger covers, strengthens Columbia-Mexico; Centralia's own tie is its
own travel and coverage -- so no coverage is counted twice. Sensitivity (each weight halved and doubled, primary
markets): rank correlation of hexagons 0.988-1.000 for Columbia, Mexico and Linn; at most 25 of 608 hexagons change
band. Columbia's strongest ties (shared places / shared coverage): Ashland 0.38 / 0.61, Jefferson City 0.19 / 0.34,
Mexico 0.16 / 0.26. KRCG (registry town New Bloomfield) overlaps nearly every town's coverage, but almost no one
travels to New Bloomfield, so it stays faint: news is made there, but it is not local to most residents.

**Markets per town** (adopted 2026-10-17): a pattern is mapped as a market only if 10%+ of the town's residents follow
it; the primary is always kept. Hubs split (Columbia 42/36/12, Springfield 31/30/18, St. Joseph 26/22/20); isolated
towns have one market (Linn 93, Belle 95, Cassville 92, Sikeston 78, Neosho 79). A stated threshold, like the
hexagon floor of 5; held-out error does not test it.

**Rural shading, dasymetric** (adopted 2026-10-17): Advan locates travel no finer than a block group, and a rural one
covers 30-60 hexagons (Barton County outside Lamar: 5 block groups). Within a rural block group, travel is spread by
OpenStreetMap destinations (115,453 statewide, `flows/build_destinations.py`): a hexagon's weight is (destinations +
0.25) / the block group's mean of the same, so the block group's average is kept, farmland falls and destinations rise;
travel capped at 1. Towns keep one value. A floor of 1 left sparse rural counties one flat band.

**Network tie, revised** (2026-10-17, Columbia first; other markets after the weights settle):
- Home county: home outlets' market is their county, so every home-county hexagon carries their outgoing tie (1.0). Before,
  outgoing coverage was compared with the home town, and rural home-county hexagons got almost none.
- Shared coverage counts only places in the town's own market (travel 0.05+ of the busiest). Two newsrooms both reporting
  statewide news (the capital, the university) had tied Columbia to Kansas City (244 of 267 lifted hexagons).
- Spatial network effect: adjacency tie' = tie + 0.25 x ring-weighted mean of neighbours (rings 1-3 at 1/2, 1/4, 1/8),
  only where residents travel; direction x (1 + 0.5 R cos(bearing - the market's mean bearing)), R the tie-weighted
  resultant length -- a market's direction strengthens (Columbia's primary south, its secondary north), the opposite side
  weakens. On a hexagon grid queen and rook contiguity coincide (6 neighbours).
- Gate on the shared ties: shared places and shared coverage count only when the pair already covers each other (out + in
  of 0.10+ of home). Without it, Columbia's heavy coverage of Jefferson City, where Linn residents go, tied Linn to Columbia
  (shared places 0.32) although the two barely cover each other (0.05 out, 0.02 in). Kept: Linn-Jefferson City (0.26),
  Mexico-Columbia (0.12), Columbia-Mexico (0.22).
- Dots only outside the home county: home outlets' coverage of their own county is the baseline of local news and stays in
  the blue shade; dotting it buried the ties between places under a uniform blanket.
- Headroom: travel is scaled so a town's busiest destination is 50; home stays 100. At 100 the top destination started at
  the cap and its news ties could not show (Linn's paper covering Jefferson City, Linn's busiest destination).
- Orange dots mark what news coverage alone adds (before the spatial effect): 10%, 25%, 50%+.
- Frame: the TV market's size, shifted toward a market that crosses it (only hexagons of 20+ count as crossing).
- ONE SCALE (adopted 2026-10-17; replaces the TV-market frame, its extension and the zoom rule below): every map is a fixed
  frame about 190 x 180 km -- the size of the Columbia-Jefferson City TV market, some 12-16 counties -- centred on the
  town's market (the tie-weighted centre of its hexagons of 10+), shifted only to keep the home county in view. Three
  counties (St. Joseph's, Kirksville's TV markets) was too close; 26-27 (Springfield's) too far. The TV-market outline stays
  as a reference line. Travel data and county lines cover Missouri only: across a state line the frame is blank.
- (superseded) Zoom in a large TV market: when a town's market core (hexagons of 10+ holding 90% of its index) spans under a third of
  its TV market's width, the frame is the core and the home county with a margin (Springfield, Independence, Lee's
  Summit); otherwise the TV-market frame.
- Display selectivity: each map shows only the hexagons holding the strongest 50% of its ties outside home (floor never
  below 5; isolated hexagons need up to twice it). Cuts the long tail so compact and diffuse markets read alike: Columbia
  primary floor 15.9 (239 hexagons), secondary 15.0 (398). At 80% the floor fell to 3-4 and cut nothing.

**Frame and display** (adopted 2026-10-17): destinations are all of Missouri (towns and rural block groups) so travel
across a TV-market border is measured; maps are DMA-sized for legibility. The frame is the TV market unless 10%+ of a
town's index (hexagons of 10+) lies outside it; then it takes in the core hexagons holding 90% of the index, capped at
1.5x the TV market's width and height around the home county. Hexagons show at 5+ inside the TV market and 10+ outside
it, so one-off distant trips and rural destination clusters stay off. Labels: home town bold; up to 8 towns on shaded
hexagons in ink; up to 4 unshaded towns of 20,000+ in small grey.

**Markets fitted separately** (`flows/regions.json`; `build_homes.py`, `travel_patterns.py <region>`,
`market_patterns.py <region>`): each TV market's patterns are fitted on its own home counties only, so adding a market
never changes another's maps (Columbia's fit verified identical after the change). Seven: Columbia-Jefferson City
(Audrain, Boone, Osage), Springfield (Greene, Webster, Barry), Paducah-Cape Girardeau (Cape Girardeau, Scott,
Bollinger), Ottumwa-Kirksville (Adair, Macon, Schuyler), Joplin (Jasper, Newton, Barton), Kansas City (Jackson, Cass,
Lafayette), St. Joseph (Buchanan, Andrew, Nodaway). Held-out months chose six patterns in every market. Advan covers
Missouri destinations only: trips into Kansas, Illinois, Iowa and Arkansas are not seen (largest for Kansas City).
Macon County had no local stories in March: no outgoing coverage there.

**Figure** (`flows/market_pattern_print.html`, title "<town>'s revealed news market"): a modelled map on the hexagon
grid; hexagons of 5+ shaded, one ring of empty hexagons as a border, labels never on a dark (20+) hexagon. A shaded
rural block group or tract can cover half a county; the grid marks the figure as a model.

Superseded on the way (kept in `flows/`): tract reach maps (`build_reach_map.py`, a shrunk logistic model chosen on
held-out months, corridor term adopted, direction and home-town terms no gain) and a travel x coverage interest index
(`build_interest_map.py`, w = 0.5/1/2, with road corridors from `build_transit_lines.py`).

## Open

- One month of coverage limits every story-count comparison; counts per county pair are small.
- The level version of saturation (rural home × destination's own stories) was tested only within the
  all-factors model; it was not tested alone.
- Out-of-state travel is not observed (Missouri destinations only).
- Spillover: the Centralia Fireside Guard and Vandalia Leader have no usable spillover figure (short texts).
- Public travel model: rings of regional hubs (Polk, Newton, Christian, Pulaski, Johnson, Webster, Callaway, Stone,
  Lawrence) are not improved by any correction; the destination pull needs public measures beyond sales and
  population (hospital, four-year college, supercenter, interstate, lakes and parks, county seat); small pairs (Advan
  share under 1%) are off by 2.3x typically and are barely counted by the share-weighted error -- a ratio measure is
  needed beside it.

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
- U.S. Census Bureau. (2024). *County Business Patterns 2022* (cbp22co) [Data set].
- U.S. Census Bureau. (2025). *American Community Survey 2020–2024 5-year estimates, table-based summary file*, tracts:
  B19013, B19001, B15003, B25003, B08006.
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
- U.S. Census Bureau. (2025). *LODES 8 workplace area characteristics*, Missouri, 2023 (mo_wac_S000_JT00_2023).
- U.S. Census Bureau. (2023). *County adjacency file* (county_adjacency2023).
- Schläpfer, M., et al. (2021). The universal visitation law of human mobility. *Nature, 593*, 522–527.
- Simini, F., González, M. C., Maritan, A., & Barabási, A.-L. (2012). A universal model for mobility and migration
  patterns. *Nature, 484*, 96–100.
- Software: Python, statsmodels, pandas, shapely, SciPy, pyosmium; D3 for figures.

### Selection rule: sensitivity test (2026-10-18)

`analysis/selection_sensitivity.py` → `analysis/selection_sensitivity.csv`. The four published areas (Columbia I and II,
Mexico, Linn), each drawn under eight variants of the selection rule. Criterion: split-half agreement, the Jaccard
overlap of the hexagons the same rule draws from odd months (Jan, Mar, May, Jul) and from even months (Feb, Apr, Jun).

| Variant | Columbia I | Columbia II | Mexico | Linn | Mean |
|---|---:|---:|---:|---:|---:|
| **Adopted: 50%, 2x at 4 hexagons** | 0.896 | **0.880** | 0.941 | 0.734 | **0.863** |
| Selectivity 40% | **0.907** | 0.804 | 0.833 | 0.586 | 0.783 |
| Selectivity 60% | 0.812 | 0.839 | 0.844 | 0.573 | 0.767 |
| No distance rule | 0.881 | 0.865 | 0.856 | 0.601 | 0.801 |
| Distance 1.5x | 0.877 | 0.860 | 0.889 | 0.630 | 0.814 |
| Distance 3x | 0.872 | 0.839 | 0.932 | 0.724 | 0.842 |
| Distance reach 2 hexagons | 0.866 | 0.866 | **0.948** | **0.739** | 0.855 |
| Distance reach 6 hexagons | 0.889 | 0.871 | 0.933 | 0.736 | 0.857 |

The adopted values give the highest mean agreement; no variant beats them by more than 0.011 in any area. Dropping the
distance rule lowers agreement in all four areas. The adopted values were set for legibility, not tuned to
split-half agreement, so their scoring highest on it is independent support. Area sensitivity (overlap with the published area):
Columbia I changes little under any variant (0.77-1.0); Mexico is the most sensitive (0.44 at 40% selectivity, 0.50 at
3x distance).


### Coverage density: the supply into a local information needs area (2026-10-20)

**Coverage density** (name set by the user) is the supply side of the assessment: for each 3 km hexagon of a published
local information needs area (the footprint, as drawn; every hexagon counts the same), the local news stories in a month
whose area includes it. Central focus counts 1, a mention 0.5. A story's area follows its geographic scope (the
enrichment's scope classification): neighbourhood 3 km around its point; town the 2020 place and 3 km around it (5 km
around a point outside any town); regional 40 km; a county-only point or a county mention the whole county; statewide,
national and international stories none. Local outlets statewide; statewide and campus outlets excluded.
Tiers (user): daily coverage 9+ a month (2-3 a week), weekly 2-8 (2-3 a month as the floor), occasional under 2, none.
`analysis/area_coverage_alignment.py` -> `analysis/area_coverage_alignment.csv`, `flows/reach/coverage_columbia.json`;
map: `market_pattern_print.html?measure=coverage` (`&cov=local` leaves out county-level stories and county mentions).

| Columbia II | Daily | Weekly | Occasional | None |
|---|---:|---:|---:|---:|
| Place-specific stories | 24% | 5% | 26% | 45% |
| Including county-level stories | 83% | 17% | 0% | 0% |

Open: whether a county mention counts across every hexagon of the county (it makes every area weekly or better).


### Name: civic interest areas (2026-10-20)

The local information needs areas are renamed **civic interest areas** (user): residents' activity areas of news
interest. Map titles: "<Town>'s civic interest area", numbered I, II only when a town has more than one. Earlier
sections keep the name they were written under. Supply into an area: coverage density. Units of analysis: county ->
civic interest area -> each outlet's zone of service; no statewide measure is a finding.

### Coverage density: attribution by region size (2026-10-20, adopted)

City, county and region claims apply to the whole region, diluted by its size (user): weight per hexagon = story weight
(central 1, mention 0.5) x (7 / the region's hexagons) ^ 0.5, full weight at 7 hexagons or fewer (a neighbourhood, a
town the size of Linn). Counties and regions spread that total by 2020 block-group population. Square root adopted;
alpha = 1 (each story counted once) is the sensitivity check (`ALPHA=1` -> `*_alpha1` outputs).

| Area | Daily | Weekly | Occasional | None | alpha = 1: daily / weekly / occasional |
|---|---:|---:|---:|---:|---|
| Columbia I | 58% | 38% | 4% | 0% | 53% / 4% / 43% |
| Columbia II | 25% | 25% | 50% | 0% | 23% / 4% / 73% |
| Mexico | 32% | 15% | 53% | 0% | 30% / 3% / 67% |
| Linn | 25% | 54% | 21% | 0% | 22% / 5% / 73% |

Daily coverage barely moves with alpha (it is place-specific reporting); the weekly tier is what county-wide stories
supply, and alpha decides it. Newsrooms for 80% of the tier (weekly / daily): Columbia I 3 / 2, Columbia II 6 / 5,
Mexico 5 / 2, Linn 2 / 3. The count for 100% is not reported: the last hexagons are reached by fractions of distant
outlets' county mentions.

**Revised same day (user: the square root "overvalues mentions and county-wide coverage"; the region "looks
well-covered, which it is not").** Counties and regions are counted once (alpha = 1, spread by population); towns and
neighbourhoods keep the square root. Map: tiers in separate colours, not one ramp -- daily in three greens (9-29, 30-99,
100+), weekly ochre, occasional light grey, none empty.

| Area | Daily | Weekly | Occasional | None | Newsrooms for 80% of weekly / daily |
|---|---:|---:|---:|---:|---|
| Columbia I | 53% | 4% | 43% | 0% | 1 / 1 |
| Columbia II | 23% | 4% | 73% | 0% | 2 / 6 |
| Mexico | 30% | 3% | 67% | 0% | 2 / 2 |
| Linn | 22% | 5% | 73% | 0% | 2 / 2 |

**Tier names (user, 2026-10-20):** frequent (9+ a month), regular (2-8), sporadic (under 2), none. "Daily" and "weekly"
are reserved for publication frequency; the tiers above that used them read frequent and regular.

**Map scale stops at frequent (user, 2026-10-20):** frequent (9+ a month) is one colour; the volume steps above it (30-99,
100+) peaked in the population centres and showed population size. Stories stay a monthly count, not per capita (user).
**Map drawn as a surface (user, 2026-10-20):** coverage is painted beneath the hexagon grid -- stories a month on a log
scale capped at frequent (9+), blurred over about a hexagon, clipped to the area -- with the grid in white outline on top.
The key is a gradient from "rarely" to "several a week or more", without counts; the subtitle keeps the tier shares.
**Map: crisp hexagons (user, 2026-10-20: the blur "just does not work" beside the civic interest area maps).** Each
hexagon is filled with the continuous green (log scale, capped at 9+ a month) with white gaps, as the area maps; the
gradient key stays word-only. `?surface=1` keeps the blurred surface. Lines step back on the coverage map (lighter grid,
county borders, home county and TV market).

### Balanced diet of civic information (2026-10-20)

`analysis/cin_diet.py`. The ten CIN categories of the codebook (the eight critical information needs, Friedland et al.
2012, plus Civic Life and Sports). A hexagon has a **balanced diet** when any 8 of the 10 reach 1 story a month each by
coverage density (user: "8 of 10 served, but any 8"). The coverage density map is filtered by it (user: "volume is not
enough, balance is also required"): coverage is shaded only where the diet is balanced; elsewhere pale (`?balance=0`
turns the filter off). Sports at half weight in coverage density from 2026-10-20 (user).

| Area | Balanced | Mean categories met | Home town |
|---|---:|---:|---|
| Columbia I | 51% | 5.0 | Columbia balanced |
| Columbia II | 10% | 1.5 | Columbia balanced |
| Mexico | 14% | 2.2 | Mexico 6 of 10 |
| Linn | 14% | 1.7 | Linn 6 of 10 |

Only Columbia and Jefferson City carry a balanced diet. Outlets required for the balanced share that exists (exact, every
combination of the top 24): Columbia I 3, Columbia II 4, Mexico 3, Linn 2. Economic Development is the scarcest
category (Linn's area: none). The earlier outlets-required calculation on volume alone (`outlets_required.py`) is
superseded: one broadcaster and one weekly cannot supply a balanced diet.
**Map: volume as colour, breadth as size (user, 2026-10-20).** The binary balance filter was "too flat", and the shade
graded by volume x balance did not show volume without breadth. Each hexagon's colour is its stories a month; its size is
its breadth, full at 8+ of the 10 categories and shrinking to 40% with fewer, on a pale full-size grid -- a small dark
hexagon is plenty of news of a narrow kind (Moberly, Mexico, Boonville); only Columbia and Jefferson City are full size.
