# Supplementary material

Supplement to "Beyond Counties: Mapping Civic Interest Areas" (manuscript under review). Copied from the manuscript on 2026-11-08; the manuscript is the authority where the two differ. `RESULTS.md` names the script that prints each value.

## S1. Spillover under other weights

Table 1's weights are definitions, not estimates. The table gives each county's spillover when a mention counts 0.25, 0.5 or 1 of a story and a sports story 0, 0.5 or 1 of its usual weight, with the spillover model refitted on the same 85 outlets. Skill is 1 − MAE<sub>model</sub> ÷ MAE<sub>mean</sub>, where MAE<sub>model</sub> is the mean absolute error, in percentage points, of each outlet's predicted spillover when its county is left out of the fit, and MAE<sub>mean</sub> is that of predicting every outlet at the average rate. Audrain's spillover depends most on the sports weight: much of its coverage of other counties is high school sports.

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

Each measure is set out below: the question it answers, the calculation, its terms with fitted values, and its output. Fitted values are shown with standard errors in parentheses or 95% intervals in brackets. Results are reported for Audrain, Boone and Osage counties. Stories: March 2026. Commuting: LODES 2023.

**Outlets.** Two analyses use only outlets whose March 2026 collection met a standard: at least 95% of stories had body text, 80% were full length, and 60%, at least 20, could be geolocated. The spillover model is fitted on the 85 outlets in 48 counties that meet it. The correlation between crossover and spillover uses the 47 of those counties with a print or digital outlet. Every other analysis uses every local outlet (except statewide outlets and student newspapers) including the county spillover figures in Table 2, the coverage model, the news ties in the civic interest areas, and coverage density and balance. In the county spillover figures, an outlet counts if it has 10 or more geolocated stories. Three of the ten outlets in the study counties miss the standard: the *Centralia Fireside Guard*, the *Vandalia Leader* and *The Unterrified Democrat*. *The Unterrified Democrat* is Osage County’s only outlet, so Osage’s spillover is reported, but Osage is not one of the counties the model is fitted on.

**Mobility data.** For each month, Advan Neighborhood Patterns Plus reports how many distinct devices from each home block group were seen in each block group, its own included. A device seen there more than once in the month counts once. A visit is one such device, scaled to a resident: one resident seen in one block group in one month. A resident seen in three block groups of a county makes three visits there. Crossover therefore counts, for each home block group, only its single busiest block group outside the county (B). The three measures use the counts differently. Travel (A) divides each month’s devices by the statewide devices per resident and sums the nine months. Crossover (B) is a ratio of two device counts, so it needs no scaling, and is averaged over the months. Civic interest areas (E) take, for each home block group and place, the devices seen in the place’s busiest block group divided by the devices seen at home, average that share over the nine months, and multiply by the block group’s population. Advan reports August and September on 2010 block groups. We restate them on 2020 block groups by splitting each 2010 block group among the 2020 block groups it overlaps, in proportion to the 2020 population of the blocks they share (U.S. Census Bureau, 2021b, 2021d).

### A. Travel: where each county's residents go

**Question.** How many visits would residents of county i be expected to make to county j, given distance, a shared border and commuting?

E[V<sub>ij</sub>] = exp(α<sub>i</sub> + γ<sub>j</sub> + β<sub>1</sub>D<sub>ij</sub> + β<sub>2</sub>D<sub>ij</sub><sup>2</sup> + R<sub>i</sub>(β<sub>3</sub>D<sub>ij</sub> + β<sub>4</sub>D<sub>ij</sub><sup>2</sup>) + β<sub>5</sub>P<sub>i</sub>D<sub>ij</sub> + β<sub>6</sub>B<sub>ij</sub> + β<sub>7</sub>C<sub>ij</sub> + β<sub>8</sub>C<sub>ji</sub>)

**Estimation.** Poisson pseudo-maximum likelihood over all 13,110 ordered pairs of 115 counties, pairs with no visits kept; standard errors clustered by home and by destination county. Held-out scores split the home counties into 8 groups; each group's destination shares are predicted from a fit to the other seven. A home county's effect α<sub>i</sub> cancels when its visits are expressed as shares, and each γ<sub>j</sub> is estimated from the other home counties.

