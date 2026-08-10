$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stocksRoot = Split-Path -Parent $repoRoot
$revMurphyRoot = Join-Path $stocksRoot "RevMurphy"
$backtestOutput = Join-Path $revMurphyRoot "output_long_short_live"
$alertOutput = Join-Path $revMurphyRoot "output_live_alerts"
$automationRoot = Join-Path $env:LOCALAPPDATA "ExtremeDashboardAutomation"
$checkout = Join-Path $automationRoot "extreme-dashboard"
$logDirectory = Join-Path $automationRoot "logs"
$python = "C:\Users\uyenl\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$git = "C:\Users\uyenl\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe"
$today = Get-Date -Format "yyyy-MM-dd"
$log = Join-Path $logDirectory "mean-reversion-$today.log"

New-Item -ItemType Directory -Force -Path $automationRoot, $logDirectory | Out-Null
Start-Transcript -Path $log -Append

try {
    if (-not (Test-Path $python)) { throw "Python runtime not found: $python" }
    if (-not (Test-Path $git)) { throw "Git executable not found: $git" }
    if (-not $env:POLYGON_API_KEY) {
        throw "POLYGON_API_KEY is not available to the scheduled task user."
    }

    if (-not (Test-Path (Join-Path $checkout ".git"))) {
        & $git clone "https://github.com/uyenl99/extreme-dashboard.git" $checkout
        if ($LASTEXITCODE -ne 0) { throw "Initial dashboard clone failed." }
    }

    & $git -C $checkout checkout main
    if ($LASTEXITCODE -ne 0) { throw "Could not check out main." }
    & $git -C $checkout pull --ff-only origin main
    if ($LASTEXITCODE -ne 0) { throw "Could not update the automation checkout." }

    & $python -m pip install -r (Join-Path $checkout "requirements.txt") -r (Join-Path $revMurphyRoot "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

    Push-Location $revMurphyRoot
    try {
        & $python "main_long_short.py" --end $today --output-dir $backtestOutput --no-force-final-exit
        if ($LASTEXITCODE -ne 0) { throw "Mean Reversion backtest refresh failed." }
        & $python "live_alerts.py" --date $today --output-dir $alertOutput --refresh --cutoff "15:30"
        if ($LASTEXITCODE -ne 0) { throw "Mean Reversion live-alert refresh failed." }
    }
    finally { Pop-Location }

    Push-Location $checkout
    try {
        & $python "generate_mean_reversion_page.py" --source $backtestOutput --alert-source $alertOutput
        if ($LASTEXITCODE -ne 0) { throw "Mean Reversion page generation failed." }

        & $git add -- mean-reversion.html strategies.html
        & $git diff --cached --quiet
        if ($LASTEXITCODE -eq 0) {
            Write-Output "No Mean Reversion website changes to publish."
            return
        }

        & $git config user.name "Extreme Dashboard Automation"
        & $git config user.email "uyenl99@users.noreply.github.com"
        & $git commit -m "Update Mean Reversion results $today"
        if ($LASTEXITCODE -ne 0) { throw "Automated commit failed." }
        & $git pull --rebase origin main
        if ($LASTEXITCODE -ne 0) { throw "Could not rebase the automated update." }
        & $git push origin main
        if ($LASTEXITCODE -ne 0) { throw "Could not push the automated update." }
    }
    finally { Pop-Location }
}
finally { Stop-Transcript }
