import json
import urllib.request

BASE_URL = "http://localhost:8000/api/v1"

endpoints = {
    "/news?limit=5": f"{BASE_URL}/news?limit=5",
    "/news?limit=7&sort_by=trending": f"{BASE_URL}/news?limit=7&sort_by=trending",
    "/news?limit=5&sort_by=freshness": f"{BASE_URL}/news?limit=5&sort_by=freshness",
    "/recommendations/feed?limit=7": f"{BASE_URL}/recommendations/feed?limit=7",
    "/news/trends": f"{BASE_URL}/news/trends"
}

mock_data = {}

for key, url in endpoints.items():
    print(f"Fetching {url}...")
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            mock_data[key] = data
            print(f"Successfully fetched data for {key}")
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")

# Save to public/mock_data.json
out_path = "frontend/public/mock_data.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(mock_data, f, indent=2)

print(f"Mock data written to {out_path}")