**Terms.** V<sub>ij</sub>: visits by residents of county i to county j (Mobility data), with highway pass-through stops removed. α<sub>i</sub>, γ<sub>j</sub>: overall travel from county i and overall draw of county j (one fixed effect per county). D<sub>ij</sub>: ln(miles between the 2020 population centers (U.S. Census Bureau, 2021a) ÷ 25). R<sub>i</sub>: 1 if county i is rural (under half its 2020 population in Census urban areas). P<sub>i</sub>: ln population of county i, centered (ACS 2020–2024). B<sub>ij</sub>: 1 if the counties share a border. C<sub>ij</sub>: ln(1 + workers living in i who work in j, per 1,000 workers living in i).

**Fitted values.** β<sub>1</sub> −0.88 (0.13), the distance elasticity at 25 miles for an urban home county; β<sub>2</sub> −0.26 (0.03); β<sub>3</sub> 0.18 (0.12); β<sub>4</sub> −0.21 (0.05); β<sub>5</sub> 0.13 (0.03); β<sub>6</sub> 0.44 (0.07); β<sub>7</sub> 0.28 (0.05); β<sub>8</sub> 0.19 (0.04).

**Output.** Expected visits for every county pair. Predicting each county without its own data, the model accounts for 93.7% [92.4, 94.8] of the variation in travel shares, with a share-weighted error of 3.28 percentage points; the terms were chosen on the same held-out groups, so this is an in-selection score. On the same basis, with its setting chosen on all the counties of a class, the public-data model's error is 4.4 points (Methods); with the choice repeated without the county scored it is 4.6, and the difference from the Advan-fitted model is 1.3 points [0.8, 1.8]. At 25 miles, the distance elasticity of visits is −0.88 for an urban home county and −0.70 for a rural one (β<sub>1</sub> and β<sub>1</sub> + β<sub>3</sub>; the difference, β<sub>3</sub>, is not distinguishable from zero); with the quadratic terms, going from 25 to 50 miles leaves 48% of the visits from an urban county and 49% from a rural one.

### B. Crossover: how many of a county's residents go elsewhere

**Question.** What share of a county's residents is seen outside the county in a month?

crossover<sub>c</sub> = Σ<sub>h∈c</sub> min(L<sub>h</sub>, D<sub>h</sub>) ÷ Σ<sub>h∈c</sub> D<sub>h</sub>,  where D<sub>h</sub> = E<sub>h</sub><sup>b</sup> S<sub>h</sub><sup>1−b</sup>

**Estimation.** b is estimated by two-stage least squares across months: a block group's log rate of leaving on its log detection ratio S<sub>h</sub>/E<sub>h</sub>, instrumented by the same ratio in another month (county-clustered first-stage F = 4,082). Identification rests on the extra devices seen at home not being seen away from it: they raise S<sub>h</sub> without raising L<sub>h</sub>. Another month's ratio is used because the same month's ratio and the leaving rate both contain S<sub>h</sub>, which would tie them together mechanically; a different month breaks that tie and averages out month-to-month noise in detection. What it cannot do is separate extra devices from residents who simply stay home more: both raise detection at home and lower leaving in every month, so b is, if anything, too high. b is 0.61 to 0.63 whichever month supplies the instrument.

**Terms.** L<sub>h</sub>: devices from home block group h seen in their busiest block group outside the county, a lower bound on residents who left. S<sub>h</sub>: devices from h seen at home, inflated where homes are over-detected. E<sub>h</sub>: devices expected from h, its ACS 2020–2024 population × the month’s Missouri devices per resident. All three are device counts, so crossover, their ratio, needs no conversion to people. b: how far the denominator moves from residents seen at home toward the expected population, on a log scale (ln D<sub>h</sub> = b ln E<sub>h</sub> + (1 − b) ln S<sub>h</sub>): b = 1 if the extra devices seen at home never leave, b = 0 if they leave as residents do.

