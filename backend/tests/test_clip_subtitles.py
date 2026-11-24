import json
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.clip import Clip
from backend.app.models.subtitle_track import SubtitleTrack
from backend.app.models.subtitle_event import SubtitleEvent
from backend.app.models.transcript import Transcript
from backend.app.models.transcript_segment import TranscriptSegment
from backend.app.models.video import Video
from backend.app.services.subtitles.schemas import SubtitleGenerateRequest
from backend.app.services.subtitles.sync_service import create_subtitle_track_for_clip
from backend.app.services.subtitles.ass_storage import delete_ass_file


@pytest.mark.asyncio
async def test_subtitles_endpoint_returns_404_for_unknown_clip(async_client: AsyncClient):
    """Verifies that GET /clips/{clip_id}/subtitles.ass returns 404 Not Found when clip does not exist."""
    dummy_clip_id = str(uuid.uuid4())
    res = await async_client.get(f"/api/v1/clips/{dummy_clip_id}/subtitles.ass")

    assert res.status_code == 404
    payload = res.json()
    assert payload["error_code"] == "RESOURCE_NOT_FOUND"
    assert f"Clip '{dummy_clip_id}' not found" in payload["detail"]


@pytest.mark.asyncio
async def test_subtitles_endpoint_returns_404_when_no_active_track(async_client: AsyncClient):
    """Verifies that a valid Clip without an active subtitle track returns 404 Not Found."""
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
            title="Clip Without Subtitles",
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
        assert res.status_code == 404
        payload = res.json()
        assert payload["error_code"] == "RESOURCE_NOT_FOUND"
        assert "No active subtitle track found" in payload["detail"]
    finally:
        async with AsyncSessionLocal() as session:
            c = await session.get(Clip, clip_id)
            if c:
                await session.delete(c)
            v = await session.get(Video, video_id)
            if v:
                await session.delete(v)
            await session.commit()


@pytest.mark.asyncio
async def test_subtitles_endpoint_returns_200_with_valid_ass_when_track_exists(async_client: AsyncClient):
    """Verifies that GET /clips/{clip_id}/subtitles.ass returns 200 OK with valid ASS document."""
    video_id = str(uuid.uuid4())
    clip_id = str(uuid.uuid4())
    transcript_id = str(uuid.uuid4())
    seg_id = str(uuid.uuid4())

    words_data = [
        {"word": "Transform", "start": 1.0, "end": 1.5, "probability": 0.95},
        {"word": "your", "start": 1.5, "end": 1.8, "probability": 0.98},
        {"word": "videos", "start": 1.8, "end": 2.5, "probability": 0.99},
    ]

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

        transcript = Transcript(
            id=transcript_id,
            video_id=video_id,
            model_name="small",
            compute_type="float16",
            device="cuda",
            language="en",
            status="COMPLETED",
            full_text="Transform your videos",
            word_count=3,
            segment_count=1,
            is_active=True,
        )
        session.add(transcript)

        segment = TranscriptSegment(
            id=seg_id,
            transcript_id=transcript_id,
            segment_index=0,
            start_ms=1000,
            end_ms=3000,
            text="Transform your videos",
            words_json=json.dumps(words_data),
        )
        session.add(segment)

        clip = Clip(
            id=clip_id,
            video_id=video_id,
            title="Active Subtitle Test Clip",
            start_ms=1000,
            end_ms=7000,
            duration_ms=6000,
            aspect_ratio_mode="BLUR_PAD",
            conversion_mode="BLUR_PAD",
            status="DRAFT",
        )
        session.add(clip)
        await session.commit()

        # Generate subtitle track via sync_service
        track = await create_subtitle_track_for_clip(
            session=session,
            clip_id=clip_id,
            request=SubtitleGenerateRequest(
                preset_name="KARAOKE_AMBER",
                max_words_per_line=3,
            ),
        )
        await session.commit()

    try:
        res = await async_client.get(f"/api/v1/clips/{clip_id}/subtitles.ass")
        assert res.status_code == 200
        assert "text/x-ssa" in res.headers["content-type"]
        assert f'filename="{clip_id}.ass"' in res.headers["content-disposition"]

        content = res.text
        assert "[Script Info]" in content
        assert f"Title: Clipsly - Clip {clip_id}" in content
        assert "ScriptType: v4.00+" in content
        assert "PlayResX: 1080" in content
        assert "PlayResY: 1920" in content
        assert "[V4+ Styles]" in content
        assert "Style: Default" in content
        assert "[Events]" in content
        assert "Dialogue: 0," in content
        assert "{\\kf" in content
        assert "Transform" in content
        assert "videos" in content
    finally:
        delete_ass_file(clip_id)
        async with AsyncSessionLocal() as session:
            # Delete events & tracks
            stmt_t = await session.execute(
                select(SubtitleTrack).where(SubtitleTrack.clip_id == clip_id)
            )
            tracks = stmt_t.scalars().all()
            for t in tracks:
                await session.delete(t)
            c = await session.get(Clip, clip_id)
            if c:
                await session.delete(c)
            s = await session.get(TranscriptSegment, seg_id)
            if s:
                await session.delete(s)
            tr = await session.get(Transcript, transcript_id)
            if tr:
                await session.delete(tr)
            v = await session.get(Video, video_id)
            if v:
                await session.delete(v)
            await session.commit()
