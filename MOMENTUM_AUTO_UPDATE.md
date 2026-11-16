# Momentum ETF automatic updates

Three independent Windows tasks refresh Momentum ETF1, Momentum ETF2 and
Momentum Stocks every Monday through Friday at **1:32, 1:33 and 1:34 PM
Pacific**. The legacy **Extreme Dashboard - Momentum Weekday Update** task is
disabled.

## What runs

`scripts/update_momentum_card.ps1` performs the selected card's refresh:

1. Refreshes only the requested Momentum model and its data.
2. Installs the pinned runtime requirements for `C:\junk\stocks\inflationcompass` when needed.
3. Runs `inflation_compass.py` to refresh Momentum ETF2 from Yahoo and FRED.
4. Regenerates the public and protected member pages, including the current partial month, latest alert, and every recent monthly allocation.
5. Copies public summary, wealth chart, and monthly P&L assets into `inflation-compass/`.
6. Publishes that card through its own preview PR after the site and Vercel checks pass.

Logs are written beneath `%LOCALAPPDATA%\ExtremeDashboardAutomation\logs\cards`.

## Install or repair the task

Open PowerShell and run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\junk\stocks\Web\scripts\register_independent_card_tasks.ps1
```

The installer is idempotent: running it again replaces the existing task with the documented schedule. `StartWhenAvailable` is enabled, so Windows starts a missed run when the signed-in computer becomes available.

## Run manually

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\junk\stocks\Web\scripts\update_momentum_card.ps1 -Card momentum-etf1
```

Or start the registered task:

```powershell
Start-ScheduledTask -TaskName "Extreme Dashboard - Card - Momentum ETF1"
```

## Verify

```powershell
Get-ScheduledTask -TaskName "Extreme Dashboard - Card - Momentum ETF1" |
  Get-ScheduledTaskInfo
```

After a successful run, verify:

- `momentum.html` contains the current Momentum ETF1 results.
- `momentum2.html` loads `inflation-compass/last_50_trades.csv` and current Momentum ETF2 data.
- The latest commits appear on `main` and the Vercel deployment succeeds.

## Operational requirements

- The PC must be signed in, online, and able to reach Yahoo, FRED, GitHub, and Vercel.
- GitHub CLI and Git credentials must remain authenticated for unattended pushes.
- The task uses the bundled Codex Python and Git paths currently configured in the scripts. Update those paths if the runtime location changes.
- These pages contain simulated research results, not verified live performance or investment advice.
