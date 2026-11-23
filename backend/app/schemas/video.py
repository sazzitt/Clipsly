from typing import Optional
from pydantic import BaseModel, ConfigDict


class VideoUploadResponse(BaseModel):
    """Schema for video upload completion response matching docs/05-API.md Section 5.1.
    Internal filesystem paths are strictly withheld to preserve host filesystem privacy.
    """
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
    audio_codec: Optional[str] = None
    audio_sample_rate: Optional[int] = None
    audio_channels: Optional[int] = None
    status: str
    created_at: str
    storage_label: str = "Local SSD Storage"


class VideoDetailResponse(BaseModel):
    """Schema for comprehensive video stream characteristics, metadata, and entity counts."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    original_filename: str
    storage_label: str = "Local SSD Storage"
    file_size_bytes: int
    duration_seconds: float
    width: int
    height: int
    aspect_ratio: str
    fps: float
    video_codec: str
    video_codec_profile: Optional[str] = None
    pixel_format: Optional[str] = None
    bit_depth: Optional[int] = None
    video_bitrate: Optional[int] = None
    rotation: int = 0
    orientation: str = "landscape"
    has_audio: bool = True
    audio_codec: Optional[str] = None
    audio_sample_rate: Optional[int] = None
    audio_channels: Optional[int] = None
    channel_layout: Optional[str] = None
    audio_bitrate: Optional[int] = None
    container_format: Optional[str] = None
    bitrate: Optional[int] = None
    status: str
    metadata_status: str = "COMPLETED"
    metadata_extracted_at: Optional[str] = None
    error_message: Optional[str] = None
    file_exists: bool = True
    processing_jobs_count: int = 0
    clips_count: int = 0
    transcripts_count: int = 0
    highlights_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


