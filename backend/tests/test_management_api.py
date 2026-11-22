import uuid
import pytest
from httpx import AsyncClient
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.clip import Clip
from backend.app.models.export_job import ExportJob
from backend.app.models.processing_job import ProcessingJob
from backend.app.models.video import Video


@pytest.mark.asyncio
async def test_video_filtering_and_search(async_client: AsyncClient):
    """Verifies searching, status filtering, sorting, and pagination on /api/v1/videos."""
    unique_tag = f"SearchTag_{uuid.uuid4().hex[:8]}"
    vid1_id = str(uuid.uuid4())
    vid2_id = str(uuid.uuid4())
    vid3_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        v1 = Video(
            id=vid1_id,
            filename=f"{vid1_id}.mp4",
            original_filename=f"Alpha_{unique_tag}.mp4",
            file_path=f"data/uploads/{vid1_id}.mp4",
            file_size_bytes=10000000,
            duration_seconds=120.0,
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
        v2 = Video(
            id=vid2_id,
            filename=f"{vid2_id}.mp4",
            original_filename=f"Beta_Interview_{unique_tag}.mp4",
            file_path=f"data/uploads/{vid2_id}.mp4",
            file_size_bytes=5000000,
            duration_seconds=60.0,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            fps=60.0,
            video_codec="h264",
            audio_codec="aac",
            audio_sample_rate=48000,
            audio_channels=2,
            status="PROCESSING",
        )
        v3 = Video(
            id=vid3_id,
            filename=f"{vid3_id}.mp4",
            original_filename=f"Gamma_Stream_{unique_tag}.mp4",
            file_path=f"data/uploads/{vid3_id}.mp4",
            file_size_bytes=25000000,
            duration_seconds=300.0,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            fps=60.0,
            video_codec="h264",
            audio_codec="aac",
            audio_sample_rate=48000,
            audio_channels=2,
            status="FAILED",
        )
        session.add_all([v1, v2, v3])
        await session.commit()

    try:
        # Search by unique keyword
        res = await async_client.get(f"/api/v1/videos?search=Alpha_{unique_tag}")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == vid1_id

        # Filter by status
        res = await async_client.get("/api/v1/videos?status=PROCESSING")
        assert res.status_code == 200
        data = res.json()
        assert any(item["id"] == vid2_id for item in data["items"])
        assert not any(item["id"] == vid1_id for item in data["items"])

        # Sort by duration ascending
        res = await async_client.get("/api/v1/videos?sort_by=duration_seconds&order=asc&limit=10")
        assert res.status_code == 200
        items = res.json()["items"]
        durations = [item["duration_seconds"] for item in items]
        assert durations == sorted(durations)

        # Sort by filename descending
        res = await async_client.get("/api/v1/videos?sort_by=filename&order=desc")
        assert res.status_code == 200
    finally:
        async with AsyncSessionLocal() as session:
            for v_id in [vid1_id, vid2_id, vid3_id]:
                v_obj = await session.get(Video, v_id)
                if v_obj:
                    await session.delete(v_obj)
            await session.commit()


@pytest.mark.asyncio
async def test_video_details_with_counts(async_client: AsyncClient):
    """Verifies get_video returns accurate counts for jobs and clips."""
    vid_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    clip_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        v = Video(
            id=vid_id,
            filename=f"{vid_id}.mp4",
            original_filename="details_test.mp4",
            file_path=f"data/uploads/{vid_id}.mp4",
            file_size_bytes=8000000,
            duration_seconds=90.0,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            audio_codec="aac",
            audio_sample_rate=44100,
            audio_channels=2,
            status="READY",
        )
        j = ProcessingJob(
            id=job_id,
            video_id=vid_id,
            job_type="WHISPER_TRANSCRIPTION",
            status="COMPLETED",
            progress_percent=100.0,
            current_step="Finished",
        )
        c = Clip(
            id=clip_id,
            video_id=vid_id,
            title="Clip 1",
            start_ms=1000,
            end_ms=10000,
            duration_ms=9000,
            aspect_ratio_mode="BLUR_PAD",
            subtitle_enabled=True,
            subtitle_style_preset="KARAOKE_AMBER",
            subtitle_font_family="Montserrat",
            subtitle_font_size=24,
            subtitle_primary_color="#FFFFFF",
            subtitle_highlight_color="#FFD700",
            subtitle_outline_color="#000000",
            subtitle_outline_width=3,
            subtitle_vertical_position="BOTTOM",
            status="DRAFT",
        )
        session.add_all([v, j, c])
        await session.commit()

    res = await async_client.get(f"/api/v1/videos/{vid_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == vid_id
    assert data["audio_sample_rate"] == 44100
    assert data["processing_jobs_count"] == 1
    assert data["clips_count"] == 1
    assert data["transcripts_count"] == 0
    assert "file_exists" in data


@pytest.mark.asyncio
async def test_video_delete_cascades_children(async_client: AsyncClient):
    """Verifies deleting a video safely cascades child jobs, clips, and exports."""
    vid_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    clip_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        v = Video(
            id=vid_id,
            filename=f"{vid_id}.mp4",
            original_filename="delete_test.mp4",
            file_path=f"data/uploads/{vid_id}.mp4",
            file_size_bytes=5000000,
            duration_seconds=30.0,
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
        j = ProcessingJob(
            id=job_id,
            video_id=vid_id,
            job_type="INGESTION",
            status="COMPLETED",
            progress_percent=100.0,
            current_step="Done",
        )
        c = Clip(
            id=clip_id,
            video_id=vid_id,
            title="Clip for Cascade",
            start_ms=0,
            end_ms=6000,
            duration_ms=6000,
            aspect_ratio_mode="BLUR_PAD",
            subtitle_enabled=True,
            subtitle_style_preset="KARAOKE_AMBER",
            subtitle_font_family="Montserrat",
            subtitle_font_size=24,
            subtitle_primary_color="#FFFFFF",
            subtitle_highlight_color="#FFD700",
            subtitle_outline_color="#000000",
            subtitle_outline_width=3,
            subtitle_vertical_position="BOTTOM",
            status="DRAFT",
        )
        session.add_all([v, j, c])
        await session.commit()

    # Delete video
    del_res = await async_client.delete(f"/api/v1/videos/{vid_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Check video is gone
    get_res = await async_client.get(f"/api/v1/videos/{vid_id}")
    assert get_res.status_code == 404

    # Check child job is gone
    job_res = await async_client.get(f"/api/v1/jobs/{job_id}")
    assert job_res.status_code == 404

    # Check child clip is gone
    clip_res = await async_client.get(f"/api/v1/clips/{clip_id}")
    assert clip_res.status_code == 404


@pytest.mark.asyncio
async def test_jobs_filtering_and_cancel(async_client: AsyncClient):
    """Verifies listing jobs with filters and cancelling an active job."""
    vid_id = str(uuid.uuid4())
    job1_id = str(uuid.uuid4())
    job2_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        v = Video(
            id=vid_id,
            filename=f"{vid_id}.mp4",
            original_filename="jobs_filter.mp4",
            file_path=f"data/uploads/{vid_id}.mp4",
            file_size_bytes=5000000,
            duration_seconds=30.0,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            audio_codec="aac",
            audio_sample_rate=48000,
            audio_channels=2,
            status="PROCESSING",
        )
        j1 = ProcessingJob(
            id=job1_id,
            video_id=vid_id,
            job_type="WHISPER_TRANSCRIPTION",
            status="PROCESSING",
            progress_percent=45.0,
            current_step="Transcribing chunk 2/5",
        )
        j2 = ProcessingJob(
            id=job2_id,
            video_id=vid_id,
            job_type="HIGHLIGHT_SCORING",
            status="COMPLETED",
            progress_percent=100.0,
            current_step="Scores computed",
        )
        session.add_all([v, j1, j2])
        await session.commit()

    # Filter by job type
    res = await async_client.get("/api/v1/jobs?job_type=WHISPER_TRANSCRIPTION")
    assert res.status_code == 200
    assert any(j["id"] == job1_id for j in res.json()["items"])

    # Filter by search
    res = await async_client.get("/api/v1/jobs?search=chunk")
    assert res.status_code == 200
    assert any(j["id"] == job1_id for j in res.json()["items"])

    # Cancel active job
    cancel_res = await async_client.post(f"/api/v1/jobs/{job1_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # Attempting to cancel an already completed job should return 409 Conflict
    conflict_res = await async_client.post(f"/api/v1/jobs/{job2_id}/cancel")
    assert conflict_res.status_code == 409


@pytest.mark.asyncio
async def test_exports_management_and_delete(async_client: AsyncClient):
    """Verifies listing export records with filters and deleting export jobs."""
    vid_id = str(uuid.uuid4())
    clip_id = str(uuid.uuid4())
    export_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        v = Video(
            id=vid_id,
            filename=f"{vid_id}.mp4",
            original_filename="export_manage.mp4",
            file_path=f"data/uploads/{vid_id}.mp4",
            file_size_bytes=5000000,
            duration_seconds=30.0,
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
        c = Clip(
            id=clip_id,
            video_id=vid_id,
            title="Clip for Export",
            start_ms=0,
            end_ms=10000,
            duration_ms=10000,
            aspect_ratio_mode="BLUR_PAD",
            subtitle_enabled=True,
            subtitle_style_preset="KARAOKE_AMBER",
            subtitle_font_family="Montserrat",
            subtitle_font_size=24,
            subtitle_primary_color="#FFFFFF",
            subtitle_highlight_color="#FFD700",
            subtitle_outline_color="#000000",
            subtitle_outline_width=3,
            subtitle_vertical_position="BOTTOM",
            status="READY",
        )
        e = ExportJob(
            id=export_id,
            clip_id=clip_id,
            video_id=vid_id,
            output_filename="Clip_for_Export_9x16.mp4",
            output_path=f"data/exports/{export_id}.mp4",
            resolution="1080x1920",
            fps=30.0,
            encoder="h264_nvenc",
            render_time_seconds=4.2,
            file_size_bytes=3400000,
            status="COMPLETED",
            progress_percent=100.0,
        )
        session.add_all([v, c, e])
        await session.commit()

    # Search exports
    res = await async_client.get("/api/v1/exports?search=Clip_for_Export")
    assert res.status_code == 200
    assert any(item["id"] == export_id for item in res.json()["items"])

    # Get export
    get_res = await async_client.get(f"/api/v1/exports/{export_id}")
    assert get_res.status_code == 200
    assert get_res.json()["clip_title"] == "Clip for Export"

    # Delete export
    del_res = await async_client.delete(f"/api/v1/exports/{export_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Verify deleted
    verify_res = await async_client.get(f"/api/v1/exports/{export_id}")
    assert verify_res.status_code == 404
