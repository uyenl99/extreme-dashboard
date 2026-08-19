$ErrorActionPreference = "Stop"

$repo = "uyenl99/extreme-dashboard"
$previewBranch = "automation/daily-strategies-preview"
$gh = "C:\Program Files\GitHub CLI\gh.exe"
$git = "C:\Users\uyenl\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe"
$workflow = "update-performance.yml"
$webRoot = "C:\junk\stocks\Web"
$meanReversionUpdate = Join-Path $webRoot "scripts\update_mean_reversion_daily.ps1"
$momentumUpdate = Join-Path $webRoot "scripts\update_momentum_weekdays.ps1"
$logRoot = Join-Path $env:LOCALAPPDATA "ExtremeDashboardAutomation\logs"
$today = Get-Date -Format "yyyy-MM-dd"
$log = Join-Path $logRoot "all-strategies-sequential-$today.log"

New-Item -ItemType Directory -Force $logRoot | Out-Null

function Invoke-Stage {
    param([string]$Name, [scriptblock]$Action)
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
    Invoke-Stage "Mean Reversion 5x5 backtest" {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $meanReversionUpdate -Mode Backtest -NoPublish -TargetCheckout $webRoot
    }
    Invoke-Stage "Momentum ETF1, ETF2, and SP" {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $momentumUpdate -NoPublish
    }

    & $git -C $webRoot add -- mean-reversion.html index.html momentum.html inflation-compass momentum-stocks.html
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
    & $git -C $webRoot push --force-with-lease -u origin $previewBranch
    if ($LASTEXITCODE -ne 0) { throw "Could not publish the completed batch branch." }

    $prUrl = $null
    for ($attempt = 1; $attempt -le 12 -and -not $prUrl; $attempt++) {
        $created = & $gh pr create --repo $repo --draft --base main --head $previewBranch --title "Daily strategy batch preview" --body "All five daily jobs completed: Collective2, Mean Reversion 5x5 backtest, Momentum ETF1, Momentum ETF2, and Momentum SP. Review the Vercel preview before merging." 2>&1
        if ($LASTEXITCODE -eq 0) { $prUrl = "$created".Trim() } else { Start-Sleep -Seconds 10 }
    }
    if (-not $prUrl) { throw "All jobs finished, but the shared PR could not be created." }
    Write-Host "All five updates completed. Shared preview PR: $prUrl"
}
finally { Stop-Transcript }
