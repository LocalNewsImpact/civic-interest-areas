#!/bin/zsh
# Rebuilds every result in MODEL_CHANGES.md "Current results", in dependency order.
#
#   zsh scripts/reproduce.sh                    # every stage
#   STAGES="travel coverage" zsh scripts/reproduce.sh
#
# Stages: data travel coverage spillover public areas qa figures. Logs: logs/reproduce/<step>.log.
# Requires the Python environment in requirements.txt at .venv/, the Advan files under neighborhood/ and weekly/
# (Dewey Data, academic licence) and the inputs listed in README.md (Inputs). The figures stage requires Google Chrome.
# Runtime on one laptop core per process: about 7 hours, most of it in the travel patterns and the drawing ensembles.
set -e
ROOT=${0:A:h:h}
cd $ROOT
PY="$ROOT/.venv/bin/python -I"
LOG=$ROOT/logs/reproduce
CHROME=${CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}
REGIONS=(columbia)        # Columbia-Jefferson City television market: the study's civic interest areas
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0
mkdir -p $LOG
stage() { [[ " ${STAGES:-data travel coverage spillover public areas qa figures} " == *" $1 "* ]]; }
step() {   # step <name> [VAR=value ...] <script> [args]
  local name=$1; shift
  local envs=(); while [[ $1 == *=* ]]; do envs+=$1; shift; done
  local t=$(date +%s)
  env $envs ${=PY} $ROOT/$@ > $LOG/$name.log 2>&1 || { echo "$name FAILED (see $LOG/$name.log)"; exit 1; }
  echo "$name $(( $(date +%s) - t ))s"
}

# Visits by home and destination county, the population calibration, distinct residents and the pass-through
# discount. Reads the raw Advan files.
if stage data; then
  step build_calibration       analysis/build_calibration.py
  step build_statewide_od      analysis/build_statewide_od.py
  step build_unique_od         analysis/build_unique_od.py
  step build_road_stop_share   analysis/build_road_stop_share.py
  step build_tract_od          analysis/build_tract_od.py
  step crossover_compare       analysis/crossover_compare.py
fi

# Gravity model of travel, its block tests and the nested test of exploratory terms; then the steps table, the
# rejected terms, the small-county tests and the county characteristics (method log, Travel model).
if stage travel; then
  step travel_model            analysis/travel_model.py
  step travel_selection        analysis/travel_model_dc_test.py selection
  step travel_spline           analysis/travel_distance_spline.py
  step travel_commute          analysis/travel_commute_pair_test.py
  step travel_nested           analysis/combined_marginal_test.py travel_nested_all
  step travel_marginal         analysis/combined_marginal_test.py travel
  step travel_competing        analysis/travel_competing_test.py
  step travel_class            analysis/travel_county_class_model.py
  step travel_steps_singly     analysis/travel_model_compare.py
  step travel_steps            analysis/travel_model_dc_test.py
  step travel_hub              analysis/travel_model_hub_test.py
  step travel_drive            analysis/travel_model_drive_test.py
  step travel_business         analysis/travel_business_test.py
  step travel_purpose          analysis/travel_purpose_split_test.py
  step travel_small_origin     analysis/travel_small_origin_model.py
  step travel_small_county     analysis/travel_small_county_test.py
  step travel_jobhub_distance  analysis/travel_distance_variants.py
  step travel_blend            analysis/travel_blend_test.py
fi

# Coverage model (reads od_predicted.csv from the travel stage).
if stage coverage; then
  step coverage_model          analysis/coverage_model.py
  step coverage_saturation     analysis/coverage_saturation_test.py
  step coverage_border         analysis/border_coverage_test.py
  step coverage_flag_compare   analysis/coverage_flag_compare.py
  step coverage_newsroom_size  analysis/coverage_newsroom_size_test.py
  step residual_autocorrelation analysis/residual_autocorrelation.py   # travel and coverage residuals
  step coverage_marginal       analysis/combined_marginal_test.py coverage_all coverage_no_broadcast
fi

