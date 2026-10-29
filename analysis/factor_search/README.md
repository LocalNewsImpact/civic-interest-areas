# Factors tested and not adopted

The article's Methods: "we tested more than a hundred factors in models of travel and coverage between counties, from
county size to business activity and hospital availability. None of these factors reliably improved predictions." These
scripts are those tests. Each adds candidate terms to an adopted model (`analysis/travel_model.py`,
`analysis/coverage_model.py`, `analysis/spillover_outlets.py`, or the crossover regression) and scores it on counties
the model was not fitted on. A term is adopted only if its held-out gain has a 95% interval excluding zero under the
nested procedure (the search repeated inside each training set); none passes.

Run them with `STAGES=factors zsh scripts/reproduce.sh`, after the `data`, `travel`, `coverage` and `spillover` stages.
The block tests of the adopted travel terms (`analysis/travel_model_dc_test.py selection`) run in the same stage.

| Script | Test |
|---|---|
| `combined_marginal_test.py` | Nested guard over the 24 exploratory travel candidates (`travel_nested_all`); every rejected factor added at once, travel and coverage |
| `combined_all_factors_test.py` | Every factor that showed a small effect anywhere, added together; destination factors in place of destination effects |
| `civic_variables_test.py` | 24 ACS county measures (age, income, education, broadband, commuting time and others): crossover, spillover, travel |
| `civic_index_test.py`, `civic_index_test_v2.py` | Civic Information Index 2026 indicators: crossover, spillover |
| `business_dynamics_test.py` | Census Business Dynamics Statistics (openings, closings, turnover): crossover, spillover |
| `hospital_test.py` | Hospitals (`build_hospitals.py`): crossover, spillover, travel, coverage |
| `spillover_bylines_test.py` | Newsroom size (distinct bylines) and volume: spillover |
| `spillover_rule_selection.py`, `spillover_nested_selection.py` | Exploratory spillover terms through the nested guard; the nested search that found the adopted terms |
| `spillover_side_tests.py` | Outlet frequency and type terms on the adopted spillover model |
| `coverage_saturation_test.py` | Coverage saturation: less coverage where the destination already has its own |
| `coverage_newsroom_size_test.py` | Rurality against newsroom size and outlet type in the coverage model |
| `travel_model_compare.py` | Stores, jobs, borders and rural origins in a singly-constrained gravity model |
| `travel_distance_spline.py` | Distance as a restricted cubic spline in place of the quadratic |
| `travel_distance_variants.py` | Distance between job centres and population centres |
| `travel_model_drive_test.py` | Driving time and "on the way" (`build_drive_routes.py`) |
| `travel_commute_pair_test.py` | Pair-level commuting flows |
| `travel_competing_test.py` | Competing destinations |
| `travel_model_hub_test.py` | Regional-centre factor |
| `travel_business_test.py` | Business activity (County Business Patterns sectors) as the non-work pull |
| `travel_purpose_split_test.py` | Work and non-work travel modelled separately (`build_statewide_od_purpose.py`) |
| `travel_small_origin_model.py`, `travel_small_county_test.py` | Separate models and theory-based terms for small counties |
| `travel_blend_test.py` | Observed travel blended with the model by sample size |
