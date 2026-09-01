# Mean Reversion Generation

This document defines the Mean Reversion version used by the website and daily
automation.

## Selected production version

The production model is a long-only mean-reversion backtest with:

- five maximum long positions;
- no short positions;
- 100% target long exposure when all five slots are filled;
- approximately 20% of current strategy equity targeted for each new position;
- no correlation clustering;
- signals calculated from completed daily bars;
- entries and exits filled at the next regular-session market open (MOO);
- the full configured stock universe (`--max-tickers 0`);
- no forced liquidation on the final result date; and
- the existing modeled round-trip transaction cost.

The production command is:

```powershell
python C:\junk\stocks\RevMurphy\main_long_short_next_open.py `
  --end YYYY-MM-DD `
  --output-dir C:\junk\stocks\RevMurphy\output_long_only_5x0_100_no_cluster_next_open `
  --no-force-final-exit `
  --max-tickers 0 `
  --long-positions 5 `
  --long-only `
  --long-gross-ratio 1.0 `
  --max-per-cluster 0
```

Despite the historical script filename, `--long-only` sets the short-position
limit and short exposure to zero. `--max-per-cluster 0` disables the cluster
filter.

## Execution timing

A signal is calculated only after a daily bar is complete. The signal is shifted
to the next available trading session, and the backtest uses that session's open
for the simulated fill. The last result date is not forcibly closed, so the open
trades in `trades.csv` represent the current model portfolio.

## Website generation

The public page is generated with:

```powershell
python generate_mean_reversion_page.py `
  --source C:\junk\stocks\RevMurphy\output_long_only_5x0_100_no_cluster_next_open `
  --output mean-reversion.html `
  --audience public
```

The member page uses the same source with `--audience member`. It adds the latest
MOO orders, current open positions, and latest 20 trades. Both versions use the
same summary, equity curve, benchmark, monthly-return table, and FAQ definitions.

The generator also synchronizes the Mean Reversion statistics on
`strategies.html` and `members.html`.

## Daily automation

`scripts/update_mean_reversion_daily.ps1` runs this exact version. It is called
by `scripts/update_all_strategies_sequentially.ps1` in the weekday batch that
starts at 3:00 PM Pacific. Mean Reversion is combined with the other completed
strategy refreshes in the shared daily pull request.

The automation must not publish a different output directory or silently add
short positions or clustering. `scripts/verify_moo_backtests.py` checks that:

- every entry and completed exit matches the corresponding daily open;
- every signal date precedes its execution date;
- every trade is long;
- the portfolio never exceeds five long positions; and
- the portfolio contains no short positions or cluster assignments.

## Output files

The website requires these files from the selected output directory:

- `summary_stats.csv`
- `equity_curve.csv`
- `benchmark_curve.csv`
- `monthly_returns.csv`
- `trades.csv`
- `daily_trades.csv`

The backtest also writes `all_signals.csv`, which is used for verification but is
not copied into the website repository.

## Important limitations

The results are hypothetical. They may differ from live trading because of
opening gaps, slippage, liquidity, order handling, fees, taxes, and unavailable
capital. The historical test currently applies today's index constituent
universe to earlier periods, which creates survivorship bias. Results do not
guarantee future performance.
