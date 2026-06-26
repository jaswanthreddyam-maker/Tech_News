from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    COMPANY = "COMPANY"
    PERSON = "PERSON"
    PRODUCT = "PRODUCT"
    TECHNOLOGY = "TECHNOLOGY"
    ORGANIZATION = "ORGANIZATION"

class Entity(BaseModel):
    id: str = Field(..., description="Canonical ID for the entity")
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    entity_type: EntityType
    description: str | None = None
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)

class TopicTaxonomy(str, Enum):
    AI = "Artificial Intelligence"
    CYBERSECURITY = "Cybersecurity"
    CLOUD = "Cloud"
    MOBILE = "Mobile"
    GAMING = "Gaming"
    HARDWARE = "Hardware"
    SOFTWARE = "Software"
    CRYPTO = "Cryptocurrency"
    STARTUPS = "Startups"
    BIG_TECH = "Big Tech"

class Topic(BaseModel):
    name: str = Field(..., description="The name of the topic")
    taxonomy_category: TopicTaxonomy = Field(..., description="Broad taxonomy category")
    confidence: float = Field(..., ge=0.0, le=1.0)

class TimelineCertainty(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class TimelineEvent(BaseModel):
    event_type: str = Field(..., description="E.g., Funding, Launch, Acquisition")
    date: str = Field(..., description="ISO8601 Date or Year-Month")
    certainty: TimelineCertainty
    entities: list[str] = Field(default_factory=list, description="List of entity IDs involved")
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)

class RelationshipPredicate(str, Enum):
    ACQUIRED = "ACQUIRED"
    ANNOUNCED = "ANNOUNCED"
    RELEASED = "RELEASED"
    FUNDED = "FUNDED"
    PARTNERED_WITH = "PARTNERED_WITH"
    INVESTED_IN = "INVESTED_IN"
    HIRED = "HIRED"
    LEFT = "LEFT"
    MERGED_WITH = "MERGED_WITH"
    INTRODUCED = "INTRODUCED"
    OPEN_SOURCED = "OPEN_SOURCED"
    LAUNCHED = "LAUNCHED"
    SUED = "SUED"
    SETTLED = "SETTLED"
    FILED = "FILED"
    EXPANDED_TO = "EXPANDED_TO"

class Relationship(BaseModel):
    source: str = Field(..., description="Source Entity ID")
    predicate: RelationshipPredicate
    target: str = Field(..., description="Target Entity ID")
    confidence: float = Field(..., ge=0.0, le=1.0)

class KnowledgeArtifact(BaseModel):
    """The enriched payload combining Article Artifact and Knowledge"""
    artifact_id: str
    entities: list[Entity] = Field(default_factory=list)
    topics: list[Topic] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
