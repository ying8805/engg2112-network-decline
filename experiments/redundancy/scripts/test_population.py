"""Projection and aggregation tests using public reference points/fictional grids."""
import unittest
import numpy as np
import pandas as pd
from population_comparison import albers_forward,albers_inverse,tile_code,summarize,in_geometry


class PopulationTests(unittest.TestCase):
    def test_independent_epsg_projection_reference(self):
        # Ordinary public locations, checked using Esri GeometryServer 26 Oct 2026.
        lon=np.array([151.2093,147.36,141.45]);lat=np.array([-33.8688,-35.11,-31.95])
        x,y=albers_forward(lon,lat)
        np.testing.assert_allclose(x,[1760981.5285978904,1393438.9185140603,884636.0409526736],atol=.001,rtol=0)
        np.testing.assert_allclose(y,[-3828749.389752656,-3918222.8992860466,-3514470.73878018],atol=.001,rtol=0)
        lo,la=albers_inverse(x,y)
        np.testing.assert_allclose(lo,lon,atol=1e-9,rtol=0)
        np.testing.assert_allclose(la,lat,atol=1e-9,rtol=0)

    def test_tile_assignment_independent_of_pandas_index(self):
        a=tile_code(pd.Series([151.,149.],index=[9,3]),pd.Series([-33.,-31.],index=[9,3]))
        b=tile_code(np.array([151.,149.]),np.array([-33.,-31.]))
        np.testing.assert_array_equal(a,b)
        self.assertIsInstance(a,np.ndarray)

    def test_missing_is_not_zero_and_groups_do_not_repeat_population(self):
        frame=pd.DataFrame({'population_estimate':[12.,0.,np.nan],
            'valid_population_cells':[1,1,0],'expected_population_cells':[1,1,1],
            'median_download_mbps':[5.,15.,25.]})
        for r in (5,10,20):
            frame[f'operators_{r}km']=[0,1,2]
            frame[f'explicit_pmts_only_operators_{r}km']=[0,0,2]
        result=summarize(frame)
        primary=result.query('definition=="broader" and radius_km==10').set_index('operators')
        self.assertEqual(primary.loc[0,'modelled_population_sum'],12)
        self.assertEqual(primary.loc[1,'modelled_population_sum'],0)
        self.assertTrue(np.isnan(primary.loc[2,'modelled_population_sum']))
        self.assertEqual(primary.modelled_population_sum.sum(),12)
        self.assertEqual(primary.grids.sum(),3)

    def test_polygon_holes_and_multipolygon_union(self):
        g={'type':'MultiPolygon','coordinates':[
            [[[0,0],[4,0],[4,4],[0,4],[0,0]],[[1,1],[2,1],[2,2],[1,2],[1,1]]],
            [[[5,0],[6,0],[6,1],[5,1],[5,0]]]]}
        np.testing.assert_array_equal(in_geometry(np.array([.5,1.5,5.5,8]),np.array([.5,1.5,.5,8]),g),[True,False,True,False])


if __name__=='__main__':unittest.main(verbosity=2)
