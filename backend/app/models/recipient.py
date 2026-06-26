from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def utc_now():
    return datetime.now(timezone.utc)

class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    primary_email: Mapped[str] = mapped_column(String(255), nullable=True, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    contacts = relationship("SubscriberContact", back_populates="subscriber", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="subscriber", cascade="all, delete-orphan")
    preferences = relationship("Preference", back_populates="subscriber", cascade="all, delete-orphan")
    delivery_preferences = relationship("DeliveryPreference", back_populates="subscriber", cascade="all, delete-orphan")
    events = relationship("SubscriptionEvent", back_populates="subscriber", cascade="all, delete-orphan")

class SubscriberContact(Base):
    __tablename__ = "subscriber_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subscriber_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subscribers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False) # EMAIL, PHONE, WEBHOOK, DEVICE_TOKEN
    value: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(50), nullable=False, default="UNVERIFIED") # UNVERIFIED, PENDING, VERIFIED, EXPIRED, FAILED
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_method: Mapped[str] = mapped_column(String(100), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    subscriber = relationship("Subscriber", back_populates="contacts")

class Audience(Base):
    __tablename__ = "audiences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    subscriptions = relationship("Subscription", back_populates="audience", cascade="all, delete-orphan")
    segments = relationship("Segment", back_populates="audience", cascade="all, delete-orphan")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subscriber_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subscribers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    audience_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("audiences.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE") # ACTIVE, UNSUBSCRIBED

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    subscriber = relationship("Subscriber", back_populates="subscriptions")
    audience = relationship("Audience", back_populates="subscriptions")

class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    audience_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("audiences.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    expression: Mapped[str] = mapped_column(Text, nullable=False) # e.g. "country == 'US' AND followed_topic == 'AI'"
    compiled_expression: Mapped[dict] = mapped_column(JSONB, nullable=True) # AST or internal representation
    compiled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    compiler_version: Mapped[str] = mapped_column(String(50), nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")

    audience = relationship("Audience", back_populates="segments")

class Preference(Base):
    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subscriber_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subscribers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_type: Mapped[str] = mapped_column(String(100), nullable=False) # ARTICLE, ENTITY, TOPIC, CATEGORY, AUTHOR, NEWSLETTER
    subject_id: Mapped[str] = mapped_column(String(255), nullable=False)

    preference: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "FOLLOW", "MUTE"
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    subscriber = relationship("Subscriber", back_populates="preferences")

class DeliveryPreference(Base):
    __tablename__ = "delivery_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subscriber_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subscribers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False) # Push, Email, etc.
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    batch_window: Mapped[str] = mapped_column(String(50), nullable=True)
    digest_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    quiet_hours: Mapped[str] = mapped_column(String(50), nullable=True) # e.g. "22:00-08:00"
    timezone: Mapped[str] = mapped_column(String(100), nullable=True) # e.g. "Asia/Kolkata"
    max_per_day: Mapped[int] = mapped_column(Integer, nullable=True)

    subscriber = relationship("Subscriber", back_populates="delivery_preferences")

class SubscriptionEvent(Base):
    __tablename__ = "subscription_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subscriber_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subscribers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event: Mapped[str] = mapped_column(String(100), nullable=False) # SUBSCRIBED, UNSUBSCRIBED, CHANGED_PREFERENCE
    actor: Mapped[str] = mapped_column(String(50), nullable=False, default="SYSTEM") # USER, SYSTEM, ADMIN
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    metadata_info: Mapped[dict] = mapped_column(JSONB, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    subscriber = relationship("Subscriber", back_populates="events")

class ResolvedAudienceSnapshot(Base):
    __tablename__ = "resolved_audience_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    audience_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    segment_version: Mapped[str] = mapped_column(String(50), nullable=True)
    compiler_version: Mapped[str] = mapped_column(String(50), nullable=True)

    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    recipient_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum: Mapped[str] = mapped_column(String(255), nullable=True)
    contacts: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
