"""
Database initialization script for Tech News Today - Phase 4.

Seeds roles, permissions, role_permissions, feature flags, and the
initial super_admin user. Safe to run multiple times (idempotent).

Usage:
    python -m app.core.init_db
"""

import asyncio
import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.permissions import Permission as PermissionEnum
from app.core.security import hash_password
from app.models.article import Category, ProcessedArticle, RawArticle
from app.editorial.models import EditorialDecisionLog

# Import Base and ALL models so metadata is registered
from app.models.base import Base
from app.models.growth import FeatureFlag
from app.models.source import Source
from app.models.user import (  # noqa: F401
    AIJobHistory,
    ArticleRevision,
    AuditLog,
    Notification,
    OAuthAccount,
    Permission,
    Role,
    RolePermission,
    SavedArticle,
    User,
    UserSession,
)

logger = logging.getLogger("tech_news.init_db")

# ---------------------------------------------------------------------------
# Seed Data Definitions
# ---------------------------------------------------------------------------

ROLES = [
    {"name": "reader", "description": "Standard reader with article browsing and bookmark capabilities"},
    {"name": "editor", "description": "Editorial staff with article review, approval, and content editing privileges"},
    {"name": "admin", "description": "Platform administrator with source, trend, telemetry, and user oversight"},
    {
        "name": "super_admin",
        "description": "Full platform control including infrastructure, emergency actions, and audit visibility",
    },
]

PERMISSIONS = [
    {"name": "read_articles", "description": "View published articles and search"},
    {"name": "save_bookmarks", "description": "Save and manage article bookmarks"},
    {"name": "manage_profile", "description": "Edit own profile settings"},
    {"name": "review_articles", "description": "Review and moderate article drafts"},
    {"name": "approve_articles", "description": "Approve articles for publication"},
    {"name": "reject_articles", "description": "Reject articles from publication queue"},
    {"name": "edit_article_content", "description": "Edit article titles, summaries, tags, and content"},
    {"name": "manage_sources", "description": "Enable, disable, and configure crawler sources"},
    {"name": "force_crawl", "description": "Trigger immediate source crawl operations"},
    {"name": "manage_trends", "description": "Override trend weights, merge, hide, and pin trends"},
    {"name": "view_telemetry", "description": "Access real-time operational telemetry dashboards"},
    {"name": "manage_users", "description": "View, search, suspend, and reactivate user accounts"},
    {"name": "promote_users", "description": "Promote or demote user roles"},
    {"name": "view_audit_logs", "description": "Access administrative audit trail"},
    {"name": "manage_ai_queue", "description": "Monitor, retry, pause, and resume AI processing jobs"},
    {"name": "manage_feature_flags", "description": "Toggle runtime feature flags"},
    {
        "name": "emergency_controls",
        "description": "Execute emergency ingestion locks, queue clears, and source shutdowns",
    },
    {"name": "manage_notifications", "description": "View and manage system notifications"},
    {"name": "full_admin", "description": "Unrestricted platform administration access"},
]

ROLE_PERMISSION_MAP = {
    "reader": [
        "read_articles",
        "save_bookmarks",
        "manage_profile",
    ],
    "editor": [
        "read_articles",
        "save_bookmarks",
        "manage_profile",
        "review_articles",
        "approve_articles",
        "reject_articles",
        "edit_article_content",
    ],
    "admin": [
        "read_articles",
        "save_bookmarks",
        "manage_profile",
        "review_articles",
        "approve_articles",
        "reject_articles",
        "edit_article_content",
        "manage_sources",
        "force_crawl",
        "manage_trends",
        "view_telemetry",
        "manage_users",
        "view_audit_logs",
        "manage_ai_queue",
        "manage_notifications",
    ],
    "super_admin": None,  # All permissions
}

FEATURE_FLAGS = [
    {
        "key": "ai_enrichment_enabled",
        "name": "AI Enrichment",
        "default_value": False,
        "environment_states": {"development": True, "staging": False, "production": False},
        "description": "Master toggle for AI summarization pipeline",
    },
    {
        "key": "enable_ai_processing",
        "name": "AI Processing Master",
        "default_value": True,
        "environment_states": {"development": True, "staging": True, "production": True},
        "description": "Master toggle for AI summarization pipeline",
    },
    {
        "key": "enable_trends",
        "name": "Trends Engine",
        "default_value": True,
        "environment_states": {"development": True, "staging": True, "production": True},
        "description": "Master toggle for trend calculation engine",
    },
    {
        "key": "enable_crawling",
        "name": "Automated Crawling",
        "default_value": True,
        "environment_states": {"development": True, "staging": True, "production": True},
        "description": "Master toggle for automated source crawling",
    },
    {
        "key": "emergency_pause_ingestion",
        "name": "Emergency Ingestion Pause",
        "default_value": False,
        "environment_states": {"development": False, "staging": False, "production": False},
        "description": "Emergency kill-switch to halt all ingestion pipelines",
    },
    {
        "key": "enable_google_oauth",
        "name": "Google OAuth",
        "default_value": True,
        "environment_states": {"development": True, "staging": True, "production": True},
        "description": "Toggle Google OAuth sign-in availability",
    },
    {
        "key": "enable_registration",
        "name": "User Registration",
        "default_value": True,
        "environment_states": {"development": True, "staging": True, "production": True},
        "description": "Toggle new user self-registration",
    },
]

