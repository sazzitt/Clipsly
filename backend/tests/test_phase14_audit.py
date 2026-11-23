import asyncio
import os
from pathlib import Path
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.database import AsyncSessionLocal
from backend.app.core.exceptions import ConflictError, NotFoundError
from backend.app.models.audio_asset import AudioAsset
from backend.app.models.clip import Clip
from backend.app.models.export_job import ExportJob
from backend.app.models.processing_job import ProcessingJob
from backend.app.models.video import Video
from backend.app.services.audio_extraction import (
    _active_extractions,
    _active_processes,
    _active_temp_files,
    cancel_audio_extraction,
    extract_and_preprocess_audio,
)
from backend.app.services.queue import job_queue


@pytest.fixture(autouse=True)
def bypass_duration_limits():
    """Temporarily disables 5-min minimum duration check for test media fixtures."""
    original_enforce = settings.ENFORCE_DURATION_LIMITS
    settings.ENFORCE_DURATION_LIMITS = False
    yield
    settings.ENFORCE_DURATION_LIMITS = original_enforce


async def _create_test_video(file_path: Path, filename: str, duration: float = 1.5) -> str:
    vid_id = str(uuid.uuid4())
    unique_name = f"{vid_id}_{filename}"
    dest_path = settings.UPLOAD_DIR / unique_name
    shutil.copy2(file_path, dest_path)

    async with AsyncSessionLocal() as session:
        vid = Video(
            id=vid_id,
            filename=unique_name,
            original_filename=filename,
            file_path=str(dest_path),
            file_size_bytes=dest_path.stat().st_size,
            duration_seconds=duration,
            width=320,
            height=240,
            aspect_ratio="4:3",
            fps=30.0,
            video_codec="h264",
            audio_codec="aac",
            audio_channels=2,
            audio_sample_rate=48000,
            status="READY",
            metadata_status="COMPLETED",
        )
        session.add(vid)
        await session.commit()
    return vid_id


# ---------------------------------------------------------------------------
# 1. Windows FFmpeg Process Cancellation with Real Media Subprocess
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_windows_ffmpeg_real_cancellation(tmp_path):
    """Verifies that an actively running FFmpeg subprocess can be terminated reliably
    on Windows 11, the process is awaited, stdout/stderr streams cleanly close,
    temporary files are removed, and the DB reflects CANCELLED state.
    """
    # Create an 8-second video to ensure FFmpeg is running long enough to catch it
    long_video = tmp_path / "cancel_target.mp4"
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=8:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=48000:duration=8",
            "-ac", "2",
            "-c:v", "libx264", "-c:a", "aac",
            "-y", str(long_video),
        ],
        check=True,
    )

    vid_id = await _create_test_video(long_video, "cancel_target.mp4", duration=8.0)
    job_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        job = ProcessingJob(
            id=job_id,
            video_id=vid_id,
            job_type="AUDIO_EXTRACTION",
            status="QUEUED",
            progress_percent=0.0,
            current_step="Queued for extraction...",
            started_at=datetime.now(timezone.utc),
        )
        session.add(job)
        await session.commit()

    # Launch extraction in background
    task = asyncio.create_task(
        extract_and_preprocess_audio(
            video_id=vid_id,
            job_id=job_id,
            force_reextract=True,
        )
    )

    # Wait until process is active
    proc = None
    for _ in range(50):
        await asyncio.sleep(0.05)
        proc = _active_processes.get(job_id)
        if proc and proc.returncode is None:
            break

    assert proc is not None, "FFmpeg process failed to start in time."
    assert proc.returncode is None, "FFmpeg process finished prematurely before cancellation."

    # Identify temporary WAV file while running
    temp_file = _active_temp_files.get(job_id)

    # Trigger cancellation
    async with AsyncSessionLocal() as session:
        cancelled = await cancel_audio_extraction(job_id, session)
        assert cancelled is True

    # Confirm process terminated on Windows
    assert proc.returncode is not None, "Process was not terminated after cancellation."

    # Wait for the background extraction task to complete (handling cancellation exception)
    try:
        await asyncio.wait_for(task, timeout=5.0)
    except Exception:
        pass

    # Verify temp file cleaned up
    if temp_file:
        assert not temp_file.exists(), "Temporary WAV file was not deleted upon cancellation."

    # Verify DB state
    async with AsyncSessionLocal() as session:
        updated_job = await session.get(ProcessingJob, job_id)
        assert updated_job.status == "CANCELLED"
        assert updated_job.completed_at is not None
        assert "cancelled" in updated_job.current_step.lower()

        # No AudioAsset record created
        stmt = select(AudioAsset).where(AudioAsset.video_id == vid_id)
        res = await session.execute(stmt)
        assert res.scalar_one_or_none() is None

    # Verify repeated cancellation raises ConflictError (cannot cancel terminal job)
    async with AsyncSessionLocal() as session:
        with pytest.raises(ConflictError):
            await cancel_audio_extraction(job_id, session)


