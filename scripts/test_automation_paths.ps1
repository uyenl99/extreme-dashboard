$ErrorActionPreference = "Stop"
$originalStateRoot = $env:EXTREME_DASHBOARD_STATE_ROOT

try {
    Remove-Item Env:EXTREME_DASHBOARD_STATE_ROOT -ErrorAction SilentlyContinue
    . (Join-Path $PSScriptRoot "automation_paths.ps1")

    $repositoryRoot = Split-Path -Parent $PSScriptRoot
    $expectedStateRoot = Join-Path $repositoryRoot ".automation-state"
    $actualStateRoot = Get-ExtremeDashboardAutomationStateRoot
    if ($actualStateRoot -ne $expectedStateRoot) {
        throw "Expected default state root '$expectedStateRoot'; found '$actualStateRoot'."
    }

    $expectedWorkspaceRoot = Join-Path $env:LOCALAPPDATA "ExtremeDashboardAutomation"
    $actualWorkspaceRoot = Get-ExtremeDashboardAutomationWorkspaceRoot
    if ($actualWorkspaceRoot -ne $expectedWorkspaceRoot) {
        throw "Expected workspace root '$expectedWorkspaceRoot'; found '$actualWorkspaceRoot'."
    }

    $override = Join-Path $env:TEMP "Extreme Dashboard State Test"
    $env:EXTREME_DASHBOARD_STATE_ROOT = $override
    $actualOverride = Get-ExtremeDashboardAutomationStateRoot
    if ($actualOverride -ne [IO.Path]::GetFullPath($override)) {
        throw "State-root override was not honored."
    }
}
finally {
    if ($null -eq $originalStateRoot) {
        Remove-Item Env:EXTREME_DASHBOARD_STATE_ROOT -ErrorAction SilentlyContinue
    }
    else {
        $env:EXTREME_DASHBOARD_STATE_ROOT = $originalStateRoot
    }
}

Write-Host "Automation path checks passed."
