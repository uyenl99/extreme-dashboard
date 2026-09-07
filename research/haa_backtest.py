"""HAA: actual ETF adjusted-close backtest. Run with Python + pandas/numpy/requests/matplotlib."""
from pathlib import Path
import json, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent / 'haa_run'
ROOT.mkdir(exist_ok=True)
DATA = ROOT / 'data'
OUT = ROOT / 'results'
DATA.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
TICKERS = ['SPY','IWM','EFA','EEM','VNQ','PDBC','IEF','TLT','TIP','BIL','DBC']
END = pd.Timestamp('2026-09-01')  # exclude the unfinished September month

def download(ticker):
    path = DATA / f'{ticker}.json'
    if path.exists():
        obj = json.loads(path.read_text())
    else:
        for attempt in range(3):
            try:
                response = requests.get(f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}',
                    params={'period1':0,'period2':int(END.timestamp()),'interval':'1d'}, headers={'User-Agent':'Mozilla/5.0'}, timeout=45)
                response.raise_for_status()
                obj = response.json()['chart']['result'][0]
                path.write_text(json.dumps(obj))
                break
            except Exception:
                if attempt == 2: raise
                time.sleep(2)
    dates = pd.to_datetime(obj['timestamp'], unit='s', utc=True).tz_convert('America/New_York').tz_localize(None).normalize()
    s = pd.Series(obj['indicators']['adjclose'][0]['adjclose'], index=dates, name=ticker).dropna()
    s = s[~s.index.duplicated(keep='last')]
    print(ticker, s.index.min().date(), s.index.max().date(), len(s), flush=True)
    return s[s.index < END]

def targets(momentum, offensive):
    w = pd.Series(0., index=momentum.index)
    safe = 'IEF' if momentum['IEF'] > momentum['BIL'] else 'BIL'
    if momentum['TIP'] <= 0:
        w[safe] = 1.
    else:
        picks = momentum[offensive].sort_values(ascending=False, kind='stable').head(4)
        for ticker, value in picks.items():
            w[ticker if value > 0 else safe] += .25
    assert abs(w.sum()-1) < 1e-10 and (w >= 0).all()
    return w

def simulate(prices, schedule, cost):
    """Cost is per dollar bought OR sold. Weights drift daily; trade after day's return."""
    start = min(schedule)
    p = prices.loc[start:]
    w = pd.Series(0., index=p.columns)
    wealth = 1.
    values = {start: 1.}
    logs = []
    for i, date in enumerate(p.index):
        if i:
            r = p.iloc[i]/p.iloc[i-1]-1
            gain = float(w @ r)
            wealth *= 1+gain
            w = w*(1+r)/(1+gain)
        if date in schedule:
            target = schedule[date]
            turnover = float((target-w).abs().sum())
            wealth *= 1-cost*turnover
            w = target.copy()
            logs.append({'date':date, 'traded_notional':turnover, **w.to_dict()})
        values[date] = wealth
    return pd.Series(values), pd.DataFrame(logs)

def metrics(equity):
    # Include initial trading cost in the first holding month.
    month = equity.resample('ME').last()
    r = month.pct_change().dropna()
    r.iloc[0] = month.iloc[1]/1.-1
    n = len(r)
    dd = equity / equity.cummax().clip(lower=1.) - 1
    return {'CAGR': equity.iloc[-1]**(12/n)-1,
            'volatility':r.std(ddof=1)*np.sqrt(12),
            'max_drawdown_daily':dd.min(),
            'ending_10000':10000*equity.iloc[-1],
            'positive_months':(r>0).mean(), 'months':n}

