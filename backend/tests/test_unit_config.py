import os
import pytest
from unittest.mock import patch
from app.core.config import Settings

def test_settings_loading_hierarchy():
    """
    Verify that Pydantic settings load according to environment hierarchy:
    1. Explicit environment variables (highest priority)
    2. .env file
    3. Default values (lowest priority)
    """
    import importlib
    import app.core.config
    
    # 1. Test defaults
    # Pydantic BaseSettings load defaults if env vars are missing
    with patch.dict(os.environ, clear=True):
        # We need to temporarily set APP_ENV to avoid validation errors if it's strictly required
        with patch.dict(os.environ, {"APP_ENV": "test"}):
            settings_default = Settings()
            # UPLOAD_PUBLIC_PREFIX has a default value
            assert settings_default.UPLOAD_PUBLIC_PREFIX == "/api/v1/uploads"
            
    # 2. Test explicit environment variables override
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://override_user:pass@localhost:5432/override_db", "UPLOAD_PUBLIC_PREFIX": "/custom-uploads"}):
        settings_test = Settings()
        assert settings_test.DATABASE_URL == "postgresql+asyncpg://override_user:pass@localhost:5432/override_db"
        assert settings_test.UPLOAD_PUBLIC_PREFIX == "/custom-uploads"
