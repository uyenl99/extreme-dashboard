param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("extreme-os", "mean-reversion", "momentum-etf1", "momentum-etf2", "momentum-stocks", "haa", "combined")]
    [string]$Card
)

$ErrorActionPreference = "Stop"

$repo = "uyenl99/extreme-dashboard"
$gh = "C:\Program Files\GitHub CLI\gh.exe"
$git = "C:\Users\uyenl\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe"
$python = "C:\Users\uyenl\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$webRoot = Split-Path -Parent $PSScriptRoot
$automationRoot = Join-Path $env:LOCALAPPDATA "ExtremeDashboardAutomation"
$statusRoot = Join-Path $automationRoot "cards\$Card"
$statusFile = Join-Path $statusRoot "last-run-status.json"
$logRoot = Join-Path $automationRoot "logs\cards"
$today = Get-Date -Format "yyyy-MM-dd"
$log = Join-Path $logRoot "$Card-$today.log"
$productionUrl = "https://uyenl99.github.io/extreme-dashboard/index.html"
$runStarted = Get-Date
$currentStage = "Initialization"
$prUrl = $null
$failureAlertPath = $null
$transcriptStarted = $false
$mutex = $null
$hasMutex = $false

$configurations = @{
    "extreme-os" = @{
        Name = "Extreme OS"
        Branch = "automation/card-extreme-os-daily"
        Files = @("data/performance_summary.json", "performance-details.html", "extreme-os.html", "members.html", "api/_member-content/extreme-os.html")
        Patterns = @('^data/performance_summary\.json$', '^performance-details\.html$', '^extreme-os\.html$', '^members\.html$', '^api/_member-content/extreme-os\.html$')
    }
    "mean-reversion" = @{
        Name = "Mean Reversion"
        Branch = "automation/card-mean-reversion-daily"
        Files = @("mean-reversion.html", "strategies.html", "members.html", "api/_member-content/mean-reversion.html")
        Patterns = @('^mean-reversion\.html$', '^strategies\.html$', '^members\.html$', '^api/_member-content/mean-reversion\.html$')
    }
    "momentum-etf1" = @{
        Name = "Momentum ETF1"
        Branch = "automation/card-momentum-etf1-daily"
        Files = @("momentum.html", "strategies.html", "members.html", "api/_member-content/momentum.html")
        Patterns = @('^momentum\.html$', '^strategies\.html$', '^members\.html$', '^api/_member-content/momentum\.html$')
    }
    "momentum-etf2" = @{
        Name = "Momentum ETF2"
        Branch = "automation/card-momentum-etf2-daily"
        Files = @("momentum2.html", "strategies.html", "members.html", "api/_member-content/momentum2.html", "inflation-compass")
        Patterns = @('^momentum2\.html$', '^strategies\.html$', '^members\.html$', '^api/_member-content/momentum2\.html$', '^inflation-compass/(monthly_pnl_by_year\.csv|summary\.csv|wealth\.png)$')
    }
    "momentum-stocks" = @{
        Name = "Momentum Stocks"
        Branch = "automation/card-momentum-stocks-daily"
        Files = @("momentum-stocks.html", "strategies.html", "members.html", "api/_member-content/momentum-stocks.html")
        Patterns = @('^momentum-stocks\.html$', '^strategies\.html$', '^members\.html$', '^api/_member-content/momentum-stocks\.html$')
    }
    "haa" = @{
        Name = "HAA"
        Branch = "automation/card-haa-daily"
        Files = @("haa.html", "strategies.html", "members.html", "api/_member-content/haa.html", "data/haa")
        Patterns = @('^haa\.html$', '^strategies\.html$', '^members\.html$', '^api/_member-content/haa\.html$', '^data/haa/[a-zA-Z0-9_]+\.(csv|json)$')
    }
    "combined" = @{
        Name = "Combined Portfolio"
        Branch = "automation/card-combined-portfolio-daily"
        Files = @("combined-portfolio.html", "strategies.html", "members.html")
        Patterns = @('^combined-portfolio\.html$', '^strategies\.html$', '^members\.html$')
    }
}
$configuration = $configurations[$Card]
$previewBranch = $configuration.Branch
$cardName = $configuration.Name

New-Item -ItemType Directory -Force -Path $statusRoot, $logRoot | Out-Null
. (Join-Path $PSScriptRoot "strategy_failure_alert.ps1")

