# Mean Reversion Generation Script

This document explains the current scripts used to generate and publish the
Mean Reversion strategy, including its long and short signals, 5-by-5 position
limits, point-in-time correlation clusters, next-day market-on-open execution,
website output, and known backtest limitations.

## Current Entry Points

The production Mean Reversion backtest is calculated by:

```powershell
C:\junk\stocks\RevMurphy\main_long_short_walk_forward.py
```

The Web repository runs it through:

```powershell
C:\junk\stocks\Web\scripts\update_mean_reversion_daily.ps1
```

That updater is called by the complete sequential dashboard batch:

```powershell
C:\junk\stocks\Web\scripts\update_all_strategies_sequentially.ps1
```

## Current Schedule

The active Windows scheduled task is:

```text
Extreme Dashboard - Sequential Strategy Updates
```

It starts Monday through Friday at 3:00 PM Pacific time. The sequential batch
runs Collective2 first and Mean Reversion second, followed by MoMoEtf1,
MoMoEtf2, and MoMo Stocks.

All stages must finish before one shared website pull request is opened,
checked, and merged.

## Production Command And Settings

The scheduled updater currently runs the equivalent of:

```powershell
python main_long_short_walk_forward.py `
  --end YYYY-MM-DD `
  --output-dir C:\junk\stocks\RevMurphy\output_long_short_5x5_walk_forward_next_open `
  --no-force-final-exit `
  --max-tickers 0 `
  --long-positions 5 `
  --short-positions 5
```

Parameters not shown in that command retain these current defaults:

| Setting | Production value |
| --- | ---: |
| Long position limit | 5 |
| Short position limit | 5 |
| Total short-book target | 20% of strategy equity |
| Maximum positions per correlation cluster | Selected annually from 1 or 2 |
| Correlation lookback | Selected annually from 60, 126, or 252 trading days |
| Absolute-correlation threshold | Selected annually from 0.60, 0.70, 0.80, or 0.90 |
| Minimum overlapping observations | 60 trading days |
| Volume filter | Off |
| CVaR filter | Off |
| Forced exit on final backtest day | Off |
| Modeled round-trip cost | 2 basis points |

`--max-tickers 0` means the full configured universe. It does not mean zero
tickers and it does not limit the report to the first few alphabetical symbols.

## Generation Flow

The Mean Reversion portion of the daily batch is:

1. Verify the RevMurphy Python environment and Polygon API key.
2. Load the full configured S&P 500 and Nasdaq-100 universe.
3. Load or refresh the required daily OHLCV histories from the shared Polygon
   cache.
4. Calculate completed-bar indicators and long/short signals for every ticker.
5. Build monthly point-in-time correlation clusters using only data available
   before each applicable month.
6. Evaluate cluster candidates with next-session MOO fills and select each
   calendar year's parameters using executions ending no later than the prior
   December 31.
7. Shift each completed daily-bar signal to the next trading session.
8. Simulate entries and exits at that next session's opening price.
9. Preserve positions that remain open on the final results date.
10. Write trades, equity, benchmark, return, summary, and cluster files.
11. Generate separate public and protected member Mean Reversion pages.
12. Include the completed pages in the shared daily strategy pull request.
13. Run the publication guard and Vercel preview checks before merging.

## Main Scripts

### `main_long_short_walk_forward.py`

This is the production backtest entry point. It selects the universe, loads
daily data, creates signals, constructs point-in-time cluster candidates,
selects each execution year's configuration from prior years only, shifts
signals to the next open, runs the long/short portfolio simulation, and writes
the output files.

### `signals.py`

This module calculates SMA, IBS, RSI(2), daily and three-day returns, QPI,
upper-tail QPI, optional volume and CVaR filters, and all long/short entry and
exit conditions.

### `clusters.py`

This module groups stocks by absolute daily-return correlation. Production uses
its point-in-time monthly method so a historical month cannot use correlation
information from later months.

### `backtest.py`

This module applies the position limits, cluster cap, sizing, next-open fills,
mark-to-market accounting, exits, transaction costs, performance statistics,
and output-file generation.

### `generate_mean_reversion_page.py`

This Web repository script reads the completed backtest results and creates the
public and protected member versions of `mean-reversion.html`.

## Universe And Market Data

The production runner uses the union of the configured:

```text
S&P 500 + Nasdaq-100
```

The universe comes from the locally cached OVNSP index snapshot. Duplicate
symbols appearing in both indexes are included only once.

Daily adjusted OHLCV data is loaded through Polygon and cached under:

```text
C:\junk\stocks\shared_data\daily
```

The universe cache is:

