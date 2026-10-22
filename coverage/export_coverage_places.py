"""March 2026 local news from Audrain, Boone and Osage newsrooms -> one row per article x place it names.

Same article set as flows/export_march.py (status enriched or enrichment_skipped; The Maneater and CoMoBuzz
left out), minus wire copy and obituaries -- these measures never count either. Places are the pipeline's (article_places) and the ones a person entered in review
(article_places_manual); `broadcast` marks KOMU, ABC 17 KMIZ and KBIA, so maps can be drawn with and without them.
An article with no place still gets one row (place columns empty), so it counts in the denominators.
"""
import csv
import os
import sys

import psycopg

OUT = sys.argv[1]
QUERY = """
WITH mine AS (
    SELECT a.id, s.canonical_name AS publisher, s.county AS publisher_county, s.type AS publisher_type,
           a.publish_date, a.title AS headline, a.primary_label
      FROM articles a
      JOIN candidate_links cl ON cl.id = a.candidate_link_id
      JOIN sources s ON s.id = cl.source_id
     WHERE a.publish_date >= '2026-03-01' AND a.publish_date < '2026-04-01'
       AND s.county IN ('Boone', 'Audrain', 'Osage')
       AND s.canonical_name NOT IN ('The Maneater', 'CoMoBuzz', 'Missouri Business Alert', 'The Missouri Independent', 'Missouri Net', 'Missouri Scout', 'The Missouri Times')
       AND a.status IN ('enriched', 'enrichment_skipped')
       AND coalesce(a.wire::text, '') IN ('', 'null', '[]')
       -- obituaries never count: status 'obituary' is already out, and a staff-written life story filed in an
       -- obituaries section (the Missourian's /obituaries/missourian_life_story/) is an obituary too
       AND a.url NOT ILIKE '%%/obituar%%' AND a.url NOT ILIKE '%%/obits/%%'
),
place AS (
    SELECT p.article_id, p.full_name, p.place_type, p.city, p.county, p.state, p.geoid, p.geoid_level,
           p.is_point, p.lat, p.lon, 'pipeline' AS entered_by
      FROM article_places p JOIN mine m ON m.id = p.article_id
    UNION ALL
    SELECT x.article_id, x.full_name, x.geoid_level, x.city, x.county, NULL, NULL, x.geoid_level,
           x.is_point, NULL, NULL, 'person'
      FROM article_places_manual x JOIN mine m ON m.id = x.article_id
)
SELECT m.id AS article_id, m.publisher, m.publisher_county, m.publisher_type,
       (m.publisher_type ILIKE '%%broadcast%%') AS broadcast, m.publish_date, m.headline, m.primary_label,
       p.full_name, p.place_type, p.city, p.county, p.state, p.geoid, p.geoid_level, p.is_point, p.lat, p.lon,
       p.entered_by
  FROM mine m LEFT JOIN place p ON p.article_id = m.id
 ORDER BY m.publisher_county, m.publisher, m.id
"""
with psycopg.connect(host="127.0.0.1", port=5439, user="mizzou_user", password=os.environ["PGPASSWORD"],
                     dbname="mizzou") as conn, conn.cursor() as cur:
    cur.execute(QUERY)
    cols = [d.name for d in cur.description]
    n = 0
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cols)
        for row in cur:
            w.writerow(row)
            n += 1
print(f"{OUT}: {n:,} rows")
