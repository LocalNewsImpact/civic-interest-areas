"""Outlets that are not local news for the county they are filed under, outlets whose home is the county they
cover, and the pinned outlet registry every script reads.

Shared by every script that counts a county's coverage, so the lists cannot drift between them.

EXCLUDE -- not any county's local news:
  The Maneater, CoMoBuzz       student and campus outlets in Columbia, out of Boone's coverage (as on the maps)
  Missouri Business Alert      a statewide business outlet run from the School of Journalism in Columbia;
                               statewide, not Boone's local news (2026-10-17)
  The Missouri Independent, Missouri Net, Missouri Scout, The Missouri Times
                               statewide outlets covering the capitol from Jefferson City; statewide, not
                               Cole County's local news, and not local outlets for the spillover model
                               (2026-10-17). With them, Cole's spillover was 36%; without, 30%.
  CAMPUS                       student newspapers of a college or university (registry owner the institution, print
                               or digital, published for its campus), on the same footing as The Maneater
                               (2026-10-24). Kept as local news: university-licensed public broadcasters (KBIA,
                               KCUR, KRCU, KSMU, KXCV, STL Public Radio) and the School of Journalism's community
                               newsrooms (Columbia Missourian, Boone County Journal, KOMU), which publish for the
                               general public.

HOME_COUNTY -- published in one county, covering another (2026-10-24, replaces leaving them out of the fit):
  Mid Rivers Newsmagazine      published in Chesterfield (St. Louis County); 19 of 26 March stories centred in
                               St. Charles County, its home here
  Greene County Commonwealth   published in Mount Vernon (Lawrence County); 20 of 23 centred in Greene County

REGISTRY, COUNTY_DMA -- pinned copies (data/registry/README.md), not the crawler's working tree.
"""
import hashlib
from pathlib import Path

import pandas as pd

CAMPUS = frozenset({
    "Griffon News", "The Arrow", "Drury Mirror", "The Standard", "UMKC Roo News", "The Chart", "The Daily BURG",
    "North West Missourian", "Student Life", "The Journal/The Webster Journal", "The University News",
})
EXCLUDE = frozenset({
    "The Maneater", "CoMoBuzz", "Missouri Business Alert",
    "The Missouri Independent", "Missouri Net", "Missouri Scout", "The Missouri Times",
}) | CAMPUS

HOME_COUNTY = {"Mid Rivers Newsmagazine": "29183", "Greene County Commonwealth": "29077"}

_DIR = Path(__file__).resolve().parents[1] / "data/registry"
REGISTRY = _DIR / "mo_outlet_registry.csv"
COUNTY_DMA = _DIR / "county_dma.csv"
_SHA256 = {
    REGISTRY: "41498f35900e30e7ac663f917b8737d06077c404e8d1ae531914849f9c740463",
    COUNTY_DMA: "3421196a234208f706fac4d76d2e5edae8ad7cc0cceb8e8750970ac32e01c20d",
}


def _checked(path):
    if hashlib.sha256(path.read_bytes()).hexdigest() != _SHA256[path]:
        raise SystemExit(f"{path} does not match its pinned checksum (data/registry/README.md)")
    return path


def registry(**kw):
    """The outlet registry as pinned; county_fips is the outlet's home county, HOME_COUNTY applied."""
    reg = pd.read_csv(_checked(REGISTRY), dtype=str, **kw)
    if "outlet" in reg and "county_fips" in reg:
        hit = reg.outlet.isin(HOME_COUNTY)
        reg.loc[hit, "county_fips"] = reg.loc[hit, "outlet"].map(HOME_COUNTY)
    return reg


def county_dma(**kw):
    return pd.read_csv(_checked(COUNTY_DMA), **kw)


def home_fips(outlet, filed):
    """An outlet's home county: HOME_COUNTY where it applies, else the county it is filed under."""
    return HOME_COUNTY.get(outlet, filed)
