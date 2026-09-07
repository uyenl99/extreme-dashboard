param([string]$WebRoot = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = "Stop"
$python = "C:\Users\uyenl\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$haaRoot = "C:\junk\stocks\HAA"
$packages = Join-Path $haaRoot ".packages"
$work = Join-Path $haaRoot "runtime"
$requirements = Join-Path $WebRoot "requirements-haa.txt"
$refresh = Join-Path $WebRoot "scripts\refresh_haa.py"
foreach ($file in @($python, $requirements, $refresh)) {
    if (-not (Test-Path -LiteralPath $file)) { throw "HAA dependency missing: $file" }
}
$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = "$WebRoot;$packages"
    & $python -c "import pandas, numpy, requests, plotly, pandas_market_calendars"
    if ($LASTEXITCODE -ne 0) {
        & $python -m pip install --target $packages --upgrade --disable-pip-version-check -r $requirements
        if ($LASTEXITCODE -ne 0) { throw "HAA dependency installation failed." }
    }
    & $python $refresh --work-dir $work
    if ($LASTEXITCODE -ne 0) { throw "HAA refresh failed; shared publication must stop." }
}
finally { $env:PYTHONPATH = $previousPythonPath }
exit 0
