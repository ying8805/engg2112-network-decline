from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from zipfile import ZipFile


OPERATORS = {
    "telstra": ("Telstra_4G_2026_Out", "telstra_4g_outdoor_2026_nsw"),
    "optus": ("Optus_4G_2026_Out", "optus_4g_outdoor_2026_nsw"),
    "tpg": ("TPG_4G_2026_Out", "tpg_4g_outdoor_2026_nsw"),
}


def ogr_source(path: Path) -> str:
    path = path.resolve()
    if path.suffix.lower() != ".zip":
        return str(path)
    with ZipFile(path) as archive:
        kmls = [member for member in archive.namelist() if member.lower().endswith(".kml")]
    if len(kmls) != 1:
        raise ValueError(f"Expected one KML inside {path.name}; found {len(kmls)}")
    return f"/vsizip/{path.as_posix()}/{kmls[0]}"


def convert(operator: str, source: Path, boundary: Path, args: argparse.Namespace) -> None:
    source_layer, output_layer = OPERATORS[operator]
    destination = args.output_dir / f"{operator}_4g_outdoor_2026_nsw.gpkg"
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {destination}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    temp_path = destination.with_name(f".{destination.stem}.tmp.gpkg")
    temp_path.unlink(missing_ok=True)
    command = [
        "ogr2ogr", "-f", "GPKG", str(temp_path), ogr_source(source), source_layer,
        "-nln", output_layer,
        "-clipsrc", str(boundary.resolve()),
        "-clipsrclayer", args.boundary_layer,
        "-clipsrcwhere", f"{args.state_field} = 'New South Wales'",
        "-t_srs", "EPSG:3577",
        "-nlt", "PROMOTE_TO_MULTI",
        "-makevalid",
        "-lco", "SPATIAL_INDEX=YES",
        "-progress",
    ]
    print(f"Preparing {operator.upper()} NSW coverage...")
    try:
        subprocess.run(command, check=True)
        temp_path.replace(destination)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    print(f"Saved: {destination}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clip supplied ACCC 2026 4G outdoor KML maps to NSW with GDAL/OGR."
    )
    parser.add_argument("--telstra", type=Path, required=True)
    parser.add_argument("--optus", type=Path, required=True)
    parser.add_argument("--tpg", type=Path, required=True)
    parser.add_argument("--state-boundary", type=Path, required=True)
    parser.add_argument("--boundary-layer", default="STE_2021_AUST_GDA2020")
    parser.add_argument("--state-field", default="STE_NAME21")
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/coverage"))
    args = parser.parse_args()

    for operator, path in (("telstra", args.telstra), ("optus", args.optus), ("tpg", args.tpg)):
        if not path.is_file():
            raise FileNotFoundError(path)
        convert(operator, path, args.state_boundary, args)


if __name__ == "__main__":
    main()
