from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import urlparse

import duckdb
import geopandas as gpd
import mercantile
import numpy as np
import pandas as pd
from shapely import contains_xy


BASE_URL = (
    "https://ookla-open-data.s3.amazonaws.com/parquet/performance/"
    "type=fixed/year={year}/quarter={quarter}/{date}_performance_fixed_tiles.parquet"
)
COLUMNS = ("quadkey", "avg_d_kbps", "avg_u_kbps", "avg_lat_ms", "tests", "devices")


def parse_quarter(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(20\d{2})Q([1-4])", value.upper())
    if not match:
        raise argparse.ArgumentTypeError("Quarter must use YYYYQn, for example 2021Q2")
    return int(match.group(1)), int(match.group(2))


def quarter_range(start: tuple[int, int], end: tuple[int, int]):
    year, quarter = start
    while (year, quarter) <= end:
        yield year, quarter
        quarter += 1
        if quarter == 5:
            year += 1
            quarter = 1


def quarter_label(year: int, quarter: int) -> str:
    return f"{year}Q{quarter}"


def source_url(year: int, quarter: int) -> str:
    month = 1 + (quarter - 1) * 3
    date = f"{year}-{month:02d}-01"
    return BASE_URL.format(year=year, quarter=quarter, date=date)


def quarter_from_path(path: str | Path) -> tuple[int, int]:
    value = str(path)
    year_match = re.search(r"(20\d{2})", value)
    quarter_match = re.search(r"quarter[=/_-]?([1-4])", value, flags=re.IGNORECASE)
    if not quarter_match:
        date_match = re.search(r"(20\d{2})-(01|04|07|10)-01", value)
        if date_match:
            month_to_quarter = {"01": 1, "04": 2, "07": 3, "10": 4}
            return int(date_match.group(1)), month_to_quarter[date_match.group(2)]
    if year_match and quarter_match:
        return int(year_match.group(1)), int(quarter_match.group(1))
    raise ValueError(f"Cannot infer year/quarter from source path: {path}")


def quadkey_centroid(quadkey: str) -> tuple[float, float]:
    key = str(quadkey)
    x = y = 0
    level = len(key)
    if level == 0 or any(digit not in "0123" for digit in key):
        raise ValueError(f"Invalid quadkey: {quadkey}")
    for index, digit in enumerate(key):
        mask = 1 << (level - index - 1)
        if digit in "13":
            x |= mask
        if digit in "23":
            y |= mask
    side = 1 << level
    lon = ((x + 0.5) / side) * 360.0 - 180.0
    mercator_y = np.pi * (1.0 - 2.0 * (y + 0.5) / side)
    lat = np.degrees(np.arctan(np.sinh(mercator_y)))
    return float(lon), float(lat)


def load_study_area(path: Path, layer: str | None):
    options = {"engine": "pyogrio"}
    if layer:
        options["layer"] = layer
    frame = gpd.read_file(path, **options)
    if frame.empty or frame.crs is None:
        raise ValueError(f"Study area must be non-empty and have a CRS: {path}")
    frame = frame.to_crs("EPSG:4326")
    geometry = frame.geometry.dropna()
    geometry = geometry[~geometry.is_empty].union_all()
    if geometry.is_empty:
        raise ValueError(f"No valid geometry in {path}")
    return geometry


def prefixes_for_geometry(geometry, zoom: int) -> list[str]:
    west, south, east, north = geometry.bounds
    prefixes = set()
    for tile in mercantile.tiles(west, south, east, north, [zoom]):
        tile_bounds = mercantile.bounds(tile)
        tile_polygon = (
            (tile_bounds.west, tile_bounds.south),
            (tile_bounds.east, tile_bounds.south),
            (tile_bounds.east, tile_bounds.north),
            (tile_bounds.west, tile_bounds.north),
            (tile_bounds.west, tile_bounds.south),
        )
        from shapely.geometry import Polygon
        if geometry.intersects(Polygon(tile_polygon)):
            prefixes.add(mercantile.quadkey(tile))
    if not prefixes:
        raise ValueError("No coarse Ookla tile prefixes intersect the study area")
    return sorted(prefixes)


def query_source(connection, source: str, prefixes: list[str], prefix_zoom: int) -> pd.DataFrame:
    quoted_columns = ", ".join(COLUMNS)
    placeholders = ", ".join("?" for _ in prefixes)
    query = (
        f"SELECT {quoted_columns} FROM read_parquet(?) "
        f"WHERE substr(CAST(quadkey AS VARCHAR), 1, {int(prefix_zoom)}) IN ({placeholders})"
    )
    return connection.execute(query, [source, *prefixes]).fetchdf()


def summarise_source(frame: pd.DataFrame, geometry, year: int, quarter: int) -> dict | None:
    if frame.empty:
        return None
    frame["quadkey"] = frame["quadkey"].astype(str)
    coords = []
    valid_rows = []
    for idx, key in frame["quadkey"].items():
        try:
            coords.append(quadkey_centroid(key))
            valid_rows.append(idx)
        except ValueError:
            continue
    if not valid_rows:
        return None
    selected = frame.loc[valid_rows].copy()
    lons = np.fromiter((coord[0] for coord in coords), dtype="float64")
    lats = np.fromiter((coord[1] for coord in coords), dtype="float64")
    selected = selected.loc[contains_xy(geometry, lons, lats)].copy()
    if selected.empty:
        return None

    for column in ("avg_d_kbps", "avg_u_kbps", "avg_lat_ms", "tests", "devices"):
        selected[column] = pd.to_numeric(selected[column], errors="coerce")
    selected = selected.dropna(subset=["avg_d_kbps"])
    selected = selected[selected["avg_d_kbps"] >= 0]
    if selected.empty:
        return None

    weights = selected["tests"].fillna(0).clip(lower=0)
    weighted_download = (
        float(np.average(selected["avg_d_kbps"], weights=weights))
        if float(weights.sum()) > 0
        else np.nan
    )
    period = "pre" if (year, quarter) <= (2021, 1) else "transition" if (year, quarter) == (2021, 2) else "post"
    return {
        "quarter": quarter_label(year, quarter),
        "event_period": period,
        "median_tile_avg_download_mbps": float(selected["avg_d_kbps"].median() / 1000),
        "tests_weighted_avg_download_mbps": weighted_download / 1000 if np.isfinite(weighted_download) else np.nan,
        "median_tile_avg_upload_mbps": float(selected["avg_u_kbps"].median() / 1000),
        "median_tile_avg_latency_ms": float(selected["avg_lat_ms"].median()),
        "retained_tile_count": int(len(selected)),
        "tests_sum": int(weights.sum()),
        "devices_sum": int(selected["devices"].fillna(0).clip(lower=0).sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarise Ookla fixed-performance tiles inside a study polygon.")
    parser.add_argument("--study-area", type=Path, required=True)
    parser.add_argument("--study-layer")
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--remote", action="store_true", help="Query public quarterly Ookla Parquet URLs.")
    parser.add_argument("--start-quarter", type=parse_quarter, default=parse_quarter("2019Q1"))
    parser.add_argument("--end-quarter", type=parse_quarter, default=parse_quarter("2026Q1"))
    parser.add_argument("--prefix-zoom", type=int, default=5)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/generated/ookla"))
    args = parser.parse_args()

    if bool(args.input_dir) == bool(args.remote):
        parser.error("Choose exactly one of --input-dir or --remote")
    if args.start_quarter > args.end_quarter:
        parser.error("--start-quarter must not be later than --end-quarter")

    geometry = load_study_area(args.study_area, args.study_layer)
    prefixes = prefixes_for_geometry(geometry, args.prefix_zoom)
    if args.remote:
        sources = [
            (quarter_label(year, quarter), source_url(year, quarter), year, quarter)
            for year, quarter in quarter_range(args.start_quarter, args.end_quarter)
        ]
        connection = duckdb.connect()
        connection.execute("INSTALL httpfs")
        connection.execute("LOAD httpfs")
    else:
        if not args.input_dir.is_dir():
            raise FileNotFoundError(args.input_dir)
        files = sorted(args.input_dir.rglob("*.parquet"))
        if not files:
            raise FileNotFoundError(f"No Parquet files under {args.input_dir}")
        sources = []
        for path in files:
            year, quarter = quarter_from_path(path)
            if args.start_quarter <= (year, quarter) <= args.end_quarter:
                sources.append((quarter_label(year, quarter), str(path), year, quarter))
        connection = duckdb.connect()

    results = []
    for label, source, year, quarter in sources:
        print(f"Reading {label}: {source}")
        try:
            raw = query_source(connection, source, prefixes, args.prefix_zoom)
        except Exception as exc:
            raise RuntimeError(f"Failed reading {label} from {source}: {exc}") from exc
        result = summarise_source(raw, geometry, year, quarter)
        if result is not None:
            results.append(result)
        else:
            print(f"No usable tiles remained for {label}")

    if not results:
        raise RuntimeError("No Ookla tiles matched the study area and selected period")
    quarterly = pd.DataFrame(results).sort_values("quarter")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    quarterly_path = args.output_dir / "quarterly_metrics.csv"
    if quarterly_path.exists():
        raise FileExistsError(f"Refusing to overwrite {quarterly_path}")
    quarterly.to_csv(quarterly_path, index=False)

    period = (
        quarterly.groupby("event_period", as_index=False)
        .agg(
            quarter_count=("quarter", "count"),
            mean_of_quarterly_median_download_mbps=("median_tile_avg_download_mbps", "mean"),
            mean_of_quarterly_weighted_download_mbps=("tests_weighted_avg_download_mbps", "mean"),
            mean_of_quarterly_median_upload_mbps=("median_tile_avg_upload_mbps", "mean"),
            mean_of_quarterly_median_latency_ms=("median_tile_avg_latency_ms", "mean"),
            total_tiles=("retained_tile_count", "sum"),
            total_tests=("tests_sum", "sum"),
            total_devices=("devices_sum", "sum"),
        )
    )
    period_path = args.output_dir / "pre_post_summary.csv"
    if period_path.exists():
        raise FileExistsError(f"Refusing to overwrite {period_path}")
    period.to_csv(period_path, index=False)
    print(f"Quarterly trend: {quarterly_path}")
    print(f"Period summary: {period_path}")


if __name__ == "__main__":
    main()
