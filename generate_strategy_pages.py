import argparse
import json
import pandas as pd
from pathlib import Path

from strategy_faq import FAQ_CSS, render_faq
from metric_style import metric_class

PUBLIC_DELAY_HOURS = 96
RECENT_TRADE_LIMIT = 20
MARKET_TIMEZONE = "America/New_York"


def to_market_time(values):
    """Convert Collective2 UTC timestamps to timezone-free New York time."""
    return (
        pd.to_datetime(values, errors="coerce", utc=True)
        .dt.tz_convert(MARKET_TIMEZONE)
        .dt.tz_localize(None)
    )


def format_quantity(value):
    return f"{float(value):,.0f}"


def format_price(value):
    return f"{float(value):,.2f}"


def format_pnl(value):
    if pd.isna(value):
        return "&mdash;"
    amount = float(value)
    css_class = "pnl-pos" if amount >= 0 else "pnl-neg"
    return f'<span class="{css_class}">${amount:,.2f}</span>'


def collective2_disclosure():
    return """
<section class="disclosure-panel" aria-label="Collective2 and risk disclosure">
<h2>Important Collective2 and Risk Disclosure</h2>
<p><strong>Go-forward verified signals, not live account performance.</strong> The signals shown are tracked and verified on a go-forward basis by Collective2; publishers cannot add a backtested history or remove executed signals. They are not a record of trades executed in any specific live brokerage account, and Collective2 requires all displayed performance to be regarded as hypothetical.</p>
<p>Displayed fills may be based on Collective2 real-time quote simulations or, when available, aggregated AutoTrade brokerage fills. Your results may differ materially because of timing, opening gaps, spreads, slippage, liquidity, commissions, fees, position sizing, missed trades, broker restrictions, and other execution differences.</p>
<p>Trading involves substantial risk of loss. Past performance does not guarantee future results, and future drawdowns may exceed historical drawdowns. This information is impersonal research and education—not personalized investment advice, a recommendation, or a guarantee. You remain responsible for every trading decision and order.</p>
<p><a href="https://www.collective2.com/how-we-calculate-hypothetical-results" target="_blank" rel="noopener">How Collective2 calculates hypothetical results</a> · <a href="/hypothetical-performance.html">Hypothetical performance disclosure</a> · <a href="/risk-disclosure.html">Risk disclosure</a></p>
</section>
"""


# ============================================================
# LOAD DATA
# ============================================================

def load_csv(path):
    df = pd.read_csv(path)
    
    df = df.rename(columns={
        "OpenDate": "Open Time ET",
        "CloseDate": "Closed Time ET",
        "ProfitLoss": "Trade P/L",
        "OpenedQuantity": "Qty Open",
        "AvgOpenFillPrice": "Avg Price Open",
        "AvgCloseFillPrice": "Avg Price Close"
    })
    if "Description" in df.columns:
        df["Descrip"] = df["Description"]
        
    #if "OpenSide" in df.columns:
    #    df["Side"] = df["OpenSide"]
    if "OpenSide" in df.columns:
        df["OpenSide"] = df["OpenSide"].replace({
            "1": "Long",
            1: "Long",
            "2": "Short",
            2: "Short"
        })

    if "Closed Time ET" in df.columns:
        df["Closed Time ET"] = to_market_time(df["Closed Time ET"])

    
    if "Open Time ET" in df.columns:
        df["Open Time ET"] = to_market_time(df["Open Time ET"])
    return df




# ============================================================
# STATS
# ============================================================

def strategy_stats(df):

    closed = df[
        df["Trade P/L"].notna()
    ].copy()

    total_trades = len(df)

    open_positions = (
        df["Closed Time ET"]
        .isna()
        .sum()
    )

    win_rate = (
        (closed["Trade P/L"] > 0).mean() * 100
        if len(closed)
        else 0
    )

    avg_trade = (
        closed["Trade P/L"].mean()
        if len(closed)
        else 0
    )

    total_pl = (
        closed["Trade P/L"].sum()
        if len(closed)
        else 0
    )

    return {
        "open_positions": open_positions,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "avg_trade": avg_trade,
        "total_pl": total_pl
    }


