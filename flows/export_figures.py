"""Export the civic interest area and coverage density figures for the datadesk builder (2026-10-21).

For every built area, market_pattern_print.html is rendered headless with ?figure=1 (area map) and
?figure=1&measure=coverage (coverage density); the figure it writes into <pre id="figure"> -- every shape already
projected into the map's W x H frame, values on the hexagons -- is saved as one JSON file per map:

    flows/figures/<region>/<town>-<rank>-area.json
    flows/figures/<region>/<town>-<rank>-coverage.json

The two files of one area share the frame, so the builder's swipe lines them up exactly. Upload with
`gsutil -m cp -r flows/figures gs://mizzou-news-maps-data/civic-interest/` (the bucket datadesk's GCS source reads).
Needs the page served: `python3 -m http.server 8765 --bind 127.0.0.1` in flows/.

Usage: export_figures.py [region ...]     (default: every area in AREAS)"""
import html
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BASE = "http://127.0.0.1:8765/market_pattern_print.html"
# the built towns; their areas are every market market_patterns.py keeps for them (the count follows the fit)
BUILT = {"columbia": ("Columbia", "Mexico", "Linn"), "springfield": ("Springfield",), "joplin": ("Joplin",),
         "kirksville": ("Kirksville",)}
_REGIONS = json.load(open(HERE / "regions.json"))
AREAS = {r_: [(t_, m_["rank"]) for t_ in towns_
              for m_ in json.load(open(HERE.parent / _REGIONS[r_]["out"] / "market_pattern_maps.json"))["towns"][t_]]
         for r_, towns_ in BUILT.items()}


def figure(region, town, rank, measure):
    q = f"region={region}&town={quote(town)}&rank={rank}&figure=1" + ("&measure=coverage" if measure == "coverage" else "")
    for attempt in range(3):          # a capture can come back before the page has drawn (seen once, 2026-10-21)
        dom = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--window-size=528,920",
                              f"--virtual-time-budget={30000 + 15000 * attempt}", "--dump-dom", f"{BASE}?{q}"],
                             capture_output=True, text=True, timeout=180).stdout
        m = re.search(r'<pre id="figure">(.*?)</pre>', dom, re.S)
        if m:
            fig = json.loads(html.unescape(m.group(1)))
            if fig.get("hexes"):
                return fig
    raise RuntimeError(f"no figure for {region} {town} {rank} {measure}")


def main():
    regions = sys.argv[1:] or list(AREAS)
    for region in regions:
        out = HERE / "figures" / region
        out.mkdir(parents=True, exist_ok=True)
        for town, rank in AREAS[region]:
            for measure in ("area", "coverage"):
                fig = figure(region, town, rank, measure)
                p = out / f"{town.lower().replace(' ', '-')}-{rank}-{measure}.json"
                p.write_text(json.dumps(fig, separators=(",", ":")))
                print(f"{p.relative_to(HERE)}  {len(fig['hexes'])} hexagons  {p.stat().st_size // 1024} KB", flush=True)


if __name__ == "__main__":
    main()
