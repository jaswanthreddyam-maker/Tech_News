import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import GraphEdge, GraphNode

logger = logging.getLogger(__name__)

class EntityResolver:
    """Resolves extracted string names into Canonical Graph Node IDs."""
    def __init__(self):
        pass

    async def resolve(self, session: AsyncSession, entity_name: str, snapshot_id: int, entity_type: str = "ENTITY") -> GraphNode:
        """
        Naive resolution by exact match. 
        In production, this uses Vector Search + Rule Matching + Confidence Scoring.
        """
        stmt = select(GraphNode).where(
            GraphNode.node_type == entity_type,
            GraphNode.name == entity_name
        )
        res = await session.execute(stmt)
        node = res.scalars().first()

        if not node:
            # ADR-0021: Append only, create new entity if not found
            node = GraphNode(
                node_type=entity_type,
                name=entity_name,
                confidence=0.8 # Initial guess
            )
            session.add(node)
            await session.flush()
            logger.info(f"EntityResolver: Created new canonical entity '{entity_name}' (ID: {node.id})")
        else:
            logger.info(f"EntityResolver: Resolved '{entity_name}' to existing node {node.id}")

        return node

class WorldEventResolver:
    """Resolves raw timeline events into Canonical WORLD_EVENT Graph Nodes."""
    def __init__(self):
        pass

    async def resolve(self, session: AsyncSession, event_dict: dict[str, Any], snapshot_id: int) -> GraphNode:
        """
        Resolves an event to a canonical graph node.
        If a similar event exists at the same time with the same entities, return it.
        Otherwise, create a new one.
        """
        # For prototype: always create new, relying on CrossArticleMerger to dedupe before calling this, 
        # or implement complex db querying.

        node = GraphNode(
            node_type="WORLD_EVENT",
            name=event_dict.get("title", "Unknown Event"),
            properties={
                "start_time": event_dict.get("start_time"),
                "end_time": event_dict.get("end_time"),
                "precision": event_dict.get("precision", "UNKNOWN"),
                "description": event_dict.get("description", "")
            },
            confidence=event_dict.get("confidence", 1.0)
        )
        session.add(node)
        await session.flush()
        logger.info(f"WorldEventResolver: Created new canonical WORLD_EVENT '{node.name}' (ID: {node.id})")
        return node

class RelationshipResolver:
    """Resolves relationships (Edges) between nodes."""
    async def create_edge(self, session: AsyncSession, source_id: str, target_id: str, edge_type: str, snapshot_id: int, properties: dict | None = None) -> GraphEdge:
        edge = GraphEdge(
            source_node_id=source_id,
            target_node_id=target_id,
            edge_type=edge_type,
            properties=properties or {}
        )
        session.add(edge)
        await session.flush()
        return edge

from app.services.knowledge_graph.canonical_resolver import CanonicalResolver


class TraversalEngine:
    """Traverses the graph for multi-hop queries."""
    def __init__(self, canonical_resolver: CanonicalResolver):
        self.canonical_resolver = canonical_resolver

    async def resolve_canonical(self, session: AsyncSession, node_id: str, snapshot_id: int) -> str:
        """Resolves node_id through any SUPERSEDED_BY links."""
        return await self.canonical_resolver.resolve(session, node_id, snapshot_id)

    async def expand_subgraph(self, session: AsyncSession, node_id: str, snapshot_id: int, depth: int = 1) -> dict[str, Any]:
        """Expands the neighborhood of a node up to `depth` hops."""
        canonical_id = await self.resolve_canonical(session, node_id, snapshot_id)
        # Placeholder for complex recursive CTE or iterative expansion
        return {"canonical_id": canonical_id, "nodes": [], "edges": []}

    async def find_common_ancestor(self, session: AsyncSession, node_a: str, node_b: str, snapshot_id: int) -> str | None:
        """Finds the shortest path intersection between two nodes."""
        canon_a = await self.resolve_canonical(session, node_a, snapshot_id)
        canon_b = await self.resolve_canonical(session, node_b, snapshot_id)
        if canon_a == canon_b:
            return canon_a
        # Placeholder for intersection logic
        return None

class GraphValidator:
    """Validates structural integrity of graph insertions."""
    pass

class KnowledgeGraphService:
    """Facade for all Knowledge Graph interactions."""
    def __init__(self):
        self.entity_resolver = EntityResolver()
        self.event_resolver = WorldEventResolver()
        self.relationship_resolver = RelationshipResolver()

        # Centralized CanonicalResolver per ADR-0023
        self.canonical_resolver = CanonicalResolver()
        self.traversal = TraversalEngine(self.canonical_resolver)
        self.validator = GraphValidator()
