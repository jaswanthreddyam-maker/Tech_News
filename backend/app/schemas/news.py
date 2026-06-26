from datetime import datetime

from pydantic import BaseModel


class TakeawayItem(BaseModel):
    title: str
    description: str
    priority: int

class ArticleBase(BaseModel):
    id: str
    title: str
    url: str
    slug: str
    summary: str | None = None
    source: str
    reading_time: int = 0
    published_at: datetime | None = None
    thumbnail_url: str | None = None
    thumbnail_local: str | None = None
    key_takeaways: list[TakeawayItem] | None = None
    alt_text: str | None = None

class ArticleCard(ArticleBase):
    """Schema for home feed and related article lists."""
    topics: list[str] = []
    entities: list[str] = []

    @classmethod
    def from_model(cls, model, topics: list[str] | None = None, entities: list[str] | None = None) -> "ArticleCard":
        return cls(
            id=model.id,
            title=model.title,
            url=model.url,
            slug=model.url,
            summary=model.summary,
            source=model.source,
            reading_time=model.reading_time,
            published_at=model.published_at,
            thumbnail_url=model.thumbnail_url,
            thumbnail_local=model.thumbnail_local,
            key_takeaways=getattr(model, "key_takeaways", None),
            alt_text=getattr(model, "alt_text", None),
            topics=topics or [],
            entities=entities or []
        )

class KnowledgeEntity(BaseModel):
    id: str
    name: str
    type: str
    confidence: float

class KnowledgeTopic(BaseModel):
    name: str
    confidence: float

class KnowledgeTimelineEvent(BaseModel):
    event_type: str
    date: str
    description: str
    entities: list[str]
    confidence: float

class KnowledgeRelationship(BaseModel):
    source_id: str
    source_name: str
    predicate: str
    target_id: str
    target_name: str
    confidence: float

class ArticleKnowledgePanel(BaseModel):
    entities: list[KnowledgeEntity] = []
    topics: list[KnowledgeTopic] = []
    timeline: list[KnowledgeTimelineEvent] = []
    relationships: list[KnowledgeRelationship] = []

class ArticleRelated(BaseModel):
    articles: list[ArticleCard] = []
    entities: list[KnowledgeEntity] = []
    topics: list[KnowledgeTopic] = []

class NavigationInfo(BaseModel):
    previous: ArticleCard | None = None
    next: ArticleCard | None = None
    position: int
    total: int

class ArticleResponse(BaseModel):
    article: ArticleBase
    content: str
    clean_html: str
    hero_image: str | None = None
    images: list[dict] | None = None
    knowledge: ArticleKnowledgePanel
    related: ArticleRelated
    navigation: NavigationInfo | None = None
    scoring_debug: dict | None = None

class EntityStats(BaseModel):
    mention_count: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None

class EntityProfileResponse(BaseModel):
    id: str
    name: str
    type: str
    description: str | None = None
    aliases: list[str] = []
    stats: EntityStats
    latest_news: list[ArticleCard] = []
    timeline: list[KnowledgeTimelineEvent] = []
    relationships: list[KnowledgeRelationship] = []
    related_companies: list[KnowledgeEntity] = []

class TopicProfileResponse(BaseModel):
    name: str
    category: str
    trending_entities: list[KnowledgeEntity] = []
    timeline: list[KnowledgeTimelineEvent] = []
    latest_articles: list[ArticleCard] = []

class SearchResultItem(BaseModel):
    type: str # 'article', 'entity', 'topic'
    id: str
    title: str
    description: str | None = None
    url: str | None = None
    date: datetime | None = None
