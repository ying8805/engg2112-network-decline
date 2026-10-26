from __future__ import annotations

import argparse

from pathlib import Path

import pandas as pd


METRICS = {
    "map_reference_date": "ACCC map reference date",
    "gap_area_km2": "No-4G outdoor map-gap area (km²)",
    "population_in_uncovered_cells": "Modelled population in gap cells",
    "share_of_nsw_population_in_uncovered_cells_pct": "Share of NSW modelled population in gap cells (%)",
    "state_and_regional_road_length_in_gap_km": "State/Regional road length in gap (km)",
    "geocoded_hospital_reporting_units_in_gap": "Geocoded hospital reporting units in gap",
}

MINISTER_RELEASE = "https://minister.infrastructure.gov.au/wells/media-release/ensuring-better-mobile-coverage-all-australians"
ACCC_D2D_REPORT = "https://www.accc.gov.au/system/files/mobile-services-inquiry-discussion-paper-october-2026.pdf?download=y"


def load_summary(path: Path) -> dict[str, str]:
    frame = pd.read_csv(path, dtype=str)
    if not {"metric", "value"}.issubset(frame.columns):
        raise ValueError("E1 summary must have 'metric' and 'value' columns")
    values = dict(zip(frame["metric"], frame["value"]))
    missing = set(METRICS) - set(values)
    if missing:
        raise KeyError(f"E1 summary is missing metrics: {sorted(missing)}")
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description="Draft an E1-linked assessment of UOMO scope and timing.")
    parser.add_argument("--e1-summary", type=Path, default=Path("outputs/generated/summary.csv"))
    parser.add_argument("--output", type=Path, default=Path("outputs/generated/e4_policy_assessment.md"))
    args = parser.parse_args()

    values = load_summary(args.e1_summary)
    lines = [
        "# E1-linked UOMO policy assessment",
        "",
        "**Evidence snapshot:** 2026-10-25. Verify Royal Assent and operative instruments before publication.",
        "",
        "## E1 exposure metrics",
        "",
        "| Metric | E1 result |",
        "|---|---:|",
    ]
    for key, label in METRICS.items():
        lines.append(f"| {label} | {values[key]} |")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "The E1 values describe areas outside all three supplied 4G outdoor prediction maps, using an ACCC map reference date of 31 January 2026. They are not a direct measure of UOMO compliance or satellite service availability.",
        "",
        "As announced on 16 October 2026, the UOMO has passed Parliament and is planned to start on 1 December 2027 subject to market developments. The Government describes its baseline as outdoor voice and SMS, delivered through a mix of towers and LEO Direct-to-Device satellites. This is a future policy outcome, not coverage that should be credited to E1 today.",
        "",
        "As of the October 2026 ACCC discussion paper, D2D messaging services are emerging but D2D voice services are not currently available. Telstra's current D2D messaging service is not an emergency service and cannot call or directly text Triple Zero. The Government's fixed LEO voice trial validates fixed voice over a Starlink broadband connection at trial sites, not native handset-to-satellite mobile voice.",
        "",
        "### Adequacy judgement",
        "",
        "- **Current:** SMS-only D2D is a limited complement; the E1 population and road exposure cannot be treated as voice-covered.",
        "- **Future UOMO:** The intended voice-plus-SMS baseline could materially address the E1 communication need if it is implemented with reliable coverage and confirmed emergency-call capability.",
        "- **Residual:** The policy announcement does not promise full mobile broadband. Exact D2D footprint, availability, quality, 000 access/routing and any outages must be checked against the final Act, standards and operator implementation.",
        "",
        "This is a qualitative adequacy finding. It does not subtract population or road kilometres using an approximate satellite footprint.",
        "",
        "## Policy references",
        "",
        f"- Minister's announcement: {MINISTER_RELEASE}",
        f"- ACCC October 2026 D2D discussion: {ACCC_D2D_REPORT}",
        "",
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite {args.output}")
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Policy assessment: {args.output}")


if __name__ == "__main__":
    main()
