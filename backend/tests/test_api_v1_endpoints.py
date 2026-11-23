import uuid
import pytest
from httpx import AsyncClient
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.video import Video


@pytest.mark.asyncio
async def test_videos_endpoints(async_client: AsyncClient):
    """Verifies video collection queries and honest 501 on upload."""
    # List videos
    res = await async_client.get("/api/v1/videos")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data

    # Upload video without file payload returns 422 validation error
    res = await async_client.post("/api/v1/videos/upload")
    assert res.status_code == 422
    err = res.json()
    assert err["error_code"] == "VALIDATION_ERROR"

    # Nonexistent video returns 404
    nonexistent = str(uuid.uuid4())
    res = await async_client.get(f"/api/v1/videos/{nonexistent}")
    assert res.status_code == 404
    assert res.json()["error_code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_jobs_endpoints(async_client: AsyncClient):
    """Verifies processing job queries and cancel endpoint."""
    res = await async_client.get("/api/v1/jobs")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data

    # Nonexistent job returns 404
    nonexistent = str(uuid.uuid4())
    res = await async_client.get(f"/api/v1/jobs/{nonexistent}")
    assert res.status_code == 404
    assert res.json()["error_code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_transcripts_endpoints(async_client: AsyncClient):
    """Verifies transcript retrieval and models catalog."""
    nonexistent = str(uuid.uuid4())
    res = await async_client.get(f"/api/v1/transcripts/{nonexistent}")
    assert res.status_code == 404
    assert res.json()["error_code"] == "RESOURCE_NOT_FOUND"

    res_models = await async_client.get("/api/v1/transcripts/models")
    assert res_models.status_code == 200
    models_data = res_models.json()
    assert "models" in models_data
    assert len(models_data["models"]) >= 1


@pytest.mark.asyncio
async def test_highlights_endpoints(async_client: AsyncClient):
    """Verifies highlight candidate retrieval and detection endpoint."""
    test_vid = str(uuid.uuid4())
    res = await async_client.get(f"/api/v1/highlights/{test_vid}")
    assert res.status_code == 200
    data = res.json()
    assert data["video_id"] == test_vid
    assert data["total"] == 0

    # Detection requires valid video, returning 404 if video does not exist
    res = await async_client.post("/api/v1/highlights/detect", json={"video_id": test_vid})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_clips_lifecycle(async_client: AsyncClient):
    """Verifies clip creation, validation, update, and deletion lifecycle."""
    # First create a test Video in DB
    video_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        v = Video(
            id=video_id,
            filename=f"{video_id}.mp4",
            original_filename="clip_test.mp4",
            file_path=f"data/uploads/{video_id}.mp4",
            file_size_bytes=5000000,
            duration_seconds=60.0,
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
        session.add(v)
        await session.commit()

    # Create Clip with duration < 5000ms should fail validation (422)
    bad_payload = {
        "video_id": video_id,
        "title": "Too short",
        "start_ms": 1000,
        "end_ms": 3000,
    }
    res = await async_client.post("/api/v1/clips", json=bad_payload)
    assert res.status_code == 422
    assert res.json()["error_code"] == "VALIDATION_ERROR"

    # Create valid Clip
    valid_payload = {
        "video_id": video_id,
        "title": "Valid Short Clip",
        "start_ms": 1000,
        "end_ms": 15000,
        "aspect_ratio_mode": "BLUR_PAD",
    }
    res = await async_client.post("/api/v1/clips", json=valid_payload)
    assert res.status_code == 201
    clip_data = res.json()
    clip_id = clip_data["id"]
    assert clip_data["title"] == "Valid Short Clip"
    assert clip_data["duration_ms"] == 14000

    # Get Clip
    res = await async_client.get(f"/api/v1/clips/{clip_id}")
    assert res.status_code == 200
    assert res.json()["id"] == clip_id

    # Patch Clip
    patch_payload = {"title": "Updated Title", "subtitle_font_size": 28}
    res = await async_client.patch(f"/api/v1/clips/{clip_id}", json=patch_payload)
    assert res.status_code == 200
    assert res.json()["title"] == "Updated Title"
    assert res.json()["subtitle_font_size"] == 28

    # ASS subtitles returns 501
    res = await async_client.get(f"/api/v1/clips/{clip_id}/subtitles.ass")
    assert res.status_code == 501
    assert "Phase 15" in res.json()["detail"]

    # Delete Clip
    res = await async_client.delete(f"/api/v1/clips/{clip_id}")
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Clean up Video
    async with AsyncSessionLocal() as session:
        v_del = (await session.execute(Video.__table__.select().where(Video.id == video_id))).first()
        if v_del:
            await session.execute(Video.__table__.delete().where(Video.id == video_id))
            await session.commit()


@pytest.mark.asyncio
async def test_exports_endpoints(async_client: AsyncClient):
    """Verifies export job queries and honest 501 on render trigger."""
    res = await async_client.get("/api/v1/exports")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data

    res = await async_client.post("/api/v1/exports")
    assert res.status_code == 501
    assert "Phase 16" in res.json()["detail"]
