param(
    [string]$SourceRoot = "",
    [string]$StateRoot = ""
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "automation_paths.ps1")

if (-not $SourceRoot) {
    $SourceRoot = Get-ExtremeDashboardAutomationWorkspaceRoot
}
if (-not $StateRoot) {
    $StateRoot = Get-ExtremeDashboardAutomationStateRoot
}

$SourceRoot = [IO.Path]::GetFullPath($SourceRoot)
$StateRoot = [IO.Path]::GetFullPath($StateRoot)
if ($SourceRoot -eq $StateRoot) {
    throw "SourceRoot and StateRoot must be different."
}
if (-not (Test-Path -LiteralPath $SourceRoot)) {
    throw "Legacy automation root not found: $SourceRoot"
}

New-Item -ItemType Directory -Force -Path $StateRoot | Out-Null
$directories = @("backup", "cards", "logs", "member-pages")
foreach ($name in $directories) {
    $source = Join-Path $SourceRoot $name
    if (-not (Test-Path -LiteralPath $source)) { continue }

    $destination = Join-Path $StateRoot $name
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    Get-ChildItem -LiteralPath $source -Force | Copy-Item -Destination $destination -Recurse -Force
    Write-Host "Copied $source to $destination"
}

$statusFile = Join-Path $SourceRoot "last-run-status.json"
if (Test-Path -LiteralPath $statusFile) {
    Copy-Item -LiteralPath $statusFile -Destination (Join-Path $StateRoot "last-run-status.json") -Force
    Write-Host "Copied $statusFile"
}

Write-Host "Durable automation state is ready at $StateRoot"
