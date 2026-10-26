"""ABS modelled 1 km population apportioned once by raster-cell centre.

Uses the existing O4 aggregate outputs, not population-growth AP experiments.
No SA2 population is copied to grids. The source raster is cached under ignored
work/. A cell is counted at most once in each separately labelled scenario.
"""
from __future__ import annotations
from pathlib import Path
from zipfile import ZipFile
import json
import sys
import hashlib

import numpy as np
import pandas as pd
from PIL import Image
import requests

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
sys.path.insert(0,str(REPO/'src'))
from boundary import _inside

URL='https://www.abs.gov.au/statistics/people/population/regional-population/2023-24/GEOTIFF.zip'
SOURCE_PAGE='https://www.abs.gov.au/statistics/people/population/regional-population/2023-24'
METHOD_PAGE='https://www.abs.gov.au/methodologies/regional-population-methodology/2023-24'
EXPECTED_SHA='833e00886fedf9b9da146d30a255d22e242f82c8a914b28770e4f7944e00d720'
RASTER_MEMBER='GEOTIFF/apg24e_1_0_0.tif'
N=4096
A=6378137.
F=1/298.257222101
E2=2*F-F*F
E=np.sqrt(E2)


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def q_of(phi):
    s=np.sin(phi)
    return (1-E2)*(s/(1-E2*s*s)-np.log((1-E*s)/(1+E*s))/(2*E))


P1,P2=np.radians([-18.,-36.])
M1=np.cos(P1)/np.sqrt(1-E2*np.sin(P1)**2)
M2=np.cos(P2)/np.sqrt(1-E2*np.sin(P2)**2)
NN=(M1*M1-M2*M2)/(q_of(P2)-q_of(P1))
CC=M1*M1+NN*q_of(P1)
RHO0=A*np.sqrt(CC)/NN


def albers_forward(lon,lat):
    """GRS80 Albers parameters read from ABS GeoTIFF (EPSG:3577)."""
    phi=np.radians(np.asarray(lat));theta=NN*np.radians(np.asarray(lon)-132)
    rho=A*np.sqrt(CC-NN*q_of(phi))/NN
    return rho*np.sin(theta), RHO0-rho*np.cos(theta)


def albers_inverse(x,y):
    x=np.asarray(x);dy=RHO0-np.asarray(y)
    rho=-np.hypot(x,dy)
    theta=np.arctan2(-x,-dy)
    target=(CC-(rho*NN/A)**2)/NN
    phi=np.arcsin(np.clip(target/2,-1,1))
    for _ in range(8):
        derivative=2*(1-E2)*np.cos(phi)/(1-E2*np.sin(phi)**2)**2
        phi+=(target-q_of(phi))/derivative
    return 132+np.degrees(theta/NN),np.degrees(phi)


def tile_code(lon,lat):
    tx=np.floor((np.asarray(lon)+180)/360*N).astype(np.int64)
    s=np.sin(np.radians(np.asarray(lat)))
    ty=np.floor((.5-np.log((1+s)/(1-s))/(4*np.pi))*N).astype(np.int64)
    return ty*N+tx


def in_geometry(lon,lat,geometry):
    """Polygon holes are subtracted within each polygon before union."""
    polys=[geometry['coordinates']] if geometry['type']=='Polygon' else geometry['coordinates']
    result=np.zeros(len(lon),bool)
    for poly in polys:
        exterior=np.asarray(poly[0])
        possible=np.flatnonzero((lon>=exterior[:,0].min()) & (lon<=exterior[:,0].max()) &
            (lat>=exterior[:,1].min()) & (lat<=exterior[:,1].max()))
        for start in range(0,len(possible),128):
            ind=possible[start:start+128]
            hit=_inside(lon[ind],lat[ind],exterior)
            for hole in poly[1:]:hit &= ~_inside(lon[ind],lat[ind],np.asarray(hole))
            result[ind] |= hit
    return result


def display_population(value):
    if pd.isna(value):return 'NA'
    if value==0:return '0 (modelled)'
    if value<100:return '<100'
    unit=10**max(0,int(np.floor(np.log10(value)))-1)
    return f'~{int(np.floor(value/unit+.5)*unit):,}'


