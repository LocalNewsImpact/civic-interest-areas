#!/bin/zsh
# Per-source collection quality for March 2026 local news, from production.
# Same definition as the first export, except full length is measured on the body as it now stands,
# length(a.text): repair-rot47-bodies rewrites `text` and leaves `text_length` as it was.
export PATH=/opt/homebrew/bin:/opt/homebrew/share/google-cloud-sdk/bin:$PATH
export PGPASSWORD="$(gcloud secrets versions access latest --secret=db-password --project=mizzou-news-crawler)"
OUT=${1:-/Users/kiesowd/VSCode/advan/coverage/source_quality_2026_03.csv}
psql -h 127.0.0.1 -p 5439 -U mizzou_user -d mizzou -v ON_ERROR_STOP=1 -c "\copy (
select s.id source_id, s.canonical_name, s.county, s.type, coalesce(s.has_paywall,false) has_paywall, coalesce(s.requires_login,false) requires_login,
  count(a.id) filter (where a.status in ('enriched','enrichment_skipped')) local_news,
  count(a.id) filter (where a.status = 'text_unavailable') text_unavailable,
  count(a.id) filter (where a.status not in ('wire','obituary','not_article','weather','opinion','non_english','curated_out')) attempted,
  percentile_cont(0.5) within group (order by length(a.text)) filter (where a.status in ('enriched','enrichment_skipped')) median_text_length,
  count(a.id) filter (where a.status in ('enriched','enrichment_skipped') and length(coalesce(a.text,'')) < 600) short_texts
from sources s left join candidate_links cl on cl.source_id = s.id
left join articles a on a.candidate_link_id = cl.id and a.publish_date >= '2026-03-01' and a.publish_date < '2026-04-01'
group by 1,2,3,4,5,6) to '$OUT' with csv header"
