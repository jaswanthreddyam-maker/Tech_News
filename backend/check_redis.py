import asyncio
import json
from app.core.redis import get_redis_client

async def run():
    client = get_redis_client()
    events = await client.lrange('recent_events', 0, 10)
    for e in events:
        print(e)

if __name__ == "__main__":
    asyncio.run(run())