```text
C:\junk\stocks\shared_data\index_universe.csv
```

The strategy benchmark file contains normalized curves for:

```text
SPY, QQQ, VOO
```

The website prominently compares the strategy with SPY and allows the other
benchmark curves to be selected on the chart.

## Indicators

### Internal Bar Strength

Internal Bar Strength is calculated as:

```text
IBS = (Close - Low) / (High - Low)
```

Values near zero mean the close was near the day's low. Values near one mean
the close was near the day's high.

### QPI

Long-side QPI is the percentile rank of the current three-trading-day return
against that stock's prior three years, or 756 trading observations, of
three-day returns.

The current return is excluded from its own reference window. A lower QPI
means the decline is more unusual relative to that stock's prior history.

The short side uses upper-tail QPI: the share of prior three-day returns that
were at least as high as the current return. A lower value means the current
positive three-day move is unusually strong.

### Trend And Exit Indicators

The model also calculates:

- a 200-trading-day simple moving average;
- two-period RSI; and
- one-day and three-day close-to-close returns.

## Long Entry Rules

A stock becomes a long candidate after a completed daily bar when all of these
conditions are true:

1. Its one-day close-to-close return is negative.
2. Its three-day-return QPI is below 0.30.
3. Its close is above its 200-day moving average.
4. Its IBS is below 0.10.
5. Any enabled volume and CVaR filters pass.

When more long candidates exist than open slots, candidates are ordered by
lowest QPI and then lowest IBS, subject to the correlation-cluster cap.

The volume and CVaR filters are currently disabled in the scheduled production
run.

## Long Exit Rules

An open long position receives an exit signal after a completed daily bar when
either:

```text
IBS > 0.90
```

or:

```text
RSI(2) > 90
```

The simulated exit occurs at the next trading session's open.

## Short Entry Rules

A stock becomes a short candidate after a completed daily bar when all of
these conditions are true:

1. Its three-day close-to-close return is positive.
2. Its three-day upper-tail QPI is below 0.15.
3. Its close is below its 200-day moving average.
4. Any enabled volume and CVaR filters pass.

When more short candidates exist than open slots, candidates are ordered by
lowest upper-tail QPI and then strongest three-day return, subject to the same
correlation-cluster cap.

## Short Exit Rules

An open short position receives an exit signal after a completed daily bar
when either:

```text
IBS < 0.10
```

or:

```text
RSI(2) < 10
```

The simulated cover occurs at the next trading session's open.

## Signal And Execution Timing

The strategy uses only completed daily bars to form a signal. Every signal
column is shifted forward one trading row for that ticker before the backtest
executes it.

In simplified form:

```text
Completed daily bar -> entry or exit signal -> next trading session's open
```

Example:

```text
Signal calculated after Monday's completed bar
Simulated order fill: Tuesday's regular market open
```

The strategy therefore does not earn Monday's close-to-Tuesday's-open move
before the order can be known. The same next-open rule applies to both entries
and exits.

## Portfolio Sizing

The production configuration allows up to five long and five short positions.

At each entry decision:

- the long book targets 80% of strategy equity, so each of five long slots
  targets approximately 16%;
- the entire short book targets 20% of current strategy equity; and
- each of five short slots therefore targets approximately 4% of equity.

If all slots are filled, the intended gross exposure is approximately:

```text
80% long + 20% short = 100% gross exposure
```

and intended net exposure is approximately:

```text
80% long - 20% short = 60% net long
```

Actual exposure can be lower when too few candidates qualify, positions exit,
the cluster cap blocks a candidate, or cash is not available for another long
entry.

## Correlation Clusters

The model selects a cap of one or two combined long/short positions per
correlation cluster independently for each execution year.

For each calendar month, the cluster map:

1. uses daily returns strictly before the first day of that month;
2. uses the annually selected 60, 126, or 252 trading-day lookback;
3. requires at least 60 overlapping observations;
4. uses absolute return correlation; and
5. links stocks using the annually selected 0.60, 0.70, 0.80, or 0.90 threshold.

The point-in-time monthly maps prevent the backtest from using future
correlations to decide which historical trades were allowed. Parameter
selection is expanding walk-forward: the configuration applied to a year is
ranked only on results through the preceding December 31. The chosen annual
parameters and all candidate scores are saved with the output.

## Optional Filters

The code supports a volume filter that can reject an entry when the signal
day's volume is above the maximum of the prior 20 trading days.

It also supports a rolling lower-tail CVaR filter. Its defaults use the prior
252 daily returns, average the worst 5%, and reject an entry below -6%.