function Write-CardStatus {
    param(
        [ValidateSet("Running", "Succeeded", "Failed", "Skipped")][string]$Status,
        [string]$Stage,
        [string]$Message,
        [string]$PullRequestUrl
    )
    try {
        $payload = [ordered]@{
            card = $Card
            card_name = $cardName
            status = $Status
            stage = $Stage
            message = $Message
            started_at = $runStarted.ToString("o")
            updated_at = (Get-Date).ToString("o")
            log_path = $log
            pull_request_url = $PullRequestUrl
            production_url = $productionUrl
            failure_alert_path = $script:failureAlertPath
        }
        $temporary = "$statusFile.tmp"
        $payload | ConvertTo-Json | Set-Content -LiteralPath $temporary -Encoding UTF8
        Move-Item -LiteralPath $temporary -Destination $statusFile -Force
    }
    catch { Write-Warning "Could not write $Card status: $($_.Exception.Message)" }
}

function Set-CardStage([string]$Name, [string]$Message = "Stage started.") {
    $script:currentStage = $Name
    Write-CardStatus -Status "Running" -Stage $Name -Message $Message -PullRequestUrl $script:prUrl
    Write-Host "`n=== $cardName :: $Name ==="
}

function Resolve-CardFailureAlertIfPresent([string]$SuccessMessage) {
    $failureRoot = Join-Path $statusRoot "failure-alerts"
    $datePrefix = Get-Date -Format "yyyyMMdd"
    if (Test-Path -LiteralPath $failureRoot) {
        $todayFailures = @(Get-ChildItem -LiteralPath $failureRoot -Filter "strategy-update-failed-$datePrefix*.json" -ErrorAction SilentlyContinue)
        if ($todayFailures.Count) {
            Resolve-StrategyFailureAlert -SuccessMessage $SuccessMessage -ResolutionLabel "$cardName only" | Out-Null
        }
    }
}

function Show-CardSuccessNotification([string]$Message) {
    try {
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        $notification = New-Object System.Windows.Forms.NotifyIcon
        $notification.Icon = [System.Drawing.SystemIcons]::Information
        $notification.BalloonTipTitle = "$cardName update succeeded"
        $notification.BalloonTipText = $Message
        $notification.BalloonTipIcon = "Info"
        $notification.Visible = $true
        $notification.ShowBalloonTip(10000)
        Start-Sleep -Seconds 10
        $notification.Dispose()
    }
    catch { Write-Warning "Could not display the $cardName success notification: $($_.Exception.Message)" }
}

function Invoke-NativeQuiet([scriptblock]$Action) {
    $savedPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $Action 2>$null
        return [pscustomobject]@{ Output = $output; ExitCode = $LASTEXITCODE }
    }
    finally { $ErrorActionPreference = $savedPreference }
}

function Wait-ForWorkflowRun([string]$RunId) {
    for ($attempt = 1; $attempt -le 360; $attempt++) {
        $result = Invoke-NativeQuiet { & $gh api "repos/$repo/actions/runs/$RunId" }
        if ($result.ExitCode -eq 0) {
            $state = ($result.Output -join "`n") | ConvertFrom-Json
            if ($state.status -eq "completed") {
                if ($state.conclusion -ne "success") { throw "Extreme OS workflow concluded $($state.conclusion)." }
                return
            }
        }
        Start-Sleep -Seconds 10
    }
    throw "Timed out waiting for the Extreme OS workflow."
}

function Wait-ForVercelCheck([string]$PullRequestUrl) {
    $registered = $false
    for ($attempt = 1; $attempt -le 360; $attempt++) {
        $result = Invoke-NativeQuiet { & $gh pr view $PullRequestUrl --repo $repo --json statusCheckRollup }
        if ($result.ExitCode -eq 0) {
            $state = ($result.Output -join "`n") | ConvertFrom-Json
            $checks = @($state.statusCheckRollup | Where-Object { $_.context -eq "Vercel" -or $_.name -eq "Vercel" })
            if ($checks.Count) {
                $registered = $true
                break
            }
        }
        Start-Sleep -Seconds 5
    }
    if (-not $registered) { throw "Timed out waiting for the Vercel preview check to register: $PullRequestUrl" }
    & $gh pr checks $PullRequestUrl --repo $repo --watch --interval 10 --fail-fast
    if ($LASTEXITCODE -ne 0) { throw "Vercel preview check failed: $PullRequestUrl" }
}

