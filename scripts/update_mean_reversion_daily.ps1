param(
    [switch]$NoPublish,
    [string]$TargetCheckout = ""
)

$ErrorActionPreference = "Stop"

$revMurphyRoot = "C:\junk\stocks\RevMurphy"
$backtestOutput = Join-Path $revMurphyRoot "output_long_short_5x5_walk_forward_next_open"
$automationRoot = Join-Path $env:LOCALAPPDATA "ExtremeDashboardAutomation"
$checkout = if ($TargetCheckout) { $TargetCheckout } else { Join-Path $automationRoot "extreme-dashboard" }
$logDirectory = Join-Path $automationRoot "logs"
$python = Join-Path $revMurphyRoot ".venv\Scripts\python.exe"
$git = "C:\Users\uyenl\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe"
$gh = "C:\Program Files\GitHub CLI\gh.exe"
$previewBranch = "automation/mean-reversion-daily-preview"
$today = Get-Date -Format "yyyy-MM-dd"
$modeTag = "walk-forward-moo-backtest"
$Publish = -not $NoPublish
$log = Join-Path $logDirectory "mean-reversion-$modeTag-$today.log"
$commandLog = Join-Path $logDirectory "mean-reversion-$modeTag-$today-commands.log"
$privateMemberRoot = Join-Path $automationRoot "member-pages"
$privateMeanReversionPage = Join-Path $privateMemberRoot "mean-reversion-members.html"

New-Item -ItemType Directory -Force -Path $automationRoot, $logDirectory, $privateMemberRoot | Out-Null
Start-Transcript -Path $log -Append

