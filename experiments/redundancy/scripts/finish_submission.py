"""Build final report, compact figures, dashboard and a measured A4 layout.

Uses existing research outputs and the population extension only. Never reruns
ACMA processing, network queries, predictions or the original panel builder.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

from analyse import ROOT,REPO,SOURCES,sha,save_json
from run_o4 import ATTRIBUTION
from population_comparison import display_population,SOURCE_PAGE,METHOD_PAGE

TITLE='The speed gradient appears under the broader operator-candidate classification, but is not reproduced under the strict classification'


def figures(regions,broad,strict):
    from boundary import _rings
    plt.rcParams.update({'font.size':8,'axes.titlesize':9,'axes.labelsize':8,'legend.fontsize':7.5})
    mapfig,ax=plt.subplots(figsize=(3.55,2.35))
    for f in json.loads((REPO/'data/au_states.geojson').read_text())['features']:
        if 'New South Wales' in f['properties'].values():
            for ring,_ in _rings(f['geometry']):ax.plot(ring[:,0],ring[:,1],color='.6',lw=.4)
    for n,marker,c in zip(range(4),['x','o','^','s'],['black','.2','.4','.65']):
        part=regions[regions.operators_10km.eq(n)]
        ax.scatter(part.lon,part.lat,s=8,marker=marker,color=c,linewidths=.4,zorder=5-n,label=f'{n}: n={len(part)}')
    ax.set(xlim=(140.5,154.5),ylim=(-37.8,-27.8),aspect=1.18,xlabel='Longitude (°)',ylabel='Latitude (°)')
    ax.set_xticks([142,146,150,154]);ax.set_yticks([-36,-32,-28])
    ax.legend(loc='upper left',bbox_to_anchor=(1.02,1),borderaxespad=0,frameon=False,title='Candidates\n(grid n)',title_fontsize=7.5)
    mapfig.suptitle('Figure 1. Broader candidates (10 km)',fontsize=9,y=.98)
    mapfig.tight_layout(pad=.35,rect=(0,0,1,.92))
    mapfig.savefig(REPO/'docs/o4_operator_redundancy.png',dpi=260)
    speedfig,ax=plt.subplots(figsize=(3.55,2.35))
    x=np.arange(4);w=.35
    b=broad[broad.radius_km.eq(10)].sort_values('category',key=lambda s:s.map({'zero-observed':0,'single-observed':1,'two-observed':2,'three-observed':3}))
    s=strict.query('radius_km==10 and definition=="explicit_pmts_only"').sort_values('category',key=lambda s:s.map({'zero-observed':0,'single-observed':1,'two-observed':2,'three-observed':3}))
    broader_bars=ax.bar(x-w/2,b.median_region_download_mbps,w,label='Broader',color='.75',edgecolor='black',hatch='//',linewidth=.6)
    strict_bars=ax.bar(x+w/2,s.median_region_download_mbps,w,label='Strict PMTS',color='white',edgecolor='black',hatch='..',linewidth=.6)
    labels=[]
    for bars,counts in ((broader_bars,b.regions),(strict_bars,s.regions)):
        labels.extend(ax.bar_label(bars,labels=[f'n={int(n)}' for n in counts],padding=6 if bars is strict_bars else 3,fontsize=7))
    ax.set(xlim=(-.6,3.6),ylim=(0,120),xticks=x,xlabel='Operator candidates within 10 km',
           ylabel='Historical median download (Mbps)',title='Figure 2. Speed gradient depends on definition')
    ax.legend(loc='upper left',ncols=2,frameon=False)
    speedfig.tight_layout(pad=.35)
    speedfig.savefig(REPO/'docs/o4_performance_comparison.png',dpi=260)
    # Audit the actual rendered artists, including the eight labels and legend.
    checks={'bar_sample_sizes':{'broader':b.regions.astype(int).tolist(),'strict_pmts':s.regions.astype(int).tolist()},
            'bar_labels':[label.get_text() for label in labels]}
    mapfig.canvas.draw();speedfig.canvas.draw()
    legend_box=mapfig.axes[0].get_legend().get_window_extent(mapfig.canvas.get_renderer())
    axes_box=mapfig.axes[0].get_window_extent()
    assert legend_box.x0>=axes_box.x1,'Map legend overlaps plotting area'
    checks['map_legend_outside_plot']=True
    renderer=speedfig.canvas.get_renderer()
    boxes=[label.get_window_extent(renderer) for label in labels]
    for i,box in enumerate(boxes):
        assert box.y0>list(broader_bars.patches+strict_bars.patches)[i].get_window_extent(renderer).y1
        assert all(not box.overlaps(other) for other in boxes[i+1:]),'Sample labels overlap'
    checks['all_eight_labels_above_bars_without_overlap']=True
    for fig in (mapfig,speedfig):
        fig.canvas.draw();renderer=fig.canvas.get_renderer()
        texts=[t for t in fig.findobj(matplotlib.text.Text) if t.get_visible() and t.get_text()]
        for text in texts:
            box=text.get_window_extent(renderer)
            assert box.x0>=-1 and box.y0>=-1 and box.x1<=fig.bbox.width+1 and box.y1<=fig.bbox.height+1,'Figure text clipped'
    for name in ('o4_operator_redundancy.png','o4_performance_comparison.png'):
        pixels=plt.imread(REPO/'docs'/name)
        assert np.array_equal(pixels[:,:,0],pixels[:,:,1]) and np.array_equal(pixels[:,:,0],pixels[:,:,2]),'Non-grayscale figure'
    checks['titles_axes_and_labels_inside_images']=True
    checks['grayscale_pixels_and_distinct_symbols_hatches']=True
    return checks


def wrap(text,width,renderer,size=10,bold=False):
    prop=FontProperties(family='DejaVu Sans',size=size,weight='bold' if bold else 'normal')
    words=text.split();lines=[];current=''
    for word in words:
        trial=(current+' '+word).strip()
        points=renderer.get_text_width_height_descent(trial,prop,False)[0]*72/renderer.dpi
        if points>width and current:lines.append(current);current=word
        else:current=trial
    if current:lines.append(current)
    return lines


def plain(text):
    return re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',text).replace('**','')


def layout_pdf(title,sections,captions,population):
    """One A4 page; validate all text bounds and body allocation numerically."""
    W,H=595.2756,841.8898
    fig=plt.figure(figsize=(W/72,H/72),dpi=144,facecolor='white')
    fig.canvas.draw();renderer=fig.canvas.get_renderer()
    margin=30.;width=W-2*margin;gap=16.;col=(width-gap)/2
    y=H-margin;artists=[]
    title_lines=wrap(title,width,renderer,12.5,True)
    for line in title_lines:
        artists.append(fig.text(margin/W,y/H,line,size=12.5,weight='bold',va='top'))
        y-=15.
    y-=8.;body_top=y
    size=10.;leading=12.
    lines=[]
    for heading,paragraphs in sections:
        lines.append((heading,True))
        for paragraph in paragraphs:
            for line in wrap(plain(paragraph),col,renderer,size):lines.append((line,False))
            lines.append(('',False))
    # Balance columns without leaving a heading at the foot of a column.
    middle=(len(lines)+1)//2
    if lines[middle-1][1]:middle-=1
    block_height=lambda block:sum(leading if text else 3. for text,_ in block)
    body_bottom=body_top-max(block_height(lines[:middle]),block_height(lines[middle:]))
    # The population table is a separate submission artifact/dashboard table;
    # population numbers are already stated in the approximately 600-word text.
    figure_height=160.;caption_height=34.;footer_height=22.;spacing=16.
    reserved=figure_height+caption_height+footer_height+spacing
    if body_bottom<margin+reserved:
        size=9.5;leading=11.2;lines=[]
        for heading,paragraphs in sections:
            lines.append((heading,True))
            for paragraph in paragraphs:
                lines.extend((line,False) for line in wrap(plain(paragraph),col,renderer,size))
                lines.append(('',False))
        middle=(len(lines)+1)//2
        if lines[middle-1][1]:middle-=1
        body_bottom=body_top-max(block_height(lines[:middle]),block_height(lines[middle:]))
    assert body_bottom>=margin+reserved, f'Layout overflows: {body_bottom} vs {margin+reserved}'
    for x,part in [(margin,lines[:middle]),(margin+col+gap,lines[middle:])]:
        yy=body_top
        for line,bold in part:
            if line:artists.append(fig.text(x/W,yy/H,line,size=size,weight='bold' if bold else 'normal',va='top'))
            yy-=leading if line else 3.
    # Crop-free placement at intended physical print size, not shrinking an
    # unreadable nine-panel plot to a report thumbnail.
    fy=body_bottom-figure_height-6
    for j,name in enumerate(('o4_operator_redundancy.png','o4_performance_comparison.png')):
        ax=fig.add_axes([(margin+j*(col+gap))/W,fy/H,col/W,figure_height/H])
        ax.imshow(plt.imread(REPO/'docs'/name));ax.axis('off')
        yy=fy-2
        for line in wrap(captions[j],col,renderer,8):
            artists.append(fig.text((margin+j*(col+gap))/W,yy/H,line,size=8,va='top'))
            yy-=9.2
        assert yy>margin+15,'Caption overflow'
    footer1=fig.text(margin/W,43/H,'[1] ABS Regional Population 2023-24: modelled 2024 population grid and methodology.',size=7.5,va='top')
    footer1.set_url(SOURCE_PAGE);artists.append(footer1)
    footer2=fig.text(margin/W,34/H,'[2] ACMA emergency calls;',size=7.5,va='top')
    footer2.set_url('https://www.acma.gov.au/emergency-calls');artists.append(footer2)
    footer3=fig.text(140/W,34/H,'2023 Optus outage investigation outcome.',size=7.5,va='top')
    footer3.set_url('https://www.acma.gov.au/articles/2024-11/optus-pays-12-million-penalty-triple-zero-outage');artists.append(footer3)
    artists.append(fig.text(margin/W,25/H,ATTRIBUTION+'.',size=7.5,va='top'))
    fig.canvas.draw();renderer=fig.canvas.get_renderer()
    for artist in artists:
        box=artist.get_window_extent(renderer)
        assert box.x0>=0 and box.y0>=0 and box.x1<=fig.bbox.width+1 and box.y1<=fig.bbox.height+1,'Text outside page'
    fig.savefig(ROOT/'REPORT_LAYOUT.pdf')
    preview=ROOT/'work/submission_audit/report_layout.png';preview.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(preview,dpi=180)
    plt.close(fig)
    return {'paper':'A4','pages':1,'page_width_points':W,'page_height_points':H,
        'body_font_points':size,'caption_font_points':8,'all_text_inside_page':True,
        'allocation_pages':1.25,'actual_pages':1,'within_allocation':True,
        'word_layout_lines':len(lines),'table_included':False,'population_table_artifact':'results/POPULATION_COMPARISON.md','figures_embedded':2}


def main():
    qa=json.loads((ROOT/'results/data_quality.json').read_text())
    pop=pd.read_csv(ROOT/'results/population_speed_comparison.csv')
    sensitivity=pd.read_csv(ROOT/'results/population_assignment_sensitivity.csv')
    broad=pd.read_csv(ROOT/'results/headline_comparison.csv')
    strict=pd.read_csv(ROOT/'results/classification_sensitivity.csv')
    regions=pd.read_csv(ROOT/'results/region_redundancy.csv')
    figure_checks=figures(regions,broad,strict)
    main_pop=pop.query('definition=="broader" and radius_km==10').sort_values('operators')
    exact=main_pop.modelled_population_sum.tolist()
    spans=sensitivity.query('definition=="broader" and radius_km==10').groupby('operators').modelled_population_sum.agg(['min','max'])
    sections=[('Question',[
        'How do population and historical download speeds differ across NSW operator-candidate groups, and can persistent decline be compared? The speed gradient appears under the broader classification but is not reproduced under strict classification (Figure 2).']),
      ('Data',[
        f'Of 768 original bounding-box grids, strict NSW centroid containment retains {qa["regions_analysed_for_redundancy"]} grids ({qa["observed_rows"]:,} observations); 358 belong to other states/ACT or remain unmatched. No offshore snapping or model-history filter is applied. Rural grids remain included. Historical Ookla speeds span 2019 Q1–2026 Q1, with at least 50 tests per observation. ACMA registrations are a 26 October 2026 snapshot, not historical deployments. Population uses the ABS 2024 modelled one-kilometre raster [1].']),
      ('Method',[
        'Exact corporate identities map registrations to Telstra, Optus and TPG/Vodafone. The strict definition retains explicit PMTS base records; the broader definition also includes inferred mobile-compatible spectrum registrations. Receivers, noncurrent licences and unrelated services are excluded. Sectors and repeated licences collapse to operator-location pairs; shared and ambiguous records remain qualified.',
        'Great-circle searches count candidates within 5, 10 and 20 km. Each population raster cell is assigned once to the measured grid containing its centre, conditional on that centre being in NSW. No SA2 total is repeated across grids. Valid-cell matching and NoData are reported separately from zero population. Four cell-corner assignments assess border sensitivity; these are scenarios, not confidence intervals.',
        'Speed is the median of grid-level historical medians. A raw persistent decline requires speeds in both following consecutive quarters to be at most 80% of baseline, with at least 50 tests throughout. Missing futures remain unknown. No model is trained.']),
      ('Result',[
        'At 10 km, broader groups with zero, one, two and three candidates contain 1, 10, 10 and 389 grids (Figure 1). Their historical median speeds are 2.83, 18.96, 36.50 and 83.15 Mbps. Strict-group medians are 91.67, 74.28, 69.54 and 88.43 Mbps, without a monotonic gradient.',
        f'The corresponding broader groups contain fewer than 100, approximately 1,100, 1,500 and 7.2 million modelled people within the observed grids. All 410 grids have some valid raster data; {int(main_pop.grids_partial_raster.sum())} are partial. Valid raster-cell matching is 100% in the first three groups and {main_pop.iloc[3].raster_match_percent:.2f}% in the last. Assignment scenarios place the last total between {spans.loc[3,"min"]/1e6:.2f} and {spans.loc[3,"max"]/1e6:.2f} million. These are estimated populations, not populations proven to depend on one network.',
        'Within rural/regional grids, broader speeds remain ordered at 2.83, 18.96, 36.50 and 68.76 Mbps. All 84 urban grids fall in the broader three-candidate group, preventing an urban comparison. The broader ordering persists across search radii, while strict results do not.',
        f'All {qa["eligible_windows"]:,} eligible decline windows belong to the broader three-candidate group at 10 km; {qa["persistent_raw_declines"]} decline and {qa["unassessable_windows"]:,} baseline rows are unassessable. Consequently, greater decline vulnerability cannot be compared.']),
      ('Limitation',[
        'Population is modelled for 2024, while infrastructure is a 2026 snapshot and speeds span different histories. A grid inherits its centre’s classification; people elsewhere in that grid may face different infrastructure. Raster missingness, boundary assignment, self-selected tests and thin rural histories limit interpretation. Counts cover measured grids, not statewide residents or operational coverage.',
        'Registration does not establish live service, independent power/backhaul or a defensible 4G/5G indicator. No causal or predictive effect is established. ACMA permits emergency calls through another available network, but its 2023 Optus investigation documents failed emergency access [2]. Nearby infrastructure therefore cannot guarantee successful calls. Signal strength, voice quality and emergency-call success were not measured.'])]
    captions=['Figure 1. Broader candidate groups at 10 km; symbols mark measured grid centres, not coverage.',
              'Figure 2. Historical median speeds; n denotes grids. The broader gradient is absent under strict PMTS classification.']
    lines=[f'# {TITLE}','']
    for head,paras in sections:
        lines += [f'## {head}','',*['\n\n'.join(paras)],'']
    lines += ['![Figure 1: candidate map](../../docs/o4_operator_redundancy.png)',captions[0],'',
              '![Figure 2: classification comparison](../../docs/o4_performance_comparison.png)',captions[1],'',
              '[1] [ABS population source and methodology](POPULATION_METHOD.md). [2] [ACMA guidance and investigation](SOURCES.md#emergency-calling).',
              '',ATTRIBUTION+'.']
    report='\n'.join(lines)+'\n';(ROOT/'REPORT_SECTION.md').write_text(report,encoding='utf-8')
    table_lines=['# Population and speed comparison','',
        '2024 ABS modelled population assigned once by 1 km cell centre. All values describe observed O4 grids, not statewide coverage or confirmed network dependence. Population is displayed to two significant figures; raw model sums in CSV are arithmetic, not measurement precision. Matching is valid raster cells / eligible NSW raster-cell centres, not resident coverage.','']
    for definition in ('broader','strict_pmts'):
        table_lines += [f'## {definition}','',
            '| Candidates (10 km) | Grids | Grids with population data | Modelled people | Raster matched | Missing grids / partial grids | Median Mbps |',
            '| ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
        for row in pop.query('definition==@definition and radius_km==10').sort_values('operators').itertuples():
            table_lines.append(f'| {row.operators} | {row.grids} | {row.grids_with_population_data}/{row.grids} | {row.population_display} | {row.raster_match_percent:.2f}% | {row.grids_missing_population}/{row.grids_partial_raster} | {row.median_download_mbps:.2f} |')
        table_lines += ['']
    table_lines += ['No SA2 population has been copied to multiple grids. Missing pixels are not imputed as zero; partial-grid totals include observed model pixels only. The source population is not AP, device counts or a 2026 resident count.',
        '',f'The broader three-candidate total ranges from {spans.loc[3,"min"]/1e6:.2f} to {spans.loc[3,"max"]/1e6:.2f} million under the five centre/corner assignment scenarios. This is a geometric sensitivity range, not an uncertainty interval.',
        '', 'See `population_assignment_sensitivity.csv`, `population_by_grid.csv` and `../POPULATION_METHOD.md` for full coverage and missingness.','',ATTRIBUTION+'.']
    (ROOT/'results/POPULATION_COMPARISON.md').write_text('\n'.join(table_lines)+'\n',encoding='utf-8')
    dashboard=json.loads((REPO/'docs/o4.json').read_text())
    dashboard['answer']='The historical speed gradient appears under the broader operator-candidate classification but is not reproduced under strict PMTS classification. ABS modelled population has been compared without duplicating SA2 totals. Low-broader-candidate groups have no eligible decline windows at 10 km, so greater decline vulnerability cannot be assessed.'
    dashboard['method']='Strict NSW centroid containment retains 410 of 768 bounding-box grids; 358 are in other states/ACT or unmatched. No offshore snapping or model-history filter. ACMA: 26 October 2026 snapshot; Ookla: 2019 Q1–2026 Q1 historical speeds; ABS: 2024 modelled 1 km population assigned once by cell centre. Comparisons are descriptive.'
    dashboard['figures'][0].update(caption=captions[0]+' '+ATTRIBUTION,alt='Ten-kilometre broader candidate counts at measured NSW grid centres.')
    dashboard['figures'][1].update(caption=captions[1]+' '+ATTRIBUTION,alt='Historical download medians with grid counts above eight bars: broader n=1,10,10,389; strict PMTS n=193,140,73,4.')
    pop_table={'title':'10 km broader candidate groups: modelled population and speed',
        'columns':['Candidates','Grids','Population-matched grids','Modelled people (2024)','Raster matched','Missing / partial grids','Median Mbps'],
        'rows':[[str(int(r.operators)),str(int(r.grids)),f'{int(r.grids_with_population_data)}/{int(r.grids)}',r.population_display,
                 f'{r.raster_match_percent:.2f}%',f'{int(r.grids_missing_population)} / {int(r.grids_partial_raster)}',f'{r.median_download_mbps:.2f}'] for r in main_pop.itertuples()]}
    strict10=strict.query('definition=="explicit_pmts_only" and radius_km==10')
    strict_table={'title':'Strict PMTS classification sensitivity','columns':['Group','Grids','Median Mbps','Eligible decline windows'],
        'rows':[[r.category,str(int(r.regions)),f'{r.median_region_download_mbps:.2f}',str(int(r.eligible_windows))] for r in strict10.itertuples()]}
    decline_table={'title':'Broader classification: persistent raw decline at 10 km',
        'columns':['Group','Eligible windows','Events','Frequency'],
        'rows':[[r.category,str(int(r.eligible_windows)),str(int(r.persistent_declines)),
                 f'{100*r.decline_frequency:.2f}%' if r.eligible_windows else 'Not assessable']
                for r in broad[broad.radius_km.eq(10)].itertuples()]}
    dashboard['tables']=[pop_table,strict_table,decline_table]
    dashboard['limits']=[x for x in dashboard['limits'] if not x.startswith('Population')]
    dashboard['limits'] += ['Population is ABS modelled 2024 data, not exact counts or 2026 residents. All grids inherit the candidate count at their centre.',
        'Raster matching describes pixel availability, not the share of NSW residents served. Fifteen grids have partial raster data; missing pixels are not zero.',
        'Centre/corner assignments put the broader three-candidate population between 6.91 and 7.24 million; this is not a confidence interval.',
        'Strict inventory classification is incomplete and does not reproduce a monotonic speed gradient.']
    dashboard['sources']=[s for s in dashboard['sources'] if s['name']!='ABS 2024 modelled population grid']
    dashboard['sources'].append({'name':'ABS 2024 modelled population grid','url':SOURCE_PAGE})
    dashboard['sources'].append({'name':'ABS population-grid methodology','url':METHOD_PAGE})
    dashboard['limits']=list(dict.fromkeys(dashboard['limits']))
    dashboard['sources']=list({s['url']:s for s in dashboard['sources']}.values())
    save_json(REPO/'docs/o4.json',dashboard)
    layout=layout_pdf(TITLE,sections,captions,pop)
    layout['figure_checks']=figure_checks
    layout.update(report_words_whitespace=len(report.split()),report_body_words=len(' '.join(p for _,paras in sections for p in paras).split()),
        report_sha256=sha(ROOT/'REPORT_SECTION.md'),pdf_sha256=sha(ROOT/'REPORT_LAYOUT.pdf'))
    save_json(ROOT/'results/layout_validation.json',layout)
    plt.close('all')
    print(json.dumps(layout,indent=2))


if __name__=='__main__':main()
