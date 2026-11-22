import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path

try:
    from backend.app.core.config import settings
except ImportError:
    from app.core.config import settings


def setup_logging() -> None:
    """Configures structured application logging with rotating file handler and stdout."""
    logs_dir = settings.LOGS_DIR
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "clipsly_app.log"

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Rotating file handler: 10 MB per file, max 5 backup files (50 MB total cap)
    file_handler = RotatingFileHandler(
        str(log_file),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))

    numeric_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    if settings.DEBUG:
        numeric_level = logging.DEBUG

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers = [stream_handler, file_handler]

    # Silence overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


logger = logging.getLogger("clipsly")
