# Verified Spectra schema and classification decisions

Reviewed 26 October 2026 from the user-supplied local archive. No ACMA download
or acceptance action was performed by the agent. Hashes and table sizes are in
`provenance/acma_preparation.json`; the complete source archive stays ignored.

## References and relational keys

The archive's `DOC/Summary_of_Spectra_RRL_Format.xlsx` specifies coordinate
datum, units and field definitions. `DOC/RRLDataDownloads_ERD.jpg` confirms
licence/client, device/licence and device/site relationships. The SQL DDL is a
reference, not executed; actual CSV headers and validated keys take precedence
over older/incomplete diagram and DDL fields. All DOC files, README and licence
text were inspected locally.

| Table | Fields actually used | Purpose |
| --- | --- | --- |
| client.csv | CLIENT_NO, LICENCEE, CLIENT_TYPE_ID | Exact corporate identity only |
| licence.csv | LICENCE_NO, CLIENT_NO, SV_ID, SS_ID, STATUS, DATE_OF_EFFECT, DATE_OF_EXPIRY | Ownership, service and current authorization |
| device_details.csv | SDD_ID, LICENCE_NO, SITE_ID, DEVICE_TYPE, FREQUENCY, BANDWIDTH, SV_ID, SS_ID, CLASS_OF_STATION_CODE, AUTHORISATION_DATE | Registered assignment classification |
| site.csv | SITE_ID, LATITUDE, LONGITUDE, SITE_PRECISION, STATE | Coordinate and precision validation; STATE does not truncate border searches |
| licence_service/subservice.csv | Service identifiers and descriptions | PMTS and spectrum service definitions |
| client_type.csv | TYPE_ID, NAME | Type 5 company; type 7 person excluded |
| class_of_station.csv | CODE, DESCRIPTION | FB denotes base station, FX fixed, ML land-mobile terminal |

Licence, client and site keys were unique. The full archive's device/licence
and nonblank device/site joins had no orphan references. Candidate installation
records were unique on SDD_ID plus direction; receive counterparts were excluded.
Frequencies are **Hz**, not MHz. LATITUDE/LONGITUDE are GDA94 decimal degrees,
not projected eastings/northings. Device generation is not explicit:
TECH_SPEC_ID is blank in every accepted record. Emission designators do not
uniquely establish cellular generation, so all possible-5G values remain unknown.

## Operator assignment

Corporate type 5 and exact normalized legal names are required. Search tokens
were only discovery aids. Reviewed exact mappings in `prepare_acma.EXACT_NAMES`:

- Telstra Limited and Telstra 3G Spectrum Holdings Pty Ltd -> Telstra.
- Optus Mobile Pty Limited -> Optus.
- Vodafone Australia Pty Limited, Vodafone Hutchison Australia Pty Limited and
  TPG Internet Pty Ltd -> TPG/Vodafone.

Multiple CLIENT_NO identities matching these names map to the same group, not
additional operators. The stable IDs and names used are recorded only in
ignored `private/operator_mapping.csv`. Broadcast, pay-TV, administration,
tower-owner or contractor names are not assigned by substring. Natural-person
licensees are not eligible. MOBILE JV PTY LIMITED remains unassigned rather
than counted as two operators or an invented fourth network. This is a
material completeness limitation, not evidence of absence of shared service.

## Current records and evidence levels

Require Granted STATUS=1, nonmissing effective/expiry dates encompassing the
snapshot, and a nonfuture nonmissing device authorization date. Dates establish
register authorization, not installation or switch-on history. Grouping remains
a contemporary snapshot even when an authorization date predates a panel row.

1. **explicit_pmts:** licence and device service 10, subservice 125/127 (PMTS
   Class B), class FB, transmit direction T. Explicit mobile-service evidence
   still does not verify live public cellular operation.
2. **spectrum_inferred:** mapped corporate holder, Spectrum service 85,
   matching licensed/device subservice, T direction, and compatible carrier
   frequency guard below. These are **candidate** mobile/wireless-broadband
   registrations. Missing station class and fixed-wireless ambiguity remain.
3. All other services, receivers, unresolved corporate identities, noncurrent
   licences and invalid coordinates are excluded. Primary results include
   levels 1 and 2; strict sensitivity uses only level 1.

| Subservice | Candidate carrier windows (MHz) |
| --- | --- |
| 850 | 1805–1880 |
| 854 | 2110–2170 |
| 857 | 2300–2400 |
| 861 | 3400–3800 |
| 866 | 24250–27500 |
| 868 | 869–890 |
| 870 | 758–803 |
| 871 | 2620–2690 |
| 873 | 859–894 or 925–960 |

These are screening guards, not a claim that every allocation in each window
is exclusively cellular. Spectrum-area entitlements alone are never counted
as sites. Frequency screening alone neither confirms base-station function nor
identifies 4G/5G. A further FDD/explicit sensitivity removes the TDD/mmWave
subservices 857, 861 and 866; its operator groups coincide with primary groups
at all study radii. The much smaller explicit-only inventory gives very
different group membership and is not an unbiased alternative census.

Band/use context was checked against official ACMA
[technical liaison tables](https://www.acma.gov.au/spectrum-and-apparatus-licence-technical-liaison-groups),
[850/900 MHz FAQs](https://www.acma.gov.au/faqs-850900-mhz-band-auction),
[spectrum use table](https://www.acma.gov.au/expiring-spectrum-licences) and
[1800 MHz auction summary](https://www.acma.gov.au/auction-summary-1800-mhz-regional-2016).
All accessed 26 October 2026. The auction summary independently identifies the
four relevant corporate bidders; TPG/Vodafone are combined for this study.
Corporate/license mappings and inclusion windows remain documented analytical
choices, rather than official operator-coverage labels.

## Deduplication, geography and precision

Repeated sectors, directions, frequencies and licences do not create extra
operators. Collapse accepted transmit registrations by canonical location and
operator. Canonical locations merge exactly identical coordinates across site
IDs; four duplicate-coordinate site IDs collapsed in this archive. Nearby
distinct registry locations are not automatically declared a single tower.
25/50/100 m proximity-cluster counts quantify potential location-count
overstatement; connected components are sensitivity bounds, not verified
physical tower identities. Primary `sites_*km` means deduplicated registered
locations, not a field-verified tower census.

All mainland Australian candidate sites are retained, including those outside
NSW and in ACT, so border searches are not cut off. Only performance-grid
centres are restricted to strict NSW state-polygon containment. This yields
410 grids; the earlier 408 figure used a different ABS remoteness lookup as
its NSW definition. Three of the 410 lack a unique NSW remoteness match and
remain Unknown; no nearest-class assignment is made.

Haversine uses mean Earth radius 6371.0088 km. GDA94 site coordinates are used
numerically alongside WGS84 grid centres as an explicit kilometre-scale datum
approximation; no exact transformation or survey accuracy is claimed. Moving
thresholds by +/-100 m changes operator counts for 14 grids at 5 km and none
at 10/20 km. This check also guards small distance-model differences; it does
not bound sites whose source precision is Unknown. Site precision and rejected
coordinate counts are recorded in preparation provenance.

Based on Australian Communications and Media Authority information.
