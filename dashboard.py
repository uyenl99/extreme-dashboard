import os
import requests

API_KEY = os.environ["C2_API_KEY"]

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

url = "https://api.collective2.com/world/apiv4"

r = requests.get(url, headers=headers)

print("STATUS:", r.status_code)
print("TEXT:")
print(r.text[:500])

with open("index.html", "w") as f:
    f.write(f"<h1>Status {r.status_code}</h1>")