**Fitted value.** b = 0.62 [0.53, 0.71].

**Output.** Share of residents seen outside the county in a typical month, January–September 2026: Audrain 44%, Boone 26%, Osage 59%. These shares depend little on b: over its 95% interval they move by less than a point in Audrain and Boone and by 3.5 points in Osage, and over the whole range of b from 0 to 1 they are 40–44%, 24–26% and 45–66%. Counting a resident in every destination visited, rather than once, gives an upper bound of 66%, 33% and 82%. These ranges reflect the choice of b and of the count, not sampling: the panel is not a probability sample of residents, so no sampling interval is given.

### C. Coverage: which counties each county's newsrooms cover

**Question.** How many stories would county k's newsrooms be expected to write about county j, given geography and residents' travel there?

E[S<sub>kj</sub>] = exp(ν<sub>k</sub> + μ<sub>j</sub> + θ<sup>⊤</sup>X<sub>kj</sub> + β<sub>1</sub>ℓ<sub>kj</sub> + β<sub>2</sub>R<sub>k</sub>ℓ<sub>kj</sub> + β<sub>3</sub>Z<sub>kj</sub>)

ℓ<sub>kj</sub> = ln V<sub>kj</sub> if V<sub>kj</sub> > 0, otherwise 0;  Z<sub>kj</sub> = 1 if V<sub>kj</sub> = 0, otherwise 0

**Estimation.** Poisson pseudo-maximum likelihood over every newsroom county k and other county j (88 newsroom counties × 114 other counties, 10,032 pairs; 14,877 stories, 10,282 of their story–county pairs outside the newsroom's county; 81% of pairs have no stories, 39% among pairs holding 1% or more of the newsroom county's visits), pairs with no stories kept; standard errors clustered by newsroom county (88 clusters); clustered by unordered county pair, the standard errors of the urban and rural elasticities are 0.052 and 0.049 against 0.069 and 0.059, and clustered two-way by newsroom county and county covered, 0.076 and 0.068; no conclusion changes. Travel spans January–September 2026 and includes the month of the stories, so the model measures association, not the direction of influence between travel and coverage.

**Terms.** S<sub>kj</sub>: stories by newsrooms in county k centered in or naming county j, March 2026. ν<sub>k</sub>, μ<sub>j</sub>: the output of k's newsrooms and how much j is covered by newsrooms anywhere (fixed effects). X<sub>kj</sub>: the distance, border and commuting terms of A. V<sub>kj</sub>: residents' visits from k to j, as in A. R<sub>k</sub>: 1 if the newsroom county is rural, as in A. Z<sub>kj</sub>: 1 if no visit was recorded.

**Fitted values.** β<sub>1</sub> 0.47 (0.069), the elasticity of stories to visits for urban newsroom counties; β<sub>2</sub> −0.23 (0.047), the difference for rural newsroom counties; β<sub>1</sub> + β<sub>2</sub> 0.24 (0.059), the elasticity for rural newsroom counties; β<sub>3</sub> −0.38 (0.62); θ: ln distance −0.73 (0.29), its square 0.21 (0.06), rural × ln distance 0.24 (0.26), rural × its square −0.37 (0.13), ln population × ln distance 0.15 (0.04), shared border −0.17 (0.09), commuting out −0.02 (0.09), commuting in 0.42 (0.07). Fitted against observed stories across pairs, r² 0.97.

**Output.** Expected stories for every pair. Twice the visits: 1.38 [1.26, 1.52] times the stories from urban newsrooms, 1.18 [1.09, 1.28] times from rural ones. Held-out error on destinations with 1% or more of the visits: 4.54 [4.09, 5.04] percentage points. Without the rural term β<sub>2</sub>, held-out error rises to 4.67: the term lowers it by 0.13 [0.05, 0.21] points (newsroom counties resampled in pairs, 1,000 draws). Leaving out one newsroom county at a time, the urban elasticity stays between 0.42 and 0.51 and the rural between 0.21 and 0.28.

