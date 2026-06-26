import asyncio
from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle
from app.models.source import Source
from app.services.ingestion.filter import check_pre_ai_ingestion_eligibility, evaluate_adaptive_quality
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        stmt = select(RawArticle).where(RawArticle.id == 71)
        res = await db.execute(stmt)
        art = res.scalars().first()
        if not art:
            print("Article 71 not found")
            return
            
        print(f"Title: {art.title}")
        print(f"URL: {art.url}")
        print(f"Clean text length: {len(art.clean_text or '')}")
        print(f"Clean text preview: {art.clean_text[:200] if art.clean_text else 'None'}")
        
        source_stmt = select(Source).where(Source.id == art.source_id)
        src_res = await db.execute(source_stmt)
        src = src_res.scalars().first()
        
        cred = src.credibility_score if src else 80
        print(f"Source credibility: {cred}")
        
        is_relevant = check_pre_ai_ingestion_eligibility(
            title=art.title, content=art.clean_text, source_credibility=cred
        )
        print(f"check_pre_ai_ingestion_eligibility: {is_relevant}")
        
        meta_dict = {
            "source_category": src.category if src else "official",
            "rss_fallback": False,
            "author": None,
            "publish_date": None,
            "seo_keywords": "",
        }
        quality_res = evaluate_adaptive_quality(
            title=art.title, content=art.clean_text, raw_html=art.clean_text, meta_dict=meta_dict
        )
        print(f"evaluate_adaptive_quality: {quality_res}")

if __name__ == "__main__":
    asyncio.run(main())