# ============================================================
# TABLES
# ============================================================

def build_open_positions_table():
    try:
    
        open_df = pd.read_csv(
            "data/extreme_os_open.csv"
        )
    
    except Exception:
    
        return "<p>No open positions.</p>"
    
    if len(open_df) == 0:
    
        return "<p>No open positions.</p>"
    table = open_df[["OpenedDate", "Symbol", "Quantity", "AvgPx"]].copy()
    quantity = pd.to_numeric(table["Quantity"], errors="coerce").fillna(0)
    price = pd.to_numeric(table["AvgPx"], errors="coerce").fillna(0)
    table.insert(2, "Direction", quantity.apply(lambda value: "Long" if value >= 0 else "Short"))
    table["OpenedDate"] = to_market_time(table["OpenedDate"]).dt.strftime("%Y-%m-%d %H:%M")
    table["Quantity"] = quantity.abs().map(format_quantity)
    table["AvgPx"] = price.map(format_price)
    table["Position Value"] = (quantity.abs() * price).map(format_price)
    table.columns = ["Open Time (ET)", "Symbol", "Direction", "Qty", "Entry", "Position Value"]
    return table.to_html(
        index=False,
        classes="trade-table",
        index_names=False
    )

def build_open_orders_table():

    try:
        orders_df = pd.read_csv(
            "data/extreme_os_orders.csv"
        )
    except (
        FileNotFoundError,
        pd.errors.EmptyDataError
    ):
        orders_df = pd.DataFrame()
    orders_df.columns.tolist()
    if orders_df.empty:
        orders_html = """
        <p>No orders today.</p>
        """
    else:
        orders_html = orders_df.to_html(
            index=False,
            classes="trade-table"
        )
    return orders_html

def build_recent_closed_table(df, limit=RECENT_TRADE_LIMIT):
    closed_df = df[
        df["Closed Time ET"].notna()
    ].copy()
    
    closed_df = closed_df.sort_values(
        "Closed Time ET",
        ascending=False
    ).head(limit)
    
    closed_df = closed_df[
        [
            "Open Time ET",
            "Symbol",
            "Description",
            "OpenSide",
            "Qty Open",
            "Avg Price Open",
            "Closed Time ET",
            "Avg Price Close",
            "Trade P/L"
        ]
    ].copy()
    
    closed_df.columns = [
        "Open Time (ET)",
        "Symbol",
        "Description",
        "Side",
        "Qty",
        "Entry",
        "Close Time (ET)",
        "Exit",
        "P/L"
    ]

    closed_df["Open Time (ET)"] = closed_df["Open Time (ET)"].dt.strftime("%Y-%m-%d %H:%M")
    closed_df["Close Time (ET)"] = closed_df["Close Time (ET)"].dt.strftime("%Y-%m-%d %H:%M")
    closed_df["Qty"] = pd.to_numeric(closed_df["Qty"], errors="coerce").abs().map(format_quantity)
    closed_df["Entry"] = pd.to_numeric(closed_df["Entry"], errors="coerce").map(format_price)
    closed_df["Exit"] = pd.to_numeric(closed_df["Exit"], errors="coerce").map(format_price)
    closed_df["P/L"] = closed_df["P/L"].map(format_pnl)
    return closed_df.to_html(
        index=False,
        classes="trade-table",
        escape=False
    )


