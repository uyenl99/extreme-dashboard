$ErrorActionPreference = "Stop"

$helper = Join-Path $PSScriptRoot "strategy_failure_alert.ps1"
. $helper

$testRoot = Join-Path ([IO.Path]::GetTempPath()) ("strategy-failure-alert-test-" + [guid]::NewGuid())
$desktop = Join-Path $testRoot "Desktop"
New-Item -ItemType Directory -Force -Path $desktop | Out-Null

try {
    $started = Get-Date "2026-11-15 15:00:00"
    $result = Publish-StrategyFailureAlert `
        -Stage "Mean Reversion" `
        -FailureMessage "Request failed token=do-not-store" `
        -LogPath "C:\logs\daily.log" `
        -PullRequestUrl "" `
        -RunStarted $started `
        -StatusRoot $testRoot `
        -DesktopDirectory $desktop `
        -SkipInteractiveNotification

    if (-not (Test-Path -LiteralPath $result.record_path)) {
        throw "Failure alert JSON was not created."
    }
    if (-not (Test-Path -LiteralPath $result.desktop_alert_path)) {
        throw "Desktop failure alert was not created."
    }

    $record = Get-Content -LiteralPath $result.record_path -Raw | ConvertFrom-Json
    if ($record.status -ne "Failed" -or $record.stage -ne "Mean Reversion") {
        throw "Failure alert JSON has incorrect terminal status data."
    }
    if ($record.message -match "do-not-store") {
        throw "Failure alert did not redact a token."
    }
    if ($record.production_updated -ne $false) {
        throw "Failure alert did not mark production as unchanged."
    }

    Resolve-StrategyFailureAlert -SuccessMessage "Retry published successfully." -DesktopDirectory $desktop | Out-Null
    $desktopText = Get-Content -LiteralPath $result.desktop_alert_path -Raw
    if ($desktopText -notmatch "RESOLVED" -or $desktopText -notmatch "Retry published successfully") {
        throw "Same-day success did not resolve the persistent Desktop alert."
    }

    Write-Host "PASS: failure JSON, persistent Desktop alert, secret redaction, and resolution marker"
}
finally {
    $fullTestRoot = [IO.Path]::GetFullPath($testRoot)
    $fullTempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if ($fullTestRoot.StartsWith($fullTempRoot, [StringComparison]::OrdinalIgnoreCase)) {
        [IO.Directory]::Delete($fullTestRoot, $true)
    }
}
