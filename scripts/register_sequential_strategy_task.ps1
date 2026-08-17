$ErrorActionPreference = "Stop"

$taskName = "Extreme Dashboard - Sequential Strategy Updates"
$updateScript = "C:\junk\stocks\Web\scripts\update_all_strategies_sequentially.ps1"
$retiredTasks = @(
    "Extreme Dashboard - Mean Reversion 5x5 Backtest",
    "Extreme Dashboard - Momentum Weekday Update",
    "Extreme Dashboard - Open Extreme OS Preview PR"
)

if (-not (Test-Path -LiteralPath $updateScript)) { throw "Update script not found: $updateScript" }

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$updateScript`""
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At "3:00 PM"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 8) `
    -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal `
    -Description "Sequential weekday refresh: Collective2, Mean Reversion backtest, Momentum ETF1/ETF2/SP. Live alerts remain at 12:30 PM." `
    -Force | Out-Null

foreach ($oldTask in $retiredTasks) {
    if (Get-ScheduledTask -TaskName $oldTask -ErrorAction SilentlyContinue) {
        Disable-ScheduledTask -TaskName $oldTask | Out-Null
        Write-Host "Disabled superseded task: $oldTask"
    }
}

Write-Host "Registered '$taskName' for weekdays at 3:00 PM local time."