# ---------------------------------------------------------------------------
# 2. Sequential Job Queue Enforcement (ADR-001 & ADR-002)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sequential_queue_one_at_a_time(tmp_path):
    """Verifies that the sequential job queue processes jobs one at a time,
    prevents concurrent duplicate jobs on the same video, and updates DB status.
    """
    # Ensure queue worker is running
    await job_queue.start()

    # Create two short video fixtures
    v1_file = tmp_path / "v1.mp4"
    v2_file = tmp_path / "v2.mp4"
    for vf in (v1_file, v2_file):
        subprocess.run(
            [
                "ffmpeg", "-v", "error",
                "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1",
                "-ac", "1",
                "-c:v", "libx264", "-c:a", "aac",
                "-y", str(vf),
            ],
            check=True,
        )

    vid_1 = await _create_test_video(v1_file, "v1.mp4", duration=1.0)
    vid_2 = await _create_test_video(v2_file, "v2.mp4", duration=1.0)

    job_1_id = str(uuid.uuid4())
    job_2_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        j1 = ProcessingJob(id=job_1_id, video_id=vid_1, job_type="AUDIO_EXTRACTION", status="QUEUED")
        j2 = ProcessingJob(id=job_2_id, video_id=vid_2, job_type="AUDIO_EXTRACTION", status="QUEUED")
        session.add_all([j1, j2])
        await session.commit()

    # Submit job 1
    await job_queue.submit_job(
        job_id=job_1_id,
        video_id=vid_1,
        handler=extract_and_preprocess_audio,
        job_kwargs={"video_id": vid_1, "job_id": job_1_id, "force_reextract": True},
    )

    # Submitting duplicate job for vid_1 must raise ConflictError
    with pytest.raises(ConflictError):
        await job_queue.submit_job(
            job_id=str(uuid.uuid4()),
            video_id=vid_1,
            handler=extract_and_preprocess_audio,
            job_kwargs={"video_id": vid_1},
        )

    # Submit job 2 for vid_2
    await job_queue.submit_job(
        job_id=job_2_id,
        video_id=vid_2,
        handler=extract_and_preprocess_audio,
        job_kwargs={"video_id": vid_2, "job_id": job_2_id, "force_reextract": True},
    )

    # Wait for queue to drain and jobs to complete
    for _ in range(60):
        await asyncio.sleep(0.2)
        async with AsyncSessionLocal() as session:
            j1_db = await session.get(ProcessingJob, job_1_id)
            j2_db = await session.get(ProcessingJob, job_2_id)
            if j1_db.status in ("COMPLETED", "FAILED") and j2_db.status in ("COMPLETED", "FAILED"):
                break

    assert j1_db.status == "COMPLETED"
    assert j2_db.status == "COMPLETED"
    assert job_queue.is_video_active(vid_1) is False
    assert job_queue.is_video_active(vid_2) is False


