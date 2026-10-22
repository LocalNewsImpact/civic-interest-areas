# Story data: Boone, Audrain and Osage counties, March 2026

The local news stories the spillover and coverage analysis used for the three study
counties: every March 2026 story collected from the outlets filed in Boone, Audrain and
Osage counties, less the campus and statewide outlets (`analysis/excluded_outlets.py`).
1,444 stories from 10 outlets. Made by `coverage/export_three_county_stories.py`.

No article text and no headlines: each story is identified by its URL, which leads to
the publisher's own page. The stories themselves remain the publishers' copyright.

Licence: [CC BY 4.0](../../LICENSE-DATA.md). Credit: Missouri School of Journalism analysis.

## march_2026_three_counties_articles.csv

One row per story.

| Column | Meaning |
|---|---|
| `article_id` | The Local News Impact crawler's id for the story |
| `outlet`, `outlet_county`, `outlet_type` | The outlet, the county it is filed in, and TV, radio or print/digital |
| `publish_date` | Publication date |
| `url` | The story on the publisher's site |
| `central_geoid`, `central_level` | Where the story is centred: a Census geoid and its level (block, place, county, state) |
| `central_lat`, `central_lon` | Coordinates of that centre |
| `central_county` | The county of the centre |
| `counties` | Every county the story touches, centred or named, `;`-separated |
| `scope` | Geographic scope: neighborhood_community, city_municipality, regional, statewide, national, international, elsewhere_to_local, local_to_elsewhere, other |
| `cin_category` | Primary category of civic information (the ten critical information needs categories, including Civic Life and Sports) |
| `cin_confidence` | The classifier's confidence in that category, 0–1 |

A story with an empty `counties` was not placed and is not counted in spillover.
Placed: Boone 1,152, Audrain 123, Osage 40.

## march_2026_three_counties_places.csv

One row per story and place it names.

| Column | Meaning |
|---|---|
| `article_id` | As above |
| `geoid`, `geoid_level` | The place: a Census geoid and its level |
| `state` | Its state |
| `is_point` | 1 = the story's central place; 0 = a place it mentions |

Geography and categories are produced by the crawler's enrichment (a language model
reading the story, its places resolved to Census geography) and by its classifier;
both are described in the paper's methods.
