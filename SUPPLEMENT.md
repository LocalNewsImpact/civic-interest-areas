# Supplementary material

Supplement to "Mapping Outside the Lines: Crossover and Spillover in Rural News" (manuscript under review). Copied from the manuscript on 2026-11-01; the manuscript is the authority where the two differ. `RESULTS.md` names the script that prints each value.

## S1. Spillover under other weights

Table 1's weights are definitions, not estimates. Table S1 gives each county's spillover when a mention counts 0.25, 0.5 or 1 of a story and a sports story 0, 0.5 or 1 of its usual weight, with the spillover model refitted on the same 85 outlets. Skill is 1 − MAE<sub>model</sub> ÷ MAE<sub>mean</sub>, where MAE<sub>model</sub> is the mean absolute error, in percentage points, of each outlet's predicted spillover when its county is left out of the fit, and MAE<sub>mean</sub> is that of predicting every outlet at the average rate. Audrain's spillover depends most on the sports weight: much of its coverage of other counties is high school sports.

**Table S1.** County spillover and model skill under alternative weights, March 2026.

| Mention | Sports | Audrain | Boone | Osage | Skill on outlets held out |
|---|---|---|---|---|---|
| 0.25 | 1 | 25% | 24% | 18% | +0.21 |
| 0.25 | 0.5 | 14% | 22% | 16% | +0.24 |
| 0.25 | 0 | 2% | 20% | 14% | +0.23 |
| 0.5 | 1 | 34% | 32% | 29% | +0.20 |
| **0.5** | **0.5** | **20%** | **29%** | **26%** | **+0.20** |
| 0.5 | 0 | 5% | 26% | 22% | +0.17 |
| 1 | 1 | 53% | 47% | 50% | +0.21 |
| 1 | 0.5 | 31% | 42% | 45% | +0.13 |
| 1 | 0 | 10% | 37% | 40% | +0.07 |

The adopted weights, 0.5 and 0.5, are in bold.

## S2. Calculations

Each measure is set out below: the question it answers, the calculation, its terms with fitted values, and its output. Fitted values are shown with standard errors in parentheses or 95% intervals in brackets. Travel and coverage are fitted on all Missouri counties, and spillover on 85 outlets in 48 of them; results are reported for Audrain, Boone and Osage counties. Visits: Advan Neighborhood Patterns Plus, January–September 2026 (civic interest areas: January–July 2026). Stories: March 2026. Commuting: LODES 2023.

### A. Travel: where each county's residents go

**Question.** How many visits would residents of county i be expected to make to county j, given distance, a shared border and commuting?

E[V<sub>ij</sub>] = exp(α<sub>i</sub> + γ<sub>j</sub> + β<sub>1</sub>D<sub>ij</sub> + β<sub>2</sub>D<sub>ij</sub><sup>2</sup> + R<sub>i</sub>(β<sub>3</sub>D<sub>ij</sub> + β<sub>4</sub>D<sub>ij</sub><sup>2</sup>) + β<sub>5</sub>P<sub>i</sub>D<sub>ij</sub> + β<sub>6</sub>B<sub>ij</sub> + β<sub>7</sub>C<sub>ij</sub> + β<sub>8</sub>C<sub>ji</sub>)

**Estimation.** Poisson pseudo-maximum likelihood over all 13,110 ordered pairs of 115 counties, pairs with no visits kept; standard errors clustered by home and by destination county. Held-out scores split the home counties into 8 groups; each group's destination shares are predicted from a fit to the other seven. A home county's effect α<sub>i</sub> cancels when its visits are expressed as shares, and each γ<sub>j</sub> is estimated from the other home counties.

**Terms.** V<sub>ij</sub>: visits by residents of county i to county j, January–September 2026, scaled to people, with highway pass-through stops removed. α<sub>i</sub>, γ<sub>j</sub>: overall travel from county i and overall draw of county j (one fixed effect per county). D<sub>ij</sub>: ln(miles between the 2020 population centers (U.S. Census Bureau, 2021b) ÷ 25). R<sub>i</sub>: 1 if county i is rural (under half its 2020 population in Census urban areas). P<sub>i</sub>: ln population of county i, centered (ACS 2020–2024). B<sub>ij</sub>: 1 if the counties share a border. C<sub>ij</sub>: ln(1 + workers living in i who work in j, per 1,000 workers living in i).

**Fitted values.** β<sub>1</sub> −0.88 (0.13), the distance elasticity at 25 miles for an urban home county; β<sub>2</sub> −0.26 (0.03); β<sub>3</sub> 0.18 (0.12); β<sub>4</sub> −0.21 (0.05); β<sub>5</sub> 0.13 (0.03); β<sub>6</sub> 0.44 (0.07); β<sub>7</sub> 0.28 (0.05); β<sub>8</sub> 0.19 (0.04).

