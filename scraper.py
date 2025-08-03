import requests
import json

url = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
params = {
    "platformCodename": "www",
    "sectionCodename": "oles-oi-tainies-1"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Referer": "https://www.ertflix.gr/",
    "X-Api-Date-Format": "iso",
    "X-Api-Camel-Case": "true"
}

r = requests.get(url, params=params, headers=headers)
print(f"🔎 Status: {r.status_code}\n")

try:
    data = r.json()
    print("🔍 Κορυφή JSON:\n", json.dumps(data, indent=2)[:1500])
except Exception as e:
    print("❌ JSON parse error:", e)
    print("Response text:\n", r.text[:1000])
