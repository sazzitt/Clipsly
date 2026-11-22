from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class SystemHealthResponse(BaseModel):
    """System health check payload (docs/05-API.md section 4.1)."""
    status: str = Field(..., description="Overall health status: 'healthy', 'degraded', or 'unhealthy'")
    version: str = Field(..., description="Application version")
    database_connected: bool = Field(..., description="Whether SQLite database connection is operational")
    cuda_available: bool = Field(..., description="Whether NVIDIA CUDA is available on this machine")
    nvenc_available: bool = Field(..., description="Whether FFmpeg h264_nvenc hardware acceleration is available")
    active_jobs_count: int = Field(0, description="Number of currently executing background jobs")
    uptime_seconds: float = Field(..., description="Total backend uptime in seconds")


class SystemInfoResponse(BaseModel):
    """Host system and runtime environment specifications (docs/05-API.md section 4.2)."""
    os: str = Field(..., description="Operating system name and build")
    cpu: str = Field(..., description="Processor name and logical thread count")
    gpu: str = Field(..., description="Graphics processor name")
    vram_total_mb: Optional[int] = Field(None, description="Total physical VRAM in megabytes")
    python_version: str = Field(..., description="Active Python interpreter version")
    ffmpeg_version: str = Field(..., description="Detected FFmpeg binary build version")


class SystemHardwareTelemetry(BaseModel):
    """Real-time hardware telemetry for resource monitoring (docs/05-API.md section 4.3)."""
    gpu_vram_used_mb: Optional[int] = Field(None, description="Used VRAM in MB")
    gpu_vram_total_mb: Optional[int] = Field(None, description="Total VRAM in MB")
    gpu_vram_free_mb: Optional[int] = Field(None, description="Free VRAM in MB")
    gpu_utilization_percent: Optional[float] = Field(None, description="GPU compute utilization %")
    cpu_load_percent: Optional[float] = Field(None, description="System CPU load %")
    system_ram_used_gb: Optional[float] = Field(None, description="System RAM used in GB")
    system_ram_total_gb: Optional[float] = Field(None, description="System RAM total in GB")
    ssd_free_space_gb: float = Field(..., description="Free SSD storage space on storage partition in GB")


class SettingsListResponse(BaseModel):
    """Key-value list of application settings (docs/05-API.md section 4.4)."""
    settings: Dict[str, Any] = Field(..., description="Key-value dictionary of settings")


class SettingUpdateRequest(BaseModel):
    """Request payload to update an application setting (docs/05-API.md section 4.5)."""
    key: str = Field(..., description="Setting key identifier")
    value: str = Field(..., description="Setting value as string or serialized JSON")
    category: Optional[str] = Field("GENERAL", description="Settings category")
    description: Optional[str] = Field(None, description="Human description")
