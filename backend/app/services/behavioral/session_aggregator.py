import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.behavioral import BehavioralEvent, ReadingSession

logger = logging.getLogger(__name__)


class SessionAggregator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def aggregate_events(self, events: list[BehavioralEvent]) -> None:
        """
        Takes newly inserted BehavioralEvents and updates their corresponding ReadingSessions.
        Assumes the caller has already committed the events.
        """
        # Group events by session_id
        session_groups = {}
        for event in events:
            if event.session_id not in session_groups:
                session_groups[event.session_id] = []
            session_groups[event.session_id].append(event)

        for session_id, group_events in session_groups.items():
            # Sort events by occurred_at for logical aggregation
            sorted_events = sorted(group_events, key=lambda e: e.occurred_at)

            # Fetch existing session
            result = await self.db.execute(select(ReadingSession).where(ReadingSession.session_id == session_id))
            session_obj = result.scalar_one_or_none()

            first_event = sorted_events[0]

            if not session_obj:
                # Create new session
                session_obj = ReadingSession(
                    session_id=session_id,
                    user_id=first_event.user_id,
                    anonymous_id=first_event.anonymous_id,
                    article_id=first_event.article_id,
                    content_version=first_event.content_version,
                    started_at=first_event.occurred_at,
                    last_activity_at=first_event.occurred_at,
                    device_type=first_event.device_type,
                    total_reading_seconds=0,
                    completion_percentage=0,
                    max_scroll_percent=0,
                    is_completed=False,
                )
                self.db.add(session_obj)

            for event in sorted_events:
                # Update last_activity
                if session_obj.last_activity_at < event.occurred_at:
                    session_obj.last_activity_at = event.occurred_at

                # Update max scroll
                if event.scroll_percent is not None and event.scroll_percent > session_obj.max_scroll_percent:
                    session_obj.max_scroll_percent = event.scroll_percent
                    session_obj.completion_percentage = session_obj.max_scroll_percent

                    if session_obj.completion_percentage >= 95:
                        session_obj.is_completed = True
                        if not session_obj.completed_at:
                            session_obj.completed_at = event.occurred_at
                            # Trigger profile update on completion
                            from celery_app import update_user_interest_profile_task

                            update_user_interest_profile_task.delay(
                                user_id=session_obj.user_id, anonymous_id=session_obj.anonymous_id
                            )

                # Update time
                if (
                    event.reading_time_seconds is not None
                    and event.reading_time_seconds > session_obj.total_reading_seconds
                ):
                    session_obj.total_reading_seconds = event.reading_time_seconds

        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to aggregate reading sessions: {e}")
