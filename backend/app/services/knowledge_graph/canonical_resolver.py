import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import GraphEdge

logger = logging.getLogger(__name__)

class CanonicalResolver:
    """
    Resolves a Node ID to its ultimate canonical identity by following SUPERSEDED_BY edges.
    Implements path compression to optimize future traversals.
    """
    def __init__(self):
        pass

    async def resolve(self, session: AsyncSession, node_id: str, snapshot_id: int) -> str:
        current_id = node_id
        path = [current_id]

        while True:
            # Query for a SUPERSEDED_BY edge originating from current_id
            stmt = select(GraphEdge).where(
                GraphEdge.source_node_id == current_id,
                GraphEdge.edge_type == "SUPERSEDED_BY"
            ).order_by(GraphEdge.created_at.desc())

            res = await session.execute(stmt)
            edge = res.scalars().first()

            if not edge:
                break

            current_id = edge.target_node_id
            if current_id in path:
                logger.error(f"Cycle detected in SUPERSEDED_BY chain for node {node_id} at {current_id}")
                break
            path.append(current_id)

        canonical_id = current_id

        # Path Compression: If path length > 2 (e.g. A -> B -> C -> D), we can add direct edges
        # A -> D, B -> D, C -> D to speed up future lookups.
        # ADR-0022/0023: We add NEW edges, we don't delete the old ones.
        if len(path) > 2:
            logger.info(f"CanonicalResolver: Performing path compression for {node_id} -> {canonical_id}")
            for intermediate_id in path[:-2]: # Skip the last node (canonical) and the one directly pointing to it
                # Create a direct shortcut
                shortcut = GraphEdge(
                    source_node_id=intermediate_id,
                    target_node_id=canonical_id,
                    edge_type="SUPERSEDED_BY",
                    properties={"is_shortcut": True, "original_path": path}
                )
                session.add(shortcut)
            # We flush so subsequent queries in this transaction benefit, 
            # but usually it's best to commit asynchronously.
            await session.flush()

        return canonical_id
