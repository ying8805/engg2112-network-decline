"""Local, retrospective O4 analysis; never downloads ACMA or trains models.

Run from the repository root. Without both reviewed inputs this emits only a
blocked-status dashboard and empty result tables, never fabricated site counts.
The reviewed CSV contract is documented in ../README.md.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as md
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO / 'src'))
from boundary import state_of
from quadkey import quadkey_to_lonlat

RADII = (5, 10, 20)
EARTH_KM = 6371.0088
OPERATORS = ('Telstra', 'Optus', 'TPG/Vodafone')
GROUPS = ('zero-observed', 'single-observed', 'two-observed', 'three-observed')
SOURCES = [
    {'name': 'ACMA RRL data and terms', 'url': 'https://www.acma.gov.au/radiocomms-licence-data'},
    {'name': 'ACMA RRL help', 'url': 'https://www.acma.gov.au/help-register-radiocommunications-licences-rrl'},
    {'name': 'ACMA emergency calls', 'url': 'https://www.acma.gov.au/emergency-calls'},
    {'name': 'ACMA investigation outcome, 2023 Optus outage', 'url': 'https://www.acma.gov.au/articles/2024-11/optus-pays-12-million-penalty-triple-zero-outage'},
]


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def save_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def persistent(raw):
    """Raw-speed exploratory outcome, distinct from O1 smoothed labels.

    Require exact consecutive quarters, positive speeds and >=50 tests in all
    three. Missing and right-censored outcomes remain NaN, never false.
    """
    df = raw.sort_values(['region', 't']).copy()
    g = df.groupby('region')
    valid = np.isfinite(df.down_mbps) & (df.down_mbps > 0) & (df.tests >= 50)
    hit = pd.Series(True, index=df.index)
    for k in (1, 2):
        speed = g.down_mbps.shift(-k)
        valid &= ((g.t.shift(-k) - df.t == k) & np.isfinite(speed)
                  & (speed > 0) & (g.tests.shift(-k) >= 50))
        hit &= speed <= 0.8 * df.down_mbps
    df['persistent_raw'] = hit.astype(float).where(valid)
    return df


def load_panel(path):
    df = pd.read_csv(path, dtype={'region': str})
    required = {'region', 'lon', 'lat', 'year', 'quarter', 't', 'down_mbps', 'tests'}
    require(required <= set(df), f'Panel lacks {required - set(df)}')
    require(not df.duplicated(['region', 't']).any(), 'Duplicate region-quarter')
    require(df.region.str.fullmatch('[0-3]{12}').all(), 'Expected zoom-12 quadkeys')
    require(df.quarter.isin([1, 2, 3, 4]).all(), 'Invalid quarter')
    require((df.t == 4 * df.year + df.quarter).all(), 'Quarter index mismatch')
    require((np.isfinite(df.tests) & (df.tests >= 0)).all(), 'Invalid test counts')
    centres = df[['region', 'lon', 'lat']].drop_duplicates()
    require(not centres.region.duplicated().any(), 'Region coordinates vary over time')
    expected = np.array([quadkey_to_lonlat(k) for k in centres.region])
    require(np.allclose(centres[['lon', 'lat']], expected, atol=1e-6, rtol=0),
            'Coordinates differ from quadkey centres')
    # Strict centroid containment, no nearest-coast reassignment. ACT excluded.
    centres['state'] = state_of(centres.lon.to_numpy(), centres.lat.to_numpy(),
                                str(REPO / 'data/au_states.geojson'), offshore=0)
    audit = centres.state.fillna('unmatched').value_counts().to_dict()
    df = df[df.region.isin(centres.loc[centres.state == 'New South Wales', 'region'])]
    require(len(df) > 0, 'No NSW observations')
    return persistent(df), audit


def load_sites(path, manifest_path):
    meta = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    for key in ('snapshot_date', 'source_crs', 'coordinate_transformation',
                'raw_sha256', 'reviewer', 'operator_mapping_evidence',
                'mobile_classification_evidence', 'physical_site_review',
                'completeness_limitations'):
        require(bool(meta.get(key)), f'Manifest requires {key}')
    require(meta.get('terms_accepted_by_user') is True, 'User must accept ACMA terms')
    require(meta.get('all_three_operators_reviewed') is True, 'Incomplete operator review')
    require(meta.get('nsw_plus_20km_buffer_reviewed') is True, 'Border site buffer required')
    require(meta.get('output_crs') == 'EPSG:4326', 'Transform to WGS84 before input')
    require(meta.get('reviewed_csv_sha256') == sha(path), 'Reviewed CSV hash mismatch')
    pd.Timestamp(meta['snapshot_date'])
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    cols = {'record_id', 'physical_site_id', 'operator', 'lat', 'lon',
            'mobile_status', 'active_status', 'technology', 'evidence'}
    require(cols <= set(df), f'Sites lack {cols - set(df)}')
    require(not df.record_id.duplicated().any(), 'Duplicate record IDs')
    require(df.record_id.ne('').all(), 'Blank record ID')
    require(df.mobile_status.isin(['confirmed', 'uncertain', 'excluded']).all(), 'Invalid mobile status')
    require(df.active_status.isin(['current', 'uncertain', 'inactive']).all(), 'Invalid active status')
    require(df.operator.isin([*OPERATORS, 'unknown']).all(), 'Unreviewed operator class')
    require(df.technology.isin(['4G', '5G', 'unknown']).all(), 'Invalid technology class')
    require(df.evidence.ne('').all(), 'Every classification requires evidence')
    df[['lat', 'lon']] = df[['lat', 'lon']].apply(pd.to_numeric, errors='coerce')
    valid_coord = (df.lat.between(-44, -9) & df.lon.between(112, 154.5))
    accepted = (df.mobile_status.eq('confirmed') & df.active_status.eq('current')
                & df.operator.isin(OPERATORS) & valid_coord & df.physical_site_id.ne(''))
    qa = {'input_records': len(df), 'invalid_coordinates': int((~valid_coord).sum()),
          'uncertain_mobile_records': int(df.mobile_status.eq('uncertain').sum()),
          'unknown_operator_records': int(df.operator.eq('unknown').sum()),
          'excluded_or_unresolved_records': int((~accepted).sum())}
    good = df[accepted].copy()
    require(len(good) > 0, 'No confirmed candidate sites')
    # Reviewed physical IDs can merge colocated licences, sectors and operators.
    span = good.groupby('physical_site_id')[['lat', 'lon']].agg(lambda s: s.max() - s.min())
    require((span <= 1e-6).all().all(), 'Canonical physical site has inconsistent coordinates')
    coords = good[['physical_site_id', 'lat', 'lon']].drop_duplicates()
    require(not coords.duplicated(['lat', 'lon']).any(), 'Same coordinate has multiple physical site IDs')
    sites = good.groupby(['physical_site_id', 'operator'], as_index=False).agg(
        lat=('lat', 'first'), lon=('lon', 'first'),
        possible_5g=('technology', lambda s: bool(s.eq('5G').any())))
    qa['accepted_records'] = len(good)
    qa['collapsed_licence_records'] = len(good) - len(sites)
    qa['unique_physical_sites'] = sites.physical_site_id.nunique()
    qa['operator_site_pairs'] = len(sites)
    unique = sites.drop_duplicates('physical_site_id')
    tree = BallTree(np.radians(unique[['lat', 'lon']]), metric='haversine')
    for metres in (25, 50, 100):
        counts = tree.query_radius(np.radians(unique[['lat', 'lon']]),
                                   r=metres / 1000 / EARTH_KM, count_only=True)
        qa[f'remaining_nearby_site_pairs_{metres}m'] = int((counts.sum() - len(unique)) // 2)
    return sites, qa, meta


def count_nearby(regions, sites):
    tree = BallTree(np.radians(sites[['lat', 'lon']].to_numpy()), metric='haversine')
    out = regions.copy()
    for radius in RADII:
        hits = tree.query_radius(np.radians(regions[['lat', 'lon']].to_numpy()),
                                 r=radius / EARTH_KM)
        out[f'operators_{radius}km'] = [sites.iloc[i].operator.nunique() for i in hits]
        out[f'sites_{radius}km'] = [sites.iloc[i].physical_site_id.nunique() for i in hits]
        out[f'category_{radius}km'] = out[f'operators_{radius}km'].map(dict(enumerate(GROUPS)))
        # True is evidence for possible presence; absent evidence stays unknown.
        out[f'possible_5g_{radius}km'] = [True if sites.iloc[i].possible_5g.any() else None for i in hits]
    require((out.operators_5km <= out.operators_10km).all() and
            (out.operators_10km <= out.operators_20km).all(), 'Non-monotone radius counts')
    require((out.sites_5km <= out.sites_10km).all() and
            (out.sites_10km <= out.sites_20km).all(), 'Non-monotone site counts')
    return out


def comparisons(rows):
    """Equal-region speed summaries and explicit eligible-window denominators.

    Stratify by official remoteness and quarter when available. Pooled windows
    overlap and are not independent trials. No significance or causal tests.
    """
    tables = []
    for radius in RADII:
        for stratum, sub in [('all', rows), *list(rows.groupby('remoteness'))]:
            for quarter, period in [('all', sub), *list(sub.groupby('t'))]:
                for count, category in enumerate(GROUPS):
                    group = period[period[f'operators_{radius}km'] == count]
                    per_region = group.groupby('region').down_mbps.median()
                    outcomes = group.persistent_raw.dropna()
                    tables.append({'radius_km': radius, 'remoteness': stratum,
                        'quarter_index': quarter, 'category': category,
                        'regions': group.region.nunique(), 'observed_rows': len(group),
                        'speed_regions': len(per_region.dropna()),
                        'median_region_download_mbps': per_region.median(),
                        'eligible_windows': len(outcomes),
                        'eligible_regions': group.loc[group.persistent_raw.notna(), 'region'].nunique(),
                        'persistent_declines': outcomes.sum(),
                        'decline_frequency': outcomes.mean(),
                        'unassessable_windows': int(group.persistent_raw.isna().sum())})
    return pd.DataFrame(tables)


def figures(regions, summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from boundary import _rings
    fig, axes = plt.subplots(1, 3, figsize=(13, 5), sharex=True, sharey=True)
    features = json.loads((REPO / 'data/au_states.geojson').read_text())['features']
    for ax, radius in zip(axes, RADII):
        for feature in features:
            if 'New South Wales' in feature['properties'].values():
                for ring, _ in _rings(feature['geometry']):
                    ax.plot(ring[:, 0], ring[:, 1], color='0.7', linewidth=.5)
        for n, marker in enumerate(['x', 'o', '^', 's']):
            part = regions[regions[f'operators_{radius}km'] == n]
            ax.scatter(part.lon, part.lat, marker=marker, s=10, color=str(.15 + n*.2), label=str(n))
        ax.set(title=f'{radius} km', xlabel='Longitude', aspect=1.18)
    axes[0].set_ylabel('Latitude')
    axes[-1].legend(title='Observed operators', fontsize=7)
    fig.suptitle('Observed mobile infrastructure near NSW grid centres; not coverage')
    fig.tight_layout()
    fig.savefig(ROOT / 'figures/operator_redundancy.png', dpi=200)
    fig.savefig(ROOT / 'figures/operator_redundancy.pdf')
    plt.close(fig)
    selected = summary[(summary.remoteness == 'all') & (summary.quarter_index == 'all')]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for ax, radius in zip(axes, RADII):
        part = selected[selected.radius_km == radius]
        ax.bar(range(4), part.median_region_download_mbps, color='0.7', edgecolor='black', hatch='//')
        ax.set(xticks=range(4), xlabel='Observed operators', title=f'{radius} km')
        for x, (_, row) in enumerate(part.iterrows()):
            ax.text(x, 0, f'n={row.regions}', ha='center', va='bottom', fontsize=8)
    axes[0].set_ylabel('Median of regional median download (Mbps)')
    fig.tight_layout()
    fig.savefig(ROOT / 'figures/speed_comparison.png', dpi=200)
    fig.savefig(ROOT / 'figures/speed_comparison.pdf')
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sites', type=Path, default=ROOT / 'private/reviewed_sites.csv')
    p.add_argument('--manifest', type=Path, default=ROOT / 'private/manifest.json')
    a = p.parse_args()
    for directory in ('results', 'figures', 'provenance'):
        (ROOT / directory).mkdir(exist_ok=True)
    panel = REPO / 'data/panel.csv'  # Deliberately no processed-panel fallback.
    blockers = [f'Missing {name}' for name, path in
                [('original data/panel.csv', panel), ('user-reviewed ACMA CSV', a.sites),
                 ('ACMA provenance manifest', a.manifest)] if not path.exists()]
    versions = {name: md.version(name) for name in ('duckdb', 'pandas', 'numpy', 'scikit-learn', 'matplotlib', 'requests')}
    for line in (REPO / 'requirements.txt').read_text().splitlines():
        if '==' in line and not line.startswith('#'):
            name, version = line.split('==')
            require(versions[name] == version, f'Pinned version mismatch: {name}')
    qa = {'status': 'blocked' if blockers else 'ready', 'blockers': blockers,
          'regions_analysed_for_redundancy': 0, 'packages': versions,
          'trained_model': False, 'historical_infrastructure_assumed': False}
    dashboard = {'id': 'o4', 'title': 'Resilience and redundancy',
        'question': 'Do NSW regions with fewer nearby observed mobile operators have poorer performance and more persistent decline?',
        'status': 'in_progress', 'answer': 'Analysis pending user-obtained ACMA data and the original panel. No redundancy association has been measured.',
        'method': 'Retrospective descriptive comparison at 5, 10 and 20 km; no predictive training.',
        'figures': [], 'tables': [], 'sources': SOURCES,
        'limits': ['Infrastructure presence is not operational coverage or emergency-call success.',
                   'A recent infrastructure snapshot cannot explain historical decline causally.',
                   'Missing inputs are not zero observed operators.']}
    if not blockers:
        rows, geography = load_panel(panel)
        sites, site_qa, meta = load_sites(a.sites, a.manifest)
        regions = count_nearby(rows[['region', 'lon', 'lat']].drop_duplicates(), sites)
        # Official remoteness labels only; do not infer rurality from test counts.
        ra_path = REPO / 'experiments/quality_fairness/data/region_remoteness.csv'
        if ra_path.exists():
            ra = pd.read_csv(ra_path, dtype={'region': str})
            require(not ra.region.duplicated().any(), 'Ambiguous remoteness keys')
            ra = ra[ra.geography_status.eq('unique_nsw')][['region', 'ra_name']]
            regions = regions.merge(ra.rename(columns={'ra_name': 'remoteness'}), how='left', on='region')
            qa['remoteness_sha256'] = sha(ra_path)
        else:
            regions['remoteness'] = None
        regions['remoteness'] = regions.remoteness.fillna('Unknown')
        valid_speed = np.isfinite(rows.down_mbps) & (rows.down_mbps > 0)
        qa['invalid_download_rows'] = int((~valid_speed).sum())
        rows.loc[~valid_speed, 'down_mbps'] = np.nan
        joined = rows.merge(regions.drop(columns=['lon', 'lat']), on='region', validate='many_to_one')
        summary = comparisons(joined)
        regions.to_csv(ROOT / 'results/region_redundancy.csv', index=False)
        joined.to_csv(ROOT / 'results/region_quarter_results.csv', index=False)
        summary.to_csv(ROOT / 'results/comparison.csv', index=False)
        sensitivity = []
        for small, large in ((5, 10), (10, 20), (5, 20)):
            sensitivity.append({'smaller_radius_km': small, 'larger_radius_km': large,
                'regions': len(regions), 'operator_count_changed_regions': int(
                    regions[f'operators_{small}km'].ne(regions[f'operators_{large}km']).sum())})
        pd.DataFrame(sensitivity).to_csv(ROOT / 'results/radius_sensitivity.csv', index=False)
        figures(regions, summary)
        qa.update(status='exploratory_complete', regions_analysed_for_redundancy=len(regions),
                  geography=geography, sites=site_qa, panel_sha256=sha(panel),
                  reviewed_sites_sha256=sha(a.sites), snapshot_date=meta['snapshot_date'],
                  observed_rows=len(rows), eligible_windows=int(rows.persistent_raw.notna().sum()),
                  unknown_remoteness_regions=int(regions.remoteness.eq('Unknown').sum()),
                  panel_period=[int(rows.t.min()), int(rows.t.max())])
        dashboard.update(answer=f'Exploratory infrastructure summaries generated for {len(regions)} observed NSW regions. See local comparison.csv; interpretation requires review.',
                         status='in_progress')
    else:
        # Header-only files are an explicit unavailable result, never a zero-site map.
        pd.DataFrame(columns=['region', 'lon', 'lat', *[f'operators_{r}km' for r in RADII],
                              *[f'sites_{r}km' for r in RADII],
                              *[f'category_{r}km' for r in RADII],
                              *[f'possible_5g_{r}km' for r in RADII]]).to_csv(ROOT / 'results/region_redundancy.csv', index=False)
        pd.DataFrame([{'radius_km': r, 'status': 'unavailable', 'regions_analysed': 0,
                       'median_download_mbps': None, 'decline_frequency': None} for r in RADII]).to_csv(ROOT / 'results/comparison.csv', index=False)
    dashboard['tables'] = [{'title': 'Local analysis availability',
        'columns': ['Status', 'Regions analysed'], 'rows': [[qa['status'], str(qa['regions_analysed_for_redundancy'])]]}]
    save_json(ROOT / 'results/data_quality.json', qa)
    save_json(REPO / 'docs/o4.json', dashboard)
    print(json.dumps(qa, indent=2))


if __name__ == '__main__':
    if (ROOT/'private/operator_sites.csv').exists() and (ROOT/'provenance/acma_preparation.json').exists():
        from run_o4 import main as run_native_analysis
        from finish_submission import main as build_native_deliverables
        run_native_analysis()
        build_native_deliverables()
    else:
        main()
