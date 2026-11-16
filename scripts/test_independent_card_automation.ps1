$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$files = @(
    "scripts\update_strategy_card_independent.ps1",
    "scripts\update_momentum_card.ps1",
    "scripts\register_independent_card_tasks.ps1",
    "scripts\restore_sequential_strategy_task.ps1"
)

foreach ($relative in $files) {
    $path = Join-Path $root $relative
    $tokens = $null
    $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$tokens, [ref]$errors)
    if ($errors.Count) { throw "$relative has PowerShell syntax errors: $($errors.Message -join '; ')" }
}

$runner = Get-Content -LiteralPath (Join-Path $root "scripts\update_strategy_card_independent.ps1") -Raw
$registration = Get-Content -LiteralPath (Join-Path $root "scripts\register_independent_card_tasks.ps1") -Raw
$restore = Get-Content -LiteralPath (Join-Path $root "scripts\restore_sequential_strategy_task.ps1") -Raw
$cards = @("extreme-os", "mean-reversion", "momentum-etf1", "momentum-etf2", "momentum-stocks", "haa", "combined")
foreach ($card in $cards) {
    if ($runner -notmatch [regex]::Escape("`"$card`"")) { throw "Independent runner is missing card: $card" }
    if ($registration -notmatch [regex]::Escape("Slug = `"$card`"")) { throw "Registration is missing card: $card" }
}
$expectedTimes = @("1:30 PM", "1:31 PM", "1:32 PM", "1:33 PM", "1:34 PM", "1:35 PM", "1:36 PM")
foreach ($time in $expectedTimes) {
    if ($registration -notmatch [regex]::Escape("Time = `"$time`"")) { throw "Registration is missing schedule time: $time" }
}
if ($registration -match 'Time = "3:0[0-5] PM"' -or $registration -match 'Time = "7:00 PM"' -or $registration -match 'Time = "5:30 PM"') {
    throw "Registration still contains a retired fixed-delay schedule."
}

$branches = [regex]::Matches($runner, 'Branch = "(automation/card-[^"]+)"') | ForEach-Object { $_.Groups[1].Value }
if ($branches.Count -ne $cards.Count) { throw "Expected one publication branch per card; found $($branches.Count)." }
if (($branches | Sort-Object -Unique).Count -ne $branches.Count) { throw "Independent card branches must be unique." }
if ($registration -notmatch 'Export-ScheduledTask' -or $registration -notmatch 'Disable-ScheduledTask -TaskName \$sequentialTask') {
    throw "Registration must export and disable the sequential backup task."
}
if ($registration -notmatch 'Disable-ScheduledTask -TaskName \$card.Task' -or $registration -notmatch 'Enable-ScheduledTask -TaskName \$card.Task') {
    throw "New tasks must stay disabled until every independent task is ready."
}
if ($registration -match 'Unregister-ScheduledTask') { throw "Registration must not delete the sequential backup task." }
if ($restore -notmatch 'Enable-ScheduledTask -TaskName \$sequentialTask') { throw "Rollback script must re-enable the sequential task." }
if ($runner -notmatch 'System\.Threading\.Mutex' -or $runner -notmatch 'Test-CombinedInputsCurrent' -or $runner -notmatch 'Wait-ForCombinedInputsCurrent') {
    throw "Independent publishing must be serialized and Combined Portfolio must require fresh card inputs."
}
$waitPosition = $runner.IndexOf('Wait-ForCombinedInputsCurrent)')
$mutexPosition = $runner.IndexOf('New-Object System.Threading.Mutex')
if ($waitPosition -lt 0 -or $mutexPosition -lt 0 -or $waitPosition -gt $mutexPosition) {
    throw "Combined Portfolio must wait for source cards before acquiring the publication mutex."
}
if ($runner -notmatch 'Wait-ForVercelProduction' -or $runner -notmatch 'Resolve-CardFailureAlertIfPresent' -or $runner -notmatch 'Show-CardSuccessNotification') {
    throw "Each card must verify Vercel production, resolve only its own failure alert, and report success."
}

Write-Host "Independent card automation contract checks passed."
