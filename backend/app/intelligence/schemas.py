from typing import Any

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    query: str
    language: str = "en"
    workspace_id: int | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    subject_types: list[str] = Field(default_factory=list) # e.g. ["ARTICLE", "WORKSPACE"]
    sort: str | None = None
    rerank: bool = False
    limit: int = 10
    cursor: str | None = None
    embedding_version: str = "v1.0"

class SearchResultItem(BaseModel):
    document_id: str
    node_type: str
    title: str
    highlight: str
    score: float
    matched_via: str # KEYWORD, SEMANTIC, HYBRID
    metadata: dict[str, Any] = Field(default_factory=dict)

class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    total_results: int | None = None
    next_cursor: str | None = None
