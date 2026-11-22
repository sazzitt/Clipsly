import logging
import sys
from pathlib import Path

try:
    from backend.app.core.config import settings
except ImportError:
    from app.core.config import settings


def setup_logging() -> None:
    """Configures structured application logging to stdout and logs/app.log."""
    logs_dir = settings.LOGS_DIR
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "clipsly_app.log"

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(log_file), encoding="utf-8")
    ]

    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
        force=True
    )

    # Silence overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)


logger = logging.getLogger("clipsly")