def main():
    series = list(ThreadPoolExecutor(max_workers=4).map(download,TICKERS))
    all_prices = pd.concat(series,axis=1).sort_index()
    all_prices.to_csv(DATA/'adjusted_close.csv')
    summaries = []
    for commodity, label in [('PDBC','exact_etfs'),('DBC','extended_dbc_proxy')]:
        offensive = ['SPY','IWM','EFA','EEM','VNQ',commodity,'IEF','TLT']
        cols = offensive+['TIP','BIL']
        prices = all_prices[cols].dropna()
        # Fail on internal holes instead of silently compressing the trading calendar.
        reference = all_prices['SPY'].dropna().loc[prices.index.min():prices.index.max()].index
        assert prices.index.equals(reference), 'Missing ETF observations within common history'
        monthly = prices.groupby(prices.index.to_period('M')).tail(1)
        mom = sum(monthly/monthly.shift(k)-1 for k in [1,3,6,12])/4
        mom = mom.dropna()
        schedule = {d:targets(row,offensive) for d,row in mom.iterrows()}
        latest = max(schedule)
        pd.DataFrame(schedule).T.to_csv(OUT/f'{label}_targets.csv')
        mom.to_csv(OUT/f'{label}_momentum.csv')
        curves = {}
        for name,cost,lag in [('HAA gross',0,0),('HAA net 5bp',.0005,0),('HAA net 10bp',.001,0),('HAA next close 5bp',.0005,1),('SPY',.0005,0),('60 SPY 40 IEF',.0005,0)]:
            sched = schedule
            if name in ['SPY','60 SPY 40 IEF']:
                target = pd.Series(0.,index=cols)
                target['SPY'] = 1 if name=='SPY' else .6
                target['IEF'] = 0 if name=='SPY' else .4
                sched = {d:target for d in schedule} if name!='SPY' else {min(schedule):target}
            if lag:
                # Start in BIL at the common baseline; use completed signal at next daily close.
                initial = pd.Series(0.,index=cols); initial['BIL']=1
                sched = {min(schedule):initial}
                for d,w in schedule.items():
                    pos = prices.index.get_loc(d)+1
                    if pos < len(prices): sched[prices.index[pos]]=w
            eq,trades = simulate(prices,sched,cost)
            curves[name] = eq
            row = {'sample':label,'strategy':name,'start':str(eq.index[0].date()),'end':str(eq.index[-1].date()), **metrics(eq)}
            summaries.append(row)
            trades.to_csv(OUT/f'{label}_{name.replace(" ","_")}_trades.csv',index=False)
        frame = pd.DataFrame(curves)
        frame.to_csv(OUT/f'{label}_daily_equity.csv')
        monthly_eq = frame.resample('ME').last()
        monthly_ret = monthly_eq.pct_change().dropna()
        monthly_ret.iloc[0] = monthly_eq.iloc[1]-1
        monthly_ret.to_csv(OUT/f'{label}_monthly_returns.csv')
        annual = (1+monthly_ret).groupby(monthly_ret.index.year).prod()-1
        annual.to_csv(OUT/f'{label}_annual_returns.csv')
        if label=='exact_etfs':
            fig,axes = plt.subplots(2,1,figsize=(11,8),sharex=True,gridspec_kw={'height_ratios':[2,1]})
            for name in ['HAA net 5bp','SPY','60 SPY 40 IEF']:
                axes[0].plot(frame.index,frame[name]*10000,label=name)
                axes[1].plot(frame.index,100*(frame[name]/frame[name].cummax().clip(lower=1)-1),label=name)
            axes[0].set(title='Hybrid Asset Allocation | actual ETFs',ylabel='Growth of $10,000 (log scale)',yscale='log')
            axes[0].legend(); axes[1].set(ylabel='Daily drawdown (%)')
            for ax in axes: ax.grid(alpha=.25)
            fig.tight_layout(); fig.savefig(OUT/'performance.png',dpi=150); plt.close(fig)
            # First full month after the public March 3, 2023 article.
            post = frame.loc['2023-03-31':]
            post = post/post.iloc[0]
            pd.DataFrame({c:metrics(post[c]) for c in post}).T.to_csv(OUT/'post_publication.csv')
        print(label,'Latest targets',str(latest.date()),schedule[latest][schedule[latest]>0].to_dict(),flush=True)
    summary = pd.DataFrame(summaries)
    summary.to_csv(OUT/'summary.csv',index=False)
    print(summary.to_string(index=False),flush=True)

if __name__=='__main__': main()
