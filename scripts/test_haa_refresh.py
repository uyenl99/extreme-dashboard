"""Calendar boundaries and stale-data safeguards for unattended HAA refreshes."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from refresh_haa import completed_dates
from generate_haa_page import refresh_snapshot, member_sections, read

class RefreshChecks(unittest.TestCase):
    def test_completed_sessions(self):
        cases=[
            ('2026-09-06T18:00:00-04:00','2026-09-04','2026-08-31','2026-09-01'),
            ('2026-09-07T18:00:00-04:00','2026-09-04','2026-08-31','2026-09-01'),
            ('2026-09-30T15:59:00-04:00','2026-09-29','2026-08-31','2026-09-01'),
            ('2026-09-30T16:05:00-04:00','2026-09-30','2026-09-30','2026-10-01'),
            ('2026-07-31T16:05:00-04:00','2026-07-31','2026-07-31','2026-08-01'),
            ('2025-11-28T12:59:00-05:00','2025-11-26','2025-10-31','2025-11-01'),
            ('2025-11-28T13:05:00-05:00','2025-11-28','2025-11-28','2025-12-01'),
        ]
        for now,latest,month,end in cases:
            with self.subTest(now=now):
                _,a,b,c=completed_dates(now)
                self.assertEqual(tuple(str(x.date()) for x in [a,b,c]),(latest,month,end))

    def test_stale_snapshot_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)
            pd.DataFrame({'SGOV':[1.]},index=pd.to_datetime(['2026-08-31'])).to_csv(source/'exact_etfs_targets.csv')
            (source/'exact_etfs_closing_state.json').write_text(json.dumps({'date':'2026-08-31','weights':{'SGOV':1.}}))
            class Response:
                def raise_for_status(self): pass
                def json(self):
                    times=[int(pd.Timestamp(t,tz='America/New_York').timestamp()) for t in ['2026-08-31 16:00','2026-09-03 16:00']]
                    return {'chart':{'result':[{'timestamp':times,'indicators':{'quote':[{'open':[100,101],'close':[100,101]}],'adjclose':[{'adjclose':[100,101]}]}}]}}
            with patch('requests.get',return_value=Response()):
                with self.assertRaisesRegex(ValueError,'Stale snapshot'):
                    refresh_snapshot(source,pd.Timestamp('2026-09-04'),'2026-09-06T18:00:00-04:00')
            self.assertFalse((source/'current_snapshot.json').exists())

    def test_snapshot_weekend_pending_and_open_execution(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)
            pd.DataFrame({'SGOV':[1.],'IEF':[0.]},index=pd.to_datetime(['2026-07-31'])).to_csv(source/'exact_etfs_targets.csv')
            (source/'exact_etfs_closing_state.json').write_text(json.dumps({'date':'2026-07-31','weights':{'SGOV':0.,'IEF':1.}}))
            class Response:
                def __init__(self,ticker): self.ticker=ticker
                def raise_for_status(self): pass
                def json(self):
                    times=[int(pd.Timestamp(t,tz='America/New_York').timestamp()) for t in ['2026-07-31 16:00','2026-08-03 16:00']]
                    op=[100.,110.] if self.ticker=='IEF' else [100.,100.]
                    cl=[100.,111.] if self.ticker=='IEF' else [100.,102.]
                    return {'chart':{'result':[{'timestamp':times,'indicators':{'quote':[{'open':op,'close':cl}],'adjclose':[{'adjclose':cl}]}}]}}
            with patch('requests.get',side_effect=lambda url,**kw:Response(url.rsplit('/',1)[-1])):
                refresh_snapshot(source,pd.Timestamp('2026-07-31'),'2026-08-01T12:00:00-04:00')
                pending=json.loads((source/'current_snapshot.json').read_text())
                self.assertTrue(pending['pending']);self.assertEqual(pending['execution_date'],'2026-08-03')
                self.assertIsNone(pending['prices']['SGOV']['entry_open'])
                self.assertEqual(pending['portfolio_return'],0.)
                refresh_snapshot(source,pd.Timestamp('2026-08-03'),'2026-08-03T16:05:00-04:00')
                active=json.loads((source/'current_snapshot.json').read_text())
                self.assertFalse(active['pending']);self.assertEqual(active['prices']['SGOV']['entry_open'],100.)
                self.assertAlmostEqual(active['entry_equity_factor'],1.1*.999)
                self.assertAlmostEqual(active['portfolio_return'],1.1*.999*1.02-1)

    def test_month_end_snapshot_is_new_allocation(self):
        source=ROOT/'data/haa'
        equity=read(source,'exact_etfs_daily_equity.csv'); returns=read(source,'exact_etfs_monthly_returns.csv')
        snapshot=json.loads((source/'current_snapshot.json').read_text())
        snapshot['as_of']=snapshot['signal_date']
        snapshot['pending']=True
        for values in snapshot['prices'].values(): values['total_return']=0
        original=Path.read_text
        def fake_read(path,*args,**kwargs):
            return json.dumps(snapshot) if path.name=='current_snapshot.json' else original(path,*args,**kwargs)
        with patch.object(Path,'read_text',fake_read):
            page=member_sections(source,equity,returns)
        self.assertIn('No holding-period return has accrued',page)
        self.assertNotIn('is incomplete and is excluded',page)

class OpeningChecks(unittest.TestCase):
    def test_overnight_and_costs(self):
        import numpy as np
        from research.haa_backtest import simulate_open
        dates=pd.to_datetime(['2024-01-31','2024-02-01','2024-02-02'])
        close=pd.DataFrame({'A':[100.,121.,200.],'B':[100.,100.,55.]},index=dates)
        opens=pd.DataFrame({'A':[100.,110.,133.1],'B':[100.,100.,50.]},index=dates)
        a=pd.Series({'A':1.,'B':0.});b=pd.Series({'A':0.,'B':1.})
        eq,trades=simulate_open(close,opens,{dates[0]:a,dates[1]:b},0)
        self.assertTrue(np.allclose(eq,[1,1.1,1.331]))
        self.assertEqual(list(trades.date),['2024-02-01','2024-02-02'])
        eq,_=simulate_open(close,opens,{dates[0]:a,dates[1]:b},.0005)
        self.assertAlmostEqual(eq.iloc[-1],1.331*(1-.0005)*(1-.001))
        # A pending signal must not change the closing portfolio.
        eq,trades=simulate_open(close.iloc[:1],opens.iloc[:1],{dates[0]:b},.0005,a)
        self.assertTrue(trades.empty);self.assertEqual(eq.attrs['weights'],a.to_dict())
        # Replaying a partial month preserves the old allocation's overnight gap.
        eq,_=simulate_open(close.iloc[:2],opens.iloc[:2],{dates[0]:b},.0005,a)
        self.assertAlmostEqual(eq.iloc[-1],1.1*(1-.001))

    def test_bil_history_link_and_switch(self):
        import numpy as np
        from research.haa_backtest import cash_history, simulate_open, targets
        dates=pd.to_datetime(['2020-05-28','2020-05-29','2020-06-01','2020-06-02'])
        raw=pd.DataFrame({'BIL':[99.,100.,101.,102.],'SGOV':[np.nan,np.nan,200.,202.]},index=dates)
        prices,opens,linked,first=cash_history(raw,raw)
        self.assertEqual(first,dates[2])
        self.assertTrue(np.allclose(linked,[99.,100.,101.,102.01]))
        # Price levels differ by 2x; linking must not invent a 100% gain.
        self.assertAlmostEqual(linked.iloc[2]/linked.iloc[1]-1,.01)
        self.assertEqual(prices.iloc[0].SGOV,1.)
        a=pd.Series({'BIL':1.,'SGOV':0.});b=pd.Series({'BIL':0.,'SGOV':1.})
        eq,trades=simulate_open(prices,opens,{dates[0]:a,dates[2]:b},.0005)
        self.assertAlmostEqual(eq.iloc[-1],1.02*(1-.0005)*(1-.001))
        self.assertEqual(trades.iloc[1].date,'2020-06-02')
        self.assertAlmostEqual(trades.iloc[1].traded_notional,2.)
        bad=raw.copy();bad.loc[dates[-1],'SGOV']=np.nan
        with self.assertRaisesRegex(ValueError,'Missing SGOV'):
            cash_history(bad,raw)
        row=pd.Series({'SPY':.2,'IEF':.02,'SGOV':.04,'BIL':.03,'TIP':-.01})
        self.assertEqual(targets(row,['SPY'],'BIL')['BIL'],1.)
        self.assertEqual(targets(row,['SPY'],'SGOV')['SGOV'],1.)

    def test_sgov_defensive_signal(self):
        from research.haa_backtest import targets
        row=pd.Series({'SPY':.2,'IEF':.02,'SGOV':.04,'TIP':-.01})
        self.assertEqual(targets(row,['SPY'])['SGOV'],1.)
        row['SGOV']=.01
        self.assertEqual(targets(row,['SPY'])['IEF'],1.)

if __name__=='__main__': unittest.main()
