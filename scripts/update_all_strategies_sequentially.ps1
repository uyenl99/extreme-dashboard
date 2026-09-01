$ErrorActionPreference = "Stop"

$repo = "uyenl99/extreme-dashboard"
$previewBranch = "automation/daily-strategies-preview"
$gh = "C:\Program Files\GitHub CLI\gh.exe"
$git = "C:\Users\uyenl\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe"
$python = "C:\Users\uyenl\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$gitDirectory = Split-Path -Parent $git
$env:PATH = "$gitDirectory;$env:PATH"
$workflow = "update-performance.yml"
$webRoot = Split-Path -Parent $PSScriptRoot
$meanReversionUpdate = Join-Path $webRoot "scripts\update_mean_reversion_daily.ps1"
$momentumUpdate = Join-Path $webRoot "scripts\update_momentum_weekdays.ps1"
$mooVerifier = Join-Path $webRoot "scripts\verify_moo_backtests.py"
$publicationGuard = Join-Path $webRoot "scripts\test_daily_site_guard.ps1"
$logRoot = Join-Path $env:LOCALAPPDATA "ExtremeDashboardAutomation\logs"
$statusRoot = Join-Path $env:LOCALAPPDATA "ExtremeDashboardAutomation"
$statusFile = Join-Path $statusRoot "last-run-status.json"
$today = Get-Date -Format "yyyy-MM-dd"
$log = Join-Path $logRoot "all-strategies-sequential-$today.log"
$productionUrl = "https://uyenl99.github.io/extreme-dashboard/index.html"
$runStarted = Get-Date
$currentStage = "Initialization"
$prUrl = $null

New-Item -ItemType Directory -Force $logRoot, $statusRoot | Out-Null

foreach ($requiredPath in @(
    $gh,
    $git,
    $python,
    $meanReversionUpdate,
    $momentumUpdate,
    $mooVerifier,
    $publicationGuard,
    (Join-Path $webRoot "inject_position_calculator.py")
)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required sequential-update dependency not found: $requiredPath"
    }
}

function Write-RunStatus {
    param(
        [ValidateSet("Running", "Succeeded", "Failed")][string]$Status,
        [string]$Stage,
        [string]$Message,
        [string]$PullRequestUrl
    )

    try {
        $payload = [ordered]@{
            status = $Status
            stage = $Stage
            message = $Message
            started_at = $runStarted.ToString("o")
            updated_at = (Get-Date).ToString("o")
            log_path = $log
            pull_request_url = $PullRequestUrl
            production_url = $productionUrl
        }
        $temporaryStatusFile = "$statusFile.tmp"
        $payload | ConvertTo-Json | Set-Content -LiteralPath $temporaryStatusFile -Encoding UTF8
        Move-Item -LiteralPath $temporaryStatusFile -Destination $statusFile -Force
    }
    catch {
        Write-Warning "Could not write automation status: $($_.Exception.Message)"
    }
}

function Set-RunStage {
    param([string]$Name, [string]$Message = "Stage started.")
    $script:currentStage = $Name
    Write-RunStatus -Status "Running" -Stage $Name -Message $Message -PullRequestUrl $script:prUrl
}

function Show-RunNotification {
    param(
        [string]$Title,
        [string]$Message,
        [ValidateSet("Info", "Error")][string]$Level = "Info"
    )

    try {
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        if ($Message.Length -gt 240) { $Message = $Message.Substring(0, 237) + "..." }
        $notification = New-Object System.Windows.Forms.NotifyIcon
        $notification.Icon = if ($Level -eq "Error") {
            [System.Drawing.SystemIcons]::Error
        }
        else {
            [System.Drawing.SystemIcons]::Information
        }
        $notification.BalloonTipTitle = $Title
        $notification.BalloonTipText = $Message
        $notification.BalloonTipIcon = $Level
        $notification.Visible = $true
        $notification.ShowBalloonTip(10000)
        Start-Sleep -Seconds 10
        $notification.Dispose()
    }
    catch {
        Write-Warning "Could not display Windows notification: $($_.Exception.Message)"
    }
}

function Invoke-Stage {
    param([string]$Name, [scriptblock]$Action)
    Set-RunStage -Name $Name
    $started = Get-Date
    Write-Host "`n=== START $Name at $started ==="
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE." }
    $finished = Get-Date
    Write-Host "=== END $Name at $finished (elapsed $($finished - $started)) ==="
}

function Wait-ForRun([string]$RunId) {
    for ($attempt = 1; $attempt -le 360; $attempt++) {
        $savedPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $json = & $gh api "repos/$repo/actions/runs/$RunId" 2>$null
        $exitCode = $LASTEXITCODE
        $ErrorActionPreference = $savedPreference
        if ($exitCode -eq 0) {
            $state = $json | ConvertFrom-Json
            if ($state.status -eq "completed") {
                if ($state.conclusion -ne "success") { throw "Collective2 workflow concluded $($state.conclusion)." }
                return
            }
        }
        Start-Sleep -Seconds 10
    }
    throw "Timed out waiting for Collective2 workflow."
}

