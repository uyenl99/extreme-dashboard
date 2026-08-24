param([switch]$NoPublish)

$ErrorActionPreference = "Stop"

$dualMomUpdate = "C:\junk\stocks\DualMom\update_momo5_daily.ps1"
$dualMomRoot = "C:\junk\stocks\DualMom"
$plotlyDir = Join-Path $dualMomRoot ".python_packages"
$inflationRoot = "C:\junk\stocks\inflationcompass"
$momoSpRoot = "C:\junk\stocks\MomoSp\pit_version"
$momoSpUpdate = Join-Path $momoSpRoot "update_v2a_live.py"
$momoSpOutput = Join-Path $momoSpRoot "output_pit_r1000_5b_latest"
$momoSpAlert = Join-Path $momoSpRoot "output_pit_v2a_live\latest_signal.json"
$webRoot = Split-Path -Parent $PSScriptRoot
$momoSpPreview = Join-Path $webRoot "generate_momentum_stocks_preview.py"
$momoSpGenerator = Join-Path $webRoot "generate_momentum_stocks_page.py"
$momentumEtf2Generator = Join-Path $webRoot "generate_momentum_etf2_page.py"
$python = "C:\Users\uyenl\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$git = "C:\Users\uyenl\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe"
$logRoot = Join-Path $env:LOCALAPPDATA "ExtremeDashboardAutomation\logs"
$privateMemberRoot = Join-Path $webRoot "api\_member-content"
$privateMomentumPage = Join-Path $privateMemberRoot "momentum.html"
$privateMomentumEtf2Page = Join-Path $privateMemberRoot "momentum2.html"
$privateMomentumStocksPage = Join-Path $privateMemberRoot "momentum-stocks.html"
$today = Get-Date -Format "yyyy-MM-dd"
$log = Join-Path $logRoot "momentum-weekday-$today.log"