function Wait-ForPages([string]$Commit) {
    for ($attempt = 1; $attempt -le 60; $attempt++) {
        $result = Invoke-NativeQuiet { & $gh api "repos/$repo/pages/builds/latest" }
        if ($result.ExitCode -eq 0) {
            $build = ($result.Output -join "`n") | ConvertFrom-Json
            if ($build.commit -eq $Commit -and $build.status -eq "built") { return }
            if ($build.commit -eq $Commit -and $build.status -eq "errored") { throw "GitHub Pages failed to publish $Commit." }
        }
        Start-Sleep -Seconds 10
    }
    throw "Timed out waiting for GitHub Pages to publish $Commit."
}

function Wait-ForVercelProduction([string]$Commit) {
    $registered = $false
    for ($attempt = 1; $attempt -le 180; $attempt++) {
        $statusResult = Invoke-NativeQuiet { & $gh api "repos/$repo/commits/$Commit/status" }
        if ($statusResult.ExitCode -eq 0) {
            $combined = ($statusResult.Output -join "`n") | ConvertFrom-Json
            $vercelStatuses = @($combined.statuses | Where-Object { $_.context -match '(?i)vercel' })
            if ($vercelStatuses.Count) {
                $registered = $true
                if (@($vercelStatuses | Where-Object { $_.state -in @('error', 'failure') }).Count) {
                    throw "Vercel production deployment failed for $Commit."
                }
                if (-not @($vercelStatuses | Where-Object { $_.state -ne 'success' }).Count) { return }
            }
        }
        $checksResult = Invoke-NativeQuiet { & $gh api -H "Accept: application/vnd.github+json" "repos/$repo/commits/$Commit/check-runs" }
        if ($checksResult.ExitCode -eq 0) {
            $rollup = ($checksResult.Output -join "`n") | ConvertFrom-Json
            $vercelChecks = @($rollup.check_runs | Where-Object { $_.name -match '(?i)vercel' })
            if ($vercelChecks.Count) {
                $registered = $true
                if (@($vercelChecks | Where-Object { $_.conclusion -and $_.conclusion -notin @('success', 'neutral', 'skipped') }).Count) {
                    throw "Vercel production deployment failed for $Commit."
                }
                if (-not @($vercelChecks | Where-Object { $_.status -ne 'completed' }).Count) { return }
            }
        }
        Start-Sleep -Seconds 10
    }
    if (-not $registered) { throw "Vercel did not register a production deployment for $Commit." }
    throw "Timed out waiting for Vercel production deployment $Commit."
}

function Close-PriorCardPr {
    $result = Invoke-NativeQuiet { & $gh pr list --repo $repo --head $previewBranch --state open --json number,url }
    if ($result.ExitCode -ne 0) { throw "Could not inspect prior $cardName pull requests." }
    $items = @(($result.Output -join "`n") | ConvertFrom-Json)
    foreach ($item in $items) {
        if (-not $item) { continue }
        & $gh pr close $item.number --repo $repo --comment "Superseded by the next independent $cardName update."
        if ($LASTEXITCODE -ne 0) { throw "Could not close superseded pull request $($item.url)." }
    }
}

function Reset-LocalCardBranch {
    & $git -C $webRoot fetch origin main
    if ($LASTEXITCODE -ne 0) { throw "Could not fetch main." }
    $remoteCardBranch = Invoke-NativeQuiet { & $git -C $webRoot ls-remote --exit-code --heads origin $previewBranch }
    if ($remoteCardBranch.ExitCode -eq 0) {
        & $git -C $webRoot fetch origin "+refs/heads/$previewBranch`:refs/remotes/origin/$previewBranch"
        if ($LASTEXITCODE -ne 0) { throw "Could not fetch the existing $cardName preview branch." }
    }
    & $git -C $webRoot checkout -f -B $previewBranch origin/main
    if ($LASTEXITCODE -ne 0) { throw "Could not reset $previewBranch from main." }
}

