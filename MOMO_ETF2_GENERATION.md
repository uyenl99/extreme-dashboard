# MoMoEtf2 Generation Script

This document explains the current scripts used to generate and publish
MoMoEtf2, including its data inputs, regime logic, signal timing, current
partial-month calculation, and automated website publication.

## Current Entry Points

The MoMoEtf2 strategy is calculated by:

```powershell
C:\junk\stocks\inflationcompass\inflation_compass.py
```

It is run by the Web repository's combined Momentum updater:

```powershell
C:\junk\stocks\Web\scripts\update_momentum_weekdays.ps1
```

That updater is called by the complete sequential dashboard batch:

```powershell
C:\junk\stocks\Web\scripts\update_all_strategies_sequentially.ps1
```

The sequential batch updates Collective2 and Mean Reversion first. It then
runs MoMoEtf1, MoMoEtf2, and MoMo Stocks before opening one shared website
pull request.

## Current Schedule

The active Windows scheduled task is:

```text
Extreme Dashboard - Sequential Strategy Updates
```

It runs Monday through Friday at 3:00 PM Pacific time. MoMoEtf2 starts after
the earlier stages finish, so its exact start time depends on how long
Collective2, Mean Reversion, and MoMoEtf1 take that day.

The website is not published from a partially completed batch. All strategy
stages must finish before the shared pull request is created, checked, and
merged.

## Generation Flow

The MoMoEtf2 portion of the daily batch is:

1. Install or verify the packages listed in
   `C:\junk\stocks\inflationcompass\requirements.txt`.
2. Download adjusted ETF prices from Yahoo Finance.
3. Download the five-year breakeven inflation rate from FRED.
4. Calculate daily growth and inflation conditions.
5. Take the last available trading observation in each calendar month.
6. Map each completed monthly signal to one of four regimes and allocations.
7. Shift the selected allocation forward one month to prevent look-ahead.
8. Calculate monthly returns, daily mark-to-market returns, drawdowns, summary
   statistics, the latest allocation alert, and the chart.
9. Write the strategy files to
   `C:\junk\stocks\inflationcompass\output`.
10. Generate separate public and member versions of `momentum2.html`.
11. Copy only approved public assets into the Web repository.
12. Include the completed MoMoEtf2 changes in the shared daily pull request.
13. Run the Vercel preview and publication guards before automatic merging.

## Main Scripts

### `inflation_compass.py`

This is the current MoMoEtf2 strategy, backtest, data-refresh, alert, and
output-generation script.

It downloads the required market and macroeconomic series, constructs the
four-regime model, applies each month-end signal to the following month,
calculates strategy and SPY performance, and writes the complete output set.

### `generate_momentum_etf2_page.py`

This Web repository script reads the files generated under:

```text
C:\junk\stocks\inflationcompass\output
```

It creates the public and member MoMoEtf2 pages. Both versions include summary
statistics, the equity chart, monthly returns, SPY comparisons, and the
strategy FAQ. The member version additionally includes the current partial
month, latest alert, and latest 20 historical allocation rows.

### `update_momentum_weekdays.ps1`

This is the combined Momentum execution wrapper. For MoMoEtf2 it:

- installs the declared Python dependencies;
- runs `inflation_compass.py`;
- generates public and member pages;
- copies the approved summary, monthly-return, and chart assets; and
- leaves publication to the shared sequential batch.

### `live_alert.py`

This optional standalone checker recalculates the latest completed-month
allocation and compares it with `output/alert_state.json`.

It prints a full alert when the proposed next holding changes, or when run with
`--force`. The main 3:00 PM dashboard batch does not depend on this standalone
checker because `inflation_compass.py` already writes the latest alert files.

## Strategy Inputs

The adjusted-price universe is:

```text
SPY, XLE, XLI, XLF, XLB, XLU, XLV, XLP, XLK, IEF
```

The model also downloads these FRED series:

```text
T5YIE   Five-Year Breakeven Inflation Rate
CPIAUCSL Consumer Price Index for All Urban Consumers
```

`T5YIE` is part of the allocation signal. `CPIAUCSL` is used for the separate
CPI bucket analysis and does not select the live monthly holding.

The benchmark is:

```text
SPY
```

Prices must be adjusted or total-return prices. Yahoo and FRED may revise
historical observations, so regenerated results can occasionally change.

## Growth Signal

The growth condition compares SPY with its 200-trading-day simple moving
average:

```text
Growth up   : SPY is above its 200-day moving average
Growth down : SPY is not above its 200-day moving average
```

The comparison is evaluated on the last available trading observation of each
calendar month.

## Inflation Signal

The inflation condition combines FRED breakeven inflation with relative sector
behavior.

The positive-inflation basket is:

```text
50% XLE + 1/6 XLI + 1/6 XLF + 1/6 XLB
```

The negative-inflation basket is:

```text
1/3 XLU + 1/3 XLV + 1/3 XLP
```

The script compounds each basket's daily return and forms a ratio of the
positive basket to the negative basket. It then calculates the 60-trading-day
regression slope of that ratio.

Inflation is on when:

1. `T5YIE` is above 2%; and
2. either `T5YIE` is above its value 60 trading days earlier or the sector
   ratio's 60-day regression slope is positive.