# Spillover model (reads crossover_compare.csv from the data stage).
if stage spillover; then
  step spillover_v2            analysis/spillover_v2.py
  step spillover_outlets       analysis/spillover_outlets.py
  step spillover_rule          analysis/spillover_rule_selection.py
  step spillover_nested        analysis/spillover_nested_selection.py
  step spillover_dma           analysis/spillover_dma_holdout.py
  step spillover_quality       analysis/collection_quality_robustness.py
  step spillover_allfactors    analysis/combined_all_factors_test.py
  step spillover_side_tests    analysis/spillover_side_tests.py
  step spillover_population    analysis/spillover_population_test.py
  # County characteristics (crossover, spillover, travel and coverage columns; read spillover_outlets.csv and the
  # coverage stage's predictions)
  step county_acs              analysis/civic_variables_test.py
  step county_civic_index      analysis/civic_index_test.py
  step county_civic_index_v2   analysis/civic_index_test_v2.py
  step county_bylines          analysis/spillover_bylines_test.py
  step county_business         analysis/business_dynamics_test.py
  step hospitals               analysis/hospital_test.py
fi

# Public-data travel model and its Advan-learned corrections.
if stage public; then
  bash $ROOT/scripts/public_model.sh > $LOG/public_model.log 2>&1 || { echo "public_model FAILED"; exit 1; }
  echo "public_model done"
  # where the gap is, and the default-weight sensitivity (read compare_shares.csv and the _s_ builds of public_model.sh)
  step public_gap_corrections  analysis/public_gap_corrections.py
  step public_default_sens     analysis/public_default_sensitivity.py "_s_ref=reference build" \
    "_s_wfh=work from home (ACS B08006)" "_s_days15=15 work days" "_s_shop05=shopping x0.5" \
    "_s_huffhome=gross leakage (Huff home share)" "_s_alpha05=Huff attraction exponent 0.5" \
    "_s_alpha15=Huff attraction exponent 1.5" "_s_trips=long-distance trips, not days" \
    "_s_recvis05=recreation and visiting x0.5" "_s_recvis2=recreation and visiting x2" \
    "_s_medspec05=medical and specialty x0.5" "_s_medspec2=medical and specialty x2" "_s_circ10=circuity 1.0" \
    "_s_circ14=circuity 1.4" "_s_commurban=commuter classes on urban decay"
  step public_gap_diagnosis    analysis/public_gap_diagnosis.py
  # non-work variants (public_model.sh step 9) and work days per commuter (_g_ builds of step 2)
  step public_nonwork_variants analysis/public_default_sensitivity.py \
    "public_model_pairs_v1.csv=v1: establishments, population-centre distance, RUCC survey classes, squared loss" \
    "public_model_pairs_emp.csv=employment draw" "public_model_pairs_hub.csv=job-centre distance" \
    "public_model_pairs_msa.csv=metro-size survey classes" "public_model_pairs_ll.csv=likelihood loss" \
    "public_model_pairs_base.csv=all four (base)"
  step public_nonwork_subgroups analysis/public_default_sensitivity.py "public_model_pairs_base.csv=base" \
    "public_model_pairs_nw_income.csv=decay by income" "public_model_pairs_nw_degree.csv=decay by degree" \
    "public_model_pairs_nw_tenure.csv=decay by tenure"
  step public_work_days_sales  analysis/public_default_sensitivity.py "_g_10_sales=10 work days" "_g_15_sales=15" \
    "_g_20_sales=20" "_g_25_sales=25" "_g_30_sales=30" "_g_40_sales=40"
  step public_work_days_surplus analysis/public_default_sensitivity.py "_g_10_surplus=10 work days, Huff on surplus" \
    "_g_15_surplus=15" "_g_20_surplus=20" "_g_25_surplus=25" "_g_30_surplus=30" "_g_40_surplus=40"
  step conference_ties         analysis/conference_ties_test.py
fi

