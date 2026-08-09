import asyncio
from agents.ingestion.html_agent import HTMLAgent

async def run():
    agent = HTMLAgent()
    # Test OpenAI
    url = "https://arstechnica.com/tech-policy/2026/08/trump-fcc-kills-tv-ownership-cap-claiming-authority-over-limit-set-by-congress"
    print("Testing:", url)
    res = await agent.extract_article(url)
    print("Success:", res.get("valid"))
    print("Clean text length:", len(res.get("clean_text", "")))
    print("HTML length:", len(res.get("html", "")))
    print("Raw HTML snippet:", res.get("html", "")[:500])
    print("Reason:", res.get("metrics", {}))
    await agent.shutdown()

asyncio.run(run())
