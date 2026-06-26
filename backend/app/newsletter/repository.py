from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.newsletter.models import NewsletterSubscriber, NewsletterReadModel, SubscriptionStatus

class NewsletterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> NewsletterSubscriber | None:
        stmt = select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create(self, subscriber: NewsletterSubscriber) -> NewsletterSubscriber:
        self.session.add(subscriber)
        await self.session.flush()
        return subscriber

    async def get_stats(self) -> NewsletterReadModel:
        stmt = select(NewsletterReadModel).limit(1)
        result = await self.session.execute(stmt)
        stats = result.scalars().first()
        if not stats:
            # Initialize if not exists
            stats = NewsletterReadModel()
            self.session.add(stats)
            await self.session.flush()
        return stats

    async def increment_stats(
        self,
        total: int = 0,
        pending: int = 0,
        confirmed: int = 0,
        unsubscribed: int = 0,
        event_id: int | None = None
    ):
        # Using atomic update to avoid race conditions
        values = {
            "total_subscribers": NewsletterReadModel.total_subscribers + total,
            "pending_subscribers": NewsletterReadModel.pending_subscribers + pending,
            "confirmed_subscribers": NewsletterReadModel.confirmed_subscribers + confirmed,
            "unsubscribed": NewsletterReadModel.unsubscribed + unsubscribed
        }
        
        if event_id is not None:
            values["last_processed_event_id"] = event_id

        stmt = (
            update(NewsletterReadModel)
            .values(**values)
        )
        await self.session.execute(stmt)
