"""Generate aggregate O4 evidence from local prepared ACMA and original panel.

No training, network access, historical infrastructure reconstruction or upload.
All published-form outputs are region aggregates; site records stay private.
"""
from pathlib import Path
import json
import shutil
import importlib.metadata as md

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from analyse import (ROOT, REPO, RADII, EARTH_KM, GROUPS, SOURCES, load_panel,
                     count_nearby, comparisons, sha, save_json, require)

ATTRIBUTION = 'Based on Australian Communications and Media Authority information'


def precision_sensitivity(regions, sites):
    tree = BallTree(np.radians(sites[['lat', 'lon']]), metric='haversine')
    result = []
    for radius in RADII:
        counts = []
        for delta in (-.1, 0, .1):
            hits = tree.query_radius(np.radians(regions[['lat', 'lon']]), r=(radius+delta)/EARTH_KM)
            counts.append(np.array([sites.iloc[i].operator.nunique() for i in hits]))
        result.append({'radius_km': radius, 'perturbation_metres': 100,
                       'regions_with_changed_operator_count': int((counts[0] != counts[2]).sum()),
                       'regions': len(regions)})
    return pd.DataFrame(result)


def standardized_contrasts(summary):
    """Equal-weight common RA-quarter cell contrasts; not causal adjustment."""
    result = []
    known = summary[(summary.remoteness != 'all') & (summary.remoteness != 'Unknown')
                    & (summary.quarter_index != 'all')]
    for radius in RADII:
        data = known[known.radius_km.eq(radius)]
        ref = data[data.category.eq('three-observed')]
        for category in GROUPS[:-1]:
            target = data[data.category.eq(category)]
            common = target.merge(ref, on=['remoteness', 'quarter_index'], suffixes=('_group', '_three'))
            for metric, size in [('median_region_download_mbps', 'speed_regions'),
                                  ('decline_frequency', 'eligible_windows')]:
                eligible = common[(common[size+'_group'] > 0) & (common[size+'_three'] > 0)]
                difference = eligible[metric+'_group'] - eligible[metric+'_three']
                result.append({'radius_km': radius, 'category_vs_three': category,
                    'metric': metric, 'common_remoteness_quarter_cells': len(eligible),
                    'mean_within_cell_difference': difference.mean(),
                    'group_observations_summed_over_common_cells': eligible[size+'_group'].sum(),
                    'reference_observations_summed_over_common_cells': eligible[size+'_three'].sum()})
    return pd.DataFrame(result)


def draw_figures(regions, summary):
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
                    ax.plot(ring[:, 0], ring[:, 1], color='0.65', linewidth=.5)
        for n, marker, colour in zip(range(4), ['x', 'o', '^', 's'], ['black', '.2', '.4', '.65']):
            part = regions[regions[f'operators_{radius}km'].eq(n)]
            ax.scatter(part.lon, part.lat, marker=marker, color=colour, s=13,
                       label=f'{n} (n={len(part)})', linewidths=.5)
        ax.set(title=f'{radius} km radius', xlabel='Longitude', aspect=1.18,
               xlim=(140.5,154.5),ylim=(-37.8,-27.8))
        ax.legend(title='Observed operator candidates', fontsize=7, title_fontsize=7,loc='upper left')
    axes[0].set_ylabel('Latitude')
    fig.suptitle('NSW measured grid centres: October 2026 registered infrastructure candidates')
    fig.text(.5, .015, 'Presence proxy, not operational coverage. '+ATTRIBUTION, ha='center', fontsize=7)
    fig.tight_layout(rect=(0,.04,1,.94))
    for ext in ('png', 'pdf'):
        fig.savefig(ROOT / f'figures/operator_redundancy.{ext}', dpi=220)
    plt.close(fig)
    overall = summary[(summary.remoteness == 'all') & (summary.quarter_index == 'all')]
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    for j, radius in enumerate(RADII):
        part = overall[overall.radius_km.eq(radius)].set_index('category').reindex(GROUPS)
        for i, metric, size, label in [(0,'median_region_download_mbps','regions','Median regional median download (Mbps)'),
                                       (1,'decline_frequency','eligible_windows','Persistent raw decline frequency')]:
            ax = axes[i,j]
            values = part[metric].to_numpy(dtype=float)
            ax.bar(range(4), values, color='.75', edgecolor='black', hatch='//')
            ax.set(xticks=range(4), xlabel='Observed operator candidates', ylabel=label, title=f'{radius} km')
            ceiling=110 if i==0 else .16
            ax.set_ylim(0,ceiling)
            for x, value, n in zip(range(4), values, part[size]):
                ax.text(x, (value if np.isfinite(value) else 0)+ceiling*.025,
                        f'n={int(n):,}' if np.isfinite(value) else 'NA\nn=0',
                        ha='center', va='bottom', fontsize=8)
    fig.suptitle('Historical panel grouped by a contemporary registration snapshot')
    fig.text(.5,.01,'Top: distinct grids; bottom: eligible overlapping baseline-quarter windows. '+ATTRIBUTION,
             ha='center',fontsize=7)
    fig.tight_layout(rect=(0,.04,1,.95))
    for ext in ('png','pdf'):
        fig.savefig(ROOT / f'figures/performance_comparison.{ext}', dpi=220)
    plt.close(fig)


