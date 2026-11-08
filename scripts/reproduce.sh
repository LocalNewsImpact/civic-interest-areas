#!/bin/zsh
# Rebuilds every result, table and figure in the article, in dependency order (RESULTS.md: which step prints each).
#
#   zsh scripts/reproduce.sh                    # every stage
#   STAGES="travel coverage" zsh scripts/reproduce.sh
#
# Stages: data travel coverage spillover factors public areas sensitivity figures. Logs: logs/reproduce/<step>.log.
# Requires the Python environment in requirements.txt at .venv/, the Advan files under neighborhood/ and weekly/
# (Dewey Data, academic licence) and the inputs listed in README.md (Inputs). The figures stage requires Google Chrome.
# Runtime: about 7 hours, most of it in the travel patterns and the drawing ensembles. The ensembles run one process
# per town, JOBS at a time (default 8; each holds about 1.2 GB), so the areas and sensitivity stages use several cores.
set -e
ROOT=${0:A:h:h}
cd $ROOT
PY="$ROOT/.venv/bin/python -I"
LOG=$ROOT/logs/reproduce
CHROME=${CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}
REGIONS=(columbia)        # Columbia-Jefferson City television market: the study's civic interest areas
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0
JOBS=${JOBS:-8}           # ensemble processes at once
mkdir -p $LOG
stage() { [[ " ${STAGES:-data travel coverage spillover factors public areas sensitivity figures} " == *" $1 "* ]]; }
step() {   # step <name> [VAR=value ...] <script> [args]
  local name=$1; shift
  local envs=(); while [[ $1 == *=* ]]; do envs+=$1; shift; done
  local t=$(date +%s)
  env $envs ${=PY} $ROOT/$@ > $LOG/$name.log 2>&1 || { echo "$name FAILED (see $LOG/$name.log)"; exit 1; }
  echo "$name $(( $(date +%s) - t ))s"
}
PIDS=()
spawn() {  # spawn <step args>: a step in the background, at most JOBS at once
  while :; do
    local live=(); for p in $PIDS; do kill -0 $p 2>/dev/null && live+=$p; done; PIDS=($live)
    (( ${#PIDS} < JOBS )) && break; sleep 5
  done
  step "$@" & PIDS+=$!
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
  step flows_bg2020            flows/build_flows_bg2020.py   # August-September on 2020 block groups: the areas' nine months
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
  # one process per town, merged into the region's ensemble file
  PARTS=$ROOT/flows/reach/ensemble_parts; mkdir -p $PARTS
  for r in $REGIONS; do
    for t in $(${=PY} flows/area_ensemble.py $r --towns); do
      rm -f $PARTS/${r}_$t.json   # a failed town leaves no part, so its merge fails
      spawn ensemble_${r}_$t TOWNS=$t OUT=$PARTS/${r}_$t.json flows/area_ensemble.py $r
    done
  done
  wait
  for r in $REGIONS; do
    f=flows/reach/probability_$r.json
    [[ $r == columbia ]] || f=$(${=PY} -c "import json; print(json.load(open('flows/regions.json'))['$r']['out'])")/probability.json
    step merge_$r flows/merge_ensembles.py $f $(for t in $(${=PY} flows/area_ensemble.py $r --towns); do echo $PARTS/${r}_$t.json; done)
  done
  step area_core               flows/area_core.py $REGIONS
  for r in $REGIONS; do
    step coverage_density_$r   REGION=$r analysis/area_coverage_alignment.py
    step diet_$r               REGION=$r DIET_K=0 analysis/cin_diet.py
    step coverage_intervals_$r REGION=$r analysis/coverage_intervals.py
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
    for t in $(${=PY} flows/area_ensemble.py columbia --towns); do
      rm -f $SENS/part_${k}_$t.json
      spawn ensemble_${k}_$t $e TOWNS=$t OUT=$SENS/part_${k}_$t.json flows/area_ensemble.py columbia
    done
  done
  wait
  for k in ${(k)V}; do
    step merge_$k flows/merge_ensembles.py $SENS/prob_$k.json \
      $(for t in $(${=PY} flows/area_ensemble.py columbia --towns); do echo $SENS/part_${k}_$t.json; done)
    step area_core_$k PROB=$SENS/prob_$k.json flows/area_core.py columbia
  done
  for k in ${(k)V}; do [[ -f $SENS/prob_$k.json ]] || { echo "sensitivity $k FAILED"; exit 1; }; done
  step judgment_constants      analysis/judgment_constants.py
fi

# Figures 1-5: the TV market locator; the data-to-measures flow (300 dpi PNG and PDF); and one panel per town, its civic
# interest area beside its coverage on one fitted scale (Figures 3-5), Mexico's two areas as two rows of Figure 4.
# Figures 1 and 3-5 are 6.0 in wide at 600 dpi.
if stage figures; then
  cd $ROOT/flows
  python3 -m http.server 8765 --bind 127.0.0.1 > /dev/null 2>&1 &
  SRV=$!
  for i in {1..20}; do curl -s -o /dev/null http://127.0.0.1:8765/ && break; sleep 0.5; done
  mkdir -p print
  blank() { ${=PY} -c "import sys; from PIL import Image, ImageChops; im = Image.open(sys.argv[1]).convert('RGB'); \
sys.exit(0 if ImageChops.difference(im, Image.new('RGB', im.size, 'white')).getbbox() is None else 1)" "$1"; }
  # shot <page and query> <png> <CSS width> <scale> [<CSS height>]: the page's own data-height unless a height is given.
  # One Chrome at a time (parallel runs draw empty pages); an empty image is drawn again, up to three times
  shot() {
    local h=${5:-$("$CHROME" --headless=new --disable-gpu --window-size=$3,2600 --virtual-time-budget=40000 --dump-dom \
      "http://127.0.0.1:8765/$1" 2>/dev/null | grep -o 'data-height="[0-9]*"' | grep -o '[0-9]*')}
    for try in 1 2 3; do
      "$CHROME" --user-data-dir=$(mktemp -d) --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=$4 \
        --window-size=$3,$(( ${h:-1100} + 10 )) --virtual-time-budget=40000 --screenshot="print/$2" \
        "http://127.0.0.1:8765/$1" 2>/dev/null
      blank "print/$2" || break
    done
    blank "print/$2" && { echo "print/$2 EMPTY after three tries"; kill $SRV; exit 1; }
    echo "print/$2"
  }
  shot "dma_locator_print.html" figure1_dma_locator.png 600 6 482   # Figure 1: 600 x 492 CSS px x 6 = 3,600 x 2,952 px
  # paper=1: the image as Journalism Studies sets it -- graphic and key only; title, notes and source are the caption
  shot "measures_flow_print.html?paper=1" measures_flow.png 528 3.125   # Figure 2
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --virtual-time-budget=40000 \
    --print-to-pdf=print/measures_flow.pdf "http://127.0.0.1:8765/measures_flow_print.html?paper=1" 2>/dev/null
  # Figures 3-5: each map 528 CSS px drawn to 1,764 px, two to a 3,600 px panel with a 72 px gutter; fit=1 one scale for
  # the three towns; ground=1 Figure 1's grey land and white county lines; ls=1.45 the place labels at that size
  for t in Columbia Mexico Linn; do
    shot "market_pattern_print.html?town=$t&rank=1&paper=1&panel=1&fit=1&ls=1.45&ground=1" "area_${(L)t}.png" 528 3.3409
    shot "market_pattern_print.html?town=$t&rank=1&measure=coverage&paper=1&panel=1&fit=1&ls=1.45&ground=1" "cov_${(L)t}.png" 528 3.3409
  done
  # Mexico's second civic interest area (13% of its residents, toward Columbia): Figure 4's second row
  shot "market_pattern_print.html?town=Mexico&rank=2&paper=1&panel=1&fit=1&ls=1.45&ground=1" area_mexico_2.png 528 3.3409
  shot "market_pattern_print.html?town=Mexico&rank=2&measure=coverage&paper=1&panel=1&fit=1&ls=1.45&ground=1" cov_mexico_2.png 528 3.3409
  # keys at the type size they have when a 440 CSS px key is scaled to one map's width: each measure's own items, and the
  # home county, county border and TV market lines with the scale bar, shown once across the panel
  K="town=Columbia&rank=1&paper=1&fit=1&keyonly=1&ground=1"
  shot "market_pattern_print.html?$K&keyparts=own&kw=440" key_area.png 440 4.0091 390
  shot "market_pattern_print.html?$K&measure=coverage&keyparts=own&kw=440" key_cov.png 440 4.0091 390
  shot "market_pattern_print.html?$K&keyparts=lines&kscale=0.83333&kw=898" key_lines.png 898 4.0091 390
  kill $SRV
  ${=PY} - <<'PYEOF'   # Figures 3-5: the keys cropped to their content above the two maps
from PIL import Image, ImageChops
def content(f):
    im = Image.open(f"print/{f}").convert("RGB")
    bb = ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()
    return im.crop((0, bb[1], im.width, bb[3]))
ka, kc, kl = content("key_area.png"), content("key_cov.png"), content("key_lines.png")
# one row per civic interest area, area left and coverage right; rows 72 px apart, the panel gutter
for n, t, rows in ((3, "columbia", [""]), (4, "mexico", ["", "_2"]), (5, "linn", [""])):
    pairs = [(Image.open(f"print/area_{t}{r}.png").convert("RGB"), Image.open(f"print/cov_{t}{r}.png").convert("RGB"))
             for r in rows]
    out = Image.new("RGB", (3600, 335 + sum(a.height for a, _ in pairs) + 72 * (len(pairs) - 1)), "white")
    out.paste(ka, (0, 10)); out.paste(kc, (1836, 10)); out.paste(kl, (0, 288))
    y = 335
    for a, c in pairs:
        out.paste(a, (0, y)); out.paste(c, (1836, y)); y += a.height + 72
    out.save(f"print/figure{n}_{t}.png", dpi=(600, 600)); print(f"print/figure{n}_{t}.png", out.size)
PYEOF
  cd $ROOT
fi
echo "done: logs in $LOG"
