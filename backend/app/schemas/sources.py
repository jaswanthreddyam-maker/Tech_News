from datetime import datetime
from pydantic import BaseModel

from app.schemas.news import ArticleCard


class SourceItem(BaseModel):
    id: int
    name: str
    slug: str | None = None
    category: str
    description: str | None = None
    logo_url: str | None = None
    url: str
    credibility_score: int = 50
    is_following: bool = False


class SourceSyncRequest(BaseModel):
    source_ids: list[int]


class FollowingFeedResponse(BaseModel):
    items: list[ArticleCard]
    followed_sources_count: int
    total: int
