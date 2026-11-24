import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from compute_real_portfolio import project, comparisons


class RealPortfolioTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {'as_of_date':'2026-11-21', 'total_eur':1000., 'holdings':[
            {'asset_id':'euro','value_eur':700.},
            {'asset_id':'a','value_eur':200.,'reference_price':100.,'price_date':'2026-11-20'},
            {'asset_id':'b','value_eur':100.,'reference_price':50.,'price_date':'2026-11-19'}]}
        self.prices = pd.DataFrame([
            ('2026-11-20','a',100.),('2026-11-23','a',110.),('2026-11-24','a',100.),
            ('2026-11-24','b',55.)],columns=['date','asset_id','close_eur'])

    def test_observation_and_buy_hold_no_double_compounding(self):
        rows = project(self.snapshot,self.prices)
        self.assertEqual([r['value_eur'] for r in rows],[1000.,1020.,1010.])
        self.assertEqual([r['index'] for r in rows],[100.,102.,101.])
        self.assertEqual(rows[0]['status'],'observed')

    def test_future_price_never_used_to_fill_missing_past(self):
        rows = project(self.snapshot,self.prices)
        self.assertEqual(rows[1]['pending_supports'],[{'asset_id':'b','price_date':'2026-11-19'}])

    def test_bad_total_rejected(self):
        self.snapshot['total_eur']=999.
        with self.assertRaises(ValueError): project(self.snapshot,self.prices)

    def test_comparisons_use_pre_observation_anchor_not_future(self):
        rows=project(self.snapshot,self.prices)
        dates, curves=comparisons(self.snapshot,rows,[{'dates':['2026-11-20','2026-11-23'],
            'series':[{'label':'theory','values':[80.,88.]}]}])
        self.assertEqual(dates,['2026-11-21','2026-11-23','2026-11-24'])
        self.assertEqual(curves[1]['values'],[100.,110.,None])


if __name__ == '__main__': unittest.main()
