from pydantic import BaseModel, Field


class SystemHealthResponse(BaseModel):
    """System health check payload."""
    status: str = Field(..., description="Overall health status: 'healthy', 'degraded', or 'unhealthy'")
    version: str = Field(..., description="Application version")
    database_connected: bool = Field(..., description="Whether SQLite database connection is operational")
    cuda_available: bool = Field(..., description="Whether NVIDIA CUDA is available on this machine")
    nvenc_available: bool = Field(..., description="Whether FFmpeg h264_nvenc hardware acceleration is available")
    active_jobs_count: int = Field(0, description="Number of currently executing background jobs")
    uptime_seconds: float = Field(..., description="Total backend uptime in seconds")


class SystemInfoResponse(BaseModel):
    """Host system and runtime environment specifications."""
    os: str
    cpu: str
    gpu: str
    vram_total_mb: int
    python_version: str
    ffmpeg_version: str
