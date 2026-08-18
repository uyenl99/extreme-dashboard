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
    $dispatchOutput = & $gh workflow run $collective2Workflow --repo $repo --ref main 2>&1
    $dispatchOutput | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) { throw "Could not dispatch the Collective2 workflow." }

    $runUrl = [regex]::Match("$dispatchOutput", 'https://github\.com/[^\s]+/actions/runs/(\d+)')
    if (-not $runUrl.Success) { throw "The Collective2 dispatch did not return a workflow run URL." }
    $runId = $runUrl.Groups[1].Value

    Write-Host "Collective2 workflow: $($runUrl.Value)"
    $conclusion = $null
    for ($attempt = 1; $attempt -le 360; $attempt++) {
        $savedErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $stateJson = & $gh api "repos/$repo/actions/runs/$runId" 2>$null
        $apiExitCode = $LASTEXITCODE
        $ErrorActionPreference = $savedErrorActionPreference
        if ($apiExitCode -ne 0) {
            Write-Host "Collective2 status is not available yet; retrying."
            Start-Sleep -Seconds 5
            continue
        }
        $currentRun = $stateJson | ConvertFrom-Json
        $status = "$($currentRun.status)"
        $conclusion = "$($currentRun.conclusion)"
        Write-Host "Collective2 status: $status $conclusion"
        if ($status -eq "completed") { break }
        Start-Sleep -Seconds 10
    }
    if ($status -ne "completed") { throw "Timed out waiting for the Collective2 workflow to finish." }
    if ($conclusion -ne "success") {
        throw "Collective2 workflow finished with conclusion '$conclusion'."
    }
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
