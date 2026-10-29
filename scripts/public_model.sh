#!/bin/bash
# Public-data travel model, Missouri: the Stage 1 builds, the Advan-fitted benchmark on the same outcome, and the
# nested Stage 1 score (the article's 4.6 points against 3.3 for the Advan-fitted model), with every environment
# setting each step needs.
# Called by scripts/reproduce.sh (stage public); runs from any directory; at most 2 processes; BLAS single-threaded.
# Inputs from the travel stage: gravity_terms.py outcome visits_statewide, road_stop_share.csv `discount`,
# LODES 2023 primary jobs (JT01), distance terms centred at 25 miles.
set -euo pipefail
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 MKL_NUM_THREADS=1
PY=".venv/bin/python -I"
mkdir -p logs
step() { [[ " ${STEPS:-1 9 2 3 4} " == *" $1 "* ]]; }   # STEPS="2 3" runs only those steps

# ---- 0. LODES 2023 JT01 files (LEHD LODES8), once -----------------------------------------------------------------------
# free/mo_residents_od_JT01_2023.csv.gz (travel model: free/mo_od_main_JT01_2023.csv.gz + the Missouri-home rows of
# free/{il,ks,ia,ar,ok,ne,tn,ky}_od_aux_JT01_2023.csv.gz):
#   curl -f -o free/<s>_od_aux_JT01_2023.csv.gz https://lehd.ces.census.gov/data/lodes/LODES8/<s>/od/<s>_od_aux_JT01_2023.csv.gz

# ---- 1. Work model (LODES JT01) -------------------------------------------------------------------------------------------
if step 1; then
DIST=pop TAG=_v1 $PY analysis/public_work_model.py > logs/work_v1_mo.log 2>&1
fi

# ---- 9. Work + non-work baseline (public_nonwork_model.py, _base: employment draw, likelihood loss), read by
#         public_vs_advan_compare.py; and the four-kinds build (public_travel_components.py, _share), read there too.
if step 9; then
DRAW=emp DIST=pop CLASS=rucc LOSS=ll TAG=_base $PY analysis/public_nonwork_model.py > logs/nonwork_base.log 2>&1
TAG=_share $PY analysis/public_travel_components.py > logs/components_share.log 2>&1
fi

# ---- 2. Stage 1 candidate builds: public_travel_tiers.py, one per setting (53, Missouri); public_stage1_nested.py
#         chooses among them --------------------------------------------------------------------------------------------
# TAG|environment. Shared bases:
S="RETAIL=tac DRAWMODE=cap REC_CODES=71----"                # trade area builds
G="$S CHAIN=1 WORK_HYBRID=90"                               # observed LODES within 90 miles, chained errands
C="$S CHAIN=1 HUFF=sales"
BUILDS=$(cat <<EOF
-|
_cap|DRAWMODE=cap
_cap71|DRAWMODE=cap REC_CODES=71----
_spare71|REC_CODES=71----
_tac|$S CAPDRAW=1
_tac_l2|$S LAMBDA=retail:2
_tac_surplus_l2|$S HUFF=surplus LAMBDA=retail:2
_tac_all2|$S LAMBDA=all:2
_s_ref|$S
_s_ref2|$S
_s_wfh|$S WFH=1
_s_days15|$S WORK_DAYS=15
_s_shop05|$S MULT=retail:0.5
_s_huffhome|$S LEAK=huffhome
_s_alpha05|$S HUFF_ALPHA=0.5
_s_alpha15|$S HUFF_ALPHA=1.5
_s_trips|$S LD_DAYS=0
_s_recvis05|$S MULT=recreation:0.5,visiting:0.5
_s_recvis2|$S MULT=recreation:2,visiting:2
_s_medspec05|$S MULT=medical:0.5,specialty:0.5
_s_medspec2|$S MULT=medical:2,specialty:2
_s_circ10|$S CIRC=1.0
_s_circ14|$S CIRC=1.4
_s_commurban|$S URBAN_CLASSES=class@3
_s_ruralset|$S LEAK=huffhome MULT=recreation:0.5,visiting:0.5 LD_DAYS=0 CIRC=1.4
_s_commset|$S LEAK=huffhome URBAN_CLASSES=class@3
_s_hr|$S LEAK=huffhome MULT=recreation:0.5,visiting:0.5
_s_workobs|$S WORK_OBS=1
_s_chain|$S CHAIN=1
_s_workobs_chain|$S WORK_OBS=1 CHAIN=1
_s_hyb40|$S CHAIN=1 WORK_HYBRID=40
_s_hyb60|$S CHAIN=1 WORK_HYBRID=60
_s_hyb90|$S CHAIN=1 WORK_HYBRID=90
_g_10_sales|$G WORK_DAYS=10 HUFF=sales
_g_10_surplus|$G WORK_DAYS=10 HUFF=surplus
_g_15_sales|$G WORK_DAYS=15 HUFF=sales
_g_15_surplus|$G WORK_DAYS=15 HUFF=surplus
_g_25_sales|$G WORK_DAYS=25 HUFF=sales
_g_25_surplus|$G WORK_DAYS=25 HUFF=surplus
_g_30_sales|$G WORK_DAYS=30 HUFF=sales
_g_30_surplus|$G WORK_DAYS=30 HUFF=surplus
_g_40_sales|$G WORK_DAYS=40 HUFF=sales
_g_40_surplus|$G WORK_DAYS=40 HUFF=surplus
_c_10_l6|$G HUFF=sales WORK_DAYS=10 LAMBDA=retail:6
_c_10_l8|$G HUFF=sales WORK_DAYS=10 LAMBDA=retail:8
_c_40_l6|$G HUFF=sales WORK_DAYS=40 LAMBDA=retail:6
_c_40_l8|$G HUFF=sales WORK_DAYS=40 LAMBDA=retail:8
_c_10_l6all|$G HUFF=sales WORK_DAYS=10 LAMBDA=retail:6,medical:6,specialty:6
_c_40_l6all|$G HUFF=sales WORK_DAYS=40 LAMBDA=retail:6,medical:6,specialty:6
_c_grav20|$C WORK_DAYS=20
_c_grav40|$C WORK_DAYS=40
_c_hyb20_40|$C WORK_HYBRID=20 WORK_DAYS=40
_c_hyb40_40|$C WORK_HYBRID=40 WORK_DAYS=40
EOF
)
build() {   # build <TAG> <env...>   (TAG "-" = none; @ stands for a space inside a value)
  local tag=$1; shift; [ "$tag" = "-" ] && tag=""
  local args=(); for a in "$@"; do args+=("${a//@/ }"); done
  env "${args[@]}" TAG=$tag $PY analysis/public_travel_tiers.py > logs/tiers_29${tag:-_none}.log 2>&1 || echo "FAIL $tag"
}
export -f build; export PY
if step 2; then
echo "$BUILDS" | while IFS='|' read -r tag e; do echo "$tag${e:+ $e}"; done | xargs -P 2 -L 1 bash -c 'build "$@"' _   # no trailing blank: xargs -L joins such lines
fi

# ---- 3. Benchmark and target: compare_shares.csv (adopted outcome; Advan-fitted, counties held out) ------------------------
if step 3; then
$PY analysis/public_vs_advan_compare.py > logs/public_vs_advan_compare.log 2>&1
fi

# ---- 4. Stage 1, nested: each class's setting with the scored county left out -----------------------------------------------
if step 4; then
$PY analysis/public_stage1_nested.py > logs/public_stage1_nested.log 2>&1
fi
