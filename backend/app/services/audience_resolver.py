import hashlib
import json
import logging

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.models.recipient import (
    Audience,
    ResolvedAudienceSnapshot,
    SubscriberContact,
    Subscription,
)

logger = logging.getLogger(__name__)

class ResolvedContact(BaseModel):
    subscriber_id: int
    contact_id: int
    type: str
    value: str
    verification_status: str

class ResolvedAudience(BaseModel):
    audience_id: int
    name: str
    resolved_contacts: list[ResolvedContact]
    total_count: int
    checksum: str | None = None
    snapshot_id: int | None = None

class AudienceResolver:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve(self, audience_id: int, ignore_cache: bool = False) -> ResolvedAudience:
        redis_client = get_redis_client()
        cache_key = f"audience:{audience_id}"

        if not ignore_cache:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for {cache_key}")
                data = json.loads(cached_data)
                return ResolvedAudience(**data)

        stmt = select(Audience).where(Audience.id == audience_id)
        res = await self.db.execute(stmt)
        audience = res.scalars().first()

        if not audience:
            raise ValueError(f"Audience {audience_id} not found")

        sub_stmt = select(Subscription).where(
            Subscription.audience_id == audience_id,
            Subscription.status == "ACTIVE"
        )
        res = await self.db.execute(sub_stmt)
        subscriptions = res.scalars().all()

        subscriber_ids = [sub.subscriber_id for sub in subscriptions]

        resolved_contacts = []
        checksum = ""

        if subscriber_ids:
            contact_stmt = select(SubscriberContact).where(
                SubscriberContact.subscriber_id.in_(subscriber_ids),
                SubscriberContact.type == "EMAIL",
                SubscriberContact.verification_status == "VERIFIED"
            )
            res = await self.db.execute(contact_stmt)
            verified_contacts = res.scalars().all()

            # Sort contacts to ensure deterministic checksum
            verified_contacts.sort(key=lambda c: c.id)

            checksum_str = ",".join(str(c.id) for c in verified_contacts)
            checksum = hashlib.sha256(checksum_str.encode()).hexdigest()

            for c in verified_contacts:
                resolved_contacts.append(ResolvedContact(
                    subscriber_id=c.subscriber_id,
                    contact_id=c.id,
                    type=c.type,
                    value=c.value,
                    verification_status=c.verification_status
                ))

        # Save snapshot
        snapshot = ResolvedAudienceSnapshot(
            audience_id=audience.id,
            recipient_count=len(resolved_contacts),
            checksum=checksum,
            contacts=[rc.model_dump() for rc in resolved_contacts]
        )
        self.db.add(snapshot)
        await self.db.flush()

        resolved_audience = ResolvedAudience(
            audience_id=audience.id,
            name=audience.name,
            resolved_contacts=resolved_contacts,
            total_count=len(resolved_contacts),
            checksum=checksum,
            snapshot_id=snapshot.id
        )

        await redis_client.setex(cache_key, 300, json.dumps(resolved_audience.model_dump()))
        return resolved_audience

    async def invalidate_cache(self, audience_id: int):
        redis_client = get_redis_client()
        await redis_client.delete(f"audience:{audience_id}")
