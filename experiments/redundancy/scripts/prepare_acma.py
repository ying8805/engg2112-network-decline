"""Inspect and normalize a user-downloaded Spectra RRL archive locally.

Never downloads, accepts terms, prints clients, or writes raw/site data to a
public output. Corporate mapping is exact, limited to CLIENT_TYPE_ID=5.
Spectrum candidates remain inferred, distinct from explicit PMTS base records.
"""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import json
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from analyse import ROOT, REPO, EARTH_KM, sha, save_json, require

EXACT_NAMES = {
    'TELSTRA LIMITED': 'Telstra',
    'TELSTRA 3G SPECTRUM HOLDINGS PTY LTD': 'Telstra',
    'OPTUS MOBILE PTY LIMITED': 'Optus',
    'VODAFONE AUSTRALIA PTY LIMITED': 'TPG/Vodafone',
    'VODAFONE HUTCHISON AUSTRALIA PTY LIMITED': 'TPG/Vodafone',
    'TPG INTERNET PTY LTD': 'TPG/Vodafone',
}
# Lower/upper MHz limits: compatible base-transmit ranges, not technology tags.
# TDD bands are candidate wireless broadband, potentially fixed wireless.
BANDS = {'850': [(1805, 1880)], '854': [(2110, 2170)],
         '857': [(2300, 2400)], '861': [(3400, 3800)],
         '866': [(24250, 27500)], '868': [(869, 890)],
         '870': [(758, 803)], '871': [(2620, 2690)],
         '873': [(859, 894), (925, 960)]}
DEVICE_COLS = ['SDD_ID', 'LICENCE_NO', 'DEVICE_REGISTRATION_IDENTIFIER',
    'DEVICE_TYPE', 'SITE_ID', 'FREQUENCY', 'BANDWIDTH', 'SV_ID', 'SS_ID',
    'CLASS_OF_STATION_CODE', 'NATURE_OF_SERVICE_ID', 'EMISSION',
    'TECH_SPEC_ID', 'AUTHORISATION_DATE', 'SITE_RADIUS']


def normalized_name(value):
    return ' '.join(value.upper().split())


def map_operator(clients):
    names = clients.LICENCEE.map(normalized_name)
    return names.map(EXACT_NAMES).where(clients.CLIENT_TYPE_ID.eq('5'))


def candidate_band(frame):
    freq = pd.to_numeric(frame.FREQUENCY, errors='coerce') / 1e6
    allowed = pd.Series(False, index=frame.index)
    for code, intervals in BANDS.items():
        for low, high in intervals:
            allowed |= frame.lic_SS_ID.eq(code) & freq.between(low, high)
    return allowed


def classify(frame):
    """Classification evidence hierarchy; no generation inferred from band."""
    explicit = (frame.lic_SV_ID.eq('10') & frame.lic_SS_ID.isin(['125', '127'])
                & frame.SV_ID.eq('10') & frame.SS_ID.isin(['125', '127'])
                & frame.CLASS_OF_STATION_CODE.eq('FB'))
    inferred = (frame.lic_SV_ID.eq('85') & frame.SV_ID.eq('85')
                & frame.SS_ID.eq(frame.lic_SS_ID) & candidate_band(frame))
    return np.select([explicit, inferred], ['explicit_pmts', 'spectrum_inferred'], default='excluded')


def workbook_rows(archive):
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with ZipFile(BytesIO(archive.read('DOC/Summary_of_Spectra_RRL_Format.xlsx'))) as book:
        shared = [''.join(t.itertext()) for t in ET.fromstring(book.read('xl/sharedStrings.xml')).findall('s:si', ns)]
        result = []
        for path in book.namelist():
            if not (path.startswith('xl/worksheets/sheet') and path.endswith('.xml')):
                continue
            for row in ET.fromstring(book.read(path)).findall('.//s:row', ns):
                values = []
                for cell in row.findall('s:c', ns):
                    value = cell.find('s:v', ns)
                    if value is not None:
                        values.append(shared[int(value.text)] if cell.get('t') == 's' else value.text)
                result.append(values)
        return result


def pair_cluster_counts(locations):
    """Proximity clustering is a sensitivity bound, not a claimed tower match."""
    coords = np.radians(locations[['lat', 'lon']].to_numpy())
    tree = BallTree(coords, metric='haversine')
    result = []
    for metres in (25, 50, 100):
        pairs = tree.query_radius(coords, r=metres/1000/EARTH_KM)
        parent = np.arange(len(locations))
        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        pair_count = 0
        for i, hits in enumerate(pairs):
            for j in hits:
                if j > i:
                    pair_count += 1
                    parent[find(j)] = find(i)
        result.append({'metres': metres, 'nearby_pairs': pair_count,
                       'proximity_clusters': len({find(i) for i in range(len(parent))})})
    return result


