import os
import requests
import pandas as pd
import plotly.graph_objects as go

API_KEY = os.environ["C2_API_KEY"]

STRATEGY_ID = 13202557

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

url = (
    f"https://api.collective2.com/world/apiv4/"
    f"strategy/{STRATEGY_ID}/historical-equity"
)

r = requests.get(url, headers=headers)

print("Status:", r.status_code)

data = r.json()

print(data)

# temporary page so we know script ran
html = """
<h1>Collective2 Connection Successful</h1>
<p>If you see this page, GitHub Actions ran.</p>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