def build_todays_trades_table(df):
    closed = df[df["Closed Time ET"].notna()].copy()
    today = pd.Timestamp.now(tz=MARKET_TIMEZONE).tz_localize(None).normalize()
    todays_trades = closed[closed["Closed Time ET"].dt.normalize().eq(today)]
    rows = []
    for _, trade in todays_trades.sort_values("Closed Time ET", ascending=False).iterrows():
        rows.append({
            "Time": trade["Closed Time ET"], "Action": "Close", "Symbol": trade["Symbol"],
            "Direction": trade["OpenSide"], "Qty": abs(float(trade["Qty Open"])),
            "Price": float(trade["Avg Price Close"]), "P/L": trade["Trade P/L"],
        })
    try:
        open_df = pd.read_csv("data/extreme_os_open.csv")
    except (FileNotFoundError, pd.errors.EmptyDataError):
        open_df = pd.DataFrame()
    if not open_df.empty:
        opened = to_market_time(open_df["OpenedDate"])
        new_positions = open_df[opened.dt.normalize().eq(today)].copy()
        for index, position in new_positions.iterrows():
            quantity = float(position["Quantity"])
            rows.append({
                "Time": opened.loc[index], "Action": "Open", "Symbol": position["Symbol"],
                "Direction": "Long" if quantity >= 0 else "Short", "Qty": abs(quantity),
                "Price": float(position["AvgPx"]), "P/L": None,
            })
    if not rows:
        return '<p class="subtle">No trades today.</p>'
    table = pd.DataFrame(rows).sort_values("Time", ascending=False)
    table["Time"] = table["Time"].dt.strftime("%H:%M")
    table["Qty"] = table["Qty"].map(format_quantity)
    table["Price"] = table["Price"].map(format_price)
    table["P/L"] = table["P/L"].map(format_pnl)
    table = table.rename(columns={"Time": "Time (ET)"})
    return table.to_html(
        index=False, classes="trade-table", index_names=False, escape=False
    )



# ============================================================
# HTML TEMPLATE
# ============================================================

CSS = """
body {
    background:#0f172a;
    color:#e5e7eb;
    font-family:Arial,Helvetica,sans-serif;
    margin:0;
}

nav {
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:18px 30px;
    background:#111827;
}

nav a {
    color:white;
    text-decoration:none;
    margin-left:20px;
}

.container {
    width:95%;
    max-width:1400px;
    margin:auto;
    padding:20px;
}

.card {
    background:#111827;
    border:1px solid #374151;
    border-radius:10px;
    padding:20px;
    margin-bottom:20px;
}

.hero,
.panel {
    background:#111827;
    border:1px solid #374151;
    border-radius:12px;
    padding:26px;
    margin-bottom:22px;
}

.eyebrow {
    color:#60a5fa;
    text-transform:uppercase;
    letter-spacing:.12em;
    font-size:12px;
    font-weight:bold;
}

.subtle { color:#94a3b8; }

.metrics {
    display:grid;
    grid-template-columns:repeat(4,minmax(160px,1fr));
    gap:14px;
    margin:22px 0;
}

.metric {
    background:#111827;
    border:1px solid #374151;
    border-radius:10px;
    padding:18px;
}

.metric-label { color:#94a3b8;font-size:13px; }
.metric-value { font-size:24px;font-weight:700;margin-top:6px; }

.trade-table {
    width:100%;
    border-collapse:collapse;
}

.trade-table th {
    background:#1f2937;
    text-align:center;
}

.trade-table th,
.trade-table td {
    border:1px solid #374151;
    padding:4px 6px;
    font-size:15px;
}

.strategy-grid {
    display:flex;
    gap:25px;
    flex-wrap:wrap;
}

.strategy-card {
    flex:1;
    min-width:320px;
    background:#111827;
    border:1px solid #374151;
    border-radius:12px;
    padding:24px;
    text-decoration:none;
    color:#e5e7eb;
}

.strategy-card:hover {
    border-color:#60a5fa;
}

.stat {
    margin-bottom:8px;
}

.performance-grid {
    display:grid;
    grid-template-columns:repeat(4,minmax(0,1fr));
    gap:15px;
}

.performance-stat {
    background:#0f172a;
    border:1px solid #374151;
    border-radius:8px;
    padding:16px;
}

.performance-label {
    color:#9ca3af;
    font-size:13px;
    margin-bottom:6px;
}

.performance-value {
    font-size:22px;
    font-weight:600;
}

.positive { color:#22c55e; }
.negative { color:#f87171; }

.performance-details {
    width:100%;
    height:1180px;
    margin-top:20px;
    border:0;
    background:#111827;
}

@media (max-width:760px) {
    .performance-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
    .metrics { grid-template-columns:repeat(2,minmax(0,1fr)); }
}

.view-link {
    margin-top:15px;
    color:#60a5fa;
    font-weight:bold;
}
.pnl-pos{
    color:#00c853;
    font-weight:600;
}

.pnl-neg{
    color:#ff5252;
    font-weight:600;
}

.disclosure-panel {
    background:#0b1220;
    border:1px solid #374151;
    border-radius:12px;
    color:#cbd5e1;
    font-size:13px;
    line-height:1.55;
    margin-bottom:22px;
    padding:22px 26px;
}

.disclosure-panel h2 {
    color:#f8fafc;
    font-size:18px;
    margin-top:0;
}

.disclosure-panel a {
    color:#60a5fa;
}
"""

