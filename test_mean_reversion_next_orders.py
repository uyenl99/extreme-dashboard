import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from mean_reversion_next_orders import latest_signal, select_orders, session_dates, render_orders


class NextOrdersTests(unittest.TestCase):
    def test_calendar_weekend_holiday_and_preclose(self):
        self.assertEqual(tuple(str(d.date()) for d in session_dates("2026-09-04T17:00:00-04:00")), ("2026-09-04", "2026-09-08"))
        self.assertEqual(tuple(str(d.date()) for d in session_dates("2026-09-08T15:00:00-04:00")), ("2026-09-04", "2026-09-08"))
        self.assertEqual(tuple(str(d.date()) for d in session_dates("2026-09-08T17:00:00-04:00")), ("2026-09-08", "2026-09-09"))

    def test_exits_free_slots_and_rank_entries(self):
        day = pd.DataFrame([
            dict(ticker=t, close=100., qpi=q, ibs=.05, entry_signal=e, exit_signal=x)
            for t,q,e,x in [('A',.1,False,True),('B',.1,True,False),('C',.1,False,False),('D',.1,False,False),('E',.1,False,False),('F',.2,True,False),('G',.1,True,False)]
        ]).set_index('ticker')
        positions = pd.DataFrame([dict(ticker=t,side='long',entry_date='2026-09-01',shares=20.) for t in 'ABCDE'])
        orders = select_orders(day, positions, 0., pd.Timestamp('2026-09-09'))
        self.assertEqual([(o['action'],o['ticker']) for o in orders], [('Exit','A'),('Buy','G')])
        self.assertLessEqual(orders[1]['estimated_notional']*1.0005, 2000*.9995+1e-8)
        day.loc['A','exit_signal'] = False
        self.assertEqual(select_orders(day, positions, 0., pd.Timestamp('2026-09-09')), [])
        with self.assertRaises(ValueError):
            select_orders(day.drop('A'), positions, 0., pd.Timestamp('2026-09-09'))

    def test_stale_orders_and_no_future_fills(self):
        payload = dict(signal_date='2026-09-08',execution_date='2026-09-09',orders=[])
        self.assertIn('No orders for this session', render_orders(payload, pd.Timestamp('2026-09-08')))
        with self.assertRaises(ValueError):
            render_orders(payload,pd.Timestamp('2026-09-09'))

    def test_latest_formulas_match_production_engine(self):
        sys.path.insert(0, 'C:/junk/stocks/RevMurphy')
        import config
        from signals import prepare_ticker_frame
        cfg = SimpleNamespace(**{k:v for k,v in vars(config).items() if k.isupper()})
        rng = np.random.default_rng(71)
        close = 100*np.exp(np.cumsum(rng.normal(0,.015,820)))
        bars = pd.DataFrame(dict(date=pd.bdate_range('2020-01-01',periods=820),close=close,high=close*1.01,low=close*.985,volume=rng.integers(1000,10000,820)))
        expected = prepare_ticker_frame('TEST',bars).iloc[-1]
        actual = latest_signal(bars,cfg)
        for column in ('qpi','ibs','rsi2','close'):
            self.assertAlmostEqual(actual[column],expected[column],places=12)
        for column in ('entry_signal','exit_signal'):
            self.assertEqual(actual[column],expected[column])


if __name__ == '__main__':
    unittest.main()
