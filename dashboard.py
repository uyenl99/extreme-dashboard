import argparse
import os
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from datetime import timedelta
from pathlib import Path

Path("data").mkdir(exist_ok=True)
API_KEY = os.environ["C2_API_KEY"]
STRATEGY_ID = 13202557
REQUEST_TIMEOUT_SECONDS = 30

parser = argparse.ArgumentParser(
    description="Refresh Collective2 performance and optional trade data."
)
parser.add_argument(
    "--performance-only",
    action="store_true",
    help="Regenerate performance.html without downloading trade/member data.",
)
args = parser.parse_args()

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

url = "https://api4-general.collective2.com/Strategies/GetStrategyHistoricalDailyEquity"

params = {
    "StrategyId": 13202557,
    "CommissionPlan": 0
}

r = requests.get(
    url,
    headers=headers,
    params=params,
    timeout=REQUEST_TIMEOUT_SECONDS,
)
r.raise_for_status()

data = r.json()
if not data.get("Results") or not data["Results"][0].get("DailyEquity"):
    raise RuntimeError("Collective2 returned no daily equity history")
daily = data["Results"][0]["DailyEquity"]
df = pd.DataFrame(daily)
df["Date"] = pd.to_datetime(df["Date"])

fig = go.Figure()
fig.update_layout(
    template="plotly_dark",
    height=550,
    margin=dict(
        l=40,
        r=20,
        t=30,
        b=40
    )
)
fig.add_trace(
    go.Scatter(
        x=df["Date"],
        y=df["EquityWithCosts"],
        mode="lines",
        name="Equity With Costs"
    )
)
fig.update_xaxes(
    dtick="M12",
    tickformat="%Y"
)

monthly_url = "https://api4-general.collective2.com/Strategies/GetStrategyHistoricalEquity"
monthly_params = {
    "StrategyId": 13202557,
    "CommissionPlan": 0
}
monthly_r = requests.get(
    monthly_url,
    headers=headers,
    params=monthly_params,
    timeout=REQUEST_TIMEOUT_SECONDS,
)
monthly_r.raise_for_status()
monthly_data = monthly_r.json()
if not monthly_data.get("Results") or not monthly_data["Results"][0].get("MonthlyResults"):
    raise RuntimeError("Collective2 returned no monthly performance history")
#print("MONTHLY STATUS:", monthly_r.status_code)
#print(
#    monthly_data["Results"][0].keys()
#)
chart_html = fig.to_html(
    full_html=False,
    include_plotlyjs="cdn"
)
monthly_results = monthly_data["Results"][0]["MonthlyResults"]
#print("MONTHLY COUNT:", len(monthly_results))
#print("FIRST RECORD:", monthly_results[0])
#print("SECOND RECORD:", monthly_results[1])

rows = []
for item in monthly_results:
    if item.get("IsAnnual"):
        continue

    rows.append({
        "Year": item["Year"],
        "Month": item["Month"],
        "Return": item["Return"]
    })

mdf = pd.DataFrame(rows)

pivot = pd.pivot_table(
    mdf,
    index="Year",
    columns="Month",
    values="Return",
    aggfunc="first"
)
pivot = pivot.sort_index(ascending=False)
#print("MDF SHAPE:", mdf.shape)
#print("PIVOT SHAPE:", pivot.shape)
'''
annual_returns = (
    mdf.groupby("Year")["Return"]
       .apply(lambda x: ((1 + x/100).prod() - 1) * 100)
)

pivot["Annual"] = annual_returns
'''
pivot["Annual"] = pivot.apply(
    lambda row: ((1 + row.dropna()/100).prod() - 1) * 100,
    axis=1
)

start_equity = float(df["EquityWithCosts"].iloc[0])
current_equity = float(df["EquityWithCosts"].iloc[-1])

total_return = (
    (current_equity / start_equity) - 1
) * 100

start_date = df["Date"].min().strftime("%Y-%m-%d")
last_date = df["Date"].max().strftime("%Y-%m-%d")


table_html = (
    pivot.style
    .format("{:.2f}")
    .map(lambda v:
        "color: green; font-weight: bold"
        if pd.notna(v) and v > 0
        else (
            "color: red; font-weight: bold"
            if pd.notna(v) and v < 0
            else ""
        )
    )
    .set_table_attributes('class="returns-table"')
    .to_html()
)
table_html = table_html.replace(
    ">Annual<",
    ' style="background:#e8eefc;font-weight:bold;">Annual<'
)

###############################################################
def download_closed_trades():
    
    url = (
        "https://api4-general.collective2.com/"
        "Strategies/GetStrategyHistoricalClosedTrades"
    )
    
    params = {
        "StrategyId": STRATEGY_ID,
        "CommissionPlan": 0
    }
    
    r = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    
    r.raise_for_status()
    
    data = r.json()
    
    trades = data["Results"]
    
    df = pd.DataFrame(trades)
    df["Symbol"] = df["C2Symbol"].apply(
        lambda x: x.get("FullSymbol", "")
        if isinstance(x, dict)
        else ""
    )
    
    df["Description"] = df["C2Symbol"].apply(
        lambda x: x.get("Description", "")
        if isinstance(x, dict)
        else ""
    )
    
    df["Description"] = df["Description"].fillna("")
    df["Description"] = df.apply(
        lambda r: r["Symbol"]
        if str(r["Description"]).strip() == ""
        else r["Description"],
        axis=1
    )
    #print(df.columns.tolist())
    #print(df[["Symbol", "Description"]].head(10))
    #print(df.iloc[0]["C2Symbol"])
    #print(type(df["C2Symbol"].iloc[0]))
    
    df.to_csv(
        "data/extreme_os.csv",
        index=False
    )
    
    print(
        f"Saved {len(df)} closed trades"
    )
    


