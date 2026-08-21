from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.news import ArticleCard


class SourceItem(BaseModel):
    id: Optional[int] = None
    slug: str = Field(..., description="Canonical URL-safe source identifier (e.g. 'openai')")
    name: str
    category: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    url: str
    credibility_score: int = 50
    is_following: bool = False


class SourceSyncRequest(BaseModel):
    source_slugs: list[str] = Field(..., description="List of canonical source slugs to synchronize")


class FollowingFeedResponse(BaseModel):
    items: list[ArticleCard]
    followed_sources_count: int
    total: int
