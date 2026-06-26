from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

print("Testing GET /api/v1/news?limit=1")
try:
    response = client.get("/api/v1/news?limit=1")
    print("Status:", response.status_code)
    print("Response JSON:", response.json())
except Exception as e:
    import traceback

    traceback.print_exc()
