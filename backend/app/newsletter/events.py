from pydantic import BaseModel
from datetime import datetime

class NewsletterSubscriptionCreated(BaseModel):
    """Domain event emitted when a new subscriber signs up."""
    subscriber_id: int
    email: str
    subscription_type: str
    timestamp: str

class NewsletterSubscriptionConfirmed(BaseModel):
    """Domain event emitted when a user completes double opt-in."""
    subscriber_id: int
    email: str
    timestamp: str

class NewsletterUnsubscribed(BaseModel):
    """Domain event emitted when a user unsubscribes."""
    subscriber_id: int
    email: str
    campaign_id: int | None = None
    timestamp: str

class DailyBriefingGenerated(BaseModel):
    """Emitted when AI finishes generating the daily digest."""
    briefing_id: int
    title: str
    timestamp: str

class BriefingApproved(BaseModel):
    """Emitted when a briefing is approved (auto or manual) to be sent."""
    briefing_id: int
    scheduled_at: str | None = None
    timestamp: str

class BriefingRejected(BaseModel):
    """Emitted when an editor rejects a briefing."""
    briefing_id: int
    timestamp: str

class BriefingUpdated(BaseModel):
    """Emitted when an editor creates a new version of a briefing."""
    briefing_id: int
    version_id: int
    timestamp: str

class EmailCampaignCreated(BaseModel):
    """Emitted when a broadcast campaign is initialized."""
    campaign_id: int
    briefing_id: int
    campaign_name: str
    timestamp: str

class EmailDispatchRequested(BaseModel):
    """Emitted to enqueue a single email for delivery."""
    campaign_id: int
    subscriber_id: int
    email: str
    timestamp: str

class EmailSent(BaseModel):
    """Emitted when the provider successfully queues/sends the email."""
    campaign_id: int
    subscriber_id: int
    delivery_id: int
    provider_message_id: str
    timestamp: str

class EmailOpened(BaseModel):
    """Emitted when the tracking pixel is loaded."""
    campaign_id: int
    subscriber_id: int
    delivery_id: int
    timestamp: str

class LinkClicked(BaseModel):
    """Emitted when a tracked link is clicked."""
    campaign_id: int
    subscriber_id: int
    delivery_id: int
    url: str
    timestamp: str

class EmailBounced(BaseModel):
    """Emitted when a hard bounce webhook is received."""
    email: str
    provider_message_id: str | None = None
    reason: str
    timestamp: str
