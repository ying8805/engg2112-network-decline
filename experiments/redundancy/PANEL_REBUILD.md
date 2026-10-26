# Original unfiltered panel reconstruction

The original generator is `src/build_panel.py`, documented by repository
README.md and the module itself. The equivalent explicit command is:

```powershell
python src/build_panel.py --start 2019 1 --end 2026 1 --min-tests 50 --threshold 0.20 --zoom 12 --out data/panel.csv
```

The public inputs are quarterly Ookla mobile Parquet files; no AWS credentials
or private source file is required. URLs and metadata are recorded for every
quarter in provenance/panel_rebuild.json. `.gitignore` excludes `data/*.csv`,
which explains why the original generated file was missing from the clone.

This experiment's resumable wrapper runs the original query and assembly
functions without changing src/. Use it from repository root only if the
original panel is absent:

```powershell
..\.venv\Scripts\python.exe -u experiments/redundancy/scripts/rebuild_original_panel.py
```

It caches successful quarters under ignored work/original_panel/, requires
all 29 planned quarters, and refuses to overwrite an existing panel. The
original builder otherwise silently skips failed quarters. No filtered or
teammate performance panel is substituted. The original zoom-8 bounding-box
selection, zoom-12 aggregation, >=50-test rule, test-weighted means, consecutive
predecessor checks and decline labels remain unchanged. State and model-history
filters are later stages; they are not applied to the saved original panel.

The completed local file contains 8,873 rows, 768 bounding-box grids and all
29 quarters, 2019Q1?2026Q1. SHA-256:
`55f3a90de29156af2ae1320029cc27aa5b42ddfc5e53ba73e509f803c01a040a`.
It was revalidated rather than downloaded again for the population extension.
The O4 strict-state analysis subsequently retains 410 grids and 4,471 rows.
Rural observations are retained subject to the original measurement threshold.
The earlier ABS-remoteness lookup audit used a different jurisdiction matching
rule; it is not the current study's NSW sample definition.

The provider can revise public aggregates, so a future reconstruction need
not be byte-identical to this snapshot. The wrapper records source object
ETags, modification dates, cache hashes and source-code hashes. Current source
documentation: https://github.com/teamookla/ookla-open-data (accessed
26 October 2026). Historical diagnostic subset exports are omitted from the
proposed package; the full source provenance is retained.
