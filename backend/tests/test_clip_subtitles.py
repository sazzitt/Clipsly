import uuid
import pytest
from httpx import AsyncClient

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.clip import Clip
from backend.app.models.video import Video


@pytest.mark.asyncio
async def test_subtitles_endpoint_returns_501_with_phase18_reference(async_client: AsyncClient):
    """Verifies that GET /clips/{clip_id}/subtitles.ass returns 501 Not Implemented,
    explicitly references Phase 18, and does not mention Phase 15.
    """
    dummy_clip_id = str(uuid.uuid4())
    res = await async_client.get(f"/api/v1/clips/{dummy_clip_id}/subtitles.ass")

    assert res.status_code == 501

    payload = res.json()

    # Standardized error envelope structure
    assert "error_code" in payload
    assert payload["error_code"] == "NOT_IMPLEMENTED"
    assert "detail" in payload
    assert "error" in payload
    assert payload["error"]["code"] == "NOT_IMPLEMENTED"
    assert payload["error"]["message"] == payload["detail"]

    # Verify Phase references
    detail = payload["detail"]
    assert "Phase 18" in detail
    assert "Subtitle & Caption Engine" in detail
    assert "Phase 17" in detail
    assert "Phase 15" not in detail


@pytest.mark.asyncio
async def test_subtitles_endpoint_with_persisted_clip_record(async_client: AsyncClient):
    """Verifies that a valid, persisted Clip record also consistently returns 501
    with the exact Phase 18 notification without breaking existing error contracts.
    """
    video_id = str(uuid.uuid4())
    clip_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        video = Video(
            id=video_id,
            filename=f"{video_id}.mp4",
            original_filename="subtitle_test_vid.mp4",
            file_path=f"storage/uploads/{video_id}.mp4",
            file_size_bytes=1024,
            duration_seconds=60.0,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            status="READY",
        )
        session.add(video)
        await session.commit()

        clip = Clip(
            id=clip_id,
            video_id=video_id,
            title="Subtitle Phase Check Clip",
            start_ms=0,
            end_ms=6000,
            duration_ms=6000,
            aspect_ratio_mode="BLUR_PAD",
            conversion_mode="BLUR_PAD",
            status="DRAFT",
        )
        session.add(clip)
        await session.commit()

    try:
        res = await async_client.get(f"/api/v1/clips/{clip_id}/subtitles.ass")
        assert res.status_code == 501

        data = res.json()
        assert data["error_code"] == "NOT_IMPLEMENTED"
        assert "Phase 18" in data["detail"]
        assert "Phase 15" not in data["detail"]
        assert "Phase 17" in data["detail"]
    finally:
        # Clean up database records
        async with AsyncSessionLocal() as session:
            c = await session.get(Clip, clip_id)
            if c:
                await session.delete(c)
            v = await session.get(Video, video_id)
            if v:
                await session.delete(v)
            await session.commit()
