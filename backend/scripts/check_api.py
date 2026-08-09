import requests
import json

try:
    response = requests.get("http://localhost:8000/api/v1/news")
    res_data = response.json()
    articles = res_data.get("data", [])
    
    print(f"API Returned {len(articles)} articles.")
    for article in articles:
        aid = article.get("id")
        title = article.get("title", "")[:40]
        thumb_url = article.get("thumbnail_url")
        thumb_local = article.get("thumbnail_local")
        thumb_status = article.get("thumbnail_status")
        print(f"[{aid}] {title}...")
        print(f"  thumb_local: {thumb_local}")
        print(f"  thumb_url: {thumb_url}")
        print(f"  thumb_status: {thumb_status}")
except Exception as e:
    print(f"Error fetching data: {e}")
