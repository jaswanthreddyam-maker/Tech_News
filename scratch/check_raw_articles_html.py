import asyncio
from sqlalchemy import text
from app.core.database import async_engine
from app.services.ingestion.image_helper import extract_all_candidate_urls
from app.services.ingestion.processor import decompress_html

async def main():
    async with async_engine.connect() as conn:
        res = await conn.execute(text("""
            SELECT id, title, url, compressed_html is not null as has_html, length(compressed_html) as html_size, clean_text
            FROM raw_articles
            WHERE status = 'fetched'
            LIMIT 5;
        """))
        rows = res.fetchall()
        print("Checking raw articles:")
        for r in rows:
            mapped = dict(r._mapping)
            print(f"ID: {mapped['id']}, HasHTML: {mapped['has_html']}, Size: {mapped['html_size']}, Title: {mapped['title']}")
            
            # Decompress HTML if present
            if mapped['has_html']:
                # Need to fetch the actual compressed_html bytes
                bytes_res = await conn.execute(text("SELECT compressed_html FROM raw_articles WHERE id = :id"), {"id": mapped['id']})
                compressed_html = bytes_res.scalar()
                try:
                    html_content = decompress_html(compressed_html)
                    candidates = extract_all_candidate_urls(html_content, mapped['url'])
                    print(f"  -> Extracted {len(candidates)} candidates from compressed_html")
                    for c in candidates[:3]:
                        print(f"    - {c}")
                except Exception as e:
                    print(f"  -> Error decompressing: {e}")
            else:
                candidates = extract_all_candidate_urls(mapped['clean_text'], mapped['url'])
                print(f"  -> Extracted {len(candidates)} candidates from clean_text")

if __name__ == "__main__":
    asyncio.run(main())