**Output.** Expected visits for every county pair. Predicting each county without its own data, the model accounts for 93.7% [92.4, 94.8] of the variation in travel shares, with a share-weighted error of 3.28 percentage points; the terms were chosen on the same held-out groups, so this is an in-selection score, whereas the public-data model's 4.6 points (Methods) comes from a selection repeated inside each group. At 25 miles, the distance elasticity of visits is −0.88 for an urban home county and −0.70 for a rural one (β1 and β1 + β3; the difference, β3, is not distinguishable from zero); with the quadratic terms, going from 25 to 50 miles leaves 48% of the visits from an urban county and 49% from a rural one.

### B. Crossover: how many of a county's residents go elsewhere

**Question.** What share of a county's residents is seen outside the county in a month?

crossover<sub>c</sub> = Σ<sub>h∈c</sub> min(L<sub>h</sub>, D<sub>h</sub>) ÷ Σ<sub>h∈c</sub> D<sub>h</sub>,  where D<sub>h</sub> = E<sub>h</sub><sup>b</sup> S<sub>h</sub><sup>1−b</sup>

**Estimation.** b is estimated by two-stage least squares across months: a block group's log rate of leaving on its log detection ratio S<sub>h</sub>/E<sub>h</sub>, instrumented by the same ratio in another month (county-clustered first-stage F = 4,082). Identification rests on the extra devices seen at home not being seen away from it: they raise S<sub>h</sub> without raising L<sub>h</sub>. Another month's ratio is used because the same month's ratio and the leaving rate both contain S<sub>h</sub>, which would tie them together mechanically; a different month breaks that tie and averages out month-to-month noise in detection. What it cannot do is separate extra devices from residents who simply stay home more: both raise detection at home and lower leaving in every month, so b is, if anything, too high. b is 0.61 to 0.63 whichever month supplies the instrument.

**Terms.** L<sub>h</sub>: residents of home block group h seen in their single busiest block group outside the county, a lower bound on the residents who left. S<sub>h</sub>: residents of h seen at home, inflated where homes are over-detected. E<sub>h</sub>: ACS 2020–2024 population of h × the month's statewide devices per resident. b: how far the denominator moves from residents seen at home toward the expected population, on a log scale (ln D<sub>h</sub> = b ln E<sub>h</sub> + (1 − b) ln S<sub>h</sub>): b = 1 if the extra devices seen at home never leave, b = 0 if they leave as residents do.

**Fitted value.** b = 0.62 [0.53, 0.71].

**Output.** Share of residents seen outside the county in a typical month, January–September 2026: Audrain 44%, Boone 26%, Osage 59%. These shares depend little on b: over its 95% interval they move by less than a point in Audrain and Boone and by 3.5 points in Osage, and over the whole range of b from 0 to 1 they are 40–44%, 24–26% and 45–66%. Counting a resident in every destination visited, rather than once, gives an upper bound of 66%, 33% and 82%. These ranges reflect the choice of b and of the count, not sampling: the panel is not a probability sample of residents, so no sampling interval is given.

### C. Coverage: which counties each county's newsrooms cover

**Question.** How many stories would county k's newsrooms be expected to write about county j, given geography and residents' travel there?

E[S<sub>kj</sub>] = exp(ν<sub>k</sub> + μ<sub>j</sub> + θ<sup>⊤</sup>X<sub>kj</sub> + β<sub>1</sub>ℓ<sub>kj</sub> + β<sub>2</sub>R<sub>k</sub>ℓ<sub>kj</sub> + β<sub>3</sub>Z<sub>kj</sub>)

ℓ<sub>kj</sub> = ln V<sub>kj</sub> if V<sub>kj</sub> > 0, otherwise 0;  Z<sub>kj</sub> = 1 if V<sub>kj</sub> = 0, otherwise 0

**Estimation.** Poisson pseudo-maximum likelihood over every newsroom county k and other county j (88 newsroom counties × 114 other counties, 10,032 pairs; 14,877 stories, 10,282 of their story–county pairs outside the newsroom's county; 81% of pairs have no stories, 39% among pairs holding 1% or more of the newsroom county's visits), pairs with no stories kept; standard errors clustered by newsroom county (88 clusters); clustered by unordered county pair, the standard errors of the urban and rural elasticities are 0.052 and 0.049 against 0.069 and 0.059, and clustered two-way by newsroom county and county covered, 0.076 and 0.068; no conclusion changes. Travel spans January–September 2026 and includes the month of the stories, so the model measures association, not the direction of influence between travel and coverage.

