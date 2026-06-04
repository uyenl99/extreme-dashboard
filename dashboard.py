import os
import requests
import pandas as pd
import plotly.graph_objects as go

API_KEY = os.environ["C2_API_KEY"]

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
    params=params
)

data = r.json()

daily = data["Results"][0]["DailyEquity"]

df = pd.DataFrame(daily)

df["Date"] = pd.to_datetime(df["Date"])

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=df["Date"],
        y=df["EquityWithCosts"],
        mode="lines",
        name="Equity With Costs"
    )
)

monthly_url = "https://api4-general.collective2.com/Strategies/GetStrategyHistoricalEquity"

monthly_params = {
    "StrategyId": 13202557,
    "CommissionPlan": 0
}

monthly_r = requests.get(
    monthly_url,
    headers=headers,
    params=monthly_params
)

monthly_data = monthly_r.json()
print("MONTHLY STATUS:", monthly_r.status_code)

print(
    monthly_data["Results"][0].keys()
)

chart_html = fig.to_html(
    full_html=False,
    include_plotlyjs="cdn"
)

monthly_results = monthly_data["Results"][0]["MonthlyResults"]
print("MONTHLY COUNT:", len(monthly_results))
print("FIRST RECORD:", monthly_results[0])
print("SECOND RECORD:", monthly_results[1])

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
print("MDF SHAPE:", mdf.shape)
print("PIVOT SHAPE:", pivot.shape)


start_equity = float(df["EquityWithCosts"].iloc[0])
current_equity = float(df["EquityWithCosts"].iloc[-1])

total_return = (
    (current_equity / start_equity) - 1
) * 100

start_date = df["Date"].min().strftime("%Y-%m-%d")
last_date = df["Date"].max().strftime("%Y-%m-%d")

html = f"""
<html>

<head>

<title>Extreme OS Dashboard</title>

<style>

body {{
    font-family: Arial, sans-serif;
    max-width: 1400px;
    margin: auto;
    padding: 20px;
    background: #f5f7fa;
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
    background:white;
    padding:20px;
    border-radius:10px;
    box-shadow:0 2px 8px rgba(0,0,0,.1);
}}

.card-value {{
    font-size:30px;
    font-weight:bold;
}}

table {{
    width:100%;
    border-collapse:collapse;
    background:white;
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

</style>

</head>

<body>

<h1>Extreme OS</h1>

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

<h2>Equity Curve</h2>

{chart_html}

<h2>Monthly Returns (%)</h2>

{pivot.to_html(float_format=lambda x: f"{x:.2f}")}

</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
    


print("INDEX.HTML WRITTEN")