# Civic interest areas, Columbia-Jefferson City television market: homes, travel patterns (non-negative matrix
# factorization), the network tie, the 6,912-version drawing ensemble, the multi-part areas and tie-market accuracy.
if stage areas; then
  step stop_weights           flows/build_stop_weights.py   # road stops at half weight (Columbia market)
  for r in $REGIONS; do
    step homes_$r              flows/build_homes.py $r
    step patterns_$r           flows/travel_patterns.py $r
    step market_$r             flows/market_patterns.py $r
    step confidence_$r         analysis/confidence_layer.py $r
  done
  step regular_distance        flows/regular_distance.py
  for r in $REGIONS; do
    step ensemble_$r           flows/area_ensemble.py $r
  done
  step area_core               flows/area_core.py $REGIONS
  # sensitivity: the busiest hexagon = 50 instead of the busiest place; its own file, never the adopted ensemble
  step ensemble_busiest_hexagon BUSIEST=hexagon OUT=$ROOT/flows/reach/probability_columbia_busiest_hexagon.json \
                               flows/area_ensemble.py columbia
  step area_core_busiest_hexagon PROB=$ROOT/flows/reach/probability_columbia_busiest_hexagon.json flows/area_core.py columbia
  step market_stability        analysis/market_stability.py
  step selection_sensitivity   analysis/selection_sensitivity.py columbia
  for r in $REGIONS; do
    step tie_$r                ATTRPOP=1 REGRULE=1 BETA_IN=0.5 PUBCOL=adjusted_C OUTTAG=_pop analysis/tie_footprint.py $r
  done
  step tie_summary             SUMMARY=1 OUTTAG=_pop analysis/tie_footprint.py columbia
  # tie-market alternatives (Tie markets): population in the spread, the nonmetro and density rules, the steps
  T=(nopop "ATTRPOP=0 REGRULE=1 BETA_IN=0.5" popnm "ATTRPOP=nonmetro REGRULE=1 BETA_IN=0.5"
     pd50 "ATTRPOP=density:50 REGRULE=1 BETA_IN=0.5" pd200 "ATTRPOP=density:200 REGRULE=1 BETA_IN=0.5"
     s0 "ATTRPOP=0 REGRULE=0 BETA_IN=1" s1 "ATTRPOP=0 REGRULE=0 BETA_IN=0.5"
     b1 "ATTRPOP=1 REGRULE=1 BETA_IN=1" b3 "ATTRPOP=1 REGRULE=1 BETA_IN=3"
     jobs "ATTRPOP=1 REGRULE=1 BETA_IN=0.5 SPREAD=jobs" osm "ATTRPOP=1 REGRULE=1 BETA_IN=0.5 SPREAD=osm"
     jobs0 "ATTRPOP=0 REGRULE=1 BETA_IN=0.5 SPREAD=jobs" osm0 "ATTRPOP=0 REGRULE=1 BETA_IN=0.5 SPREAD=osm"
     reg45 "PUBFILE=public_adjusted_pairs_reg45.csv ATTRPOP=1 REGRULE=1 BETA_IN=0.5"
     reg90 "PUBFILE=public_adjusted_pairs_reg90.csv ATTRPOP=1 REGRULE=1 BETA_IN=0.5")
  for tag set in $T; do
    step tie_alt_$tag          ${=set} PUBCOL=adjusted_C OUTTAG=_alt_$tag analysis/tie_footprint.py columbia
    step tie_alt_${tag}_summary SUMMARY=1 OUTTAG=_alt_$tag analysis/tie_footprint.py columbia
  done
  step tie_mexico_reg45        PUBFILE=public_adjusted_pairs_reg45.csv PUBCOL=adjusted_C ATTRPOP=1 REGRULE=1 BETA_IN=0.5 \
                               DETAIL=Mexico OUTTAG=_alt_reg45_detail analysis/tie_footprint.py columbia
fi

# Supply on the travel-only footprint: quality-assurance diagnostics, not results of the article.
if stage qa; then
  for r in $REGIONS; do
    step coverage_density_$r   REGION=$r analysis/area_coverage_alignment.py
    step diet_$r               REGION=$r DIET_K=0 analysis/cin_diet.py
  done
  step coverage_density_alpha1 ALPHA=1 analysis/area_coverage_alignment.py
