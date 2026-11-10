
import os
import requests

TOKEN = os.getenv("GFW_API_TOKEN")

if not TOKEN:
    raise RuntimeError("GFW_API_TOKEN introuvable")

url = "https://gateway.api.globalfishingwatch.org/v3/vessels/search"

params = {
    "query": "7831410",
    "datasets[0]": "public-global-vessel-identity:latest",
}

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
}

response = requests.get(
    url,
    params=params,
    headers=headers,
    timeout=30,
)

print("HTTP Status:", response.status_code)
print(response.text)
