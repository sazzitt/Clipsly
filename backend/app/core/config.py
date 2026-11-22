from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment or defaults."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "Clipsly"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # CORS origins: Strictly local Vite dev server
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Base filesystem paths relative to Clipsly root
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    LOGS_DIR: Path = PROJECT_ROOT / "logs"
    STORAGE_DIR: Path = PROJECT_ROOT / "storage"

    DATABASE_URL: str = f"sqlite+aiosqlite:///{PROJECT_ROOT / 'data' / 'clipsly.db'}"

    # Hardware & Model Defaults
    TRANSCRIPTION_MODEL: str = "small"
    TRANSCRIPTION_COMPUTE_TYPE: str = "float16"
    FORCE_CPU_TRANSCRIPTION: bool = False
    DEFAULT_VIDEO_ENCODER: str = "h264_nvenc"
    MIN_FREE_DISK_SPACE_GB: int = 10

    # Optional External AI API Key (None by default)
    EXTERNAL_AI_API_KEY: str | None = None


settings = Settings()
