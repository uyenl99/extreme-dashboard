$ErrorActionPreference = "Stop"

$repo = "uyenl99/extreme-dashboard"
$gh = "C:\Program Files\GitHub CLI\gh.exe"
$collective2Workflow = "update-performance.yml"
$collective2Preview = "C:\Users\uyenl\.codex\visualizations\2026\07\19\019f7cb4-9df2-7a73-8c57-98ac4f98c039\open_extreme_os_preview.ps1"
$meanReversionUpdate = "C:\Users\uyenl\.codex\visualizations\2026\07\19\019f7cb4-9df2-7a73-8c57-98ac4f98c039\extreme-os-work\scripts\update_mean_reversion_daily.ps1"
$momentumUpdate = "C:\junk\stocks\Web\scripts\update_momentum_weekdays.ps1"
$logRoot = Join-Path $env:LOCALAPPDATA "ExtremeDashboardAutomation\logs"
$today = Get-Date -Format "yyyy-MM-dd"
$log = Join-Path $logRoot "all-strategies-sequential-$today.log"

New-Item -ItemType Directory -Force $logRoot | Out-Null
foreach ($path in @($gh, $collective2Preview, $meanReversionUpdate, $momentumUpdate)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Required path not found: $path" }
}

function Invoke-Stage {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )
    $started = Get-Date
    Write-Host "`n=== START $Name at $started ==="
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE." }
    $finished = Get-Date
    Write-Host "=== END $Name at $finished (elapsed $($finished - $started)) ==="
}

function Start-And-WaitCollective2 {
    $dispatchTime = [DateTime]::UtcNow
    & $gh workflow run $collective2Workflow --repo $repo --ref main
    if ($LASTEXITCODE -ne 0) { throw "Could not dispatch the Collective2 workflow." }

    $run = $null
    for ($attempt = 1; $attempt -le 30 -and -not $run; $attempt++) {
        Start-Sleep -Seconds 5
        $runs = & $gh run list --repo $repo --workflow $collective2Workflow --event workflow_dispatch --limit 10 `
            --json databaseId,createdAt,status,url | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0) { throw "Could not query the Collective2 workflow run." }
        $run = $runs |
            Where-Object { [DateTime]$_.createdAt -ge $dispatchTime.AddMinutes(-1) } |
            Sort-Object { [DateTime]$_.createdAt } -Descending |
            Select-Object -First 1
    }
    if (-not $run) { throw "Timed out waiting for the dispatched Collective2 workflow to appear." }

    Write-Host "Collective2 workflow: $($run.url)"
    & $gh run watch $run.databaseId --repo $repo --exit-status
    if ($LASTEXITCODE -ne 0) { throw "Collective2 workflow failed." }
}

Start-Transcript -Path $log -Append
try {
    Invoke-Stage "Collective2 refresh" { Start-And-WaitCollective2 }
    Invoke-Stage "Collective2 preview PR" {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $collective2Preview
    }
    Invoke-Stage "Mean Reversion 5x5 backtest" {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $meanReversionUpdate -Mode Backtest
    }
    Invoke-Stage "Momentum ETF1, ETF2, and SP" {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $momentumUpdate
    }
    Write-Host "`nAll scheduled strategy updates completed successfully."
}
finally { Stop-Transcript }
