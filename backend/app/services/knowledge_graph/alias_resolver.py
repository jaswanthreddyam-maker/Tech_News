import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import GraphNodeAlias

logger = logging.getLogger(__name__)

class AliasResolver:
    """
    Maps an incoming string to a canonical node ID via recorded aliases.
    """
    def __init__(self):
        pass

    async def resolve(self, session: AsyncSession, alias_string: str) -> str | None:
        # Normalize the string
        normalized = alias_string.strip().lower()

        stmt = select(GraphNodeAlias).where(
            GraphNodeAlias.alias == normalized
        )
        res = await session.execute(stmt)
        alias_record = res.scalars().first()

        if alias_record:
            logger.info(f"AliasResolver: Mapped '{alias_string}' to canonical node {alias_record.canonical_node_id}")
            return str(alias_record.canonical_node_id)

        return None

    async def register_alias(self, session: AsyncSession, canonical_node_id: str, alias_string: str) -> GraphNodeAlias:
        normalized = alias_string.strip().lower()

        # Check if exists
        stmt = select(GraphNodeAlias).where(
            GraphNodeAlias.alias == normalized,
            GraphNodeAlias.canonical_node_id == canonical_node_id
        )
        res = await session.execute(stmt)
        existing = res.scalars().first()
        if existing:
            return existing

        alias_record = GraphNodeAlias(
            canonical_node_id=canonical_node_id,
            alias=normalized
        )
        session.add(alias_record)
        await session.flush()
        logger.info(f"AliasResolver: Registered new alias '{alias_string}' for node {canonical_node_id}")
        return alias_record
