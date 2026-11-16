param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("momentum-etf1", "momentum-etf2", "momentum-stocks")]
    [string]$Card,
    [string]$WebRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"

$python = "C:\Users\uyenl\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$dualMomRoot = "C:\junk\stocks\DualMom"
$plotlyDir = Join-Path $dualMomRoot ".python_packages"
$marketCalendarDir = "C:\junk\stocks\HAA\.packages"
$inflationRoot = "C:\junk\stocks\inflationcompass"
$momoSpRoot = "C:\junk\stocks\MomoSp\pit_version"
$momoSpOutput = Join-Path $momoSpRoot "output_pit_r1000_5b_latest"
$momoSpAlert = Join-Path $momoSpRoot "output_pit_v2a_live\latest_signal.json"
$memberContentRoot = Join-Path $WebRoot "api\_member-content"
$injector = Join-Path $WebRoot "inject_position_calculator.py"

foreach ($path in @($python, $WebRoot, $memberContentRoot, $injector)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Required path not found: $path" }
}

$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = "$WebRoot;$plotlyDir;$marketCalendarDir"

    switch ($Card) {
        "momentum-etf1" {
            foreach ($path in @(
                (Join-Path $dualMomRoot "refresh_momo5_data.py"),
                (Join-Path $dualMomRoot "momo5.py"),
                (Join-Path $WebRoot "generate_momentum_page.py")
            )) {
                if (-not (Test-Path -LiteralPath $path)) { throw "Momentum ETF1 dependency missing: $path" }
            }

            Push-Location $dualMomRoot
            try {
                & $python "refresh_momo5_data.py"
                if ($LASTEXITCODE -ne 0) { throw "Momentum ETF1 data refresh failed." }
                & $python "momo5.py"
                if ($LASTEXITCODE -ne 0) { throw "Momentum ETF1 backtest failed." }
            }
            finally { Pop-Location }

            & $python (Join-Path $WebRoot "generate_momentum_page.py") `
                --source (Join-Path $dualMomRoot "output_momo5") `
                --output (Join-Path $WebRoot "momentum.html") `
                --audience public `
                --strategies-page (Join-Path $WebRoot "strategies.html") `
                --members-page (Join-Path $WebRoot "members.html")
            if ($LASTEXITCODE -ne 0) { throw "Momentum ETF1 public page generation failed." }
            & $python (Join-Path $WebRoot "generate_momentum_page.py") `
                --source (Join-Path $dualMomRoot "output_momo5") `
                --output (Join-Path $memberContentRoot "momentum.html") `
                --audience member `
                --strategies-page (Join-Path $WebRoot "strategies.html") `
                --members-page (Join-Path $WebRoot "members.html")
            if ($LASTEXITCODE -ne 0) { throw "Momentum ETF1 member page generation failed." }
            $memberPage = Join-Path $memberContentRoot "momentum.html"
        }

        "momentum-etf2" {
            foreach ($path in @(
                (Join-Path $inflationRoot "inflation_compass.py"),
                (Join-Path $inflationRoot "requirements.txt"),
                (Join-Path $WebRoot "generate_momentum_etf2_page.py")
            )) {
                if (-not (Test-Path -LiteralPath $path)) { throw "Momentum ETF2 dependency missing: $path" }
            }

            & $python -c "import pandas,numpy,requests,matplotlib,yfinance"
            if ($LASTEXITCODE -ne 0) {
                & $python -m pip install --target $marketCalendarDir --upgrade --disable-pip-version-check -r (Join-Path $inflationRoot "requirements.txt")
                if ($LASTEXITCODE -ne 0) { throw "Momentum ETF2 dependency installation failed." }
            }
            Push-Location $inflationRoot
            try {
                & $python "inflation_compass.py" --cost-bps 5
                if ($LASTEXITCODE -ne 0) { throw "Momentum ETF2 refresh failed." }
            }
            finally { Pop-Location }

            $source = Join-Path $inflationRoot "output"
            $generator = Join-Path $WebRoot "generate_momentum_etf2_page.py"
            & $python $generator --source $source --output (Join-Path $WebRoot "momentum2.html") `
                --audience public --strategies-page (Join-Path $WebRoot "strategies.html") `
                --members-page (Join-Path $WebRoot "members.html") --chart-src "inflation-compass/wealth.png"
            if ($LASTEXITCODE -ne 0) { throw "Momentum ETF2 public page generation failed." }
            & $python $generator --source $source --output (Join-Path $memberContentRoot "momentum2.html") `
                --audience member --strategies-page (Join-Path $WebRoot "strategies.html") `
                --members-page (Join-Path $WebRoot "members.html") --chart-src "inflation-compass/wealth.png"
            if ($LASTEXITCODE -ne 0) { throw "Momentum ETF2 member page generation failed." }

            $assetRoot = Join-Path $WebRoot "inflation-compass"
            New-Item -ItemType Directory -Force -Path $assetRoot | Out-Null
            foreach ($name in @("summary.csv", "monthly_pnl_by_year.csv", "wealth.png")) {
                Copy-Item -LiteralPath (Join-Path $source $name) -Destination (Join-Path $assetRoot $name) -Force
            }
            foreach ($protectedName in @("latest_alert.json", "last_50_trades.csv")) {
                $publicProtectedPath = Join-Path $assetRoot $protectedName
                if (Test-Path -LiteralPath $publicProtectedPath) {
                    Remove-Item -LiteralPath $publicProtectedPath -Force
                }
            }
            $memberPage = Join-Path $memberContentRoot "momentum2.html"
        }

        "momentum-stocks" {
            $update = Join-Path $momoSpRoot "update_v2a_live.py"
            $preview = Join-Path $WebRoot "generate_momentum_stocks_preview.py"
            $generator = Join-Path $WebRoot "generate_momentum_stocks_page.py"
            foreach ($path in @($update, $preview, $generator)) {
                if (-not (Test-Path -LiteralPath $path)) { throw "Momentum Stocks dependency missing: $path" }
            }

            Push-Location $momoSpRoot
            try {
                & $python $update
                if ($LASTEXITCODE -ne 0) { throw "Momentum Stocks refresh failed." }
            }
            finally { Pop-Location }
            & $python $preview --strategy-root $momoSpRoot
            if ($LASTEXITCODE -ne 0) { throw "Momentum Stocks preview signal failed." }

            & $python $generator --source $momoSpOutput --alert-source $momoSpAlert `
                --output (Join-Path $WebRoot "momentum-stocks.html") --audience public `
                --strategies-page (Join-Path $WebRoot "strategies.html") --members-page (Join-Path $WebRoot "members.html")
            if ($LASTEXITCODE -ne 0) { throw "Momentum Stocks public page generation failed." }
            & $python $generator --source $momoSpOutput --alert-source $momoSpAlert `
                --output (Join-Path $memberContentRoot "momentum-stocks.html") --audience member `
                --strategies-page (Join-Path $WebRoot "strategies.html") --members-page (Join-Path $WebRoot "members.html")
            if ($LASTEXITCODE -ne 0) { throw "Momentum Stocks member page generation failed." }
            $memberPage = Join-Path $memberContentRoot "momentum-stocks.html"
        }
    }

    & $python $injector $memberPage
    if ($LASTEXITCODE -ne 0) { throw "Position calculator injection failed for $Card." }
    Write-Host "$Card calculation and page generation completed independently."
}
finally {
    $env:PYTHONPATH = $previousPythonPath
}