def main():
    archive_path = ROOT / 'raw/spectra_rrl.zip'
    private = ROOT / 'private'
    private.mkdir(exist_ok=True)
    date = pd.Timestamp('2026-10-26')
    qa = {'raw_archive_sha256': sha(archive_path), 'snapshot_date': str(date.date()),
          'snapshot_date_basis': 'Archive member timestamps and latest licence/device dates; timezone of ZIP timestamps unspecified',
          'user_supplied_download': True, 'agent_accepted_terms': False,
          'encoding': 'UTF-8', 'source_crs': 'EPSG:4283 (GDA94)',
          'frequency_unit': 'Hz', 'site_data_publication': False}
    with ZipFile(archive_path) as z:
        require(z.testzip() is None, 'Corrupt archive CRC')
        rows = workbook_rows(z)
        dictionary = '\n'.join(' | '.join(row) for row in rows)
        require('Datum - GDA94' in dictionary and 'in Hertz' in dictionary,
                'Coordinate/frequency dictionary differs from reviewed schema')
        qa['archive_members'] = [{'name': i.filename, 'bytes': i.file_size,
                                  'zip_date': list(i.date_time)} for i in z.infolist()]
        qa['reference_documents_read'] = ['README.TXT', 'LICENCE.TXT', 'DOC/cr_tables_oracle.sql',
            'DOC/Summary_of_Spectra_RRL_Format.xlsx', 'DOC/RRLDataDownloads_ERD.jpg', 'DOC/offline_rrl_link.htm']
        # Only the three corporate classification fields are loaded. Postal and
        # natural-person contact fields are never used in this research.
        clients = pd.read_csv(z.open('client.csv'), dtype=str, keep_default_na=False,
                              usecols=['CLIENT_NO', 'LICENCEE', 'CLIENT_TYPE_ID'])
        clients['operator'] = map_operator(clients)
        licences = pd.read_csv(z.open('licence.csv'), dtype=str, keep_default_na=False)
        sites = pd.read_csv(z.open('site.csv'), dtype=str, keep_default_na=False,
                            usecols=['SITE_ID', 'LATITUDE', 'LONGITUDE', 'SITE_PRECISION', 'STATE'])
        for table, key in ((clients, 'CLIENT_NO'), (licences, 'LICENCE_NO'), (sites, 'SITE_ID')):
            require(not table[key].duplicated().any(), f'Duplicate {key}')
        qa['table_rows'] = {'client': len(clients), 'licence': len(licences), 'site': len(sites)}
        holders = clients[clients.operator.notna()][['CLIENT_NO', 'operator']]
        mapped = licences.merge(holders, on='CLIENT_NO', validate='many_to_one')
        effect = pd.to_datetime(mapped.DATE_OF_EFFECT, errors='coerce')
        expiry = pd.to_datetime(mapped.DATE_OF_EXPIRY, errors='coerce')
        current = mapped.STATUS.eq('1') & effect.notna() & expiry.notna() & effect.le(date) & expiry.ge(date)
        qa['mapped_licences'] = len(mapped)
        qa['mapped_noncurrent_or_unresolved_licences'] = int((~current).sum())
        mapped = mapped[current]
        # Exact company identities are retained only in ignored private review.
        clients[clients.operator.notna()].to_csv(private / 'operator_mapping.csv', index=False)
        jv = clients.loc[clients.LICENCEE.map(normalized_name).eq('MOBILE JV PTY LIMITED'), 'CLIENT_NO']
        jv_licences = licences.loc[licences.CLIENT_NO.isin(jv), 'LICENCE_NO']
        mapped_ids = set(mapped.LICENCE_NO)
        all_licences = set(licences.LICENCE_NO)
        all_sites = set(sites.SITE_ID)
        keep = []
        qa.update(total_device_records=0, device_licence_orphans=0, device_site_orphans=0,
                  unassigned_joint_venture_transmit_records=0)
        for chunk in pd.read_csv(z.open('device_details.csv'), dtype=str, keep_default_na=False,
                                 usecols=DEVICE_COLS, chunksize=150000):
            qa['total_device_records'] += len(chunk)
            qa['device_licence_orphans'] += int((~chunk.LICENCE_NO.isin(all_licences)).sum())
            qa['device_site_orphans'] += int((chunk.SITE_ID.ne('') & ~chunk.SITE_ID.isin(all_sites)).sum())
            qa['unassigned_joint_venture_transmit_records'] += int((chunk.LICENCE_NO.isin(jv_licences) & chunk.DEVICE_TYPE.eq('T')).sum())
            selected = chunk[chunk.LICENCE_NO.isin(mapped_ids)].copy()
            keep.append(selected)
        devices = pd.concat(keep, ignore_index=True)
        require(not devices.duplicated(['SDD_ID', 'DEVICE_TYPE']).any(), 'Duplicate device+direction key')
        devices = devices.merge(mapped.add_prefix('lic_'), left_on='LICENCE_NO', right_on='lic_LICENCE_NO', validate='many_to_one')
        devices['classification'] = classify(devices)
        qa['mapped_device_records'] = len(devices)
        qa['mapped_receive_records_excluded'] = int(devices.DEVICE_TYPE.ne('T').sum())
        approved = pd.to_datetime(devices.AUTHORISATION_DATE, errors='coerce')
        authorized = approved.notna() & approved.le(date)
        qa['mapped_device_future_or_missing_authorisation'] = int((~authorized).sum())
        accepted = devices.DEVICE_TYPE.eq('T') & authorized & devices.classification.ne('excluded')
        selected = devices[accepted].merge(sites, on='SITE_ID', how='left', validate='many_to_one')
        qa['accepted_before_coordinate_checks'] = len(selected)
        selected['lat'] = pd.to_numeric(selected.LATITUDE, errors='coerce')
        selected['lon'] = pd.to_numeric(selected.LONGITUDE, errors='coerce')
        valid = selected.lat.between(-44, -9) & selected.lon.between(112, 154.5)
        qa['accepted_missing_site_or_invalid_mainland_coordinates'] = int((~valid).sum())
        selected = selected[valid].copy()
        # The whole mainland national archive is used; no NSW boundary truncates
        # sites across the 20 km search radius or ACT/state borders.
        qa['accepted_classifications'] = selected.classification.value_counts().to_dict()
        qa['accepted_site_precision_records'] = selected.SITE_PRECISION.value_counts().to_dict()
        qa['accepted_empty_technology_fields'] = int(selected.TECH_SPEC_ID.eq('').sum())
        # Do not export or invent technology labels from emission or frequency.
        selected['operator'] = selected.lic_operator
        selected['fdd_or_explicit'] = (selected.classification.eq('explicit_pmts')
            | ~selected.lic_SS_ID.isin(['857', '861', '866']))
        # Merge exactly identical coordinates across registry IDs. Nearby but
        # distinct coordinates are assessed as count bounds, not silently merged.
        canonical = selected[['SITE_ID', 'lat', 'lon']].drop_duplicates()
        require(not canonical.SITE_ID.duplicated().any(), 'Site coordinates conflict')
        canonical['physical_site_id'] = canonical.groupby(['lat', 'lon']).SITE_ID.transform('min')
        selected = selected.merge(canonical[['SITE_ID', 'physical_site_id']], on='SITE_ID', validate='many_to_one')
        selected[['SDD_ID','DEVICE_TYPE','LICENCE_NO','SITE_ID','operator','classification',
                  'physical_site_id','lat','lon','FREQUENCY','SITE_PRECISION']].to_csv(private / 'accepted_record_audit.csv', index=False)
        pairs = selected.groupby(['physical_site_id', 'operator'], as_index=False).agg(
            lat=('lat', 'first'), lon=('lon', 'first'), registrations=('SDD_ID', 'size'),
            has_explicit_pmts=('classification', lambda x: bool(x.eq('explicit_pmts').any())),
            has_fdd_or_explicit=('fdd_or_explicit', 'any'))
        pairs['possible_5g'] = False  # helper interprets absence as unknown, not false
        pairs.to_csv(private / 'operator_sites.csv', index=False)
        qa.update(accepted_records=len(selected), unique_registry_site_ids=selected.SITE_ID.nunique(),
                  coordinate_deduplicated_sites=pairs.physical_site_id.nunique(),
                  operator_site_pairs=len(pairs),
                  collapsed_registration_records=len(selected)-len(pairs),
                  duplicate_coordinate_site_ids=selected.SITE_ID.nunique()-pairs.physical_site_id.nunique(),
                  technology_indicator='Unavailable: no explicit generation field; frequency is not unique evidence')
        qa['operator_site_pair_counts'] = pairs.groupby('operator').size().to_dict()
        locations = pairs[['physical_site_id','lat','lon']].drop_duplicates()
        qa['physical_site_proximity_sensitivity'] = pair_cluster_counts(locations)
        qa['schema_sha256'] = {name: __import__('hashlib').sha256(z.read(name)).hexdigest()
            for name in ['DOC/Summary_of_Spectra_RRL_Format.xlsx','DOC/cr_tables_oracle.sql','DOC/RRLDataDownloads_ERD.jpg','LICENCE.TXT']}
    qa['operator_sites_sha256'] = sha(private / 'operator_sites.csv')
    save_json(ROOT / 'provenance/acma_preparation.json', qa)
    print(json.dumps({k: v for k,v in qa.items() if k not in ('archive_members', 'schema_sha256')}, indent=2))


if __name__ == '__main__':
    main()
