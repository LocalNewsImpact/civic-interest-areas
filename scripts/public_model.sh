#!/bin/bash
# Public-data travel model: rebuilds the Stage 1 builds, the Advan-learned corrections (Stage 2), the Kansas transfer
# test and public_adjusted_pairs_trnear.csv, with every environment setting each step needs.
# Called by scripts/reproduce.sh (stage public); runs from any directory; at most 2 processes; BLAS single-threaded.
# Inputs from the travel stage: gravity_terms.py outcome visits_statewide, road_stop_share.csv `discount`,
# LODES 2023 primary jobs (JT01), distance terms centred at 25 miles.
set -euo pipefail
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 MKL_NUM_THREADS=1
PY=".venv/bin/python -I"
mkdir -p logs
step() { [[ " ${STEPS:-1 2 3 4 5 6 7 8} " == *" $1 "* ]]; }   # STEPS="2 3" runs only those steps

# Round 3 (2026-10-25): free/mo_residents_od_JT01_2023.csv.gz (travel model; Missouri main + Missouri-home rows of the
# 8 aux files) is read by public_work_model.py (Missouri), public_adjusted_model.py, transfer_adjustments.py and
# ks_advan_fitted.py. For the work model it holds exactly the rows read before (2,621,217 jobs, every tract->county
# cell equal), so steps 1-2 need no rerun after the switch; run STEPS="3 4 5 6 7 8".
# ---- 0. LODES 2023 JT01 files (LEHD LODES8), once -----------------------------------------------------------------------
# free/mo_od_main_JT01_2023.csv.gz, free/mo_od_aux_JT01_2023.csv.gz (travel model);
# free/{il,ks,ia,ar,ok,ne,tn,ky}_od_aux_JT01_2023.csv.gz; free/ks/ks_od_main_JT01_2023.csv.gz;
# free/ks/{mo,ne,ok,co}_od_aux_JT01_2023.csv.gz:
#   curl -f -o free/<s>_od_aux_JT01_2023.csv.gz https://lehd.ces.census.gov/data/lodes/LODES8/<s>/od/<s>_od_aux_JT01_2023.csv.gz
# ACS 2020-2024 B01003 (Kansas county classes): census_dl/acs_tract/b01003.dat from
#   https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b01003.dat

# ---- 1. Work model (LODES JT01), Missouri and Kansas ----------------------------------------------------------------------
if step 1; then
DIST=pop TAG=_v1 $PY analysis/public_work_model.py > logs/work_v1_mo.log 2>&1 &
STATE=20 DIST=pop TAG=_v1 $PY analysis/public_work_model.py > logs/work_v1_ks.log 2>&1 &
wait
$PY analysis/build_ks_county_classes.py                     # Kansas classes, ACS 2020-2024 population
fi

# ---- 2. Stage 1 candidate builds: public_travel_tiers.py, one per setting (53, Missouri) ---------------------------------
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
_g_20_sales|$G WORK_DAYS=20 HUFF=sales
_g_20_surplus|$G WORK_DAYS=20 HUFF=surplus
_g_25_sales|$G WORK_DAYS=25 HUFF=sales
_g_25_surplus|$G WORK_DAYS=25 HUFF=surplus
_g_30_sales|$G WORK_DAYS=30 HUFF=sales
_g_30_surplus|$G WORK_DAYS=30 HUFF=surplus
_g_40_sales|$G WORK_DAYS=40 HUFF=sales
_g_40_surplus|$G WORK_DAYS=40 HUFF=surplus
_c_10_l6|$G HUFF=sales WORK_DAYS=10 LAMBDA=retail:6
_c_10_l8|$G HUFF=sales WORK_DAYS=10 LAMBDA=retail:8
_c_20_l6|$G HUFF=sales WORK_DAYS=20 LAMBDA=retail:6
_c_20_l8|$G HUFF=sales WORK_DAYS=20 LAMBDA=retail:8
_c_40_l6|$G HUFF=sales WORK_DAYS=40 LAMBDA=retail:6
_c_40_l8|$G HUFF=sales WORK_DAYS=40 LAMBDA=retail:8
_c_10_l6all|$G HUFF=sales WORK_DAYS=10 LAMBDA=retail:6,medical:6,specialty:6
_c_20_l6all|$G HUFF=sales WORK_DAYS=20 LAMBDA=retail:6,medical:6,specialty:6
_c_40_l6all|$G HUFF=sales WORK_DAYS=40 LAMBDA=retail:6,medical:6,specialty:6
_c_grav20|$C WORK_DAYS=20
_c_grav40|$C WORK_DAYS=40
_c_hyb20_40|$C WORK_HYBRID=20 WORK_DAYS=40
_c_hyb40_40|$C WORK_HYBRID=40 WORK_DAYS=40
EOF
)
build() {   # build <STATE> <TAG> <env...>   (@ stands for a space inside a value)
  local st=$1 tag=$2; shift 2; [ "$tag" = "-" ] && tag=""
  local args=(); for a in "$@"; do args+=("${a//@/ }"); done
  env STATE=$st "${args[@]}" TAG=$tag $PY analysis/public_travel_tiers.py > logs/tiers_${st}${tag:-_none}.log 2>&1 || echo "FAIL $st $tag"
}
export -f build; export PY
if step 2; then
echo "$BUILDS" | while IFS='|' read -r tag e; do echo "29 $tag${e:+ $e}"; done | xargs -P 2 -L 1 bash -c 'build "$@"' _   # no trailing blank: xargs -L joins such lines
fi

