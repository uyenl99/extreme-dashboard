$ErrorActionPreference = "Stop"

$repoUrl = "https://github.com/uyenl99/extreme-dashboard.git"
$git = "C:\Users\uyenl\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe"
. (Join-Path $PSScriptRoot "automation_paths.ps1")
$workspaceRoot = Get-ExtremeDashboardAutomationWorkspaceRoot
$stateRoot = Get-ExtremeDashboardAutomationStateRoot
$independentRoot = Join-Path $workspaceRoot "independent"
$backupRoot = Join-Path $stateRoot "backup"
$escapedStateRoot = $stateRoot.Replace("'", "''")
$sequentialTask = "Extreme Dashboard - Sequential Strategy Updates"
$cards = @(
    @{ Slug = "extreme-os";       Name = "Extreme OS";       Task = "Extreme Dashboard - Card - Extreme OS";       Time = "1:30 PM" },
    @{ Slug = "mean-reversion";   Name = "Mean Reversion";   Task = "Extreme Dashboard - Card - Mean Reversion";   Time = "1:31 PM" },
    @{ Slug = "momentum-etf1";    Name = "Momentum ETF1";    Task = "Extreme Dashboard - Card - Momentum ETF1";    Time = "1:32 PM" },
    @{ Slug = "momentum-etf2";    Name = "Momentum ETF2";    Task = "Extreme Dashboard - Card - Momentum ETF2";    Time = "1:33 PM" },
    @{ Slug = "momentum-stocks";  Name = "Momentum Stocks";  Task = "Extreme Dashboard - Card - Momentum Stocks";  Time = "1:34 PM" },
    @{ Slug = "haa";              Name = "HAA";              Task = "Extreme Dashboard - Card - HAA";              Time = "1:35 PM" },
    @{ Slug = "combined";         Name = "Combined Portfolio";Task = "Extreme Dashboard - Card - Combined Portfolio";Time = "1:36 PM" }
)

New-Item -ItemType Directory -Force -Path $independentRoot, $stateRoot, $backupRoot | Out-Null

foreach ($card in $cards) {
    $checkout = Join-Path $independentRoot "$($card.Slug)\dashboard"
    if (-not (Test-Path -LiteralPath (Join-Path $checkout ".git"))) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $checkout) | Out-Null
        & $git clone $repoUrl $checkout
        if ($LASTEXITCODE -ne 0) { throw "Could not create the $($card.Name) automation checkout." }
    }
    & $git -C $checkout fetch origin main
    if ($LASTEXITCODE -ne 0) { throw "Could not refresh the $($card.Name) automation checkout." }
    & $git -C $checkout checkout -f -B main origin/main
    if ($LASTEXITCODE -ne 0) { throw "Could not synchronize the $($card.Name) automation checkout." }
    $runner = Join-Path $checkout "scripts\update_strategy_card_independent.ps1"
    $helper = Join-Path $checkout "scripts\strategy_failure_alert.ps1"
    if (-not (Test-Path -LiteralPath $runner)) { throw "Independent runner not found: $runner" }
    if (-not (Test-Path -LiteralPath $helper)) { throw "Failure-alert helper not found: $helper" }

    $cardStatusRoot = Join-Path $stateRoot "cards\$($card.Slug)"
    $bootstrap = @"
`$ErrorActionPreference='Stop'
`$env:EXTREME_DASHBOARD_STATE_ROOT='$escapedStateRoot'
`$bootstrapStarted=Get-Date
try {
    & '$git' -C '$checkout' fetch origin main
    if (`$LASTEXITCODE -ne 0) { throw 'Could not fetch main before the scheduled $($card.Name) update.' }
    & '$git' -C '$checkout' checkout -f -B main origin/main
    if (`$LASTEXITCODE -ne 0) { throw 'Could not synchronize the $($card.Name) automation checkout.' }
}
catch {
    `$failureMessage=`$_.Exception.Message
    `$helper=Join-Path '$checkout' 'scripts\strategy_failure_alert.ps1'
    if (Test-Path -LiteralPath `$helper) {
        try {
            . `$helper
            Publish-StrategyFailureAlert -Stage '$($card.Name) - Automation bootstrap' -FailureMessage `$failureMessage -LogPath '' -PullRequestUrl '' -RunStarted `$bootstrapStarted -StatusRoot '$cardStatusRoot' | Out-Null
        }
        catch { Write-Warning "Could not publish the $($card.Name) bootstrap failure alert: `$(`$_.Exception.Message)" }
    }
    exit 1
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File '$runner' -Card '$($card.Slug)'
exit `$LASTEXITCODE
"@.Trim()
    $encodedBootstrap = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($bootstrap))
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -EncodedCommand $encodedBootstrap"
    $trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At $card.Time
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 8) -MultipleInstances IgnoreNew
    $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
    $description = "$($card.Name) updates independently. A failure alerts the user and does not block the next strategy card. Publishing is serialized and requires Vercel and production deployment checks."
    Register-ScheduledTask -TaskName $card.Task -Action $action -Trigger $trigger -Settings $settings `
        -Principal $principal -Description $description -Force | Out-Null
    Disable-ScheduledTask -TaskName $card.Task | Out-Null
    Write-Host "Registered '$($card.Task)' for weekdays at $($card.Time); activation deferred until every task is ready."
}

$oldTask = Get-ScheduledTask -TaskName $sequentialTask -ErrorAction SilentlyContinue
if ($oldTask) {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupPath = Join-Path $backupRoot "sequential-task-$timestamp.xml"
    Export-ScheduledTask -TaskName $sequentialTask | Set-Content -LiteralPath $backupPath -Encoding Unicode
    if (-not (Test-Path -LiteralPath $backupPath)) { throw "Could not preserve the sequential task XML." }
    Disable-ScheduledTask -TaskName $sequentialTask | Out-Null
    Write-Host "Preserved and disabled '$sequentialTask'. XML backup: $backupPath"
}
else {
    Write-Warning "The prior sequential task was not found. The new independent tasks were registered without changing a backup task."
}

foreach ($card in $cards) {
    Enable-ScheduledTask -TaskName $card.Task | Out-Null
    Write-Host "Activated '$($card.Task)'."
}

Write-Host "Independent card automation is active. Use scripts\restore_sequential_strategy_task.ps1 to roll back."
