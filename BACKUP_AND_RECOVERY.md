# Backup and recovery plan

Last verified: 2026-11-17 (America/Los_Angeles)

## Protected project folders

The following folders are explicitly selected for continuous Carbonite backup:

- `C:\junk\stocks\Web`
- `C:\junk\stocks\RevMurphy`
- `C:\junk\stocks\MomoSp`
- `C:\junk\stocks\DualMom`
- `C:\junk\stocks\inflationcompass`
- `C:\junk\stocks\HAA`
- `C:\junk\stocks\shared_data`

Carbonite showed **0 files waiting to back up** at the time of verification. Each folder's File Explorer context menu showed **Exclude from Carbonite backup**, confirming that the folder is currently included.

## Other recovery sources

- Dashboard website and automation definitions: `https://github.com/uyenl99/extreme-dashboard`
- Production deployment: Vercel rebuilds from the GitHub repository.
- Local strategy engines and their generated data: Carbonite is the primary off-computer backup unless a separate Git remote is added later.

Do not treat `%LOCALAPPDATA%\ExtremeDashboardAutomation\independent` as a primary backup. Those directories are disposable coordinator clones and should be recreated from GitHub after recovery.

## Automatic update scripts and schedules

The current independent-card automation source is stored in GitHub `main` and is also covered by Carbonite as part of the `Web` folder. The key recovery files are:

- `scripts/automation_paths.ps1`
- `scripts/register_independent_card_tasks.ps1`
- `scripts/update_strategy_card_independent.ps1`
- `scripts/strategy_failure_alert.ps1`
- `scripts/restore_sequential_strategy_task.ps1`

The active Windows Task Scheduler entries run on weekdays:

| Time (Pacific) | Task |
| --- | --- |
| 1:30 PM | Extreme OS |
| 1:31 PM | Mean Reversion |
| 1:32 PM | Momentum ETF1 |
| 1:33 PM | Momentum ETF2 |
| 1:34 PM | Momentum Stocks |
| 1:35 PM | HAA |
| 1:36 PM | Combined Portfolio |

The older **Extreme Dashboard - Sequential Strategy Updates** task is retained as a disabled rollback option. The seven independent tasks were verified as Ready with a last result of `0` on 2026-11-17.

Task Scheduler registrations are Windows machine state; they are not restored merely by cloning the repository. After restoring the projects, open an ordinary PowerShell window and run the registration script from the latest dashboard checkout:

```powershell
Set-Location C:\junk\stocks\Web
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\register_independent_card_tasks.ps1
```

The registration script creates fresh automation checkouts under `%LOCALAPPDATA%\ExtremeDashboardAutomation\independent`. These checkouts are disposable. Durable runtime state is stored under `C:\junk\stocks\Web\.automation-state`, which Carbonite protects as part of the `Web` project folder and Git ignores.

To copy legacy durable state without moving or deleting the old files, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\migrate_automation_state.ps1
```

### Automation storage layout

Do not back up the entire `%LOCALAPPDATA%\ExtremeDashboardAutomation` folder. It currently contains roughly 740 MB, primarily duplicate Git checkouts that the registration script recreates:

- `independent` — seven disposable Git checkouts; recreate from GitHub.
- `extreme-dashboard` and `sequential-dashboard` — obsolete/rollback checkouts; recreate only if specifically needed.

New durable automation files belong under `C:\junk\stocks\Web\.automation-state`:

- `member-pages` — generated member HTML used during publication.
- `cards` and `last-run-status.json` — current run status and failure-alert history.
- `logs` — diagnostic run history.
- `backup` — XML exports of the retired sequential scheduled task.

GitHub CLI authentication, API credentials, and Windows Task Scheduler registrations are not recovered from either runtime folder. Before re-registering after a new Windows installation, install and authenticate GitHub CLI, install Git, install Python, and verify the executable paths near the top of the registration and updater scripts. Authentication tokens and API credentials must be restored separately from a password manager or re-created at their service; they should not be committed to GitHub.

## Restore order after a disk failure

1. Install Git for Windows and Python.
2. Clone `uyenl99/extreme-dashboard` into `C:\junk\stocks\Web`.
3. Install Carbonite and restore the six strategy/data folders beside `Web`, including `Web\.automation-state`.
4. Recreate Python virtual environments and reinstall dependencies; do not depend on restored virtual-environment or cache folders.
5. Recreate any required environment variables or secret files from the password manager or service dashboards.
6. Run each strategy locally once and confirm its expected output files are produced.
7. Run `scripts\register_independent_card_tasks.ps1` to recreate the seven Windows scheduled tasks and disposable automation checkouts.
8. Confirm the next update creates the expected GitHub pull request and Vercel preview before restoring the normal schedule.

## Monthly verification

1. Confirm Carbonite says the backup is current and shows 0 failed or waiting files.
2. Right-click each protected folder and confirm the Carbonite menu says **Exclude from Carbonite backup** (which means it is included).
3. Confirm recent source and output files have current modification dates.
4. Confirm the GitHub default branch contains the latest dashboard and workflow changes.
5. Perform a small test restore of one harmless file to a temporary folder, then delete the temporary restored copy.

## Important limitation

Carbonite and GitHub serve different purposes. GitHub preserves the dashboard's version history; Carbonite preserves the local strategy engines and data. The local-only strategy folders should eventually also be placed in private Git repositories (excluding secrets, caches, virtual environments, and large generated data) to provide version history in addition to file recovery.
