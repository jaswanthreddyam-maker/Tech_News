from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.news import ArticleCard
from app.services.personalization_service import PersonalizationService

router = APIRouter()

class ReadingHistoryPayload(BaseModel):
    article_id: str | int
    progress: float
    completed: bool
    reading_time_seconds: int

class FeedItemResponse(BaseModel):
    article: ArticleCard
    reasoning_metadata: dict
    score: float

class ToggleResponse(BaseModel):
    status: str
    active: bool

@router.post("/saved/{article_id}", response_model=ToggleResponse)
async def toggle_saved_article(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from datetime import datetime, timezone
    service = PersonalizationService(db)
    active = await service.toggle_saved_article(current_user.id, article_id)

    state = dict(current_user.personalization_state or {})
    bookmarks = list(state.get("bookmarkedArticles") or [])
    art_num = int(article_id) if article_id.isdigit() else article_id
    if active:
        if not any((b.get("articleId") if isinstance(b, dict) else b) == art_num for b in bookmarks):
            bookmarks.insert(0, {"articleId": art_num, "savedAt": int(datetime.now(timezone.utc).timestamp() * 1000)})
    else:
        bookmarks = [b for b in bookmarks if (b.get("articleId") if isinstance(b, dict) else b) != art_num]
    state["bookmarkedArticles"] = bookmarks
    current_user.personalization_state = state
    await db.commit()

    return ToggleResponse(status="success", active=active)

@router.post("/following/entities/{entity_id}", response_model=ToggleResponse)
async def toggle_followed_entity(
    entity_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = PersonalizationService(db)
    active = await service.toggle_followed_entity(current_user.id, entity_id)
    return ToggleResponse(status="success", active=active)

@router.post("/following/topics/{topic_name}", response_model=ToggleResponse)
async def toggle_followed_topic(
    topic_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = PersonalizationService(db)
    active = await service.toggle_followed_topic(current_user.id, topic_name)
    return ToggleResponse(status="success", active=active)

@router.get("/saved")
async def get_saved_articles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import select
    from app.models.user import SavedArticle
    stmt = select(SavedArticle.article_id).where(SavedArticle.user_id == current_user.id).order_by(SavedArticle.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/following/entities")
async def get_followed_entities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = PersonalizationService(db)
    entities = await service.get_followed_entities(current_user.id)
    return [{"id": e.id, "canonical_name": e.canonical_name, "entity_type": e.entity_type} for e in entities]

@router.get("/following/topics")
async def get_followed_topics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = PersonalizationService(db)
    topics = await service.get_followed_topics(current_user.id)
    return [{"name": t.name, "taxonomy_category": t.taxonomy_category} for t in topics]

@router.post("/history")
async def record_reading_history(
    payload: ReadingHistoryPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = PersonalizationService(db)
    history = await service.record_reading_history(
        user_id=current_user.id,
        article_id=payload.article_id,
        progress=payload.progress,
        completed=payload.completed,
        reading_time_seconds=payload.reading_time_seconds
    )
    return {"status": "success"}

@router.get("/feed", response_model=list[FeedItemResponse])
async def get_personalized_feed(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = PersonalizationService(db)
    feed = await service.get_personalized_feed(current_user.id, limit=limit, offset=offset)
    return feed


@router.get("/personalization")
async def get_personalization_snapshot(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve full personalization state snapshot for syncing."""
    from datetime import datetime, timezone
    from app.models.user import SavedArticle
    from sqlalchemy import select

    saved_stmt = select(SavedArticle.article_id).where(SavedArticle.user_id == current_user.id)
    saved_res = await db.execute(saved_stmt)
    saved = saved_res.scalars().all()

    state = dict(current_user.personalization_state or {})

    # Ensure all expected fields exist for frontend
    if "bookmarkedArticles" not in state or not state["bookmarkedArticles"]:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        state["bookmarkedArticles"] = [
            {"articleId": int(s) if str(s).isdigit() else s, "savedAt": now_ms}
            for s in saved
        ]
    if "readingHistory" not in state:
        state["readingHistory"] = []
    if "recommendationSettings" not in state:
        state["recommendationSettings"] = {
            "prioritize": "balanced",
            "hideReadArticles": False,
            "preferTrustedSources": True,
            "showBreakingNews": True,
            "includeEmergingTopics": True,
        }
    if "topicPreferences" not in state:
        state["topicPreferences"] = []

    state["lastSyncedAt"] = int(datetime.now(timezone.utc).timestamp() * 1000)
    return {"data": state}


@router.post("/personalization")
async def upload_personalization_snapshot(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Save personalization state snapshot."""
    from app.models.user import SavedArticle, UserReadingHistory
    from app.models.article import ArticleReadModel
    from sqlalchemy import select, delete, update

    current_user.personalization_state = payload
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(personalization_state=payload)
    )

    try:
        # Sync bookmarked articles to saved_articles table
        bookmarks = payload.get("bookmarkedArticles") or []
        if isinstance(bookmarks, list):
            current_saved_stmt = select(SavedArticle.article_id).where(SavedArticle.user_id == current_user.id)
            current_saved_res = await db.execute(current_saved_stmt)
            existing_ids = set(str(x) for x in current_saved_res.scalars().all())

            target_ids = set()
            for b in bookmarks:
                art_id = str(b.get("articleId") if isinstance(b, dict) else b)
                if art_id:
                    target_ids.add(art_id)

            # Check valid article IDs in database to respect foreign key constraint
            valid_arts = set()
            if target_ids:
                valid_stmt = select(ArticleReadModel.id).where(ArticleReadModel.id.in_(list(target_ids)))
                valid_res = await db.execute(valid_stmt)
                valid_arts = set(str(x) for x in valid_res.scalars().all())

            for art_id in valid_arts:
                if art_id not in existing_ids:
                    db.add(SavedArticle(user_id=current_user.id, article_id=art_id))

            to_remove = existing_ids - target_ids
            if to_remove:
                await db.execute(
                    delete(SavedArticle).where(
                        SavedArticle.user_id == current_user.id,
                        SavedArticle.article_id.in_(list(to_remove))
                    )
                )

        # Sync reading history to user_reading_history table
        history_items = payload.get("readingHistory") or []
        if isinstance(history_items, list):
            hist_target_ids = set()
            for item in history_items:
                if isinstance(item, dict) and item.get("articleId"):
                    hist_target_ids.add(str(item["articleId"]))

            valid_hist_arts = set()
            if hist_target_ids:
                valid_hist_stmt = select(ArticleReadModel.id).where(ArticleReadModel.id.in_(list(hist_target_ids)))
                valid_hist_res = await db.execute(valid_hist_stmt)
                valid_hist_arts = set(str(x) for x in valid_hist_res.scalars().all())

            for item in history_items:
                if isinstance(item, dict) and item.get("articleId"):
                    art_id = str(item["articleId"])
                    if art_id in valid_hist_arts:
                        stmt = select(UserReadingHistory).where(
                            UserReadingHistory.user_id == current_user.id,
                            UserReadingHistory.article_id == art_id
                        )
                        existing = (await db.execute(stmt)).scalar_one_or_none()
                        if existing:
                            existing.completed = existing.completed or bool(item.get("completed"))
                            existing.reading_time_seconds = max(existing.reading_time_seconds, int(item.get("readingTime", 0)))
                        else:
                            db.add(UserReadingHistory(
                                user_id=current_user.id,
                                article_id=art_id,
                                completed=bool(item.get("completed")),
                                reading_time_seconds=int(item.get("readingTime", 0)),
                                read_progress=1.0 if item.get("completed") else 0.5
                            ))
    except Exception as e:
        import logging
        logging.getLogger("tech_news.routes.personalization").warning(f"Error syncing relational personalization tables: {e}")

    await db.commit()
    return {"status": "success", "data": payload}


