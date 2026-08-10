import requests
import time
import json
import os
import sys

BASE_URL = "https://tech-news-api-production-1b42.up.railway.app"

def get_headers():
    login_payload = {'email': 'jeshu0069@gmail.com', 'password': 'mnbvcxzlkjhgfdsapoiuytrewq'}
    resp = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_payload)
    if resp.status_code != 200:
        print(f"Failed to login to production API: {resp.text}")
        sys.exit(1)
    
    token = resp.json()['data']['access_token']
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def main():
    print("--- 1. Query production DB-truth ---")
    headers = get_headers()
    
    # Wait for Railway deployment to be healthy and apply migrations
    print("Waiting for Railway deployment and running migrations...")
    for i in range(30):
        try:
            mig_resp = requests.post(f"{BASE_URL}/api/v1/admin/diagnostic/run-migrations", headers=headers, timeout=30)
            if mig_resp.status_code == 200:
                json_resp = mig_resp.json()
                print(f"Migration Response: {json_resp}")
                if json_resp.get("status") == "success":
                    print("Migrations ran successfully!")
                    # Wait 2 seconds for DB to settle
                    time.sleep(2)
                    break
                else:
                    print("Migration failed, might be still deploying...")
        except requests.exceptions.RequestException as e:
            pass
        time.sleep(3)
    else:
        print("Deployment or migration failed within 90 seconds.")
        sys.exit(1)
        
    print("--- 1. Query production DB-truth ---")
    for i in range(30):
        try:
            resp = requests.get(f"{BASE_URL}/api/v1/admin/diagnostic/filtered-samples", headers=headers, timeout=5)
            if resp.status_code == 200:
                print("Deployment healthy! DB migration applied.")
                data = resp.json().get("samples", [])
                break
        except requests.exceptions.RequestException as e:
            pass
        time.sleep(3)
    else:
        print(f"Failed to fetch samples within 90 seconds.")
        sys.exit(1)
    
    print("\n--- 2. Identify exact filter_reason distribution ---")
    reasons = {}
    filtered_ids = []
    for d in data:
        filtered_ids.append(d["id"])
        reason = d.get("filter_reason", "UNKNOWN")
        reasons[reason] = reasons.get(reason, 0) + 1
        
    print(f"Total Filtered Articles: {len(data)}")
    for r, c in reasons.items():
        print(f" - {r}: {c}")

    if not filtered_ids:
        print("No filtered articles found in production DB! Exiting.")
        sys.exit(1)

    print("\n--- 3. Replay ONLY the affected filtered records ---")
    payload = {"article_ids": filtered_ids}
    resp = requests.post(f"{BASE_URL}/api/v1/admin/diagnostic/replay", headers=headers, json=payload)
    print(f"Replay response: {resp.status_code} {resp.text}")

    print("\n--- 4/5/6/7/8 Wait and Capture Funnel Counts ---")
    print("Polling API for news (waiting for celery worker)...")
    
    for i in range(15):
        time.sleep(3)
        resp = requests.get(f"{BASE_URL}/api/v1/news?limit=10")
        if resp.status_code == 200:
            news = resp.json()
            if news.get("data") and len(news["data"]) > 0:
                print(f"Success: /api/v1/news returned {len(news['data'])} articles!")
                break
        print("Waiting for celery processing...")
    else:
        print("Timeout waiting for articles.")

    print("\n--- Verify /api/v1/news returns populated data ---")
    resp = requests.get(f"{BASE_URL}/api/v1/news?limit=20")
    if resp.status_code == 200:
        news = resp.json().get("data", [])
        print(f"Total projected articles (/api/v1/news): {len(news)}")

    print("\n--- Verify /api/v1/news/desks returns populated data ---")
    resp = requests.get(f"{BASE_URL}/api/v1/news/desks")
    if resp.status_code == 200:
        data = resp.json()
        desks = data.get("data", []) if isinstance(data, dict) else data
        print(f"Desks count: {len(desks)}")
        for d in desks:
            print(f"  - {d.get('name', 'Unknown')}: {d.get('article_count', 0)} articles")

if __name__ == "__main__":
    main()
