param(
    [ValidateSet("Alerts", "Backtest")]
    [string]$Mode = "Alerts"
)

$ErrorActionPreference = "Stop"

$revMurphyRoot = "C:\junk\stocks\RevMurphy"
$backtestOutput = Join-Path $revMurphyRoot "output_long_short_5x5"
$alertOutput = Join-Path $revMurphyRoot "output_live_alerts_5x5"
$automationRoot = Join-Path $env:LOCALAPPDATA "ExtremeDashboardAutomation"
$checkout = Join-Path $automationRoot "extreme-dashboard"
$logDirectory = Join-Path $automationRoot "logs"
$python = Join-Path $revMurphyRoot ".venv\Scripts\python.exe"
$git = "C:\Users\uyenl\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe"
$gh = "C:\Program Files\GitHub CLI\gh.exe"
$previewBranch = "automation/mean-reversion-daily-preview"
$today = Get-Date -Format "yyyy-MM-dd"
$modeTag = $Mode.ToLowerInvariant()
$log = Join-Path $logDirectory "mean-reversion-$modeTag-$today.log"
$commandLog = Join-Path $logDirectory "mean-reversion-$modeTag-$today-commands.log"

New-Item -ItemType Directory -Force -Path $automationRoot, $logDirectory | Out-Null
Start-Transcript -Path $log -Append

try {
    if (-not (Test-Path $python)) { throw "Python runtime not found: $python" }
    if (-not (Test-Path $git)) { throw "Git executable not found: $git" }
    if (-not (Test-Path $gh)) { throw "GitHub CLI not found: $gh" }
    if (-not $env:POLYGON_API_KEY) {
        throw "POLYGON_API_KEY is not available to the scheduled task user."
    }

    if (-not (Test-Path (Join-Path $checkout ".git"))) {
        & $git clone "https://github.com/uyenl99/extreme-dashboard.git" $checkout
        if ($LASTEXITCODE -ne 0) { throw "Initial dashboard clone failed." }
    }

    & $git -C $checkout fetch origin main
    if ($LASTEXITCODE -ne 0) { throw "Could not fetch main." }
    & $git -C $checkout ls-remote --exit-code --heads origin $previewBranch | Out-Null
    if ($LASTEXITCODE -eq 0) {
        & $git -C $checkout fetch origin "+refs/heads/$previewBranch`:refs/remotes/origin/$previewBranch"
        if ($LASTEXITCODE -ne 0) { throw "Could not refresh the daily preview branch lease." }
    }
    elseif ($LASTEXITCODE -eq 2) {
        & $git -C $checkout update-ref -d "refs/remotes/origin/$previewBranch"
        Write-Output "Daily preview branch does not exist yet; it will be created from main."
    }
    else {
        throw "Could not query the daily preview branch."
    }
    & $git -C $checkout reset --hard origin/main
    if ($LASTEXITCODE -ne 0) { throw "Could not clean the disposable automation checkout." }
    & $git -C $checkout checkout -B $previewBranch origin/main
    if ($LASTEXITCODE -ne 0) { throw "Could not reset the daily preview branch." }

    Push-Location $revMurphyRoot
    try {
        if ($Mode -eq "Alerts") {
            & $python "live_alerts_optimized.py" --minute-workers 4 --mode "long_short" --date $today --output-dir $alertOutput --portfolio-trades (Join-Path $backtestOutput "trades.csv") --refresh --cutoff "15:30" --max-tickers 0 --long-positions 5 --short-positions 5 2>&1 | Tee-Object -FilePath $commandLog -Append
            if ($LASTEXITCODE -ne 0) { throw "Mean Reversion live-alert refresh failed." }
        }
        else {
            & $python "main_long_short.py" --end $today --output-dir $backtestOutput --no-force-final-exit --max-tickers 0 --long-positions 5 --short-positions 5 2>&1 | Tee-Object -FilePath $commandLog -Append
            if ($LASTEXITCODE -ne 0) { throw "Mean Reversion 5x5 backtest refresh failed." }
        }
    }
    finally { Pop-Location }

    Push-Location $checkout
    try {
        & $python "generate_mean_reversion_page.py" --source $backtestOutput --alert-source $alertOutput 2>&1 | Tee-Object -FilePath $commandLog -Append
        if ($LASTEXITCODE -ne 0) { throw "Mean Reversion page generation failed." }

        & $git add -- mean-reversion.html strategies.html
        & $git diff --cached --quiet
        if ($LASTEXITCODE -eq 0) {
            Write-Output "No Mean Reversion website changes to publish."
            return
        }

        & $git config user.name "Extreme Dashboard Automation"
        & $git config user.email "uyenl99@users.noreply.github.com"
        & $git commit -m "Update Mean Reversion $modeTag $today"
        if ($LASTEXITCODE -ne 0) { throw "Automated commit failed." }
        & $git push --force-with-lease -u origin $previewBranch
        if ($LASTEXITCODE -ne 0) { throw "Could not push the daily preview branch." }

        $prUrl = & $gh pr list --repo "uyenl99/extreme-dashboard" --head $previewBranch --state open --json url --jq ".[0].url"
        if ($LASTEXITCODE -ne 0) { throw "Could not query the daily preview pull request." }
        if (-not $prUrl) {
            $prUrl = & $gh pr create --repo "uyenl99/extreme-dashboard" --draft --base main --head $previewBranch --title "Daily Mean Reversion preview" --body "Automated Mean Reversion refresh for $today. Review the Vercel preview before merging."
            if ($LASTEXITCODE -ne 0) { throw "Could not create the daily preview pull request." }
        }
        Write-Output "Daily preview PR: $prUrl"
    }
    finally { Pop-Location }
}
finally { Stop-Transcript }