function Wait-ForVercelCheckRegistration([string]$PullRequestUrl) {
    for ($attempt = 1; $attempt -le 60; $attempt++) {
        $savedPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $json = & $gh pr view $PullRequestUrl --repo $repo --json statusCheckRollup 2>$null
        $exitCode = $LASTEXITCODE
        $ErrorActionPreference = $savedPreference
        if ($exitCode -eq 0) {
            $state = $json | ConvertFrom-Json
            $vercelChecks = @($state.statusCheckRollup | Where-Object {
                $_.context -eq "Vercel" -or $_.name -eq "Vercel"
            })
            if ($vercelChecks.Count -gt 0) {
                Write-Host "Vercel preview check registered."
                return
            }
        }
        if ($attempt -eq 1 -or $attempt % 6 -eq 0) {
            Write-Host "Waiting for Vercel preview check registration (attempt $attempt of 60)..."
        }
        Start-Sleep -Seconds 5
    }
    throw "Timed out waiting for the Vercel preview check to register: $PullRequestUrl"
}

Write-RunStatus -Status "Running" -Stage $currentStage -Message "Daily strategy batch started." -PullRequestUrl $null
Start-Transcript -Path $log -Append
try {
    $openPr = & $gh pr list --repo $repo --head $previewBranch --state open --json url | ConvertFrom-Json | Select-Object -First 1
    if ($openPr) { throw "Shared daily PR is still open: $($openPr.url). Merge or close it before the next batch." }

    $trackedChanges = & $git -C $webRoot status --porcelain --untracked-files=no
    if ($trackedChanges) { throw "Web checkout has tracked changes; batch stopped safely: $($trackedChanges -join ', ')" }
    & $git -C $webRoot fetch origin main
    if ($LASTEXITCODE -ne 0) { throw "Could not fetch main." }
    & $git -C $webRoot checkout main
    if ($LASTEXITCODE -ne 0) { throw "Could not check out main." }
    & $git -C $webRoot reset --hard origin/main
    if ($LASTEXITCODE -ne 0) { throw "Could not synchronize main." }

    Invoke-Stage "Collective2" {
        $dispatch = & $gh workflow run $workflow --repo $repo --ref main 2>&1
        $match = [regex]::Match("$dispatch", 'actions/runs/(\d+)')
        if (-not $match.Success) { throw "Collective2 dispatch did not return a run ID: $dispatch" }
        Wait-ForRun $match.Groups[1].Value
        & $git -C $webRoot fetch origin "+refs/heads/$previewBranch`:refs/remotes/origin/$previewBranch"
        if ($LASTEXITCODE -ne 0) { throw "Could not fetch the shared preview branch." }
        & $git -C $webRoot checkout -B $previewBranch "origin/$previewBranch"
        if ($LASTEXITCODE -ne 0) { throw "Could not check out the shared preview branch." }
    }
    Invoke-Stage "Mean Reversion 5x5 walk-forward next-day MOO backtest" {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $meanReversionUpdate -NoPublish -TargetCheckout $webRoot
    }
    Invoke-Stage "Momentum ETF1, ETF2, and SP" {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $momentumUpdate -NoPublish
    }
    Invoke-Stage "Verify all backtests use MOO prices" {
        & $python $mooVerifier
    }

    Set-RunStage -Name "Prepare generated site files"
    $generatedMemberRoot = Join-Path $env:LOCALAPPDATA "ExtremeDashboardAutomation\member-pages"
    $memberContentRoot = Join-Path $webRoot "api\_member-content"
    New-Item -ItemType Directory -Force $memberContentRoot | Out-Null
    $memberPages = @{
        "mean-reversion-members.html" = "mean-reversion.html"
        "momentum-members.html" = "momentum.html"
        "momentum2-members.html" = "momentum2.html"
        "momentum-stocks-members.html" = "momentum-stocks.html"
    }
    foreach ($sourceName in $memberPages.Keys) {
        $sourcePath = Join-Path $generatedMemberRoot $sourceName
        if (-not (Test-Path -LiteralPath $sourcePath)) { throw "Generated member page not found: $sourcePath" }
        Copy-Item -LiteralPath $sourcePath -Destination (Join-Path $memberContentRoot $memberPages[$sourceName]) -Force
    }
    $memberPagePaths = @($memberPages.Values | ForEach-Object { Join-Path $memberContentRoot $_ })
    & $python (Join-Path $webRoot "inject_position_calculator.py") @memberPagePaths
    if ($LASTEXITCODE -ne 0) { throw "Position calculator injection failed." }

    Set-RunStage -Name "Commit generated results"
    & $git -C $webRoot add -- mean-reversion.html strategies.html members.html momentum.html momentum2.html inflation-compass momentum-stocks.html api/_member-content position-calculator.js
    & $git -C $webRoot diff --cached --quiet
    if ($LASTEXITCODE -eq 1) {
        & $git -C $webRoot config user.name "Extreme Dashboard Automation"
        & $git -C $webRoot config user.email "uyenl99@users.noreply.github.com"
        & $git -C $webRoot commit -m "Complete daily strategy batch $today"
        if ($LASTEXITCODE -ne 0) { throw "Could not commit the completed batch." }
    }
    elseif ($LASTEXITCODE -ne 0) { throw "Could not inspect the completed batch." }

    $leftovers = & $git -C $webRoot status --porcelain
    if ($leftovers) { throw "Unexpected files remain before publication: $($leftovers -join ', ')" }

    # Rebase generated results onto the newest production site. Any overlap with
    # a site edit stops the batch instead of allowing stale HTML to win.
    Set-RunStage -Name "Rebase and validate publication"
    & $git -C $webRoot fetch origin main
    if ($LASTEXITCODE -ne 0) { throw "Could not refresh main before publication." }
    & $git -C $webRoot rebase origin/main
    if ($LASTEXITCODE -ne 0) { throw "Daily results conflict with newer site changes; production was not changed." }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $publicationGuard -WebRoot $webRoot -BaseRef origin/main
    if ($LASTEXITCODE -ne 0) { throw "Daily site publication guard failed; production was not changed." }

    Set-RunStage -Name "Publish preview branch"
    & $git -C $webRoot push --force-with-lease -u origin $previewBranch
    if ($LASTEXITCODE -ne 0) { throw "Could not publish the completed batch branch." }

    Set-RunStage -Name "Create preview PR"
    for ($attempt = 1; $attempt -le 12 -and -not $prUrl; $attempt++) {
        $created = & $gh pr create --repo $repo --draft --base main --head $previewBranch --title "Daily strategy batch update" --body "All five daily jobs completed: Collective2, Mean Reversion 5x5 walk-forward next-day MOO backtest, Momentum ETF1, Momentum ETF2, and Momentum SP. This PR is published automatically only after the Vercel preview check passes." 2>&1
        if ($LASTEXITCODE -eq 0) { $prUrl = "$created".Trim() } else { Start-Sleep -Seconds 10 }
    }
    if (-not $prUrl) { throw "All jobs finished, but the shared PR could not be created." }
    Set-RunStage -Name "Wait for preview checks" -Message "Preview PR created; waiting for Vercel check registration and completion."
    & $gh pr ready $prUrl --repo $repo
    if ($LASTEXITCODE -ne 0) { throw "Could not mark the daily update PR ready: $prUrl" }
    Wait-ForVercelCheckRegistration $prUrl
    & $gh pr checks $prUrl --repo $repo --watch --interval 10 --fail-fast
    if ($LASTEXITCODE -ne 0) { throw "Daily update preview checks failed; production was not changed: $prUrl" }
    Set-RunStage -Name "Merge daily update" -Message "Preview checks passed; validating and merging the daily update."
    & $git -C $webRoot fetch origin main
    if ($LASTEXITCODE -ne 0) { throw "Could not refresh main before merge." }
    & $git -C $webRoot merge-base --is-ancestor origin/main HEAD
    if ($LASTEXITCODE -ne 0) { throw "Main changed during preview checks. The daily batch must rerun its guard; production was not changed: $prUrl" }
    & $gh pr merge $prUrl --repo $repo --squash --delete-branch
    if ($LASTEXITCODE -ne 0) { throw "Daily update passed preview checks but could not be merged: $prUrl" }
    $mergeInfo = & $gh pr view $prUrl --repo $repo --json mergeCommit | ConvertFrom-Json
    $mergeSha = $mergeInfo.mergeCommit.oid
    if (-not $mergeSha) { throw "Daily update merged, but its production commit could not be identified: $prUrl" }
    Set-RunStage -Name "Wait for production deployment" -Message "Daily update merged; waiting for GitHub Pages to publish."
    $pagesPublished = $false
    for ($attempt = 1; $attempt -le 60 -and -not $pagesPublished; $attempt++) {
        $pagesBuild = & $gh api "repos/$repo/pages/builds/latest" | ConvertFrom-Json
        if ($pagesBuild.commit -eq $mergeSha -and $pagesBuild.status -eq "built") {
            $pagesPublished = $true
        }
        elseif ($pagesBuild.commit -eq $mergeSha -and $pagesBuild.status -eq "errored") {
            throw "GitHub Pages failed to publish daily update commit $mergeSha."
        }
        else { Start-Sleep -Seconds 10 }
    }
    if (-not $pagesPublished) { throw "Timed out waiting for GitHub Pages to publish daily update commit $mergeSha." }
    $successMessage = "All five updates published successfully. PR: $prUrl Production: $productionUrl"
    Write-Host "$successMessage ($mergeSha)."
    Write-RunStatus -Status "Succeeded" -Stage "Complete" -Message $successMessage -PullRequestUrl $prUrl
    Show-RunNotification -Title "Extreme Dashboard update succeeded" -Message $successMessage -Level Info
}
catch {
    $failureMessage = $_.Exception.Message
    Write-RunStatus -Status "Failed" -Stage $currentStage -Message $failureMessage -PullRequestUrl $prUrl
    Show-RunNotification -Title "Extreme Dashboard update failed" -Message "$currentStage`: $failureMessage Log: $log" -Level Error
    throw
}
finally { Stop-Transcript }
