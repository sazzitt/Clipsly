from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class WordTimestampSchema(BaseModel):
    """Word-level timestamp with token confidence probability."""
    model_config = ConfigDict(from_attributes=True)

    word: str
    start_ms: int
    end_ms: int
    probability: Optional[float] = None


class TranscriptSegmentResponse(BaseModel):
    """Sentence-level segment with start/end timing in milliseconds and word timing array."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    transcript_id: str
    segment_index: int
    start_ms: int
    end_ms: int
    text: str
    words: List[WordTimestampSchema] = Field(default_factory=list)
    avg_confidence: float = 1.0
    no_speech_prob: Optional[float] = None
    speaker_id: Optional[str] = None
    created_at: Optional[str] = None


class TranscriptSegmentListResponse(BaseModel):
    """Paginated list of transcript segments."""
    transcript_id: str
    total: int
    offset: int = 0
    limit: int = 100
    segments: List[TranscriptSegmentResponse]


class TranscriptResponse(BaseModel):
    """Header record for a speech-to-text transcription run with full technical metadata."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_id: str
    audio_asset_id: Optional[str] = None
    model_name: str
    compute_type: str
    device: str
    language: str
    language_probability: Optional[float] = None
    status: str
    full_text: str
    word_count: int
    segment_count: int
    audio_duration_seconds: Optional[float] = None
    processing_time_seconds: float = 0.0
    error_message: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    segments: Optional[List[TranscriptSegmentResponse]] = None


class TranscriptionRequest(BaseModel):
    """Parameters for triggering or re-running speech transcription."""
    model_name: Optional[str] = Field(
        None,
        description="Whisper model size ('tiny', 'base', 'small'). Defaults to 'base'."
    )
    device: Optional[str] = Field(
        None,
        description="Compute device ('cuda' or 'cpu'). Defaults to 'cuda' with automatic fallback."
    )
    compute_type: Optional[str] = Field(
        None,
        description="Quantization / compute type ('float16', 'int8_float16', 'int8')."
    )
    language: Optional[str] = Field(
        None,
        description="Language code (e.g. 'en', 'es', 'fr') or None for automatic language detection."
    )
    vad_filter: Optional[bool] = Field(
        None,
        description="Whether to apply Silero VAD speech filtering. Defaults to True."
    )
    word_timestamps: Optional[bool] = Field(
        None,
        description="Whether to extract word-level timestamps. Defaults to True."
    )
    force_retranscribe: bool = Field(
        False,
        description="If True, forces new transcription run even if active transcript already exists."
    )


class TranscriptionVideoRequest(TranscriptionRequest):
    """Parameters for triggering transcription with an explicit video ID."""
    video_id: str = Field(..., description="ID of the video to transcribe")


class TranscriptionJobResponse(BaseModel):
    """Response payload when a transcription job is queued or finished."""
    job_id: str
    video_id: str
    status: str
    progress_percent: float = 0.0
    current_step: str = "Queued"
    transcript: Optional[TranscriptResponse] = None


class SegmentUpdateRequest(BaseModel):
    """Payload for editing a single segment's text."""
    text: str = Field(..., min_length=1, description="Corrected transcript text")


class ModelOptionInfo(BaseModel):
    """Specifications for available Faster-Whisper model sizes."""
    model_name: str
    description: str
    parameters: str
    vram_required_mb: int
    recommended_for: str
    devices_supported: List[str]


class AvailableModelsResponse(BaseModel):
    """Catalog of available Whisper model options and detected hardware environment."""
    models: List[ModelOptionInfo]
    default_model: str
    cuda_available: bool
    detected_gpu: Optional[str] = None
    cuda_compute_types: List[str] = Field(default_factory=list)
    cpu_compute_types: List[str] = Field(default_factory=list)