Both optional filters are currently off. They should not be described as part
of the production results unless the scheduled command is changed and the
backtest is regenerated.

## Transaction Costs And Unmodeled Costs

The backtest subtracts 2 basis points of entry notional as a modeled round-trip
cost when a trade closes.

It does not separately model:

- bid/ask spreads or opening-auction slippage;
- short borrow fees or stock availability;
- market impact or liquidity limits;
- taxes; or
- rejected, partial, or delayed orders.

Real member results can therefore differ materially from the simulation.

## Open Final Positions

The scheduled command uses `--no-force-final-exit`. Positions that have not
triggered a genuine exit remain open on the last backtest date instead of being
artificially closed for reporting.

The member Open Positions table is built from those open records. Latest MOO
Orders is built from the most recent entry and exit execution date in the
refreshed backtest; it is not a separate intraday alert feed.

## Main Output Files

Production results are written under:

```text
C:\junk\stocks\RevMurphy\output_long_short_5x5_walk_forward_next_open
```

Important files include:

- `all_signals.csv`: shifted next-open signal and indicator history.
- `trades.csv`: closed and still-open long/short trades with entry and exit
  prices, sizes, P/L, return, and status.
- `daily_trades.csv`: daily entries, exits, notionals, realized P/L, and current
  holdings.
- `daily_pnl.csv`: daily equity, P/L, return, peak equity, and drawdown.
- `equity_curve.csv`: cash, market value, total equity, and open-position counts.
- `benchmark_curve.csv`: normalized SPY, QQQ, and VOO benchmark curves.
- `monthly_returns.csv`: completed strategy return by month.
- `monthly_returns_table.csv`: presentation table with monthly and compounded
  yearly returns.
- `yearly_returns.csv`: completed strategy return by year.
- `summary_stats.csv`: trade count, win rate, average trade return, CAGR,
  drawdown, volatility, Sharpe ratio, and final equity.
- `cluster_walk_forward_selection.csv`: the prior-only configuration chosen for
  each execution year.
- `cluster_walk_forward_scores.csv`: every candidate's training-period score.
- `equity_plot.png`: strategy, benchmarks, and drawdown plot written by the
  backtest.

## Public And Member Pages

The public page includes historical performance metrics, strategy/SPY
comparison, the interactive equity chart, monthly returns, public FAQ, and the
simulation disclaimer. It excludes current orders, open positions, and recent
trade records.

The protected member page additionally includes:

- Latest MOO Orders
- Open Positions
- Latest 20 Trades

The member tables show trade direction, execution dates, prices, position
values, shares, and open/closed status where applicable.

## Publication Behavior

The sequential coordinator starts from the latest GitHub `main`, runs all five
strategy stages, and stages only approved public and protected result paths.

After every strategy finishes, it:

1. commits the combined result set to the shared preview branch;
2. opens one daily strategy pull request;
3. runs the site publication guard and Vercel checks;
4. squash-merges only after those checks pass; and
5. verifies the production publication.

If Mean Reversion or any other strategy stage fails, the combined production
update is not merged.

## Safety Behavior

The page generator requires the expected summary, equity, benchmark, monthly
return, trade, and daily-trade files. It rejects invalid or unsorted result
dates.

It separately verifies that Latest MOO Orders, Open Positions, and Latest 20
Trades have not leaked into the public page.

The daily publication guard restricts the files that automation may change and
checks the protected strategy pages before publication.

## Known Backtest Limitations

The current index universe is a static snapshot rather than point-in-time S&P
500 and Nasdaq-100 membership. Historical results can therefore contain
survivorship bias and universe-membership look-ahead bias.

Correlation clusters and their annual parameter selections are point-in-time
and do not use future returns, but that does not correct the static-universe
limitation.

The backtest also depends on vendor-adjusted historical OHLCV data. Vendor
corrections, corporate-action adjustments, ticker changes, and missing history
can change regenerated results.

These limitations are especially important because the displayed performance
is simulated and may appear substantially better than achievable live results.

## Member-Facing Interpretation

Members should treat Mean Reversion as a next-day-MOO model, not an intraday
signal service.

The important timing summary is:

```text
Signal: after a completed daily bar
Entry or exit: next regular market open
Maximum positions: 5 long and 5 short
Sizing: about 20% per long and 4% per short at entry
Cluster parameters: selected annually from prior results only
```

The latest MOO table reports the newest simulated execution event in the
completed refresh. Open Positions reports trades still open at the final result
date.

The model can lose money, short losses can exceed the initial short proceeds,
and the strategy can underperform SPY. Results are simulated research, not
verified personal-account performance or individualized financial advice.