New-Item -ItemType Directory -Force $logRoot | Out-Null
New-Item -ItemType Directory -Force $privateMemberRoot | Out-Null
Start-Transcript -Path $log -Append
try {
    foreach ($path in @(
        $dualMomUpdate,
        $python,
        $git,
        (Join-Path $inflationRoot "inflation_compass.py"),
        $momoSpUpdate,
        $momoSpPreview,
        $momoSpGenerator,
        $momentumEtf2Generator
    )) {
        if (-not (Test-Path -LiteralPath $path)) { throw "Required path not found: $path" }
    }

    if ($NoPublish) {
        Push-Location $dualMomRoot
        try {
            & $python "refresh_momo5_data.py"
            if ($LASTEXITCODE -ne 0) { throw "Momentum ETF1 data refresh failed." }
            & $python "momo5.py"
            if ($LASTEXITCODE -ne 0) { throw "Momentum ETF1 backtest failed." }
            $publicGeneratorCode = "import runpy,sys; sys.path.insert(0,r'$webRoot'); sys.path.insert(0,r'$plotlyDir'); sys.argv=['generate_momentum_page.py','--source',r'$dualMomRoot\output_momo5','--output',r'$webRoot\momentum.html','--audience','public']; runpy.run_path(r'$webRoot\generate_momentum_page.py',run_name='__main__')"
            & $python -c $publicGeneratorCode
            if ($LASTEXITCODE -ne 0) { throw "Momentum ETF1 public page generation failed." }
            $memberGeneratorCode = "import runpy,sys; sys.path.insert(0,r'$webRoot'); sys.path.insert(0,r'$plotlyDir'); sys.argv=['generate_momentum_page.py','--source',r'$dualMomRoot\output_momo5','--output',r'$privateMomentumPage','--audience','member']; runpy.run_path(r'$webRoot\generate_momentum_page.py',run_name='__main__')"
            & $python -c $memberGeneratorCode
            if ($LASTEXITCODE -ne 0) { throw "Momentum ETF1 member page generation failed." }
            & $python "update_momentum_html_current.py" --source "output_momo5" --html $privateMomentumPage
            if ($LASTEXITCODE -ne 0) { throw "Momentum ETF1 private current-holdings update failed." }
            Write-Host "Private Momentum ETF1 member page: $privateMomentumPage"
        }
        finally { Pop-Location }
    }
    else {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $dualMomUpdate
        if ($LASTEXITCODE -ne 0) { throw "Momentum ETF1 update failed." }
    }

    # Ensure the independent Inflation Compass runtime is reproducible on unattended runs.
    & $python -m pip install -r (Join-Path $inflationRoot "requirements.txt") --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) { throw "Momentum ETF2 dependency install failed." }
    Push-Location $inflationRoot
    try {
        & $python "inflation_compass.py"
        if ($LASTEXITCODE -ne 0) { throw "Momentum ETF2 refresh failed." }
    }
    finally { Pop-Location }

    & $python $momoSpPreview --strategy-root $momoSpRoot
    if ($LASTEXITCODE -ne 0) { throw "Momentum SP preview signal failed." }

    & $python $momentumEtf2Generator `
        --source (Join-Path $inflationRoot "output") `
        --output (Join-Path $webRoot "momentum2.html") `
        --audience public `
        --chart-src "inflation-compass/wealth.png"
    if ($LASTEXITCODE -ne 0) { throw "Momentum ETF2 public page generation failed." }
    & $python $momentumEtf2Generator `
        --source (Join-Path $inflationRoot "output") `
        --output $privateMomentumEtf2Page `
        --audience member `
        --chart-src "inflation-compass/wealth.png"
    if ($LASTEXITCODE -ne 0) { throw "Momentum ETF2 member page generation failed." }
    Write-Host "Private Momentum ETF2 member page: $privateMomentumEtf2Page"

    $assetRoot = Join-Path $webRoot "inflation-compass"
    New-Item -ItemType Directory -Force $assetRoot | Out-Null
    foreach ($name in @("summary.csv", "monthly_pnl_by_year.csv", "wealth.png")) {
        Copy-Item -LiteralPath (Join-Path $inflationRoot "output\$name") -Destination (Join-Path $assetRoot $name) -Force
    }
    foreach ($protectedName in @("latest_alert.json", "last_50_trades.csv")) {
        $publicProtectedPath = Join-Path $assetRoot $protectedName
        if (Test-Path -LiteralPath $publicProtectedPath) {
            Remove-Item -LiteralPath $publicProtectedPath -Force
        }
    }

    & $git -c "safe.directory=$($webRoot.Replace('\', '/'))" -C $webRoot diff --quiet -- inflation-compass
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Momentum ETF2 is current; no site assets changed."
    }
    elseif ($LASTEXITCODE -ne 1) { throw "Could not inspect Momentum ETF2 changes." }

    # Momentum SP: refresh the production V2A data/live signal and rebuild its page.
    Push-Location $momoSpRoot
    try {
        & $python $momoSpUpdate
        if ($LASTEXITCODE -ne 0) { throw "Momentum SP refresh failed." }
    }
    finally { Pop-Location }

    Push-Location $webRoot
    try {
        & $python $momoSpGenerator `
            --source $momoSpOutput `
            --alert-source $momoSpAlert `
            --output (Join-Path $webRoot "momentum-stocks.html") `
            --audience public
        if ($LASTEXITCODE -ne 0) { throw "Momentum SP public page generation failed." }
        & $python $momoSpGenerator `
            --source $momoSpOutput `
            --alert-source $momoSpAlert `
            --output $privateMomentumStocksPage `
            --audience member
        if ($LASTEXITCODE -ne 0) { throw "Momentum SP member page generation failed." }
        Write-Host "Private Momentum Stocks member page: $privateMomentumStocksPage"
    }
    finally { Pop-Location }

    & $git -c "safe.directory=$($webRoot.Replace('\', '/'))" -C $webRoot diff --quiet -- inflation-compass momentum2.html momentum-stocks.html api/_member-content
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Momentum ETF2 and Momentum SP are current; no site changes to publish."
    }
    elseif ($LASTEXITCODE -eq 1 -and -not $NoPublish) {
        & $git -c "safe.directory=$($webRoot.Replace('\', '/'))" -C $webRoot add -- inflation-compass momentum2.html momentum-stocks.html api/_member-content
        & $git -c "safe.directory=$($webRoot.Replace('\', '/'))" -C $webRoot commit -m "Refresh Momentum ETF2 and Momentum Stocks results"
        if ($LASTEXITCODE -ne 0) { throw "Momentum ETF2/Momentum SP commit failed." }
        & $git -c "safe.directory=$($webRoot.Replace('\', '/'))" -C $webRoot push origin HEAD:main
        if ($LASTEXITCODE -ne 0) { throw "Momentum ETF2/Momentum SP publish failed." }
        Write-Host "Momentum ETF2 and Momentum SP published; Vercel production deployment triggered."
    }
    elseif ($LASTEXITCODE -eq 1 -and $NoPublish) {
        Write-Host "Momentum files generated for the shared batch; publishing deferred."
    }
    else { throw "Could not inspect Momentum ETF2/Momentum SP changes." }

    Write-Host "Momentum ETF1, Momentum ETF2, and Momentum SP refreshed."
}
finally { Stop-Transcript }

# Native commands such as `git diff --quiet` use exit code 1 to mean
# "changes found." That result is handled above, but PowerShell otherwise
# returns the stale native exit code to the parent sequential scheduler.
exit 0
