import time
import requests
import statistics
import concurrent.futures

API_URL = "https://tech-news-api-production-1b42.up.railway.app/api/v1/news?limit=10"

def make_request():
    start = time.perf_counter()
    try:
        response = requests.get(API_URL, timeout=30)
        end = time.perf_counter()
        latency = (end - start) * 1000 # ms
        success = response.status_code == 200
        
        # Check if valid JSON and article count
        article_count = 0
        if success:
            try:
                data = response.json()
                article_count = len(data.get("data", []))
            except:
                pass
                
        return latency, success, article_count
    except Exception as e:
        return 0, False, 0

def run_test(name, is_concurrent=False, count=10):
    print(f"\n--- Running {name} Test ({count} requests) ---")
    latencies = []
    successes = 0
    total_articles = 0
    
    if is_concurrent:
        with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
            futures = [executor.submit(make_request) for _ in range(count)]
            for future in concurrent.futures.as_completed(futures):
                lat, succ, count_articles = future.result()
                if succ:
                    latencies.append(lat)
                    successes += 1
                    total_articles += count_articles
    else:
        for _ in range(count):
            lat, succ, count_articles = make_request()
            if succ:
                latencies.append(lat)
                successes += 1
                total_articles += count_articles

    if latencies:
        print(f"Min: {min(latencies):.2f} ms")
        print(f"Max: {max(latencies):.2f} ms")
        print(f"Avg: {statistics.mean(latencies):.2f} ms")
        print(f"p95: {statistics.quantiles(latencies, n=100)[94]:.2f} ms")
        print(f"p99: {statistics.quantiles(latencies, n=100)[98]:.2f} ms")
    print(f"HTTP Success: {successes}/{count}")
    print(f"Total Articles Found (sum): {total_articles}")

if __name__ == "__main__":
    print("Waiting for deployment to complete (latency < 2000ms)...")
    while True:
        lat, succ, count = make_request()
        print(f"Current latency: {lat:.2f} ms")
        if succ and lat < 2000:
            print("Deployment detected! API is fast now.")
            break
        time.sleep(10)
        
    run_test("Sequential", is_concurrent=False, count=10)
    run_test("Concurrent", is_concurrent=True, count=10)