function Assert-CardOwnership {
    $changed = @(& $git -C $webRoot diff --name-only "origin/main...HEAD")
    if ($LASTEXITCODE -ne 0) { throw "Could not inspect $cardName generated files." }
    foreach ($path in $changed) {
        $normalized = $path.Replace('\', '/')
        if (-not ($configuration.Patterns | Where-Object { $normalized -match $_ })) {
            throw "$cardName attempted to publish an unowned file: $normalized"
        }
    }
    return $changed
}

function Test-CombinedInputsCurrent {
    $missing = @()
    foreach ($dependency in @("extreme-os", "mean-reversion", "momentum-etf1", "momentum-etf2", "momentum-stocks", "haa")) {
        $path = Join-Path $automationRoot "cards\$dependency\last-run-status.json"
        if (-not (Test-Path -LiteralPath $path)) { $missing += "$dependency (no status)"; continue }
        try {
            $status = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
            $updated = [datetime]$status.updated_at
        }
        catch {
            $missing += "$dependency (unreadable status)"
            continue
        }
        if ($status.status -ne "Succeeded" -or $updated.Date -ne (Get-Date).Date) {
            $missing += "$dependency ($($status.status), $($updated.ToString('yyyy-MM-dd')))"
        }
    }
    return $missing
}

function Wait-ForCombinedInputsCurrent {
    param(
        [TimeSpan]$Timeout = ([TimeSpan]::FromHours(5)),
        [int]$PollSeconds = 30
    )
    $deadline = (Get-Date).Add($Timeout)
    $attempt = 0
    do {
        $attempt++
        $incomplete = @(Test-CombinedInputsCurrent)
        if (-not $incomplete.Count) { return @() }

        $terminalFailure = @($incomplete | Where-Object { $_ -match '\((Failed|Skipped),' })
        if ($terminalFailure.Count) { return $incomplete }

        if ($attempt -eq 1 -or $attempt % 20 -eq 0) {
            Write-Host "Combined Portfolio is waiting for same-day card success: $($incomplete -join ', ')."
        }
        if ((Get-Date) -lt $deadline) { Start-Sleep -Seconds $PollSeconds }
    } while ((Get-Date) -lt $deadline)
    return @(Test-CombinedInputsCurrent)
}

function Invoke-CardGeneration {
    switch ($Card) {
        "mean-reversion" {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $webRoot "scripts\update_mean_reversion_daily.ps1") -NoPublish -TargetCheckout $webRoot
            if ($LASTEXITCODE -ne 0) { throw "Mean Reversion calculation failed." }
            $source = Join-Path $automationRoot "member-pages\mean-reversion-members.html"
            $destination = Join-Path $webRoot "api\_member-content\mean-reversion.html"
            Copy-Item -LiteralPath $source -Destination $destination -Force
            & $python (Join-Path $webRoot "inject_position_calculator.py") $destination
            if ($LASTEXITCODE -ne 0) { throw "Mean Reversion position calculator injection failed." }
            $previousPythonPath = $env:PYTHONPATH
            try {
                $env:PYTHONPATH = "$webRoot;C:\junk\stocks\HAA\.packages"
                & $python (Join-Path $webRoot "scripts\verify_moo_backtests.py") --strategy mean-reversion
                if ($LASTEXITCODE -ne 0) { throw "Mean Reversion MOO verification failed." }
            }
            finally { $env:PYTHONPATH = $previousPythonPath }
        }
        "momentum-etf1" { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $webRoot "scripts\update_momentum_card.ps1") -Card $Card -WebRoot $webRoot; if ($LASTEXITCODE -ne 0) { throw "$cardName generation failed." } }
        "momentum-etf2" { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $webRoot "scripts\update_momentum_card.ps1") -Card $Card -WebRoot $webRoot; if ($LASTEXITCODE -ne 0) { throw "$cardName generation failed." } }
        "momentum-stocks" { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $webRoot "scripts\update_momentum_card.ps1") -Card $Card -WebRoot $webRoot; if ($LASTEXITCODE -ne 0) { throw "$cardName generation failed." } }
        "haa" { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $webRoot "scripts\update_haa_weekdays.ps1") -WebRoot $webRoot; if ($LASTEXITCODE -ne 0) { throw "$cardName generation failed." } }
        "combined" {
            $previousPythonPath = $env:PYTHONPATH
            try {
                $env:PYTHONPATH = "$webRoot;C:\junk\stocks\DualMom\.python_packages;C:\junk\stocks\HAA\.packages"
                & $python (Join-Path $webRoot "generate_combined_portfolio_page.py") `
                    --etf1-source "C:\junk\stocks\DualMom\output_momo5" `
                    --mean-reversion-source "C:\junk\stocks\RevMurphy\output_long_only_5x0_100_no_cluster_next_open"
                if ($LASTEXITCODE -ne 0) { throw "$cardName generation failed." }
            }
            finally { $env:PYTHONPATH = $previousPythonPath }
        }
    }
    if ($Card -like "momentum-*") {
        $previousPythonPath = $env:PYTHONPATH
        try {
            $env:PYTHONPATH = "$webRoot;C:\junk\stocks\HAA\.packages"
            & $python (Join-Path $webRoot "scripts\verify_moo_backtests.py") --strategy $Card
            if ($LASTEXITCODE -ne 0) { throw "$cardName MOO verification failed." }
        }
        finally { $env:PYTHONPATH = $previousPythonPath }
    }
}

