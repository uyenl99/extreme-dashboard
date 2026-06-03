import os
import requests

API_KEY = os.environ["C2_API_KEY"]

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

url = "https://api4-general.collective2.com/Strategies/GetStrategyHistoricalEquity"

params = {
    "StrategyId": 13202557,
    "CommissionPlan": 0
}

r = requests.get(
    url,
    headers=headers,
    params=params
)

print("STATUS:", r.status_code)
print(r.text[:3000])

with open("index.html", "w", encoding="utf-8") as f:
    f.write(f"""
    <html>
    <head>
        <title>Extreme Trading Dashboard</title>
    </head>
    <body>
        <h1>Extreme Trading Dashboard</h1>

        <h2>Strategy ID: 13202557</h2>

        <p>
        Collective2 API Connected Successfully
        </p>

        <p>
        Retrieved Monthly Return History
        </p>

        <pre>{r.text[:3000]}</pre>

    </body>
    </html>
    """)
