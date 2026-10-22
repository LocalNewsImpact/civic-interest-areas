#!/bin/zsh
# Rebuild coverage/storymap/statewide_2026_03_articles.json from production, through datadesk's
# production shell (~/.config/datadesk/dd-prod; the local datadesk checkout must equal the deployed tag).
# Same definition as the original export: Visual 13's spec, March 2026, every publisher; each article's
# central county from its enrichment point, its counties from the point, its mention codes and any
# geography a person placed (ArticlePlaceManual), all rolled up to counties.
export PATH=/opt/homebrew/bin:/opt/homebrew/share/google-cloud-sdk/bin:$PATH
OUT=${1:-/Users/kiesowd/VSCode/advan/coverage/storymap/statewide_2026_03_articles.json}
~/.config/datadesk/dd-prod shell -c "
import json, copy
from visuals.models import Visual
from visuals.corpus import _base_queryset
from explorer.models import ArticlePlaceManual
from datasets.geo import to_county
v = Visual.objects.get(id=13)
spec = copy.deepcopy(v.spec)
spec['publishers'] = []
spec['from'], spec['to'] = '2026-03-01', '2026-03-31'
qs = _base_queryset(spec, v.datasets)
rows = {}
for aid, src, sname, scounty, stype, pg, pl, raw in qs.values_list('id', 'candidate_link__source_id', 'candidate_link__source__canonical_name',
        'candidate_link__source__county', 'candidate_link__source__type', 'enrichment__point_geoid', 'enrichment__point_geoid_level', 'enrichment__geoids'):
    r = rows.setdefault(str(aid), {'id': str(aid), 'source': str(src), 'publisher': sname, 'publisher_county': scounty,
                                   'publisher_type': stype, 'central': None, 'counties': set()})
    if pg:
        c = to_county(str(pg), pl or 'place')
        if c: r['central'] = c; r['counties'].add(c)
    try: places = json.loads(raw) if raw else []
    except (TypeError, ValueError): places = []
    for p in places or []:
        c = to_county(str(p), 'place')
        if c: r['counties'].add(c)
for aid, geoid, level in ArticlePlaceManual.objects.filter(article_id__in=qs.values('id')).values_list('article_id', 'geoid', 'geoid_level'):
    if geoid and str(aid) in rows:
        c = to_county(str(geoid), level or 'place')
        if c: rows[str(aid)]['counties'].add(c)
out = [{**r, 'counties': sorted(r['counties'])} for r in rows.values()]
json.dump({'spec': spec, 'datasets': v.datasets, 'articles': out}, open('$OUT', 'w'), default=str)
pubs = {}
for r in out: pubs[(r['publisher_county'], r['publisher'])] = pubs.get((r['publisher_county'], r['publisher']), 0) + 1
print('articles', len(out), 'placed', sum(1 for r in out if r['counties']), 'newsrooms', len(pubs), 'publisher counties', len({k[0] for k in pubs}))
" 2>&1 | grep -v "succeeded\|imported automatically" | tail -3
