$ErrorActionPreference = "Stop"

$dualMomUpdate = "C:\junk\stocks\DualMom\update_momo5_daily.ps1"
$inflationRoot = "C:\junk\stocks\inflationcompass"
$webRoot = "C:\junk\stocks\Web"
$python = "C:\Users\uyenl\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$git = "C:\Users\uyenl\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe"
$logRoot = Join-Path $env:LOCALAPPDATA "ExtremeDashboardAutomation\logs"
$today = Get-Date -Format "yyyy-MM-dd"
$log = Join-Path $logRoot "momentum-weekday-$today.log"

New-Item -ItemType Directory -Force $logRoot | Out-Null
Start-Transcript -Path $log -Append
try {
    foreach ($path in @($dualMomUpdate, $python, $git, (Join-Path $inflationRoot "inflation_compass.py"))) {
        if (-not (Test-Path -LiteralPath $path)) { throw "Required path not found: $path" }
    }

    # Momentum ETF1: refresh data, rebuild momentum.html, commit and publish if changed.
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $dualMomUpdate
    if ($LASTEXITCODE -ne 0) { throw "Momentum ETF1 update failed." }

    # Ensure the independent Inflation Compass runtime is reproducible on unattended runs.
    & $python -m pip install -r (Join-Path $inflationRoot "requirements.txt") --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) { throw "Momentum ETF2 dependency install failed." }
    Push-Location $inflationRoot
    try {
        & $python "inflation_compass.py"
        if ($LASTEXITCODE -ne 0) { throw "Momentum ETF2 refresh failed." }
    }
    finally { Pop-Location }

    $assetRoot = Join-Path $webRoot "inflation-compass"
    New-Item -ItemType Directory -Force $assetRoot | Out-Null
    foreach ($name in @("summary.csv", "monthly_pnl_by_year.csv", "latest_alert.json", "wealth.png", "last_50_trades.csv")) {
        Copy-Item -LiteralPath (Join-Path $inflationRoot "output\$name") -Destination (Join-Path $assetRoot $name) -Force
    }

    & $git -c "safe.directory=C:/junk/stocks/Web" -C $webRoot diff --quiet -- inflation-compass
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Momentum ETF2 is current; no site assets changed."
        return
    }
    if ($LASTEXITCODE -ne 1) { throw "Could not inspect Momentum ETF2 changes." }

    & $git -c "safe.directory=C:/junk/stocks/Web" -C $webRoot add -- inflation-compass
    & $git -c "safe.directory=C:/junk/stocks/Web" -C $webRoot commit -m "Refresh Momentum ETF2 results"
    if ($LASTEXITCODE -ne 0) { throw "Momentum ETF2 commit failed." }
    & $git -c "safe.directory=C:/junk/stocks/Web" -C $webRoot push origin HEAD:main
    if ($LASTEXITCODE -ne 0) { throw "Momentum ETF2 publish failed." }
    Write-Host "Momentum ETF1 and Momentum ETF2 refreshed; Vercel production deployment triggered."
}
finally { Stop-Transcript }
