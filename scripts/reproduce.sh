#!/bin/zsh
# Rebuilds every result, table and figure in the article, in dependency order (RESULTS.md: which step prints each).
#
#   zsh scripts/reproduce.sh                    # every stage
#   STAGES="travel coverage" zsh scripts/reproduce.sh
#
# Stages: data travel coverage spillover factors public areas sensitivity figures. Logs: logs/reproduce/<step>.log.
# Requires the Python environment in requirements.txt at .venv/, the Advan files under neighborhood/ and weekly/
# (Dewey Data, academic licence) and the inputs listed in README.md (Inputs). The figures stage requires Google Chrome.
# Runtime on one laptop core per process: about 7 hours, most of it in the travel patterns and the drawing ensembles;
# the sensitivity stage adds about 2 hours on six cores.
set -e
ROOT=${0:A:h:h}
cd $ROOT
PY="$ROOT/.venv/bin/python -I"
LOG=$ROOT/logs/reproduce
CHROME=${CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}
REGIONS=(columbia)        # Columbia-Jefferson City television market: the study's civic interest areas
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0
mkdir -p $LOG
stage() { [[ " ${STAGES:-data travel coverage spillover factors public areas sensitivity figures} " == *" $1 "* ]]; }
step() {   # step <name> [VAR=value ...] <script> [args]
  local name=$1; shift
  local envs=(); while [[ $1 == *=* ]]; do envs+=$1; shift; done
  local t=$(date +%s)
  env $envs ${=PY} $ROOT/$@ > $LOG/$name.log 2>&1 || { echo "$name FAILED (see $LOG/$name.log)"; exit 1; }
  echo "$name $(( $(date +%s) - t ))s"
}

# Visits by home and destination county, the population calibration, distinct residents, the pass-through discount and
# crossover; county covariates, the three study counties' block-group flows, county subdivision boundaries and
# OpenStreetMap destinations. Reads the raw Advan files and the public inputs (README.md, Inputs).
if stage data; then
  step build_county_covariates analysis/build_county_covariates.py
  step build_calibration       analysis/build_calibration.py
  step build_statewide_od      analysis/build_statewide_od.py
  step build_unique_od         analysis/build_unique_od.py
  step build_road_stop_share   analysis/build_road_stop_share.py
  step crossover_compare       analysis/crossover_compare.py
  step extract_three_counties  neighborhood/extract.py $ROOT/neighborhood/raw $ROOT/neighborhood/flows_audrain_boone_osage_2026.csv
  step cousub_geo              flows/build_cousub_shares.py --geo
  step destinations            flows/build_destinations.py
fi

# Gravity model of travel (the Advan-fitted error, 3.3 points; od_predicted.csv for the coverage model). The county
# classes it scores by are fitted first.
if stage travel; then
  step travel_class            analysis/travel_county_class_model.py
  step travel_model            analysis/travel_model.py
fi

# Coverage model: stories against travel, urban and rural newsroom counties (reads od_predicted.csv).
if stage coverage; then
  step coverage_model          analysis/coverage_model.py
fi

# Spillover: county tables, the outlet model on the 85 fitted outlets (Table 2, Table S1), outlet type and print
# outlets in the county, the crossover-spillover correlation on the fitted outlets, and the county figures' intervals.
if stage spillover; then
  step spillover_v2            analysis/spillover_v2.py
  step spillover_outlets       analysis/spillover_outlets.py
  step spillover_population    analysis/spillover_population_test.py
  step county_collection_quality analysis/county_collection_quality.py
  step spillover_quality       analysis/collection_quality_robustness.py
  step county_intervals        analysis/county_intervals.py
  # Table 2's story counts and the stories reaching another county: county story files from the statewide export, then
  # each study county's stories and travel by destination county
  step county_story_files      coverage/storymap/rebuild_county_files.py
  step alignment               coverage/build_alignment.py
fi

# The factors tested and not adopted (Methods: "more than a hundred factors"): every exploratory travel, coverage and
# spillover term, county characteristics, and all rejected terms at once. analysis/factor_search/README.md.
if stage factors; then
  F=analysis/factor_search
  step build_drive_routes      $F/build_drive_routes.py
  step build_hospitals         $F/build_hospitals.py
  step build_od_purpose        $F/build_statewide_od_purpose.py
  step travel_selection        analysis/travel_model_dc_test.py selection
  step travel_steps            analysis/travel_model_dc_test.py
  step travel_steps_singly     $F/travel_model_compare.py
  step travel_spline           $F/travel_distance_spline.py
  step travel_commute          $F/travel_commute_pair_test.py
  step travel_competing        $F/travel_competing_test.py
  step travel_hub              $F/travel_model_hub_test.py
  step travel_drive            $F/travel_model_drive_test.py
  step travel_business         $F/travel_business_test.py
  step travel_purpose          $F/travel_purpose_split_test.py
  step travel_small_origin     $F/travel_small_origin_model.py
  step travel_small_county     $F/travel_small_county_test.py
  step travel_jobhub_distance  $F/travel_distance_variants.py
  step travel_blend            $F/travel_blend_test.py
  step travel_nested           $F/combined_marginal_test.py travel_nested_all
  step travel_marginal         $F/combined_marginal_test.py travel
  step coverage_saturation     $F/coverage_saturation_test.py
  step coverage_newsroom_size  $F/coverage_newsroom_size_test.py
  step coverage_marginal       $F/combined_marginal_test.py coverage_all coverage_no_broadcast
  step spillover_rule          $F/spillover_rule_selection.py
  step spillover_nested        $F/spillover_nested_selection.py
  step spillover_side_tests    $F/spillover_side_tests.py
  step county_acs              $F/civic_variables_test.py
  step county_civic_index      $F/civic_index_test.py
  step county_civic_index_v2   $F/civic_index_test_v2.py
  step county_bylines          $F/spillover_bylines_test.py
  step county_business         $F/business_dynamics_test.py
  step hospitals               $F/hospital_test.py
  step all_factors             $F/combined_all_factors_test.py
