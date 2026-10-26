"""Stream-parse a very large ACCC KML that GDAL cannot load into memory.

GDAL's KML driver builds the whole document in memory and fails on the 1.3 GB
Optus and Optus-TPG MOCN 4G outdoor files. This walks Placemarks one at a time,
keeps polygons whose bounding box touches NSW, and writes the same GeoPackage
the rest of the E1 pipeline expects.
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely import make_valid
from shapely.geometry import Polygon

K = "{http://www.opengis.net/kml/2.2}"
LON0, LAT0, LON1, LAT1 = 140.9, -37.6, 153.7, -28.1


def ring(text):
    a = np.array(text.replace(",", " ").split(), dtype="float64")
    # coordinates may be lon,lat or lon,lat,alt; detect from count
    for dims in (2, 3):
        if a.size % dims == 0:
            pts = a.reshape(-1, dims)[:, :2]
            if np.all(np.abs(pts[:, 1]) <= 90):
                return pts
    raise ValueError("unparseable coordinates")


def polygons(placemark):
    for poly in placemark.iter(K + "Polygon"):
        outer = poly.find(f"{K}outerBoundaryIs/{K}LinearRing/{K}coordinates")
        if outer is None or not outer.text:
            continue
        shell = ring(outer.text)
        if (shell[:, 0].max() < LON0 or shell[:, 0].min() > LON1 or
                shell[:, 1].max() < LAT0 or shell[:, 1].min() > LAT1):
            continue
        holes = [ring(h.text) for h in poly.findall(f"{K}innerBoundaryIs/{K}LinearRing/{K}coordinates")
                 if h.text]
        yield Polygon(shell, holes)


def main(operator, path, out_dir):
    kept, seen = [], 0
    for _, el in ET.iterparse(path, events=("end",)):
        if el.tag == K + "Placemark":
            seen += 1
            kept.extend(polygons(el))
            el.clear()
    gdf = gpd.GeoDataFrame(geometry=[make_valid(p) for p in kept], crs="EPSG:4326")
    gdf = gdf[~gdf.geometry.is_empty].to_crs("EPSG:3577")
    out = Path(out_dir) / f"{operator}_4g_outdoor_2026_nsw.gpkg"
    out.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(out, layer=f"{operator}_4g_outdoor_2026_nsw", driver="GPKG", engine="pyogrio")
    print(f"{operator}: {seen} placemarks read, {len(gdf)} polygons touching NSW -> {out.name}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
