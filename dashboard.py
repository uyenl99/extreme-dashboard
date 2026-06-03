import os
import requests

API_KEY = os.environ["C2_API_KEY"]

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

url = "https://api4-general.collective2.com/General/GetAccessKey"

r = requests.get(url, headers=headers)

print("STATUS:", r.status_code)
print("TEXT:")
print(r.text[:2000])

with open("index.html", "w", encoding="utf-8") as f:
    f.write(f"""
    <h1>API Test</h1>
    <p>Status: {r.status_code}</p>
    <pre>{r.text[:500]}</pre>
    """)
