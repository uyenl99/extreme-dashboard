import os
import requests

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

print("STATUS:", r.status_code)
print(r.text[:10000])

with open("index.html", "w", encoding="utf-8") as f:
    f.write(f"""
    <h1>Daily Equity Test</h1>
    <p>Status: {r.status_code}</p>
    <pre>{r.text[:5000]}</pre>
    """)
