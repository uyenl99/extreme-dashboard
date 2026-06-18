import pandas as pd
from pathlib import Path

PUBLIC_DELAY_HOURS = 96
PUBLIC_TRADE_LIMIT = 100


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
        
    if "OpenSide" in df.columns:
        df["Side"] = df["OpenSide"]

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
    
    table = open_df[
        [
            "OpenedDate",
            "Symbol",
            "Description",
            "Quantity",
            "AvgPx"
        ]
    ].copy()
    
    table.columns = [
        "Open Time",
        "Symbol",
        "Description",
        "Qty",
        "Entry"
    ]
    
    return table.to_html(
        index=False,
        classes="trade-table",
        index_names=False
    )

def build_open_orders_table(df):

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
        "P/L"
    ]
    
    return closed_df.to_html(
        index=False,
        classes="trade-table"
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

.view-link {
    margin-top:15px;
    color:#60a5fa;
    font-weight:bold;
}
"""


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
<a href="performance.html">Performance</a>
<a href="strategies.html">Strategies</a>
<a href="members.html">Members</a>
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
        title):

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

    table_html = build_recent_closed_table(
        df,
        PUBLIC_TRADE_LIMIT
    )

    body = f"""
<div class="card">

<h1>{title}</h1>

<p>
Historical trades delayed 96 hours.
</p>

</div>

<div class="card">

<div class="stat">
Total Trades: {stats['total_trades']}
</div>

<div class="stat">
Win Rate: {stats['win_rate']:.1f}%
</div>

<div class="stat">
Average Trade: ${stats['avg_trade']:,.2f}
</div>

<div class="stat">
Total P/L: ${stats['total_pl']:,.0f}
</div>

</div>

<div class="card">

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

os_df = load_csv(
    "data/extreme_os.csv"
)

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
    "Extreme OS Historical Trades"
)

generate_public_page(
    "data/extreme_os.csv",
    "momentum.html",
    "Momentum Historical Trades"
)

generate_strategy_member_page(
    os_df,
    "Extreme OS Members",
    "extreme-os-members.html",
    "data/extreme_os.csv"
)

generate_strategy_member_page(
    mom_df,
    "Momentum Members",
    "momentum-members.html",
    "data/extreme_os.csv"
)

generate_members_dashboard(
    os_df,
    mom_df
)

print("Done.")
