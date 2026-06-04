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

chart_html = fig.to_html(
    full_html=False,
    include_plotlyjs="cdn"
)

html = f"""
<html>
<head>
<title>Extreme Trading Dashboard</title>
</head>

<body>

<h1>Extreme OS</h1>

<h2>Equity Curve</h2>

{chart_html}

<p>
Last Update: {df['Date'].max()}
</p>

</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