CATEGORIES = [
    {"name": "Artificial Intelligence", "slug": "artificial-intelligence"},
    {"name": "Robotics", "slug": "robotics"},
    {"name": "Startups", "slug": "startups"},
    {"name": "Cybersecurity", "slug": "cybersecurity"},
    {"name": "Software Development", "slug": "software-development"},
    {"name": "Space & Science", "slug": "space-science"},
]

SOURCES = [
    {
        "name": "Google Blog",
        "slug": "google",
        "category": "official",
        "method": "rss",
        "url": "https://blog.google/rss/",
        "credibility_score": 98,
        "crawl_interval": 900,
        "description": "Official announcements, product breakthroughs, and research from Google.",
        "logo_url": "/logos/google.svg",
    },
    {
        "name": "OpenAI Blog",
        "slug": "openai",
        "category": "official",
        "method": "rss",
        "url": "https://openai.com/news/rss.xml",
        "credibility_score": 98,
        "crawl_interval": 900,
        "description": "Frontier AI research, GPT model releases, and company updates from OpenAI.",
        "logo_url": "/logos/openai.svg",
    },
    {
        "name": "Anthropic News",
        "slug": "anthropic",
        "category": "official",
        "method": "html_adapter",
        "url": "https://www.anthropic.com/news",
        "credibility_score": 98,
        "crawl_interval": 900,
        "description": "Claude releases, alignment research, and company updates from Anthropic.",
        "logo_url": "/logos/anthropic.svg",
    },
    {
        "name": "NVIDIA AI Blog",
        "slug": "nvidia",
        "category": "official",
        "method": "rss",
        "url": "https://blogs.nvidia.com/feed/",
        "credibility_score": 98,
        "crawl_interval": 1800,
        "description": "Accelerated computing, GPUs, AI infrastructure, and robotics from NVIDIA.",
        "logo_url": "/logos/nvidia.svg",
    },
    {
        "name": "Microsoft Blog",
        "slug": "microsoft",
        "category": "official",
        "method": "rss",
        "url": "https://blogs.microsoft.com/feed/",
        "credibility_score": 96,
        "crawl_interval": 1800,
        "description": "Official Microsoft technology, Copilot, and Azure announcements.",
        "logo_url": "/logos/microsoft.svg",
    },
    {
        "name": "Meta Newsroom",
        "slug": "meta",
        "category": "official",
        "method": "rss",
        "url": "https://about.fb.com/news/feed/",
        "credibility_score": 95,
        "crawl_interval": 1800,
        "description": "Llama models, open-source AI, hardware, and metaverse news from Meta.",
        "logo_url": "/logos/meta.svg",
    },
    {
        "name": "Apple Newsroom",
        "slug": "apple",
        "category": "official",
        "method": "rss",
        "url": "https://www.apple.com/newsroom/rss-feed.rss",
        "credibility_score": 96,
        "crawl_interval": 1800,
        "description": "Official announcements, hardware releases, and OS updates from Apple.",
        "logo_url": "/logos/apple.svg",
    },
    {
        "name": "Google DeepMind",
        "slug": "google-deepmind",
        "category": "official",
        "method": "rss",
        "url": "https://deepmind.google/blog/feed/basic/",
        "credibility_score": 98,
        "crawl_interval": 1800,
        "description": "Cutting-edge artificial intelligence, AlphaFold, and fundamental science from DeepMind.",
        "logo_url": "/logos/deepmind.svg",
    },
    {
        "name": "TechCrunch",
        "slug": "techcrunch",
        "category": "editorial",
        "method": "rss",
        "url": "https://techcrunch.com/feed/",
        "credibility_score": 92,
        "crawl_interval": 600,
        "description": "Venture capital, startup funding rounds, and Silicon Valley technology news.",
        "logo_url": "/logos/techcrunch.svg",
    },
    {
        "name": "The Verge",
        "slug": "the-verge",
        "category": "editorial",
        "method": "rss",
        "url": "https://www.theverge.com/rss/index.xml",
        "credibility_score": 90,
        "crawl_interval": 600,
        "description": "In-depth reviews, consumer electronics, and cultural tech reporting.",
        "logo_url": "/logos/theverge.svg",
    },
    {
        "name": "Ars Technica",
        "slug": "ars-technica",
        "category": "editorial",
        "method": "rss",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "credibility_score": 88,
        "crawl_interval": 1200,
        "description": "Rigorous technical analysis, cybersecurity deep dives, and hardware reporting.",
        "logo_url": "/logos/arstechnica.svg",
    },
    {
        "name": "MIT Technology Review",
        "slug": "mit-technology-review",
        "category": "editorial",
        "method": "rss",
        "url": "https://www.technologyreview.com/feed/",
        "credibility_score": 95,
        "crawl_interval": 1800,
        "description": "Authoritative journalism exploring the commercial and societal impact of emerging tech.",
        "logo_url": "/logos/mit.svg",
    },
    {
        "name": "Hacker News",
        "slug": "hacker-news",
        "category": "community",
        "method": "api",
        "url": "https://hacker-news.firebaseio.com/v0",
        "credibility_score": 85,
        "crawl_interval": 300,
        "description": "Real-time developer and technologist community discussions from Y Combinator.",
        "logo_url": "/logos/hackernews.svg",
    },
    {
        "name": "GitHub Trending",
        "slug": "github-trending",
        "category": "community",
        "method": "scraping",
        "url": "https://github.com/trending",
        "credibility_score": 80,
        "crawl_interval": 1800,
        "description": "Trending open-source repositories and emerging developer tools.",
        "logo_url": "/logos/github.svg",
    },
    {
        "name": "Reddit MachineLearning",
        "slug": "reddit-machinelearning",
        "category": "community",
        "method": "rss",
        "url": "https://www.reddit.com/r/MachineLearning/.rss",
        "credibility_score": 70,
        "crawl_interval": 900,
        "description": "Community submissions and discussions on machine learning papers and projects.",
        "logo_url": "/logos/reddit.svg",
    },
]



