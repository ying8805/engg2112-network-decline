"""Synthetic edge cases only; no fixture is a research observation."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from analyse import count_nearby, load_sites, persistent, sha
import analyse


class AnalysisTests(unittest.TestCase):
    def panel(self, speeds=(100, 80, 79), times=(1, 2, 3), tests=(50, 50, 50)):
        return pd.DataFrame({'region': ['r'] * 3, 'down_mbps': speeds,
                             't': times, 'tests': tests})

    def test_inclusive_decline_and_censoring(self):
        result = persistent(self.panel()).persistent_raw
        self.assertEqual(result.iloc[0], 1)
        self.assertTrue(result.iloc[1:].isna().all())

    def test_recovery_is_not_persistent(self):
        self.assertEqual(persistent(self.panel((100, 70, 90))).persistent_raw.iloc[0], 0)

    def test_gap_remains_unknown(self):
        self.assertTrue(persistent(self.panel(times=(1, 3, 4))).persistent_raw.isna().all())

    def test_thin_or_zero_speed_is_not_healthy(self):
        self.assertTrue(persistent(self.panel(tests=(50, 49, 50))).persistent_raw.isna().all())
        self.assertTrue(persistent(self.panel(speeds=(0, 80, 79))).persistent_raw.isna().all())

    def test_distance_radii_and_colocation(self):
        regions = pd.DataFrame({'region': ['r'], 'lat': [-33.0], 'lon': [151.0]})
        sites = pd.DataFrame({'physical_site_id': ['a', 'a', 'b', 'c'],
            'operator': ['Telstra', 'Optus', 'TPG/Vodafone', 'Telstra'],
            'lat': [-33.0, -33.0, -33.072, -33.135], 'lon': [151.0] * 4,
            'possible_5g': [False, True, False, False]})
        out = count_nearby(regions, sites).iloc[0]
        self.assertEqual([out[f'operators_{r}km'] for r in (5, 10, 20)], [2, 3, 3])
        self.assertEqual([out[f'sites_{r}km'] for r in (5, 10, 20)], [1, 2, 3])

    def test_radius_boundary(self):
        from analyse import EARTH_KM
        lat = -33 + np.degrees(5 / EARTH_KM)
        regions = pd.DataFrame({'region': ['r'], 'lat': [-33.0], 'lon': [151.0]})
        sites = pd.DataFrame({'physical_site_id': ['a'], 'operator': ['Telstra'],
                              'lat': [lat], 'lon': [151.0], 'possible_5g': [False]})
        out = count_nearby(regions, sites).iloc[0]
        self.assertEqual(out.operators_10km, 1)
        self.assertIsNone(out.possible_5g_10km)
        # Numeric equality at the radius can vary at machine precision; test
        # points 1 metre inside/outside, rather than asserting a rounded distance.
        sites.loc[0, 'lat'] = -33 + np.degrees(4.999 / EARTH_KM)
        self.assertEqual(count_nearby(regions, sites).operators_5km.iloc[0], 1)
        sites.loc[0, 'lat'] = -33 + np.degrees(5.001 / EARTH_KM)
        self.assertEqual(count_nearby(regions, sites).operators_5km.iloc[0], 0)

    def input_fixture(self, folder):
        path, manifest = folder / 'sites.csv', folder / 'manifest.json'
        pd.DataFrame([{'record_id': str(i), 'physical_site_id': 'a', 'operator': 'Telstra',
            'lat': '-33', 'lon': '151', 'mobile_status': 'confirmed',
            'active_status': 'current', 'technology': 'unknown', 'evidence': 'synthetic test'}
            for i in range(2)]).to_csv(path, index=False)
        meta = {key: 'synthetic test' for key in ('source_crs', 'coordinate_transformation',
            'raw_sha256', 'reviewer', 'operator_mapping_evidence', 'mobile_classification_evidence',
            'physical_site_review', 'completeness_limitations')}
        meta.update(snapshot_date='2026-10-26', terms_accepted_by_user=True,
            all_three_operators_reviewed=True, nsw_plus_20km_buffer_reviewed=True,
            output_crs='EPSG:4326', reviewed_csv_sha256=sha(path))
        manifest.write_text(json.dumps(meta))
        return path, manifest, meta

    def test_duplicate_licences_collapse(self):
        with tempfile.TemporaryDirectory() as folder:
            path, manifest, _ = self.input_fixture(Path(folder))
            sites, qa, _ = load_sites(path, manifest)
            self.assertEqual(len(sites), 1)
            self.assertEqual(qa['collapsed_licence_records'], 1)

    def test_terms_not_accepted_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            path, manifest, meta = self.input_fixture(Path(folder))
            meta['terms_accepted_by_user'] = False
            manifest.write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError, 'accept ACMA'):
                load_sites(path, manifest)

    def test_unreviewed_operator_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path, manifest, meta = self.input_fixture(Path(folder))
            df = pd.read_csv(path)
            df['operator'] = 'Tower owner is not a mobile operator'
            df.to_csv(path, index=False)
            meta['reviewed_csv_sha256'] = sha(path)
            manifest.write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError, 'operator'):
                load_sites(path, manifest)

    def test_conflicting_physical_coordinates_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path, manifest, meta = self.input_fixture(Path(folder))
            df = pd.read_csv(path)
            df.loc[1, 'lat'] = -34
            df.to_csv(path, index=False)
            meta['reviewed_csv_sha256'] = sha(path)
            manifest.write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError, 'inconsistent coordinates'):
                load_sites(path, manifest)

    def test_invalid_coordinates_excluded_and_audited(self):
        with tempfile.TemporaryDirectory() as folder:
            path, manifest, meta = self.input_fixture(Path(folder))
            df = pd.read_csv(path)
            df.loc[1, ['lat', 'lon']] = [151, -33]
            df.to_csv(path, index=False)
            meta['reviewed_csv_sha256'] = sha(path)
            manifest.write_text(json.dumps(meta))
            _, qa, _ = load_sites(path, manifest)
            self.assertEqual(qa['invalid_coordinates'], 1)
            self.assertEqual(qa['accepted_records'], 1)

    def test_synthetic_summary_and_figure_generation(self):
        rows = persistent(self.panel())
        rows['remoteness'] = 'Unknown'
        for r in (5, 10, 20):
            rows[f'operators_{r}km'] = 1
        summary = analyse.comparisons(rows)
        one = summary[(summary.remoteness == 'all') & (summary.quarter_index == 'all')
                      & (summary.radius_km == 10) & (summary.category == 'single-observed')].iloc[0]
        self.assertEqual(one.eligible_windows, 1)
        self.assertEqual(one.decline_frequency, 1)
        self.assertEqual(one.regions, 1)
        regions = pd.DataFrame({'lon': [151.], 'lat': [-33.],
            **{f'operators_{r}km': [1] for r in (5, 10, 20)}})
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'figures').mkdir()
            with patch.object(analyse, 'ROOT', Path(folder)):
                analyse.figures(regions, summary)
            self.assertEqual(len(list((Path(folder) / 'figures').glob('*'))), 4)


if __name__ == '__main__':
    unittest.main(verbosity=2)
