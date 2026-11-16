$ErrorActionPreference = "Stop"

$sequentialTask = "Extreme Dashboard - Sequential Strategy Updates"
$independentTasks = @(
    "Extreme Dashboard - Card - Extreme OS",
    "Extreme Dashboard - Card - Mean Reversion",
    "Extreme Dashboard - Card - Momentum ETF1",
    "Extreme Dashboard - Card - Momentum ETF2",
    "Extreme Dashboard - Card - Momentum Stocks",
    "Extreme Dashboard - Card - HAA",
    "Extreme Dashboard - Card - Combined Portfolio"
)

$oldTask = Get-ScheduledTask -TaskName $sequentialTask -ErrorAction SilentlyContinue
if (-not $oldTask) {
    throw "The preserved sequential task '$sequentialTask' was not found. Re-import its saved XML before rolling back."
}

foreach ($taskName in $independentTasks) {
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
        Disable-ScheduledTask -TaskName $taskName | Out-Null
        Write-Host "Disabled '$taskName'."
    }
}

Enable-ScheduledTask -TaskName $sequentialTask | Out-Null
Write-Host "Restored '$sequentialTask'. The independent tasks remain installed but disabled."
