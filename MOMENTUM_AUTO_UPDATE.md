# Momentum ETF automatic updates

The Windows scheduled task **Extreme Dashboard - Momentum Weekday Update** runs every Monday through Friday at **4:00 PM Pacific** (the computer's local time).

## What runs

`scripts/update_momentum_weekdays.ps1` performs these steps in order:

1. Runs `C:\junk\stocks\DualMom\update_momo5_daily.ps1` to refresh Momentum ETF1, regenerate `momentum.html`, commit changed results, and push `main`.
2. Installs the pinned runtime requirements for `C:\junk\stocks\inflationcompass` when needed.
3. Runs `inflation_compass.py` to refresh Momentum ETF2 from Yahoo and FRED.
4. Copies the summary, current alert, wealth chart, monthly P&L, and last 50 allocation changes into `inflation-compass/`.
5. Commits only changed Momentum ETF2 assets and pushes `main`, triggering Vercel production deployment.

Logs are written to `%LOCALAPPDATA%\ExtremeDashboardAutomation\logs\momentum-weekday-YYYY-MM-DD.log`.

## Install or repair the task

Open PowerShell and run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\junk\stocks\Web\scripts\register_momentum_weekday_task.ps1
```

The installer is idempotent: running it again replaces the existing task with the documented schedule. `StartWhenAvailable` is enabled, so Windows starts a missed run when the signed-in computer becomes available.

## Run manually

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\junk\stocks\Web\scripts\update_momentum_weekdays.ps1
```

Or start the registered task:

```powershell
Start-ScheduledTask -TaskName "Extreme Dashboard - Momentum Weekday Update"
```

## Verify

```powershell
Get-ScheduledTask -TaskName "Extreme Dashboard - Momentum Weekday Update" |
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