try {
    if (-not (Test-Path $python)) { throw "Python runtime not found: $python" }
    if (-not (Test-Path $git)) { throw "Git executable not found: $git" }
    if (-not (Test-Path $gh)) { throw "GitHub CLI not found: $gh" }
    if (-not $env:POLYGON_API_KEY) {
        throw "POLYGON_API_KEY is not available to the scheduled task user."
    }

    if (-not $Publish -and -not $TargetCheckout) { throw "TargetCheckout is required when Publish is false." }
    if ($Publish -and -not (Test-Path (Join-Path $checkout ".git"))) {
        & $git clone "https://github.com/uyenl99/extreme-dashboard.git" $checkout
        if ($LASTEXITCODE -ne 0) { throw "Initial dashboard clone failed." }
    }

    if ($Publish) {
    & $git -C $checkout fetch origin main
    if ($LASTEXITCODE -ne 0) { throw "Could not fetch main." }
    & $git -C $checkout ls-remote --exit-code --heads origin $previewBranch | Out-Null
    if ($LASTEXITCODE -eq 0) {
        & $git -C $checkout fetch origin "+refs/heads/$previewBranch`:refs/remotes/origin/$previewBranch"
        if ($LASTEXITCODE -ne 0) { throw "Could not refresh the daily preview branch lease." }
    }
    elseif ($LASTEXITCODE -eq 2) {
        & $git -C $checkout update-ref -d "refs/remotes/origin/$previewBranch"
        Write-Output "Daily preview branch does not exist yet; it will be created from main."
    }
    else {
        throw "Could not query the daily preview branch."
    }
    & $git -C $checkout reset --hard origin/main
    if ($LASTEXITCODE -ne 0) { throw "Could not clean the disposable automation checkout." }
    & $git -C $checkout checkout -B $previewBranch origin/main
    if ($LASTEXITCODE -ne 0) { throw "Could not reset the daily preview branch." }
    }

    Push-Location $revMurphyRoot
    try {
        & $python "main_long_short_walk_forward.py" --end $today --output-dir $backtestOutput --no-force-final-exit --max-tickers 0 --long-positions 5 --short-positions 5 --long-gross-ratio 0.80 --short-gross-ratio 0.20 2>&1 | Tee-Object -FilePath $commandLog -Append
        if ($LASTEXITCODE -ne 0) { throw "Mean Reversion walk-forward next-day MOO 5x5 backtest refresh failed." }
        & $python "verify_walk_forward_backtest.py" $backtestOutput 2>&1 | Tee-Object -FilePath $commandLog -Append
        if ($LASTEXITCODE -ne 0) { throw "Mean Reversion walk-forward validation failed." }
    }
    finally { Pop-Location }

    Push-Location $checkout
    try {
        & $python "generate_mean_reversion_page.py" --source $backtestOutput --output "mean-reversion.html" --audience public --members-page (Join-Path $checkout "members.html") 2>&1 | Tee-Object -FilePath $commandLog -Append
        if ($LASTEXITCODE -ne 0) { throw "Mean Reversion public page generation failed." }
        & $python "generate_mean_reversion_page.py" --source $backtestOutput --output $privateMeanReversionPage --audience member --members-page (Join-Path $checkout "members.html") 2>&1 | Tee-Object -FilePath $commandLog -Append
        if ($LASTEXITCODE -ne 0) { throw "Mean Reversion member page generation failed." }
        Write-Output "Private Mean Reversion member page: $privateMeanReversionPage"

        if (-not $Publish) {
            Write-Output "Mean Reversion files generated for the shared batch; publishing deferred."
            return
        }

        & $git add -- mean-reversion.html strategies.html members.html
        & $git diff --cached --quiet
        if ($LASTEXITCODE -eq 0) {
            Write-Output "No Mean Reversion website changes to publish."
            return
        }

        & $git config user.name "Extreme Dashboard Automation"
        & $git config user.email "uyenl99@users.noreply.github.com"
        & $git commit -m "Update Mean Reversion MOO backtest $today"
        if ($LASTEXITCODE -ne 0) { throw "Automated commit failed." }

        $unexpectedChanges = & $git status --porcelain
        if ($LASTEXITCODE -ne 0) { throw "Could not verify the automation checkout after commit." }
        if ($unexpectedChanges) {
            throw "Unexpected tracked or untracked files remain after the automated commit: $($unexpectedChanges -join ', ')"
        }

        & $git push --force-with-lease -u origin $previewBranch
        if ($LASTEXITCODE -ne 0) { throw "Could not push the daily preview branch." }

        $branchReady = $false
        for ($attempt = 1; $attempt -le 24 -and -not $branchReady; $attempt++) {
            $savedErrorActionPreference = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            $compareJson = & $gh api "repos/uyenl99/extreme-dashboard/compare/main...$previewBranch" 2>$null
            $compareExitCode = $LASTEXITCODE
            $ErrorActionPreference = $savedErrorActionPreference
            if ($compareExitCode -eq 0) {
                $comparison = $compareJson | ConvertFrom-Json
                $branchReady = [int]$comparison.ahead_by -gt 0
            }
            if (-not $branchReady) {
                Write-Output "Preview branch is not visible ahead of main yet; retrying ($attempt/24)."
                Start-Sleep -Seconds 5
            }
        }
        if (-not $branchReady) { throw "Preview branch did not become visible ahead of main." }

        $prUrl = $null
        for ($attempt = 1; $attempt -le 12 -and -not $prUrl; $attempt++) {
            $savedErrorActionPreference = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            $prListJson = & $gh pr list --repo "uyenl99/extreme-dashboard" --head $previewBranch --state open --json url 2>$null
            $prListExitCode = $LASTEXITCODE
            $ErrorActionPreference = $savedErrorActionPreference
            if ($prListExitCode -eq 0) {
                $openPr = $prListJson | ConvertFrom-Json | Select-Object -First 1
                if ($openPr) { $prUrl = $openPr.url }
            }
            if ($prUrl) { break }

            $savedErrorActionPreference = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            $createOutput = & $gh pr create --repo "uyenl99/extreme-dashboard" --draft --base main --head $previewBranch --title "Daily Mean Reversion preview" --body "Automated Mean Reversion refresh for $today. Review the Vercel preview before merging." 2>&1
            $createExitCode = $LASTEXITCODE
            $ErrorActionPreference = $savedErrorActionPreference
            if ($createExitCode -eq 0) {
                $prUrl = "$createOutput".Trim()
                break
            }
            Write-Output "PR creation attempt $attempt/12 failed: $createOutput"
            Start-Sleep -Seconds 10
        }
        if (-not $prUrl) { throw "Could not create or find the daily preview pull request after 12 attempts." }
        Write-Output "Daily preview PR: $prUrl"
    }
    finally { Pop-Location }
}
finally { Stop-Transcript }
