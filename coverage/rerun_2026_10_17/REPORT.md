# Re-run of March 2026 enrichment: before and after

Missouri articles. Enrichment re-run 2026-10-17 on #736-#739; spillover model refitted on the result.

## 1. What was re-run

| Set | Articles |
|---|---|
| Places re-run, Missouri | 2217 |
| March statewide stories | 1810 |
| March sports stories (home-team rule) | 1837 |
| All (deduplicated) | 5864 |

Changes carried by the re-run: the model is told where the publication is (#736); a game is centred on the publication's own team (#738); a statewide story is filed under its own state and scope-v3 keeps state-named places local (#738, #739); a long partial story is enriched rather than skipped, and the TownNews premium-content notice is removed (#739); 970 March bodies stored as ROT47 ciphertext were decoded (#736, #737).

## 2. Status

| before \ after | cleaned | enriched | enrichment_skipped | in_review | labeled | not_article | total |
|---|---|---|---|---|---|---|---|
| cleaned | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| enriched | 0 | 5759 | 34 | 31 | 6 | 0 | 5830 |
| not_article | 0 | 0 | 0 | 0 | 0 | 33 | 33 |
| total | 1 | 5759 | 34 | 31 | 6 | 33 | 5864 |

## 3. Scope

Unchanged 4130 of 5864; changed 1734.

| scope | before | after |
|---|---|---|
| city_municipality | 2034 | 3513 |
| statewide | 1878 | 1179 |
| regional | 1080 | 620 |
| neighborhood_community | 610 | 480 |
| national | 116 | 32 |
| other | 106 | 14 |
| local_to_elsewhere | 26 | 14 |
| elsewhere_to_local | 11 | 9 |
| international | 3 | 3 |

The 1810 March statewide stories now: statewide 1165, city_municipality 563, neighborhood_community 52, regional 28, elsewhere_to_local 1, other 1.

## 4. Story point

| Point | Articles |
|---|---|
| unchanged | 3862 |
| had none, now has one | 885 |
| had one, now none | 0 |
| moved within the same state | 795 |
| moved to another state | 322 |

| point level | before | after |
|---|---|---|
| place | 2400 | 3671 |
| state | 1878 | 1211 |
| none | 1522 | 637 |
| county | 57 | 339 |
| block | 7 | 6 |

## 5. Place and county codes

| Codes | Articles with identical set | Before | After | Added | Removed | Outside publisher scope before | after |
|---|---|---|---|---|---|---|---|
| place | 2926 of 5864 | 10720 | 16658 | 6647 | 709 | 3491 | 4202 |
| county | 2894 of 5864 | 9651 | 15408 | 6412 | 655 | 3403 | 4095 |

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

### The three counties

| County | Before | After |
|---|---|---|
| Audrain | county 17% actual vs 22% expected (107 stories) | county 20% actual vs 23% expected (123 stories) |
| Boone | county 29% actual vs 25% expected (807 stories) | county 29% actual vs 24% expected (1152 stories) |
| Osage | county 26% actual vs 23% expected (40 stories) | county 26% actual vs 24% expected (40 stories) |

### Outlets of the three counties, largest change first (percentage points)

| Outlet | Stories before | after | Spillover before % | after % | change |
|---|---|---|---|---|---|
| Columbia Missourian | 122.0 | 232.0 | 13.0 | 22.0 | 9.4 |
| Columbia Daily Tribune | 33.0 | 86.0 | 11.0 | 17.0 | 6.0 |
| KBIA | 23.0 | 41.0 | 22.0 | 27.0 | 5.1 |
| Boone County Journal | 106.0 | 138.0 | 10.0 | 15.0 | 5.0 |
| ABC 17 KMIZ News | 240.0 | 308.0 | 41.0 | 37.0 | -3.7 |
| The Mexico Ledger | 90.0 | 105.0 | 19.0 | 22.0 | 2.7 |
| KOMU | 263.0 | 327.0 | 38.0 | 36.0 | -1.6 |
| Vandalia Leader | 17.0 | 18.0 | 4.0 | 4.0 | -0.2 |
| Centralia Fireside Guard | 20.0 | 20.0 | 5.0 | 5.0 | 0.0 |
| The Unterrified Democrat | 40.0 | 40.0 | 26.0 | 26.0 | 0.0 |

Quality set: 14 outlets newly well collected, of them in the three counties: Columbia Daily Tribune, Columbia Missourian, KBIA; 0 no longer, of them in the three counties: none.

### Volume floor for the fit (2026-10-17 snapshot and model; current comparison: spillover_outlets.py)

| Volume floor (placed stories) | Outlets fitted | Counties | Held-out mean miss | median |
|---|---|---|---|---|
| 10.0 | 97.0 | 52.0 | 6.5 | 5.9 |
| 20.0 | 87.0 | 47.0 | 6.48 | 5.31 |
