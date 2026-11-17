$script:ExtremeDashboardAutomationRepositoryRoot = Split-Path -Parent $PSScriptRoot

function Get-ExtremeDashboardAutomationWorkspaceRoot {
    return Join-Path $env:LOCALAPPDATA "ExtremeDashboardAutomation"
}

function Get-ExtremeDashboardAutomationStateRoot {
    $configuredRoot = [Environment]::ExpandEnvironmentVariables(
        [string]$env:EXTREME_DASHBOARD_STATE_ROOT
    ).Trim()
    if ($configuredRoot) {
        return [IO.Path]::GetFullPath($configuredRoot)
    }

    return Join-Path $script:ExtremeDashboardAutomationRepositoryRoot ".automation-state"
}
