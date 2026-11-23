from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class AudioStreamInfo(BaseModel):
    """Detailed stream parameters for an individual audio stream in a media container."""
    model_config = ConfigDict(from_attributes=True)

    index: int
    codec_name: str
    channels: int
    sample_rate: int
    channel_layout: Optional[str] = None
    bit_rate: Optional[int] = None
    language: Optional[str] = None
    title: Optional[str] = None
    is_default: bool = False


class AudioExtractionRequest(BaseModel):
    """Request payload for triggering audio extraction and preprocessing."""
    stream_index: Optional[int] = None
    force_reextract: bool = False


class AudioAssetResponse(BaseModel):
    """Schema for validated transcription-ready 16kHz mono PCM WAV audio asset."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_id: str
    job_id: Optional[str] = None
    filename: str
    format: str = "wav"
    codec: str = "pcm_s16le"
    sample_rate: int = 16000
    channels: int = 1
    channel_layout: str = "mono"
    bit_depth: int = 16
    duration_seconds: float
    file_size_bytes: int
    source_stream_index: int = 0
    status: str
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AudioExtractionJobResponse(BaseModel):
    """Response payload when an audio extraction job is queued or processed."""
    job_id: str
    video_id: str
    status: str
    progress_percent: float = 0.0
    current_step: str = "Queued"
    audio_asset: Optional[AudioAssetResponse] = None
