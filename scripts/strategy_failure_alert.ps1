function Get-StrategyFailureAlertSummary {
    param([string]$Text, [int]$MaximumLength = 300)

    $summary = [regex]::Replace("$Text", "\s+", " ").Trim()
    $summary = [regex]::Replace(
        $summary,
        "(?i)(api[_-]?key|token|authorization|password|secret)(\s*[:=]\s*)([^\s&]+)",
        '$1$2[REDACTED]'
    )
    if ($summary.Length -gt $MaximumLength) {
        return $summary.Substring(0, $MaximumLength - 3) + "..."
    }
    return $summary
}

function Show-StrategyFailureNotification {
    param(
        [string]$Stage,
        [string]$DesktopAlertPath
    )

    $stageSummary = Get-StrategyFailureAlertSummary -Text $Stage -MaximumLength 120
    $message = "Stage: $stageSummary. Production was not updated. Details: $DesktopAlertPath"

    try {
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        $toastMessage = Get-StrategyFailureAlertSummary -Text $message -MaximumLength 240
        $notification = New-Object System.Windows.Forms.NotifyIcon
        $notification.Icon = [System.Drawing.SystemIcons]::Error
        $notification.BalloonTipTitle = "Extreme Dashboard update failed"
        $notification.BalloonTipText = $toastMessage
        $notification.BalloonTipIcon = "Error"
        $notification.Visible = $true
        $notification.ShowBalloonTip(10000)
        Start-Sleep -Seconds 10
        $notification.Dispose()
    }
    catch {
        Write-Warning "Could not display the failure toast: $($_.Exception.Message)"
    }

    try {
        $msg = Join-Path $env:SystemRoot "System32\msg.exe"
        if (-not (Test-Path -LiteralPath $msg)) { throw "msg.exe was not found." }
        $dialogMessage = Get-StrategyFailureAlertSummary -Text (
            "EXTREME DASHBOARD UPDATE FAILED. $message Open Codex and ask why the autoupdate failed."
        ) -MaximumLength 240
        $msgOutput = & $msg $env:USERNAME "/TIME:86400" $dialogMessage 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "msg.exe exited with code $LASTEXITCODE`: $msgOutput"
        }
    }
    catch {
        Write-Warning "Could not display the persistent failure message: $($_.Exception.Message)"
    }
}

function Publish-StrategyFailureAlert {
    param(
        [string]$Stage,
        [string]$FailureMessage,
        [string]$LogPath,
        [string]$PullRequestUrl,
        [datetime]$RunStarted,
        [string]$StatusRoot,
        [string]$DesktopDirectory = [Environment]::GetFolderPath("Desktop"),
        [switch]$SkipInteractiveNotification
    )

    $now = Get-Date
    $date = $now.ToString("yyyy-MM-dd")
    $safeMessage = Get-StrategyFailureAlertSummary -Text $FailureMessage -MaximumLength 1000
    $alertRoot = Join-Path $StatusRoot "failure-alerts"
    New-Item -ItemType Directory -Force -Path $alertRoot | Out-Null

    $recordPath = Join-Path $alertRoot (
        "strategy-update-failed-{0}.json" -f $now.ToString("yyyyMMdd-HHmmss-fff")
    )
    $record = [ordered]@{
        status = "Failed"
        failed_at = $now.ToString("o")
        run_started_at = $RunStarted.ToString("o")
        stage = $Stage
        message = $safeMessage
        production_updated = $false
        pull_request_url = $PullRequestUrl
        log_path = $LogPath
    }
    $temporaryRecord = "$recordPath.tmp"
    $record | ConvertTo-Json | Set-Content -LiteralPath $temporaryRecord -Encoding UTF8
    Move-Item -LiteralPath $temporaryRecord -Destination $recordPath -Force

    $desktopAlertPath = $null
    if ($DesktopDirectory -and (Test-Path -LiteralPath $DesktopDirectory)) {
        $desktopAlertPath = Join-Path $DesktopDirectory "Extreme Dashboard FAILED $date.txt"
        $pullRequestLine = if ($PullRequestUrl) { $PullRequestUrl } else { "None created" }
        $alertText = @"
EXTREME DASHBOARD UPDATE FAILED

Failed at: $($now.ToString("yyyy-MM-dd hh:mm:ss tt"))
Stage: $Stage
Error: $safeMessage
Production updated: No
Pull request: $pullRequestLine
Local log: $LogPath
Machine-readable alert: $recordPath

Action required: inspect and rerun the failed update before relying on the next-session orders.
"@
        if (Test-Path -LiteralPath $desktopAlertPath) {
            Add-Content -LiteralPath $desktopAlertPath -Value ("`r`n`r`n" + ("=" * 72) + "`r`n" + $alertText) -Encoding UTF8
        }
        else {
            Set-Content -LiteralPath $desktopAlertPath -Value $alertText -Encoding UTF8
        }
    }

    if (-not $SkipInteractiveNotification) {
        Show-StrategyFailureNotification -Stage $Stage -DesktopAlertPath $desktopAlertPath
    }

    return [pscustomobject]@{
        record_path = $recordPath
        desktop_alert_path = $desktopAlertPath
    }
}

function Resolve-StrategyFailureAlert {
    param(
        [string]$SuccessMessage,
        [string]$DesktopDirectory = [Environment]::GetFolderPath("Desktop")
    )

    try {
        if (-not $DesktopDirectory) { return $null }
        $date = Get-Date -Format "yyyy-MM-dd"
        $desktopAlertPath = Join-Path $DesktopDirectory "Extreme Dashboard FAILED $date.txt"
        if (-not (Test-Path -LiteralPath $desktopAlertPath)) { return $null }

        $resolvedAt = Get-Date -Format "yyyy-MM-dd hh:mm:ss tt"
        Add-Content -LiteralPath $desktopAlertPath -Value @"


RESOLVED at $resolvedAt
$SuccessMessage
"@ -Encoding UTF8
        return $desktopAlertPath
    }
    catch {
        Write-Warning "Could not mark the persistent failure alert resolved: $($_.Exception.Message)"
        return $null
    }
}
