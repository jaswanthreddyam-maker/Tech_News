import asyncio

import httpx


async def run():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.head('http://172.27.144.1:8081/valid.jpg')
            print(r.status_code)
    except Exception as e:
        print(repr(e))
asyncio.run(run())