**Terms.** S<sub>kj</sub>: stories by newsrooms in county k centered in or naming county j, March 2026. ν<sub>k</sub>, μ<sub>j</sub>: the output of k's newsrooms and how much j is covered by newsrooms anywhere (fixed effects). X<sub>kj</sub>: the distance, border and commuting terms of A. V<sub>kj</sub>: residents' visits from k to j, as in A. R<sub>k</sub>: 1 if the newsroom county is rural, as in A. Z<sub>kj</sub>: 1 if no visit was recorded.

**Fitted values.** β<sub>1</sub> 0.47 (0.069), the elasticity of stories to visits for urban newsroom counties; β2 −0.23 (0.047), the difference for rural newsroom counties; β1 + β2 0.24 (0.059), the elasticity for rural newsroom counties; β<sub>3</sub> −0.38 (0.62); θ: ln distance −0.73 (0.29), its square 0.21 (0.06), rural × ln distance 0.24 (0.26), rural × its square −0.37 (0.13), ln population × ln distance 0.15 (0.04), shared border −0.17 (0.09), commuting out −0.02 (0.09), commuting in 0.42 (0.07). Fitted against observed stories across pairs, r² 0.97.

**Output.** Expected stories for every pair. Twice the visits: 1.38 [1.26, 1.52] times the stories from urban newsrooms, 1.18 [1.09, 1.28] times from rural ones. Held-out error on destinations with 1% or more of the visits: 4.54 [4.09, 5.04] percentage points. Without the rural term β2, held-out error rises to 4.67: the term lowers it by 0.13 [0.05, 0.21] points (newsroom counties resampled in pairs, 1,000 draws). Leaving out one newsroom county at a time, the urban elasticity stays between 0.42 and 0.51 and the rural between 0.21 and 0.28.

### D. Spillover: how much of an outlet's news is about another county

**Question.** What share of an outlet's stories would be expected to be about other counties?

E[y<sub>o</sub>] = 1 ÷ (1 + exp(−z<sub>o</sub>)),  where z<sub>o</sub> = β<sub>0</sub> + β<sub>1</sub>T<sub>o</sub> + β<sub>2</sub> ln(1 + N<sub>o</sub>)

**Estimation.** Fractional logistic regression; cluster-jackknife (CRV3) standard errors by county. Fitted on the 85 outlets in 48 counties that meet the collection standard described in the Methods. The model carries no county effect: N<sub>o</sub> varies only between counties, and a county effect would absorb it. Outlets that meet the standard spill over more than those that do not (24.7% against 18.7%), so the fitted values describe well-collected outlets.

**Terms.** y<sub>o</sub>: outlet o's spillover, March 2026, weighted as in Table 1. T<sub>o</sub>: 1 if the outlet is a television or radio broadcaster. N<sub>o</sub>: print and digital news outlets active in the outlet's county.

**Fitted values.** β<sub>0</sub> −0.81 (0.13); β1 0.67 (0.15), p < 0.001; β2 −0.39 (0.12), p = 0.003 (t with 47 degrees of freedom).

**Output.** The expected share for each outlet; a county's expectation weights its outlets by stories. Held-out error, each county's outlets predicted by a fit without that county: 5.98 percentage points against 7.49 for predicting every outlet at the average rate, a skill of 0.20 (as in Table S1); 6.57 when the choice of terms is also repeated in each group. Refitted without each outlet in turn, the broadcaster term stays between 0.62 and 0.74 and the outlet term between −0.43 and −0.36; no single outlet carries either. County spillover, with 95% intervals from resampling each outlet's stories (9,999 draws): Audrain 20% [16, 23], Boone 29% [27, 31] (its print and digital outlets 18% [16, 20]), Osage 26% [17, 35]. Crossover is 2.3 times spillover in Audrain [1.9, 2.7] and in Osage [1.6, 3.6], the intervals also spanning the interval of b.

### E. Civic interest area: the places a town's residents share

**Question.** Which places belong to a town's civic interest area, and how likely is each?

R<sub>hx</sub> ≈ Σ<sub>k=1</sub><sup>K</sup> W<sub>hk</sub>H<sub>kx</sub>

T<sub>x</sub> = min(0.99, t · s<sub>x</sub> · U<sub>x</sub>)

a<sub>x</sub> = min(0.99, T<sub>x</sub>(1 + ω(0.3O<sub>x</sub> + 0.3I<sub>x</sub> + g<sub>x</sub>(0.7P<sub>x</sub> + 0.7Q<sub>x</sub>)))),  g<sub>x</sub> = 1 if O<sub>x</sub> + I<sub>x</sub> ≥ 0.10, otherwise 0

