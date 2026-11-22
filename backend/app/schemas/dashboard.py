from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.schemas.system import SystemHardwareTelemetry, SystemHealthResponse


class DashboardCounts(BaseModel):
    """Aggregate entity counts across the application (docs/05-API.md section 4.6)."""
    total_videos: int = Field(0, description="Total ingested source videos in database")
    total_clips: int = Field(0, description="Total generated short clips in database")
    active_jobs: int = Field(0, description="Jobs currently in QUEUED or PROCESSING status")
    completed_exports: int = Field(0, description="Total successfully rendered MP4 export jobs")
    total_transcripts: int = Field(0, description="Total video transcripts in database")
    total_highlights: int = Field(0, description="Total candidate highlights in database")


class DashboardStorageSummary(BaseModel):
    """Local workstation storage capacity diagnostics (docs/05-API.md section 4.6)."""
    ssd_free_gb: float = Field(..., description="Available SSD space on storage volume in GB")
    ssd_total_gb: float = Field(..., description="Total SSD storage volume capacity in GB")
    clipsly_storage_bytes: int = Field(0, description="Total storage consumed by Clipsly ingested videos")
    storage_path: str = Field(..., description="Filesystem directory for Clipsly storage")
    is_critical: bool = Field(False, description="True when available SSD headroom is below 10GB safeguard")


class DashboardRecentVideoItem(BaseModel):
    """Summary of a recently ingested video for dashboard display."""
    id: str
    filename: str
    original_filename: str
    file_size_bytes: int
    duration_seconds: float
    width: int
    height: int
    fps: float
    status: str
    created_at: Optional[str] = None


class DashboardRecentJobItem(BaseModel):
    """Summary of a recently queued or executing background task for dashboard display."""
    id: str
    video_id: str
    job_type: str
    status: str
    progress_percent: float
    current_step: str
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DashboardSummaryResponse(BaseModel):
    """Consolidated workstation summary payload (docs/05-API.md section 4.6)."""
    counts: DashboardCounts
    storage: DashboardStorageSummary
    hardware: SystemHardwareTelemetry
    system: SystemHealthResponse
    recent_videos: List[DashboardRecentVideoItem] = Field(default_factory=list)
    recent_jobs: List[DashboardRecentJobItem] = Field(default_factory=list)
