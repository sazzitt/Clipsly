from typing import Optional
from pydantic import BaseModel, ConfigDict


class VideoUploadResponse(BaseModel):
    """Schema for video upload completion response matching docs/05-API.md Section 5.1."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    original_filename: str
    file_size_bytes: int
    duration_seconds: float
    width: int
    height: int
    aspect_ratio: str
    fps: float
    video_codec: str
    audio_codec: str
    audio_sample_rate: int
    audio_channels: int
    status: str
    created_at: str
    file_path: Optional[str] = None