Write-CardStatus -Status "Running" -Stage $currentStage -Message "$cardName independent update started." -PullRequestUrl $null
try {
    Start-Transcript -Path $log -Append
    $transcriptStarted = $true
    foreach ($path in @($gh, $git, $python, (Join-Path $webRoot "scripts\strategy_failure_alert.ps1"), (Join-Path $webRoot "scripts\test_daily_site_guard.ps1"))) {
        if (-not (Test-Path -LiteralPath $path)) { throw "Required independent-update dependency not found: $path" }
    }

    if ($Card -eq "combined") {
        Set-CardStage "Waiting for source cards" "Combined Portfolio will publish as soon as all six source cards succeed today."
        $incomplete = @(Wait-ForCombinedInputsCurrent)
        if ($incomplete.Count) {
            $message = "Combined Portfolio retained its previous valid version because these card updates are incomplete: $($incomplete -join ', ')."
            Write-CardStatus -Status "Skipped" -Stage "Input freshness check" -Message $message -PullRequestUrl $null
            Write-Host $message
            return
        }
    }

    Set-CardStage "Waiting for publication slot" "Other card calculations may continue independently; Git publication is serialized."
    $mutex = New-Object System.Threading.Mutex($false, "Local\ExtremeDashboardIndependentCardPublisher")
    $hasMutex = $mutex.WaitOne([TimeSpan]::FromHours(7))
    if (-not $hasMutex) { throw "Timed out waiting for the independent card publication slot." }

    Set-CardStage "Prepare isolated branch"
    Close-PriorCardPr
    if ($Card -eq "extreme-os") {
        & $git -C $webRoot fetch origin main
        if ($LASTEXITCODE -ne 0) { throw "Could not fetch main before Extreme OS dispatch." }
        & $git -C $webRoot checkout -f -B main origin/main
        if ($LASTEXITCODE -ne 0) { throw "Could not synchronize main before Extreme OS dispatch." }
        Set-CardStage "Run Extreme OS data workflow"
        $dispatch = & $gh workflow run update-performance.yml --repo $repo --ref main -f "preview_branch=$previewBranch" 2>&1
        $match = [regex]::Match("$dispatch", 'actions/runs/(\d+)')
        if (-not $match.Success) { throw "Extreme OS dispatch did not return a run ID: $dispatch" }
        Wait-ForWorkflowRun $match.Groups[1].Value
        & $git -C $webRoot fetch origin "+refs/heads/$previewBranch`:refs/remotes/origin/$previewBranch"
        if ($LASTEXITCODE -ne 0) { throw "Could not fetch the Extreme OS card branch." }
        & $git -C $webRoot checkout -f -B $previewBranch "origin/$previewBranch"
        if ($LASTEXITCODE -ne 0) { throw "Could not check out the Extreme OS card branch." }
    }
    else {
        Reset-LocalCardBranch
        Set-CardStage "Calculate and generate card"
        Invoke-CardGeneration
        & $git -C $webRoot add -- $configuration.Files
        if ($LASTEXITCODE -ne 0) { throw "Could not stage $cardName files." }
        & $git -C $webRoot diff --cached --quiet
        if ($LASTEXITCODE -eq 0) {
            $message = "$cardName is already current; no publication was needed."
            Write-CardStatus -Status "Succeeded" -Stage "Complete" -Message $message -PullRequestUrl $null
            Resolve-CardFailureAlertIfPresent $message
            Show-CardSuccessNotification $message
            return
        }
        if ($LASTEXITCODE -ne 1) { throw "Could not inspect staged $cardName changes." }
        & $git -C $webRoot config user.name "Extreme Dashboard Automation"
        & $git -C $webRoot config user.email "uyenl99@users.noreply.github.com"
        & $git -C $webRoot commit -m "Update $cardName card $today"
        if ($LASTEXITCODE -ne 0) { throw "Could not commit $cardName card changes." }
    }

    $changes = @(Assert-CardOwnership)
    if (-not $changes.Count) {
        $message = "$cardName is already current; no publication was needed."
        Write-CardStatus -Status "Succeeded" -Stage "Complete" -Message $message -PullRequestUrl $null
        Resolve-CardFailureAlertIfPresent $message
        Show-CardSuccessNotification $message
        return
    }

    Set-CardStage "Rebase and validate card"
    & $git -C $webRoot fetch origin main
    if ($LASTEXITCODE -ne 0) { throw "Could not refresh main before $cardName publication." }
    & $git -C $webRoot rebase origin/main
    if ($LASTEXITCODE -ne 0) { throw "$cardName conflicts with newer site changes; production was not changed." }
    Assert-CardOwnership | Out-Null
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $webRoot "scripts\test_daily_site_guard.ps1") -WebRoot $webRoot -BaseRef origin/main
    if ($LASTEXITCODE -ne 0) { throw "$cardName publication guard failed." }

    Set-CardStage "Publish card preview"
    & $git -C $webRoot push --force-with-lease -u origin $previewBranch
    if ($LASTEXITCODE -ne 0) { throw "Could not push $cardName preview branch." }
    for ($attempt = 1; $attempt -le 12 -and -not $prUrl; $attempt++) {
        $created = & $gh pr create --repo $repo --base main --head $previewBranch --title "Daily $cardName card update" --body "$cardName completed its independent calculation and validation. No other strategy card is included in this PR." 2>&1
        if ($LASTEXITCODE -eq 0) { $prUrl = "$created".Trim() } else { Start-Sleep -Seconds 10 }
    }
    if (-not $prUrl) { throw "$cardName completed, but its preview PR could not be created." }

    Set-CardStage "Validate card preview" "Waiting for Vercel preview checks: $prUrl"
    Wait-ForVercelCheck $prUrl
    Set-CardStage "Merge card update"
    & $git -C $webRoot fetch origin main
    if ($LASTEXITCODE -ne 0) { throw "Could not refresh main before merging $cardName." }
    & $git -C $webRoot merge-base --is-ancestor origin/main HEAD
    if ($LASTEXITCODE -ne 0) { throw "Main changed during $cardName preview checks; this card must rerun." }
    & $gh pr merge $prUrl --repo $repo --squash --delete-branch
    if ($LASTEXITCODE -ne 0) { throw "$cardName preview passed but could not be merged: $prUrl" }
    $mergeInfo = & $gh pr view $prUrl --repo $repo --json mergeCommit | ConvertFrom-Json
    $mergeSha = $mergeInfo.mergeCommit.oid
    if (-not $mergeSha) { throw "$cardName merged, but its production commit could not be identified." }
    Set-CardStage "Wait for production deployment"
    Wait-ForVercelProduction $mergeSha
    Wait-ForPages $mergeSha

    $successMessage = "$cardName published successfully. PR: $prUrl Production: $productionUrl"
    Write-CardStatus -Status "Succeeded" -Stage "Complete" -Message $successMessage -PullRequestUrl $prUrl
    Resolve-CardFailureAlertIfPresent $successMessage
    Show-CardSuccessNotification $successMessage
    Write-Host $successMessage
}
catch {
    $failureMessage = $_.Exception.Message
    try {
        $alert = Publish-StrategyFailureAlert -Stage "$cardName - $currentStage" -FailureMessage $failureMessage `
            -LogPath $log -PullRequestUrl $prUrl -RunStarted $runStarted -StatusRoot $statusRoot
        $failureAlertPath = $alert.desktop_alert_path
        if (-not $failureAlertPath) { $failureAlertPath = $alert.record_path }
    }
    catch { Write-Warning "Could not publish the $cardName failure alert: $($_.Exception.Message)" }
    Write-CardStatus -Status "Failed" -Stage $currentStage -Message $failureMessage -PullRequestUrl $prUrl
    throw
}
finally {
    if ($hasMutex -and $mutex) { $mutex.ReleaseMutex() }
    if ($mutex) { $mutex.Dispose() }
    if ($transcriptStarted) { Stop-Transcript }
}
