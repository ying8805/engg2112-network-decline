# Prespecified descriptive O4 protocol

Recorded 26 October 2026 before any infrastructure outcomes were computed.

Use the original panel and preserve its rural observations; apply no modelling
feature-completeness filter. Its original acquisition threshold still limits
representativeness. The unit is a zoom-12 network grid, not an SA2 or household.
Require unique region-quarter keys and exact agreement with quadkey centres.
Assign NSW by strict centroid containment in the repository state geometry;
exclude ACT and unmatched/coastal centroids and count them in the geography
audit. No nearest-coast assignment. This is a centroid study, not full land
coverage. Inspect boundary provenance before substantive publication.

## Operator and installation review

Candidate name tokens Telstra, Optus, Singtel Optus, TPG and Vodafone are search
leads only. Establish a reviewed mapping from stable corporate client IDs to
the three mobile network operator groups, with exact legal entity names,
supporting evidence and snapshot dates. Do not classify by substring alone.
Subsidiaries, legacy Hutchison entities, network-sharing arrangements, tower
landlords, joint ventures and contractors require individual review. A tower
owner is not evidence of the tenant operator; MVNO brands are not additional
infrastructure networks. Keep ambiguous entities unknown and report counts.

Join the actual site/device/licence/client keys according to the downloaded
dictionary. Verify current authorization, transmitting base-station role and
mobile-service evidence. Exclude receivers, microwave backhaul, broadcast,
private radio and non-cellular installations. Corporate ownership plus a
frequency band is insufficient. Uncertain installations are retained privately
and excluded from the primary counts; their exclusion makes counts conservative
observations, not exhaustive network inventories. Spectrum-area entitlements
alone are not site locations. Record unresolved and excluded counts and reasons.

Use stable ACMA site IDs as initial candidates; reconcile coordinate-identical
and near-coincident IDs using location metadata. Review candidate pairs within
50 m, repeat the physical-site count at 25/100 m review tolerances, and do not
merge distinct nearby facilities solely because they are close. Document each
canonical ID privately. Collapse sectors, frequency assignments and duplicate
licences to operator/physical-site pairs. Count a shared tower once as a physical
site but allow each independently evidenced operator to count. Common towers,
backhaul and power can create shared failure modes. Coordinate checks catch
sign/order errors, datum mismatches, invalid values and inconsistent canonical
sites. These manual tolerances are planned checks, not completed data validation.

Use explicit technology/equipment evidence for 4G/5G labels; otherwise unknown.
Do not infer technology from frequency alone. A true possible-5G indicator means
supporting registration evidence nearby; absent evidence remains unknown.

## Spatial counts and outcomes

Retain sites outside NSW within at least the largest search radius, including
across state/ACT borders. Use spherical haversine great-circle distances with
Earth mean radius 6371.0088 km. Calculate 5/10/20 km distinct operator counts,
unique physical sites and observed redundancy classes. Radius monotonicity is
checked. Zero observed means no accepted record within the radius, never no
signal; single observed is not demonstrated reliance on one network.

Exploratory performance is median across each region's median observed quarterly
download speeds (equal weight per region). Also tabulate each quarter to expose
composition/time differences. Persistent raw decline means both t+1 and t+2
speeds are at most 80% of t, all exact consecutive quarters, positive finite
speeds and at least 50 tests in each. This is an unsmoothed descriptive variant,
not the production O1 smoothed outcome. Missing/right-censored windows stay
unknown. Report eligible windows, distinct eligible grids, unassessable windows
and event counts; pooled frequency is event count / eligible windows.

Stratify by uniquely matched official ABS remoteness labels already available
from O3, joined by region only; preserve unknown labels and record the input
hash. Inspect O3's official-boundary provenance before use. Compare within the
same remoteness class and quarter; sparse/empty cells cannot support rankings.
No causal geographic control or standardized effect is claimed by these tables.
No population total is inferred from device/test counts.

A contemporary ACMA snapshot is associated retrospectively with historical
performance only. There is no model training, split or predictive validation,
and no assumption that the snapshot existed historically. Any later predictive
extension would require historical infrastructure vintages and the original
`src/shrink.py:purge()` on every temporal training split. It is outside this run.

## Realized archive-specific decisions

After the user supplied Spectra, the dictionary confirmed GDA94 coordinates,
Hz units and missing explicit technology metadata. Native preparation was
implemented separately in `prepare_acma.py`; `SCHEMA_NOTES.md` records exact
corporate mapping, current-status/date filters and classification decisions.
Primary exposure includes explicitly labelled PMTS records plus **inferred**
mobile-compatible spectrum registrations. This differs from a hypothetical
fully confirmed cellular inventory: a strict PMTS-only definition and an
FDD/explicit-only sensitivity expose that uncertainty rather than relabelling
all registrations confirmed. These inclusion rules were coded before this
archive's region outcomes were calculated.

The planned manual physical-site reconciliation could not establish actual
tower identity for every nearby site. Exact-coordinate duplicates were merged;
25/50/100 m proximity clustering is reported only as a count sensitivity.
Mean-Earth distance with a stated GDA94/WGS84 approximation and +/-100 m radius
perturbation was used without adding unpinned geospatial dependencies. Unknown
source precision remains unbounded. Possible-5G remains entirely unknown.

Common-remoteness/quarter contrasts and a latest-quarter comparison supplement
the main historical summaries. They are exploratory support checks, not a
prespecified confirmatory test. The original protocol is preserved above; no
significance, causality or historical predictive effect is claimed.

## Population requirement completed after submission audit

At the user's explicit clarification, population totals and speeds were compared
across candidate groups. The population-growth AP experiment was not rerun or
used as evidence. Its source manifests were investigated, and the finer-scale
official ABS 2024 modelled population grid was selected instead of repeating
SA2 ERP totals across observed network grids. The source has its own dwelling-
based allocation model; no additional uniform-population model is invented here.

Each raster cell is assigned once by centre to a measured NSW grid. Four
cell-corner scenarios expose geometric sensitivity, and NoData remains missing.
These are post-audit descriptive extensions, not prespecified confirmatory
effects. All dates, definitions and limitations are explicit. The report and
dashboard now state the absence of a classification-robust monotonic gradient.
