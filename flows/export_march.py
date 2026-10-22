"""March 2026 articles from Audrain, Boone and Osage, with their geography.

One file, one row per article: the publisher, the headline, the URL, the full
text, and every piece of geography the pipeline holds for it -- the resolved
places and their counties and cities, the central place and its coordinates, the
geoid set with how each was derived, and the geographic entities found in the
text.

Every newline inside a field is collapsed to a space, so one logical row is one
physical line and a plain viewer does not show broken rows.
"""

import csv
import os
import re
import sys

import psycopg

OUT = sys.argv[1]
WHERE = """
    a.publish_date >= '2026-03-01' AND a.publish_date < '2026-04-01'
    AND s.county IN ('Boone', 'Audrain', 'Osage')
    AND s.canonical_name NOT IN ('The Maneater', 'CoMoBuzz', 'Missouri Business Alert')
    AND a.status IN ('enriched', 'enrichment_skipped')
"""
IDS = f"""
    SELECT a.id FROM articles a
    JOIN candidate_links cl ON cl.id = a.candidate_link_id
    JOIN sources s ON s.id = cl.source_id
    WHERE {WHERE}
"""
# One row per article. The geography is folded into the row rather than left in
# files of its own: four files joined on an id cannot be read, and the question
# every count here answers is which publisher wrote what.
QUERY = f"""
    WITH mine AS (
        SELECT a.id, s.canonical_name AS publisher, s.county AS publisher_county, s.city AS publisher_city,
               a.publish_date, a.status, a.url, a.title AS headline, a.author, a.wire,
               a.primary_label, a.text_length, a.text
          FROM articles a
          JOIN candidate_links cl ON cl.id = a.candidate_link_id
          JOIN sources s ON s.id = cl.source_id
         WHERE {WHERE}
    ),
    -- the pipeline's places and the ones a person entered in the review queue, together. 37 of the
    -- 43 enrichment_skipped articles here have no pipeline place and only a contributed one, so a
    -- reader seeing the pipeline's table alone concludes those articles name nowhere.
    place AS (
        SELECT p.article_id, p.full_name, p.place_type, p.city, p.county, p.geoid_level,
               p.is_point, p.lat, p.lon, 'a_pipeline' AS entered_by, p.id
          FROM article_places p JOIN mine m ON m.id = p.article_id
        UNION ALL
        SELECT x.article_id, x.full_name, x.geoid_level, x.city, x.county, x.geoid_level,
               x.is_point, NULL, NULL, 'b_person', x.id
          FROM article_places_manual x JOIN mine m ON m.id = x.article_id
    ),
    agg AS (
        SELECT article_id,
               string_agg(DISTINCT split_part(county, ' County', 1), '; ')
                 FILTER (WHERE coalesce(county, '') <> '') AS place_counties,
               string_agg(DISTINCT city, '; ') FILTER (WHERE coalesce(city, '') <> '') AS place_cities,
               string_agg(full_name || ' [' || coalesce(place_type, '') || ']' ||
                          CASE WHEN entered_by = 'b_person' THEN ' (entered)' ELSE '' END,
                          ' | ' ORDER BY entered_by, id) AS places,
               count(*) AS place_count,
               count(*) FILTER (WHERE entered_by = 'b_person') AS places_entered_by_hand,
               (array_agg(full_name ORDER BY entered_by, id) FILTER (WHERE is_point))[1] AS central_place,
               (array_agg(lat ORDER BY entered_by, id) FILTER (WHERE is_point AND lat IS NOT NULL))[1] AS central_lat,
               (array_agg(lon ORDER BY entered_by, id) FILTER (WHERE is_point AND lon IS NOT NULL))[1] AS central_lon
          FROM place GROUP BY article_id
    ),
    gids AS (
        SELECT g.article_id,
               string_agg(g.geoid || ':' || g.geoid_level ||
                          CASE WHEN g.is_primary THEN ':primary' ELSE '' END ||
                          ' (' || g.source || ')', ' | ' ORDER BY g.geoid) AS geoids,
               string_agg(DISTINCT g.geoid, '; ') FILTER (WHERE g.geoid_level = 'county') AS county_geoids
          FROM article_geoids g JOIN mine m ON m.id = g.article_id GROUP BY g.article_id
    ),
    ents AS (
        SELECT e.article_id, string_agg(DISTINCT e.entity_text, '; ') AS geographic_entities
          FROM article_entities e JOIN mine m ON m.id = e.article_id
         WHERE e.entity_label IN ('GPE', 'LOC', 'FAC') GROUP BY e.article_id
    )
    SELECT m.id AS article_id, m.publisher, m.publisher_county, m.publisher_city, m.publish_date,
           m.status, m.url, m.headline, m.author, m.wire, m.primary_label, m.text_length,
           agg.place_counties, agg.place_cities, agg.places, coalesce(agg.place_count, 0) AS place_count,
           coalesce(agg.places_entered_by_hand, 0) AS places_entered_by_hand,
           agg.central_place, agg.central_lat, agg.central_lon,
           gids.geoids, gids.county_geoids, ents.geographic_entities, m.text
      FROM mine m
      LEFT JOIN agg ON agg.article_id = m.id
      LEFT JOIN gids ON gids.article_id = m.id
      LEFT JOIN ents ON ents.article_id = m.id
     ORDER BY m.publisher_county, m.publisher, m.publish_date, m.id
"""

flat = lambda v: re.sub(r"\s*\n\s*", " ", v).strip() if isinstance(v, str) else v

os.makedirs(OUT, exist_ok=True)
with psycopg.connect(
    host="127.0.0.1", port=5439, user="mizzou_user",
    password=os.environ["PGPASSWORD"], dbname="mizzou",
) as conn:
    with conn.cursor() as cur:
        cur.execute(QUERY)
        cols = [d.name for d in cur.description]
        with open(f"{OUT}/march_2026_articles.csv", "w", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(cols)
            n = 0
            for row in cur:
                w.writerow([flat(v) for v in row])
                n += 1
    print(f"march_2026_articles.csv: {n:,} rows, {len(cols)} columns")
