#!/bin/zsh
# Rebuilds the county-level figures: travel maps, alignment maps, outlet spillover charts and triptychs.
# The civic interest area maps and the calculation diagram are built by scripts/reproduce.sh (stage figures).
#   analysis: travel model -> coverage model -> county table -> outlet model -> three-county table
#   (od_mo_2026.csv carries population-calibrated visits: analysis/build_calibration.py, run once after the raw build)
#   flows:    township shares (Jan-Sep, pass-through discounted) -> alignment data
#   render:   travel maps, alignment maps, outlet chart, triptychs (5.5 in at 300 dpi)
set -e
ROOT=${0:A:h}
PY="$ROOT/.venv/bin/python -I"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
cd /tmp
eval $PY $ROOT/analysis/travel_model.py
eval $PY $ROOT/analysis/coverage_model.py > /dev/null
eval $PY $ROOT/analysis/spillover_v2.py > /dev/null   # county table the outlet model reads
eval $PY $ROOT/analysis/crossover_compare.py > /dev/null   # crossover = distinct residents outside (needs build_unique_od.py)
eval $PY $ROOT/analysis/spillover_outlets.py 2>/dev/null | sed -n '/## final model/,$p'
eval $PY $ROOT/flows/build_cousub_shares.py jan-sep > /dev/null
eval $PY $ROOT/coverage/storymap/rebuild_county_files.py > /dev/null   # county story maps from the statewide export
eval $PY $ROOT/coverage/build_alignment.py > /dev/null
eval $PY $ROOT/analysis/three_counties_vs_models.py > /dev/null

cd $ROOT/flows
./render_print.sh cousub_markets_print.html travel
python3 -m http.server 8765 --bind 127.0.0.1 >/dev/null 2>&1 &
SRV=$!; sleep 1
shot() {   # shot <url path> <png name>
  local url="http://127.0.0.1:8765/$1"
  local h=$("$CHROME" --headless=new --disable-gpu --window-size=528,1400 --virtual-time-budget=40000 --dump-dom "$url" 2>/dev/null | grep -o 'data-height="[0-9]*"' | grep -o '[0-9]*')
  h=$((h + 10))   # the measured height can come in short of the footer; a margin keeps the source line whole
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=3.125 --window-size=528,$h \
    --virtual-time-budget=40000 --screenshot="print/$2" "$url" 2>/dev/null
  sips -s dpiWidth 300 -s dpiHeight 300 "print/$2" >/dev/null
  echo "print/$2"
}
for v in audrain_all boone_all boone_no_broadcast osage_all; do shot "alignment_print.html?v=$v" "alignment_${v}_2026_03.png"; done
shot "outlet_spillover_print.html" "outlet_spillover_2026_03.png"
shot "model_diagram_print.html" "model_diagram.png"
kill $SRV
cd print && eval $PY - <<'PYEOF'
from PIL import Image
for name, files in (("travel_triptych_2026_jan_sep.png", [f"travel_{c}_2026_jan_sep.png" for c in ("audrain", "boone", "osage")]),
                    ("alignment_triptych_2026_03.png", [f"alignment_{c}_all_2026_03.png" for c in ("audrain", "boone", "osage")])):
    ims = [Image.open(f).convert("RGB") for f in files]
    gap = 90; w = sum(i.width for i in ims) + gap * 2; h = max(i.height for i in ims)
    out = Image.new("RGB", (w, h), "white"); x = 0
    for i in ims:
        out.paste(i, (x, 0)); x += i.width + gap
    out.save(name, dpi=(300, 300)); print(name, out.size)
PYEOF
