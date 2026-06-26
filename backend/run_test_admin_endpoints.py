import asyncio

from app.main import app
from httpx import AsyncClient

from app.core.security import create_access_token


async def test():
    token = create_access_token(data={"sub": "1", "role": "super_admin"})
    headers = {"Authorization": f"Bearer {token}"}

    endpoints = [
        "/api/v1/admin/overview",
        "/api/v1/admin/infrastructure",
        "/api/v1/admin/queue",
        "/api/v1/admin/metrics",
        "/api/v1/admin/notifications",
        "/api/v1/admin/ai/jobs",
        "/api/v1/admin/ai/costs",
    ]

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        for ep in endpoints:
            res = await client.get(ep, headers=headers)
            print(f"=== {ep} ===")
            print(f"Status: {res.status_code}")
            try:
                print(res.json())
            except Exception:
                print(res.text)


if __name__ == "__main__":
    asyncio.run(test())
