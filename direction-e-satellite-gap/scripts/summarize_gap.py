from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from rasterio.features import geometry_window, rasterize
from rasterio.windows import Window
from shapely.geometry import Point, mapping
from shapely.ops import transform


ANALYSIS_CRS = "EPSG:3577"
OPERATOR_FILES = (
    "telstra_4g_outdoor_2026_nsw.gpkg",
    "optus_4g_outdoor_2026_nsw.gpkg",
    "tpg_4g_outdoor_2026_nsw.gpkg",
)


def one_file(root: Path, pattern: str) -> Path:
    matches = sorted(root.rglob(pattern))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected exactly one {pattern} under {root}; found {len(matches)}. "
            "Pass an explicit path using the corresponding option."
        )
    return matches[0]


def read_vector(path: Path, layer: str | None = None) -> gpd.GeoDataFrame:
    options = {"engine": "pyogrio"}
    if layer:
        options["layer"] = layer
    data = gpd.read_file(path, **options)
    if data.empty or data.crs is None:
        raise ValueError(f"Empty layer or missing CRS: {path}")
    return data


def field_name(frame: gpd.GeoDataFrame, requested: str | None, candidates: tuple[str, ...]) -> str:
    if requested:
        if requested not in frame.columns:
            raise KeyError(f"Field {requested!r} not found. Fields: {list(frame.columns)}")
        return requested
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    raise KeyError(f"Could not find one of {candidates}. Fields: {list(frame.columns)}")


def clean_union(frame: gpd.GeoDataFrame):
    geometries = frame.geometry.dropna()
    geometries = geometries[~geometries.is_empty]
    if geometries.empty:
        raise ValueError("No usable geometries")
    return geometries.union_all()


def reproject_geometry(geometry, source_crs, target_crs):
    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    return transform(transformer.transform, geometry)


def record_values(node: Any):
    if isinstance(node, dict):
        lowered = {str(key).lower(): value for key, value in node.items()}
        lat = lowered.get("latitude", lowered.get("lat"))
        lon = lowered.get("longitude", lowered.get("lon", lowered.get("lng")))
        code = lowered.get("reporting_unit_code", lowered.get("code"))
        name = lowered.get("reporting_unit_name", lowered.get("name"))
        if lat is not None and lon is not None and (code is not None or name is not None):
            yield node
            return
        for value in node.values():
            yield from record_values(value)
    elif isinstance(node, list):
        for value in node:
            yield from record_values(value)


