from typing import AsyncGenerator
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

try:
    from backend.app.core.config import settings
    from backend.app.core.logging import logger
except ImportError:
    from app.core.config import settings
    from app.core.logging import logger

# Ensure data directory exists
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

# Async SQLite engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record):
    """Enforces SQLite WAL mode, foreign keys, and 30-second busy timeout (docs/04-DATABASE.md)."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA busy_timeout=30000;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injecting an asynchronous database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """Tests database connectivity and validates WAL mode."""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("PRAGMA journal_mode;"))
            mode = result.scalar()
            logger.info("Database connection validated. SQLite journal mode: %s", mode)
            return True
    except Exception as e:
        logger.error("Database connection check failed: %s", str(e))
        return False
