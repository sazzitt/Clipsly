import pytest
from sqlalchemy import text
from backend.app.core.database import AsyncSessionLocal, check_db_connection, engine


@pytest.mark.asyncio
async def test_check_db_connection():
    """Verifies that the database connection check succeeds and returns True."""
    connected = await check_db_connection()
    assert connected is True


@pytest.mark.asyncio
async def test_sqlite_pragmas():
    """Verifies SQLite WAL journal mode and foreign key enforcement."""
    async with AsyncSessionLocal() as session:
        # Check WAL mode
        result = await session.execute(text("PRAGMA journal_mode;"))
        journal_mode = result.scalar()
        assert journal_mode.upper() == "WAL"

        # Check foreign keys
        result = await session.execute(text("PRAGMA foreign_keys;"))
        fk_enabled = result.scalar()
        assert fk_enabled == 1
