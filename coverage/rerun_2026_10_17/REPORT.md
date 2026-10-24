# Re-run of March 2026 enrichment: before and after

Written for: the authors. Enrichment re-run 2026-10-17 on #736-#739; spillover model refitted on the result.

## 1. What was re-run

| Set | Articles |
|---|---|
| Places re-run, Missouri | 2217 |
| Places re-run, Washington | 642 |
| March statewide stories | 1810 |
| March sports stories (home-team rule) | 1837 |
| All (deduplicated) | 6506 |

Changes carried by the re-run: the model is told where the publication is (#736); a game is centred on the publication's own team (#738); a statewide story is filed under its own state and scope-v3 keeps state-named places local (#738, #739); a long partial story is enriched rather than skipped, and the TownNews premium-content notice is removed (#739); 970 March bodies stored as ROT47 ciphertext were decoded (#736, #737).

## 2. Status

| before \ after | cleaned | enriched | enrichment_skipped | in_review | labeled | not_article | total |
|---|---|---|---|---|---|---|---|
| cleaned | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| enriched | 0 | 6401 | 34 | 31 | 6 | 0 | 6472 |
| not_article | 0 | 0 | 0 | 0 | 0 | 33 | 33 |
| total | 1 | 6401 | 34 | 31 | 6 | 33 | 6506 |

## 3. Scope

Unchanged 4666 of 6506; changed 1840.

| scope | before | after |
|---|---|---|
| city_municipality | 2234 | 3769 |
| statewide | 1965 | 1265 |
| regional | 1342 | 859 |
| neighborhood_community | 628 | 494 |
| national | 150 | 53 |
| other | 113 | 16 |
| elsewhere_to_local | 38 | 32 |
| local_to_elsewhere | 31 | 15 |
| international | 5 | 3 |

The 1810 March statewide stories now: statewide 1165, city_municipality 563, neighborhood_community 52, regional 28, elsewhere_to_local 1, other 1.

## 4. Story point

| Point | Articles |
|---|---|
| unchanged | 4423 |
| had none, now has one | 938 |
| had one, now none | 0 |
| moved within the same state | 809 |
| moved to another state | 336 |

| point level | before | after |
|---|---|---|
| place | 2614 | 3927 |
| state | 1969 | 1302 |
| none | 1847 | 909 |
| county | 69 | 362 |
| block | 7 | 6 |

Cross-state moves (first 30 of 336):

| Story | Before | After |
|---|---|---|
| Warsaw Police Officer Sensed Something Was Off, His Quick Reaction Saved A Life | Warsaw | Warsaw |
| Gofundme accused of deceptive practices by Oklahoma officials |  |  |
| Community unites at &quot;United We Feud&quot; fundraising event | Adams County | Adams |
| Kansas AG Kobach offers to delay enforcement of anti-trans law until March 26 |  |  |
| Incumbent Arkansas U.S. Senator Tom Cotton wins Republican nomination |  |  |
| Krishnamoorthi stops in Cairo on GOTV tour ahead of Illinois Senate primary |  |  |
| House Max accused of scamming Kansas homeowners in AG's lawsuit |  |  |
| Schools worry a Kansas bill would force them to hire more staff and care for fewer at-risk kids |  |  |
| Fire report for week of March 15 | Olympia | El Dorado Springs |
| Worth County Prom Saturday, March 28th | Worth County | Worth |
| HVAC unit suspected in Advance house fire contained to basement | Advance | Advance |
| Kansas Jayhawks, Bill Self arrive in San Diego for NCAA Tournament opener |  | San Diego |
| CHS Class of 1966 Plans Reunion | Clearwater | Piedmont |
| Washington teachers who lost their license for misconduct |  |  |
| Lenten Fish Fry | Lewis County | Lewis |
| County health department now administering naltrexone | Franklin County | Franklin |
| Ethics Complaints Against Piedmont Mayor, City Clerk Dismissed by State Commission | Piedmont | Piedmont |
| Reflections of the past | Dixie | Sikeston |
| Kansas House passes bill requiring jail without bond after 'serious' felony convictions |  |  |
| John Resman, Kansas state representative from Olathe, dead at age 70 |  | Olathe |
| K-State makes its move: Casey Alexander named 27th head men’s basketball coach |  | Manhattan |
| Kingsville baseball no-hits Santa Fe in opener | Kingsville | Kingsville |
| Reports: K-State hires Belmont’s Casey Alexander as new men’s hoops head coach |  | Manhattan |
| Kansas lawmakers mourn loss of Olathe Representative John Resman |  |  |
| ‘Good Morning America’ to visit Kansas Speedway to celebrate USA’s 250th birthday |  | Kansas City |
| 100 Games Won | Highland | Canton |
| Illinois bill combining home and car insurance regulation passes House, awaits Senate action |  |  |
| Kansas lawmakers want to require age verification on all phone application downloads |  |  |
| Land Transfers: March 3 - 6 | Elkhart | Nevada |
| God’s Squad on Running the Race at Sheridan Christian Church | Sheridan | Sheridan |

## 5. Place and county codes

| Codes | Articles with identical set | Before | After | Added | Removed | Outside publisher scope before | after |
|---|---|---|---|---|---|---|---|
| place | 3400 of 6506 | 13044 | 18912 | 6714 | 846 | 4404 | 5021 |
| county | 3386 of 6506 | 11675 | 17369 | 6470 | 776 | 4282 | 4883 |

Place rows: 29,776 before, 39,714 after. Articles with any place row: 4,295 before, 6,347 after.

## 6. Spillover model

|  | Before | After |
|---|---|---|
| Outlets fitted (well collected) | 70 | 87 |
| Counties | 39 | 47 |
| All outlets with 10+ placed stories | 128 | 133 |
| Held-out error (points) | 6.6 | 6.0 |
| broadcast (coef, p) | +0.86 (0.000) | +0.68 (0.000) |
| crowded_weekly (coef, p) | -0.42 (0.044) | -0.56 (0.008) |
| log_border_mi (coef, p) | -0.12 (0.003) | -0.14 (0.000) |
| log_print (coef, p) | -0.34 (0.001) | -0.28 (0.001) |

### The three counties and the Springfield area

| County | Before | After |
|---|---|---|
| Audrain | county 17% actual vs 22% expected (107 stories) | county 20% actual vs 23% expected (123 stories) |
| Boone | county 29% actual vs 25% expected (807 stories) | county 29% actual vs 24% expected (1152 stories) |
| Osage | county 26% actual vs 23% expected (40 stories) | county 26% actual vs 24% expected (40 stories) |
| Greene |  |  |
| Webster |  |  |
| Barry |  |  |

### Outlets whose spillover moved most (percentage points)

| Outlet | Stories before | after | Spillover before % | after % | change |
|---|---|---|---|---|---|
| Douglas County Herald | 19.0 | 20.0 | 21.0 | 34.0 | 12.7 |
| Columbia Missourian | 122.0 | 232.0 | 13.0 | 22.0 | 9.4 |
| The Platte County Citizen | 18.0 | 26.0 | 33.0 | 27.0 | -6.4 |
| KC Beacon | 28.0 | 39.0 | 16.0 | 22.0 | 6.4 |
| Sheridan Express | 41.0 | 52.0 | 38.0 | 45.0 | 6.3 |
| KQTV | 177.0 | 227.0 | 25.0 | 31.0 | 6.2 |
| Columbia Daily Tribune | 33.0 | 86.0 | 11.0 | 17.0 | 6.0 |
| Bethany Republican Clipper | 38.0 | 50.0 | 11.0 | 16.0 | 5.5 |
| The Prospect News | 53.0 | 65.0 | 15.0 | 20.0 | 5.4 |
| Southeast Missourian | 78.0 | 86.0 | 25.0 | 31.0 | 5.2 |
| Daily American Republic | 46.0 | 55.0 | 16.0 | 21.0 | 5.1 |
| KBIA | 23.0 | 41.0 | 22.0 | 27.0 | 5.1 |
| Pemiscot Press | 58.0 | 74.0 | 14.0 | 19.0 | 5.0 |
| Boone County Journal | 106.0 | 138.0 | 10.0 | 15.0 | 5.0 |
| St. Louis American | 94.0 | 107.0 | 10.0 | 14.0 | 4.9 |
| STL Public Radio | 94.0 | 130.0 | 21.0 | 26.0 | 4.9 |
| Carthage News Online | 19.0 | 23.0 | 16.0 | 21.0 | 4.9 |
| Greene County Commonwealth | 23.0 | 27.0 | 76.0 | 71.0 | -4.8 |
| Kirksville Daily Express | 136.0 | 157.0 | 19.0 | 24.0 | 4.4 |
| Missourian | 170.0 | 197.0 | 15.0 | 20.0 | 4.4 |

Quality set: 14 outlets newly well collected (Citizen Observer, Columbia Daily Tribune, Columbia Missourian, El Dorado Springs Sun, KBIA, Memphis Democrat, Perryville Republic Monitor, Reynolds County Courier/Wayne County Journal Banner, Richmond Daily News, Shelby County Herald, Sheridan Express, The Arrow, The Kansas City Globe, The Nevada Daily Mail); 0 no longer (none).

### Volume floor for the fit (2026-10-17 snapshot and model; current comparison: spillover_outlets.py)

| Volume floor (placed stories) | Outlets fitted | Counties | Held-out mean miss | median |
|---|---|---|---|---|
| 10.0 | 97.0 | 52.0 | 6.5 | 5.9 |
| 20.0 | 87.0 | 47.0 | 6.48 | 5.31 |
