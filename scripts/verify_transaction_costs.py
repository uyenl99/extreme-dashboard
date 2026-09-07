from pathlib import Path
import numpy as np
import pandas as pd
R=Path('C:/junk/stocks')
def equal(a,b,label):
    if not np.allclose(a,b,rtol=1e-9,atol=1e-7,equal_nan=False): raise AssertionError(label)
# ETF1 independently reconstruct traded weights and net return from execution prices.
e=pd.read_csv(R/'DualMom/output_momo5/dual_momentum_results.csv',parse_dates=['date','exit_date'])
names=set(e[['h1','h2','h3']].stack()); opens={t:pd.read_csv(R/f'DualMom/data/{t}_daily.csv',parse_dates=['date']).set_index('date').open.resample('MS').first() for t in names}
prior={}
for row in e.itertuples():
    hs=[row.h1,row.h2,row.h3]; target={t:hs.count(t)/3 for t in set(hs)}
    buy=sum(max(target.get(t,0)-prior.get(t,0),0) for t in set(target)|set(prior)); sell=sum(max(prior.get(t,0)-target.get(t,0),0) for t in set(target)|set(prior))
    growth={t:w*opens[t].loc[row.exit_date]/opens[t].loc[row.date] for t,w in target.items()}; total=sum(growth.values())
    equal(row.cost_fraction,.0005*(buy+sell),'ETF1 fee'); equal(row.port_ret,(1-.0005*(buy+sell))*total-1,'ETF1 net return'); prior={t:v/total for t,v in growth.items()}
print('ETF1: all entry/sale turnover fees and monthly net returns reconcile')
# ETF2: independently replay target and drifted weights, including unchanged blend rebalancing.
p=R/'inflationcompass/output'; e=pd.read_csv(p/'monthly_backtest.csv',parse_dates=['entry_date','exit_date']); opens=pd.read_csv(p/'adjusted_open_prices.csv',index_col=0,parse_dates=True); prior={}
for row in e.itertuples():
    target={'XLP':.5,'IEF':.5} if row.held=='XLP/IEF' else {row.held:1.0}
    turnover=sum(abs(target.get(t,0)-prior.get(t,0)) for t in set(target)|set(prior))
    growth={t:w*opens.loc[row.exit_date,t]/opens.loc[row.entry_date,t] for t,w in target.items()}; total=sum(growth.values())
    equal(row.cost_fraction,.0005*turnover,'ETF2 fee'); equal(row.strategy_return,(1-.0005*turnover)*total-1,'ETF2 net return'); prior={t:v/total for t,v in growth.items()}
print('ETF2: initial purchase, switches, drift rebalances and net returns reconcile')
# Mean Reversion: independently reconstruct every day's cash from purchases, sales, and both fees.
p=R/'RevMurphy/output_long_only_5x0_100_no_cluster_next_open'; t=pd.read_csv(p/'trades.csv',parse_dates=['entry_date','exit_date']); eq=pd.read_csv(p/'equity_curve.csv',parse_dates=['date']).set_index('date'); closed=t[t.status=='closed']
equal(t.entry_cost,t.entry_notional*.0005,'MR entry fee'); proceeds=closed.shares*closed.exit_price
equal(closed.exit_cost,proceeds*.0005,'MR exit fee'); equal(closed.pnl_dollars,proceeds-closed.entry_notional-closed.entry_cost-closed.exit_cost,'MR trade P&L')
entries=pd.Series(-(t.entry_notional+t.entry_cost).values,index=t.entry_date).groupby(level=0).sum(); exits=pd.Series((proceeds-closed.exit_cost).values,index=closed.exit_date).groupby(level=0).sum(); cash=100000+entries.add(exits,fill_value=0).reindex(eq.index,fill_value=0).cumsum(); equal(eq.cash,cash,'MR cash ledger')
print(f'Mean Reversion: {len(t)} entries, {len(closed)} exits, daily cash and realized net P&L reconcile')
# HAA's gross/net weight paths are identical; ratio isolates the cumulative transaction fees.
p=Path(__file__).resolve().parents[1]/'data/haa'; e=pd.read_csv(p/'exact_etfs_daily_equity.csv',index_col=0,parse_dates=True); t=pd.read_csv(p/'exact_etfs_HAA_net_5bp_trades.csv',parse_dates=['date']); fees=pd.Series(1-.0005*t.traded_notional.values,index=t.date).reindex(e.index,fill_value=1).cumprod(); equal(e['HAA net 5bp']/e['HAA gross'],fees,'HAA fees')
print('HAA: all net/gross equity differences reconcile to 5-bps buy/sell turnover')
p=R/'MomoSp/pit_version/output_pit_r1000_5b_latest'; t=pd.read_csv(p/'transaction_costs.csv'); equal(t.buy_cost,t.start_equity*t.buy_turnover*.0005,'Stocks buy fee'); equal(t.sell_cost,t.start_equity*t.sell_turnover*.0005,'Stocks sell fee'); equal(t.net_return,(1-t.total_cost/t.start_equity)*(1+t.gross_return)-1,'Stocks net return')
print('Momentum Stocks: all purchases, sales, and net monthly returns reconcile')
