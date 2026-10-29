"""The network tie of a study town (flows/market_patterns.py, adopted 2026-10-17) as a function of its travel input,
for the civic interest area scripts (analysis/confidence_layer.py, flows/area_ensemble.py), which load it with
runpy.run_path and read tie_map and market_patterns.py's names from its globals.

  tie(H, X) = travel(H -> X) x (1 + 0.3 out + 0.3 in + 0.7 shared places + 0.7 shared coverage), the gate on shared
  terms, the spatial lag and direction boost, home 100 -- the maps' own code, run unchanged up to the figure
  (market_patterns.py, through the weights); only the travel input differs.

Usage (as a library): sys.argv = ["network_tie.py", <region>]; runpy.run_path(".../analysis/network_tie.py")
HEX_KM (environment) sets the hexagon size, as in market_patterns.py.
"""
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
FLOWS = root / "flows"
REGION_ = sys.argv[1] if len(sys.argv) > 1 else "columbia"
sys.argv = ["market_patterns.py", REGION_]
sys.path.insert(0, str(root / "analysis"))
_src = open(FLOWS / "market_patterns.py").read()
# read-only: market_patterns.py writes market_patterns.json before the cut; loading the library must not rewrite it
_src = _src.replace('json.dump(', '(lambda *a, **k: None)(').replace('open(R / "market_patterns.json", "w")', "None")
_cut = _src.index('maps = {"hexes": hexes, "towns": {}}')
assert '"w")' not in _src[:_cut], "market_patterns.py opens a file for writing before the cut; neutralise it here"
__file__ = str(FLOWS / "market_patterns.py")
exec(compile(_src[:_cut], str(FLOWS / "market_patterns.py"), "exec"))


# --- the tie map (the loop body of market_patterns.py, one travel input) ----------------------------------------------
def tie_map(town, Hk, weights=BASE_W):
    Hk_u, Hk = Hk, norm_hex(Hk)             # busiest hexagon = 1 (market_patterns.norm_hex); Hk_u: busiest place = 1
    cu = COV[town]
    own_u = {P["bg_unit"].get(h) for h in town_bgs(town)} | {HOME_PLACE[town]}
    OV = {X: overlap_of(Hk, own_u, X) for X in place_outlets if X not in own_u}
    h_cov = cov_dist([o for o, al in by_outlet.items() if home_of(al[0]) == STUDY[town] and o not in EXCLUDE])
    mkt = {u_ for u_, w in Hk_u.items() if w >= 0.05}
    inm_ = lambda d_: {u_: w for u_, w in d_.items() if u_ in mkt}
    SC = {X: overlap_dists(inm_(h_cov), inm_(cov_dist(place_outlets[X])), own_u | {X}) for X in place_outlets if X not in own_u}
    wo, wi, wv, wc = weights
    raw = {}
    for k, u in unit_at.items():
        t_ = tr_at(Hk, k, u)
        if t_ <= 0:
            continue
        xk = hex_place.get(k) or u
        o_, i_ = cu["out"].get(k, 0), cu["in"].get(k, 0)
        gate = 1.0 if (o_ + i_) >= 0.10 else 0.0
        raw[k] = min(DCAP, t_ * (1 + wo * o_ + wi * i_ + gate * (wv * OV.get(xk, 0) + wc * SC.get(xk, 0))))
    if raw:
        raw = spatial(raw, home_hexes_of[town])
    out_ = {k: 100 * x for k, x in raw.items()}
    for k in home_hexes_of[town]:
        out_[k] = 100.0
    return out_