#################################################
def download_open_positions():
    url = (
        "https://api4-general.collective2.com/"
        "Strategies/GetStrategyOpenPositions"
    )
    params = {
        "StrategyIds": STRATEGY_ID
    }
    r = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    r.raise_for_status()
    data = r.json()
    positions = data["Results"]
    df = pd.DataFrame(
        positions
    )
    if df.empty:
        df.to_csv(
            "data/extreme_os_open.csv",
            index=False
        )
        print("Saved 0 open positions")
        return
    df["Symbol"] = df["C2Symbol"].apply(
        lambda x: x.get("FullSymbol", "")
        if isinstance(x, dict)
        else ""
    )
    df["Description"] = df["C2Symbol"].apply(
        lambda x: x.get("Description", "")
        if isinstance(x, dict)
        else ""
    )
    
    df["Description"] = df["Description"].fillna("")
    df["Description"] = df.apply(
        lambda r: r["Symbol"]
        if str(r["Description"]).strip() == ""
        else r["Description"],
        axis=1
    )    
    #print(df.columns.tolist())
    #print(df[["Symbol", "Description"]].head(10))
    #print(df.iloc[0]["C2Symbol"])
    df.to_csv(
        "data/extreme_os_open.csv",
        index=False
    )

    print(
        "Saved",
        len(df),
        "open positions"
    )
################################################
def download_orders():
    today = datetime.utcnow()
    start_date = today.strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")
    url = (
        "https://api4-general.collective2.com/"
        "Strategies/GetStrategyHistoricalOrders"
    )
    params = {
        "StrategyId": STRATEGY_ID,
        "StartDate": start_date,
        "EndDate": end_date
    }
    r = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    r.raise_for_status()
    data = r.json()
    
    orders = data["Results"]
    df = pd.DataFrame(orders)
    if "C2Symbol" in df.columns:
        df["Symbol"] = df["C2Symbol"].apply(
            lambda x:
                x.get("Underlying", "")
                if isinstance(x, dict)
                else ""
        )
    
        df["Description"] = df["C2Symbol"].apply(
            lambda x:
                x.get("Description", "")
                if isinstance(x, dict)
                else ""
        )
    
    df.to_csv(
        "data/extreme_os_orders.csv",
        index=False
    )
    
    print(
        f"Saved {len(df)} orders"
    )

#########################################
html = f"""
<html>

<head>

<title>Extreme OS Dashboard</title>

<style>
.returns-table {{
    width: 100%;
    border-collapse: collapse;
    background: white;
}}

.returns-table td {{
    padding: 2px 6px;
    font-size:12px;
}}
.returns-table th {{
    padding: 4px 6px;
    font-size:12px;
}}
.positive {{
    color: #22c55e;
    font-weight: bold;
}}
.negative {{
    color: #ef4444;
    font-weight: bold;
}}

.annual-col {{
    font-weight: bold;
    background: #f2f2f2;
}}

body {{
    font-family: Arial, Helvetica, sans-serif;
    font-size:14px;
    max-width: 1400px;
    margin: auto;
    padding: 20px;
    background:#0f172a;
    color:#e5e7eb;    
}}

h1 {{
    text-align:center;
}}

.cards {{
    display:flex;
    gap:20px;
    margin-bottom:25px;
}}

.card {{
    flex:1;
    padding:20px;
    border-radius:10px;
    box-shadow:0 2px 8px rgba(0,0,0,.1);
    background:#111827;
    color:#e5e7eb;
    border:1px solid #374151;
}}

.card-value {{
    font-size:22px;
    font-weight:600;
}}

table {{
    width:100%;
    border-collapse:collapse;
    background:white;
}}

.returns-table {{
    border-collapse: collapse;
}}

.returns-table td {{
    background:#111827;
    color:#e5e7eb;
    border:1px solid #374151;
}}

.returns-table th {{
    background:#1f2937;
    color:white;
    border:1px solid #374151;
}}

th {{
    background:#222;
    color:white;
}}

td, th {{
    padding:8px;
    border:1px solid #ddd;
    text-align:right;
}}

td:first-child,
th:first-child {{
    text-align:center;
}}

nav {{
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:18px 25px;
    background:#111827;
    margin:-20px -20px 25px -20px;
}}

nav a {{
    color:white;
    text-decoration:none;
    margin-left:20px;
    font-size:14px;
}}
</style>

</head>

<body>
<nav>
<div><strong>Extreme Trading Inc.</strong></div>

<div>
<a href="index.html">Home</a>
<a href="performance.html">Performance</a>
<a href="strategies.html">Strategies</a>
<a href="subscribe.html">Subscribe</a>
<a href="members.html">Members</a>
<a href="about.html">About</a>
<a href="contact.html">Contact</a>
</div>
</nav>
<h1>Performance Report</h1>

<p style="text-align:center;color:#666;margin-top:-10px;">
Verified Collective2 Performance
</p>
<div class="cards">

<div class="card">
<div>Current Equity</div>
<div class="card-value">
${current_equity:,.0f}
</div>
</div>

<div class="card">
<div>Total Return</div>
<div class="card-value">
{total_return:.1f}%
</div>
</div>

<div class="card">
<div>Start Date</div>
<div class="card-value">
{start_date}
</div>
</div>

<div class="card">
<div>Last Update</div>
<div class="card-value">
{last_date}
</div>
</div>

</div>
<h2>Monthly Returns (%)</h2>
{table_html}

<h2>Equity Curve</h2>
{chart_html}



</body>
</html>
"""

with open("performance.html", "w", encoding="utf-8") as f:
    f.write(html)
  
print("INDEX.HTML WRITTEN")

if not args.performance_only:
    download_closed_trades()
    download_open_positions()
    download_orders()
