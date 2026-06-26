import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.intelligence.search.registry import KeywordRetriever, SemanticRetriever
from app.models.intelligence import SearchIndexNode

logger = logging.getLogger(__name__)

class HybridSearchPipeline:
    def __init__(self):
        self.keyword_retriever = KeywordRetriever()
        self.semantic_retriever = SemanticRetriever()
        self.rrf_k = 60 # Standard smoothing constant for RRF

    async def execute(self, db: AsyncSession, query: str, filters: dict[str, Any] | None = None, limit: int = 10) -> list[dict[str, Any]]:
        # 1. Query Parsing (stub for now, just passes query string)
        parsed_query = query

        # 2. Candidate Retrieval
        # Execute retrievers sequentially to prevent concurrent session usage issues
        keyword_results = await self.keyword_retriever.retrieve(db, parsed_query, filters, limit=50)
        semantic_results = await self.semantic_retriever.retrieve(db, parsed_query, filters, limit=50)

        # 3. RRF Fusion
        rrf_scores = {}
        matched_via = {}

        # Rank keywords
        for rank, item in enumerate(keyword_results, start=1):
            doc_id = item["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (self.rrf_k + rank)
            matched_via[doc_id] = ["KEYWORD"]

        # Rank semantic
        for rank, item in enumerate(semantic_results, start=1):
            doc_id = item["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (self.rrf_k + rank)
            if doc_id in matched_via:
                matched_via[doc_id].append("SEMANTIC")
            else:
                matched_via[doc_id] = ["SEMANTIC"]

        # 4. Ranking
        ranked_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        if not ranked_docs:
            return []

        doc_ids = [doc_id for doc_id, _ in ranked_docs]

        # 5. Hydration & Highlighting
        stmt = select(SearchIndexNode).where(SearchIndexNode.id.in_(doc_ids))
        result = await db.execute(stmt)
        nodes = {node.id: node for node in result.scalars().all()}

        response = []
        for doc_id, score in ranked_docs:
            node = nodes.get(doc_id)
            if not node:
                continue

            # Basic application-side highlighting stub
            content = node.content or ""
            # Simple context window extraction around query terms could go here
            highlight = content[:200] + "..." if len(content) > 200 else content

            response.append({
                "document_id": node.source_id,
                "node_type": node.node_type,
                "title": node.title,
                "highlight": highlight,
                "score": score,
                "matched_via": "HYBRID" if len(matched_via[doc_id]) > 1 else matched_via[doc_id][0],
                "metadata": node.metadata_payload
            })

        return response
