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
            pd.DataFrame({'BIL':[1.]},index=pd.to_datetime(['2026-08-31'])).to_csv(source/'exact_etfs_targets.csv')
            class Response:
                def raise_for_status(self): pass
                def json(self):
                    times=[int(pd.Timestamp(t,tz='America/New_York').timestamp()) for t in ['2026-08-31 16:00','2026-09-03 16:00']]
                    return {'chart':{'result':[{'timestamp':times,'indicators':{'quote':[{'close':[100,101]}],'adjclose':[{'adjclose':[100,101]}]}}]}}
            with patch('requests.get',return_value=Response()):
                with self.assertRaisesRegex(ValueError,'Stale snapshot'):
                    refresh_snapshot(source,pd.Timestamp('2026-09-04'),'2026-09-06T18:00:00-04:00')
            self.assertFalse((source/'current_snapshot.json').exists())

    def test_month_end_snapshot_is_new_allocation(self):
        source=ROOT/'data/haa'
        equity=read(source,'exact_etfs_daily_equity.csv'); returns=read(source,'exact_etfs_monthly_returns.csv')
        snapshot=json.loads((source/'current_snapshot.json').read_text())
        snapshot['as_of']=snapshot['signal_date']
        for values in snapshot['prices'].values(): values['total_return']=0
        original=Path.read_text
        def fake_read(path,*args,**kwargs):
            return json.dumps(snapshot) if path.name=='current_snapshot.json' else original(path,*args,**kwargs)
        with patch.object(Path,'read_text',fake_read):
            page=member_sections(source,equity,returns)
        self.assertIn('No holding-period return has accrued',page)
        self.assertNotIn('is incomplete and is excluded',page)

if __name__=='__main__': unittest.main()
