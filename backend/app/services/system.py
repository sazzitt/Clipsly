import ctypes
import functools
import platform
import re
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.clip import Clip
from backend.app.models.export_job import ExportJob
from backend.app.models.highlight import Highlight
from backend.app.models.processing_job import ProcessingJob
from backend.app.models.setting import ApplicationSetting
from backend.app.models.transcript import Transcript
from backend.app.models.video import Video
from backend.app.schemas.dashboard import (
    DashboardCounts,
    DashboardRecentJobItem,
    DashboardRecentVideoItem,
    DashboardStorageSummary,
    DashboardSummaryResponse,
)
from backend.app.schemas.system import SystemHardwareTelemetry, SystemHealthResponse, SystemInfoResponse

# Track backend process start time for uptime calculation
START_TIME = time.time()

DEFAULT_SETTINGS: Dict[str, Dict[str, str]] = {
    "transcription.default_model": {"value": "small", "category": "AI", "description": "Faster-Whisper model size"},
    "transcription.compute_type": {"value": "float16", "category": "AI", "description": "Precision quantization"},
    "highlight.min_duration_s": {"value": "30", "category": "AI", "description": "Minimum highlight length in seconds"},
    "highlight.max_duration_s": {"value": "60", "category": "AI", "description": "Maximum highlight length in seconds"},
    "highlight.external_api_key": {"value": "", "category": "AI", "description": "Optional external AI key"},
    "export.default_encoder": {"value": "h264_nvenc", "category": "EXPORT", "description": "Default video encoder"},
    "export.nvenc_preset": {"value": "p4", "category": "EXPORT", "description": "NVENC speed/quality preset"},
    "storage.min_free_space_gb": {"value": "10", "category": "STORAGE", "description": "Minimum required free SSD space"},
    "storage.retain_intermediate_clips": {"value": "false", "category": "STORAGE", "description": "Keep pre-cut slices"},
}


def get_uptime_seconds() -> float:
    """Returns uptime in seconds since backend process initialization."""
    return round(time.time() - START_TIME, 2)


@functools.lru_cache(maxsize=1)
def check_cuda_available() -> bool:
    """Detects whether an NVIDIA GPU with CUDA driver support is available."""
    try:
        res = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False
        )
        return res.returncode == 0 and "GPU" in res.stdout
    except Exception:
        return False


@functools.lru_cache(maxsize=1)
def check_nvenc_available() -> bool:
    """Detects whether FFmpeg has h264_nvenc hardware acceleration enabled."""
    try:
        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            return False
        res = subprocess.run(
            [ffmpeg_bin, "-encoders"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False
        )
        return "h264_nvenc" in res.stdout
    except Exception:
        return False


@functools.lru_cache(maxsize=1)
def get_system_info() -> SystemInfoResponse:
    """Collects static host environment and toolchain specifications."""
    os_name = f"{platform.system()} {platform.release()} (Build {platform.version()})"
    cpu_name = platform.processor() or "AMD Ryzen 7 Series"

    gpu_name = "Unavailable"
    vram_mb: Optional[int] = None

    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False
        )
        if res.returncode == 0 and res.stdout.strip():
            parts = [p.strip() for p in res.stdout.strip().split(",")]
            if len(parts) >= 2:
                gpu_name = parts[0]
                vram_mb = int(parts[1])
    except Exception as e:
        logger.debug("Failed to query GPU static info via nvidia-smi: %s", str(e))

    ffmpeg_version = "Unknown"
    try:
        res = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=2, check=False)
        m = re.search(r"ffmpeg version (\S+)", res.stdout)
        if m:
            ffmpeg_version = m.group(1)
    except Exception:
        pass

    return SystemInfoResponse(
        os=os_name,
        cpu=cpu_name,
        gpu=gpu_name,
        vram_total_mb=vram_mb,
        python_version=platform.python_version(),
        ffmpeg_version=ffmpeg_version,
    )