τ<sub>x</sub> = 100 · min(0.99, (a<sub>x</sub> + λL<sub>x</sub>)(1 + 0.5R cos(θ<sub>x</sub> − θ̄)));  τ<sub>x</sub> = 100 in the home town

p<sub>x</sub> = (1 ÷ 6,912) Σ<sub>s</sub> f<sub>s</sub>(x)

**Estimation.** Non-negative matrix factorization (Lee & Seung, 1999; multiplicative updates, Lee & Seung, 2001) of block-group travel in the Columbia–Jefferson City television market; the map drawn in 6,912 equally weighted versions (Steegen et al., 2016).

**Terms.** R<sub>hx</sub>: share of block group h's residents seen at place x, January–July 2026. W<sub>hk</sub>, H<sub>kx</sub>: h's weight on travel pattern k and pattern k's reach to x. K: the number of patterns, 2: the largest number each holding at least 10% and 1,000 of a town's residents and 10% of its travel, and recurring in odd and even months and across 10 random starts; each study town has one pattern. U<sub>x</sub>: the town's travel to hexagon x, each home block group's residents times its travel in the town's pattern (n<sub>h</sub>W<sub>hk*</sub>H<sub>k*x</sub>, summed), scaled so the busiest place is 1. t: 0.5 or 1, so the busiest place scores 50 or 100 (the home town is 100). s<sub>x</sub>: hexagon x's weight within its place (defined below). O<sub>x</sub>: the town's outlets' coverage located at x, relative to their coverage of the town (at most 1). I<sub>x</sub>: x's outlets' share of coverage in the town's county, relative to the town's own outlets' share (at most 1). P<sub>x</sub>, Q<sub>x</sub>: the overlap between the places the town's residents visit and the places x's outlets cover, and between the places the town's outlets and x's outlets cover (defined below). g<sub>x</sub>: ties through shared places count only where a direct tie reaches 0.10. ω: weight on news ties, 0, ½, 1 or 2; the four weights 0.3, 0.3, 0.7 and 0.7 are set by judgment (Table S2) and sum to 2, so at ω = 1 news ties can at most triple a travel tie and at ω = 2 multiply it by five, within the cap of 0.99. L<sub>x</sub>: the mean of a over rings about 1.6, 3.2 and 4.8 miles from x, weighted ½, ¼ and ⅛; a hexagon with no tie counts as 0, and the term is added only to hexagons with a tie. λ: 0, 0.25 or 0.5. θ<sub>x</sub>: the bearing of x from the mean center of the home town's hexagons; θ̄, R: the bearing and length (0 to 1) of the mean unit vector of those bearings over tied hexagons outside home, weighted by the smoothed tie. Ties below 1 are dropped. f<sub>s</sub>(x): the share of hexagon x's area inside the area drawn by version s (the 1.0- and 4.0-square-mile grids mapped onto the 2.3-square-mile grid). D90: the regular-travel distance, within which lies 90% of residents' trips to places visited every month, January–July 2026: Columbia 15 miles, Mexico 30, Linn 44.

**Drawing choices.** The 6,912 versions combine seven drawing choices and ω, levels in parentheses: hexagons of about 1.0, 2.3 or 4.0 square miles (3); t (2); spread of travel within places, off or at three strengths (4); λ (3); selectivity, the drawn hexagons holding 40, 50 or 60% of the town's ties outside home (3); a distance rule, on or off (2); reach, joining separate pieces within 6, 9 or 16 miles or within D90 (4); ω (4): 3 × 2 × 4 × 3 × 3 × 2 × 4 × 4 = 6,912.

**Definitions.** Spread (s<sub>x</sub>): within a rural block group, (OpenStreetMap destinations in x + f) ÷ the block group's mean of the same, so the weights average 1; within a town of two or more hexagons, half that and half x's 2020 population ÷ the town's mean; f = 0.1, 0.25 or 1, or no spread. Overlap (P<sub>x</sub>, Q<sub>x</sub>): Σ<sub>u</sub> min(a<sub>u</sub> ÷ Σa, b<sub>u</sub> ÷ Σb) over places u other than the town's own and x; for P<sub>x</sub>, a is the town's travel by place and b the stories x's outlets locate in each place (Table 1 weights; statewide and wider stories locate nothing); for Q<sub>x</sub>, a and b are the stories the town's outlets and x's outlets locate, over places holding at least 5% of the town's busiest-place travel. Distance rule: a hexagon not contiguous with the area's body needs a tie of f + f × min(1, g ÷ r) rather than f, where f is the tie at which the strongest hexagons hold the selectivity share of the town's ties outside home (at least 5; the raised floor at least 10), g is the hexagon's distance from the body and r is 6.5 miles inside the television market and 3.2 miles outside; the body grows from home until no further hexagon qualifies.

