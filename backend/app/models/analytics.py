from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)



# --- Analytics Read Models ---

class AnalyticsSession(Base):
    """
    Read model for user sessions.
    """
    __tablename__ = "analytics_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, unique=True)
    user_id = Column(String(255), nullable=True, index=True)

    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    device = Column(String(100), nullable=True)
    referrer = Column(String(255), nullable=True)


class ArticleMetrics(Base):
    """
    Read model for article-level aggregated metrics.
    """
    __tablename__ = "article_metrics"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(String(255), nullable=False, unique=True)

    views = Column(Integer, default=0, nullable=False)
    unique_views = Column(Integer, default=0, nullable=False)
    total_read_time_seconds = Column(Integer, default=0, nullable=False)
    avg_read_time_seconds = Column(Float, default=0.0, nullable=False)

    completed_reads = Column(Integer, default=0, nullable=False)
    completion_rate = Column(Float, default=0.0, nullable=False)

    shares = Column(Integer, default=0, nullable=False)

    projection_version = Column(Integer, default=1, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class DistributionMetrics(Base):
    """
    Read model for distribution aggregated metrics.
    """
    __tablename__ = "distribution_metrics"

    id = Column(Integer, primary_key=True, index=True)
    manifest_id = Column(String(255), nullable=False, unique=True)

    sent = Column(Integer, default=0, nullable=False)
    delivered = Column(Integer, default=0, nullable=False)
    bounced = Column(Integer, default=0, nullable=False)
    opened = Column(Integer, default=0, nullable=False)
    clicked = Column(Integer, default=0, nullable=False)

    projection_version = Column(Integer, default=1, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class EngagementMetrics(Base):
    """
    Read model for subscriber-level aggregated engagement.
    """
    __tablename__ = "engagement_metrics"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(String(255), nullable=False, unique=True)

    total_opens = Column(Integer, default=0, nullable=False)
    total_clicks = Column(Integer, default=0, nullable=False)
    unsubscribes = Column(Integer, default=0, nullable=False)

    projection_version = Column(Integer, default=1, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class SearchMetrics(Base):
    """
    Read model for search metrics.
    """
    __tablename__ = "search_metrics"

    id = Column(Integer, primary_key=True, index=True)
    query_string = Column(String(255), nullable=False, unique=True)

    search_count = Column(Integer, default=0, nullable=False)
    zero_result_count = Column(Integer, default=0, nullable=False)
    click_count = Column(Integer, default=0, nullable=False)

    projection_version = Column(Integer, default=1, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class AIInteractionMetrics(Base):
    """
    Read model for AI performance and usage metrics.
    """
    __tablename__ = "ai_interaction_metrics"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(100), nullable=False, unique=True)

    total_requests = Column(Integer, default=0, nullable=False)
    total_latency_ms = Column(Integer, default=0, nullable=False)
    avg_latency_ms = Column(Float, default=0.0, nullable=False)

    patches_proposed = Column(Integer, default=0, nullable=False)
    patches_accepted = Column(Integer, default=0, nullable=False)
    patches_rejected = Column(Integer, default=0, nullable=False)

    projection_version = Column(Integer, default=1, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class StoryTelemetrySnapshot(Base):
    """
    Time-series snapshot of a story's performance metrics.
    Collected hourly during the RC3.3A Calibration phase.
    """
    __tablename__ = "story_telemetry_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(String(255), nullable=False, index=True)
    captured_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    story_status = Column(String(50), nullable=False)
    story_age_hours = Column(Float, nullable=False)

    views = Column(Integer, default=0, nullable=False)
    unique_readers = Column(Integer, default=0, nullable=False)
    avg_read_time_seconds = Column(Float, default=0.0, nullable=False)
    avg_completion_rate = Column(Float, default=0.0, nullable=False)
    reawaken_count = Column(Integer, default=0, nullable=False)
    bookmarks = Column(Integer, default=0, nullable=False)
    newsletter_deliveries = Column(Integer, default=0, nullable=False)
    newsletter_clicks = Column(Integer, default=0, nullable=False)
    article_count = Column(Integer, default=0, nullable=False)

    snapshot_version = Column(Integer, default=1, nullable=False)

# TODO (Post-RC3.3B): StoryHealthSnapshot
# We will need a time-series record of StoryHealthProjection.
# Because StoryHealthProjection is ephemeral and constantly mutating (momentum, trend), 
# we need historical snapshots to answer: 
# - Why did this story become dormant?
# - Why did attention spike?
# - Why was it archived?
# 
# Proposed Schema:
# class StoryHealthSnapshot(Base):
#     __tablename__ = "story_health_snapshots"
#     id = Column(Integer, primary_key=True)
#     story_id = Column(String(255), index=True)
#     captured_at = Column(DateTime(timezone=True), default=utc_now)
#     momentum = Column(Float)
#     trend = Column(String)
#     attention_score = Column(Float)
#     coverage_score = Column(Float)
#     reawakening_signal_score = Column(Float)

class CoverageGapAnalytic(Base):
    """
    Formal representation of coverage gaps for the dashboard and Copilot.
    """
    __tablename__ = "coverage_gap_analytics"
    
    topic_id = Column(String(255), primary_key=True)
    search_volume_score = Column(Float, default=0.0)
    coverage_strength = Column(Float, default=0.0)
    gap_score = Column(Float, default=0.0)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
