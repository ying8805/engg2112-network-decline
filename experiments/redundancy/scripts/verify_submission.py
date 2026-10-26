"""Targeted final checks and curated future PR allowlist. Never stages files."""
import json
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
import pandas as pd
from dulwich.repo import Repo
from dulwich import porcelain

from analyse import ROOT,REPO,sha,save_json
from population_comparison import EXPECTED_SHA,display_population

PACKAGE={
    'docs':['o4.json','o4_operator_redundancy.png','o4_performance_comparison.png'],
    'root':['.gitignore','README.md','REPORT_SECTION.md','REPORT_LAYOUT.pdf','POPULATION_METHOD.md',
            'SCHEMA_NOTES.md','SOURCES.md','PROTOCOL.md','PANEL_REBUILD.md','PR_FILES.txt','LOCAL_REVIEW.md'],
    'provenance':['acma_preparation.json','environment.txt','panel_rebuild.json','repository_baseline.json','population_source.json'],
    'results':['data_quality.json','headline_comparison.csv','comparison.csv','classification_sensitivity.csv',
        'common_strata_contrasts.csv','coordinate_sensitivity.csv','radius_sensitivity.csv',
        'region_redundancy.csv','region_performance.csv','region_quarter_results.csv',
        'population_by_grid.csv','population_speed_comparison.csv','population_assignment_sensitivity.csv',
        'POPULATION_COMPARISON.md','validation.json','layout_validation.json','final_validation.json'],
    'scripts':['analyse.py','prepare_acma.py','run_o4.py','population_comparison.py','finish_submission.py',
        'verify_o4.py','verify_submission.py','rebuild_original_panel.py','test_analysis.py','test_acma.py','test_population.py']}


