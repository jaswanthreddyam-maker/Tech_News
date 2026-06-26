import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import GraphEdge
from app.services.knowledge_graph.duplicate_detector import MergeCandidate

logger = logging.getLogger(__name__)

class MergeEngine:
    """
    Executes or proposes merges based on MergeCandidate scores.
    Adheres to ADR-0022 and ADR-0023 by using SUPERSEDED_BY relationships.
    """
    def __init__(self):
        self.auto_merge_threshold = 0.99
        self.review_threshold = 0.90

    async def process_candidate(self, session: AsyncSession, candidate: MergeCandidate) -> str:
        """
        Returns the resolution status: "AUTO_MERGED", "FLAGGED_FOR_REVIEW", or "IGNORED".
        """
        if candidate.score >= self.auto_merge_threshold:
            logger.info(f"MergeEngine: Auto-merging {candidate.source_id} into {candidate.target_id} (Score: {candidate.score})")
            await self.execute_merge(session, candidate.source_id, candidate.target_id)
            return "AUTO_MERGED"

        elif candidate.score >= self.review_threshold:
            logger.info(f"MergeEngine: Flagging merge {candidate.source_id} -> {candidate.target_id} for review (Score: {candidate.score})")
            await self.create_merge_proposal(session, candidate)
            return "FLAGGED_FOR_REVIEW"

        else:
            logger.debug(f"MergeEngine: Ignoring candidate {candidate.source_id} -> {candidate.target_id} (Score: {candidate.score})")
            return "IGNORED"

    async def execute_merge(self, session: AsyncSession, source_id: str, target_id: str) -> None:
        """
        Creates the SUPERSEDED_BY edge. Does NOT rewrite historical edges.
        """
        superseded_edge = GraphEdge(
            source_node_id=source_id,
            target_node_id=target_id,
            edge_type="SUPERSEDED_BY",
            properties={"auto_merged": True, "reason": "High confidence duplicate detection"}
        )
        session.add(superseded_edge)
        await session.flush()

    async def create_merge_proposal(self, session: AsyncSession, candidate: MergeCandidate) -> None:
        """
        In a real system, this inserts into a `MergeProposals` table for editor review.
        """
        pass
