import pandas as pd
from pathlib import Path

PUBLIC_DELAY_HOURS = 96
PUBLIC_TRADE_LIMIT = 100

CSV_FILE = "data/extreme_os.csv"
OUTPUT_FILE = "extreme-os.html"

def build_open_positions_table(df):

    open_df = df[
        df["Closed Time ET"].isna()
    ][[
        "Open Time ET",
        "Symbol",
        "Descrip",
        "Side",
        "Qty Open",
        "Avg Price Open"
    ]].copy()

    open_df.columns = [
        "Open Time",
        "Symbol",
        "Description",
        "Side",
        "Qty",
        "Entry"
    ]

    return open_df.to_html(
        index=False,
        classes="trade-table"
    )


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
            "Descrip",
            "Side",
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

# Load CSV
df = pd.read_csv(CSV_FILE)

# Convert close time
df["Closed Time ET"] = pd.to_datetime(
    df["Closed Time ET"],
    errors="coerce"
)

# Apply 96-hour delay
cutoff = (
    pd.Timestamp.now()
    - pd.Timedelta(hours=PUBLIC_DELAY_HOURS)
)

df = df[
    df["Closed Time ET"] < cutoff
]

# Most recent trades first
df = df.sort_values(
    "Closed Time ET",
    ascending=False
)

# Limit to latest 100
df = df.head(PUBLIC_TRADE_LIMIT)

# Select display columns
display_df = df[
    [
        "Open Time ET",
        "Symbol",
        "Descrip",
        "Side",
        "Qty Open",
        "Avg Price Open",
        "Closed Time ET",
        "Trade P/L"
    ]
].copy()

display_df.columns = [
    "Open Time",
    "Symbol",
    "Description",
    "Side",
    "Qty",
    "Entry",
    "Close Time",
    "P/L"
]

# Summary statistics
total_trades = len(df)

winning_trades = len(
    df[df["Trade P/L"] > 0]
)

win_rate = (
    winning_trades / total_trades * 100
    if total_trades > 0
    else 0
)

total_pl = df["Trade P/L"].sum()

avg_trade = df["Trade P/L"].mean()

table_html = display_df.to_html(
    index=False,
    classes="trade-table"
)

html = f"""
<!DOCTYPE html>
<html>

<head>

<meta charset="utf-8">

<title>Extreme OS Historical Trades</title>

<style>

body {{
    background:#0f172a;
    color:#e5e7eb;
    font-family:Arial,Helvetica,sans-serif;
    margin:0;
}}

nav {{
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:18px 30px;
    background:#111827;
}}

nav a {{
    color:white;
    text-decoration:none;
    margin-left:20px;
}}

.container {{
    width:95%;
    max-width:1400px;
    margin:auto;
    padding:20px;
}}

.card {{
    background:#111827;
    border:1px solid #374151;
    border-radius:10px;
    padding:20px;
    margin-bottom:20px;
}}

.stats {{
    display:flex;
    gap:20px;
    flex-wrap:wrap;
}}

.stat {{
    background:#1f2937;
    padding:15px;
    border-radius:8px;
    min-width:180px;
}}

.trade-table {{
    width:100%;
    border-collapse:collapse;
}}

.trade-table th {{
    background:#1f2937;
}}

.trade-table th,
.trade-table td {{
    border:1px solid #374151;
    padding:4px 6px;
    font-size:12px;
}}

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

<div class="card">

<h1>Extreme OS Historical Trades</h1>

<p>
Public trade history delayed 96 hours.
</p>

</div>

<div class="card">

<div class="stats">

<div class="stat">
<b>Total Trades</b><br>
{total_trades}
</div>

<div class="stat">
<b>Win Rate</b><br>
{win_rate:.1f}%
</div>

<div class="stat">
<b>Total P/L</b><br>
{total_pl:,.2f}
</div>

<div class="stat">
<b>Average Trade</b><br>
{avg_trade:,.2f}
</div>

</div>

</div>

<div class="card">

{table_html}

</div>

</div>

</body>

</html>
"""

Path(OUTPUT_FILE).write_text(
    html,
    encoding="utf-8"
)

print("Generated extreme-os.html")


def generate_members_page():

    os_df = pd.read_csv(
        "data/extreme_os.csv"
    )

    mom_df = pd.read_csv(
        "data/momentum.csv"
    )

    os_df["Closed Time ET"] = pd.to_datetime(
        os_df["Closed Time ET"],
        errors="coerce"
    )

    mom_df["Closed Time ET"] = pd.to_datetime(
        mom_df["Closed Time ET"],
        errors="coerce"
    )

    html = f"""
<!DOCTYPE html>
<html>

<head>

<meta charset="utf-8">

<title>Members Dashboard</title>

<style>

body {{
    background:#0f172a;
    color:#e5e7eb;
    font-family:Arial,Helvetica,sans-serif;
    margin:0;
}}

nav {{
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:18px 30px;
    background:#111827;
}}

nav a {{
    color:white;
    text-decoration:none;
    margin-left:20px;
}}

.container {{
    width:95%;
    max-width:1400px;
    margin:auto;
    padding:20px;
}}

.card {{
    background:#111827;
    border:1px solid #374151;
    border-radius:10px;
    padding:20px;
    margin-bottom:20px;
}}

.trade-table {{
    width:100%;
    border-collapse:collapse;
}}

.trade-table th {{
    background:#1f2937;
}}

.trade-table th,
.trade-table td {{
    border:1px solid #374151;
    padding:4px 6px;
    font-size:12px;
}}

a {{
    color:#60a5fa;
}}

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

<div class="card">

<h1>Members Dashboard</h1>

<p>
Current positions, recent trades, and downloadable history.
</p>

</div>

<div class="card">

<h2>
Current Extreme OS Positions
({len(os_df[os_df['Closed Time ET'].isna()])})
</h2>

{build_open_positions_table(os_df)}

</div>

<div class="card">

<h2>
Current Momentum Positions
({len(mom_df[mom_df['Closed Time ET'].isna()])})
</h2>

{build_open_positions_table(mom_df)}

</div>

<div class="card">

<h2>Recent Extreme OS Closed Trades</h2>

{build_recent_closed_table(os_df)}

</div>

<div class="card">

<h2>Recent Momentum Closed Trades</h2>

{build_recent_closed_table(mom_df)}

</div>

<div class="card">

<h2>Downloads</h2>

<p>
<a href="data/extreme_os.csv">
Download Extreme OS History
</a>
</p>

<p>
<a href="data/momentum.csv">
Download Momentum History
</a>
</p>

</div>

</div>

</body>

</html>
"""

    Path("members.html").write_text(
        html,
        encoding="utf-8"
    )

    print("Generated members.html")

generate_members_page()
