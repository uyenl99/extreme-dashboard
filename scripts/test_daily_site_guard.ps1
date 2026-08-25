param(
    [string]$WebRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$BaseRef = "origin/main"
)

$ErrorActionPreference = "Stop"
$git = "C:\Users\uyenl\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe"

function Read-GitUtf8File([string]$Ref, [string]$Path) {
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $git
    $startInfo.Arguments = "-C `"$WebRoot`" show `"${Ref}:$Path`""
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.StandardOutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    [void]$process.Start()
    $content = $process.StandardOutput.ReadToEnd()
    $errorText = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) { throw "Could not read ${Ref}:$Path from Git: $errorText" }
    return $content
}

function Assert-Contains([string]$Path, [string[]]$RequiredText) {
    $content = Get-Content -LiteralPath (Join-Path $WebRoot $Path) -Raw
    foreach ($text in $RequiredText) {
        if (-not $content.Contains($text)) {
            throw "Daily publication guard failed: $Path is missing required site marker: $text"
        }
    }
}

function Assert-SectionRowCount([string]$Path, [string]$Heading, [int]$ExpectedRows) {
    $content = Get-Content -LiteralPath (Join-Path $WebRoot $Path) -Raw
    $start = $content.IndexOf("<h2>$Heading</h2>")
    $end = if ($start -ge 0) { $content.IndexOf('</section>', $start) } else { -1 }
    if ($start -lt 0 -or $end -lt 0) {
        throw "Daily publication guard failed: $Path is missing section: $Heading"
    }
    $section = $content.Substring($start, $end - $start)
    $rows = ([regex]::Matches($section, '<tr>')).Count - 1
    if ($rows -ne $ExpectedRows) {
        throw "Daily publication guard failed: $Path section '$Heading' has $rows rows; expected $ExpectedRows."
    }
}

$allowedPaths = @(
    '^api/_member-content/(extreme-os|mean-reversion|momentum|momentum2|momentum-stocks)\.html$',
    '^data/performance_summary\.json$',
    '^extreme-os\.html$',
    '^performance-details\.html$',
    '^index\.html$',
    '^mean-reversion\.html$',
    '^momentum\.html$',
    '^momentum2\.html$',
    '^momentum-stocks\.html$',
    '^inflation-compass/(monthly_pnl_by_year\.csv|summary\.csv|wealth\.png)$'
)

$changedPaths = & $git -C $WebRoot diff --name-only "$BaseRef...HEAD"
if ($LASTEXITCODE -ne 0) { throw "Daily publication guard could not inspect changed files." }
foreach ($path in $changedPaths) {
    $normalized = $path.Replace('\', '/')
    if (-not ($allowedPaths | Where-Object { $normalized -match $_ })) {
        throw "Daily publication guard blocked an unapproved file change: $normalized"
    }
}

# The Mean Reversion generator may update only its card contents on the public
# homepage. The prefix and suffix around that card must match current main byte
# for byte, preventing an old generator from replacing navigation or layout.
$baseIndex = (Read-GitUtf8File $BaseRef "index.html") -replace "`r`n?", "`n"
$baseIndex = $baseIndex.TrimEnd()
$currentIndex = [System.IO.File]::ReadAllText((Join-Path $WebRoot "index.html"), (New-Object System.Text.UTF8Encoding($false))) -replace "`r`n?", "`n"
$currentIndex = $currentIndex.TrimEnd()
$marker = '<h2>Mean Reversion</h2>'
$baseStart = $baseIndex.IndexOf($marker)
$currentStart = $currentIndex.IndexOf($marker)
if ($baseStart -lt 0 -or $currentStart -lt 0) { throw "Daily publication guard could not locate the Mean Reversion homepage card." }
$baseEnd = $baseIndex.IndexOf('</div>', $baseStart)
$currentEnd = $currentIndex.IndexOf('</div>', $currentStart)
if ($baseEnd -lt 0 -or $currentEnd -lt 0) { throw "Daily publication guard could not locate the end of the Mean Reversion homepage card." }
$baseEnd += 6
$currentEnd += 6
$protectedPrefixMatches = $baseIndex.Substring(0, $baseStart) -ceq $currentIndex.Substring(0, $currentStart)
$protectedSuffixMatches = $baseIndex.Substring($baseEnd) -ceq $currentIndex.Substring($currentEnd)
if (-not $protectedPrefixMatches -or -not $protectedSuffixMatches) {
    throw "Daily publication guard blocked changes outside the Mean Reversion card on index.html (prefix=$protectedPrefixMatches, suffix=$protectedSuffixMatches, baseLength=$($baseIndex.Length), currentLength=$($currentIndex.Length), finalCode=$([int][char]$currentIndex[$currentIndex.Length - 1]))."
}

Assert-Contains "members.html" @(
    'id="strategy-directory"',
    'members.html?strategy=extreme-os',
    'members.html?strategy=momentum',
    'members.html?strategy=momentum2',
    'members.html?strategy=momentum-stocks',
    'members.html?strategy=mean-reversion',
    'id="nav-signout-button"',
    'id="loading" class="member-loading" aria-live="polite" hidden',
    '<a href="risk-disclosure.html">Risk Disclosure</a>',
    '<a href="hypothetical-performance.html">Hypothetical Performance Disclosure</a>'
)
Assert-Contains "member.js" @(
    'location.replace("members.html")',
    'show("strategy-directory", !showDetail)',
    'showMemberNavigation(true)'
)
Assert-Contains "api/member-page.js" @(
    '<a href="members.html">Home</a>',
    "localStorage.removeItem('eti_member_session')",
    'Sign out'
)
Assert-Contains "index.html" @(
    '<a href="members.html">Login</a>',
    '<h1>Trading Strategies</h1>',
    '<h2>Extreme OS</h2>',
    '<h2>MoMoEtf1</h2>',
    '<h2>MoMoEtf2</h2>',
    '<h2>MoMo Stocks</h2>',
    '<h2>Mean Reversion</h2>'
)
foreach ($memberPage in @(
    "api/_member-content/momentum.html",
    "api/_member-content/momentum2.html",
    "api/_member-content/momentum-stocks.html"
)) {
    Assert-Contains $memberPage @(
        'metric-value positive',
        'metric-value negative'
    )
}
Assert-Contains "api/_member-content/momentum.html" @('<h2>Current Partial Month</h2>')
foreach ($memberPage in @(
    "api/_member-content/momentum.html",
    "api/_member-content/momentum2.html",
    "api/_member-content/momentum-stocks.html"
)) {
    Assert-SectionRowCount $memberPage "Latest 20 Historical Trades" 20
}

Write-Host "Daily publication guard passed. Only approved strategy results changed; site and member UI are protected."
