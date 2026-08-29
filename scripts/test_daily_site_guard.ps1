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

function Assert-NotContains([string]$Path, [string[]]$ForbiddenText) {
    $content = Get-Content -LiteralPath (Join-Path $WebRoot $Path) -Raw
    foreach ($text in $ForbiddenText) {
        if ($content.Contains($text)) {
            throw "Daily publication guard failed: $Path contains forbidden site marker: $text"
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
    '^members\.html$',
    '^strategies\.html$',
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

# Daily generators may refresh only the generated statistics blocks on the
# public strategies page. Mask those blocks, then require every other byte to
# match main so an old generator cannot replace navigation or layout.
$baseIndex = (Read-GitUtf8File $BaseRef "strategies.html") -replace "`r`n?", "`n"
$baseIndex = $baseIndex.TrimEnd()
$currentIndex = [System.IO.File]::ReadAllText((Join-Path $WebRoot "strategies.html"), (New-Object System.Text.UTF8Encoding($false))) -replace "`r`n?", "`n"
$currentIndex = $currentIndex.TrimEnd()
function Mask-GeneratedCardStats([string]$Content) {
    return [regex]::Replace(
        $Content,
        '(?s)<p class="card-stats">.*?</p>',
        '<p class="card-stats">__GENERATED_STRATEGY_STATS__</p>'
    )
}
if (-not ((Mask-GeneratedCardStats $baseIndex) -ceq (Mask-GeneratedCardStats $currentIndex))) {
    throw "Daily publication guard blocked changes outside generated strategy statistics on strategies.html."
}

$baseMembers = (Read-GitUtf8File $BaseRef "members.html") -replace "`r`n?", "`n"
$baseMembers = $baseMembers.TrimEnd()
$currentMembers = [System.IO.File]::ReadAllText((Join-Path $WebRoot "members.html"), (New-Object System.Text.UTF8Encoding($false))) -replace "`r`n?", "`n"
$currentMembers = $currentMembers.TrimEnd()
function Mask-GeneratedMemberStats([string]$Content) {
    return [regex]::Replace(
        $Content,
        '(?s)<p class="home-stats">.*?</p>',
        '<p class="home-stats">__GENERATED_MEMBER_STATS__</p>'
    )
}
if (-not ((Mask-GeneratedMemberStats $baseMembers) -ceq (Mask-GeneratedMemberStats $currentMembers))) {
    throw "Daily publication guard blocked changes outside generated member statistics on members.html."
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
    'const MEMBER_DIRECTORY_URL = "members.html?view=strategies&nav=13"',
    'location.replace(MEMBER_DIRECTORY_URL)',
    'show("strategy-directory", !showDetail)',
    'showMemberNavigation(true)',
    'showMemberNavigationPending()',
    '$("member-strategies-link").href = visible ? MEMBER_DIRECTORY_URL : "strategies.html"'
)
Assert-Contains "site-auth-nav.js" @(
    'const SESSION_KEY = "eti_member_session"',
    'const MEMBER_DIRECTORY_URL = "/members.html?view=strategies&nav=13"',
    'findLink(nav, "Login")?.remove()',
    'billing.textContent = "Manage billing"',
    'signOut.textContent = "Sign out"',
    'navigationObserver = new MutationObserver(() => applyNavigationWhenReady())',
    'root.classList.remove("auth-nav-pending")'
)
Assert-Contains "api/member-page.js" @(
    'const MEMBER_DIRECTORY_URL = "members.html?view=strategies&nav=13"',
    'localStorage.removeItem("eti_member_session")',
    'Manage billing',
    'Sign out'
)
Assert-NotContains "members.html" @('<a id="member-login-link"')
Assert-Contains "index.html" @(
    '<a href="members.html">Login</a>',
    '<script src="/site-auth-nav.js?v=2"></script>',
    '<h1>Two decades of trading experience. A new generation of systematic research.</h1>',
    '<a class="button secondary" href="extreme-os.html">Review the Extreme OS record</a>',
    '<small>THE NEW RESEARCH PRIORITY</small>',
    '<h2>Lower drawdown by design</h2>',
    '<b>Lower historical drawdowns than SPY in backtests</b>',
    'Hypothetical results, not live performance. Lower backtest drawdown does not guarantee lower future risk.'
)
Assert-Contains "strategies.html" @(
    '<a href="members.html">Login</a>',
    '<script src="/site-auth-nav.js?v=2"></script>',
    '<h1>Trading Strategies</h1>',
    '<h2>Extreme OS</h2>',
    '<h2>MoMoEtf1</h2>',
    '<h2>MoMoEtf2</h2>',
    '<h2>MoMo Stocks</h2>',
    '<h2>Mean Reversion</h2>'
)
foreach ($publicPage in @(
    "about.html",
    "contact.html",
    "extreme-os.html",
    "hypothetical-performance.html",
    "mean-reversion.html",
    "momentum.html",
    "momentum2.html",
    "momentum-stocks.html",
    "privacy.html",
    "refund-cancellation.html",
    "risk-disclosure.html",
    "subscribe.html",
    "terms.html"
)) {
    Assert-Contains $publicPage @('<script src="/site-auth-nav.js?v=2"></script>')
}
foreach ($memberPage in @(
    "api/_member-content/extreme-os.html",
    "api/_member-content/mean-reversion.html",
    "api/_member-content/momentum.html",
    "api/_member-content/momentum2.html",
    "api/_member-content/momentum-stocks.html"
)) {
    Assert-Contains $memberPage @('<script src="/site-auth-nav.js?v=2"></script>')
}
foreach ($memberPage in @(
    "api/_member-content/momentum.html",
    "api/_member-content/momentum2.html",
    "api/_member-content/momentum-stocks.html"
)) {
    Assert-Contains $memberPage @(
        '<script src="/site-auth-nav.js?v=2"></script>',
        'metric-value positive',
        'metric-value negative'
    )
}
Assert-Contains "api/_member-content/momentum.html" @('<h2>Current Partial Month</h2>')
Assert-Contains "api/_member-content/momentum-stocks.html" @(
    '<h2>Current Partial Month</h2>',
    '<div class="metric-label">Current Month Return</div>',
    'title="Partial month-to-date through',
    ' open</td>'
)
Assert-NotContains "api/_member-content/momentum-stocks.html" @(
    '<th>VIX 30d MA</th>',
    '<th>SPY 10d RV</th>',
    '<th>Realized Vol</th>',
    '<th>VIX MA</th>'
)
foreach ($memberPage in @(
    "api/_member-content/momentum.html",
    "api/_member-content/momentum2.html",
    "api/_member-content/momentum-stocks.html"
)) {
    Assert-SectionRowCount $memberPage "Latest 20 Historical Trades" 20
}

Write-Host "Daily publication guard passed. Only approved strategy results changed; site and member UI are protected."
