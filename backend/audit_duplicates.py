import asyncio
import httpx

async def verify():
    async with httpx.AsyncClient() as client:
        r = await client.get("http://127.0.0.1:8000/api/v1/news?limit=60")
        data = r.json().get("data", [])
        print(f"Total articles in API response: {len(data)}")
        
        titles = {}
        for card in data:
            title = card.get("title", "")
            if title in titles:
                titles[title].append(card)
            else:
                titles[title] = [card]
        
        dup_titles = {t: cards for t, cards in titles.items() if len(cards) > 1}
        print(f"Duplicate titles in API response: {len(dup_titles)}")
        
        if dup_titles:
            for title, cards in dup_titles.items():
                print(f"  DUP: {title[:60]}")
        else:
            print("ALL UNIQUE - no duplicates in API response")

asyncio.run(verify())
