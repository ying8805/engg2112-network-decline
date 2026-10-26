"""Rebuild original unfiltered panel with unchanged upstream functions.

Only connection/cache adapters are applied in memory. Query, aggregation,
labels, defaults and column assembly come from src/build_panel.py. All quarters
must succeed before the previously absent data/panel.csv is installed atomically.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import duckdb
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO / 'src'))
import build_panel as upstream
from quadkey import bbox_prefixes, quadkey_to_lonlat


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    output = REPO / 'data/panel.csv'
    if output.exists():
        raise FileExistsError('Refusing to overwrite an existing original panel')
    work = ROOT / 'work/original_panel'
    for name in ('quarters', 'parquet', 'extensions', 'temp', 'home'):
        (work / name).mkdir(parents=True, exist_ok=True)
    source_hashes = {name: sha(REPO / 'src' / name) for name in
                     ('build_panel.py', 'fetch_ookla.py', 'quadkey.py')}
    original_connect, original_load = duckdb.connect, upstream.load_quarter
    original_url = upstream.url_for
    def connection(*args, **kwargs):
        config = {'extension_directory': str(work / 'extensions'),
                  'temp_directory': str(work / 'temp'),
                  'home_directory': str(work / 'home'),
                  'memory_limit': '1GB', 'threads': '2'}
        config.update(kwargs.pop('config', {}))
        return original_connect(*args, config=config, **kwargs)
    with connection() as con:
        con.execute('INSTALL httpfs; LOAD httpfs;')
    periods = list(upstream.quarters((2019, 1), (2026, 1)))
    box = upstream.NSW
    prefixes = bbox_prefixes(box['xmin'], box['ymin'], box['xmax'], box['ymax'], upstream.FILTER_ZOOM)

    def acquire(period):
        y, q = period
        path = work / f'quarters/{y}Q{q}.csv'
        meta_path = path.with_suffix('.json')
        if path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text())
            if sha(path) == meta['aggregate_sha256'] and meta['source_hashes'] == source_hashes:
                print(f'{y}Q{q}: verified cache', flush=True)
                return meta
            raise ValueError(f'Cache provenance mismatch: {path}')
        url = original_url(y, q)
        response = requests.head(url, timeout=60)
        response.raise_for_status()
        headers = {k: response.headers.get(k) for k in ('ETag', 'Last-Modified', 'Content-Length')}
        start = time.monotonic()
        print(f'{y}Q{q}: querying original public source', flush=True)
        for attempt in range(3):
            try:
                with connection() as con:
                    con.execute('LOAD httpfs;')
                    frame = original_load(con, y, q, prefixes, 50, 12)
                break
            except Exception:
                if attempt == 2:
                    raise
                print(f'{y}Q{q}: retry {attempt+1}', flush=True)
        assert len(frame) and (frame.tests >= 50).all()
        partial = path.with_suffix('.csv.partial')
        frame.to_csv(partial, index=False)
        partial.replace(path)
        meta = {'year': y, 'quarter': q, 'url': url, 'source_headers': headers,
                'acquired_utc': datetime.now(timezone.utc).isoformat(),
                'rows': len(frame), 'seconds': time.monotonic()-start,
                'transport': 'original DuckDB httpfs remote Parquet query',
                'aggregate_sha256': sha(path), 'source_hashes': source_hashes}
        meta_path.write_text(json.dumps(meta, indent=2))
        print(f'{y}Q{q}: {len(frame)} regions, {meta["seconds"]:.1f}s', flush=True)
        return meta

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(acquire, period) for period in periods]
        metadata = [f.result() for f in as_completed(futures)]

    def cached_load(con, y, q, prefixes, min_tests, region_zoom=12):
        assert min_tests == 50 and region_zoom == 12
        return pd.read_csv(work / f'quarters/{y}Q{q}.csv', dtype={'region': str})

    duckdb.connect, upstream.load_quarter = connection, cached_load
    try:
        # Unmodified original builder performs the final assembly and labels.
        panel = upstream.build(verbose=False)
    finally:
        duckdb.connect, upstream.load_quarter = original_connect, original_load
    assert set(zip(panel.year, panel.quarter)) == set(periods)
    assert not panel.duplicated(['region', 't']).any()
    assert panel.tests.ge(50).all()
    assert panel.region.str.fullmatch('[0-3]{12}').all()
    assert (panel.t == panel.year*4+panel.quarter).all()
    expected = np.array([quadkey_to_lonlat(r) for r in panel.region])
    assert np.allclose(panel[['lon', 'lat']], expected, atol=1e-10, rtol=0)
    previous = panel.groupby('region')[['down_mbps', 'tests', 't']].shift()
    consecutive = panel.t - previous.t == 1
    assert panel.loc[~consecutive, ['prev_down_mbps', 'prev_tests', 'pct_change', 'declined']].isna().all().all()
    assert np.allclose(panel.loc[consecutive, 'prev_down_mbps'], previous.loc[consecutive, 'down_mbps'])
    assert panel.loc[consecutive, 'declined'].astype(int).eq(
        (panel.loc[consecutive, 'pct_change'] <= -.2).astype(int)).all()
    assert all(sha(REPO / 'src' / k) == v for k, v in source_hashes.items())
    partial = output.with_suffix('.csv.partial')
    panel.to_csv(partial, index=False)
    partial.replace(output)
    result = {'status': 'complete', 'output': 'data/panel.csv', 'sha256': sha(output),
        'rows': len(panel), 'regions': panel.region.nunique(), 'quarters': len(periods),
        'minimum_tests': 50, 'region_zoom': 12, 'bounding_box': box,
        'state_filter_applied': False, 'model_history_filter_applied': False,
        'source_hashes': source_hashes, 'sources': sorted(metadata, key=lambda m:(m['year'],m['quarter'])),
        'validation': 'All quarters, unique keys, coordinates, minimum tests, predecessor/gap handling and decline labels passed',
        'historical_bytes_identical_to_team_original': 'Not established; provider data may be revised'}
    (ROOT / 'provenance/panel_rebuild.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'sources'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
