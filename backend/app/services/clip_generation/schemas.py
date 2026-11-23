from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ConversionMode(str, Enum):
    BLUR_PAD = "BLUR_PAD"
    CROP_CENTER = "CROP_CENTER"
    FIT_LETTERBOX = "FIT_LETTERBOX"


def normalize_conversion_mode(mode: Optional[str]) -> str:
    """Normalizes various conversion mode aliases to standard canonical enum strings."""
    if not mode:
        return ConversionMode.BLUR_PAD.value
    cleaned = mode.strip().upper()
    if cleaned in ("BLUR_PAD", "BLURRED_BACKGROUND", "BLUR", "BLURRED"):
        return ConversionMode.BLUR_PAD.value
    elif cleaned in ("CROP_CENTER", "CENTER_CROP", "CROP"):
        return ConversionMode.CROP_CENTER.value
    elif cleaned in ("FIT_LETTERBOX", "FIT_WITH_BACKGROUND", "FIT", "LETTERBOX"):
        return ConversionMode.FIT_LETTERBOX.value
    return ConversionMode.BLUR_PAD.value


class ClipGenerationRequest(BaseModel):
    video_id: str = Field(..., description="Source Video UUID")
    highlight_id: Optional[str] = Field(None, description="Optional associated Highlight UUID")
    title: Optional[str] = Field("Untitled Clip", max_length=255, description="Display title for the generated clip")
    start_ms: int = Field(..., ge=0, description="Start timestamp in milliseconds")
    end_ms: int = Field(..., description="End timestamp in milliseconds")
    aspect_ratio_mode: Optional[str] = Field(None, description="Alias for conversion_mode")
    conversion_mode: Optional[str] = Field("BLUR_PAD", description="BLUR_PAD, CROP_CENTER, or FIT_LETTERBOX")
    target_width: int = Field(1080, ge=360, le=3840, description="Target canvas width (default 1080)")
    target_height: int = Field(1920, ge=640, le=3840, description="Target canvas height (default 1920)")
    target_fps: float = Field(30.0, ge=15.0, le=60.0, description="Target video frame rate (default 30.0)")


class ClipGenerationJobResponse(BaseModel):
    job_id: str
    clip_id: str
    video_id: str
    status: str
    message: str


class ClipProbeResult(BaseModel):
    valid: bool
    file_size_bytes: int = 0
    duration_seconds: float = 0.0
    width: int = 0
    height: int = 0
    video_codec: str = ""
    audio_codec: Optional[str] = None
    fps: float = 0.0
    format_name: str = ""
    error_message: Optional[str] = None


class ClipResponse(BaseModel):
    id: str
    video_id: str
    video_filename: Optional[str] = None
    highlight_id: Optional[str] = None
    title: str
    start_ms: int
    end_ms: int
    duration_ms: int
    aspect_ratio_mode: str
    conversion_mode: str
    status: str
    output_path: Optional[str] = None
    output_filename: Optional[str] = None
    width: Optional[int] = 1080
    height: Optional[int] = 1920
    fps: Optional[float] = 30.0
    video_codec: Optional[str] = "h264"
    audio_codec: Optional[str] = None
    file_size_bytes: Optional[int] = None
    encoding_backend: Optional[str] = None
    error_message: Optional[str] = None
    subtitle_enabled: bool = True
    subtitle_style_preset: str = "KARAOKE_AMBER"
    subtitle_font_family: str = "Montserrat"
    subtitle_font_size: int = 24
    subtitle_primary_color: str = "#FFFFFF"
    subtitle_highlight_color: str = "#FFD700"
    subtitle_outline_color: str = "#000000"
    subtitle_outline_width: int = 3
    subtitle_vertical_position: str = "BOTTOM"
    custom_subtitle_text: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
