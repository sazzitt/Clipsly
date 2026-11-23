from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class NormalizedWord(BaseModel):
    """Canonical representation of a word-level timing token."""
    text: str
    start_ms: int
    end_ms: int
    confidence: Optional[float] = None

    model_config = ConfigDict(extra="ignore")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Word text cannot be empty or whitespace only.")
        return s

    @field_validator("start_ms")
    @classmethod
    def validate_start_ms(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"start_ms must be non-negative, got {v}")
        return v

    @field_validator("end_ms")
    @classmethod
    def validate_end_ms(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"end_ms must be non-negative, got {v}")
        return v


class CaptionEventData(BaseModel):
    """In-memory representation of a line-level caption event grouping words."""
    sequence_index: int = Field(ge=0)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    text: str
    words: List[NormalizedWord]
    style_name: str = "Default"
    is_modified: bool = False

    model_config = ConfigDict(extra="ignore")

    @field_validator("end_ms")
    @classmethod
    def validate_timing(cls, v: int, info) -> int:
        start = info.data.get("start_ms", 0)
        if v <= start:
            raise ValueError(f"end_ms ({v}) must be strictly greater than start_ms ({start})")
        return v


# --- API Request and Response Schemas ---

class SubtitleGenerateRequest(BaseModel):
    """Request payload to generate a subtitle track for a clip."""
    preset_name: str = Field(default="KARAOKE_AMBER", max_length=64)
    max_words_per_line: int = Field(default=4, ge=1, le=10)
    max_chars_per_line: int = Field(default=28, ge=10, le=80)
    force_realign: bool = False


class SubtitleEventResponse(BaseModel):
    """Serialized caption event for client API responses."""
    id: str
    sequence_index: int
    start_ms: int
    end_ms: int
    text: str
    words: List[NormalizedWord]
    style_name: str
    is_modified: bool

    model_config = ConfigDict(from_attributes=True)


class SubtitleTrackResponse(BaseModel):
    """Serialized subtitle track header with nested events."""
    id: str
    clip_id: str
    transcript_id: Optional[str] = None
    preset_name: str
    is_enabled: bool
    is_active: bool
    language: str
    ass_file_path: Optional[str] = None
    compile_status: str
    custom_style_overrides: Optional[Dict[str, Any]] = None
    event_count: int
    events: Optional[List[SubtitleEventResponse]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