### D. Spillover: how much of an outlet's news is about another county

**Question.** What share of an outlet's stories would be expected to be about other counties?

E[y<sub>o</sub>] = 1 ÷ (1 + exp(−z<sub>o</sub>)),  where z<sub>o</sub> = β<sub>0</sub> + β<sub>1</sub>T<sub>o</sub> + β<sub>2</sub> ln(1 + N<sub>o</sub>)

**Estimation.** The model is a fractional logistic regression fitted on the 85 outlets that meet the collection standard (S2, Outlets). Standard errors are clustered by county with the cluster jackknife (CRV3). The model has no county effect, because N<sub>o</sub> varies only between counties and a county effect would absorb it. Outlets that meet the standard spill over more than those that do not (24.7% against 18.7%), so the fitted values describe well-collected outlets.

**Terms.** y<sub>o</sub>: outlet o's spillover, March 2026, weighted as in Table 1. T<sub>o</sub>: 1 if the outlet is a television or radio broadcaster. N<sub>o</sub>: print and digital news outlets active in the outlet's county.

**Example.** KOMU published 327 geolocated stories in March 2026. Eighty-five were centered in another county and count 1 each. Five more were sports stories centered in another county and count 0.5 each. Fifty-nine were centered in Boone County, or had no center, and mentioned at least one other county; each counts 0.5 whatever the number of counties mentioned. Four were sports stories that mentioned another county and count 0.25 each. The remaining 174 were about the home county only and count 0. The weighted count, 118, divided by all 327 stories gives a spillover of 36%. Stories with no central place and stories centered out of state beyond 60 miles stay in the denominator and count 0 unless they mention another county.

**Fitted values.** β<sub>0</sub> −0.81 (0.13); β<sub>1</sub> 0.67 (0.15), p < 0.001; β<sub>2</sub> −0.39 (0.12), p = 0.003 (t with 47 degrees of freedom).

**Output.** The model gives an expected spillover for each outlet. A county's expected spillover is the average of its outlets' expectations, weighted by their stories. The held-out error is 5.98 percentage points: each county's outlets are predicted by a model fitted without that county, and the prediction misses an outlet's spillover by 5.98 points on average. Predicting every outlet at the average rate misses by 7.49 points, so the model's skill is 0.20 (as in Table S1). When the choice of terms is also repeated within each held-out group, the error is 6.57 points. Neither term depends on any one outlet: refitted without each outlet in turn, the broadcaster term stays between 0.62 and 0.74 and the outlet term between −0.43 and −0.36. County spillover, with 95% intervals from resampling each outlet's stories 9,999 times, is 20% [16, 23] in Audrain, 29% [27, 31] in Boone (18% [16, 20] for its print and digital outlets) and 26% [17, 35] in Osage. Crossover is 2.3 times spillover in Audrain [1.9, 2.7] and in Osage [1.6, 3.6]; these intervals also allow for the 95% interval of b.

### E. Civic interest area: the places a town's residents share

**Question.** Which places belong to a town's civic interest area, and how likely is each?

R<sub>hx</sub> ≈ Σ<sub>k=1</sub><sup>K</sup> W<sub>hk</sub>H<sub>kx</sub>

T<sub>x</sub> = min(0.99, t · s<sub>x</sub> · U<sub>x</sub>)

a<sub>x</sub> = min(0.99, T<sub>x</sub>(1 + ω(0.3O<sub>x</sub> + 0.3I<sub>x</sub> + g<sub>x</sub>(0.7P<sub>x</sub> + 0.7Q<sub>x</sub>)))),  g<sub>x</sub> = 1 if O<sub>x</sub> + I<sub>x</sub> ≥ 0.10, otherwise 0

τ<sub>x</sub> = 100 · min(0.99, (a<sub>x</sub> + λL<sub>x</sub>)(1 + 0.5ρ cos(θ<sub>x</sub> − θ̄)));  τ<sub>x</sub> = 100 in the home town

