"""Before/after report for the 2026-10-17 enrichment re-run and the spillover model.

Inputs, all in coverage/rerun_2026_10_17/:
  before_articles.csv, before_geoids.csv, before_places.csv        places re-run set (2,859), before
  statewide_before_*.csv                                             March statewide stories (1,810), before
  after_articles.csv, after_geoids.csv, after_places.csv            the whole re-run universe, after
  source_scope.csv                                                   publisher gazetteer scope
  before_spillover_outlets_current_model.csv, before_model.txt      the adopted model on the before data
  after_spillover_outlets.csv, after_model.txt                       the adopted model on the after data
Writes coverage/rerun_2026_10_17/REPORT.md.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

root = Path(__file__).resolve().parents[1]
R = root / "coverage/rerun_2026_10_17"
FIPS = {'AL': '01', 'AK': '02', 'AZ': '04', 'AR': '05', 'CA': '06', 'CO': '08', 'CT': '09', 'DE': '10', 'DC': '11',
        'FL': '12', 'GA': '13', 'HI': '15', 'ID': '16', 'IL': '17', 'IN': '18', 'IA': '19', 'KS': '20', 'KY': '21',
        'LA': '22', 'ME': '23', 'MD': '24', 'MA': '25', 'MI': '26', 'MN': '27', 'MS': '28', 'MO': '29', 'MT': '30',
        'NE': '31', 'NV': '32', 'NH': '33', 'NJ': '34', 'NM': '35', 'NY': '36', 'NC': '37', 'ND': '38', 'OH': '39',
        'OK': '40', 'OR': '41', 'PA': '42', 'RI': '44', 'SC': '45', 'SD': '46', 'TN': '47', 'TX': '48', 'UT': '49',
        'VT': '50', 'VA': '51', 'WA': '53', 'WV': '54', 'WI': '55', 'WY': '56'}
rd = lambda p: pd.read_csv(R / p, dtype=str)
out: list[str] = []
w = out.append


def table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |")
    return "\n".join(lines)


# ---------------------------------------------------------------- enrichment
ba = pd.concat([rd("before_articles.csv"), rd("statewide_before_articles.csv"), rd("sports_before_articles.csv")]).drop_duplicates("id").set_index("id")
bg = pd.concat([rd("before_geoids.csv"), rd("statewide_before_geoids.csv"), rd("sports_before_geoids.csv")]).drop_duplicates()
bp = pd.concat([rd("before_places.csv"), rd("statewide_before_places.csv"), rd("sports_before_places.csv")])
aa = rd("after_articles.csv").set_index("id")
ag = rd("after_geoids.csv")
ap = rd("after_places.csv")
sc = rd("source_scope.csv")
allowed = sc.assign(f=sc.state.map(FIPS)).groupby("source_id").f.apply(set)
groups = {
    "Places re-run, Missouri": set(open(R / "ids_Mizzou-Missouri-State.txt").read().split()),
    "Places re-run, Washington": set(open(R / "ids_WSU-Washington-State.txt").read().split()),
    "March statewide stories": set(open(R / "statewide_ids.txt").read().split()),
    "March sports stories (home-team rule)": set(open(R / "sports_ids.txt").read().split()),
}
aa = aa[aa.index.isin(ba.index)]
x = aa.join(ba[["status", "scope", "point_place", "point_geoid", "point_geoid_level"]], rsuffix="_b")
n = len(x)
w("# Re-run of March 2026 enrichment: before and after\n")
w("Written for: the authors. Enrichment re-run 2026-10-17 on #736-#739; spillover model refitted on the result.\n")
w("## 1. What was re-run\n")
w(table(pd.DataFrame([{"Set": k, "Articles": len(v)} for k, v in groups.items()] + [{"Set": "All (deduplicated)", "Articles": n}])))
w("\nChanges carried by the re-run: the model is told where the publication is (#736); a game is centred on the "
  "publication's own team (#738); a statewide story is filed under its own state and scope-v3 keeps state-named "
  "places local (#738, #739); a long partial story is enriched rather than skipped, and the TownNews premium-content "
  "notice is removed (#739); 970 March bodies stored as ROT47 ciphertext were decoded (#736, #737).\n")

w("## 2. Status\n")
st = pd.crosstab(x.status_b.fillna("-"), x.status.fillna("-"), margins=True, margins_name="total")
st.index.name = "before \\ after"
w(table(st.reset_index()))

w("\n## 3. Scope\n")
sb, sa = x.scope_b.fillna("-"), x.scope.fillna("-")
w(f"Unchanged {int((sb == sa).sum())} of {n}; changed {int((sb != sa).sum())}.\n")
cnt = pd.DataFrame({"before": sb.value_counts(), "after": sa.value_counts()}).fillna(0).astype(int)
cnt.index.name = "scope"
w(table(cnt.sort_values("before", ascending=False).reset_index()))
sw = x[x.index.isin(groups["March statewide stories"])]
mv = pd.crosstab(sw.scope_b.fillna("-"), sw.scope.fillna("-"))
w(f"\nThe {len(sw)} March statewide stories now: " + ", ".join(f"{k} {v}" for k, v in sw.scope.fillna("-").value_counts().items()) + ".\n")

w("## 4. Story point\n")
pb, pa = x.point_geoid_b.fillna(""), x.point_geoid.fillna("")
both = (pb != "") & (pa != "") & (pb != pa)
rows = [("unchanged", int((pb == pa).sum())), ("had none, now has one", int(((pb == "") & (pa != "")).sum())),
        ("had one, now none", int(((pb != "") & (pa == "")).sum())), ("moved within the same state", int((both & (pa.str[:2] == pb.str[:2])).sum())),
        ("moved to another state", int((both & (pa.str[:2] != pb.str[:2])).sum()))]
w(table(pd.DataFrame(rows, columns=["Point", "Articles"])))
lvl = pd.DataFrame({"before": x.point_geoid_level_b.fillna("none").value_counts(), "after": x.point_geoid_level.fillna("none").value_counts()}).fillna(0).astype(int)
lvl.index.name = "point level"
w("\n" + table(lvl.reset_index()))
cross = x[both & (pa.str[:2] != pb.str[:2])]
if len(cross):
    w(f"\nCross-state moves (first 30 of {len(cross)}):\n")
    w(table(cross[["title", "point_place_b", "point_place"]].head(30).rename(columns={"title": "Story", "point_place_b": "Before", "point_place": "After"})))

w("\n## 5. Place and county codes\n")
src = x.source_id


def codes(g, levels):
    s = g[g.geoid_level.isin(levels)].groupby("article_id").geoid.apply(set)
    return s.reindex(x.index).apply(lambda v: v if isinstance(v, set) else set())


rows = []
for name, lv in (("place", ["place"]), ("county", ["county"])):
    b, a = codes(bg, lv), codes(ag, lv)
    same = sum(p == q for p, q in zip(b, a))
    out_b = sum(sum(c[:2] not in allowed.get(s, set()) for c in v) for v, s in zip(b, src))
    out_a = sum(sum(c[:2] not in allowed.get(s, set()) for c in v) for v, s in zip(a, src))
    rows.append({"Codes": name, "Articles with identical set": f"{same} of {n}", "Before": sum(map(len, b)), "After": sum(map(len, a)),
                 "Added": sum(len(q - p) for p, q in zip(b, a)), "Removed": sum(len(p - q) for p, q in zip(b, a)),
                 "Outside publisher scope before": out_b, "after": out_a})
w(table(pd.DataFrame(rows)))
w(f"\nPlace rows: {len(bp):,} before, {len(ap):,} after. "
  f"Articles with any place row: {bp.article_id.nunique():,} before, {ap.article_id.nunique():,} after.\n")

# ---------------------------------------------------------------- model
w("## 6. Spillover model\n")
bm, am = (R / "before_model.txt").read_text(), (R / "after_model.txt").read_text()


def coefs(txt):
    block = txt.split("## final model", 1)[1].splitlines()[2:7]
    return {l.split()[0]: (float(l.split()[1]), float(l.split()[3])) for l in block if l.strip() and l.split()[0] != "coef"}


def fitline(txt):
    m = re.search(r"fitted on (\d+) well-collected outlets in (\d+) counties \(of (\d+)\); held-out error ([\d.]+)", txt)
    return m.groups() if m else ("?",) * 4


cb, ca = coefs(bm), coefs(am)
fb, fa = fitline(bm), fitline(am)
w(table(pd.DataFrame([
    {"": "Outlets fitted (well collected)", "Before": fb[0], "After": fa[0]},
    {"": "Counties", "Before": fb[1], "After": fa[1]},
    {"": "All outlets with 10+ placed stories", "Before": fb[2], "After": fa[2]},
    {"": "Held-out error (points)", "Before": fb[3], "After": fa[3]},
] + [{"": f"{k} (coef, p)", "Before": f"{cb[k][0]:+.2f} ({cb[k][1]:.3f})" if k in cb else "",
      "After": f"{ca[k][0]:+.2f} ({ca[k][1]:.3f})" if k in ca else ""} for k in dict.fromkeys(list(cb) + list(ca)) if k != "Intercept"])))

ob = rd("before_spillover_outlets_current_model.csv").set_index("outlet")
oa = rd("after_spillover_outlets.csv").set_index("outlet")
for c in ("rate", "expected", "placed"):
    ob[c], oa[c] = ob[c].astype(float), oa[c].astype(float)
j = oa[["fips", "placed", "rate", "expected", "good"]].join(ob[["placed", "rate", "expected", "good"]], rsuffix="_b", how="outer")
j["d_rate"] = 100 * (j.rate - j.rate_b)
w("\n### The three counties and the Springfield area\n")
lines = []
for name, pat in (("Audrain", r"^Audrain:"), ("Boone", r"^Boone:"), ("Osage", r"^Osage:"), ("Greene", r"Greene:"), ("Webster", r"Webster:"), ("Barry", r"Barry:")):
    gb = re.search(pat + r".*", bm, re.M); ga = re.search(pat + r".*", am, re.M)
    lines.append({"County": name, "Before": gb.group(0).split(":", 1)[1].split(";")[0].strip() if gb else "",
                  "After": ga.group(0).split(":", 1)[1].split(";")[0].strip() if ga else ""})
w(table(pd.DataFrame(lines)))
w("\n### Outlets whose spillover moved most (percentage points)\n")
mv = j.dropna(subset=["d_rate"]).reindex(j.d_rate.abs().sort_values(ascending=False).index).head(20)
w(table(mv.reset_index()[["outlet", "placed_b", "placed", "rate_b", "rate", "d_rate"]].assign(
    rate_b=lambda d: (100 * d.rate_b).round(0), rate=lambda d: (100 * d.rate).round(0), d_rate=lambda d: d.d_rate.round(1)).rename(
    columns={"outlet": "Outlet", "placed_b": "Stories before", "placed": "after", "rate_b": "Spillover before %", "rate": "after %", "d_rate": "change"})))
gin = set(j.index[(j.good == "True") & (j.good_b != "True")]); gout = set(j.index[(j.good_b == "True") & (j.good != "True")])
w(f"\nQuality set: {len(gin)} outlets newly well collected ({', '.join(sorted(gin)) or 'none'}); "
  f"{len(gout)} no longer ({', '.join(sorted(gout)) or 'none'}).\n")

# volume floor
d = oa.copy()
for c in ("broadcast", "crowded_weekly", "log_border_mi", "log_print"):
    d[c] = d[c].astype(float)
# HISTORICAL: this section scores the 2026-10-17 snapshot (after_spillover_outlets.csv) with the model and outlet set of
# that day -- three outlets left out, border term for every outlet. The current model, its outlet set (Mid Rivers and
# the Greene County Commonwealth fitted in the county they cover; campus papers out) and its floor-20 / floor-10
# comparison are in spillover_outlets.py (held-out table) and spillover_common.py. Not used for current figures.
NOT_FITTED = {"Greene County Commonwealth", "Three Rivers Publishing", "Mid Rivers Newsmagazine"}
FINAL = "rate ~ broadcast + crowded_weekly + log_border_mi + log_print"


# Both floors are scored on the SAME outlets -- every well-collected outlet with 10+ placed stories -- each
# county's outlets predicted by a model trained, at that floor, on the other counties. Scoring each floor on
# its own fit set would compare errors over different outlets.
EVAL = d[(d.good == "True") & ~d.index.isin(NOT_FITTED) & (d.placed >= 10)]


def loo(train_all):
    e = []
    for fp in EVAL.fips.unique():
        tr, te = train_all[train_all.fips != fp], EVAL[EVAL.fips == fp]
        e += list((smf.glm(FINAL, tr, family=sm.families.Binomial()).fit().predict(te) - te.rate).abs())
    return 100 * np.mean(e), 100 * np.median(e)


rows = []
for floor in (10, 20):
    g = d[(d.good == "True") & ~d.index.isin(NOT_FITTED) & (d.placed >= floor)]
    m, md = loo(g)
    rows.append({"Volume floor (placed stories)": floor, "Outlets fitted": len(g), "Counties": g.fips.nunique(),
                 "Held-out mean miss": round(m, 2), "median": round(md, 2)})
w("### Volume floor for the fit (2026-10-17 snapshot and model; current comparison: spillover_outlets.py)\n")
w(table(pd.DataFrame(rows)))
(R / "REPORT.md").write_text("\n".join(out) + "\n")
print("\n".join(out))
