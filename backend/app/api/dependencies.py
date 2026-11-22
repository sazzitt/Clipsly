from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import Settings, settings
from backend.app.core.database import get_db


async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """Provides a request-scoped async database session with automatic commit/rollback."""
    async for session in get_db():
        yield session


def get_app_settings() -> Settings:
    """Provides application settings."""
    return settings
