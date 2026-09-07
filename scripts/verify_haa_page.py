"""Validate HAA data reconciliation and public/member presentation boundaries."""
from pathlib import Path
from html.parser import HTMLParser
import json, sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generate_haa_page import render, sharpe
class Tables(HTMLParser):
    def __init__(self): super().__init__(); self.tables=[]; self.active=None; self.row=None; self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='table': self.active=[]
        elif tag=='tr' and self.active is not None: self.row=[]
        elif tag in ('td','th') and self.row is not None: self.cell=''
    def handle_data(self,data):
        if self.cell is not None: self.cell+=data
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None: self.row.append(self.cell); self.cell=None
        elif tag=='tr' and self.row is not None: self.active.append(self.row); self.row=None
        elif tag=='table' and self.active is not None: self.tables.append(self.active); self.active=None
source=ROOT/'data/haa'
public=(ROOT/'haa.html').read_text(encoding='utf-8'); member=(ROOT/'api/_member-content/haa.html').read_text(encoding='utf-8')
assert public==render(source,'public') and member==render(source,'member'),'Committed pages differ from generator'
for marker in ['id="current-month"','data-model-weights','<h2>Latest Alert</h2>','<h2>Latest 20 Historical Trades</h2>']:
    assert marker not in public and marker in member
for marker in ['haa-equity-chart','haa-dbc-chart','Strategy FAQ','Trading Costs and Execution Timing','After Publication']:
    assert marker in public and marker in member
p=Tables(); p.feed(public)
monthly=next(t for t in p.tables if t[0][:2]==['Year','Jan'])
r=pd.read_csv(source/'exact_etfs_monthly_returns.csv',index_col=0,parse_dates=True)
actual={int(row[0]):row for row in monthly[1:]}
for date,row in r.iterrows(): assert actual[date.year][date.month]==f'{row["HAA net 5bp"]*100:.1f}%'
assert sum(cell!='—' for row in monthly[1:] for cell in row[1:13])==len(r)
for year,g in r.groupby(r.index.year): assert actual[year][13]==f'{((1+g["HAA net 5bp"]).prod()-1)*100:.1f}%'
eq=pd.read_csv(source/'exact_etfs_daily_equity.csv',index_col=0)
assert np.allclose((1+r).prod(),eq.iloc[-1])
assert f'{sharpe(eq["HAA net 5bp"]):.2f} Sharpe Ratio' in (ROOT/'strategies.html').read_text()
for filename in ['strategies.html','members.html']:
    s=(ROOT/filename).read_text(encoding='utf-8'); assert s.count('<h2>Hybrid Asset Allocation (HAA)</h2>')==1
    expected_cagr=(float(eq['HAA net 5bp'].iloc[-1])**(12/len(r))-1)*100
    assert f'{expected_cagr:.1f}% Backtest CAGR' in s
m=Tables(); m.feed(member)
history=next(t for t in m.tables if t[0][:2]==['Month','Signal'])
targets=pd.read_csv(source/'exact_etfs_targets.csv',index_col=0,parse_dates=True)
for row in history[1:]:
    date=pd.Period(row[0]).to_timestamp('M'); prior=targets.loc[targets.index<date].index[-1]
    assert row[1]==str(prior.date())
assert len(history)==21
snapshot=json.loads((source/'current_snapshot.json').read_text())
assert snapshot['signal_date']==str(targets.index[-1].date())
assert pd.Timestamp(snapshot['as_of'])>=targets.index[-1]
assert snapshot['as_of'] in member
if (source/'refresh_info.json').exists():
    info=json.loads((source/'refresh_info.json').read_text())
    assert info['latest_session']==snapshot['as_of']
    assert pd.Timestamp(info['complete_month_end'])==pd.Timestamp(eq.index[-1])==targets.index[-1]
for filename in ['haa.html','api/_member-content/haa.html','position-calculator.js']:
    s=(ROOT/filename).read_text(encoding='utf-8'); assert '\u00e2\u20ac' not in s
print(f'PASS: card metrics, {len(r)} monthly returns, annual compounding, charts, allocation dates, snapshot, and public/member boundaries')
