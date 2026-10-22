#!/bin/zsh
# The same three tables as the before snapshot, for every article in the re-run (universe.txt).
export PATH=/opt/homebrew/bin:/opt/homebrew/share/google-cloud-sdk/bin:$PATH
export PGPASSWORD="$(gcloud secrets versions access latest --secret=db-password --project=mizzou-news-crawler)"
R=/Users/kiesowd/VSCode/advan/coverage/rerun_2026_10_17
psql -h 127.0.0.1 -p 5439 -U mizzou_user -d mizzou -q -v ON_ERROR_STOP=1 <<SQL
create temp table u(id varchar primary key);
\copy u from '$R/universe_all.txt'
\copy (select a.id, a.status, a.title, cl.source_id, e.enriched_at, e.scope, e.skip_reason, e.point_place, e.point_method, e.point_geoid, e.point_geoid_level, e.geoids, e.geo_skip_reason from u join articles a on a.id=u.id join candidate_links cl on cl.id=a.candidate_link_id left join article_enrichment e on e.article_id=a.id) to '$R/after_articles.csv' with csv header
\copy (select g.article_id, g.geoid, g.geoid_level, g.is_primary, g.source from u join article_geoids g on g.article_id=u.id) to '$R/after_geoids.csv' with csv header
\copy (select p.article_id, p.full_name, p.place_type, p.city, p.county, p.state, p.geoid, p.geoid_level, p.is_point from u join article_places p on p.article_id=u.id) to '$R/after_places.csv' with csv header
\copy (select source_id, state from source_gazetteer_scope) to '$R/source_scope.csv' with csv header
SQL
wc -l $R/after_*.csv
