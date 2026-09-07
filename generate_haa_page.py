"""Render public and protected HAA results from the audited backtest CSVs."""
import argparse
import calendar
import html
import json
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from generate_momentum_etf2_page import table
from strategy_card import update_backtest_card, update_member_backtest_card
from strategy_chart import build_equity_drawdown_chart
from metric_style import metric_class

ROOT = Path(__file__).resolve().parent
TITLE = 'Hybrid Asset Allocation (HAA)'
STRATEGY = 'HAA net 5bp'

def read(source, name):
    return pd.read_csv(source / name, index_col=0, parse_dates=True)

def percent(x):
    return f'{float(x)*100:.2f}%'

def sharpe(equity):
    # Same convention as ETF1: daily returns, 252 sessions, zero risk-free rate.
    r=equity.pct_change().dropna()
    return float(r.mean()/r.std(ddof=1)*np.sqrt(252))

def holdings(row):
    return ', '.join(f'{ticker} {value:.0%}' for ticker,value in row.items() if value>0)

def panel(title, content, extra=''):
    return f'<section class="panel enlarged-table" {extra}><h2>{title}</h2>{content}</section>'

def monthly_table(returns):
    headers='<th>Year</th>'+''.join(f'<th>{calendar.month_abbr[m]}</th>' for m in range(1,13))+'<th>Year Return</th><th>SPY Year</th><th>60/40 Year</th>'
    rows=[]
    for year,g in returns.groupby(returns.index.year,sort=True):
        by_month=dict(zip(g.index.month,g[STRATEGY]))
        values=[by_month.get(m,np.nan) for m in range(1,13)]
        values += [float((1+g[c]).prod()-1) for c in [STRATEGY,'SPY','60 SPY 40 IEF']]
        cells=''.join('<td class="muted">—</td>' if pd.isna(v) else f'<td class="{metric_class(percent(v))}">{v*100:.1f}%</td>' for v in values)
        rows.append(f'<tr><th>{year}</th>{cells}</tr>')
    return f'<div class="table-wrap"><table><thead><tr>{headers}</tr></thead><tbody>'+''.join(reversed(rows))+'</tbody></table></div>'

def stats_table(summary):
    frame=summary[['strategy','CAGR','volatility','max_drawdown_daily','ending_10000']].copy()
    frame.columns=['Portfolio','CAGR','Annualized Volatility','Daily Max Drawdown','Final Equity ($100k)']
    frame['Final Equity ($100k)']=frame['Final Equity ($100k)'].map(lambda v:f'${v*10:,.0f}')
    return table(frame,('CAGR','Annualized Volatility','Daily Max Drawdown'))

def refresh_snapshot(source):
    import requests
    weights=read(source,'exact_etfs_targets.csv').iloc[-1]
    signal=read(source,'exact_etfs_targets.csv').index[-1]
    snapshots={}
    # Request only the existing portfolio and benchmark; never infer a fresh monthly signal.
    for ticker in set(weights[weights>0].index)|{'SPY'}:
        response=requests.get(f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}',params={'period1':int(signal.tz_localize('America/New_York').timestamp()),'period2':int(datetime.now(timezone.utc).timestamp()),'interval':'1d','events':'div'},headers={'User-Agent':'Mozilla/5.0'},timeout=40)
        response.raise_for_status()
        obj=response.json()['chart']['result'][0]
        dates=pd.to_datetime(obj['timestamp'],unit='s',utc=True).tz_convert('America/New_York').tz_localize(None).normalize()
        frame=pd.DataFrame({'close':obj['indicators']['quote'][0]['close'],'adjusted':obj['indicators']['adjclose'][0]['adjclose']},index=dates).dropna()
        # A daily close is usable only after that New York trading session ends.
        cutoff=pd.Timestamp.now(tz='America/New_York')
        if cutoff.hour<16: frame=frame.loc[frame.index<cutoff.tz_localize(None).normalize()]
        snapshots[ticker]=frame
    common=set.intersection(*(set(f.index) for f in snapshots.values()))
    latest=max(common)
    if signal not in common: raise ValueError('Missing signal-date prices in current snapshot')
    payload={'signal_date':str(signal.date()),'as_of':str(latest.date()),'prices':{ticker:{'entry_close':float(f.at[signal,'close']),'latest_close':float(f.at[latest,'close']),'total_return':float(f.at[latest,'adjusted']/f.at[signal,'adjusted']-1)} for ticker,f in snapshots.items()}}
    (source/'current_snapshot.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')