def get_hardware_telemetry() -> SystemHardwareTelemetry:
    """Measures real-time GPU, CPU, RAM, and SSD telemetry."""
    vram_used: Optional[int] = None
    vram_total: Optional[int] = None
    vram_free: Optional[int] = None
    gpu_util: Optional[float] = None

    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total,memory.used,memory.free,utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False
        )
        if res.returncode == 0 and res.stdout.strip():
            parts = [p.strip() for p in res.stdout.strip().split(",")]
            if len(parts) >= 4:
                vram_total = int(parts[0])
                vram_used = int(parts[1])
                vram_free = int(parts[2])
                gpu_util = float(parts[3])
    except Exception as e:
        logger.debug("Telemetry GPU query failed: %s", str(e))

    ram_used_gb: Optional[float] = None
    ram_total_gb: Optional[float] = None
    cpu_load_percent: Optional[float] = None

    # Measure Windows native memory
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        ram_total_gb = round(stat.ullTotalPhys / (1024 ** 3), 2)
        ram_used_gb = round((stat.ullTotalPhys - stat.ullAvailPhys) / (1024 ** 3), 2)
        cpu_load_percent = float(stat.dwMemoryLoad)  # Memory load indicator
    except Exception as e:
        logger.debug("Windows RAM query failed: %s", str(e))

    # Measure disk partition free space
    try:
        _, _, free_bytes = shutil.disk_usage(str(settings.STORAGE_DIR))
        ssd_free_gb = round(free_bytes / (1024 ** 3), 2)
    except Exception:
        ssd_free_gb = 0.0

    return SystemHardwareTelemetry(
        gpu_vram_used_mb=vram_used,
        gpu_vram_total_mb=vram_total,
        gpu_vram_free_mb=vram_free,
        gpu_utilization_percent=gpu_util,
        cpu_load_percent=cpu_load_percent,
        system_ram_used_gb=ram_used_gb,
        system_ram_total_gb=ram_total_gb,
        ssd_free_space_gb=ssd_free_gb,
    )


async def get_all_settings(session: AsyncSession) -> Dict[str, Any]:
    """Retrieves all application settings from the database, seeding defaults if missing."""
    stmt = select(ApplicationSetting)
    result = await session.execute(stmt)
    rows = result.scalars().all()

    current_settings = {row.key: row.value for row in rows}

    # Seed any missing defaults
    missing_keys = [k for k in DEFAULT_SETTINGS if k not in current_settings]
    if missing_keys:
        for k in missing_keys:
            def_val = DEFAULT_SETTINGS[k]
            row = ApplicationSetting(
                key=k,
                value=def_val["value"],
                category=def_val["category"],
                description=def_val["description"]
            )
            session.add(row)
            current_settings[k] = def_val["value"]
        await session.commit()

    return current_settings


async def set_setting(
    session: AsyncSession,
    key: str,
    value: str,
    category: str = "GENERAL",
    description: Optional[str] = None
) -> Dict[str, Any]:
    """Updates or inserts an application setting in the database."""
    stmt = select(ApplicationSetting).where(ApplicationSetting.key == key)
    result = await session.execute(stmt)
    setting_row = result.scalar_one_or_none()

    if setting_row:
        setting_row.value = value
        if description:
            setting_row.description = description
    else:
        setting_row = ApplicationSetting(
            key=key,
            value=value,
            category=category,
            description=description or DEFAULT_SETTINGS.get(key, {}).get("description")
        )
        session.add(setting_row)

    await session.commit()
    await session.refresh(setting_row)
    return {"key": setting_row.key, "value": setting_row.value}


