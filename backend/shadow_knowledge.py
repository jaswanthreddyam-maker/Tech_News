import asyncio
import json
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle
from app.core.capability.knowledge import EntityExtractionCapabilityV2, TopicClassificationCapabilityV2


async def run_shadow_extraction():
    async with AsyncSessionLocal() as db:
        # Get 10 articles for shadow validation
        stmt = select(ProcessedArticle).where(ProcessedArticle.is_test_data == False).limit(10)
        result = await db.execute(stmt)
        articles = result.scalars().all()
        
        entity_cap = EntityExtractionCapabilityV2()
        topic_cap = TopicClassificationCapabilityV2()
        
        results = []
        
        for art in articles:
            print(f"Shadow processing article {art.id}: {art.title[:50]}...")
            
            payload = {
                "article": {
                    "id": art.id,
                    "title": art.title,
                    "content": art.content
                }
            }
            
            # Run extraction
            try:
                entities_res = await entity_cap.execute(payload, None)
                topics_res = await topic_cap.execute(payload, None)
                
                results.append({
                    "article_id": art.id,
                    "title": art.title,
                    "entities": entities_res.get("entities", []),
                    "topics": topics_res.get("topics", [])
                })
            except Exception as e:
                print(f"Failed to process {art.id}: {e}")
                
        # Save to JSON staging file
        with open("shadow_extraction_results.json", "w") as f:
            json.dump(results, f, indent=2)
            
        print("Shadow extraction complete. Results saved to shadow_extraction_results.json")


if __name__ == "__main__":
    asyncio.run(run_shadow_extraction())
