"""Outlets that are not local news for the county they are filed under.

Shared by every script that counts a county's coverage, so the list cannot drift between them.
  The Maneater, CoMoBuzz       student and campus outlets in Columbia, out of Boone's coverage (as on the maps)
  Missouri Business Alert      a statewide business outlet run from the School of Journalism in Columbia;
                               statewide, not Boone's local news (2026-10-17)
  The Missouri Independent, Missouri Net, Missouri Scout, The Missouri Times
                               statewide outlets covering the capitol from Jefferson City; statewide, not
                               Cole County's local news, and not local outlets for the spillover model
                               (2026-10-17). With them, Cole's spillover was 36%; without, 30%.
"""
EXCLUDE = frozenset({
    "The Maneater", "CoMoBuzz", "Missouri Business Alert",
    "The Missouri Independent", "Missouri Net", "Missouri Scout", "The Missouri Times",
})
