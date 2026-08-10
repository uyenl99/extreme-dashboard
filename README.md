## Extreme Dashboard

### Refresh the Mean Reversion backtest page

After running RevMurphy, generate the public page from its compact CSV outputs:

```powershell
python generate_mean_reversion_page.py `
  --source ../RevMurphy/output_long_short_live `
  --alert-source ../RevMurphy/output_live_alerts
```

This writes `mean-reversion.html` with the latest alert and latest 50 trades,
including entry and exit prices. The page clearly identifies the results as a
simulated backtest and does not import the large `all_signals.csv` file.

### Automatic Mean Reversion updates

`scripts/update_mean_reversion_daily.ps1` refreshes the RevMurphy backtest and
live alerts, regenerates the page and strategy-card metrics, and commits only
the two generated website files directly to `main`. A Windows scheduled task
runs it daily at 12:30 PM local Pacific time. The PC must be on and online, and
`POLYGON_API_KEY` must be available as a user environment variable.

### Refresh the Dual Momentum backtest page

After running `DualMom/momo5.py`, generate the public page from its outputs:

```powershell
python generate_momentum_page.py --source ../DualMom/output_momo5
```

This replaces the old placeholder `momentum.html` with the Dual Momentum
backtest, SPY comparison, return tables, and monthly allocation history.

### Refresh the Momentum Stocks backtest page

After running `MomoSp/pit_version/momo_sp_v2a.py` and its live-signal job,
generate the public stock-momentum page:

```powershell
python generate_momentum_stocks_page.py `
  --source ../MomoSp/pit_version/output_pit_v2a `
  --alert-source ../MomoSp/pit_version/output_pit_v2a_live/latest_signal.json
```

This writes `momentum-stocks.html` with the equity/SPY comparison, return
tables, monthly allocations, and the latest v2a live alert.

### Automatic Collective2 performance updates

`.github/workflows/update-performance.yml` refreshes `performance.html` from
the Collective2 API every day at 14:00 UTC (6:00 AM PST / 7:00 AM PDT). It can
also be run manually from the repository's Actions tab.

The repository must have an Actions secret named `C2_API_KEY`. The workflow
also refreshes the Extreme OS historical trades and current open positions.
It commits `performance.html` and `extreme-os.html` only when the API data
changed, which triggers the normal Vercel production deployment.
