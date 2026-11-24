from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application configuration managing local workstation paths, ports, and models."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "Clipsly"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Local-only loopback binding
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"

    # CORS origins: Strictly local Vite dev server
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    ALLOWED_HOSTS: list[str] = [
        "127.0.0.1",
        "localhost",
        "127.0.0.1:8000",
        "localhost:8000",
    ]

    # Base filesystem paths relative to Clipsly root
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    LOGS_DIR: Path = PROJECT_ROOT / "logs"
    STORAGE_DIR: Path = PROJECT_ROOT / "storage"

    DATABASE_URL: str = f"sqlite+aiosqlite:///{PROJECT_ROOT / 'data' / 'clipsly.db'}"

    # Request limits & timeouts
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024 * 1024  # 10GB max file size
    MIN_VIDEO_DURATION_SECONDS: float = 300.0  # 5 minutes
    MAX_VIDEO_DURATION_SECONDS: float = 7200.0  # 120 minutes
    ENFORCE_DURATION_LIMITS: bool = True
    ALLOWED_VIDEO_EXTENSIONS: list[str] = [".mp4", ".mkv", ".mov", ".webm"]
    UPLOAD_CHUNK_SIZE_BYTES: int = 1024 * 1024  # 1MB buffer
    API_TIMEOUT_SECONDS: int = 30
    LOG_LEVEL: str = "INFO"

    # Hardware & Model Defaults (ADR-002: 4GB VRAM constraint)
    TRANSCRIPTION_MODEL: str = "base"
    TRANSCRIPTION_COMPUTE_TYPE: str = "float16"
    FORCE_CPU_TRANSCRIPTION: bool = False
    WHISPER_BEAM_SIZE: int = 5
    DEFAULT_WHISPER_LANGUAGE: str | None = None  # None = auto-detect
    ENABLE_WORD_TIMESTAMPS: bool = True

    # Silero VAD Settings (Section 8)
    VAD_ENABLED: bool = True
    VAD_THRESHOLD: float = 0.5
    VAD_MIN_SPEECH_DURATION_MS: int = 250
    VAD_MAX_SPEECH_DURATION_S: float = 30.0
    VAD_MIN_SILENCE_DURATION_MS: int = 2000
    VAD_SPEECH_PAD_MS: int = 400

    DEFAULT_VIDEO_ENCODER: str = "h264_nvenc"
    MIN_FREE_DISK_SPACE_GB: int = 10

    # Optional External AI API Key (None by default, sovereign heuristic engine preferred)
    EXTERNAL_AI_API_KEY: str | None = None

    @property
    def UPLOAD_DIR(self) -> Path:
        return self.STORAGE_DIR / "uploads"

    @property
    def EXPORT_DIR(self) -> Path:
        return self.STORAGE_DIR / "exports"

    @property
    def CLIPS_DIR(self) -> Path:
        return self.STORAGE_DIR / "clips"

    @property
    def CACHE_DIR(self) -> Path:
        return self.STORAGE_DIR / "cache"

    @property
    def AUDIO_DIR(self) -> Path:
        return self.STORAGE_DIR / "audio"

    @property
    def TEMP_DIR(self) -> Path:
        return self.STORAGE_DIR / "temp"

    @property
    def SUBTITLES_DIR(self) -> Path:
        return self.STORAGE_DIR / "subtitles"

    @property
    def WHISPER_MODELS_DIR(self) -> Path:
        return self.DATA_DIR / "models" / "whisper"

    def model_post_init(self, __context) -> None:
        """Ensures that all local filesystem storage directories exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.CLIPS_DIR.mkdir(parents=True, exist_ok=True)
        self.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        self.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        self.SUBTITLES_DIR.mkdir(parents=True, exist_ok=True)
        self.WHISPER_MODELS_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
