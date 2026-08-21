import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_optional
from app.models.user import User
from app.schemas.responses import StandardResponse
from app.schemas.sources import FollowingFeedResponse, SourceItem, SourceSyncRequest
from app.services.personalization_service import PersonalizationService

logger = logging.getLogger("tech_news.sources")

sources_router = APIRouter()
following_router = APIRouter()
user_following_router = APIRouter()


# ---------------------------------------------------------------------------
# 1. Sources Catalog Endpoints (/api/v1/sources)
# ---------------------------------------------------------------------------


@sources_router.get("", response_model=StandardResponse[list[SourceItem]])
async def list_sources(
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    List all active, canonical sources with `is_following` status.
    Excludes disabled or soft-deleted sources.
    """
    service = PersonalizationService(db)
    user_id = current_user.id if current_user else None
    sources = await service.list_sources(user_id=user_id)
    return StandardResponse(correlation_id="sources-list", data=sources)


# ---------------------------------------------------------------------------
# 2. User Source Following Endpoints (/api/v1/users/me/following/sources)
# ---------------------------------------------------------------------------


@user_following_router.get("/sources", response_model=StandardResponse[list[str]])
@sources_router.get("/me", response_model=StandardResponse[list[str]])
async def get_my_followed_sources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the list of active canonical source slugs followed by the authenticated user.
    """
    service = PersonalizationService(db)
    source_slugs = await service.get_followed_source_slugs(current_user.id)
    return StandardResponse(correlation_id="my-followed-sources", data=source_slugs)


@user_following_router.post("/sources/{source_slug}", response_model=StandardResponse[dict])
@sources_router.post("/{source_slug}/follow", response_model=StandardResponse[dict])
async def follow_source(
    source_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Idempotently follows a canonical source by slug for the authenticated user.
    Rejects nonexistent, disabled, or deleted sources with HTTP 404.
    """
    service = PersonalizationService(db)
    try:
        await service.follow_source(user_id=current_user.id, source_slug=source_slug)
        return StandardResponse(
            correlation_id="follow-source",
            data={"status": "followed", "source_slug": source_slug.strip().lower(), "is_following": True},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@user_following_router.delete("/sources/{source_slug}", response_model=StandardResponse[dict])
@sources_router.delete("/{source_slug}/follow", response_model=StandardResponse[dict])
async def unfollow_source(
    source_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Idempotently unfollows a source by slug for the authenticated user.
    """
    service = PersonalizationService(db)
    await service.unfollow_source(user_id=current_user.id, source_slug=source_slug)
    return StandardResponse(
        correlation_id="unfollow-source",
        data={"status": "unfollowed", "source_slug": source_slug.strip().lower(), "is_following": False},
    )


@user_following_router.post("/sources/sync", response_model=StandardResponse[list[str]])
@sources_router.post("/sync", response_model=StandardResponse[list[str]])
async def sync_guest_follows(
    payload: SourceSyncRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Merges local guest follows (canonical slugs) into the authenticated user's account upon sign-in.
    """
    service = PersonalizationService(db)
    all_followed_slugs = await service.sync_guest_follows(
        user_id=current_user.id,
        source_slugs=payload.source_slugs,
    )
    return StandardResponse(correlation_id="sync-guest-follows", data=all_followed_slugs)


# ---------------------------------------------------------------------------
# 3. Following Feed Endpoints (/api/v1/following/feed & /api/v1/users/me/following/feed)
# ---------------------------------------------------------------------------


@following_router.get("/feed", response_model=StandardResponse[FollowingFeedResponse])
@user_following_router.get("/feed", response_model=StandardResponse[FollowingFeedResponse])
async def get_following_feed(
    source_slugs: Annotated[list[str] | None, Query()] = None,
    limit: int = 30,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    Returns the personal source feed.
    - Authenticated users: resolves followed sources from database `followed_sources`.
    - Guest users: accepts `?source_slugs=openai&source_slugs=google` from client localStorage.
    Strictly filters by `ProcessedArticle.source_id IN (followed_source_ids)`,
    enforces active source and publication lifecycle predicates, and sorts newest first (`published_at DESC`).
    Invariant: When followed sources is empty, returns empty array (never falls back to latest or projection).
    """
    service = PersonalizationService(db)
    user_id = current_user.id if current_user else None
    feed_data = await service.get_source_following_feed(
        user_id=user_id,
        guest_source_slugs=source_slugs,
        limit=limit,
        offset=offset,
    )
    return StandardResponse(correlation_id="following-feed", data=feed_data)
