#!/bin/zsh
# One public_travel_tiers.py build per default weight changed (see public_default_sensitivity.py).
cd "$(dirname $0)/.."
B=(RETAIL=tac DRAWMODE=cap REC_CODES=71----)
run() { tag=$1; shift; env $B "$@" TAG=$tag .venv/bin/python -I analysis/public_travel_tiers.py > logs/sens$tag.log 2>&1 || echo "FAIL $tag"; }
mkdir -p logs
run _s_ref &
run _s_wfh WFH=1 &
run _s_days15 WORK_DAYS=15 &
run _s_shop05 MULT=retail:0.5 &
run _s_huffhome LEAK=huffhome &
wait
run _s_alpha05 HUFF_ALPHA=0.5 &
run _s_alpha15 HUFF_ALPHA=1.5 &
run _s_trips LD_DAYS=0 &
run _s_recvis05 MULT=recreation:0.5,visiting:0.5 &
run _s_recvis2 MULT=recreation:2,visiting:2 &
wait
run _s_medspec05 MULT=medical:0.5,specialty:0.5 &
run _s_medspec2 MULT=medical:2,specialty:2 &
run _s_circ10 CIRC=1.0 &
run _s_circ14 CIRC=1.4 &
run _s_commurban "URBAN_CLASSES=class 3" &
wait
