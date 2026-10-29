# Pinned outlet registry

Every script reads these copies through `analysis/excluded_outlets.py` (`registry()`, `county_dma()`), which
refuses a file whose SHA-256 does not match. The crawler's working tree is never read, so an uncommitted edit
there cannot change a result here.

| File | Source | SHA-256 |
|---|---|---|
| `mo_outlet_registry.csv` | MizzouNewsCrawler `src/lookups/mo_outlet_registry.csv` at commit `efdf84eddb6eacfb78224ce4131beeefae5d5bc8` (origin/main, 2026-10-24) | `41498f35900e30e7ac663f917b8737d06077c404e8d1ae531914849f9c740463` |
| `county_dma.csv` | MizzouNewsCrawler `src/enrichment/reference/county_dma.csv` (not tracked there; copied 2026-10-24) | `3421196a234208f706fac4d76d2e5edae8ad7cc0cceb8e8750970ac32e01c20d` |

Neither file is committed: `county_dma.csv` carries Nielsen DMA assignments. To refresh, copy the new file,
update the checksum here and in `excluded_outlets.py`, and rerun `scripts/reproduce.sh`.