p<sub>x</sub> = (1 ÷ 6,912) Σ<sub>s</sub> f<sub>s</sub>(x)

**Estimation.** Non-negative matrix factorization (Lee & Seung, 1999; multiplicative updates, Lee & Seung, 2001) of block-group travel in the Columbia–Jefferson City television market; the map drawn in 6,912 equally weighted versions (Steegen et al., 2016).

**Terms: travel patterns.** R<sub>hx</sub>: share of block group h's residents seen at place x (Mobility data). W<sub>hk</sub>: h's weight on travel pattern k. H<sub>kx</sub>: pattern k's reach to x. n<sub>h</sub>: h's population (ACS 2020–2024). m<sub>hk</sub>: share of h's residents assigned to pattern k, equal to the share of h's travel the pattern carries, W<sub>hk</sub> Σ<sub>x</sub> H<sub>kx</sub> ÷ Σ<sub>k</sub> W<sub>hk</sub> Σ<sub>x</sub> H<sub>kx</sub>. A pattern's residents are Σ<sub>h</sub> n<sub>h</sub> m<sub>hk</sub>. Each block group's shares sum to 1, so every resident is counted once. The data describe block groups, not people, so this assumes a block group's residents divide among patterns as its travel does. A town's residents live in the block groups with at least half of their 2020 population inside the town (U.S. Census Bureau, 2021b, 2021c). These are 89 block groups in Columbia, 13 in Mexico and 1 in Linn, holding 96%, 99% and 93% of each town's population. Linn is smaller than its block group, so its residents include people in the countryside around it. K: the number of patterns, 2. It is the largest number at which every pattern holds at least 10% of a town's residents and 10% of that town's travel, holds at least 1,000 people (half the residents of a town under 2,000), and reappears from 10 random starts and in fits to odd and to even months. Columbia and Linn have one pattern each and Mexico two. A town's largest pattern is always drawn. The month test, not the population floor, rules out a third pattern.

**Terms: ties.** U<sub>x</sub>: the town's travel to hexagon x, Σ<sub>h</sub> n<sub>h</sub> W<sub>hk*</sub> H<sub>k*x</sub> over the town's block groups, where k* is the pattern drawn, scaled so the busiest place is 1. A hexagon belongs to the place that holds its center. t: 0.5 or 1, so the busiest place scores 50 or 100 (the home town scores 100). s<sub>x</sub>: x's weight within its place (Definitions). O<sub>x</sub>: the town's outlets' coverage located at x relative to their coverage of the town, at most 1. I<sub>x</sub>: x's outlets' share of coverage in the town's county relative to the town's own outlets' share, at most 1. P<sub>x</sub>: overlap between the places the town's residents visit and the places x's outlets cover. Q<sub>x</sub>: overlap between the places the town's outlets cover and the places x's outlets cover (Definitions). g<sub>x</sub>: ties through shared places count only where a direct tie, O<sub>x</sub> + I<sub>x</sub>, reaches 0.10. ω: weight on news ties, 0, ½, 1 or 2. The weights 0.3, 0.3, 0.7 and 0.7 are set by judgment (Table S2) and sum to 2, so news ties can at most triple a travel tie at ω = 1 and multiply it by five at ω = 2, within the cap of 0.99. L<sub>x</sub>: mean of a over rings about 1.6, 3.2 and 4.8 miles from x, weighted ½, ¼ and ⅛, with untied hexagons counted as 0. It is added only to hexagons with a tie. λ: 0, 0.25 or 0.5. θ<sub>x</sub>: bearing of x from the mean center of the home town's hexagons. θ̄ and ρ: the direction and strength (0 to 1) of the town's ties outside home, from the mean unit vector of the bearings of tied hexagons outside home, weighted by smoothed tie. Ties below 1 are dropped.

**Terms: versions.** f<sub>s</sub>(x): share of x's area inside the area drawn by version s, with the 1.0- and 4.0-square-mile grids mapped onto the 2.3-square-mile grid. D<sub>90</sub>: the regular-travel distance, within which lies 90% of residents' travel to places visited in every month, January–September 2026: Columbia 15 miles, Mexico 30, Linn 44.

