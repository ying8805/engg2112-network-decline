"""Classification/privacy edge cases with fictional records only."""
import unittest
import pandas as pd
from prepare_acma import map_operator, classify


class ClassificationTests(unittest.TestCase):
    def test_exact_company_identity_and_natural_person_exclusion(self):
        frame=pd.DataFrame({'LICENCEE':['TELSTRA LIMITED','TELSTRA LIMITED','TELSTRA BROADCAST SERVICES PTY LIMITED','MOBILE JV PTY LIMITED',' OPTUS  MOBILE PTY LIMITED '],
                            'CLIENT_TYPE_ID':['5','7','5','5','5']})
        result=map_operator(frame)
        self.assertEqual(result.iloc[0],'Telstra')
        self.assertTrue(result.iloc[1:4].isna().all())
        self.assertEqual(result.iloc[4],'Optus')

    def test_explicit_mobile_vs_private_radio_and_microwave(self):
        frame=pd.DataFrame({'lic_SV_ID':['10','3','2'],'lic_SS_ID':['125','304','203'],
            'SV_ID':['10','3','2'],'SS_ID':['125','304','203'],
            'CLASS_OF_STATION_CODE':['FB','FB','FX'],'FREQUENCY':['885000000','450000000','6000000000']})
        self.assertEqual(list(classify(frame)),['explicit_pmts','excluded','excluded'])

    def test_inferred_spectrum_has_no_technology_claim(self):
        frame=pd.DataFrame({'lic_SV_ID':['85']*3,'lic_SS_ID':['870']*3,
            'SV_ID':['85']*3,'SS_ID':['870']*3,'CLASS_OF_STATION_CODE':['']*3,
            'FREQUENCY':['778000000','723000000','700000']})
        self.assertEqual(list(classify(frame)),['spectrum_inferred','excluded','excluded'])

    def test_service_identifier_mismatch_excluded(self):
        frame=pd.DataFrame({'lic_SV_ID':['85'],'lic_SS_ID':['870'],'SV_ID':['85'],
            'SS_ID':['850'],'CLASS_OF_STATION_CODE':[''],'FREQUENCY':['778000000']})
        self.assertEqual(list(classify(frame)),['excluded'])


if __name__=='__main__': unittest.main(verbosity=2)
