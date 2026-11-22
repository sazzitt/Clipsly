import os
from pathlib import Path
import pytest
from backend.app.core.config import Settings, settings


def test_settings_defaults():
    """Verifies that default settings enforce local workstation isolation and correct ports."""
    assert settings.APP_NAME == "Clipsly"
    assert settings.VERSION == "1.0.0"
    assert settings.HOST == "127.0.0.1"
    assert settings.PORT == 8000
    assert "127.0.0.1" in settings.ALLOWED_HOSTS
    assert "localhost" in settings.ALLOWED_HOSTS


def test_directory_paths_exist():
    """Verifies that local storage engine directories are resolved properly."""
    assert settings.DATA_DIR.exists()
    assert settings.LOGS_DIR.exists()
    assert settings.STORAGE_DIR.exists()
    assert settings.UPLOAD_DIR.exists()
    assert settings.EXPORT_DIR.exists()
    assert settings.CACHE_DIR.exists()


def test_cors_origins_contain_local_vite():
    """Verifies that CORS origins only contain local development web interfaces."""
    assert "http://127.0.0.1:5173" in settings.CORS_ORIGINS
    assert "http://localhost:5173" in settings.CORS_ORIGINS
