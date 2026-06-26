from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from app.newsletter.models import SubscriptionStatus

class NewsletterSubscribeRequest(BaseModel):
    email: EmailStr

class NewsletterResponse(BaseModel):
    success: bool
    message: str

class NewsletterStatsResponse(BaseModel):
    total_subscribers: int
    pending_subscribers: int
    confirmed_subscribers: int
    unsubscribed: int
    confirmation_rate: float
    new_today: int # Computed on the fly typically or projection extended

class BriefingUpdateRequest(BaseModel):
    title: str
    content_html: str
    content_text: str

class BriefingApprovalRequest(BaseModel):
    scheduled_at: Optional[datetime] = None

class BriefingVersionSchema(BaseModel):
    id: int
    version_number: int
    title: str
    created_by: Optional[str]
    source: str
    created_at: datetime
    content_html: str
    content_text: str
    class Config:
        from_attributes = True

class BriefingSchema(BaseModel):
    id: int
    status: str
    current_version_id: Optional[int]
    created_at: datetime
    approved_at: Optional[datetime]
    versions: list[BriefingVersionSchema] = []
    class Config:
        from_attributes = True

class CampaignSchema(BaseModel):
    id: int
    briefing_id: int
    campaign_name: str
    status: str
    created_at: datetime
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    class Config:
        from_attributes = True

class CampaignAnalyticsSchema(BaseModel):
    campaign_id: int
    total_recipients: int
    sent_count: int
    delivered_count: int
    opened_count: int
    clicked_count: int
    bounced_count: int
    complained_count: int
    failed_count: int
    open_rate: str
    click_rate: str
    bounce_rate: str
    unsubscribe_rate: str
    delivery_rate: str
    class Config:
        from_attributes = True
