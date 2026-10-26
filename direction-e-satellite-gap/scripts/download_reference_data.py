from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import requests


SOURCES = {
    "abs_population_grid_2025": (
        "https://www.abs.gov.au/statistics/people/population/regional-population/2024-25/GEOTIFF.zip",
        "abs_population_grid_2025.zip",
    ),
    "abs_state_boundary_2021": (
        "https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/edition-3-july-2021-june-2026/access-and-downloads/digital-boundary-files/STE_2021_AUST_SHP_GDA2020.zip",
        "abs_state_boundary_2021_gda2020.zip",
    ),
    "abs_remoteness_2021": (
        "https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/edition-3-july-2021-june-2026/access-and-downloads/digital-boundary-files/ASGS_Ed3_2021_RA_GPKG_GDA2020.zip",
        "abs_remoteness_2021_gda2020.zip",
    ),
    "nsw_roads": (
        "https://opendata.transport.nsw.gov.au/data/dataset/3fd475d4-ffed-479f-8fe7-99bbf78d85be/resource/63a25fc2-7bf6-42ee-96d2-ff749d04d688/download/nsw_road_network_categorisation.zip",
        "nsw_road_network_categorisation.zip",
    ),
}
HOSPITALS_URL = "https://myhospitalsapi.aihw.gov.au/api/v1/reporting-units"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(session: requests.Session, url: str, destination: Path) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or destination.stat().st_size == 0:
        partial = destination.with_suffix(destination.suffix + ".part")
        try:
            with session.get(url, stream=True, timeout=(20, 180)) as response:
                response.raise_for_status()
                with partial.open("wb") as stream:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            stream.write(chunk)
            os.replace(partial, destination)
        except Exception:
            partial.unlink(missing_ok=True)
            raise
        print(f"Downloaded: {destination}")
    else:
        print(f"Already present: {destination}")
    return {
        "url": url,
        "filename": destination.name,
        "bytes": destination.stat().st_size,
        "sha256": sha256(destination),
    }


def safe_extract(archive: Path, destination: Path) -> list[str]:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    extracted = []
    with ZipFile(archive) as zipped:
        for info in zipped.infolist():
            if info.is_dir():
                continue
            target = (destination / info.filename).resolve()
            if not target.is_relative_to(root):
                raise ValueError(f"Unsafe archive member path: {info.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with zipped.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            extracted.append(str(target))
    return extracted


def main() -> None:
    parser = argparse.ArgumentParser(description="Download public ABS, TfNSW and AIHW context layers.")
    parser.add_argument("--reference-dir", type=Path, default=Path("data/raw/reference"))
    args = parser.parse_args()

    args.reference_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = "nsw-coverage-gap-research/0.1 (student research)"
    manifest = {"retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "files": {}, "extracted": {}}

    for key, (url, filename) in SOURCES.items():
        archive = args.reference_dir / filename
        manifest["files"][key] = download(session, url, archive)
        manifest["extracted"][key] = safe_extract(archive, args.reference_dir / key)

    hospital_path = args.reference_dir / "aihw_reporting_units.json"
    manifest["files"]["aihw_reporting_units"] = download(session, HOSPITALS_URL, hospital_path)
    manifest_path = args.reference_dir / "download_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Reference download manifest: {manifest_path}")


if __name__ == "__main__":
    main()
