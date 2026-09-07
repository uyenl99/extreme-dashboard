"""Refresh HAA from completed NYSE sessions before the shared batch publishes."""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pandas_market_calendars as mcal

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generate_haa_page import refresh_snapshot, render, main as generate_pages


def completed_dates(as_of=None):
    now=pd.Timestamp(as_of) if as_of is not None else pd.Timestamp.now(tz='America/New_York')
    if now.tzinfo is None: raise ValueError('as_of must include a timezone')
    now=now.tz_convert('America/New_York')
    schedule=mcal.get_calendar('NYSE').schedule(start_date=(now-pd.Timedelta(days=70)).date(),end_date=(now+pd.Timedelta(days=40)).date())
    closed=schedule.loc[schedule.market_close<=now]
    if closed.empty: raise ValueError('No completed trading session')
    month_ends=schedule.groupby(schedule.index.to_period('M')).tail(1)
    complete=month_ends.loc[month_ends.market_close<=now]
    last_complete=complete.index[-1]
    exclusive=(last_complete.to_period('M')+1).start_time
    return now,closed.index[-1],last_complete,exclusive


def run(as_of=None,work_dir=None):
    now,latest,month_end,exclusive=completed_dates(as_of)
    print(f'HAA: latest completed session {latest.date()}, full-month endpoint {month_end.date()}',flush=True)
    if work_dir is not None: work_dir.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='haa-refresh-',dir=work_dir) as temporary:
        stage=Path(temporary)
        subprocess.run([sys.executable,str(ROOT/'research/haa_backtest.py'),'--refresh','--skip-chart','--end',str(exclusive.date()),'--output-root',str(stage)],check=True)
        source=stage/'results'
        for sample in ['exact_etfs','extended_dbc_proxy']:
            equity=pd.read_csv(source/f'{sample}_daily_equity.csv',index_col=0,parse_dates=True)
            targets=pd.read_csv(source/f'{sample}_targets.csv',index_col=0,parse_dates=True)
            if equity.index[-1]!=month_end or targets.index[-1]!=month_end:
                raise ValueError(f'{sample}: missing prices at the expected complete-month endpoint {month_end.date()}')
        refresh_snapshot(source,expected_session=latest,as_of=now)
        # Render before replacing tracked files so missing/misaligned inputs stop the stage.
        for audience in ['public','member']: render(source,audience)
        info={'latest_session':str(latest.date()),'complete_month_end':str(month_end.date()),'exclusive_cutoff':str(exclusive.date()),'calendar':'NYSE','execution':'month-end close','cost_per_traded_dollar':0.0005}
        (source/'refresh_info.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
        destination=ROOT/'data/haa'
        destination.mkdir(parents=True,exist_ok=True)
        for file in source.iterdir():
            if file.suffix not in {'.csv','.json'}: continue
            pending=destination/(file.name+'.tmp')
            shutil.copyfile(file,pending)
            pending.replace(destination/file.name)
    original=sys.argv
    try:
        sys.argv=['generate_haa_page.py']
        generate_pages()
    finally: sys.argv=original
    subprocess.run([sys.executable,str(ROOT/'scripts/verify_haa_page.py')],check=True)
    print('HAA refresh verified; publication remains controlled by the shared batch.',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of',help='Timezone-aware timestamp for reproducible checks; defaults to now')
    parser.add_argument('--work-dir',type=Path,help='Parent directory for temporary download/calculation files')
    args=parser.parse_args()
    run(args.as_of,args.work_dir)
