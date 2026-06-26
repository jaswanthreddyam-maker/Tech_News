import asyncio
import json

from app.api.v1.routes.telemetry import get_telemetry_snapshot
from app.core.database import AsyncSessionLocal


async def main():
    print("Direct snapshot query initialization...")
    async with AsyncSessionLocal() as db:
        snapshot = await get_telemetry_snapshot(db)
        print("=" * 60)
        print("TELEMETRY SNAPSHOT OBTAINED:")
        print("=" * 60)
        # Safely convert or remove the timestamp object for json serialization
        snapshot["timestamp"] = "2026-06-08T06:12:00Z"
        print(json.dumps(snapshot, indent=2))
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