async def main():
    """Initialize the database schema and seed essential reference data."""
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s [%(name)s] - %(message)s")
    logger.info("Starting database initialization...")

    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    # Validate Seeded Permissions against Registry
    valid_permissions = {p.value for p in PermissionEnum}
    for perm in PERMISSIONS:
        if perm["name"] not in valid_permissions:
            logger.error(f"FATAL: Seeded permission '{perm['name']}' does not exist in Permission enum registry.")
            raise ValueError(f"Invalid permission: {perm['name']}")

    for role_name, perms in ROLE_PERMISSION_MAP.items():
        if perms is not None:
            for p in perms:
                if p not in valid_permissions:
                    logger.error(f"FATAL: Role '{role_name}' references invalid permission '{p}'.")
                    raise ValueError(f"Invalid permission for role {role_name}: {p}")
    logger.info("Validated all seeded permissions against registry.")

    # Create all tables from ORM metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified via ORM metadata.")

    # Ensure required columns exist across tables
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE sources ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE"))
        await conn.execute(text("ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS lease_id VARCHAR(100)"))
        await conn.execute(text("ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMPTZ"))
        await conn.execute(text("ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0"))
        await conn.execute(text("ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 3"))
        await conn.execute(text("ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS error_log TEXT"))
        await conn.execute(text("ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(255)"))
    logger.info("Checked/applied required schema migrations.")

    async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        async with session.begin():
            # --- Seed Roles ---
            role_map = {}
            for role_data in ROLES:
                existing = await session.execute(select(Role).where(Role.name == role_data["name"]))
                role = existing.scalars().first()
                if role is None:
                    role = Role(**role_data)
                    session.add(role)
                    await session.flush()
                    logger.info(f"Created role: {role_data['name']}")
                else:
                    logger.info(f"Role already exists: {role_data['name']}")
                role_map[role.name] = role.id

            # --- Seed Permissions ---
            perm_map = {}
            for perm_data in PERMISSIONS:
                existing = await session.execute(select(Permission).where(Permission.name == perm_data["name"]))
                perm = existing.scalars().first()
                if perm is None:
                    perm = Permission(**perm_data)
                    session.add(perm)
                    await session.flush()
                    logger.info(f"Created permission: {perm_data['name']}")
                else:
                    logger.info(f"Permission already exists: {perm_data['name']}")
                perm_map[perm.name] = perm.id

            # --- Seed Role-Permission Mappings ---
            all_perm_names = list(perm_map.keys())
            for role_name, perm_names in ROLE_PERMISSION_MAP.items():
                target_perms = perm_names if perm_names is not None else all_perm_names
                rid = role_map.get(role_name)
                if rid is None:
                    continue

                for perm_name in target_perms:
                    pid = perm_map.get(perm_name)
                    if pid is None:
                        continue
                    existing_rp = await session.execute(
                        select(RolePermission).where(
                            RolePermission.role_id == rid,
                            RolePermission.permission_id == pid,
                        )
                    )
                    if existing_rp.scalars().first() is None:
                        rp = RolePermission(role_id=rid, permission_id=pid)
                        session.add(rp)

                logger.info(f"Role-permission mappings verified for: {role_name}")

            await session.flush()

            # --- Seed Feature Flags ---
            for flag_data in FEATURE_FLAGS:
                existing = await session.execute(select(FeatureFlag).where(FeatureFlag.key == flag_data["key"]))
                if existing.scalars().first() is None:
                    flag = FeatureFlag(**flag_data)
                    session.add(flag)
                    logger.info(f"Created feature flag: {flag_data['key']}")
                else:
                    logger.info(f"Feature flag already exists: {flag_data['key']}")

            await session.flush()

            # --- Seed Categories ---
            for cat_data in CATEGORIES:
                existing = await session.execute(select(Category).where(Category.name == cat_data["name"]))
                if existing.scalars().first() is None:
                    cat = Category(**cat_data)
                    session.add(cat)
                    logger.info(f"Created category: {cat_data['name']}")
                else:
                    logger.info(f"Category already exists: {cat_data['name']}")

            await session.flush()

            # --- Seed Sources ---
            for source_data in SOURCES:
                existing = await session.execute(
                    select(Source).where(
                        or_(
                            Source.name == source_data["name"],
                            Source.url == source_data["url"],
                            Source.slug == source_data["slug"],
                        )
                    )
                )
                src = existing.scalars().first()
                if src is None:
                    src = Source(**source_data)
                    session.add(src)
                    logger.info(f"Created source: {source_data['name']}")
                else:
                    src.name = source_data["name"]
                    src.url = source_data["url"]
                    src.method = source_data["method"]
                    src.slug = source_data.get("slug")
                    src.description = source_data.get("description")
                    src.logo_url = source_data.get("logo_url")
                    src.category = source_data.get("category", src.category)
                    src.credibility_score = source_data.get("credibility_score", src.credibility_score)
                    logger.info(f"Updated source: {source_data['name']} (slug: {src.slug}, category: {src.category})")

            await session.flush()

            # --- Seed Initial Super Admin User ---
            admin_email = settings.ADMIN_EMAIL or settings.INITIAL_ADMIN_EMAIL
            admin_password_hash = settings.ADMIN_PASSWORD_HASH
            admin_password_plain = settings.INITIAL_ADMIN_PASSWORD

            if admin_email:
                existing_admin = await session.execute(select(User).where(User.email == admin_email))
                if existing_admin.scalars().first() is None:
                    super_admin_role_id = role_map.get("super_admin")
                    if super_admin_role_id is None:
                        logger.error("Cannot create admin: super_admin role not found.")
                    else:
                        is_valid_hash = admin_password_hash and (
                            admin_password_hash.startswith("$2a$")
                            or admin_password_hash.startswith("$2b$")
                            or admin_password_hash.startswith("$2y$")
                        )
                        if is_valid_hash:
                            hashed = admin_password_hash
                        else:
                            if admin_password_hash:
                                logger.warning(
                                    "Provided ADMIN_PASSWORD_HASH is invalid. Ignoring it and falling back to INITIAL_ADMIN_PASSWORD."
                                )
                            if admin_password_plain:
                                hashed = hash_password(admin_password_plain)
                            else:
                                logger.error("Cannot create admin: neither password hash nor plain password set.")
                                hashed = None

                        if hashed:
                            admin_user = User(
                                name="Super Admin",
                                email=admin_email,
                                password_hash=hashed,
                                role_id=super_admin_role_id,
                                status="active",
                            )
                            session.add(admin_user)
                            await session.flush()
                            logger.info(f"Created initial super_admin user: {admin_email}")
                else:
                    logger.info(f"Initial admin user already exists: {admin_email}")
            else:
                logger.warning("INITIAL_ADMIN_EMAIL or ADMIN_EMAIL not set. Skipping initial admin user creation.")

            # --- Trigger Initial Ingestion ---
            try:
                # Check if there are any articles to ensure idempotency
                raw_res = await session.execute(select(RawArticle).limit(1))
                proc_res = await session.execute(select(ProcessedArticle).limit(1))

                if raw_res.scalars().first() is None and proc_res.scalars().first() is None:
                    try:
                        from celery_app import run_scheduled_scrapers_task
                        run_scheduled_scrapers_task.delay()
                        logger.info("Triggered initial news ingestion task to populate homepage.")
                    except Exception as ce:
                        logger.warning(f"Could not enqueue initial ingestion task via Celery/Redis: {ce}")
                else:
                    logger.info("Articles already exist in database, skipping initial ingestion trigger.")
            except Exception as e:
                logger.error(f"Failed to trigger initial ingestion: {e}")

        # session.begin() auto-commits on successful exit

    await engine.dispose()
    logger.info("Database initialization completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
