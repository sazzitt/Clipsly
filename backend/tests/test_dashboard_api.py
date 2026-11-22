import uuid
import pytest
from httpx import AsyncClient
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.video import Video
from backend.app.models.clip import Clip
from backend.app.models.processing_job import ProcessingJob


@pytest.mark.asyncio
async def test_dashboard_summary_empty_database(async_client: AsyncClient):
    """Verifies that GET /api/v1/system/dashboard returns 200 and valid schema on empty/fresh DB."""
    response = await async_client.get("/api/v1/system/dashboard")
    assert response.status_code == 200
    data = response.json()

    # Counts
    assert "counts" in data
    assert "total_videos" in data["counts"]
    assert "total_clips" in data["counts"]
    assert "active_jobs" in data["counts"]
    assert "completed_exports" in data["counts"]

    # Storage
    assert "storage" in data
    assert "ssd_free_gb" in data["storage"]
    assert "ssd_total_gb" in data["storage"]
    assert data["storage"]["ssd_total_gb"] > 0
    assert "clipsly_storage_bytes" in data["storage"]

    # Hardware
    assert "hardware" in data
    assert "system_ram_total_gb" in data["hardware"]

    # System Health
    assert "system" in data
    assert data["system"]["database_connected"] is True
    assert data["system"]["status"] == "healthy"

    # Recent arrays
    assert "recent_videos" in data
    assert isinstance(data["recent_videos"], list)
    assert "recent_jobs" in data
    assert isinstance(data["recent_jobs"], list)


@pytest.mark.asyncio
async def test_dashboard_summary_with_entities(async_client: AsyncClient):
    """Verifies that entity creation increments dashboard counts and reflects in recent lists."""
    video_id = str(uuid.uuid4())
    clip_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        # Create Video
        video = Video(
            id=video_id,
            filename=f"{video_id}.mp4",
            original_filename="dashboard_test.mp4",
            file_path=f"data/uploads/{video_id}.mp4",
            file_size_bytes=20480000,
            duration_seconds=95.0,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            audio_codec="aac",
            audio_sample_rate=48000,
            audio_channels=2,
            status="READY",
        )
        session.add(video)

        # Create Clip
        clip = Clip(
            id=clip_id,
            video_id=video_id,
            title="Dashboard Test Clip",
            start_ms=1000,
            end_ms=15000,
            duration_ms=14000,
            aspect_ratio_mode="BLUR_PAD",
            status="DRAFT",
        )
        session.add(clip)

        # Create ProcessingJob
        job = ProcessingJob(
            id=job_id,
            video_id=video_id,
            job_type="TRANSCRIPTION",
            status="PROCESSING",
            progress_percent=45.0,
            current_step="Transcribing audio with Whisper...",
        )
        session.add(job)
        await session.commit()

    try:
        response = await async_client.get("/api/v1/system/dashboard")
        assert response.status_code == 200
        data = response.json()

        # Check counts reflect additions
        assert data["counts"]["total_videos"] >= 1
        assert data["counts"]["total_clips"] >= 1
        assert data["counts"]["active_jobs"] >= 1
        assert data["counts"]["completed_exports"] >= 0

        # Check recent videos contains created video
        recent_video_ids = [v["id"] for v in data["recent_videos"]]
        assert video_id in recent_video_ids

        # Check recent jobs contains created job
        recent_job_ids = [j["id"] for j in data["recent_jobs"]]
        assert job_id in recent_job_ids
    finally:
        # Cleanup test records
        async with AsyncSessionLocal() as session:
            v_fetch = (await session.execute(Video.__table__.select().where(Video.id == video_id))).first()
            if v_fetch:
                await session.execute(Video.__table__.delete().where(Video.id == video_id))
                await session.commit()
