# Reproducible population-and-speed comparison

This is a descriptive population comparison, not a predictive-AP comparison.
It resolves the population requirement using an official finer-scale model,
without copying a whole SA2's population into each intersecting O4 grid.

## Source investigation and selection

The population-growth experiment's scripts and `provenance/abs_sources.json`
were inspected. They record 2021–2024 SA2 ERP vintages and an SA2 boundary file,
but none of those downloaded workbooks/boundaries is present in this checkout.
The repository's SEIFA workbook does contain 2021 usual-resident SA2 counts.
Those are useful contextual totals, but a network grid and an SA2 are different
geographies. Centroid matching, equal division or uniform land-area allocation
would not establish how many residents live in each network grid, especially
in rural SA2s with concentrated settlements. No such allocation was made. The
population-growth experiment, its files and its AP results remain unchanged.

Instead use the ABS **Australian Population Grid 2024**, available from the
[Regional population 2023–24 release](https://www.abs.gov.au/statistics/people/population/regional-population/2023-24)
and [direct GeoTIFF archive](https://www.abs.gov.au/statistics/people/population/regional-population/2023-24/GEOTIFF.zip).
The [official methodology](https://www.abs.gov.au/methodologies/regional-population-methodology/2023-24#other-population-measures)
explains that SA1 population estimates are distributed over residential dwelling
locations and summed into one-square-kilometre cells. This is an ABS model,
not a census measurement at the one-kilometre scale. It is not necessarily the
latest population vintage; 2024 is a clearly specified, independently verified
vintage consistent with the previously investigated release.

Access date: **26 October 2026 (Australia/Sydney)**. The archive is cached only
under ignored `work/population/GEOTIFF.zip`. SHA-256:
`833e00886fedf9b9da146d30a255d22e242f82c8a914b28770e4f7944e00d720`.
The archive's metadata identifies ABS copyright and CC BY 4.0. No residential
addresses are downloaded: the published raster contains modelled cell values.

## Raster and geographic checks

- `GEOTIFF/apg24e_1_0_0.tif`: floating-point model values, 1,000 × 1,000 metre
  cells, NoData=-1. Valid zero cells remain zero, distinct from NoData.
- Embedded CRS: **GDA94 / Australian Albers, EPSG:3577**, GRS80 ellipsoid,
  central meridian 132°, standard parallels -18°/-36°, zero false offsets.
- The inverse Albers transform is implemented using the embedded parameters,
  with no additional unpinned GIS library. Three ordinary public coordinate
  fixtures independently checked against Esri GeometryServer agree within
  one millimetre; round-trip and polygon-hole tests are included.
- GDA94 coordinates are used numerically with the WGS84 quadkey grid as an
  explicit metre-scale datum approximation at one-kilometre resolution. No
  survey-level coordinate accuracy is claimed.

## Assignment and prevention of double-counting

Each source raster cell is visited once per separately labelled scenario. Its
centre is converted to one zoom-12 quadkey. The population is included only if
that key is an observed O4 grid and the point is strictly inside the NSW state
polygon, including exclusion of holes such as ACT. A valid cell contributes
to exactly one grid, which then contributes to exactly one 0/1/2/3 category for
each radius and operator definition. SA2 totals are never joined or repeated.

The primary assignment includes **26,192 valid cells** out of **26,209** eligible
cell centres. All **410 grids** have some valid data; **15** are partial and
contain the **17** NoData cells. The partial-grid sums are observed model-pixel
sums, not completed resident totals. NoData is not filled with zero.

The primary model sum across measured grids is approximately **7.2 million**.
`population_by_grid.csv` retains unrounded arithmetic for traceability.
Display totals use two significant figures; positive totals below 100 are
shown as `<100`. Rounded category displays need not sum exactly. The many
decimal places in CSVs come from summing ABS floating-point model values and
must not be interpreted as resident-count precision.

## Coverage, missingness and sensitivity

`population_speed_comparison.csv` contains both broader and strict definitions
at 5/10/20 km. For each category it reports grids, population-matched grids,
missing/partial grids, expected/valid raster cells, matching percentage,
modelled population and equal-grid historical median download speed. The
population is not a weight in the speed statistic.

"Raster matched" means valid raster-cell centres divided by eligible NSW cell
centres in the selected grids. It is **not the percentage of NSW residents with
mobile coverage**. "Population-matched grids" means at least one valid pixel,
not that every resident or pixel is observed.

The centre assignment is compared with four offsets to cell corners:
(-500,-500), (-500,+500), (+500,-500), (+500,+500) metres. Each scenario applies
the same unique assignment and NSW restriction. The broader three-candidate
population spans **6.91–7.24 million**. This is a geometric sensitivity range,
not a confidence interval or a bound on the population model's error. Small
categories' exact scenarios are retained in the sensitivity CSV.

A 2024 population model is associated with October 2026 infrastructure
candidates and historical speeds; no temporal alignment or historical cause is
asserted. A grid inherits the candidate count at its centre, so the table does
not establish how many residents actually depend on a single operator.

## Reproduce and validate locally

From repository root:

```powershell
..\.venv\Scripts\python.exe experiments/redundancy/scripts/population_comparison.py
..\.venv\Scripts\python.exe experiments/redundancy/scripts/finish_submission.py
..\.venv\Scripts\python.exe experiments/redundancy/scripts/verify_submission.py
```

The first command reuses the local source archive or downloads the exact public
ABS object if absent. A changed SHA-256 stops the calculation for review. No
ACMA download, model training or full Ookla/ACMA rerun occurs in these commands.
Source/version/hash metadata are in `provenance/population_source.json`.

Population source: Australian Bureau of Statistics. Infrastructure aggregates:
Based on Australian Communications and Media Authority information.