def main():
    versions = {name:md.version(name) for name in ('duckdb','pandas','numpy','scikit-learn','matplotlib','requests')}
    for line in (REPO/'requirements.txt').read_text().splitlines():
        if '==' in line and not line.startswith('#'):
            name,version = line.split('==')
            require(versions[name]==version,f'Pinned dependency mismatch: {name}')
    for directory in ('results','figures','provenance'):
        (ROOT / directory).mkdir(exist_ok=True)
    prep = json.loads((ROOT / 'provenance/acma_preparation.json').read_text())
    require(prep['raw_archive_sha256'] == sha(ROOT / 'raw/spectra_rrl.zip'), 'Raw archive changed')
    site_path = ROOT / 'private/operator_sites.csv'
    require(prep['operator_sites_sha256'] == sha(site_path), 'Prepared sites changed')
    sites = pd.read_csv(site_path, dtype={'physical_site_id':str})
    rows, geography = load_panel(REPO / 'data/panel.csv')
    centres = rows[['region','lat','lon']].drop_duplicates()
    regions = count_nearby(centres, sites)
    # Fixed geographic covariates only, never O3 performance or its panel.
    ra_path = REPO / 'experiments/quality_fairness/data/region_remoteness.csv'
    ra = pd.read_csv(ra_path,dtype={'region':str})
    require(not ra.region.duplicated().any(), 'Duplicate remoteness lookup')
    ra = ra[ra.geography_status.eq('unique_nsw')][['region','ra_name']]
    regions = regions.merge(ra.rename(columns={'ra_name':'remoteness'}),on='region',how='left',validate='one_to_one')
    regions['remoteness'] = regions.remoteness.fillna('Unknown')
    regions['snapshot_date'] = prep['snapshot_date']
    regions['presence_definition'] = 'explicit PMTS plus inferred mobile-compatible spectrum candidates'
    regions.to_csv(ROOT / 'results/region_redundancy.csv',index=False)
    joined = rows.merge(regions.drop(columns=['lat','lon']),on='region',validate='many_to_one')
    joined.to_csv(ROOT / 'results/region_quarter_results.csv',index=False)
    summary = comparisons(joined)
    summary.to_csv(ROOT / 'results/comparison.csv',index=False)
    summary[(summary.remoteness.eq('all')) & (summary.quarter_index.eq('all'))].to_csv(ROOT / 'results/headline_comparison.csv',index=False)
    summary[(summary.remoteness.ne('all')) & (summary.quarter_index.eq('all'))].to_csv(ROOT / 'results/remoteness_comparison.csv',index=False)
    standardized_contrasts(summary).to_csv(ROOT / 'results/common_strata_contrasts.csv',index=False)
    sensitivity = []
    for name, subset in [('explicit_pmts_only', sites[sites.has_explicit_pmts]),
                          ('fdd_or_explicit_only',sites[sites.has_fdd_or_explicit])]:
        counted = count_nearby(centres,subset)
        part = rows.merge(counted.drop(columns=['lat','lon']),on='region',validate='many_to_one')
        part = part.merge(regions[['region','remoteness']],on='region',validate='many_to_one')
        alternative = comparisons(part)
        alternative['definition'] = name
        sensitivity.append(alternative[(alternative.remoteness=='all') & (alternative.quarter_index=='all')])
        for radius in RADII:
            regions[f'{name}_operators_{radius}km'] = counted[f'operators_{radius}km'].to_numpy()
    regions.to_csv(ROOT / 'results/region_redundancy.csv',index=False)
    pd.concat(sensitivity,ignore_index=True).to_csv(ROOT / 'results/classification_sensitivity.csv',index=False)
    precision_sensitivity(centres,sites).to_csv(ROOT / 'results/coordinate_sensitivity.csv',index=False)
    radius_rows = []
    for r in RADII:
        for n in range(4):
            radius_rows.append({'radius_km':r,'operators':n,'regions':int(regions[f'operators_{r}km'].eq(n).sum())})
    pd.DataFrame(radius_rows).to_csv(ROOT / 'results/radius_sensitivity.csv',index=False)
    latest_t = int(rows.t.max())
    latest = comparisons(joined[joined.t.eq(latest_t)])
    latest[(latest.remoteness=='all') & (latest.quarter_index=='all')].to_csv(ROOT / 'results/latest_quarter_comparison.csv',index=False)
    region_outcomes = joined.groupby('region',as_index=False).agg(
        observed_quarters=('t','size'),median_download_mbps=('down_mbps','median'),
        eligible_windows=('persistent_raw','count'),persistent_declines=('persistent_raw','sum'))
    region_outcomes['decline_frequency'] = region_outcomes.persistent_declines / region_outcomes.eligible_windows.replace(0,np.nan)
    region_outcomes.to_csv(ROOT / 'results/region_performance.csv',index=False)
    qa = {'status':'exploratory_complete','blockers':[],
        'regions_analysed_for_redundancy':len(regions),'observed_rows':len(rows),
        'eligible_windows':int(rows.persistent_raw.notna().sum()),
        'eligible_regions':int(rows.loc[rows.persistent_raw.notna(),'region'].nunique()),
        'persistent_raw_declines':int(rows.persistent_raw.sum()),
        'unassessable_windows':int(rows.persistent_raw.isna().sum()),
        'unknown_remoteness_regions':int(regions.remoteness.eq('Unknown').sum()),
        'invalid_download_rows':int((~np.isfinite(rows.down_mbps) | rows.down_mbps.le(0)).sum()),
        'geography':geography,'snapshot_date':prep['snapshot_date'],
        'panel_sha256':sha(REPO/'data/panel.csv'),'remoteness_sha256':sha(ra_path),
        'raw_archive_sha256':prep['raw_archive_sha256'],
        'trained_model':False,'historical_infrastructure_assumed':False,
        'coordinate_method':'GDA94 decimal-degree sites and WGS84 panel centres used in mean-Earth haversine approximation; no exact datum transform claimed. +/-100m sensitivity supplied; unknown site precision not bounded.',
        'attribution':ATTRIBUTION,
        'limits':['Spectrum registrations are mobile-compatible candidates, not verified cellular deployments.',
                  'Site counts are coordinate-deduplicated registry locations; nearby-location bounds are not validated physical towers.',
                  'Strict state containment excludes unmatched offshore/coastal centroids; ACT excluded.',
                  'No defensible generation indicator; possible_5g is unknown throughout.',
                  'Historical associations with a recent snapshot are descriptive, not predictive or causal.']}
    qa['packages'] = versions
    right_censored = rows.t + 2 > int(rows.t.max())
    qa['right_censored_baseline_rows'] = int(right_censored.sum())
    qa['mature_unassessable_baseline_rows'] = int((~right_censored & rows.persistent_raw.isna()).sum())
    qa['official_remoteness_region_counts'] = regions.remoteness.value_counts().to_dict()
    qa['official_remoteness_eligible_windows'] = joined.groupby('remoteness').persistent_raw.count().to_dict()
    save_json(ROOT/'results/data_quality.json',qa)
    draw_figures(regions,summary)
    print(json.dumps(qa,indent=2))
    print(summary[(summary.remoteness=='all') & (summary.quarter_index=='all')].to_string(index=False))


if __name__ == '__main__':
    main()
