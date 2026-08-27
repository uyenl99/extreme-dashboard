# MoMo Stocks Generation Script

This document explains the current scripts used to generate and publish
MoMo Stocks, including its point-in-time universe, monthly signal timing,
current partial-month calculation, preliminary alert, and website publication.

## Current Entry Points

The production MoMo Stocks strategy is refreshed by:

```powershell
C:\junk\stocks\MomoSp\pit_version\update_v2a_live.py
```

The Web repository then creates the current-month preview with:

```powershell
C:\junk\stocks\Web\generate_momentum_stocks_preview.py
```

Both scripts are called by the combined Momentum updater:

```powershell
C:\junk\stocks\Web\scripts\update_momentum_weekdays.ps1
```

That updater is called by the complete sequential dashboard batch:

```powershell
C:\junk\stocks\Web\scripts\update_all_strategies_sequentially.ps1
```

## Current Schedule

The active sequential strategy task runs Monday through Friday beginning at
3:00 PM Pacific time.

The batch updates Collective2 and Mean Reversion first. It then runs MoMoEtf1,
MoMoEtf2, and MoMo Stocks in sequence. MoMo Stocks therefore starts after the
earlier stages finish rather than at an exact independent time.

All stages must complete before the shared daily pull request is opened and
merged.

## Generation Flow

The MoMo Stocks portion of the daily batch is:

1. Refresh the latest completed Russell 1000 month-end membership.
2. Refresh current price histories for the eligible universe.
3. Refresh missing point-in-time market-cap records.
4. Regenerate completed monthly backtest results.
5. Write the completed month-end allocation signal.
6. Run the current-month preview scanner using the latest completed price day.
7. Calculate the preliminary allocation for the next month's first trading
   session.
8. Mark the allocation already in effect to the latest available close.
9. Generate separate public and member MoMo Stocks pages.
10. Add the completed pages to the shared daily strategy pull request.
11. Run the publication guard and Vercel preview checks before merging.

## Main Scripts

### `update_v2a_live.py`

This is the production data-refresh and completed-month signal script under:

```text
C:\junk\stocks\MomoSp\pit_version
```

It refreshes Russell 1000 membership, price data, and market-cap records;
regenerates the completed backtest; and writes the latest completed-month
signal.

### `momo_sp_v2a.py`

This is the point-in-time V2A backtest wrapper. It filters historical
membership by point-in-time market capitalization, runs the monthly momentum
model, applies transaction costs, and writes the completed result files.

### `pit_v2.py`

This module contains the core point-in-time monthly selection logic. It uses
the membership and price information available at each historical month end,
ranks eligible stocks by momentum, applies the risk regime, and calculates the
following holding-period return.

### `generate_momentum_stocks_preview.py`

This Web repository script extends the completed-month signal with two
member-facing records:

- a preliminary signal calculated from the latest available price date for
  the following month's open; and
- the current allocation already in effect, including its incomplete
  month-to-date return and SPY comparison.

The preview scanner refreshes clean price histories for the current Russell
1000 membership. Because that universe contains roughly one thousand stocks,
this stage can take several minutes.

### `generate_momentum_stocks_page.py`

This script reads the completed backtest outputs and preview signal, then
creates the public and protected member versions of `momentum-stocks.html`.

The member page includes Current Partial Month, Latest Alert, and Latest 20
Historical Trades. The public page excludes those sections.

## Strategy Inputs

The production universe is the point-in-time Russell 1000 membership captured
at each completed month end.

An eligible stock must have:

- membership in that point-in-time universe;
- sufficient valid adjusted-price history;
- a point-in-time market capitalization above $5 billion; and
- a valid 210-trading-day momentum score.

The benchmark is:

```text
SPY
```

Historical results depend on the stored membership, adjusted prices, and
market-cap records. Data corrections can change regenerated results.

## Defensive Candidates

When the volatility regime is risk-off, MoMo Stocks rotates out of the ten
stock positions and selects one of these defensive candidates:

| Ticker | Exposure |
| --- | --- |
| `GLD` | Gold bullion |
| `GDX` | Gold-mining stocks |
| `AOM` | Moderate-allocation stock and bond portfolio |
| `TLT` | Long-term U.S. Treasury bonds |
| `SHY` | Short-term U.S. Treasury bonds |

The model compares the candidates over the prior 21 trading days and selects
the one with the strongest return. The selected defensive asset receives 100%
of the model portfolio until the next monthly rebalance.

This is a relative-strength selection, not a guarantee that the chosen asset
will rise or prevent a loss.

## Signal Logic

At each completed month end, the strategy:

1. Uses only stocks in the point-in-time Russell 1000 membership.
2. Removes stocks without valid price or market-cap information.
3. Requires market capitalization above $5 billion.
4. Calculates 210-trading-day momentum.
5. Selects the ten highest-ranked eligible stocks when risk-on.
6. Assigns equal 10% target weights to those ten stocks.
7. Applies the volatility regime filter.
8. When risk-off, selects the strongest defensive candidate over the prior
   21 trading days and allocates the full model portfolio to that asset.

The production run currently uses zero momentum skip days.

## Risk Regime

The volatility regime compares:

- SPY's annualized 10-trading-day realized volatility; and
- the VIX 30-trading-day moving average.

