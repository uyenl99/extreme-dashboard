$ErrorActionPreference = "Stop"
$taskName = "Extreme Dashboard - Momentum Weekday Update"
$updateScript = "C:\junk\stocks\Web\scripts\update_momentum_weekdays.ps1"
if (-not (Test-Path -LiteralPath $updateScript)) { throw "Update script not found: $updateScript" }

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$updateScript`""
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At "4:00 PM"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Refresh and publish Momentum ETF1 and Momentum ETF2 every weekday at 4 PM Pacific." -Force
Write-Host "Registered '$taskName' for weekdays at 4:00 PM local time."
