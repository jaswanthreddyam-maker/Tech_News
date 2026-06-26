from enum import Enum


class Permission(str, Enum):
    READ_ARTICLES = "read_articles"
    SAVE_BOOKMARKS = "save_bookmarks"
    MANAGE_PROFILE = "manage_profile"
    REVIEW_ARTICLES = "review_articles"
    APPROVE_ARTICLES = "approve_articles"
    REJECT_ARTICLES = "reject_articles"
    EDIT_ARTICLE_CONTENT = "edit_article_content"
    MANAGE_SOURCES = "manage_sources"
    FORCE_CRAWL = "force_crawl"
    MANAGE_TRENDS = "manage_trends"
    VIEW_TELEMETRY = "view_telemetry"
    MANAGE_USERS = "manage_users"
    PROMOTE_USERS = "promote_users"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_AI_QUEUE = "manage_ai_queue"
    MANAGE_FEATURE_FLAGS = "manage_feature_flags"
    EMERGENCY_CONTROLS = "emergency_controls"
    MANAGE_NOTIFICATIONS = "manage_notifications"
    FULL_ADMIN = "full_admin"