The current implementation labels the model risk-on when the VIX moving
average is above SPY realized volatility. Otherwise it is risk-off.

These diagnostic values remain part of the model calculation but are not
displayed in the member alert or historical table.

## Entry And Exit Timing

MoMo Stocks is a monthly strategy.

The intended sequence is:

```text
Completed month-end signal -> first trading day of next month -> hold until
the first trading day of the following month
```

Example:

```text
July completed signal
Current allocation begins: first trading day of August
Next preliminary signal: formed during August
Next rebalance: first trading day of September
```

The website labels the intended execution as the next month's open. The
current backtest return series uses the stored adjusted daily price on the
entry and exit dates, so it is not a reconstruction of exact broker MOO fills.
Opening prices, spreads, slippage, and available liquidity can differ.

## Current Partial-Month Timing

The Current Partial Month panel describes the allocation already in effect,
not the preliminary next allocation.

The preview script:

1. reads the latest completed signal and its execution date;
2. uses the completed signal's holdings as the current allocation;
3. finds the first available price session on or after the execution date;
4. marks each equal-weight holding to the latest available close;
5. averages those holding returns for the incomplete strategy return; and
6. calculates SPY's return over the same available dates.

The preview return is not final and does not separately deduct estimated
transaction costs. It can change on every successful weekday refresh.

The same allocation is added as a starred current-month row at the top of the
member historical table. Only 19 completed rows are then shown, keeping the
table at 20 rows total.

## Latest Alert Timing

The Latest Alert is the preliminary allocation for the first trading day of
the next month.

During the current month, the preview scanner uses the latest completed price
day as a provisional signal date. The selected holdings can change before the
month closes. After month end, the normal completed-month run finalizes the
signal.

Current Partial Month and Latest Alert therefore answer different questions:

- Current Partial Month: what the model is holding now.
- Latest Alert: what the model currently expects to hold next month.

## Transaction Costs

The completed backtest applies 2 basis points to the model dollars bought and
2 basis points to the model dollars sold at each rebalance.

The transaction-cost calculation uses actual target-weight changes, so a
position retained from one month to the next does not incur the same turnover
as a fully replaced position.

## Main Output Files

Completed result files are written under:

```text
C:\junk\stocks\MomoSp\pit_version\output_pit_r1000_5b_latest
```

Important files include:

- `monthly_results.csv`: completed monthly signals, holdings, returns,
  benchmark returns, equity, and transaction-cost information.
- `daily_equity.csv`: daily strategy/SPY equity and drawdown for completed
  holding periods.
- `monthly_return_table.csv`: monthly and compounded yearly strategy returns.
- `summary.csv`: CAGR, volatility, Sharpe ratio, drawdown, SPY comparison,
  universe mode, minimum market cap, and position count.
- `monthly_coverage.csv`: point-in-time membership and data-coverage checks.
- `transaction_costs.csv`: rebalance turnover and modeled costs.
- `equity_drawdown.svg`: strategy equity and drawdown chart output.

Live and preview files are written under:

```text
C:\junk\stocks\MomoSp\pit_version\output_pit_v2a_live
```

They include:

- `latest_signal.json`: preliminary next-month alert plus the current
  allocation and incomplete return.
- `latest_ranked_stocks.csv`: ranked stocks underlying the preliminary alert.
- `clean_history_audit.csv`: completed-signal clean-price audit.
- `preview_clean_history_audit.csv`: current preview clean-price audit.
- `price_refresh_audit.csv`: daily refresh status by ticker.

## Public And Member Pages

The public page includes historical performance metrics, the equity chart,
monthly returns, FAQ, and disclaimer. It does not include current holdings,
the preliminary alert, or the latest allocation history.

The protected member page additionally includes:

- Current Partial Month
- Latest Alert
- Latest 20 Historical Trades

The historical table displays Entry, Holdings, Regime, Return, and SPY. The
internal realized-volatility and VIX-moving-average diagnostics are not shown.

## Publication Behavior

The sequential coordinator starts from the latest GitHub `main`, runs every
strategy, and stages the approved public and protected strategy pages.

After all strategies finish, it:

1. commits the combined result set to the shared preview branch;
2. opens one shared daily pull request;
3. runs the publication guard and Vercel checks;
4. squash-merges only after the checks pass; and
5. verifies the published production commit.

If MoMo Stocks or any earlier stage fails, the combined production update is
not merged.

## Safety Behavior

The preview scanner fails if current holdings do not have valid entry and
latest prices. It does not silently publish an incomplete partial-month
return.

The page generator separately verifies that member-only Current Partial Month,
Latest Alert, and historical sections have not leaked into the public page.

The daily publication guard restricts which generated paths automation may
change and verifies that member historical tables contain exactly 20 rows.

## Member-Facing Interpretation

Members should treat MoMo Stocks as a concentrated monthly allocation model,
not an intraday signal service.

In risk-on periods, the model holds ten equal-weight stocks. In risk-off
periods, it can hold one defensive asset with the full model portfolio.

The current allocation is already in effect. The latest alert is preliminary
until month end and is intended for the next monthly rebalance. The partial
return is an estimate through the displayed price date, not a completed month.

The model can lose money and can underperform SPY. Results are simulated model
output, not verified personal-account performance or individualized financial
advice.