# ---- 3. Benchmark and target: compare_shares.csv (adopted outcome; Advan-fitted, counties held out) ------------------------
if step 3; then
$PY analysis/public_vs_advan_compare.py > logs/public_vs_advan_compare.log 2>&1
fi

# ---- 4. Stage 1, nested: each class's setting with the scored county left out -----------------------------------------------
if step 4; then
$PY analysis/public_stage1_nested.py > logs/public_stage1_nested.log 2>&1
fi

# ---- 5. Stage 2, outer loop (245 structures x 3 modes, 2 workers; exports segment_corrections_mo.pkl) -----------------------
if step 5; then
PROCS=2 $PY analysis/public_adjusted_nested.py > logs/adj_nested.log 2>&1
$PY analysis/score_segments.py > logs/score_segments_nested.log 2>&1
fi

# ---- 6. public_adjusted_pairs_trnear.csv: the 2026-10-18 structure on the 2026-10-18 base (read by tie_footprint.py,
if step 6; then
#         public_activity_space.py, directions_per_tract.py) ------------------------------------------------------------------
LEGACY=1 CLASS5=_g_40_sales OUTTAG=_c5_g_40_sales $PY analysis/assemble_public_by_class.py
BASE=public_model_pairs_tiers_byclass_c5_g_40_sales.csv SPLIT3=1 C5AS="class 2" DIST_BY_RANK=1 CORE= CORE_NEAR=1 TRANSFER=1 \
  RC_PF=1.0 COMMUTE=commute_rank,dest_order,dest_class POOLED= OUTTAG=_trnear $PY analysis/public_adjusted_model.py > logs/adj_trnear.log 2>&1
fi

# ---- 7. Kansas: the Missouri-chosen settings built for Kansas, assembled, corrected, scored -------------------------------------
if step 7; then
OUTTAG=_nested $PY analysis/assemble_public_by_class.py                 # Missouri, for the record
for tag in $($PY -c "import pandas as pd; c=pd.read_csv('analysis/public_stage1_choice.csv', keep_default_na=False); print(' '.join(sorted(set(c[c.county=='ALL'].insample_choice))))"); do
  e=$(echo "$BUILDS" | awk -F'|' -v t="$tag" '$1==t {print $2}')
  build 20 "$tag" $e
done
STATE=20 OUTTAG=_nested $PY analysis/assemble_public_by_class.py
$PY analysis/ks_advan_fitted.py > logs/ks_advan_fitted.log 2>&1
BASE=public_model_pairs_tiers_20_byclass_nested.csv PKL=segment_corrections_mo.pkl $PY analysis/transfer_adjustments.py > logs/transfer_adjustments.log 2>&1
$PY analysis/score_ks.py > logs/score_ks.log 2>&1
fi

# ---- 8. travel_tier_pull_cv.py (adopted 8 FACTORS baseline; nested guard) ----------------------------------------------------
if step 8; then
$PY analysis/travel_tier_pull_cv.py > logs/travel_tier_pull_cv.log 2>&1
fi