**Drawing choices.** The 6,912 versions combine seven drawing choices and ω, levels in parentheses: shexagons of about 1.0, 2.3 or 4.0 square miles (3); t (2); spread of travel within places, off or at three strengths (4); λ (3); selectivity, the drawn hexagons holding 40, 50 or 60% of the town's ties outside home (3); a distance rule, on or off (2); reach, joining separate pieces within 6, 9 or 16 miles or within D<sub>90</sub> (4); ω (4): 3 × 2 × 4 × 3 × 3 × 2 × 4 × 4 = 6,912.

**Definitions.** Spread (s<sub>x</sub>): within a rural block group, (OpenStreetMap destinations in x + c) ÷ the block group's mean of the same, so the weights average 1; within a town of two or more hexagons, half that and half x's 2020 population ÷ the town's mean; c = 0.1, 0.25 or 1, or no spread. Overlap (P<sub>x</sub>, Q<sub>x</sub>): Σ<sub>u</sub> min(π<sub>u</sub> ÷ Σπ, σ<sub>u</sub> ÷ Σσ) over places u other than the town's own and x; for P<sub>x</sub>, π is the town's travel by place and σ the stories x's outlets locate in each place (Table 1 weights; statewide and wider stories locate nothing); for Q<sub>x</sub>, π and σ are the stories the town's outlets and x's outlets locate, over places holding at least 5% of the town's busiest-place travel. Distance rule: a hexagon not contiguous with the area's body needs a tie of v + v × min(1, d ÷ r) rather than v, where v is the tie at which the strongest hexagons hold the selectivity share of the town's ties outside home (at least 5; the raised floor at least 10), d is the hexagon's distance from the body and r is 6.5 miles inside the television market and 3.2 miles outside; the body grows from home until no further hexagon qualifies.

**Output.** p<sub>x</sub>, how likely each place is to be part of the area. The area is every place with p<sub>x</sub> ≥ 0.5 that is joined to the town or lies within D<sub>90</sub> of it, together with every town that at least half of the versions include in part, taken whole.

**Sensitivity.** Halving or doubling the constants set by judgment (the weights on direct news ties and on ties through shared places, and the strength of the direction term, 0.5) keeps 93% to 100% of each area's places and changes frequent coverage by at most six percentage points (Table S2).

**Table S2. Civic interest areas with the constants set by judgment halved or doubled.**

| Constant | Value | Places kept |  |  |  | Frequent coverage |  |  |  |
|---|---|---|---|---|---|---|---|---|---|
|  |  | Columbia | Mexico | Mexico, second area | Linn | Columbia | Mexico | Mexico, second area | Linn |
| As adopted | 0.3, 0.7, 0.5 | 100% | 100% | 100% | 100% | 56% | 34% | 98% | 40% |
| Direct news ties | 0.15 | 100% | 100% | 100% | 100% | 56% | 34% | 98% | 41% |
| Direct news ties | 0.6 | 100% | 100% | 100% | 98% | 56% | 34% | 98% | 41% |
| Ties through shared places | 0.35 | 100% | 100% | 100% | 100% | 56% | 34% | 98% | 40% |
| Ties through shared places | 1.4 | 98% | 94% | 100% | 99% | 57% | 36% | 98% | 41% |
| Direction strength | 0.25 | 100% | 100% | 93% | 100% | 56% | 34% | 100% | 39% |
| Direction strength | 1.0 | 97% | 99% | 100% | 96% | 57% | 34% | 92% | 41% |

## S3. Coverage density and balance

Each story is placed by its geolocated central point and its geographic scope, as classified by Backfield (Davis, 2026). A story is mapped to an area set by its scope: a neighborhood story to the 2 miles around its point; a town story to the town's 2020 boundary and the 2 miles around it (3 miles around a point outside any town); a regional story to the 25 miles around its point; and a story located only at the county level to the whole county. Statewide, national and international stories, and their mentions, are not mapped. A hexagon lies in a story's area when its center does.

