# Current source review

Access/review date: 26 October 2026 (Australia/Sydney). This supersedes the
initial missing-input feasibility notes in the earlier review.

- User-supplied `raw/spectra_rrl.zip`: archive reference documents and actual CSV
  headers checked locally. SHA-256 and per-document hashes are recorded in
  `provenance/acma_preparation.json`. Site coordinates are GDA94 decimal degrees;
  frequency/bandwidth values are Hertz. A current archive is not a historical
  deployment inventory. Its ZIP members and latest dated records indicate
  26 October 2026; archive timestamps do not declare their timezone.
- [ACMA register data and conditions](https://www.acma.gov.au/radiocomms-licence-data):
  current snapshot availability and conditional derivative use; the agent did
  not click the terms-accepting data link. The user supplied the download.
  Licence text in the archive was also read. Derivatives require attribution;
  natural-person client information must not be reproduced in them.
- [ACMA RRL help](https://www.acma.gov.au/help-register-radiocommunications-licences-rrl):
  explains clients, licences, sites, assignments and spectrum areas, which are
  distinct objects. Registered locations are not operational coverage.
- [ACMA technical liaison tables](https://www.acma.gov.au/spectrum-and-apparatus-licence-technical-liaison-groups),
  [850/900 MHz FAQs](https://www.acma.gov.au/faqs-850900-mhz-band-auction),
  [spectrum use table](https://www.acma.gov.au/expiring-spectrum-licences),
  [1800 MHz auction summary](https://www.acma.gov.au/auction-summary-1800-mhz-regional-2016):
  band/use and corporate participant context for candidate screening. The
  classification remains an inference, documented in `SCHEMA_NOTES.md`; these
  pages do not validate each registration as a live mobile site or its technology.
- [Ookla source documentation](https://github.com/teamookla/ookla-open-data):
  quarterly public mobile aggregates, attributes, licensing and potential
  revisions. `provenance/panel_rebuild.json` records the exact public S3 objects
  and metadata used to rebuild the original unfiltered panel. Original query,
  geography, threshold and aggregation are documented in `PANEL_REBUILD.md`.
- Official ABS remoteness geography is taken only from the existing O3 lookup,
  whose source provenance is `experiments/quality_fairness/provenance/abs_source.json`.
  The original official boundary URL is the ABS
  [digital boundary files page](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/edition-3-july-2021-june-2026/access-and-downloads/digital-boundary-files).
  No O3 performance values or processed panel were substituted. Fixed 2021
  geography is a retrospective stratification, not a point-in-time feature.

## Emergency calling

[ACMA emergency-call guidance](https://www.acma.gov.au/emergency-calls) explains
that a call can use an available mobile network when the caller's own provider
lacks coverage; actual network availability is necessary. Neither a nearby
licence nor a second corporate operator proves that the handset has compatible
service or that the end-to-end call path is functioning.

[ACMA's investigation outcome for the 2023 Optus outage](https://www.acma.gov.au/articles/2024-11/optus-pays-12-million-penalty-triple-zero-outage)
documents emergency-access failures and subsequent welfare-check failures.
It supports the distinction between infrastructure presence and successful
emergency access, not an inference about the cause or location of every failure.
No incident counts have been presented as findings from this O4 analysis.

## Project provenance

`PLAN.md`, `docs/README.md`, `src/build_panel.py`, `src/fetch_ookla.py`,
`src/quadkey.py`, `src/boundary.py` and `src/shrink.py` were read. All original
tracked files remain unchanged. `PROTOCOL.md` is the pre-outcome descriptive
protocol; the realized archive-specific decisions and sensitivity tests are
documented in `SCHEMA_NOTES.md`. No training or temporal split took place.

Based on Australian Communications and Media Authority information.

## Population extension and report layout

The original population-growth source manifest was inspected, but its raw ERP
workbooks were absent and its AP results are not used. Existing SEIFA SA2
population counts could not establish within-grid residents without unsupported
apportionment. Instead, the extension downloads the official ABS
[2024 modelled 1 km population raster](https://www.abs.gov.au/statistics/people/population/regional-population/2023-24/GEOTIFF.zip)
from the [2023–24 release](https://www.abs.gov.au/statistics/people/population/regional-population/2023-24).
The [official model methodology](https://www.abs.gov.au/methodologies/regional-population-methodology/2023-24)
was verified; access date 26 October 2026. Population source: Australian Bureau
of Statistics, CC BY 4.0 as stated in the downloaded metadata.

POPULATION_METHOD.md and provenance/population_source.json give the exact hash,
CRS/units, model vintage, unique-cell assignment, missingness and sensitivity.
The Albers conversion was independently checked using Esri GeometryServer
against three ordinary public coordinate fixtures, recorded in test_population.py;
the analysis does not depend on a live GIS service.

The report's two compact figures are generated from existing aggregates.
REPORT_LAYOUT.pdf is a one-page A4 composition, with source links and ACMA
attribution. Its layout and image assets are validated without a full research
pipeline rerun. The old audit's missing-population and presentation blockers
are superseded by results/final_validation.json.
