$ErrorActionPreference = "Stop"

$taskName = "Extreme Dashboard - Sequential Strategy Updates"
$git = "C:\Users\uyenl\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe"
. (Join-Path $PSScriptRoot "automation_paths.ps1")
$workspaceRoot = Get-ExtremeDashboardAutomationWorkspaceRoot
$stateRoot = Get-ExtremeDashboardAutomationStateRoot
$escapedStateRoot = $stateRoot.Replace("'", "''")
$automationCheckout = Join-Path $workspaceRoot "sequential-dashboard"
$updateScript = Join-Path $automationCheckout "scripts\update_all_strategies_sequentially.ps1"
$retiredTasks = @(
    "Extreme Dashboard - Mean Reversion 5x5 Backtest",
    "Extreme Dashboard - Momentum Weekday Update",
    "Extreme Dashboard - Open Extreme OS Preview PR"
)

if (-not (Test-Path -LiteralPath (Join-Path $automationCheckout ".git"))) {
    & $git clone "https://github.com/uyenl99/extreme-dashboard.git" $automationCheckout
    if ($LASTEXITCODE -ne 0) { throw "Could not create the clean sequential automation checkout." }
}
& $git -C $automationCheckout fetch origin main
if ($LASTEXITCODE -ne 0) { throw "Could not refresh the sequential automation checkout." }
& $git -C $automationCheckout checkout -f -B main origin/main
if ($LASTEXITCODE -ne 0) { throw "Could not synchronize the sequential automation checkout." }
if (-not (Test-Path -LiteralPath $updateScript)) { throw "Update script not found: $updateScript" }

$bootstrap = @"
`$ErrorActionPreference='Stop'
`$env:EXTREME_DASHBOARD_STATE_ROOT='$escapedStateRoot'
`$bootstrapStarted=Get-Date
try {
    & '$git' -C '$automationCheckout' fetch origin main
    if (`$LASTEXITCODE -ne 0) { throw 'Could not fetch main before the scheduled dashboard update.' }
    & '$git' -C '$automationCheckout' checkout -f -B main origin/main
    if (`$LASTEXITCODE -ne 0) { throw 'Could not synchronize the automation checkout before the scheduled dashboard update.' }
}
catch {
    `$failureMessage=`$_.Exception.Message
    `$helper=Join-Path '$automationCheckout' 'scripts\strategy_failure_alert.ps1'
    if (Test-Path -LiteralPath `$helper) {
        try {
            . `$helper
            Publish-StrategyFailureAlert -Stage 'Automation bootstrap' -FailureMessage `$failureMessage -LogPath '' -PullRequestUrl '' -RunStarted `$bootstrapStarted -StatusRoot '$escapedStateRoot' | Out-Null
        }
        catch { Write-Warning "Could not publish the bootstrap failure alert: `$(`$_.Exception.Message)" }
    }
    exit 1
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File '$updateScript'
exit `$LASTEXITCODE
"@.Trim()
$encodedBootstrap = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($bootstrap))
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -EncodedCommand $encodedBootstrap"
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At "3:00 PM"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 8) `
    -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal `
    -Description "Six sequential jobs (including HAA) publish after Vercel preview checks pass. Mean Reversion live alerts publish separately at 12:30 PM." `
    -Force | Out-Null

foreach ($oldTask in $retiredTasks) {
    if (Get-ScheduledTask -TaskName $oldTask -ErrorAction SilentlyContinue) {
        Disable-ScheduledTask -TaskName $oldTask | Out-Null
        Write-Host "Disabled superseded task: $oldTask"
    }
}

Write-Host "Registered '$taskName' for weekdays at 3:00 PM local time."