**Output.** p<sub>x</sub>, how likely each place is to be part of the area. The area is every place with p<sub>x</sub> ≥ 0.5 that is joined to the town or lies within D<sub>90</sub> of it, together with every town that at least half of the versions include in part, taken whole.

**Sensitivity.** Halving or doubling the constants set by judgment (the weights on direct news ties and on ties through shared places, and the strength of the direction term, 0.5) keeps 94% to 100% of each area's places and changes frequent coverage by at most three percentage points (Table S2).

**Table S2. Civic interest areas with the constants set by judgment halved or doubled.**

| Constant | Value | Places kept |  |  | Frequent coverage |  |  |
|---|---|---|---|---|---|---|---|
|  |  | Columbia | Mexico | Linn | Columbia | Mexico | Linn |
| As adopted | 0.3, 0.7, 0.5 | 100% | 100% | 100% | 60% | 44% | 41% |
| Direct news ties | 0.15 | 100% | 100% | 100% | 60% | 44% | 41% |
| Direct news ties | 0.6 | 98% | 99% | 97% | 60% | 45% | 41% |
| Ties through shared places | 0.35 | 100% | 100% | 99% | 59% | 43% | 41% |
| Ties through shared places | 1.4 | 97% | 94% | 98% | 61% | 47% | 42% |
| Direction strength | 0.25 | 99% | 99% | 99% | 59% | 44% | 41% |
| Direction strength | 1.0 | 97% | 95% | 98% | 59% | 46% | 42% |

Note. Each row redraws all 6,912 versions with one constant changed and every other setting as adopted. Places kept: the share of the adopted area's places that the redrawn area also includes. Frequent coverage: the share of the area covered by 9 or more stories a month.

## S3. Coverage density and balance

Each story is placed by its geolocated central point and its geographic scope, as classified by Backfield (Davis, 2026). A story is mapped to an area set by its scope: a neighborhood story to the 2 miles around its point; a town story to the town's 2020 boundary and the 2 miles around it (3 miles around a point outside any town); a regional story to the 25 miles around its point; and a story located only at the county level to the whole county. Statewide, national and international stories, and their mentions, are not mapped.

A story counts 1 where it is centered and 0.5 for each place or county it mentions; a named town stands for the town and the 2 miles around it, a named county for the county. Sports stories count half, as in the spillover measure.

The weight a story gives each hexagon depends on the size of the area it is mapped to. A town or neighborhood story gives each hexagon of its area w × min(1, (7 ÷ A)<sup>½</sup>), where w is the story's weight and A the number of hexagons its area covers on the 2.3-square-mile grid: full weight up to seven hexagons, about 16 square miles (a neighborhood, or a town the size of Linn), less beyond. A county or regional story gives its area, in total, the weight of seven fully covered hexagons (7w), spread in proportion to where people live (2020 block-group population) and at most w on any one hexagon. A hexagon takes a story's strongest claim.

Coverage density is the sum of these weights over the month. A hexagon is frequently covered at 9 or more stories a month (about two a week), regularly covered at 2 to 8 and infrequently covered below 2. No hexagon in the three areas goes without coverage: each lies in a county with county-level stories. A hexagon has a balanced diet when at least 8 of the 10 CIN categories each reach one story a month.

Coverage density and balance are measured on the civic interest area as mapped: every hexagon the maps show, including towns counted whole. Part of a place's news tie is how much the home town's outlets cover it, so news ties could draw well-covered places into the area in which coverage is then measured. The effect is small. Before whole towns are added, frequent coverage reaches 54%, 38% and 34% of the Columbia, Mexico and Linn areas with news ties, and 51%, 35% and 35% when the areas are drawn from residents' travel alone. Adding whole towns, which are covered more than the countryside around them, raises the shares to 60%, 44% and 41%. Resampling the month's stories 999 times, the frequent shares are 60% [59, 62], 44% [44, 44] and 41% [40, 44], and the balanced shares 56% [45, 56], 21% [19, 21] and 36% [33, 36]; the intervals hold the outlets and the month fixed, so they describe the sampling of stories alone. The thresholds move the shares little: frequent coverage at 6 or at 12 stories a month instead of 9 gives 61% or 59% for Columbia, 44% either way for Mexico and 44% or 40% for Linn; a balanced diet at 7 or at 9 categories instead of 8 gives 56% or 48%, 25% or 19%, and 36% or 35%.