def member_sections(source,equity,returns):
    targets=read(source,'exact_etfs_targets.csv')
    signal=targets.index[-1]; weights=targets.iloc[-1]
    snapshot=json.loads((source/'current_snapshot.json').read_text())
    assert snapshot['signal_date']==str(signal.date()),'Snapshot is stale relative to final target'
    asof=pd.Timestamp(snapshot['as_of'])
    assert signal<=asof and asof.to_period('M')<=signal.to_period('M')+1,'Refresh the full monthly backtest before showing later prices'
    prices=snapshot['prices']; base=equity[STRATEGY].iloc[-1]*100000
    positions=[]
    for ticker,weight in weights.items():
        if weight<=0: continue
        q=prices[ticker]; shares=base*weight/q['entry_close']; pnl=base*weight*q['total_return']
        positions.append({'Ticker':ticker,'Target Weight':weight,'Entry Date':str(signal.date()),'Shares':f'{shares:,.2f}','Entry Price':f"${q['entry_close']:.2f}",'Current Price':f"${q['latest_close']:.2f}",'Value incl. Distributions':f'${base*weight+pnl:,.2f}','Open Total P/L':f'${pnl:,.2f}','Return':q['total_return']})
    total=sum(weights[t]*prices[t]['total_return'] for t in weights[weights>0].index)
    content=f'<p class="subtle">Snapshot through {asof:%Y-%m-%d}. {asof:%B %Y} is incomplete and is excluded from the backtest metrics and monthly table below.</p><p class="model-summary"><span>HAA: <strong class="{metric_class(percent(total))}">{percent(total)}</strong></span><span>SPY: <strong class="{metric_class(percent(prices["SPY"]["total_return"]))}">{percent(prices["SPY"]["total_return"])}</strong></span></p>'
    content+=table(pd.DataFrame(positions),('Target Weight','Return'))
    content+='<p class="subtle">Model shares use equity after the latest rebalance costs and allow fractional shares. Prices are raw closes; returns and values include reinvested distributions. Entry date is the latest monthly rebalance, not necessarily the first purchase.</p>'
    result=panel('Current Partial Month',content,'id="current-month"')
    alert=pd.DataFrame([{'Signal':str(signal.date()),'Holding':holdings(weights),'Execution':f'{signal:%Y-%m-%d} close','Applies to':str(signal.to_period('M')+1),'Changed':'Yes' if not weights.equals(targets.iloc[-2]) else 'No','Status':'Confirmed month-end model allocation'}])
    alloc={t:float(w) for t,w in weights.items() if w>0}
    alert_html=table(alert).replace('<table>',f'<table data-model-weights="{html.escape(json.dumps(alloc),quote=True)}">',1)
    result+=panel('Latest Alert','<p class="subtle">This is the allocation already in effect. No preliminary next-month signal is shown. Model execution uses the signal-day close.</p>'+alert_html)
    history=[]
    for date,row in returns.iterrows():
        prior=targets.loc[targets.index<date].iloc[-1]
        prior_date=targets.loc[targets.index<date].index[-1]
        history.append({'Month':str(date.to_period('M')),'Signal':str(prior_date.date()),'Holdings':holdings(prior),'Return':row[STRATEGY],'SPY':row['SPY']})
    history=pd.DataFrame(history).iloc[::-1]
    result+=panel('Latest 20 Historical Trades','<p class="subtle">Monthly allocation records; returns include the modeled trading costs.</p>'+table(history.head(20),('Return','SPY')))
    result+=f'<details class="panel result-options"><summary>Complete Monthly Allocation History ({len(history)} months)</summary>'+table(history,('Return','SPY'))+'</details>'
    result+='<script src="/position-calculator.js" defer></script>'
    return result

