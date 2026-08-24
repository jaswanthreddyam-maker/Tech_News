import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, DateTime, Enum, Boolean, ForeignKey,
    UniqueConstraint, Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.models.base import Base


def utc_now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Delivery Status Enum — lifecycle states ONLY.
# Engagement (opens, clicks) lives as separate telemetry columns; it does NOT
# change delivery status. CLICKED / OPENED_OBSERVED are removed.
# ---------------------------------------------------------------------------

class BriefingDeliveryStatus(str, enum.Enum):
    PENDING   = "PENDING"
    QUEUED    = "QUEUED"
    SENT      = "SENT"
    DELIVERED = "DELIVERED"
    FAILED    = "FAILED"
    BOUNCED   = "BOUNCED"
    COMPLAINED = "COMPLAINED"


# Terminal states — no further transitions allowed once reached.
BRIEFING_TERMINAL_STATES = frozenset({
    BriefingDeliveryStatus.FAILED,
    BriefingDeliveryStatus.BOUNCED,
    BriefingDeliveryStatus.COMPLAINED,
})

# Explicit allowed transitions. Anything not listed is forbidden.
BRIEFING_STATE_TRANSITIONS: dict = {
    BriefingDeliveryStatus.PENDING:   {BriefingDeliveryStatus.QUEUED},
    BriefingDeliveryStatus.QUEUED:    {BriefingDeliveryStatus.SENT,      BriefingDeliveryStatus.FAILED},
    BriefingDeliveryStatus.SENT:      {BriefingDeliveryStatus.DELIVERED, BriefingDeliveryStatus.BOUNCED, BriefingDeliveryStatus.FAILED},
    BriefingDeliveryStatus.DELIVERED: {BriefingDeliveryStatus.COMPLAINED},
}


def can_transition(current: BriefingDeliveryStatus, next_status: BriefingDeliveryStatus) -> bool:
    """Guard: returns True only when current→next_status is a valid transition."""
    if current in BRIEFING_TERMINAL_STATES:
        return False
    return next_status in BRIEFING_STATE_TRANSITIONS.get(current, set())


# ---------------------------------------------------------------------------
# Subscriber
# ---------------------------------------------------------------------------

class DailyBriefingSubscriber(Base):
    """
    Registered Daily Briefing subscriber.

    Security model:
    - verification_token_hash: SHA-256 of the raw HMAC-signed verification token
      that was emailed. Never stored in plaintext.
    - unsubscribe_token_hash: SHA-256 of the raw HMAC-signed unsubscribe token.
      The raw token is embedded in the email URL, hashed here for server-side
      comparison. The hash is NEVER exposed in URLs.

    enabled defaults to False — subscriber must verify email first.
    """
    __tablename__ = "daily_briefing_subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Email verification
    email_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_token_hash: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    verification_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Preferences — off until verified
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delivery_time: Mapped[str] = mapped_column(String(10), default="08:00", nullable=False)
    timezone: Mapped[str] = mapped_column(String(100), default="Asia/Kolkata", nullable=False)
    story_count: Mapped[int] = mapped_column(Integer, default=5, nullable=False)  # 5 or 10
    topics: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)

    # Unsubscribe — optional fallback hash; primary verification is cryptographic HMAC token
    unsubscribe_token_hash: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    unsubscribed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    deliveries = relationship("DailyBriefingDelivery", back_populates="subscriber", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Edition
# ---------------------------------------------------------------------------

class DailyBriefingEdition(Base):
    """
    One canonical global edition per date.

    INVARIANT: always generated at maximum configured capacity (up to 10 items),
    regardless of the first subscriber's story_count preference. Subscriber
    preference is applied at delivery/render time by slicing items[:story_count].
    """
    __tablename__ = "daily_briefing_editions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    edition_date: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    selection_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(50), default="v2.2", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PUBLISHED", nullable=False)

    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    items = relationship(
        "DailyBriefingItem", back_populates="edition",
        cascade="all, delete-orphan", order_by="DailyBriefingItem.rank"
    )
    deliveries = relationship("DailyBriefingDelivery", back_populates="edition", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Item
# ---------------------------------------------------------------------------

class DailyBriefingItem(Base):
    """
    One story in an edition. rank >= 1 with no DB ceiling.
    Maximum rank is bounded by edition capacity (10) at the application layer.
    """
    __tablename__ = "daily_briefing_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    edition_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("daily_briefing_editions.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    article_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cluster_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)

    rank: Mapped[int] = mapped_column(Integer, nullable=False)   # 1..N, bounded by app
    headline: Mapped[str] = mapped_column(String(500), nullable=False)
    why_it_matters: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=True)
    read_time: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    edition = relationship("DailyBriefingEdition", back_populates="items")


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------

class DailyBriefingDelivery(Base):
    """
    Delivery lifecycle record for one edition → one subscriber.
    UNIQUE(subscriber_id, edition_id) enforces idempotency.

    Delivery status = email lifecycle (PENDING → QUEUED → SENT → DELIVERED, etc.)
    Engagement telemetry = separate columns, status is NOT changed by opens/clicks.

    Click counting uses canonical /click/{signed_token} route only.
    Resend webhook email.clicked records provider_clicked_at for audit but does
    NOT increment click_count to avoid double counting.
    """
    __tablename__ = "daily_briefing_deliveries"
    __table_args__ = (
        UniqueConstraint("subscriber_id", "edition_id", name="uq_briefing_delivery_subscriber_edition"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    edition_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("daily_briefing_editions.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    subscriber_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("daily_briefing_subscribers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[BriefingDeliveryStatus] = mapped_column(
        Enum(BriefingDeliveryStatus, name="briefingdeliverystatus"),
        default=BriefingDeliveryStatus.PENDING, nullable=False
    )
    stories_delivered: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    provider_message_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    provider_idempotency_key: Mapped[str] = mapped_column(String(255), nullable=True, index=True)

    # Delivery timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    # --- Engagement telemetry (does NOT affect status) ---
    # Open pixel is unreliable (privacy blockers) → named "observed"
    opened_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    # Canonical click telemetry from our signed /click/ route
    first_clicked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    click_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Provider-level click event timestamp — audit only, not counted
    provider_clicked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    edition = relationship("DailyBriefingEdition", back_populates="deliveries")
    subscriber = relationship("DailyBriefingSubscriber", back_populates="deliveries")


# ---------------------------------------------------------------------------
# Webhook Event
# ---------------------------------------------------------------------------

class WebhookEvent(Base):
    """
    Inbound webhook events from email providers.
    UNIQUE(provider, event_id) provides infrastructure-level idempotency.
    """
    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("provider", "event_id", name="uq_webhook_event_provider_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="RESEND", index=True)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(255), nullable=True)

    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