CSS += FAQ_CSS


def page_template(title, body):

    return f"""
<!DOCTYPE html>
<html>

<head>

<meta charset="utf-8">

<title>{title}</title>

<style>
{CSS}
</style>
<script src="/site-auth-nav.js?v=5"></script>
</head>

<body>

<nav class="site-nav">
<strong class="brand">Extreme Trading Inc.</strong>
<div class="navlinks"><a href="index.html">Home</a><a href="strategies.html">Strategies</a><a href="subscribe.html">Subscribe</a><a href="members.html">Login</a><a href="about.html">About</a><a href="contact.html">Contact</a></div>
</nav>

<div class="container">

{body}

</div>

</body>

</html>
"""


# ============================================================
# PUBLIC STRATEGY PAGE
# ============================================================

def build_performance_metrics(summary):
    metrics = (
        ("Annual Return", summary.get("annual_return", "N/A")),
        ("Max Drawdown", summary.get("max_drawdown", "N/A")),
        ("Number of Trades", summary.get("number_of_trades", "N/A")),
        ("Win Trades %", summary.get("win_trades_pct", "N/A")),
    )
    cards = "".join(
        f'<div class="metric"><div class="metric-label">{label}</div>'
        f'<div class="metric-value {metric_class(value)}">{value}</div></div>'
        for label, value in metrics
    )
    return f'<section><h2>Verified Collective2 Performance</h2><div class="metrics">{cards}</div></section>'

def generate_public_page(
        csv_file,
        output_file,
        title,
        show_current_positions=False):

    df = load_csv(csv_file)

    cutoff = (
        pd.Timestamp.now()
        - pd.Timedelta(hours=PUBLIC_DELAY_HOURS)
    )

    df = df[
        df["Closed Time ET"] < cutoff
    ]

    df = df.sort_values(
        "Closed Time ET",
        ascending=False
    ).head(RECENT_TRADE_LIMIT)

    stats = strategy_stats(df)

    summary_path = Path("data/performance_summary.json")
    performance_html = ""
    if output_file == "extreme-os.html" and summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        performance_html = build_performance_metrics(summary)

    table_html = build_recent_closed_table(
        df,
        RECENT_TRADE_LIMIT
    )

    current_positions_html = ""
    if show_current_positions:
        current_positions_html = f"""
<div class="card">

<h2>Current Open Positions</h2>

<p>
Current positions are sourced from Collective2 and updated daily.
</p>

{build_open_positions_table()}

</div>
"""

    body = f"""
<div class="card">

<h1>{title}</h1>

<p>
Trades are sourced from Collective2 and updated daily. Public trade details are shown after a 96-hour delay.
</p>

{render_faq("extreme-os", "public")}

</div>

{performance_html}

{current_positions_html}

<div class="card">

<h2>Latest 20 Trades</h2>

{table_html}

</div>

<section class="panel">
<iframe class="performance-details" src="/performance-details.html" title="Extreme OS equity curve and monthly returns" loading="lazy"></iframe>
</section>

{collective2_disclosure()}
"""

    Path(output_file).write_text(
        page_template(title, body),
        encoding="utf-8"
    )

    print(f"Generated {output_file}")


# ============================================================
# MEMBER DETAIL PAGE
# ============================================================

