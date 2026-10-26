# Population and speed comparison

2024 ABS modelled population assigned once by 1 km cell centre. All values describe observed O4 grids, not statewide coverage or confirmed network dependence. Population is displayed to two significant figures; raw model sums in CSV are arithmetic, not measurement precision. Matching is valid raster cells / eligible NSW raster-cell centres, not resident coverage.

## broader

| Candidates (10 km) | Grids | Grids with population data | Modelled people | Raster matched | Missing grids / partial grids | Median Mbps |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 1 | 1/1 | <100 | 100.00% | 0/0 | 2.83 |
| 1 | 10 | 10/10 | ~1,100 | 100.00% | 0/0 | 18.96 |
| 2 | 10 | 10/10 | ~1,500 | 100.00% | 0/0 | 36.50 |
| 3 | 389 | 389/389 | ~7,200,000 | 99.93% | 0/15 | 83.15 |

## strict_pmts

| Candidates (10 km) | Grids | Grids with population data | Modelled people | Raster matched | Missing grids / partial grids | Median Mbps |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 193 | 193/193 | ~6,200,000 | 99.95% | 0/6 | 91.67 |
| 1 | 140 | 140/140 | ~660,000 | 99.90% | 0/7 | 74.28 |
| 2 | 73 | 73/73 | ~360,000 | 99.96% | 0/2 | 69.54 |
| 3 | 4 | 4/4 | ~18,000 | 100.00% | 0/0 | 88.43 |

No SA2 population has been copied to multiple grids. Missing pixels are not imputed as zero; partial-grid totals include observed model pixels only. The source population is not AP, device counts or a 2026 resident count.

The broader three-candidate total ranges from 6.91 to 7.24 million under the five centre/corner assignment scenarios. This is a geometric sensitivity range, not an uncertainty interval.

See `population_assignment_sensitivity.csv`, `population_by_grid.csv` and `../POPULATION_METHOD.md` for full coverage and missingness.

Based on Australian Communications and Media Authority information.
