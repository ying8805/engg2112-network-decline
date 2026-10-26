"""
E1 by rasterising the coverage maps instead of unioning polygons.

summarize_gap.py unions every coverage polygon into one geometry before doing
anything else. The ACCC maps are mosaics of ~100 m squares - about half a
million polygons each for Optus and the Optus-TPG MOCN in NSW - and that union
did not finish in two hours. Burning each map onto a 100 m grid gives the same
answer to the questions E1 asks, in minutes:

  gap        NSW cells covered by none of the maps; area = cells x 0.01 km2
  population ABS 1 km grid cells whose centre is NSW and is not covered - the
             same centre rule summarize_gap.py applies with all_touched=False
  roads      the State/Regional road layer, cut into ~50 m pieces, each counted
             as in the gap if its midpoint is
  hospitals  AIHW reporting units, located and filtered exactly as
             summarize_gap.load_hospitals does, then tested against the grid

The area is exact to 100 m rather than to the polygon edge, which moves a
statewide total by a negligible amount and is stated with the result.
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely import segmentize, get_coordinates

TEAM = Path.home() / "Desktop/claudeee/ENGG2112/project/direction-e-satellite-gap/scripts"
sys.path.insert(0, str(TEAM))
import summarize_gap as sg                         # noqa: E402  (reuse their parsing)

CRS = "EPSG:3577"
RES = 100.0
REF = Path("data/raw/reference")
COV = Path("data/processed/coverage")


def grid_for(geom):
    x0, y0, x1, y1 = geom.bounds
    x0, y0 = np.floor(x0 / RES) * RES, np.floor(y0 / RES) * RES
    x1, y1 = np.ceil(x1 / RES) * RES, np.ceil(y1 / RES) * RES
    w, h = int((x1 - x0) / RES), int((y1 - y0) / RES)
    return from_origin(x0, y1, RES, RES), (h, w)


def burn(geoms, transform, shape):
    return rasterize(((g, 1) for g in geoms), out_shape=shape, transform=transform,
                     fill=0, dtype="uint8", all_touched=False).astype(bool)


def sample(mask, transform, xs, ys):
    cols = ((np.asarray(xs) - transform.c) / RES).astype(int)
    rows = ((transform.f - np.asarray(ys)) / RES).astype(int)
    ok = (rows >= 0) & (rows < mask.shape[0]) & (cols >= 0) & (cols < mask.shape[1])
    out = np.zeros(len(cols), bool)
    out[ok] = mask[rows[ok], cols[ok]]
    return out


def main():
    state = gpd.read_file(REF / "abs_state_boundary_2021/STE_2021_AUST_GDA2020.shp")
    nsw = state[state.STE_NAME21 == "New South Wales"].to_crs(CRS).union_all()
    transform, shape = grid_for(nsw)
    in_nsw = burn([nsw], transform, shape)
    print(f"grid {shape[1]} x {shape[0]} at {RES:.0f} m; NSW = {in_nsw.sum() * RES**2 / 1e6:,.0f} km2")

    layers = {}
    for op in ("telstra", "optus", "tpg", "mocn"):
        g = gpd.read_file(COV / f"{op}_4g_outdoor_2026_nsw.gpkg").to_crs(CRS)
        layers[op] = burn(g.geometry, transform, shape) & in_nsw
        print(f"  {op:8s} covers {layers[op].sum() * RES**2 / 1e6:>10,.0f} km2 of NSW")

    pop = rasterio.open(next((REF / "abs_population_grid_2025").rglob("*.tif")))
    P = pop.read(1, masked=True)
    rows, cols = np.nonzero(~np.ma.getmaskarray(P) & (P.data > 0))
    xs, ys = rasterio.transform.xy(pop.transform, rows, cols)          # cell centres
    xs, ys, vals = np.asarray(xs), np.asarray(ys), P.data[rows, cols].astype("float64")
    centre_nsw = sample(in_nsw, transform, xs, ys)
    xs, ys, vals, prow, pcol = xs[centre_nsw], ys[centre_nsw], vals[centre_nsw], rows[centre_nsw], cols[centre_nsw]

    remote = gpd.read_file(REF / "abs_remoteness_2021/ASGS_Ed3_2021_RA_GDA2020.gpkg").to_crs(pop.crs)
    names = sorted(remote.RA_NAME_2021.dropna().unique())
    code = {n: i + 1 for i, n in enumerate(names)}
    ra = rasterize(((g, code[n]) for g, n in zip(remote.geometry, remote.RA_NAME_2021)
                    if g is not None and n in code), out_shape=(pop.height, pop.width),
                   transform=pop.transform, fill=0, dtype="uint8")[prow, pcol]

    roads = gpd.read_file(REF / "nsw_roads/NSW_Road_Network_Categorisation.shp").to_crs(CRS)
    pieces = segmentize(roads.geometry.values, 50.0)
    mids, lens = [], []
    for line in pieces:
        c = get_coordinates(line)
        if len(c) < 2:
            continue
        mids.append((c[:-1] + c[1:]) / 2)
        lens.append(np.hypot(*(c[1:] - c[:-1]).T))
    mids, lens = np.vstack(mids), np.concatenate(lens)
    road_nsw = sample(in_nsw, transform, mids[:, 0], mids[:, 1])

    hosp = sg.load_hospitals(REF / "aihw_reporting_units.json", nsw, nsw.buffer(0))  # NSW units
    hx, hy = hosp.geometry.x.values, hosp.geometry.y.values

    results, by_ra = [], []
    for variant, ops in (("three_carriers", ("telstra", "optus", "tpg")),
                         ("with_mocn", ("telstra", "optus", "tpg", "mocn"))):
        covered = np.zeros(shape, bool)
        for op in ops:
            covered |= layers[op]
        gap = in_nsw & ~covered
        pop_gap = ~sample(covered, transform, xs, ys)
        road_gap = sample(gap, transform, mids[:, 0], mids[:, 1])
        hosp_gap = sample(gap, transform, hx, hy)
        total = vals.sum()
        results.append({
            "variant": variant, "maps": "+".join(ops),
            "gap_area_km2": gap.sum() * RES**2 / 1e6,
            "gap_share_of_nsw_area_pct": 100 * gap.sum() / in_nsw.sum(),
            "nsw_population_grid_2025": total,
            "population_in_uncovered_cells": vals[pop_gap].sum(),
            "share_of_nsw_population_in_uncovered_cells_pct": 100 * vals[pop_gap].sum() / total,
            "uncovered_populated_1km_cells": int(pop_gap.sum()),
            "state_and_regional_road_length_km": lens[road_nsw].sum() / 1000,
            "state_and_regional_road_length_in_gap_km": lens[road_gap].sum() / 1000,
            "road_share_in_gap_pct": 100 * lens[road_gap].sum() / lens[road_nsw].sum(),
            "nsw_hospital_reporting_units": len(hosp),
            "hospital_reporting_units_in_gap": int(hosp_gap.sum()),
        })
        for n, c in code.items():
            m = ra == c
            by_ra.append({"variant": variant, "remoteness_area": n,
                          "population": vals[m].sum(),
                          "uncovered_population": vals[m & pop_gap].sum(),
                          "uncovered_share_pct": 100 * vals[m & pop_gap].sum() / vals[m].sum()
                          if vals[m].sum() else np.nan})
        if variant == "with_mocn":
            np.save("gap_with_mocn.npy", gap[::10, ::10])            # 1 km preview for the map
            json.dump({"transform": list(transform)[:6], "step": 10}, open("gap_meta.json", "w"))

    out = Path("outputs/raster"); out.mkdir(parents=True, exist_ok=True)
    r = pd.DataFrame(results); r.to_csv(out / "summary_by_variant.csv", index=False)
    b = pd.DataFrame(by_ra); b.to_csv(out / "population_by_remoteness.csv", index=False)
    pd.set_option("display.width", 220)
    print(r.T.to_string())
    print(b[b.population > 0].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
