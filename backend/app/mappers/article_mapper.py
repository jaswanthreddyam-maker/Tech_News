from typing import Any
from app.schemas.news import ArticleBase, ArticleCard
from app.core.storage_paths import StoragePathService

class ArticleMapper:
    @staticmethod
    def to_base(model: Any) -> ArticleBase:
        """
        Maps a database model to the ArticleBase schema.
        Cleans and normalizes thumbnail paths on-the-fly to handle unmigrated database entries gracefully.
        """
        clean_local = StoragePathService.clean_relative(model.thumbnail_local)
        resolved_url = StoragePathService.to_public_url(clean_local) or model.thumbnail_url
        
        return ArticleBase(
            id=str(model.id),
            title=model.title,
            url=model.url,
            slug=model.url,
            summary=model.summary,
            source=model.source,
            reading_time=model.reading_time,
            published_at=model.published_at,
            thumbnail_url=resolved_url,
            thumbnail_local=clean_local,
            key_takeaways=getattr(model, "key_takeaways", None) or None,
            alt_text=getattr(model, "alt_text", None)
        )

    @staticmethod
    def to_card(model: Any, topics: list[str] | None = None, entities: list[str] | None = None) -> ArticleCard:
        """
        Maps a database model to the ArticleCard schema.
        Cleans and normalizes thumbnail paths on-the-fly to handle unmigrated database entries gracefully.
        """
        clean_local = StoragePathService.clean_relative(model.thumbnail_local)
        resolved_url = StoragePathService.to_public_url(clean_local) or model.thumbnail_url
        
        return ArticleCard(
            id=str(model.id),
            title=model.title,
            url=model.url,
            slug=model.url,
            summary=model.summary,
            source=model.source,
            reading_time=model.reading_time,
            published_at=model.published_at,
            thumbnail_url=resolved_url,
            thumbnail_local=clean_local,
            key_takeaways=getattr(model, "key_takeaways", None) or None,
            alt_text=getattr(model, "alt_text", None),
            topics=topics or [],
            entities=entities or []
        )