fi

# Public-data travel model: the nested Stage 1 score against the Advan-fitted model (4.6 against 3.3 points).
if stage public; then
  step public_geography        analysis/build_public_geography.py
  step tract_acs               analysis/build_tract_acs.py
  bash $ROOT/scripts/public_model.sh > $LOG/public_model.log 2>&1 || { echo "public_model FAILED"; exit 1; }
  echo "public_model done"
fi

# Civic interest areas, Columbia-Jefferson City television market: homes, travel patterns (non-negative matrix
# factorization), the network tie, the 6,912-version drawing ensemble, the multi-part areas (Table 3, Figure 3), and
# coverage density and the balanced diet on the areas (Figure 4).
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
  for r in $REGIONS; do
    step coverage_density_$r   REGION=$r analysis/area_coverage_alignment.py
    step diet_$r               REGION=$r DIET_K=0 analysis/cin_diet.py
  done
fi

# Table S2: the constants set by judgment (direct and shared-place news-tie weights, direction strength) halved and
# doubled. Six full 6,912-version ensembles in parallel, each with the area rule applied; never over the adopted one.
if stage sensitivity; then
  SENS=$ROOT/flows/reach/sensitivity; mkdir -p $SENS
  typeset -A V
  V=(direct_half "TIE_W=0.15,0.15,0.7,0.7" direct_double "TIE_W=0.6,0.6,0.7,0.7" shared_half "TIE_W=0.3,0.3,0.35,0.35"
     shared_double "TIE_W=0.3,0.3,1.4,1.4" gamma_quarter "GAMMA=0.25" gamma_one "GAMMA=1.0")
  for k e in ${(kv)V}; do
    ( step ensemble_$k $e OUT=$SENS/prob_$k.json flows/area_ensemble.py columbia &&
      step area_core_$k PROB=$SENS/prob_$k.json flows/area_core.py columbia ) &
  done
  wait
  for k in ${(k)V}; do [[ -f $SENS/prob_$k.json ]] || { echo "sensitivity $k FAILED"; exit 1; }; done
  step judgment_constants      analysis/judgment_constants.py
fi

# Figures 2-4: the data-to-measures flow and the area and coverage maps (300 dpi PNG; Figure 2 also as PDF).
if stage figures; then
  cd $ROOT/flows
  python3 -m http.server 8765 --bind 127.0.0.1 > /dev/null 2>&1 &
  SRV=$!
  for i in {1..20}; do curl -s -o /dev/null http://127.0.0.1:8765/ && break; sleep 0.5; done
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
  shot "measures_flow_print.html?paper=1" measures_flow.png 528
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --virtual-time-budget=40000 \
    --print-to-pdf=print/measures_flow.pdf "http://127.0.0.1:8765/measures_flow_print.html?paper=1" 2>/dev/null
  # triptych panels: ls=1.9 sets place labels at about 6 pt once a panel is a third of the page width
  for t in Columbia Mexico Linn; do
    shot "market_pattern_print.html?town=$t&rank=1&paper=1&panel=1&ls=1.9" "civic_area_${(L)t}.png" 528   # Figure 3
    shot "market_pattern_print.html?town=$t&rank=1&measure=coverage&paper=1&panel=1&ls=1.9" "civic_coverage_${(L)t}.png" 528   # Figure 4
  done
  key() {   # key <page and query> <png>: the triptych's shared key, 660 CSS px drawn to the triptych's 5,130 px
    "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=7.773 --window-size=660,600 \
      --virtual-time-budget=40000 --screenshot="print/$2" "http://127.0.0.1:8765/$1" 2>/dev/null
    echo "print/$2"
  }
  key "market_pattern_print.html?town=Columbia&rank=1&paper=1&keyonly=1" civic_area_key.png
  key "market_pattern_print.html?town=Columbia&rank=1&measure=coverage&paper=1&keyonly=1" civic_coverage_key.png
  kill $SRV
  ${=PY} - <<'PYEOF'   # Figures 3 and 4: each triptych's shared key over its three panels
from PIL import Image, ImageChops
FIGS = {"civic_area_triptych.png": ("civic_area_key.png", [f"civic_area_{t}.png" for t in ("columbia", "mexico", "linn")]),
        "civic_coverage_triptych.png": ("civic_coverage_key.png", [f"civic_coverage_{t}.png" for t in ("columbia", "mexico", "linn")])}
for name, (key, panels) in FIGS.items():
    ims = [Image.open(f"print/{f}").convert("RGB") for f in panels]
    gap = 90; w = sum(i.width for i in ims) + gap * 2; h = max(i.height for i in ims)
    k = Image.open(f"print/{key}").convert("RGB")
    k = k.crop((0, 0, w, ImageChops.difference(k, Image.new("RGB", k.size, "white")).getbbox()[3] + 12))
    out = Image.new("RGB", (w, k.height + 40 + h), "white"); out.paste(k, (0, 0)); x = 0
    for i in ims:
        out.paste(i, (x, k.height + 40)); x += i.width + gap
    out.save(f"print/{name}", dpi=(300, 300)); print(f"print/{name}", out.size)
PYEOF
  cd $ROOT
fi
echo "done: logs in $LOG"