def faq(audience):
    items=[('What is HAA?','Hybrid Asset Allocation was developed by Wouter Keller and JW Keuning. It combines momentum-based ETF selection with a TIPS filter that determines whether to use growth or defensive exposure.'),('How does it allocate?','Each month, average the trailing 1, 3, 6 and 12-month total returns. Positive TIP momentum allows four 25% slots from SPY, IWM, EFA, EEM, VNQ, PDBC, IEF and TLT. Nonpositive slots move to whichever of IEF or BIL has stronger momentum. If TIP momentum is nonpositive, the entire portfolio moves to that defensive choice.'),('Why does the backtest start in December 2015?','The backtest uses actual ETF history and reserves the first 12 months of common data for momentum calculations. Reconstructed pre-ETF histories are excluded.'),('What do Sharpe and drawdown mean here?','Sharpe uses daily returns, 252 trading sessions per year and a zero risk-free rate, matching ETF1. Maximum drawdown measures the largest peak-to-trough decline using daily portfolio values.'),('When are these results updated?','The performance statistics cover complete months only. Always use the dates printed on this page. The current allocation snapshot is separately dated; automatic HAA updates and email delivery have not been enabled.')]
    if audience=='member': items.append(('How do I read the allocation and calculator?','The confirmed alert is already in effect. Target weights may combine multiple 25% defensive slots. The calculator uses these explicit weights. Current values include distribution-adjusted returns; your account, fills, fees and taxes may differ.'))
    return '<details class="faq-wrap"><summary>Strategy FAQ</summary><div class="faq-content">'+''.join(f'<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>' for q,a in items)+'</div></details>'

