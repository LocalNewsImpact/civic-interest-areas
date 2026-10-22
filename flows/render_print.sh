#!/bin/zsh
# Render the print figures: 528 CSS px wide at 3.125x = 1650 px = 5.5 in at 300 dpi; height measured from the page.
# usage: render_print.sh <page.html> <outprefix> [extra query]
cd "$(dirname "$0")"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
python3 -m http.server 8765 --bind 127.0.0.1 >/dev/null 2>&1 &
SRV=$!; sleep 1
for c in Audrain Boone Osage; do
  url="http://127.0.0.1:8765/$1?county=$c$3"
  h=$("$CHROME" --headless=new --disable-gpu --window-size=528,1400 --virtual-time-budget=30000 --dump-dom "$url" 2>/dev/null | grep -o 'data-height="[0-9]*"' | grep -o '[0-9]*')
  out="print/$2_$(echo $c | tr A-Z a-z)_${PERIOD:-2026_jan_sep}.png"
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=3.125 --window-size=528,$h \
    --virtual-time-budget=30000 --screenshot="$out" "$url" 2>/dev/null
  sips -s dpiWidth 300 -s dpiHeight 300 "$out" >/dev/null
  echo "$out $(sips -g pixelWidth -g pixelHeight "$out" | awk '/pixel/{printf "%s ", $2}')(css height $h)"
done
kill $SRV