A story counts 1 where it is centered and 0.5 for each place or county it mentions, unlike spillover, which counts a story once; a named town stands for the town and the 2 miles around it, a named county for the county. Sports stories count half, as in the spillover measure.

The weight a story gives each hexagon depends on the size of the area it is mapped to. A town or neighborhood story gives each hexagon of its area w × min(1, (7 ÷ A)<sup>½</sup>), where w is the story's weight and A the number of hexagons its area covers on the 2.3-square-mile grid: full weight up to seven hexagons, about 16 square miles (a neighborhood, or a town the size of Linn), less beyond. A county or regional story gives its area, in total, the weight of seven fully covered hexagons (7w), spread in proportion to where people live (2020 block-group population) and at most w on any one hexagon. The wider a story’s scope, the less it concerns any one place within it, so its weight per hexagon falls: a town story over 28 hexagons contributes 14 units in all, a county story over the same 28 contributes 7. A hexagon takes a story's strongest claim.

Coverage density is the sum of these weights over the month. A hexagon is frequently covered at 9 or more stories a month (about two a week), regularly covered at 2 to 8 and infrequently covered below 2. No hexagon in the three areas goes without coverage: each lies in a county with county-level stories. A hexagon has a balanced diet when at least 8 of the 10 CIN categories each reach one story a month.

Coverage density and balance are measured on the civic interest area as mapped: every hexagon the maps show, including towns counted whole. Part of a place's news tie is how much the home town's outlets cover it, so news ties could draw well-covered places into the area in which coverage is then measured. The effect is small. Before whole towns are added, frequent coverage reaches 50%, 30% and 30% of the Columbia, Mexico and Linn areas with news ties, and 50%, 27% and 31% when the areas are drawn from residents' travel alone. Adding whole towns, which are covered more than the countryside around them, raises the shares to 56%, 34% and 40%. Resampling the month's stories 999 times, the frequent shares are 56% [55, 58], 34% [34, 34] and 40% [40, 43], and the balanced shares 52% [42, 52], 15% [14, 16] and 35% [33, 35]; the intervals hold the outlets and the month fixed, so they describe the sampling of stories alone. The thresholds move the shares little: frequent coverage at 6 or at 12 stories a month instead of 9 gives 57% or 55% for Columbia, 34% at both for Mexico and 43% or 40% for Linn; a balanced diet at 7 or at 9 categories instead of 8 gives 52% or 45%, 18% or 14%, and 35% or 34%. Mexico's second area is frequently covered in 98% of its area under every threshold and draw, and its balanced share is 61% [61, 63].

**References**

Lee, D. D., & Seung, H. S. (2001). Algorithms for non-negative matrix factorization. In T. K. Leen, T. G. Dietterich, & V. Tresp (Eds.), *Advances in Neural Information Processing Systems 13* (pp. 556–562). MIT Press. https://proceedings.neurips.cc/paper/2000/hash/f9d1152547c0bde01830b7e8bd60024c-Abstract.html

Steegen, S., Tuerlinckx, F., Gelman, A., & Vanpaemel, W. (2016). Increasing transparency through a multiverse analysis. *Perspectives on Psychological Science, 11*(5), 702–712. https://doi.org/10.1177/1745691616658637

U.S. Census Bureau. (2021a). *Centers of population: 2020 Census* [Data set]. https://www.census.gov/geographies/reference-files/time-series/geo/centers-population.html

U.S. Census Bureau. (2021b). *2020 Census redistricting data (Public Law 94-171) summary file: Table P1, total population, census blocks* [Data set]. https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html

U.S. Census Bureau. (2021c). *Block assignment files: 2020 Census, incorporated places and census designated places, Missouri* [Data set]. https://www.census.gov/geographies/reference-files/time-series/geo/block-assignment-files.html

U.S. Census Bureau. (2021d). *2010 Census tabulation block to 2020 Census tabulation block relationship file, Missouri* [Data set]. https://www.census.gov/geographies/reference-files/time-series/geo/relationship-files.2020.html