def render(source,audience):
    equity=read(source,'exact_etfs_daily_equity.csv')
    returns=read(source,'exact_etfs_monthly_returns.csv')
    summary=pd.read_csv(source/'summary.csv')
    exact=summary[summary['sample']=='exact_etfs']; main=exact.set_index('strategy').loc[STRATEGY]; spy=exact.set_index('strategy').loc['SPY']
    start=returns.index[0]; end=returns.index[-1]
    metrics=[('Strategy CAGR',percent(main.CAGR)),('SPY CAGR',percent(spy.CAGR)),('Strategy Max Drawdown',percent(main.max_drawdown_daily)),('SPY Max Drawdown',percent(spy.max_drawdown_daily)),('Total Return',percent(equity[STRATEGY].iloc[-1]-1)),('Sharpe Ratio',f'{sharpe(equity[STRATEGY]):.2f}'),('Final Equity',f'${equity[STRATEGY].iloc[-1]*100000:,.0f}'),('Active Months',str(len(returns)))]
    cards=''.join(f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value {metric_class(value)}">{value}</div></div>' for label,value in metrics)
    chart=build_equity_drawdown_chart(equity.index,equity[STRATEGY]*100000,equity['SPY']*100000,'HAA','haa-equity-chart')
    primary=panel('Equity Curve',f'<p class="subtle">HAA and SPY, starting with $100,000. Daily equity and drawdowns through {end:%Y-%m-%d}.</p><div class="chart">{chart}</div>')
    primary+=panel('Monthly Returns','<p class="subtle">Net returns. Annual columns compound only the months shown; 2015 and 2026 are partial years. 60/40 means monthly rebalanced SPY/IEF.</p>'+monthly_table(returns))
    primary+=panel('Portfolio Comparison',stats_table(exact[exact.strategy.isin([STRATEGY,'SPY','60 SPY 40 IEF'])]))
    primary+='<details class="panel result-options"><summary>Trading Costs and Execution Timing</summary><p class="subtle">Costs are per dollar bought or sold. A full switch between assets incurs both sides. Next-close execution waits one trading day after the completed signal.</p>'+stats_table(exact[~exact.strategy.isin(['SPY','60 SPY 40 IEF'])])+'</details>'
    post=pd.read_csv(source/'post_publication.csv',index_col=0).reset_index(names='strategy')
    primary+=panel('After Publication: April 2023–August 2026','<p class="subtle">First full month after the public article; a historical check, not recorded live performance. Each portfolio is rebased to $100,000.</p>'+stats_table(post[post.strategy.isin([STRATEGY,'SPY','60 SPY 40 IEF'])]))
    ext=read(source,'extended_dbc_proxy_daily_equity.csv'); ext_returns=read(source,'extended_dbc_proxy_monthly_returns.csv')
    ext_chart=build_equity_drawdown_chart(ext.index,ext[STRATEGY]*100000,ext['SPY']*100000,'HAA (DBC proxy)','haa-dbc-chart')
    primary+='<details class="panel result-options"><summary>Longer History: DBC Proxy, June 2008–August 2026</summary><p class="subtle">DBC replaces PDBC throughout this separate test. It is a different commodity implementation; these results are not spliced into the main history.</p>'+stats_table(summary[summary['sample']=='extended_dbc_proxy'])+f'<div class="chart">{ext_chart}</div>'+monthly_table(ext_returns)+'</details>'
    method='<p class="result-note">Hypothetical backtest using Yahoo Finance dividend/split-adjusted ETF closes, with dividends reinvested, no leverage and no taxes. The main result uses 0.05% per dollar bought or sold, monthly rebalancing from drifted weights and BIL as the cash proxy. ETF expenses are embedded in prices. Signals and fills at the same month-end close are idealized; the next-close sensitivity is shown above. Annualized volatility is calculated from monthly returns. The first 12 months of common ETF history are reserved for momentum. Initial allocation: November 30, 2015.</p><p class="result-note">Reconstructed pre-ETF histories are excluded. Results depend on vendor adjustments and have not been cross-validated with a second vendor. This is our implementation of the <a href="https://allocatesmartly.com/hybrid-asset-allocation/">published HAA rules</a>, including the corrected defensive fallback, not a replication of Allocate Smartly’s proprietary data.</p>'
    primary+=panel('Methodology',method)
    member=member_sections(source,equity,returns) if audience=='member' else ''
    cta=panel('Member Signals','<p class="subtle">Members can view the dated allocation snapshot, confirmed monthly alert, position calculator and complete allocation history.</p><p><a href="members.html?strategy=haa">Sign in to view HAA</a> · <a href="subscribe.html">View membership options</a></p>') if audience=='public' else ''
    robots='<meta name="robots" content="noindex,nofollow">' if audience=='member' else '<link rel="canonical" href="https://www.extremetradinginc.com/haa.html">'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{robots}<title>HAA Backtest - Extreme Trading Inc.</title><meta name="description" content="Hybrid Asset Allocation backtest, SPY comparison, monthly returns and execution sensitivities."><link rel="stylesheet" href="haa.css"><script src="/site-auth-nav.js?v=5"></script></head><body><nav><div><strong>Extreme Trading Inc.</strong></div><div><a href="index.html">Home</a><a href="strategies.html">Strategies</a><a href="subscribe.html">Subscribe</a><a href="members.html">Login</a><a href="about.html">About</a><a href="contact.html">Contact</a></div></nav><main class="container"><section class="hero"><div class="eyebrow">Backtested monthly ETF allocation model</div><h1>{TITLE}</h1><p>Monthly rotation across stocks, real estate, commodities and Treasuries, using TIPS momentum to select growth or defensive exposure.</p><p class="subtle">Complete holding months: {start:%B %Y} through {end:%B %Y} · Starting equity: $100,000 · Net of modeled trading costs</p>{faq(audience)}</section><section class="metrics">{cards}</section>{member}{primary}{cta}<script>document.querySelectorAll("details.result-options").forEach(el=>el.addEventListener("toggle",()=>{{if(el.open)requestAnimationFrame(()=>el.querySelectorAll(".js-plotly-plot").forEach(chart=>window.Plotly?.Plots.resize(chart)));}}));</script><section class="panel disclaimer"><strong>Important:</strong> Hypothetical backtest results, not verified live performance or personalized advice. Past or simulated performance does not guarantee future results. <a href="risk-disclosure.html">Risk Disclosure</a> · <a href="hypothetical-performance.html">Hypothetical Performance Disclosure</a></section></main><footer>&copy; 2026 Extreme Trading Inc.</footer></body></html>'''

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'data'/'haa')
    parser.add_argument('--refresh-snapshot',action='store_true')
    args=parser.parse_args()
    if args.refresh_snapshot: refresh_snapshot(args.source)
    for audience,path in [('public',ROOT/'haa.html'),('member',ROOT/'api'/'_member-content'/'haa.html')]:
        page=render(args.source,audience)
        if audience=='public':
            assert 'data-model-weights' not in page and 'id="current-month"' not in page
        path.write_text(page,encoding='utf-8')
    summary=pd.read_csv(args.source/'summary.csv'); s=summary[summary['sample']=='exact_etfs'].set_index('strategy')
    eq=read(args.source,'exact_etfs_daily_equity.csv')
    values=(s.at[STRATEGY,'CAGR'],sharpe(eq[STRATEGY]),s.at[STRATEGY,'max_drawdown_daily'],s.at['SPY','max_drawdown_daily'])
    update_backtest_card(ROOT/'strategies.html',TITLE,*values)
    update_member_backtest_card(ROOT/'members.html',TITLE,*values)
    print('Generated HAA public/member results and synchronized cards:',values)

if __name__=='__main__': main()