def generate_strategy_member_page(
        df,
        title,
        output_file,
        csv_link):

    summary = json.loads(Path("data/performance_summary.json").read_text(encoding="utf-8"))

    body = f"""
<section class="hero">
<div class="eyebrow">Collective2 go-forward verified track record</div>
<h1>{title}</h1>
<p>Signals are submitted and tracked go-forward by Collective2. Displayed results remain hypothetical and do not represent any specific live brokerage account.</p>

{render_faq("extreme-os", "member")}
</section>

{build_performance_metrics(summary)}

<section class="panel">

<h2>Today's Trades</h2>

{build_todays_trades_table(df)}

</section>

<section class="panel">

<h2>Open Positions</h2>

{build_open_positions_table()}

</section>

<section class="panel">

<h2>Latest 20 Trades</h2>

{build_recent_closed_table(df, RECENT_TRADE_LIMIT)}

</section>

<section class="panel">
<iframe class="performance-details" src="/performance-details.html" title="Extreme OS equity curve and monthly returns" loading="lazy"></iframe>
</section>

{collective2_disclosure()}

"""

    Path(output_file).write_text(
        page_template(title, body),
        encoding="utf-8"
    )

    print(f"Generated {output_file}")


# ============================================================
# MEMBERS DASHBOARD
# ============================================================

def generate_members_dashboard(
        os_df,
        mom_df):

    os_stats = strategy_stats(os_df)
    mom_stats = strategy_stats(mom_df)

    body = f"""
<div class="card">

<h1>Members Dashboard</h1>

<p>
Select a strategy.
</p>

</div>

<div class="strategy-grid">

<a
class="strategy-card"
href="extreme-os-members.html">

<h2>Extreme OS</h2>

<div class="stat">
Open Positions:
{os_stats['open_positions']}
</div>

<div class="stat">
Total Trades:
{os_stats['total_trades']}
</div>

<div class="stat">
Win Rate:
{os_stats['win_rate']:.1f}%
</div>

<div class="stat">
Total P/L:
${os_stats['total_pl']:,.0f}
</div>

<div class="view-link">
View Strategy →
</div>

</a>

<a
class="strategy-card"
href="momentum-members.html">

<h2>Momentum</h2>

<div class="stat">
Open Positions:
{mom_stats['open_positions']}
</div>

<div class="stat">
Total Trades:
{mom_stats['total_trades']}
</div>

<div class="stat">
Win Rate:
{mom_stats['win_rate']:.1f}%
</div>

<div class="stat">
Total P/L:
${mom_stats['total_pl']:,.0f}
</div>

<div class="view-link">
View Strategy →
</div>

</a>

</div>
"""

    Path("members.html").write_text(
        page_template(
            "Members Dashboard",
            body
        ),
        encoding="utf-8"
    )

    print("Generated members.html")


# ============================================================
# MAIN
# ============================================================

parser = argparse.ArgumentParser(
    description="Generate public and member strategy pages."
)
parser.add_argument(
    "--extreme-os-only",
    action="store_true",
    help="Generate only the public Extreme OS page.",
)
args = parser.parse_args()

os_df = load_csv(
    "data/extreme_os.csv"
)

if args.extreme_os_only:
    generate_public_page(
        "data/extreme_os.csv",
        "extreme-os.html",
        "Extreme OS Historical Trades",
        show_current_positions=False
    )
    generate_strategy_member_page(
        os_df,
        "Extreme OS",
        "api/_member-content/extreme-os.html",
        "#",
    )
    print("Done.")
    raise SystemExit(0)

try:
    mom_df = load_csv(
        "data/momentum.csv"
    )
except:
    print(
        "momentum.csv not found. "
        "Using extreme_os.csv as placeholder."
    )

    mom_df = load_csv(
        "data/extreme_os.csv"
    )


generate_public_page(
    "data/extreme_os.csv",
    "extreme-os.html",
    "Extreme OS Historical Trades",
    show_current_positions=False
)

generate_strategy_member_page(
    os_df,
    "Extreme OS",
    "api/_member-content/extreme-os.html",
    "#",
)

print("Done.")
