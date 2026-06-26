import logging
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.story import Story, StoryStatus, RelatedStory
from app.models.article import ProcessedArticle

logger = logging.getLogger(__name__)

class RelatedCoverageEngine:
    SIMILARITY_THRESHOLD = 0.85

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _compute_centroid(self, story_id: str):
        # We compute a simplistic centroid by averaging the embeddings of articles in the story.
        # This requires PostgreSQL's vector AVG function or calculating it in memory.
        # Since pgvector doesn't support AVG natively without extension, we fetch embeddings and compute manually.
        
        stmt = select(ProcessedArticle.embedding).where(
            and_(
                ProcessedArticle.story_id == story_id,
                ProcessedArticle.embedding.is_not(None)
            )
        )
        res = await self.db.execute(stmt)
        embeddings = [row[0] for row in res.all()]
        
        if not embeddings:
            return None
            
        import numpy as np
        centroid = np.mean(embeddings, axis=0)
        return centroid

    async def execute_batch_job(self):
        """Finds related active/monitoring stories and populates RelatedStory graph."""
        logger.info("Starting Related Coverage Engine batch job.")
        
        # Get all relevant stories
        stmt = select(Story.id).where(Story.status.in_([StoryStatus.ACTIVE, StoryStatus.MONITORING]))
        res = await self.db.execute(stmt)
        story_ids = [row[0] for row in res.all()]
        
        if len(story_ids) < 2:
            return
            
        centroids = {}
        for sid in story_ids:
            c = await self._compute_centroid(sid)
            if c is not None:
                centroids[sid] = c
                
        import numpy as np
        
        # Clear old related stories to regenerate (in a real system we might upsert to preserve history)
        # For RC3.2 we rebuild
        from sqlalchemy import delete
        await self.db.execute(delete(RelatedStory))
        
        for i, sid1 in enumerate(story_ids):
            if sid1 not in centroids: continue
            c1 = centroids[sid1]
            
            for sid2 in story_ids[i+1:]:
                if sid2 not in centroids: continue
                c2 = centroids[sid2]
                
                # Cosine similarity
                sim = np.dot(c1, c2) / (np.linalg.norm(c1) * np.linalg.norm(c2))
                
                if sim >= self.SIMILARITY_THRESHOLD:
                    rs1 = RelatedStory(
                        source_story_id=sid1,
                        target_story_id=sid2,
                        confidence=float(sim),
                        relationship_type="INDUSTRY_RELATED"
                    )
                    rs2 = RelatedStory(
                        source_story_id=sid2,
                        target_story_id=sid1,
                        confidence=float(sim),
                        relationship_type="INDUSTRY_RELATED"
                    )
                    self.db.add_all([rs1, rs2])
                    logger.info(f"Found related stories: {sid1} <-> {sid2} (sim: {sim:.3f})")
                    
        await self.db.commit()
        logger.info("Finished Related Coverage Engine batch job.")
