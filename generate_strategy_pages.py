import argparse
import json
import pandas as pd
from pathlib import Path

from strategy_faq import FAQ_CSS, render_faq
from metric_style import metric_class

PUBLIC_DELAY_HOURS = 96
PUBLIC_TRADE_LIMIT = 50


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
        df["Closed Time ET"] = pd.to_datetime(
            df["Closed Time ET"],
            errors="coerce",
            utc=True
        ).dt.tz_localize(None)

    
    if "Open Time ET" in df.columns:
        df["Open Time ET"] = pd.to_datetime(
            df["Open Time ET"],
            errors="coerce",
            utc=True
        ).dt.tz_localize(None)    
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
    print(open_df.columns.tolist())
    table = open_df[
        [
            "OpenedDate",
            "Symbol",
            "Quantity",
            "AvgPx",
        ]
    ].copy()
    
    table.columns = [
        "Open Time",
        "Symbol",
        "Qty",
        "Entry",
    ]    
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

def build_recent_closed_table(df, limit=50):
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
        "Open Time",
        "Symbol",
        "Description",
        "Side",
        "Qty",
        "Entry",
        "Close Time",
        "Exit",
        "P/L"
    ]

    closed_df["P/L"] = closed_df["P/L"].apply(
        lambda x:
        f'<span class="pnl-pos">${x:,.0f}</span>'
        if float(x) >= 0
        else
        f'<span class="pnl-neg">${x:,.0f}</span>'
    )
    return closed_df.to_html(
        index=False,
        classes="trade-table",
        escape=False
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

.trade-table {
    width:100%;
    border-collapse:collapse;
}

.trade-table th {
    background:#1f2937;
}

.trade-table th,
.trade-table td {
    border:1px solid #374151;
    padding:4px 6px;
    font-size:12px;
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

</head>

<body>

<nav>

<div>
<strong>Extreme Trading Inc.</strong>
</div>

<div>
<a href="index.html">Home</a>
<a href="members.html">Login</a>
</div>

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
    ).head(PUBLIC_TRADE_LIMIT)

    stats = strategy_stats(df)

    summary_path = Path("data/performance_summary.json")
    performance_html = ""
    if output_file == "extreme-os.html" and summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        performance_html = f"""
<div class="card">

<h2>Verified Collective2 Performance</h2>

<div class="performance-grid">
<div class="performance-stat"><div class="performance-label">Annual Return</div><div class="performance-value {metric_class(summary.get('annual_return', 'N/A'))}">{summary.get('annual_return', 'N/A')}</div></div>
<div class="performance-stat"><div class="performance-label">Max Drawdown</div><div class="performance-value {metric_class(summary.get('max_drawdown', 'N/A'))}">{summary.get('max_drawdown', 'N/A')}</div></div>
<div class="performance-stat"><div class="performance-label">Number of Trades</div><div class="performance-value {metric_class(summary.get('number_of_trades', 'N/A'))}">{summary.get('number_of_trades', 'N/A')}</div></div>
<div class="performance-stat"><div class="performance-label">Win Trades %</div><div class="performance-value {metric_class(summary.get('win_trades_pct', 'N/A'))}">{summary.get('win_trades_pct', 'N/A')}</div></div>
</div>

<iframe class="performance-details" src="performance-details.html" title="Extreme OS monthly returns and equity curve" loading="lazy"></iframe>

</div>
"""

    table_html = build_recent_closed_table(
        df,
        PUBLIC_TRADE_LIMIT
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

<h2>Historical Trades</h2>

{table_html}

</div>
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

    body = f"""
<div class="card">

<h1>{title}</h1>

{render_faq("extreme-os", "member")}

</div>

<div class="card">

<h2>Current Open Positions</h2>

{build_open_positions_table()}

</div>

<div class="card">

<h2>Today's Orders</h2>

{build_open_orders_table()}

</div>

<div class="card">

<h2>Recent Closed Trades</h2>

{build_recent_closed_table(df)}

</div>

<div class="card">

<a href="{csv_link}">
Download CSV History
</a>

</div>
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

# Member pages are intentionally not generated from CSV data. Live member
# data is returned only by the authenticated /api/member-data endpoint.
print("Skipped protected member pages.")

print("Done.")
