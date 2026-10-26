"""Independent output reconciliation, raw-data exclusion and source preservation."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

import numpy as np
import pandas as pd

from analyse import ROOT, REPO, RADII, EARTH_KM, GROUPS, sha, save_json


def main():
    qa=json.loads((ROOT/'results/data_quality.json').read_text())
    prep=json.loads((ROOT/'provenance/acma_preparation.json').read_text())
    regions=pd.read_csv(ROOT/'results/region_redundancy.csv',dtype={'region':str})
    rows=pd.read_csv(ROOT/'results/region_quarter_results.csv',dtype={'region':str})
    summary=pd.read_csv(ROOT/'results/headline_comparison.csv')
    sites=pd.read_csv(ROOT/'private/operator_sites.csv',dtype={'physical_site_id':str})
    assert len(regions)==qa['regions_analysed_for_redundancy']
    assert len(rows)==qa['observed_rows']
    assert not regions.region.duplicated().any()
    assert not rows.duplicated(['region','t']).any()
    assert regions[[f'possible_5g_{r}km' for r in RADII]].isna().all().all()
    # Independent, dense haversine calculation reconciles BallTree results.
    # Colocated operators share one deduplicated physical-location index.
    unique=sites.drop_duplicates('physical_site_id')
    coords=np.radians(sites[['lat','lon']].to_numpy())
    unique_coords=np.radians(unique[['lat','lon']].to_numpy())
    def distances(point, points):
        a=np.sin((points[:,0]-point[0])/2)**2 + np.cos(point[0])*np.cos(points[:,0])*np.sin((points[:,1]-point[1])/2)**2
        return 2*EARTH_KM*np.arcsin(np.sqrt(np.clip(a,0,1)))
    for row in regions.itertuples():
        point=np.radians([row.lat,row.lon])
        d=distances(point,coords)
        du=distances(point,unique_coords)
        for radius in RADII:
            assert sites.loc[d<=radius,'operator'].nunique()==getattr(row,f'operators_{radius}km')
            assert int((du<=radius).sum())==getattr(row,f'sites_{radius}km')
    for radius in RADII:
        group=summary[summary.radius_km.eq(radius)]
        assert group.regions.sum()==len(regions)
        assert group.eligible_windows.sum()==rows.persistent_raw.notna().sum()
        assert group.persistent_declines.sum()==rows.persistent_raw.sum()
        for record in group.itertuples():
            part=rows[rows[f'category_{radius}km'].eq(record.category)]
            median=part.groupby('region').down_mbps.median().median()
            if pd.isna(median): assert pd.isna(record.median_region_download_mbps)
            else: assert np.isclose(median,record.median_region_download_mbps)
            if not record.eligible_windows: assert pd.isna(record.decline_frequency)
    # Reconstruct outcomes with explicit keyed lookups, independent of shifts.
    lookup=rows.set_index(['region','t'])
    for record in rows.itertuples():
        eligible=all((record.region,record.t+k) in lookup.index for k in (1,2))
        if not eligible:
            assert pd.isna(record.persistent_raw)
            continue
        future=[lookup.loc[(record.region,record.t+k)] for k in (1,2)]
        valid=(record.down_mbps>0 and record.tests>=50 and all(x.down_mbps>0 and x.tests>=50 for x in future))
        if valid: assert record.persistent_raw==float(all(x.down_mbps<=.8*record.down_mbps for x in future))
        else: assert pd.isna(record.persistent_raw)
    baseline=json.loads((ROOT/'provenance/repository_baseline.json').read_text())
    changed=[name for name,value in baseline['tracked_sha256'].items() if not (REPO/name).exists() or sha(REPO/name)!=value]
    assert not changed,changed
    from dulwich.repo import Repo
    from dulwich import porcelain
    with Repo(str(REPO)) as repo:
        assert repo.head().decode()==baseline['initial_head']
        assert repo.refs.read_ref(b'HEAD')==b'ref: refs/heads/o4-local-review'
        status=porcelain.status(repo)
        assert not any(status.staged.values()) and not status.unstaged
        raw='experiments/redundancy/raw/spectra_rrl.zip'
        assert list(porcelain.check_ignore(repo,[raw]))==[raw]
        # All private files, including exploratory caches, must be ignored.
        private_files=[p.relative_to(REPO).as_posix() for p in (ROOT/'private').rglob('*') if p.is_file()]
        assert len(list(porcelain.check_ignore(repo,private_files)))==len(private_files)
    dashboard=json.loads((REPO/'docs/o4.json').read_text())
    assert dashboard['id']=='o4' and dashboard['status']=='done'
    for table in dashboard['tables']:
        assert all(len(r)==len(table['columns']) for r in table['rows'])
    for figure in dashboard['figures']:
        assert (REPO/'docs'/figure['src']).exists()
    attribution='Based on Australian Communications and Media Authority information'
    assert attribution in (ROOT/'REPORT_SECTION.md').read_text()
    assert attribution in (ROOT/'results/COMPARISON.md').read_text()
    assert all(attribution in f['caption'] for f in dashboard['figures'])
    # Public-form outputs cannot contain register/client/site record columns.
    forbidden={'LICENCE_NO','CLIENT_NO','LICENCEE','POSTAL_STREET','SDD_ID','SITE_ID','physical_site_id'}
    for path in (ROOT/'results').glob('*.csv'):
        assert not forbidden.intersection(pd.read_csv(path,nrows=0).columns),path
    run=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'scripts'),'-p','test_*.py','-v'],capture_output=True,text=True)
    (ROOT/'provenance/test_output.txt').write_text(run.stdout+run.stderr,encoding='utf-8')
    assert run.returncode==0,run.stderr
    result={'status':'passed','existing_tracked_files_checked':len(baseline['tracked_sha256']),
        'existing_tracked_files_changed':changed,'raw_and_private_data_ignored':True,
        'no_staged_changes_or_new_commits':True,'independently_checked_regions':len(regions),
        'independent_distance_counts':'passed at all three radii',
        'independent_outcome_windows':'passed keyed future lookup',
        'dashboard_schema_and_images':'passed','unit_tests':unittest.TestLoader().discover(str(ROOT/'scripts'),pattern='test_*.py').countTestCases(),
        'panel_sha256':sha(REPO/'data/panel.csv'),'raw_archive_sha256':sha(ROOT/'raw/spectra_rrl.zip'),
        'licence_attribution_present':True,
        'caveat':'Registration classification is an explicit rule-based proxy, not field verification or certification of operational coverage.'}
    assert prep['raw_archive_sha256']==result['raw_archive_sha256']
    save_json(ROOT/'results/validation.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