def summarize(regions):
    output=[]
    for definition,prefix in [('broader','operators_'),('strict_pmts','explicit_pmts_only_operators_')]:
        for radius in (5,10,20):
            for count in range(4):
                part=regions[regions[f'{prefix}{radius}km'].eq(count)]
                value=part.population_estimate.sum(min_count=1)
                if len(part)==0:value=np.nan
                output.append({'definition':definition,'radius_km':radius,'operators':count,
                    'grids':len(part),'grids_with_population_data':int(part.population_estimate.notna().sum()),
                    'grids_missing_population':int(part.population_estimate.isna().sum()),
                    'grids_partial_raster':int((part.valid_population_cells<part.expected_population_cells).sum()),
                    'valid_1km_cells':int(part.valid_population_cells.sum()),
                    'expected_1km_cells':int(part.expected_population_cells.sum()),
                    'raster_match_percent':100*part.valid_population_cells.sum()/part.expected_population_cells.sum() if part.expected_population_cells.sum() else np.nan,
                    'modelled_population_sum':value,'population_display':display_population(value),
                    'median_download_mbps':part.median_download_mbps.median()})
    return pd.DataFrame(output)


def main():
    cache=ROOT/'work/population';cache.mkdir(parents=True,exist_ok=True)
    archive=cache/'GEOTIFF.zip'
    if not archive.exists():
        response=requests.get(URL,timeout=90);response.raise_for_status();archive.write_bytes(response.content)
    assert sha(archive)==EXPECTED_SHA,'ABS object changed: review new metadata before using'
    with ZipFile(archive) as z:
        assert z.testzip() is None
        with z.open(RASTER_MEMBER) as source:
            image=Image.open(source)
            tags=image.tag_v2
            assert tags[33550][:2]==(1000.,1000.) and 3577 in tags[34735]
            assert str(tags[42113])=='-1'
            raster=np.array(image)
            x0,y0=tags[33922][3:5]
    regions=pd.read_csv(ROOT/'results/region_redundancy.csv',dtype={'region':str})
    performance=pd.read_csv(ROOT/'results/region_performance.csv',dtype={'region':str})
    regions=regions.merge(performance[['region','median_download_mbps']],on='region',validate='one_to_one')
    codes=tile_code(regions.lon,regions.lat)
    order=np.argsort(codes);keys=codes[order]
    assert len(np.unique(keys))==len(regions)
    # Tile corner extrema, expanded by 2 km, provide a safe small raster crop.
    tx=codes%N;ty=codes//N
    corner_x=[];corner_y=[]
    for dx,dy in ((0,0),(1,0),(0,1),(1,1)):
        lon=(tx+dx)/N*360-180
        lat=np.degrees(np.arctan(np.sinh(np.pi*(1-2*(ty+dy)/N))))
        x,y=albers_forward(lon,lat);corner_x.extend(x);corner_y.extend(y)
    col_min=max(0,int(np.floor((min(corner_x)-2000-x0)/1000)))
    col_max=min(raster.shape[1],int(np.ceil((max(corner_x)+2000-x0)/1000)))
    row_min=max(0,int(np.floor((y0-max(corner_y)-2000)/1000)))
    row_max=min(raster.shape[0],int(np.ceil((y0-min(corner_y)+2000)/1000)))
    boundary=json.loads((REPO/'data/au_states.geojson').read_text())
    geometry=next(f['geometry'] for f in boundary['features'] if 'New South Wales' in f['properties'].values())
    scenarios=[('centre',0,0),('southwest',-500,-500),('northwest',-500,500),('southeast',500,-500),('northeast',500,500)]
    summaries=[];totals=[]
    for label,dx,dy in scenarios:
        pop=np.zeros(len(regions));valid=np.zeros(len(regions),int);expected=np.zeros(len(regions),int)
        seen_cells=0
        assignments=[]
        for first in range(row_min,row_max,64):
            rr,cc=np.meshgrid(np.arange(first,min(first+64,row_max)),np.arange(col_min,col_max),indexing='ij')
            x=x0+(cc.ravel()+.5)*1000+dx;y=y0-(rr.ravel()+.5)*1000+dy
            lon,lat=albers_inverse(x,y)
            encoded=tile_code(lon,lat);pos=np.searchsorted(keys,encoded)
            matched=(pos<len(keys)) & (keys[np.minimum(pos,len(keys)-1)]==encoded)
            select=np.flatnonzero(matched)
            if not len(select):continue
            select=select[in_geometry(lon[select],lat[select],geometry)]
            idx=order[pos[select]]
            values=raster[rr.ravel()[select],cc.ravel()[select]].astype(float)
            good=np.isfinite(values)&(values>=0)
            if label=='centre':
                assignments.append(pd.DataFrame({'raster_cell_id':rr.ravel()[select]*raster.shape[1]+cc.ravel()[select],
                    'region':regions.region.to_numpy()[idx],'population_value':values,'valid':good}))
            expected+=np.bincount(idx,minlength=len(regions))
            valid+=np.bincount(idx[good],minlength=len(regions))
            pop+=np.bincount(idx[good],weights=values[good],minlength=len(regions))
            seen_cells+=int(good.sum())
        frame=regions.copy()
        frame['expected_population_cells']=expected;frame['valid_population_cells']=valid
        frame['population_estimate']=np.where(valid>0,pop,np.nan)
        summary=summarize(frame);summary['assignment_scenario']=label;summaries.append(summary)
        totals.append({'scenario':label,'unique_valid_cells_assigned':seen_cells,'population_sum':float(pop.sum())})
        assert valid.sum()==seen_cells
        if label=='centre':
            frame.to_csv(ROOT/'results/population_by_grid.csv',index=False)
            audit=pd.concat(assignments,ignore_index=True)
            assert not audit.raster_cell_id.duplicated().any(),'Population pixel assigned more than once'
            assert int(audit.valid.sum())==seen_cells
            audit.to_csv(cache/'assigned_population_cells.csv',index=False)
        print(label,seen_cells,round(pop.sum()),flush=True)
    all_scenarios=pd.concat(summaries,ignore_index=True)
    primary=all_scenarios[all_scenarios.assignment_scenario.eq('centre')]
    primary.to_csv(ROOT/'results/population_speed_comparison.csv',index=False)
    all_scenarios.to_csv(ROOT/'results/population_assignment_sensitivity.csv',index=False)
    metadata={'status':'completed_modelled_population_comparison','source_url':URL,'source_page':SOURCE_PAGE,
        'methodology_url':METHOD_PAGE,'source_sha256':EXPECTED_SHA,'source_bytes':archive.stat().st_size,
        'raster_member':RASTER_MEMBER,'population_year':2024,'source_crs':'EPSG:3577 GDA94 / Australian Albers',
        'access_date_sydney':'2026-10-26','cell_size_metres':1000,'nodata':-1,
        'source_country_population_sum':float(raster[raster>=0].sum(dtype='float64')),
        'assignment':'Each raster cell once to zoom-12 grid containing its centre, conditional on centre in strict NSW polygon; no SA2 populations repeated',
        'datum':'Albers GRS80 inverse from embedded parameters; GDA94 coordinates used with WGS84 grid numeric approximation at kilometre resolution',
        'scenarios':totals,'display_rounding':'Two significant figures; positive totals below 100 displayed <100',
        'coverage_definition':'Valid raster-cell centres / all raster-cell centres within the selected grid and strict NSW polygon, not percentage of NSW residents',
        'population_growth_investigation':'Source manifest inspected; raw ERP workbooks absent. AP results unused. SA2 ERP not apportioned uniformly; official finer-scale population grid used instead.',
        'limitations':['ABS modelled 2024 population, not enumerated 1km counts or 2026 population.',
            'Cells straddling grid/state borders use centre assignment; four +/-500m corner scenarios quantify sensitivity, not confidence intervals.',
            'Whole O4 grid inherits the operator count at its centre; residents may be farther from infrastructure.',
            'Only O4 observed NSW grids are summarized, not statewide population coverage.'],
        'inputs':{name:sha(ROOT/'results'/name) for name in ['region_redundancy.csv','region_performance.csv']}}
    (ROOT/'provenance/population_source.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(primary.query('definition == "broader" and radius_km == 10').to_string(index=False))


if __name__=='__main__':main()
