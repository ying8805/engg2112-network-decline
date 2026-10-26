# Final local review

The population requirement is completed using the official ABS 2024 modelled
one-kilometre population raster. It is a population-and-speed comparison,
not predictive AP. Each source cell is counted once; no whole-SA2 population
is repeated across O4 grids. The source, exact URL/hash, allocation method,
missingness and five geometric scenarios are reproducible locally.

The broader 10 km groups contain <100 / approximately 1,100 / 1,500 / 7.2 million
modelled people. All 410 grids have some data; 15 are partial. NoData is not zero.
The three-candidate assignment sensitivity is 6.91?7.24 million. This is not an
uncertainty interval or a population proven to depend on a particular network.

The headline and dashboard now state that the speed gradient appears under
the broader definition and is not reproduced under strict PMTS classification.
The approximately 600-word report explicitly references both captioned figures.
REPORT_LAYOUT.pdf puts the complete section and two compact grayscale figures
on one A4 page, within the 1.25-page allocation. The population table is supplied
separately in results/POPULATION_COMPARISON.md and the dashboard.

Targeted checks cover population conservation/unique-cell allocation, NoData,
source hashes, independent projection fixtures, report figures/layout, dashboard
values and Git exclusions. The full ACMA/Ookla pipeline was not rerun. The final
machine-readable decision and test count are in results/final_validation.json.

PR_FILES.txt supersedes the old 52-file audit proposal. Unnecessary historic
audits, duplicate image/PDF exports, local logs, wrappers and redundant subset
exports are omitted, not deleted from the user's computer. All raw/private/work
files, the ABS raster and regenerated data/panel.csv stay out of Git. The
original 224 tracked files, src/ and other experiments remain unchanged.

The remaining limitations are evidence limits: a modelled 2024 population,
a 2026 infrastructure proxy, uncertain mobile-site classification, missing
low-candidate decline windows, and no direct coverage/voice/emergency-call
measurement. They are stated in the report and are not masked by modelling.
No additional input or approval is needed to review the local artifacts.
No commit, push, PR or publication has occurred; those remain unauthorized.
