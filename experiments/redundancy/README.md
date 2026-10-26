# O4: resilience, population and historical performance

**Open for review in [PR #4](https://github.com/YangRenRR/engg2112-network-decline/pull/4)
as a scoped exploratory contribution; not merged.** Raw ACMA data, private site records, the ABS
source raster, intermediates and `data/panel.csv` remain local and ignored.

Read [the report](REPORT_SECTION.md), [one-page A4 layout](REPORT_LAYOUT.pdf),
[population-and-speed table](results/POPULATION_COMPARISON.md),
[population method](POPULATION_METHOD.md) and [final validation](results/final_validation.json).
The report explicitly references two compact grayscale figures, with captions.
It occupies one A4 page within the PLAN's approximately 1.25-page allocation.

## Verified findings

At 10 km the broader 0/1/2/3 operator-candidate groups contain 1/10/10/389 grids,
with historical download medians of 2.83/18.96/36.50/83.15 Mbps. Strict PMTS-only
medians are 91.67/74.28/69.54/88.43 Mbps: **the broader gradient is not reproduced
under the strict classification**. The broader rural/regional gradient remains;
all 84 urban grids are in the broader three-candidate group, so no within-urban
gradient can be estimated. These are descriptive associations, not causal effects.

ABS's official 2024 one-kilometre population model provides a population
comparison without duplicating SA2 totals. A source cell is assigned once by
its centre to an observed NSW grid. The broader groups contain <100, about
1,100, 1,500 and 7.2 million modelled people. All 410 grids have some valid data;
15 have partial raster data, covering 17 missing pixels. Raster availability
is not population or mobile coverage. The three-candidate population ranges
from 6.91 to 7.24 million across centre/corner assignment scenarios.

No population-growth AP result is used. The earlier population-growth
experiment's source manifests were inspected without modification; its raw
ERP workbooks were absent. The finer official ABS raster is the defensible
alternative to unsupported SA2-to-grid allocations. See POPULATION_METHOD.md.

At 10 km the low-broader-candidate groups have no eligible persistent-decline
windows. All 3,198 eligible windows and 180 raw persistent declines are in the
broader three-candidate group; no vulnerability contrast is supportable. There
is also no defensible generation indicator: possible-5G remains unknown.

## Reproduce only the completed extension / report

From repository root, with the workspace virtual environment:

```powershell
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe experiments/redundancy/scripts/population_comparison.py
..\.venv\Scripts\python.exe experiments/redundancy/scripts/finish_submission.py
..\.venv\Scripts\python.exe experiments/redundancy/scripts/verify_submission.py --published
```

The population script reuses ignored `work/population/GEOTIFF.zip` or downloads
its exact public ABS URL, checking the pinned SHA-256. It uses numpy/pandas and
Pillow already installed with matplotlib; the complete installed versions are
recorded in `provenance/environment.txt`. No new GIS or PDF dependency is needed.
Review/Git checks additionally use the existing Dulwich 1.2.19 utility; it is
separate from the six pinned research dependencies.

These commands do not rerun the expensive Ookla or ACMA pipeline. A private
per-pixel audit under work/ verifies unique assignment, including valid zeros
and NoData. Independent projection fixtures, population conservation and report
checks are covered by 20 passing tests and targeted validation.

## Full original-input reproduction

After personally obtaining the ACMA archive under its terms, place it at
`experiments/redundancy/raw/spectra_rrl.zip`. The scripts never download ACMA or
accept terms. If the original panel is absent, use
`scripts/rebuild_original_panel.py` from repository root; see PANEL_REBUILD.md.
Then run:

```powershell
..\.venv\Scripts\python.exe experiments/redundancy/scripts/prepare_acma.py
..\.venv\Scripts\python.exe experiments/redundancy/scripts/run_o4.py
..\.venv\Scripts\python.exe experiments/redundancy/scripts/population_comparison.py
..\.venv\Scripts\python.exe experiments/redundancy/scripts/finish_submission.py
..\.venv\Scripts\python.exe experiments/redundancy/scripts/verify_o4.py --published
..\.venv\Scripts\python.exe experiments/redundancy/scripts/verify_submission.py --published
```

`run_o4.py` regenerates the main research tables but not the population
extension. `finish_submission.py` is the current report/dashboard builder.
Legacy wrapper/audit files are retained locally and omitted from the package.

## Source, geography and publication limits

The original-method panel contains 8,873 bounding-box rows, 768 grids and all
29 quarters from 2019Q1 through 2026Q1. It retains the original >=50-test rule,
with no model-history filter and no `panel_nsw.csv` substitution. Strict NSW
state-centroid matching yields 410 study grids; three lack an official remoteness
label and remain Unknown. The 358 excluded grids comprise Victoria 171,
Queensland 110, South Australia 6, ACT 13 and unmatched centroids 58. There is
no offshore snapping or additional rural-history exclusion; see PANEL_REBUILD.md.
The 2024 population model, 26 October 2026 registration snapshot
and historical speed measurements are not temporally aligned exposures.

SCHEMA_NOTES.md documents exact corporate names, joins, explicit/inferred
registration classes, excluded joint ventures, deduplication and positional
uncertainty. Registered locations do not establish operational coverage,
independent failure paths, signal strength or successful emergency calls.
No model was trained and no causal or predictive effect is claimed.

## Proposed submission package

PR_FILES.txt is the explicit allowlist. It includes the scripts, essential
region-level results, population tables/sensitivity, source metadata, report
and dashboard assets needed for review and reproduction. Historical submission
audits, machine-specific logs, duplicate figure exports, wrappers and redundant
subset exports remain locally available but are omitted. The new population
source and all restricted/intermediate files remain ignored. All original
224 tracked files are unchanged; no source file under src/ or other experiment
was edited. Figure 2 labels report the grid denominator for each bar, not the
number of tests or eligible decline windows. The published-review validation
mode permits only allowlisted O4 changes on the existing feature branch.

Population source: Australian Bureau of Statistics. Based on Australian
Communications and Media Authority information.
