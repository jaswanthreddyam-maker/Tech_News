import logging
from typing import TypeVar

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.models.ai_artifacts import AIArtifact
from app.schemas.ai_artifacts import AIArtifactStatus, BaseAIArtifact

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseAIArtifact)

class ArtifactStore:
    """Handles PostgreSQL persistence, transactions, and reads/writes."""
    async def save(self, session: AsyncSession, artifact: BaseAIArtifact, article_id: int | None = None) -> int:
        db_artifact = AIArtifact(
            artifact_type=artifact.__class__.__name__,
            status=artifact.metadata.status.value,
            version=artifact.metadata.version,
            payload=artifact.model_dump(exclude={"metadata"}),
            metadata_json=artifact.metadata.model_dump(),
            article_id=article_id
        )
        session.add(db_artifact)
        await session.flush()
        return int(str(db_artifact.id))

    async def get(self, session: AsyncSession, artifact_id: int) -> AIArtifact | None:
        stmt = select(AIArtifact).where(AIArtifact.id == artifact_id)
        res = await session.execute(stmt)
        return res.scalars().first()

    async def update_status(self, session: AsyncSession, artifact_id: int, status: AIArtifactStatus) -> None:
        stmt = update(AIArtifact).where(AIArtifact.id == artifact_id).values(status=status.value)
        await session.execute(stmt)

class ArtifactCache:
    """Handles Redis caching, invalidation, TTL."""
    def __init__(self):
        self.redis = get_redis_client()

    def _key(self, artifact_type: str, article_id: int) -> str:
        return f"ai_artifact:{artifact_type.lower()}:article:{article_id}"

    async def get(self, artifact_type: str, article_id: int) -> str | None:
        return await self.redis.get(self._key(artifact_type, article_id))

    async def set(self, artifact_type: str, article_id: int, payload: str, ttl: int = 86400) -> None:
        await self.redis.set(self._key(artifact_type, article_id), payload, ex=ttl)

    async def invalidate(self, artifact_type: str, article_id: int) -> None:
        await self.redis.delete(self._key(artifact_type, article_id))

class ArtifactVersionManager:
    """Handles artifact lifecycle states without touching storage."""
    def transition(self, artifact: BaseAIArtifact, new_status: AIArtifactStatus) -> BaseAIArtifact:
        valid_transitions = {
            AIArtifactStatus.CREATED: [AIArtifactStatus.VALIDATING],
            AIArtifactStatus.VALIDATING: [AIArtifactStatus.VALIDATED, AIArtifactStatus.INVALIDATED],
            AIArtifactStatus.VALIDATED: [AIArtifactStatus.ACTIVE],
            AIArtifactStatus.ACTIVE: [AIArtifactStatus.SUPERSEDED, AIArtifactStatus.INVALIDATED],
            AIArtifactStatus.SUPERSEDED: [AIArtifactStatus.ARCHIVED],
            AIArtifactStatus.INVALIDATED: [AIArtifactStatus.ARCHIVED, AIArtifactStatus.DELETED],
            AIArtifactStatus.ARCHIVED: [AIArtifactStatus.DELETED]
        }

        current = artifact.metadata.status
        if new_status in valid_transitions.get(current, []):
            artifact.metadata.status = new_status
            logger.info(f"Transitioned artifact from {current.value} to {new_status.value}")
        else:
            logger.warning(f"Invalid transition from {current.value} to {new_status.value}")

        return artifact

class ArtifactRepository:
    """Facade for managing AI Artifact persistence, caching, and lifecycle."""
    def __init__(self):
        self.store = ArtifactStore()
        self.cache = ArtifactCache()
        self.version_manager = ArtifactVersionManager()

    async def persist_and_cache(self, session: AsyncSession, artifact: BaseAIArtifact, article_id: int) -> BaseAIArtifact:
        # Mark as ACTIVE
        artifact = self.version_manager.transition(artifact, AIArtifactStatus.ACTIVE)

        # Save to DB
        artifact_id = await self.store.save(session, artifact, article_id)
        artifact.metadata.artifact_id = artifact_id

        # Cache to Redis
        await self.cache.set(artifact.__class__.__name__, article_id, artifact.model_dump_json())

        return artifact

    async def get_active(self, session: AsyncSession, artifact_type: str, article_id: int, snapshot_id: int, model_schema: type[T]) -> T | None:
        # Check cache
        cached = await self.cache.get(artifact_type, article_id)
        if cached:
            return model_schema.model_validate_json(cached)

        # Fallback to DB (assuming we query by type and article_id for ACTIVE)
        stmt = select(AIArtifact).where(
            AIArtifact.article_id == article_id,
            AIArtifact.artifact_type == artifact_type,
            AIArtifact.status == AIArtifactStatus.ACTIVE.value
        ).order_by(AIArtifact.created_at.desc())

        res = await session.execute(stmt)
        db_obj = res.scalars().first()

        if db_obj:
            # Reconstruct Pydantic model
            raw_dict = db_obj.payload
            raw_dict["metadata"] = db_obj.metadata_json
            artifact = model_schema.model_validate(raw_dict)

            # Repopulate cache
            self.cache.set(artifact_type, article_id, artifact.model_dump_json())
            return artifact

        return None
