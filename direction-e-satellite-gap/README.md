# Direction E — NSW terrestrial coverage gaps and satellite services

This folder is a self-contained E1–E4 project module for the team repository. It combines the NSW 4G outdoor coverage-gap analysis, satellite-service evidence, fixed Ookla trend analysis, and UOMO policy assessment. It does not replace or edit the parent repository's README, dependencies, or existing scripts.

## Research questions

- **E1 — Where are the mapped terrestrial gaps?** Merge the 2026 ACCC Telstra, Optus and TPG 4G outdoor prediction maps, then describe the NSW union gap by modelled population, remoteness, selected roads and hospital locations.
- **E2 — Can satellite services fill those gaps?** Distinguish coverage potential, services sold commercially, and voice capability measured in a trial. The government voice trial tested fixed voice over Starlink LEO broadband, not native phone-to-satellite calling.
- **E3 — Did fixed broadband performance change after Starlink entered Australia?** Summarise quarterly Ookla fixed-performance tiles over one fixed NSW regional/remote study area. Changes are descriptive because Ookla does not identify the provider.
- **E4 — Is the UOMO enough?** Compare E1 exposure with the future outdoor voice/SMS obligation and identify timing, emergency-call, data and implementation limits.

## Evidence snapshot — 25 October 2026

The ACCC maps refer to 31 January 2026, show predicted 4G outdoor coverage, and predate the standardised approach effective 30 June 2026. Operators' modelling assumptions differ. Telstra changed its mapping method in 2024 after identifying an underestimation issue in its 2022/2023 submissions; interpret cross-year changes carefully.

Telstra Satellite Messaging is a commercial Starlink Direct-to-Cell service for eligible phones and plans. It supports SMS and selected low-bandwidth apps, but not voice calls, full internet access, or Triple Zero. The Australian Government voice trial ran from November 2024 to July 2025 across 50 regional/remote regions, including eight NSW regions. The Department reports that Starlink and NBN fixed wireless generally performed well on most technical metrics; this trial validates a fixed-voice access type, not D2D mobile voice. The October 2026 ACCC discussion paper says D2D voice services were not currently available.

The Minister announced on 16 October 2026 that the UOMO had passed Parliament and was planned to start on 1 December 2027, subject to market developments. Verify Royal Assent, the final Act, emergency-call requirements and operative service standards before publication. The announced baseline is outdoor voice and SMS, not full mobile broadband.

## Files

- data/sources.yml — source dates, links, licences and handling notes for E1–E4.
- data/e2/satellite_service_matrix.csv — service capability and evidence-class matrix.
- data/e2/nsw_voice_trial_sites.csv — eight NSW government LEO voice-trial regions and closest towns.
- docs/E2_satellite-capability.md — service comparison and E1 crosswalk method.
- docs/E3_speed-trends.md — Ookla metrics, study design, launch transition and limitations.
- docs/E4_policy-assessment.md — policy adequacy assessment and E1 measures.
- scripts/ — E1 preparation/summarisation plus E2 crosswalk, E3 trend and E4 report scripts.

## Setup

Create the environment:

    conda env create -f environment.yml
    conda activate nsw-coverage-gap-direction-e

The three ACCC 2026 coverage maps are team-supplied inputs and stay outside Git. Download the public E1 supporting layers:

    python scripts/download_reference_data.py

Do not download, commit or redistribute raw ACMA licence data. Ookla tiles are licensed CC BY-NC-SA 4.0 and should not be committed.

## E1 — Prepare and summarise the gap

Find the extracted ABS 2021 state-boundary shapefile under data/raw/reference/abs_state_boundary_2021, then run:

    python scripts/prepare_coverage.py --telstra "PATH_TO_TELSTRA.kml" --optus "PATH_TO_OPTUS.zip" --tpg "PATH_TO_TPG.kml" --state-boundary "PATH_TO_STE_2021_AUST_GDA2020.shp"

This clips the supplied 4G outdoor maps to NSW. Then run:

    python scripts/summarize_gap.py

Outputs include the union gap polygon, population mask, summary metrics, remoteness summary and hospital locations. Population is modelled on a 1 km grid. Road totals include State and Regional roads only, not all local roads.

## E2 — Compare satellite capability with E1

After E1 has produced outputs/generated/summary.csv:

    python scripts/build_satellite_gap_crosswalk.py --e1-summary outputs/generated/summary.csv

This links E1's gap population, area, roads and hospitals to the evidence matrix. It does not claim an exact satellite overlap: the checked public sources do not provide a matching downloadable D2D service polygon.

## E3 — Summarise fixed Ookla trends

Choose one NSW regional/remote polygon and use the same boundary for all quarters. Query public quarterly Parquet directly:

    python scripts/run_ookla_e3.py --study-area PATH_TO_REMOTE_NSW.gpkg --remote --start-quarter 2019Q1 --end-quarter 2026Q1 --output-dir outputs/generated/ookla

Or read local quarterly Parquet files:

    python scripts/run_ookla_e3.py --study-area PATH_TO_REMOTE_NSW.gpkg --input-dir PATH_TO_OOKLA_PARQUETS --output-dir outputs/generated/ookla

The script reports median tile-average speed, not the median of individual tests. It keeps 2021 Q2 as a transition quarter; do not interpret a pre/post change as proof of a Starlink effect.

## E4 — Assess the policy against E1

After E1 has produced summary.csv:

    python scripts/build_e4_policy_report.py --e1-summary outputs/generated/summary.csv

The generated report carries the E1 population, road, hospital and gap-area values into a qualitative assessment. It treats the UOMO as a future policy target, not current coverage.

## Interpretation limits

- E1 identifies places outside all three supplied predicted terrestrial 4G maps; it does not guarantee no signal at every point.
- Telstra's broad “most outdoor areas” satellite statement is not an exact map polygon and cannot support exact per-cell satellite-covered population totals.
- Fixed LEO broadband/voice can help some eligible premises, but it does not provide mobile coverage along roads.
- Current D2D messaging is not D2D voice, emergency calling, or general mobile broadband.
- E3 uses fixed broadband measurements. It is not a mobile-speed measure and does not identify ISP or access technology.
- E4 requires a fresh legal-status check and confirmation of emergency-call standards before publication.

## Sources

See data/sources.yml and the E2–E4 reports in docs/. Telstra's 2024 coverage-method change is documented in the [ACCC 2024 report](https://www.accc.gov.au/system/files/mobile-infrastructure-report-2024.pdf) and [Telstra's letter to the ACCC](https://www.accc.gov.au/system/files/Telstra%20letter%20to%20ACCC%20%E2%80%93%20changed%20methodology%20for%20calculating%204G%20outdoor%20coverage%20%E2%80%93%202024%20%5BRedacted%5D.pdf).
