#!/bin/zsh
# Rebuilds every result in MODEL_CHANGES.md "Current results", in dependency order.
#
#   zsh scripts/reproduce.sh                    # every stage
#   STAGES="travel coverage" zsh scripts/reproduce.sh
#
# Stages: data travel coverage spillover public areas qa figures. Logs: logs/reproduce/<step>.log.
# Requires the Python environment in requirements.txt at .venv/, the Advan files under neighborhood/ and weekly/
# (Dewey Data, academic licence) and the inputs listed in README.md (Inputs). The figures stage requires Google Chrome.
# Runtime on one laptop core per process: about 6 hours, most of it in the travel patterns and the drawing ensembles.
set -e
ROOT=${0:A:h:h}
cd $ROOT
PY="$ROOT/.venv/bin/python -I"
LOG=$ROOT/logs/reproduce
CHROME=${CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}
REGIONS=(columbia springfield cape kirksville joplin kansascity stjoseph)
BUILT=(columbia springfield joplin kirksville)        # markets with study towns that have mapped areas
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
  step build_ks_od             analysis/build_ks_od.py
  step build_ks_tract_bg       analysis/build_ks_tract_bg.py
  step crossover_compare       analysis/crossover_compare.py
fi

# Gravity model of travel, its block tests and the nested test of exploratory terms.
if stage travel; then
  step travel_model            analysis/travel_model.py
  step travel_selection        analysis/travel_model_dc_test.py selection
  step travel_commute          analysis/travel_commute_pair_test.py
  step travel_nested           analysis/combined_marginal_test.py travel_nested_all
  step travel_marginal         analysis/combined_marginal_test.py travel
  step travel_competing        analysis/travel_competing_test.py
  step travel_class            analysis/travel_county_class_model.py
fi

# Coverage model (reads od_predicted.csv from the travel stage).
if stage coverage; then
  step coverage_model          analysis/coverage_model.py
  step coverage_saturation     analysis/coverage_saturation_test.py
  step coverage_border         analysis/border_coverage_test.py
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
fi

# Public-data travel model, its Advan-learned corrections and the Kansas transfer test.
if stage public; then
  bash $ROOT/scripts/public_model.sh > $LOG/public_model.log 2>&1 || { echo "public_model FAILED"; exit 1; }
  echo "public_model done"
fi

# Civic interest areas: homes, travel patterns (non-negative matrix factorization) and the network tie per market;
# the 1,728-version drawing ensemble and the multi-part area for markets with mapped areas; tie-market accuracy.
if stage areas; then
  for r in $REGIONS; do
    step homes_$r              flows/build_homes.py $r
    step patterns_$r           flows/travel_patterns.py $r
    step market_$r             flows/market_patterns.py $r
    step confidence_$r         analysis/confidence_layer.py $r
  done
  for r in $BUILT; do
    step ensemble_$r           flows/area_ensemble.py $r
  done
  step area_core               flows/area_core.py $BUILT
  step market_stability        analysis/market_stability.py
  step selection_sensitivity   analysis/selection_sensitivity.py columbia
  for r in $REGIONS; do
    step tie_$r                ATTRPOP=1 REGRULE=1 BETA_IN=0.5 PUBCOL=adjusted_C OUTTAG=_pop analysis/tie_footprint.py $r
  done
  step tie_summary             SUMMARY=1 OUTTAG=_pop analysis/tie_footprint.py columbia
fi

# Supply on the travel-only footprint: quality-assurance diagnostics, not results of the article.
if stage qa; then
  for r in $BUILT; do
    step coverage_density_$r   REGION=$r analysis/area_coverage_alignment.py
    step diet_$r               REGION=$r DIET_K=0 analysis/cin_diet.py
  done
  step coverage_density_alpha1 ALPHA=1 analysis/area_coverage_alignment.py
fi

# Tables and figures: the area table, the calculation diagram and the area maps (300 dpi PNG and PDF).
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
  shot "model_diagram_print.html" model_diagram.png 528
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --virtual-time-budget=40000 \
    --print-to-pdf=print/model_diagram.pdf "http://127.0.0.1:8765/model_diagram_print.html" 2>/dev/null
  for t in Columbia Mexico Linn; do
    shot "market_pattern_print.html?town=$t&rank=1" "civic_area_${(L)t}.png" 900
  done
  kill $SRV
  cd $ROOT
fi
echo "done: logs in $LOG"
