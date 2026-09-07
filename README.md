## Extreme Dashboard

### Refresh the Mean Reversion backtest page

After running RevMurphy, generate the public page from its compact CSV outputs:

```powershell
python generate_mean_reversion_page.py `
  --source ../RevMurphy/output_long_only_5x0_100_no_cluster_next_open
```

This writes the public Mean Reversion page from the selected five-position,
100%-long, no-cluster, next-session MOO backtest. Generate the member page with
the same source and `--audience member`.

### Automatic Mean Reversion updates

`scripts/update_mean_reversion_daily.ps1` refreshes the RevMurphy backtest,
regenerates the public/member pages and strategy-card metrics, and contributes
the results to the shared daily pull request so Vercel provides a preview
before production is changed. The sequential weekday batch starts at 3:00 PM
Pacific.
The PC must be on and online, and `POLYGON_API_KEY` must be available as a user
environment variable.

### Automatic Momentum ETF updates

`scripts/update_momentum_weekdays.ps1` refreshes and publishes Momentum ETF1 and
Momentum ETF2 every weekday at 4:00 PM Pacific. Installation, logging,
verification, and manual-run instructions are documented in
[`MOMENTUM_AUTO_UPDATE.md`](MOMENTUM_AUTO_UPDATE.md).

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

`.github/workflows/update-performance.yml` refreshes the performance summary, monthly returns, and equity curve shown on `extreme-os.html` from
the Collective2 API every day at 14:00 UTC (6:00 AM PST / 7:00 AM PDT). It can
also be run manually from the repository's Actions tab.

The repository must have an Actions secret named `C2_API_KEY`. The workflow
also refreshes the Extreme OS historical trades and current open positions.
It commits the performance data fragments and `extreme-os.html` only when the API data
changed, which triggers the normal Vercel production deployment.

### HAA weekday updates

Hybrid Asset Allocation now joins the shared weekday batch at 3:00 PM Pacific. See [HAA_GENERATION.md](HAA_GENERATION.md) for calendar handling, verification and manual refresh instructions.
