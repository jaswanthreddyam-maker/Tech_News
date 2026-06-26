import asyncio
import zlib
from bs4 import BeautifulSoup
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def run():
    async with AsyncSessionLocal() as db:
        # Fetch a Verge article
        res = await db.execute(text("""
            SELECT title, compressed_html FROM raw_articles 
            WHERE compressed_html IS NOT NULL AND (title LIKE '%Verge%' OR title LIKE '%Fitbit%' OR title LIKE '%Prime Day%')
            LIMIT 1
        """))
        row_verge = res.fetchone()
        
        # Fetch a TechCrunch article
        res = await db.execute(text("""
            SELECT title, compressed_html FROM raw_articles 
            WHERE compressed_html IS NOT NULL AND source_id = 6
            LIMIT 1
        """))
        row_tc = res.fetchone()
        
        selectors = [
            ".duet--layout--entry-body",  # The Verge body content container
            ".entry-content",             # TechCrunch/WordPress content container
            "[itemprop='articleBody']", 
            ".article-content", 
            ".post-content", 
            ".story-content",
            "#article-body", 
            "#story-body", 
            ".main-content",
            "article",                    # Fallback to article
            "main"                        # Fallback to main
        ]
        
        for name, row in [("The Verge", row_verge), ("TechCrunch", row_tc)]:
            if not row:
                print(f"No raw article found for {name}")
                continue
            title, compressed_html = row
            html_content = zlib.decompress(compressed_html).decode("utf-8")
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Clean boilerplate tags just like HTMLAgent does
            boilerplate_tags = [
                "script", "style", "noscript", "iframe", "header", "footer", "nav", 
                "aside", "form", "svg", "button", "canvas", "video", "audio", "input",
                "select", "textarea", "modal", "dialog"
            ]
            for tag in soup.find_all(boilerplate_tags):
                tag.decompose()
                
            body_container = None
            for sel in selectors:
                found = soup.select_one(sel)
                if found and len(found.get_text(strip=True)) > 200:
                    body_container = found
                    print(f"[{name}] Matched Selector: '{sel}'")
                    break
                    
            if body_container:
                content_elements = body_container.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6"])
                if content_elements:
                    cleaned_text = "\n\n".join(elem.get_text().strip() for elem in content_elements if elem.get_text().strip())
                else:
                    cleaned_text = body_container.get_text(separator="\n\n", strip=True)
                print(f"Title: {title}")
                print(f"Snippet:\n{cleaned_text[:400]}")
                print("-" * 50)
            else:
                print(f"[{name}] No body container matched.")

if __name__ == "__main__":
    asyncio.run(run())
