import argparse
import json
import os
import requests
import pandas as pd
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from strategy_chart import build_equity_drawdown_chart

Path("data").mkdir(exist_ok=True)
API_KEY = os.environ["C2_API_KEY"]
STRATEGY_ID = 13202557
REQUEST_TIMEOUT_SECONDS = 30
MARKET_TIMEZONE = "America/New_York"

parser = argparse.ArgumentParser(
    description="Refresh Collective2 performance and optional trade data."
)
parser.add_argument(
    "--performance-only",
    action="store_true",
    help="Refresh the public performance summary without downloading trade/member data.",
)
parser.add_argument(
    "--public-strategy-data",
    action="store_true",
    help="Refresh closed trades and open positions, but skip private order data.",
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
df["Date"] = (
    pd.to_datetime(df["Date"], errors="coerce", utc=True)
    .dt.tz_convert(MARKET_TIMEZONE)
    .dt.tz_localize(None)
    .dt.normalize()
)
if df["Date"].isna().any():
    raise RuntimeError("Collective2 returned an invalid daily equity timestamp")

def download_spy_equity(start_date, end_date, starting_equity):
    """Download daily SPY closes without requiring another paid API key."""
    period1 = int(pd.Timestamp(start_date, tz="UTC").timestamp())
    period2 = int((pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=2)).timestamp())
    response = requests.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/SPY",
        params={"period1": period1, "period2": period2, "interval": "1d", "events": "history"},
        headers={"User-Agent": "Mozilla/5.0 ExtremeTradingDashboard/1.0"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    result = response.json().get("chart", {}).get("result")
    if not result:
        raise RuntimeError("Yahoo Finance returned no SPY history")
    result = result[0]
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators", {})
    adjusted = (indicators.get("adjclose") or [{}])[0].get("adjclose")
    raw_closes = (indicators.get("quote") or [{}])[0].get("close") or []
    adjusted_series = pd.Series(adjusted or [], dtype="float64").reindex(range(len(timestamps)))
    raw_series = pd.Series(raw_closes, dtype="float64").reindex(range(len(timestamps)))
    closes = adjusted_series.fillna(raw_series)
    spy = pd.DataFrame({
        "Date": (
            pd.to_datetime(timestamps, unit="s", utc=True)
            .tz_convert(MARKET_TIMEZONE)
            .tz_localize(None)
            .normalize()
        ),
        "SPY_Close": closes.to_numpy(),
    }).dropna()
    meta = result.get("meta", {})
    meta_price = pd.to_numeric(meta.get("regularMarketPrice"), errors="coerce")
    meta_time = pd.to_numeric(meta.get("regularMarketTime"), errors="coerce")
    if pd.notna(meta_price) and pd.notna(meta_time):
        meta_date = (
            pd.to_datetime(meta_time, unit="s", utc=True)
            .tz_convert(MARKET_TIMEZONE)
            .tz_localize(None)
            .normalize()
        )
        if pd.Timestamp(start_date) <= meta_date <= pd.Timestamp(end_date):
            spy = pd.concat(
                [spy, pd.DataFrame([{"Date": meta_date, "SPY_Close": float(meta_price)}])],
                ignore_index=True,
            )
    spy = spy.sort_values("Date").drop_duplicates("Date", keep="last")
    if spy.empty:
        raise RuntimeError("Yahoo Finance returned no usable SPY closes")
    spy["SPY_Equity"] = float(starting_equity) * spy["SPY_Close"] / spy["SPY_Close"].iloc[0]
    return spy[["Date", "SPY_Equity"]]


spy_daily = download_spy_equity(df["Date"].min(), df["Date"].max(), df["EquityWithCosts"].iloc[0])
chart_data = df[["Date", "EquityWithCosts"]].merge(spy_daily, on="Date", how="inner")
if chart_data.empty or chart_data["Date"].max() < df["Date"].max():
    c2_date = df["Date"].max()
    spy_date = spy_daily["Date"].max() if not spy_daily.empty else None
    chart_date = chart_data["Date"].max() if not chart_data.empty else None
    raise RuntimeError(
        "SPY comparison data does not reach the latest Collective2 equity date: "
        f"C2={c2_date}, SPY={spy_date}, merged={chart_date}"
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
chart_html = build_equity_drawdown_chart(
    chart_data["Date"],
    chart_data["EquityWithCosts"],
    chart_data["SPY_Equity"],
    "Extreme OS",
    "extreme-os-equity-chart",
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

elapsed_years = max((df["Date"].max() - df["Date"].min()).days / 365.2425, 1 / 365.2425)
annual_return = ((current_equity / start_equity) ** (1 / elapsed_years) - 1) * 100
running_peak = df["EquityWithCosts"].cummax()
max_drawdown = ((df["EquityWithCosts"] / running_peak) - 1).min() * 100

daily_returns = pd.to_numeric(df["EquityWithCosts"], errors="coerce").pct_change(fill_method=None).dropna()
daily_volatility = daily_returns.std(ddof=1)
sharpe_ratio = (
    (daily_returns.mean() / daily_volatility) * (252 ** 0.5)
    if len(daily_returns) > 1 and pd.notna(daily_volatility) and daily_volatility > 0
    else 0.0
)

equity_since_2013 = df.loc[
    df["Date"] >= pd.Timestamp("2013-01-01"),
    "EquityWithCosts",
]
if equity_since_2013.empty:
    raise RuntimeError("Collective2 equity history does not include 2013 or later")
peak_since_2013 = equity_since_2013.cummax()
max_drawdown_since_2013 = ((equity_since_2013 / peak_since_2013) - 1).min() * 100

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
    font-size:15px;
}}
.returns-table th {{
    padding: 4px 6px;
    font-size:15px;
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
<nav class="site-nav">
<strong class="brand">Extreme Trading Inc.</strong>
<div class="navlinks"><a href="index.html">Home</a><a href="strategies.html">Strategies</a><a href="subscribe.html">Subscribe</a><a href="members.html">Login</a><a href="about.html">About</a><a href="contact.html">Contact</a></div>
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

Path("performance-details.html").write_text(
    f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{{margin:0;background:#111827;color:#e5e7eb;font-family:Arial,Helvetica,sans-serif;font-size:14px}}
h2{{margin:20px 0 12px}}
table{{width:100%;border-collapse:collapse}}
.returns-table td{{padding:2px 6px;font-size:15px;background:#111827;color:#e5e7eb;border:1px solid #374151}}
.returns-table th{{padding:4px 6px;font-size:15px;background:#1f2937;color:white;border:1px solid #374151}}
th{{text-align:center}}
td{{text-align:right}}
td:first-child{{text-align:center}}
</style>
</head>
<body>
<h2>Equity Curve</h2>
{chart_html}
<h2>Monthly Returns (%)</h2>
{table_html}
</body>
</html>
""",
    encoding="utf-8",
)

print("PERFORMANCE SUMMARY WRITTEN")

if args.public_strategy_data:
    download_closed_trades()
    download_open_positions()
elif not args.performance_only:
    download_closed_trades()
    download_open_positions()
    download_orders()

closed_trades = pd.read_csv("data/extreme_os.csv")
trade_pl = pd.to_numeric(closed_trades.get("ProfitLoss"), errors="coerce").dropna()
number_of_trades = int(len(trade_pl))
win_trades_pct = (trade_pl.gt(0).mean() * 100) if number_of_trades else 0.0

Path("data/performance_summary.json").write_text(
    json.dumps({
        "current_equity": f"${current_equity:,.0f}",
        "total_return": f"{total_return:.1f}%",
        "annual_return": f"{annual_return:.1f}%",
        "sharpe_ratio": f"{sharpe_ratio:.2f}",
        "max_drawdown": f"{max_drawdown:.1f}%",
        "max_drawdown_since_2013": f"{max_drawdown_since_2013:.1f}%",
        "number_of_trades": f"{number_of_trades:,}",
        "win_trades_pct": f"{win_trades_pct:.1f}%",
        "start_date": str(start_date),
        "last_update": str(last_date),
    }, indent=2) + "\n",
    encoding="utf-8",
)
