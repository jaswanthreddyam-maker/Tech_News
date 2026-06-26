import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import ConflictingObservation

logger = logging.getLogger(__name__)

class ConflictResolver:
    """
    Handles contradictions between the graph and new extracted facts.
    Adheres to ADR-0022 by storing contradictions as Observations rather than rewriting facts.
    """
    def __init__(self):
        pass

    async def register_conflict(
        self, 
        session: AsyncSession, 
        node_id: str, 
        claim: str, 
        existing_fact: dict, 
        new_fact: dict, 
        source: str, 
        confidence: float, 
        reason: str
    ) -> ConflictingObservation:

        observation = ConflictingObservation(
            node_id=node_id,
            claim=claim,
            existing_fact=existing_fact,
            new_fact=new_fact,
            source=source,
            confidence=confidence,
            reason=reason,
            resolution_state="OPEN"
        )

        session.add(observation)
        await session.flush()

        logger.warning(f"ConflictResolver: Registered new conflicting observation on node {node_id}: {claim}")

        return observation