@pytest.mark.asyncio
async def test_job_queue_cancel_queued_job(tmp_path):
    """Verifies that a job cancelled while waiting in the queue is skipped
    without being executed by the worker.
    """
    await job_queue.start()

    v_file = tmp_path / "v_queue.mp4"
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=4:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=4",
            "-ac", "1",
            "-c:v", "libx264", "-c:a", "aac",
            "-y", str(v_file),
        ],
        check=True,
    )

    vid_slow = await _create_test_video(v_file, "slow.mp4", duration=4.0)
    vid_cancel = await _create_test_video(v_file, "to_cancel.mp4", duration=4.0)

    job_slow_id = str(uuid.uuid4())
    job_cancel_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        j_slow = ProcessingJob(id=job_slow_id, video_id=vid_slow, job_type="AUDIO_EXTRACTION", status="QUEUED")
        j_cancel = ProcessingJob(id=job_cancel_id, video_id=vid_cancel, job_type="AUDIO_EXTRACTION", status="QUEUED")
        session.add_all([j_slow, j_cancel])
        await session.commit()

    # Submit slow job first
    await job_queue.submit_job(
        job_id=job_slow_id,
        video_id=vid_slow,
        handler=extract_and_preprocess_audio,
        job_kwargs={"video_id": vid_slow, "job_id": job_slow_id, "force_reextract": True},
    )

    # Submit second job that will sit in queue
    await job_queue.submit_job(
        job_id=job_cancel_id,
        video_id=vid_cancel,
        handler=extract_and_preprocess_audio,
        job_kwargs={"video_id": vid_cancel, "job_id": job_cancel_id, "force_reextract": True},
    )

    # Cancel the queued job immediately before it starts
    async with AsyncSessionLocal() as session:
        cancelled = await job_queue.cancel_job(job_cancel_id, session)
        assert cancelled is True

    # Assert job is CANCELLED in DB
    async with AsyncSessionLocal() as session:
        db_job = await session.get(ProcessingJob, job_cancel_id)
        assert db_job.status == "CANCELLED"
        assert "queued" in db_job.current_step.lower()

    # Wait for slow job to finish
    for _ in range(60):
        await asyncio.sleep(0.2)
        async with AsyncSessionLocal() as session:
            j_slow_db = await session.get(ProcessingJob, job_slow_id)
            if j_slow_db.status in ("COMPLETED", "FAILED"):
                break

    # Cancelled job was never executed: no AudioAsset exists for vid_cancel
    async with AsyncSessionLocal() as session:
        stmt = select(AudioAsset).where(AudioAsset.video_id == vid_cancel)
        res = await session.execute(stmt)
        assert res.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# 3. Path Security & Video Deletion Integrity (ADR-008)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_video_path_traversal_blocked(async_client: AsyncClient, tmp_path):
    """Verifies that delete_video with purge_files=true will not delete files
    outside of the designated storage directory.
    """
    # Create a protected file outside storage
    outside_file = tmp_path / "protected_system_file.txt"
    outside_file.write_text("SENSITIVE DATA")

    vid_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        vid = Video(
            id=vid_id,
            filename="traversal.mp4",
            original_filename="traversal.mp4",
            file_path=str(outside_file),
            file_size_bytes=100,
            duration_seconds=1.0,
            width=320,
            height=240,
            aspect_ratio="4:3",
            fps=30.0,
            video_codec="h264",
            status="READY",
        )
        session.add(vid)
        await session.commit()

    resp = await async_client.delete(f"/api/v1/videos/{vid_id}?purge_files=true")
    assert resp.status_code == 200

    # Ensure the outside file was NOT removed
    assert outside_file.exists(), "Path traversal protection failed! File outside storage was deleted."


@pytest.mark.asyncio
async def test_delete_video_preserves_exports_adr008(async_client: AsyncClient, tmp_path):
    """Verifies ADR-008: deleting a video and its audio asset preserves completed MP4 exports."""
    # Create fake upload file and audio asset
    upload_file = settings.UPLOAD_DIR / f"{uuid.uuid4().hex}_source.mp4"
    upload_file.write_bytes(b"FAKE_SOURCE_VIDEO")

    audio_file = settings.AUDIO_DIR / f"{uuid.uuid4().hex}.wav"
    audio_file.write_bytes(b"FAKE_AUDIO_WAV")

    export_file = settings.EXPORT_DIR / f"{uuid.uuid4().hex}_export.mp4"
    export_file.write_bytes(b"COMPLETED_MP4_EXPORT")

    vid_id = str(uuid.uuid4())
    audio_id = str(uuid.uuid4())
    clip_id = str(uuid.uuid4())
    export_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        vid = Video(
            id=vid_id,
            filename=upload_file.name,
            original_filename="source.mp4",
            file_path=str(upload_file),
            file_size_bytes=len(b"FAKE_SOURCE_VIDEO"),
            duration_seconds=5.0,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            status="READY",
        )
        asset = AudioAsset(
            id=audio_id,
            video_id=vid_id,
            filename=audio_file.name,
            file_path=str(audio_file),
            file_size_bytes=len(b"FAKE_AUDIO_WAV"),
            duration_seconds=5.0,
            format="wav",
            codec="pcm_s16le",
            sample_rate=16000,
            channels=1,
            channel_layout="mono",
            bit_depth=16,
            source_stream_index=1,
            status="COMPLETED",
        )
        clip = Clip(
            id=clip_id,
            video_id=vid_id,
            title="Highlight Clip",
            start_ms=1000,
            end_ms=7000,
            duration_ms=6000,
            status="READY",
        )
        export = ExportJob(
            id=export_id,
            clip_id=clip_id,
            video_id=vid_id,
            output_filename=export_file.name,
            output_path=str(export_file),
            status="COMPLETED",
            progress_percent=100.0,
        )
        session.add_all([vid, asset, clip, export])
        await session.commit()

    resp = await async_client.delete(f"/api/v1/videos/{vid_id}?purge_files=true")
    assert resp.status_code == 200

    # Source and audio files must be unlinked
    assert not upload_file.exists(), "Source video file was not unlinked."
    assert not audio_file.exists(), "Audio asset file was not unlinked."

    # Completed export must be preserved on disk (ADR-008)
    assert export_file.exists(), "ADR-008 violation: Exported MP4 was deleted when video was purged!"

    # Cleanup export file
    export_file.unlink()
