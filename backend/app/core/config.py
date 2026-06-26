import json
from typing import Annotated

from pydantic import BeforeValidator, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def assemble_cors_origins(v: str | list[str]) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, (list, str)):
        return v
import os
from dotenv import load_dotenv

app_env_val = os.environ.get("APP_ENV", "development").lower()
env_file_path = f".env.{app_env_val}" if app_env_val != "development" else ".env"

# Override docker-injected OS env vars ONLY for test environment
if app_env_val == "test" and os.path.exists(env_file_path):
    load_dotenv(env_file_path, override=True)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=env_file_path, env_ignore_empty=True, extra="ignore")

    PROJECT_NAME: str = "Tech News Today"
    APP_ENV: str = ""
    EDITORIAL_WINDOW_HOURS: int = 24
    MAX_ARTICLES_PER_CATEGORY: int = 3
    FRESHNESS_DECAY_MODEL: str = "curved"  # "linear" or "curved"
    MAX_HOMEPAGE_ARTICLES: int = 30
    MINIMUM_EFFECTIVE_SCORE: float = 20.0
    EDITORIAL_ALGORITHM_VERSION: str = "v1"

    # ENV is kept as a legacy alias while new deployments use APP_ENV.
    ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "supersecretkey_change_me_in_production_32_chars_long"

    # CORS Configuration
    BACKEND_CORS_ORIGINS: Annotated[list[str] | str, BeforeValidator(assemble_cors_origins)] = []

    @field_validator("BACKEND_CORS_ORIGINS")
    @classmethod
    def check_cors_origins(cls, v: list[str] | str) -> list[str] | str:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        return v

    # PostgreSQL Exclusive (No SQLite Fallback allowed)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres_secure_pass@db:5432/tech_news_today"

    # Observability and Health Configurations
    BACKEND_HEALTH_URL: str = "http://backend:8000/api/v1/health/live"

    HEALTH_THRESHOLDS: dict = {
        "postgres": {"healthy": 100.0, "delayed": 300.0, "degraded": 1000.0},
        "redis": {"healthy": 100.0, "delayed": 300.0, "degraded": 1000.0},
        "backend": {"healthy": 500.0, "delayed": 2000.0, "degraded": 4000.0},
        "beat": {"online": 10.0, "delayed": 20.0, "degraded": 30.0},
    }

    # Redis Broker/Cache Configs
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # Recommendation Engine Config
    REC_WEIGHT_SIMILARITY: float = 0.45
    REC_WEIGHT_FRESHNESS: float = 0.20
    REC_WEIGHT_EDITORIAL: float = 0.15
    REC_WEIGHT_TRENDING: float = 0.10
    REC_WEIGHT_NOVELTY: float = 0.05
    REC_WEIGHT_DIVERSITY: float = 0.05

    # AI Configs (Provider-Agnostic Setup)
    OPENAI_API_KEY: str = "sk-placeholder-openai-api-key"
    GEMINI_API_KEY: str | None = None
    AI_PROVIDER: str = "disabled"
    AI_PROVIDER_PRIORITY: str = "openai,anthropic,gemini"
    AI_MODEL: str = "phase4-foundation"

    # Embedding config
    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    MAX_AI_RETRIES: int = 3
    AI_REQUEST_TIMEOUT_SECONDS: float = 20.0
    AI_MAX_INPUT_CHARS: int = 12000
    AI_MAX_OUTPUT_TOKENS: int = 700
    AI_DAILY_BUDGET_USD: str = "5.00"
    AI_MONTHLY_BUDGET_USD: str = "75.00"

    # Scrapers
    SCRAPER_RATE_LIMIT_DELAY: float = 2.0
    MAX_THUMBNAIL_CANDIDATES: int = 4
    USER_AGENT: str = "TechNewsTodayBot/1.0 (+http://localhost/bot)"

    # Storage and Uploads
    STORAGE_ROOT: str = "storage"
    UPLOAD_DIR: str = "storage/uploads"
    UPLOAD_PUBLIC_PREFIX: str = "/api/v1/uploads"

    # Configurable Ranking Engine Mappings
    RANKING_COMPANY_WEIGHTS: dict = {
        "openai": 30.0,
        "nvidia": 30.0,
        "google": 25.0,
        "microsoft": 25.0,
        "anthropic": 25.0,
        "apple": 20.0,
        "meta": 20.0,
        "amazon": 15.0,
    }
    RANKING_TECH_KEYWORDS: dict = {
        "gpt-6": 35.0,
        "gpt-5": 30.0,
        "claude 4": 30.0,
        "llama 4": 30.0,
        "gemini 2": 25.0,
        "model release": 25.0,
        "breach": 25.0,
        "data leak": 25.0,
        "cybersecurity": 20.0,
        "hack": 20.0,
        "exploit": 20.0,
        "leak": 15.0,
        "space launch": 20.0,
        "spacex": 20.0,
        "orbit": 15.0,
        "acquisition": 25.0,
        "acquire": 25.0,
        "merger": 25.0,
        "buyout": 25.0,
        "regulatory": 20.0,
        "regulation": 20.0,
        "antitrust": 20.0,
        "lawsuit": 15.0,
    }
    RANKING_REDUCTIONS: dict = {
        "minor update": -15.0,
        "product update": -10.0,
        "funding round": -10.0,
        "blog post": -15.0,
    }

    # Embedding Settings
    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    # Semantic Match Thresholds (Cosine Similarity)
    CLUSTER_THRESHOLD: float = 0.90
    RELATED_THRESHOLD: float = 0.80
    SEARCH_THRESHOLD: float = 0.70

    # Hybrid Ranking Weights
    SEMANTIC_WEIGHT: float = 0.60
    KEYWORD_WEIGHT: float = 0.20
    FRESHNESS_WEIGHT: float = 0.10
    CREDIBILITY_WEIGHT: float = 0.10
    # JWT Authentication
    JWT_SECRET_KEY: str = "phase4_dev_jwt_secret_key_change_in_production_64chars_minimum_okay"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Initial Admin Provisioning
    INITIAL_ADMIN_EMAIL: str = ""
    INITIAL_ADMIN_PASSWORD: str = ""
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD_HASH: str = ""

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_ADMIN_EMAIL: str = ""

    # Backup & Disaster Recovery Configurations
    BACKUP_ENCRYPTION_KEY: str = "dev_only_super_secure_32_character_encryption_key!"
    BACKUP_SIGNING_KEY: str = "dev_only_super_secure_32_character_signing_key!!!!"
    BACKUP_STORAGE_BACKEND: str = "local"
    BACKUP_COMPRESSION: str = "gzip"
    BACKUP_STORAGE_PATH: str = "storage/backups"

    @model_validator(mode="after")
    def validate_production_readiness(self) -> "Settings":
        # Log loaded environment
        import logging

        logger = logging.getLogger("tech_news.config")
        app_env = self.effective_environment
        if app_env not in {"development", "staging", "production", "test"}:
            raise ValueError("APP_ENV must be one of: development, staging, production, test")

        logger.info(f"Configuration settings loaded successfully for environment: {app_env.upper()}")

        if app_env == "test":
            from urllib.parse import urlparse
            parsed = urlparse(self.DATABASE_URL)
            if "tech_news_today_test" not in parsed.path:
                logger.critical(f"CRITICAL: Test database name must be 'tech_news_today_test'. Got: {parsed.path}")
                raise RuntimeError("Tests are attempting to run against a non-test database.")
            if parsed.hostname and "prod" in parsed.hostname.lower():
                logger.critical(f"CRITICAL: Test database host cannot be a production server. Got: {parsed.hostname}")
                raise RuntimeError("Tests are attempting to run against a production database host.")

        if app_env == "production":
            # 1. Fail fast on default secret key
            if self.SECRET_KEY in (
                "supersecretkey_change_me_in_production_32_chars_long",
                "dev_only_super_secure_32_character_secret_key",
                "change_me",
            ):
                logger.critical("CRITICAL: Invalid SECRET_KEY in production environment!")
                raise ValueError("SECRET_KEY must be a strong, non-default value in production!")

            # Validate backup keys in production
            if "dev_only" in self.BACKUP_ENCRYPTION_KEY or "encryption_key" in self.BACKUP_ENCRYPTION_KEY:
                logger.critical("CRITICAL: Invalid BACKUP_ENCRYPTION_KEY in production environment!")
                raise ValueError("BACKUP_ENCRYPTION_KEY must be a strong, non-default value in production!")

            if "dev_only" in self.BACKUP_SIGNING_KEY or "signing_key" in self.BACKUP_SIGNING_KEY:
                logger.critical("CRITICAL: Invalid BACKUP_SIGNING_KEY in production environment!")
                raise ValueError("BACKUP_SIGNING_KEY must be a strong, non-default value in production!")

            # 2. Fail fast on default JWT secret key
            if "phase4_dev" in self.JWT_SECRET_KEY or "change_in_production" in self.JWT_SECRET_KEY:
                logger.critical("CRITICAL: Invalid JWT_SECRET_KEY in production environment!")
                raise ValueError("JWT_SECRET_KEY must be a strong, non-default value in production!")

            # 3. Prevent wildcard CORS in production
            if isinstance(self.BACKEND_CORS_ORIGINS, list):
                if "*" in self.BACKEND_CORS_ORIGINS:
                    logger.critical("CRITICAL: CORS wildcard ('*') is strictly prohibited in production!")
                    raise ValueError("CORS wildcard ('*') is strictly prohibited in production!")
            elif self.BACKEND_CORS_ORIGINS == "*":
                logger.critical("CRITICAL: CORS wildcard ('*') is strictly prohibited in production!")
                raise ValueError("CORS wildcard ('*') is strictly prohibited in production!")

            # 4. Fail fast on placeholder AI API Key in production if provider is OpenAI
            if self.AI_PROVIDER == "openai" and "placeholder" in self.OPENAI_API_KEY.lower():
                logger.critical("CRITICAL: Invalid OPENAI_API_KEY in production environment!")
                raise ValueError("A real OPENAI_API_KEY must be supplied in a production environment!")

        return self

    @property
    def effective_environment(self) -> str:
        return (self.APP_ENV or self.ENV or "development").lower()


settings = Settings()
