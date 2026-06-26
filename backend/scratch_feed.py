import asyncio
from agents.ingestion.html_agent import HTMLAgent

async def main():
    agent = HTMLAgent()
    url = "https://deepmind.google/blog/unlocking-uk-house-building-with-ai-accelerated-planning/"
    print(f"Extracting article from: {url}")
    result = await agent.extract_article(url)
    if result:
        print("\nSUCCESS!")
        print(f"Title: {result.get('title')}")
        print(f"Content length: {len(result.get('clean_text', ''))}")
        print(f"Content preview: {result.get('clean_text', '')[:400]}")
    else:
        print("\nFAILED!")

if __name__ == "__main__":
    asyncio.run(main())