Short FRED publication and holiday gaps can be forward-filled for up to ten
trading observations. Longer missing periods are not silently filled.

## Regimes And Allocations

The growth and inflation conditions produce four regimes:

| Growth | Inflation | Regime | Next-month allocation |
| --- | --- | --- | --- |
| Up | On | Reflation | 100% XLE |
| Up | Off | Goldilocks | 100% XLK |
| Down | On | Stagflation | 100% XLU |
| Down | Off | Slowdown | 50% XLP / 50% IEF |

The regime names describe the model state. They are not guarantees about the
economy or future market returns.

## Signal And Holding Timing

MoMoEtf2 is a monthly model. The last actual trading observation in month
`t` determines the allocation held during month `t+1`.

In simplified form:

```text
Completed month-end signal -> following month's allocation -> following month's return
```

The code enforces this with a one-month shift:

```python
held = signals["holding"].shift(1)
```

This prevents a month from earning the return of an allocation selected using
information that was not known until that month ended.

Example:

```text
July completed signal
Effective allocation: August
August model return: return of that selected allocation during August
```

## Backtest Price Convention

The current backtest calculates monthly returns from adjusted month-end closes.
It is therefore a close-to-close monthly return model, not a backtest of exact
broker MOO fills.

The website's alert may describe the next allocation as effective at the next
month's open for member planning. Real opening fills, spreads, slippage, and
broker execution can differ from the adjusted-close backtest convention.

An optional `--cost-bps` argument subtracts the specified transaction cost
when the effective holding changes. The scheduled production run currently
uses the default of zero basis points.

## Current Partial-Month Timing

The current partial-month value is not a finalized monthly return.

For the current month, the page generator:

1. identifies the current calendar month in `monthly_backtest.csv`;
2. reads the allocation already in effect for that month;
3. reads the current regime that selected that allocation;
4. uses the latest available daily mark-to-market date; and
5. displays the incomplete current-month strategy return.

This value can change every weekday. It becomes a completed monthly result
only after the month closes and a later run finalizes that holding period.

## Latest Alert Timing

The member page distinguishes the current allocation from the latest alert.

- **Current Partial Month** is the allocation already in effect.
- **Latest Alert** is the preliminary signal being formed during the current
  month for the following month.

The preliminary signal can change until month end. The completed alert files
written by `inflation_compass.py` use only the latest completed calendar month.

## Main Output Files

The strategy writes these files under
`C:\junk\stocks\inflationcompass\output`:

- `monthly_backtest.csv`: monthly signal state, effective holding, strategy
  return, SPY return, and switch indicator.
- `daily_drawdown.csv`: daily holding, strategy/SPY return, wealth, and
  drawdown.
- `monthly_pnl_by_year.csv`: monthly strategy returns with compounded strategy
  and SPY annual returns.
- `summary.csv`: CAGR, Sharpe, volatility, drawdown, Sortino, Calmar, growth of
  one dollar, and daily maximum drawdown.
- `latest_alert.csv` and `latest_alert.json`: the latest completed-month model
  alert.
- `last_50_trades.csv`: the latest completed allocation changes. The member
  website displays only the latest 20 historical rows.
- `wealth.png`: the strategy-versus-SPY growth chart generated by the strategy
  script.
- `cpi_buckets.csv`: separate CPI bucket analysis.
- `alert_state.json`: the last recommendation stored by `live_alert.py`.

## Public And Member Pages

The public page includes historical summary information but excludes current
allocation details, alerts, and the latest 20 allocation history.

The protected member page includes:

- Current Partial Month
- Latest Alert
- Latest 20 Historical Trades
- Equity Curve
- Monthly Returns
- Strategy FAQ and disclaimer

Protected alert and trade files are not copied into the public
`inflation-compass` asset directory.

## Publication Behavior

The daily strategy coordinator starts from the latest GitHub `main`, generates
all public and protected pages, and stages only approved strategy-result paths.

After every strategy finishes, it:

1. commits the combined daily result set to the shared preview branch;
2. opens the daily strategy pull request;
3. waits for the Vercel preview and publication guards;
4. merges the pull request only after the checks pass; and
5. verifies the resulting production publication.

If any strategy or preview check fails, production is not changed.

## Safety Behavior

The sequential updater stops if its automation checkout contains unexpected
tracked changes or if an earlier shared daily pull request is still open.

The publication guard limits the paths that a daily result update may change.
It also verifies the member navigation, protected strategy pages, colored
performance metrics, and 20-row historical tables before publication.

The public MoMoEtf2 generator explicitly checks that current-month details,
latest alerts, and historical allocation rows have not leaked into the public
page.

## Member-Facing Interpretation

Members should read MoMoEtf2 as a monthly regime allocation model, not an
intraday signal service.

The current allocation is the model holding already in effect. The latest
alert is a preliminary view of the following month's allocation and can change
before the current month ends.

The weekday refresh keeps current mark-to-market returns, the dashboard, and
the preliminary signal current. It does not mean the model necessarily changes
holdings every day.

The model can lose money and can underperform SPY. The dashboard is simulated
model output, not verified personal-account performance or individualized
financial advice.
