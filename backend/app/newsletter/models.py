from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean, UniqueConstraint
from sqlalchemy.sql import func
import enum
from app.models.base import Base

class SubscriptionStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    UNSUBSCRIBED = "UNSUBSCRIBED"

class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.PENDING, nullable=False)
    subscription_type = Column(String, default="DAILY_AI_BRIEFING")
    
    unsubscribe_token = Column(String, unique=True, index=True, nullable=False)
    confirmation_token = Column(String, unique=True, index=True, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    confirmation_sent_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

class NewsletterReadModel(Base):
    """
    CQRS Projection table for Admin operations.
    Maintains aggregate statistics about newsletter subscriptions.
    """
    __tablename__ = "newsletter_stats_projection"

    id = Column(Integer, primary_key=True)
    total_subscribers = Column(Integer, default=0, nullable=False)
    pending_subscribers = Column(Integer, default=0, nullable=False)
    confirmed_subscribers = Column(Integer, default=0, nullable=False)
    unsubscribed = Column(Integer, default=0, nullable=False)
    
    last_processed_event_id = Column(Integer, nullable=True)
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class NewsletterBriefing(Base):
    """
    Tracks the lifecycle and current state of a briefing.
    """
    __tablename__ = "newsletter_briefings"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="DRAFT", nullable=False) # DRAFT, APPROVED, REJECTED, ARCHIVED
    current_version_id = Column(Integer, nullable=True) # Points to the latest NewsletterBriefingVersion
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)

class NewsletterBriefingVersion(Base):
    """
    Tracks full version history of a briefing.
    """
    __tablename__ = "newsletter_briefing_versions"

    id = Column(Integer, primary_key=True, index=True)
    briefing_id = Column(Integer, nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    
    title = Column(String, nullable=False)
    content_html = Column(String, nullable=False)
    content_text = Column(String, nullable=False)
    
    created_by = Column(String, nullable=True) # e.g. 'ai-generator', 'editor-id'
    source = Column(String, nullable=False) # AI_GENERATED, EDITOR_EDIT, SYSTEM_UPDATE
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class NewsletterCampaign(Base):
    """
    Tracks a specific broadcast using a Briefing.
    """
    __tablename__ = "newsletter_campaigns"
    __table_args__ = (
        UniqueConstraint('briefing_id', name='uq_newsletter_campaign_briefing'),
    )

    id = Column(Integer, primary_key=True, index=True)
    briefing_id = Column(Integer, nullable=False, index=True)
    campaign_name = Column(String, nullable=False, index=True) # e.g. "Daily AI Briefing - 2026-07-01"
    
    status = Column(String, default="DRAFT", nullable=False) # DRAFT, SCHEDULED, SENDING, COMPLETED, FAILED, CANCELLED
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

class EmailDeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    SENDING = "SENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    OPENED = "OPENED" # Treated as OPEN_TRACKED
    CLICKED = "CLICKED"
    BOUNCED = "BOUNCED"
    COMPLAINED = "COMPLAINED"
    FAILED = "FAILED"

class EmailDeliveryRecord(Base):
    """
    Maps a campaign to a subscriber to track delivery lifecycle.
    """
    __tablename__ = "newsletter_email_deliveries"
    __table_args__ = (
        UniqueConstraint('campaign_id', 'subscriber_id', name='uq_email_delivery_campaign_subscriber'),
    )

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, nullable=False, index=True)
    subscriber_id = Column(Integer, nullable=False, index=True)
    
    status = Column(Enum(EmailDeliveryStatus), default=EmailDeliveryStatus.PENDING, nullable=False)
    provider_message_id = Column(String, nullable=True, index=True) # from Resend/SendGrid
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    bounced_at = Column(DateTime(timezone=True), nullable=True)
    
    error_message = Column(String, nullable=True)

class LinkClickRecord(Base):
    """
    Tracks which links a subscriber clicked in which campaign.
    """
    __tablename__ = "newsletter_link_clicks"

    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(Integer, nullable=False, index=True)
    url = Column(String, nullable=False)
    
    clicked_at = Column(DateTime(timezone=True), server_default=func.now())

class SuppressedEmail(Base):
    """
    A suppression list preventing sending to bad addresses.
    """
    __tablename__ = "newsletter_suppressed_emails"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    reason = Column(String, nullable=False) # HARD_BOUNCE, SPAM_COMPLAINT, MANUAL
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CampaignAnalyticsProjection(Base):
    """
    CQRS projection tracking engagement rates for campaigns.
    """
    __tablename__ = "newsletter_campaign_analytics"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, unique=True, nullable=False)
    
    total_recipients = Column(Integer, default=0, nullable=False)
    sent_count = Column(Integer, default=0, nullable=False)
    delivered_count = Column(Integer, default=0, nullable=False)
    opened_count = Column(Integer, default=0, nullable=False)
    clicked_count = Column(Integer, default=0, nullable=False)
    bounced_count = Column(Integer, default=0, nullable=False)
    complained_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    
    open_rate = Column(String, default="0.00", nullable=False)
    click_rate = Column(String, default="0.00", nullable=False)
    bounce_rate = Column(String, default="0.00", nullable=False)
    unsubscribe_rate = Column(String, default="0.00", nullable=False)
    delivery_rate = Column(String, default="0.00", nullable=False)
    
    last_processed_event_id = Column(Integer, nullable=True)
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