def main():
    regions=pd.read_csv(ROOT/'results/region_redundancy.csv',dtype={'region':str})
    pop=pd.read_csv(ROOT/'results/population_by_grid.csv',dtype={'region':str})
    summaries=pd.read_csv(ROOT/'results/population_speed_comparison.csv')
    scenarios=pd.read_csv(ROOT/'results/population_assignment_sensitivity.csv')
    source=json.loads((ROOT/'provenance/population_source.json').read_text())
    assert sha(ROOT/'work/population/GEOTIFF.zip')==EXPECTED_SHA==source['source_sha256']
    cells=pd.read_csv(ROOT/'work/population/assigned_population_cells.csv',dtype={'region':str})
    assert not cells.raster_cell_id.duplicated().any()
    assert len(cells)==26209 and int(cells.valid.sum())==26192
    assert cells.region.isin(regions.region).all()
    assert len(pop)==len(regions)==410 and not pop.region.duplicated().any()
    reconciled=cells[cells.valid].groupby('region').population_value.sum()
    np.testing.assert_allclose(pop.set_index('region').population_estimate.sort_index(),reconciled.sort_index(),rtol=1e-12,atol=1e-8)
    assert (pop.valid_population_cells>0).all() and (pop.valid_population_cells<pop.expected_population_cells).sum()==15
    assert int((pop.expected_population_cells-pop.valid_population_cells).sum())==17
    for (definition,radius),table in summaries.groupby(['definition','radius_km']):
        assert table.grids.sum()==410
        assert table.grids_with_population_data.sum()==410 and table.grids_missing_population.sum()==0
        assert table.valid_1km_cells.sum()==26192 and table.expected_1km_cells.sum()==26209
        assert np.isclose(table.modelled_population_sum.sum(),reconciled.sum())
        prefix='operators_' if definition=='broader' else 'explicit_pmts_only_operators_'
        for row in table.itertuples():
            part=pop[pop[f'{prefix}{radius}km'].eq(row.operators)]
            assert len(part)==row.grids
            if len(part):
                assert np.isclose(part.population_estimate.sum(),row.modelled_population_sum)
                assert row.population_display==display_population(row.modelled_population_sum)
                assert np.isclose(part.median_download_mbps.median(),row.median_download_mbps)
            else:assert pd.isna(row.modelled_population_sum)
    for scenario in source['scenarios']:
        data=scenarios[(scenarios.assignment_scenario==scenario['scenario']) & (scenarios.radius_km==10)]
        for definition,table in data.groupby('definition'):
            assert np.isclose(table.modelled_population_sum.sum(),scenario['population_sum'])
            assert table.valid_1km_cells.sum()==scenario['unique_valid_cells_assigned']
    report=(ROOT/'REPORT_SECTION.md').read_text()
    assert 'not reproduced under the strict classification' in report
    assert all(f'## {h}' in report for h in ['Question','Data','Method','Result','Limitation'])
    assert report.count('![')==2 and 'Figure 1.' in report and 'Figure 2.' in report
    assert 550<=len(report.split())<=650
    broad=summaries.query('definition=="broader" and radius_km==10').sort_values('operators')
    assert list(broad.grids)==[1,10,10,389]
    assert list(broad.population_display)==['<100','~1,100','~1,500','~7,200,000']
    assert [f'{x:.2f}' for x in broad.median_download_mbps]==['2.83','18.96','36.50','83.15']
    assert '99.93%' in report and '15 are partial' in report
    limits=scenarios.query('definition=="broader" and radius_km==10 and operators==3').modelled_population_sum
    assert f'{limits.min()/1e6:.2f}'=='6.91' and f'{limits.max()/1e6:.2f}'=='7.24'
    assert '6.91 and 7.24 million' in report
    strict=pd.read_csv(ROOT/'results/classification_sensitivity.csv').query('definition=="explicit_pmts_only" and radius_km==10')
    assert [f'{x:.2f}' for x in strict.median_region_download_mbps]==['91.67','74.28','69.54','88.43']
    layout=json.loads((ROOT/'results/layout_validation.json').read_text())
    assert layout['report_sha256']==sha(ROOT/'REPORT_SECTION.md') and layout['pdf_sha256']==sha(ROOT/'REPORT_LAYOUT.pdf')
    assert layout['pages']==1 and layout['figures_embedded']==2 and layout['all_text_inside_page']
    assert layout['body_font_points']>=9.5 and layout['caption_font_points']>=8
    pdf=(ROOT/'REPORT_LAYOUT.pdf').read_bytes()
    assert len(re.findall(rb'/Type\s*/Page\b',pdf))==1
    dashboard=json.loads((REPO/'docs/o4.json').read_text())
    assert dashboard['id']=='o4' and dashboard['status']=='done'
    assert 'not reproduced under strict' in dashboard['answer']
    assert len(dashboard['limits'])==len(set(dashboard['limits']))
    assert len(dashboard['sources'])==len({s['url'] for s in dashboard['sources']})
    for table in dashboard['tables']:
        assert all(len(r)==len(table['columns']) and all(isinstance(v,str) for v in r) for r in table['rows'])
    for figure in dashboard['figures']:
        assert (REPO/'docs'/figure['src']).exists() and all(figure[k] for k in ('alt','caption'))
    for source_url in dashboard['sources']:assert source_url['url'].startswith('https://')
    assert len(dashboard['tables'][0]['rows'])==4
    for i,row in enumerate(dashboard['tables'][0]['rows']):
        assert row[0]==str(i) and row[3]==broad.iloc[i].population_display and row[-1]==f'{broad.iloc[i].median_download_mbps:.2f}'
    baseline=json.loads((ROOT/'provenance/repository_baseline.json').read_text())
    assert all(sha(REPO/path)==expected for path,expected in baseline['tracked_sha256'].items())
    with Repo(str(REPO)) as repo:
        state=porcelain.status(repo)
        assert not any(state.staged.values()) and not state.unstaged
        assert repo.head().decode()==baseline['initial_head']
        protected=[p.relative_to(REPO).as_posix() for folder in ['raw','private','work','__pycache__'] for p in (ROOT/folder).rglob('*') if p.is_file()]
        protected+=['data/panel.csv']
        assert set(porcelain.check_ignore(repo,protected))==set(protected)
        indexed={p.decode().replace('\\','/') for p in repo.open_index()}
        assert not indexed.intersection(protected)
    run=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'scripts'),'-p','test_*.py','-v'],capture_output=True,text=True)
    (ROOT/'provenance/test_output.txt').write_text(run.stdout+run.stderr,encoding='utf-8')
    assert run.returncode==0,run.stderr
    assert 'Ran 20 tests' in run.stderr
    names=[f'docs/{name}' for name in PACKAGE['docs']]
    names+=[f'experiments/redundancy/{name}' for name in PACKAGE['root']]
    for directory in ('provenance','results','scripts'):
        names += [f'experiments/redundancy/{directory}/{name}' for name in PACKAGE[directory]]
    assert len(names)==len(set(names))
    names.sort();(ROOT/'PR_FILES.txt').write_text('\n'.join(names)+'\n')
    with Repo(str(REPO)) as repo:
        assert not list(porcelain.check_ignore(repo,names))
        untracked={p.decode().replace('\\','/') for p in porcelain.status(repo,untracked_files='all').untracked}
        scoped={p for p in untracked if p.startswith('experiments/redundancy/') or p.startswith('docs/o4')}
        assert scoped==set(names),sorted(scoped.symmetric_difference(names))
    result={'recommendation':'READY for user review and future scoped exploratory PR',
        'population_comparison':'Verified ABS modelled 2024 raster; no repeated SA2 totals',
        'population_unique_cells_checked':len(cells),'valid_population_cells':int(cells.valid.sum()),
        'population_matched_grids':410,'partial_population_grids':15,'missing_population_grids':0,
        'independent_projection_reference':'Three public EPSG:3577 fixtures agree within 1 mm',
        'scenario_population_reconciliation':'passed for both definitions and all radii',
        'report_words_including_title_captions_references':len(report.split()),
        'report_pages':1,'page_allocation':1.25,'figures_embedded':2,'layout_visually_reviewed':True,
        'dashboard_schema_and_population_values':'passed','tests_passed':20,
        'existing_tracked_files_unchanged':224,'raw_private_work_panel_excluded':True,
        'git_staged_changes':0,'new_commits':0,'full_pipeline_rerun':False,
        'previous_proposed_files':52,'proposed_files':len(names),
        'removed_from_proposal':'Historical audits, duplicate figures/review, machine logs, legacy wrappers and redundant subset exports; retained locally',
        'remaining_evidence_limits':['Population is modelled, date-mismatched and sensitive to boundary assignment.',
            'The speed gradient is broader-definition-specific; strict classification does not reproduce it.',
            'Broader low-candidate groups have no eligible decline windows at 10 km.',
            'Candidate infrastructure and grid population do not measure operational coverage or single-network dependence.'],
        'publication_authorized':False,'source_sha256':EXPECTED_SHA}
    save_json(ROOT/'results/final_validation.json',result)
    assert all((REPO/name).exists() for name in names)
    assert not any((REPO/name).stat().st_size>5*1024**2 for name in names)
    result['proposed_total_bytes']=sum((REPO/name).stat().st_size for name in names)
    save_json(ROOT/'results/final_validation.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