def get_value(record: dict, *keys: str):
    lowered = {str(key).lower(): value for key, value in record.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if isinstance(value, dict):
            value = value.get("name", value.get("reporting_unit_type_name", value.get("value")))
        if value is not None:
            return value
    return None


def load_hospitals(path: Path, state_geometry, gap_geometry) -> gpd.GeoDataFrame:
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for record in record_values(document):
        code = str(get_value(record, "reporting_unit_code", "code") or "")
        name = str(get_value(record, "reporting_unit_name", "name") or "")
        unit_type = str(get_value(record, "reporting_unit_type", "reporting_unit_type_name", "type") or "")
        if not (code.upper().startswith("H") or "hospital" in unit_type.lower()):
            continue
        if str(get_value(record, "closed") or "").lower() == "true":
            continue
        try:
            latitude = float(get_value(record, "latitude", "lat"))
            longitude = float(get_value(record, "longitude", "lon", "lng"))
        except (TypeError, ValueError):
            continue
        if not (-45 <= latitude <= -10 and 110 <= longitude <= 160):
            continue
        point = reproject_geometry(Point(longitude, latitude), "EPSG:4326", ANALYSIS_CRS)
        if state_geometry.covers(point):
            rows.append({
                "reporting_unit_code": code,
                "reporting_unit_name": name,
                "reporting_unit_type": unit_type,
                "in_gap": bool(gap_geometry.covers(point)),
                "geometry": point,
            })
    columns = ["reporting_unit_code", "reporting_unit_name", "reporting_unit_type", "in_gap", "geometry"]
    return gpd.GeoDataFrame(rows, columns=columns, geometry="geometry", crs=ANALYSIS_CRS)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the 2026 NSW no-4G-outdoor-coverage gap and supporting summaries."
    )
    parser.add_argument("--reference-dir", type=Path, default=Path("data/raw/reference"))
    parser.add_argument("--coverage-dir", type=Path, default=Path("data/processed/coverage"))
    parser.add_argument("--population-grid", type=Path)
    parser.add_argument("--state-boundary", type=Path)
    parser.add_argument("--boundary-layer")
    parser.add_argument("--state-field")
    parser.add_argument("--remoteness", type=Path)
    parser.add_argument("--remoteness-layer")
    parser.add_argument("--remoteness-field")
    parser.add_argument("--roads", type=Path)
    parser.add_argument("--hospital-json", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/generated"))
    args = parser.parse_args()

    population_path = args.population_grid or one_file(args.reference_dir, "*.tif")
    state_path = args.state_boundary or one_file(args.reference_dir / "abs_state_boundary_2021", "*.shp")
    remote_path = args.remoteness or one_file(args.reference_dir / "abs_remoteness_2021", "*.gpkg")
    roads_path = args.roads or one_file(args.reference_dir / "nsw_roads", "*.shp")
    hospital_path = args.hospital_json or (args.reference_dir / "aihw_reporting_units.json")

    state = read_vector(state_path, args.boundary_layer)
    state_field = field_name(state, args.state_field, ("STE_NAME21", "STE_NAME"))
    state = state[state[state_field].astype(str).str.casefold().eq("new south wales")]
    if state.empty:
        raise ValueError("NSW row not found in state boundary")
    state = state.to_crs(ANALYSIS_CRS)
    state_geometry = clean_union(state)

    coverage_frames = []
    for filename in OPERATOR_FILES:
        path = args.coverage_dir / filename
        if not path.exists():
            raise FileNotFoundError(path)
        coverage_frames.append(read_vector(path).to_crs(ANALYSIS_CRS))
    coverage = gpd.GeoDataFrame(
        pd.concat(coverage_frames, ignore_index=True), geometry="geometry", crs=ANALYSIS_CRS
    )
    coverage_geometry = clean_union(coverage)
    gap_geometry = state_geometry.difference(coverage_geometry)
    gap_frame = gpd.GeoDataFrame(
        {"definition": ["outside all three 4G outdoor maps as at 2026-01-31"]},
        geometry=[gap_geometry],
        crs=ANALYSIS_CRS,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    gap_path = args.output_dir / "nsw_4g_outdoor_gap_2026.gpkg"
    if gap_path.exists():
        raise FileExistsError(f"Refusing to overwrite {gap_path}")
    gap_frame.to_file(gap_path, layer="nsw_4g_outdoor_gap_2026", driver="GPKG", engine="pyogrio")

    by_remoteness = []
    with rasterio.open(population_path) as source:
        if source.crs is None:
            raise ValueError("Population grid has no CRS")
        raster_state = reproject_geometry(state_geometry, ANALYSIS_CRS, source.crs)
        raster_coverage = reproject_geometry(coverage_geometry, ANALYSIS_CRS, source.crs)
        window = geometry_window(source, [mapping(raster_state)])
        window = window.intersection(Window(0, 0, source.width, source.height)).round_offsets().round_lengths()
        population = source.read(1, window=window, masked=True)
        window_transform = source.window_transform(window)
        shape = population.shape
        nsw_mask = rasterize(
            [(mapping(raster_state), 1)], out_shape=shape, transform=window_transform,
            fill=0, dtype="uint8", all_touched=False,
        ).astype(bool)
        covered_mask = rasterize(
            [(mapping(raster_coverage), 1)], out_shape=shape, transform=window_transform,
            fill=0, dtype="uint8", all_touched=False,
        ).astype(bool)

        values = np.asarray(population.data, dtype="float64")
        valid = ~np.ma.getmaskarray(population) & np.isfinite(values) & (values >= 0)
        in_state = nsw_mask & valid
        gap_mask = nsw_mask & ~covered_mask & valid
        gap_populated = gap_mask & (values > 0)
        total_population = float(values[in_state].sum())
        gap_population = float(values[gap_mask].sum())
        gap_cells = int(gap_populated.sum())

        profile = source.profile.copy()
        profile.update(height=shape[0], width=shape[1], transform=window_transform, compress="deflate", tiled=True)

        mask_path = args.output_dir / "gap_mask.tif"
        if mask_path.exists():
            raise FileExistsError(f"Refusing to overwrite {mask_path}")
        mask_data = np.full(shape, 255, dtype="uint8")
        mask_data[in_state] = 0
        mask_data[gap_mask] = 1
        mask_profile = profile.copy()
        mask_profile.update(dtype="uint8", count=1, nodata=255)
        with rasterio.open(mask_path, "w", **mask_profile) as target:
            target.write(mask_data, 1)

        gap_population_path = args.output_dir / "gap_population.tif"
        if gap_population_path.exists():
            raise FileExistsError(f"Refusing to overwrite {gap_population_path}")
        pop_data = np.full(shape, -9999, dtype="float32")
        pop_data[in_state] = 0
        pop_data[gap_mask] = values[gap_mask].astype("float32")
        pop_profile = profile.copy()
        pop_profile.update(dtype="float32", count=1, nodata=-9999)
        with rasterio.open(gap_population_path, "w", **pop_profile) as target:
            target.write(pop_data, 1)

        remote = read_vector(remote_path, args.remoteness_layer).to_crs(source.crs)
        remote_field = field_name(remote, args.remoteness_field, ("RA_NAME21", "RA_NAME"))
        categories = sorted(str(name) for name in remote[remote_field].dropna().unique())
        codes = {name: index + 1 for index, name in enumerate(categories)}
        remote_shapes = [
            (mapping(geometry), codes[str(name)])
            for geometry, name in zip(remote.geometry, remote[remote_field])
            if geometry is not None and name is not None and not geometry.is_empty
        ]
        remote_ids = rasterize(
            remote_shapes, out_shape=shape, transform=window_transform,
            fill=0, dtype="uint8", all_touched=False,
        )
        for name, code in codes.items():
            cell_mask = gap_populated & (remote_ids == code)
            by_remoteness.append({
                "remoteness_area": name,
                "uncovered_population": float(values[cell_mask].sum()),
                "uncovered_populated_1km_cells": int(cell_mask.sum()),
            })

    roads = read_vector(roads_path).to_crs(ANALYSIS_CRS)
    road_indices = roads.sindex.query(gap_geometry, predicate="intersects")
    road_length_km = float(
        roads.iloc[np.unique(road_indices)].geometry.intersection(gap_geometry).length.sum() / 1000
    )

    hospitals = load_hospitals(hospital_path, state_geometry, gap_geometry)
    hospital_output = args.output_dir / "hospitals_in_gap.gpkg"
    if hospital_output.exists():
        raise FileExistsError(f"Refusing to overwrite {hospital_output}")
    hospitals.to_file(hospital_output, layer="hospitals_nsw", driver="GPKG", engine="pyogrio")

    metrics = [
        {"metric": "map_reference_date", "value": "2026-01-31"},
        {"metric": "gap_area_km2", "value": float(gap_geometry.area / 1_000_000)},
        {"metric": "nsw_population_grid_2025", "value": total_population},
        {"metric": "population_in_uncovered_cells", "value": gap_population},
        {"metric": "share_of_nsw_population_in_uncovered_cells_pct", "value": gap_population / total_population * 100 if total_population else 0},
        {"metric": "uncovered_populated_1km_cells", "value": gap_cells},
        {"metric": "state_and_regional_road_length_in_gap_km", "value": road_length_km},
        {"metric": "geocoded_hospital_reporting_units_in_gap", "value": int(hospitals["in_gap"].sum())},
    ]
    summary_path = args.output_dir / "summary.csv"
    remote_output = args.output_dir / "population_by_remoteness.csv"
    if summary_path.exists() or remote_output.exists():
        raise FileExistsError("Refusing to overwrite existing summary CSVs")
    pd.DataFrame(metrics).to_csv(summary_path, index=False)
    pd.DataFrame(by_remoteness).to_csv(remote_output, index=False)

    print(f"Gap polygons: {gap_path}")
    print(f"Summary: {summary_path}")
    print(f"Population by remoteness: {remote_output}")
    print(f"Gap population: {gap_population:,.0f}")


if __name__ == "__main__":
    main()