fi

# Tables and figures: the area table, the calculation diagram, the data-to-measures flow and the area maps (300 dpi PNG and PDF).
if stage figures; then
  cd $ROOT/flows
  python3 -m http.server 8765 --bind 127.0.0.1 > /dev/null 2>&1 &
  SRV=$!
  for i in {1..20}; do curl -s -o /dev/null http://127.0.0.1:8765/ && break; sleep 0.5; done
  step area_table              flows/export_area_table.py
  step figures_export          flows/export_figures.py
  mkdir -p print
  shot() {   # shot <page and query> <png> <width>
    local h=$("$CHROME" --headless=new --disable-gpu --window-size=$3,2600 --virtual-time-budget=40000 --dump-dom \
      "http://127.0.0.1:8765/$1" 2>/dev/null | grep -o 'data-height="[0-9]*"' | grep -o '[0-9]*')
    "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=3.125 \
      --window-size=$3,$(( ${h:-1100} + 10 )) --virtual-time-budget=40000 --screenshot="print/$2" \
      "http://127.0.0.1:8765/$1" 2>/dev/null
    echo "print/$2"
  }
  # paper=1: the image as Journalism Studies sets it -- graphic and key only; title, notes and source are the caption
  shot "model_diagram_print.html?paper=1" model_diagram.png 528
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --virtual-time-budget=40000 \
    --print-to-pdf=print/model_diagram.pdf "http://127.0.0.1:8765/model_diagram_print.html?paper=1" 2>/dev/null
  shot "measures_flow_print.html?paper=1" measures_flow.png 528
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --virtual-time-budget=40000 \
    --print-to-pdf=print/measures_flow.pdf "http://127.0.0.1:8765/measures_flow_print.html?paper=1" 2>/dev/null
  # triptych panels: ls=1.9 sets place labels at about 6 pt once a panel is a third of the page width
  for t in Columbia Mexico Linn; do
    shot "market_pattern_print.html?town=$t&rank=1&paper=1&panel=1&ls=1.9" "civic_area_${(L)t}.png" 528   # Figure 4
    shot "market_pattern_print.html?town=$t&rank=1&measure=coverage&paper=1&panel=1&ls=1.9" "civic_coverage_${(L)t}.png" 528   # Figure 5
  done
  key() {   # key <page and query> <png>: the triptych's shared key, 660 CSS px drawn to the triptych's 5,130 px
    "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=7.773 --window-size=660,600 \
      --virtual-time-budget=40000 --screenshot="print/$2" "http://127.0.0.1:8765/$1" 2>/dev/null
    echo "print/$2"
  }
  key "market_pattern_print.html?town=Columbia&rank=1&paper=1&keyonly=1" civic_area_key.png
  key "market_pattern_print.html?town=Columbia&rank=1&measure=coverage&paper=1&keyonly=1" civic_coverage_key.png
  kill $SRV
  ${=PY} - <<'PYEOF'   # Figures 4 and 5: the shared key over the three area maps, and over the three coverage maps
from PIL import Image, ImageChops
for kind in ("area", "coverage"):
    ims = [Image.open(f"print/civic_{kind}_{t}.png").convert("RGB") for t in ("columbia", "mexico", "linn")]
    gap = 90; w = sum(i.width for i in ims) + gap * 2; h = max(i.height for i in ims)
    k = Image.open(f"print/civic_{kind}_key.png").convert("RGB")
    k = k.crop((0, 0, w, ImageChops.difference(k, Image.new("RGB", k.size, "white")).getbbox()[3] + 12))
    out = Image.new("RGB", (w, k.height + 40 + h), "white"); out.paste(k, (0, 0)); x = 0
    for i in ims:
        out.paste(i, (x, k.height + 40)); x += i.width + gap
    out.save(f"print/civic_{kind}_triptych.png", dpi=(300, 300)); print(f"print/civic_{kind}_triptych.png", out.size)
PYEOF
  cd $ROOT
fi
echo "done: logs in $LOG"
