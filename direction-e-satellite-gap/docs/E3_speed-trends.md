# E3 implementation note

The runnable E3 entry point is scripts/run_ookla_e3.py. It accepts local quarterly Parquet files or the public Ookla Parquet URLs. The public mode uses DuckDB HTTPFS and may scan substantial source data. Install DuckDB and Mercantile with conda-forge if they are not already available.

    conda install -c conda-forge duckdb mercantile

Prepare a single study polygon for NSW Outer Regional, Remote and Very Remote areas, or another explicitly justified region, then run:

    python scripts/run_ookla_e3.py --study-area PATH_TO_REMOTE_NSW.gpkg --remote --start-quarter 2019Q1 --end-quarter 2026Q1 --output-dir outputs/generated/ookla

Starlink began fixed broadband service in Australia in 2021. Keep 2021 Q2 as the transition quarter and compare 2019 Q1–2021 Q1 with 2021 Q3 onward descriptively. Ookla's tile-average metrics do not identify a provider or access technology. The median is over retained tile averages, not individual tests.

The E2 crosswalk entry point is scripts/build_satellite_gap_crosswalk.py. Its default evidence table is data/e2/satellite_service_matrix_clean.csv; this properly quoted CSV is provided because descriptive fields contain commas.

