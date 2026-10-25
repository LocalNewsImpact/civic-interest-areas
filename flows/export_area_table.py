"""Export every civic interest area as one data table for the datadesk builder (2026-10-22).

The user's split: the Advan travel model runs here and its result is uploaded to the builder as a CSV; the builder
draws the hexagons, frame, borders and labels itself, and computes coverage density from the corpus. One row per
hexagon of each area's drawn footprint (market_pattern_print.html?table=1):

  region, town, area      which civic interest area (area = 1, 2, 3: I, II, III)
  residents, share        residents following the area's travel pattern, and their share of the town
  hex                     hexagon id "q,r": 3 km pointy-top axial grid, 1.5 km circumradius, on the plane
                          x = lon * 111.32 * cos(38.7 deg), y = lat * 110.57 (km): centre x = 1.5 * sqrt(3) * (q + r/2),
                          y = 1.5 * 1.5 * r
  lon, lat                hexagon centre
  travel                  the network tie of the adopted-setting map, home = 100 (0 where not shaded)
  lift                    how much news ties add, 0.10 = 10% (0 below 10%)
  shown                   1 = drawn shaded by the map's selection rule; 0 = empty, inside the area's outline
  home                    1 = the home town's own hexagons
  p                       share of the settings ensemble's members that draw the hexagon (flows/area_ensemble.py);
                          rows are the adopted map's hexagons, its outline's, and every hexagon with p >= 0.1

Writes flows/civic_interest_areas.csv. Needs the page served on 127.0.0.1:8765 (python3 -m http.server in flows/)."""
import csv
import html
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

from export_figures import AREAS, BASE, CHROME

HERE = Path(__file__).resolve().parent


def table(region, town, rank):
    q = f"region={region}&town={quote(town)}&rank={rank}&table=1&prob=0"
    for attempt in range(3):
        dom = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--window-size=528,920",
                              f"--virtual-time-budget={30000 + 15000 * attempt}", "--dump-dom", f"{BASE}?{q}"],
                             capture_output=True, text=True, timeout=180).stdout
        m = re.search(r'<pre id="table">(.*?)</pre>', dom, re.S)
        if m:
            rows = json.loads(html.unescape(m.group(1)))
            if rows:
                return rows
    raise RuntimeError(f"no table for {region} {town} {rank}")


def main():
    rows = []
    for region, areas in AREAS.items():
        for town, rank in areas:
            got = table(region, town, rank)
            print(f"{region:12} {town:12} {rank}  {len(got)} hexagons, {sum(r['shown'] for r in got)} shaded", flush=True)
            rows += got
    out = HERE / "civic_interest_areas.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {out.name}: {len(rows)} rows, {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