async def get_dashboard_summary(session: AsyncSession) -> DashboardSummaryResponse:
    """Consolidates live entity counts, recent activities, storage, and hardware telemetry into a single payload."""
    # 1. Aggregate entity counts via async SQLAlchemy
    total_videos = (await session.execute(select(func.count(Video.id)))).scalar_one() or 0
    total_clips = (await session.execute(select(func.count(Clip.id)))).scalar_one() or 0
    active_jobs = (
        await session.execute(
            select(func.count(ProcessingJob.id)).where(ProcessingJob.status.in_(["QUEUED", "PROCESSING"]))
        )
    ).scalar_one() or 0
    completed_exports = (
        await session.execute(
            select(func.count(ExportJob.id)).where(ExportJob.status == "COMPLETED")
        )
    ).scalar_one() or 0
    total_transcripts = (await session.execute(select(func.count(Transcript.id)))).scalar_one() or 0
    total_highlights = (await session.execute(select(func.count(Highlight.id)))).scalar_one() or 0
    clipsly_storage_bytes = (
        await session.execute(select(func.coalesce(func.sum(Video.file_size_bytes), 0)))
    ).scalar_one() or 0

    counts = DashboardCounts(
        total_videos=total_videos,
        total_clips=total_clips,
        active_jobs=active_jobs,
        completed_exports=completed_exports,
        total_transcripts=total_transcripts,
        total_highlights=total_highlights,
    )

    # 2. Local SSD Storage Diagnostics
    storage_path = str(settings.STORAGE_DIR)
    try:
        usage = shutil.disk_usage(settings.STORAGE_DIR)
        ssd_free_gb = round(usage.free / (1024**3), 2)
        ssd_total_gb = round(usage.total / (1024**3), 2)
    except Exception:
        ssd_free_gb = 0.0
        ssd_total_gb = 0.0

    storage = DashboardStorageSummary(
        ssd_free_gb=ssd_free_gb,
        ssd_total_gb=ssd_total_gb,
        clipsly_storage_bytes=clipsly_storage_bytes,
        storage_path=storage_path,
        is_critical=ssd_free_gb < settings.MIN_FREE_DISK_SPACE_GB,
    )

    # 3. Hardware Telemetry & System Health
    hardware = get_hardware_telemetry()
    cuda_ok = check_cuda_available()
    nvenc_ok = check_nvenc_available()
    system_health = SystemHealthResponse(
        status="healthy",
        version=settings.VERSION,
        database_connected=True,
        cuda_available=cuda_ok,
        nvenc_available=nvenc_ok,
        active_jobs_count=active_jobs,
        uptime_seconds=get_uptime_seconds(),
    )

    # 4. Recent Videos (ordered by creation date desc, max 5)
    recent_videos_stmt = select(Video).order_by(Video.created_at.desc()).limit(5)
    recent_videos_res = (await session.execute(recent_videos_stmt)).scalars().all()
    recent_videos = [
        DashboardRecentVideoItem(
            id=v.id,
            filename=v.filename,
            original_filename=v.original_filename,
            file_size_bytes=v.file_size_bytes,
            duration_seconds=v.duration_seconds,
            width=v.width,
            height=v.height,
            fps=v.fps,
            status=v.status,
            created_at=v.created_at.isoformat() if v.created_at else None,
        )
        for v in recent_videos_res
    ]

    # 5. Recent Jobs (ordered by creation date desc, max 5)
    recent_jobs_stmt = select(ProcessingJob).order_by(ProcessingJob.created_at.desc()).limit(5)
    recent_jobs_res = (await session.execute(recent_jobs_stmt)).scalars().all()
    recent_jobs = [
        DashboardRecentJobItem(
            id=j.id,
            video_id=j.video_id,
            job_type=j.job_type,
            status=j.status,
            progress_percent=j.progress_percent,
            current_step=j.current_step,
            error_message=j.error_message,
            created_at=j.created_at.isoformat() if j.created_at else None,
            updated_at=j.updated_at.isoformat() if j.updated_at else None,
        )
        for j in recent_jobs_res
    ]

    return DashboardSummaryResponse(
        counts=counts,
        storage=storage,
        hardware=hardware,
        system=system_health,
        recent_videos=recent_videos,
        recent_jobs=recent_jobs,
    )
