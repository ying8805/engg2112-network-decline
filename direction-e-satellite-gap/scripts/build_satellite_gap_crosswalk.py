from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


E1_KEYS = {
    "map_reference_date",
    "gap_area_km2",
    "population_in_uncovered_cells",
    "share_of_nsw_population_in_uncovered_cells_pct",
    "state_and_regional_road_length_in_gap_km",
    "geocoded_hospital_reporting_units_in_gap",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Link E1 metrics to the E2 evidence classes without inventing a satellite polygon.")
    parser.add_argument("--e1-summary", type=Path, default=Path("outputs/generated/summary.csv"))
    parser.add_argument("--services", type=Path, default=Path("data/e2/satellite_service_matrix_clean.csv"))
    parser.add_argument("--output", type=Path, default=Path("outputs/generated/satellite_gap_crosswalk.csv"))
    args = parser.parse_args()

    summary = pd.read_csv(args.e1_summary, dtype=str)
    if not {"metric", "value"}.issubset(summary.columns):
        raise ValueError("E1 summary must have metric and value columns")
    values = dict(zip(summary["metric"], summary["value"]))
    missing = E1_KEYS - set(values)
    if missing:
        raise KeyError(f"E1 summary is missing metrics: {sorted(missing)}")
    services = pd.read_csv(args.services, dtype=str).fillna("")

    rows = []
    for _, service in services.iterrows():
        rows.append({
            "provider": service["provider"],
            "service": service["service"],
            "evidence_class": (
                "validated voice capability" if service["voice_validated"].startswith("Yes")
                else "commercial service" if service["commercial_status"].startswith("Commercial")
                else "coverage potential / trial only"
            ),
            "e1_map_reference_date": values["map_reference_date"],
            "e1_gap_area_km2": values["gap_area_km2"],
            "e1_gap_population": values["population_in_uncovered_cells"],
            "e1_gap_population_share_pct": values["share_of_nsw_population_in_uncovered_cells_pct"],
            "e1_state_regional_road_km": values["state_and_regional_road_length_in_gap_km"],
            "e1_hospitals_in_gap": values["geocoded_hospital_reporting_units_in_gap"],
            "sms_or_messaging": service["sms_or_messaging"],
            "voice": service["voice"],
            "broadband_or_data": service["broadband_or_data"],
            "footprint_or_conditions": service["footprint_or_conditions"],
            "e1_overlay_caveat": "No operator-published exact D2D service polygon; E1 figures are contextual and are not an exact satellite intersection.",
            "checked_date": service["checked_date"],
            "source_url": service["source_url"],
        })

    output = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite {args.output}")
    output.to_csv(args.output, index=False)
    print(f"Satellite/E1 evidence crosswalk: {args.output}")


if __name__ == "__main__":
    main()
