import asyncio
import json
import os

import httpx


async def capture():
    # 1. Login to get token
    login_data = {"email": "jeshu0069@gmail.com", "password": "mnbvcxzlkjhgfdsapoiuytrewq"}

    # We'll use the docker network 'testserver' or localhost depending on where it runs.
    # Since we'll run it inside the container, we can use http://127.0.0.1:8000
    base_url = "http://127.0.0.1:8000"

    async with httpx.AsyncClient(base_url=base_url) as client:
        # FastAPI OAuth2PasswordRequestForm expects form data, not json
        login_res = await client.post("/api/v1/auth/login", json=login_data)
        if login_res.status_code != 200:
            print(f"Login failed: {login_res.status_code} {login_res.text}")
            return

        token = login_res.json().get("data", {}).get("access_token")
        if not token:
            print("Token missing from response:", login_res.json())
            return

        headers = {"Authorization": f"Bearer {token}"}

        endpoints = {
            "overview": "/api/v1/admin/overview",
            "infrastructure": "/api/v1/admin/infrastructure",
            "queue": "/api/v1/admin/queue",
            "metrics": "/api/v1/admin/metrics",
            "notifications": "/api/v1/admin/notifications",
            "ai_jobs": "/api/v1/admin/ai/jobs",
            "ai_costs": "/api/v1/admin/ai/costs",
        }

        os.makedirs("verification", exist_ok=True)

        for name, ep in endpoints.items():
            res = await client.get(ep, headers=headers)
            try:
                data = res.json()
            except Exception:
                data = {"error": "JSON Decode Failed", "status_code": res.status_code, "text": res.text}

            with open(f"verification/{name}.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"Captured {name}")


if __name__ == "__main__":
    asyncio.run(capture())
