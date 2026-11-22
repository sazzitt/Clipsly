import asyncio
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
from httpx import AsyncClient
import pytest
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.video import Video


@pytest.fixture(scope="session")
def media_fixtures(tmp_path_factory):
    """Generates small, valid media test fixtures using local FFmpeg."""
    fixture_dir = tmp_path_factory.mktemp("test_media")
    mp4_path = fixture_dir / "valid_sample.mp4"
    mkv_path = fixture_dir / "valid_sample.mkv"
    webm_path = fixture_dir / "valid_sample.webm"
    mov_path = fixture_dir / "valid_sample.mov"
    audio_only_path = fixture_dir / "audio_only.mp4"

    # 1-second valid MP4 with video + audio
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-c:v", "libx264", "-c:a", "aac",
            "-y", str(mp4_path)
        ],
        check=True
    )

    # 1-second valid MKV
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-c:v", "libx264", "-c:a", "aac",
            "-y", str(mkv_path)
        ],
        check=True
    )

    # 1-second valid WebM
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-c:v", "libvpx", "-c:a", "libopus",
            "-y", str(webm_path)
        ],
        check=True
    )

    # 1-second valid QuickTime MOV
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-c:v", "libx264", "-c:a", "aac",
            "-y", str(mov_path)
        ],
        check=True
    )

    # Audio-only MP4 (no video stream)
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-c:a", "aac", "-vn",
            "-y", str(audio_only_path)
        ],
        check=True
    )

    return {
        "mp4": mp4_path,
        "mkv": mkv_path,
        "webm": webm_path,
        "mov": mov_path,
        "audio_only": audio_only_path,
    }


@pytest.fixture(autouse=True)
def bypass_duration_limits():
    """Temporarily disables 5-min minimum duration check for unit test media fixtures."""
    original_enforce = settings.ENFORCE_DURATION_LIMITS
    settings.ENFORCE_DURATION_LIMITS = False
    yield
    settings.ENFORCE_DURATION_LIMITS = original_enforce


@pytest.mark.asyncio
async def test_upload_valid_mp4(async_client: AsyncClient, media_fixtures):
    """Verifies successful upload of a valid MP4 file."""
    mp4_path = media_fixtures["mp4"]
    original_name = "My_Podcast_Ep1.mp4"

    with open(mp4_path, "rb") as f:
        files = {"file": (original_name, f, "video/mp4")}
        res = await async_client.post("/api/v1/videos/upload", files=files)

    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    assert data["original_filename"] == original_name
    assert data["filename"].endswith(".mp4")
    assert data["status"] == "READY"
    assert data["width"] == 320
    assert data["height"] == 240
    assert data["fps"] == 30.0
    assert data["video_codec"] == "h264"
    assert data["audio_codec"] == "aac"
    assert data["duration_seconds"] > 0

    # Verify physical file existence in storage/uploads/
    final_file = settings.UPLOAD_DIR / data["filename"]
    assert final_file.exists()
    assert final_file.stat().st_size == data["file_size_bytes"]

    # Verify database persistence
    async with AsyncSessionLocal() as session:
        vid_in_db = await session.get(Video, data["id"])
        assert vid_in_db is not None
        assert vid_in_db.original_filename == original_name
        # Cleanup
        await session.delete(vid_in_db)
        await session.commit()

    if final_file.exists():
        final_file.unlink()


@pytest.mark.asyncio
async def test_upload_valid_mkv(async_client: AsyncClient, media_fixtures):
    """Verifies successful upload of a valid MKV file."""
    mkv_path = media_fixtures["mkv"]
    with open(mkv_path, "rb") as f:
        files = {"file": ("stream_recording.mkv", f, "video/x-matroska")}
        res = await async_client.post("/api/v1/videos/upload", files=files)

    assert res.status_code == 201
    data = res.json()
    assert data["original_filename"] == "stream_recording.mkv"
    assert data["filename"].endswith(".mkv")

    # Cleanup
    final_file = settings.UPLOAD_DIR / data["filename"]
    if final_file.exists():
        final_file.unlink()
    async with AsyncSessionLocal() as session:
        v = await session.get(Video, data["id"])
        if v:
            await session.delete(v)
            await session.commit()


@pytest.mark.asyncio
async def test_upload_valid_webm(async_client: AsyncClient, media_fixtures):
    """Verifies successful upload of a valid WebM file."""
    webm_path = media_fixtures["webm"]
    with open(webm_path, "rb") as f:
        files = {"file": ("browser_capture.webm", f, "video/webm")}
        res = await async_client.post("/api/v1/videos/upload", files=files)

    assert res.status_code == 201
    data = res.json()
    assert data["original_filename"] == "browser_capture.webm"
    assert data["filename"].endswith(".webm")

    # Cleanup
    final_file = settings.UPLOAD_DIR / data["filename"]
    if final_file.exists():
        final_file.unlink()
    async with AsyncSessionLocal() as session:
        v = await session.get(Video, data["id"])
        if v:
            await session.delete(v)
            await session.commit()


@pytest.mark.asyncio
async def test_upload_unsupported_extension(async_client: AsyncClient):
    """Rejects files with unsupported extensions (e.g. .txt, .exe, .png)."""
    file_bytes = b"Hello world text content"
    files = {"file": ("notes.txt", io.BytesIO(file_bytes), "text/plain")}
    res = await async_client.post("/api/v1/videos/upload", files=files)

    assert res.status_code == 400
    data = res.json()
    assert data["error_code"] == "INVALID_FILE_FORMAT"
    assert "Unsupported video file extension" in data["detail"]


@pytest.mark.asyncio
async def test_upload_empty_file(async_client: AsyncClient):
    """Rejects empty (0 bytes) upload files."""
    files = {"file": ("empty.mp4", io.BytesIO(b""), "video/mp4")}
    res = await async_client.post("/api/v1/videos/upload", files=files)

    assert res.status_code == 400
    data = res.json()
    assert data["error_code"] == "INVALID_FILE_FORMAT"
    assert "empty (0 bytes)" in data["detail"]


@pytest.mark.asyncio
async def test_upload_exceeds_max_size(async_client: AsyncClient, monkeypatch):
    """Enforces maximum allowed upload size limit during streaming."""
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 500)  # Low 500-byte limit for test

    oversized_data = b"X" * 1024  # 1024 bytes > 500 bytes
    files = {"file": ("oversized.mp4", io.BytesIO(oversized_data), "video/mp4")}
    res = await async_client.post("/api/v1/videos/upload", files=files)

    assert res.status_code == 413
    data = res.json()
    assert data["error_code"] == "FILE_TOO_LARGE"

    # Confirm no temp files remain in storage/temp/
    temp_files = list(settings.TEMP_DIR.glob("upload_*.tmp"))
    assert len(temp_files) == 0


@pytest.mark.asyncio
async def test_upload_corrupt_video(async_client: AsyncClient):
    """Rejects corrupt or non-media files with a valid video extension."""
    fake_video_bytes = b"NOT_A_REAL_VIDEO_HEADER_RANDOM_DATA" * 50
    files = {"file": ("corrupt.mp4", io.BytesIO(fake_video_bytes), "video/mp4")}
    res = await async_client.post("/api/v1/videos/upload", files=files)

    assert res.status_code == 400
    data = res.json()
    assert data["error_code"] == "INVALID_FILE_FORMAT"
    assert "FFprobe failed" in data["detail"]

    # Confirm temp file unlinked
    temp_files = list(settings.TEMP_DIR.glob("upload_*.tmp"))
    assert len(temp_files) == 0


@pytest.mark.asyncio
async def test_upload_no_video_stream(async_client: AsyncClient, media_fixtures):
    """Rejects media container missing a video stream."""
    audio_only = media_fixtures["audio_only"]
    with open(audio_only, "rb") as f:
        files = {"file": ("audio_only.mp4", f, "video/mp4")}
        res = await async_client.post("/api/v1/videos/upload", files=files)

    assert res.status_code == 400
    data = res.json()
    assert data["error_code"] == "INVALID_FILE_FORMAT"
    assert "No valid video stream" in data["detail"]


@pytest.mark.asyncio
async def test_upload_low_disk_space_rejection(async_client: AsyncClient, monkeypatch, media_fixtures):
    """Rejects uploads when SSD free space is below the 10GB threshold."""
    # Simulate free disk space = 2GB (< 10GB)
    class MockUsage:
        free = 2 * (1024 ** 3)
    monkeypatch.setattr(shutil, "disk_usage", lambda _: MockUsage())

    mp4_path = media_fixtures["mp4"]
    with open(mp4_path, "rb") as f:
        files = {"file": ("sample.mp4", f, "video/mp4")}
        res = await async_client.post("/api/v1/videos/upload", files=files)

    assert res.status_code == 507
    data = res.json()
    assert data["error_code"] == "INSUFFICIENT_STORAGE"
    assert "Insufficient local SSD storage" in data["detail"]


@pytest.mark.asyncio
async def test_upload_duration_limits_enforced(async_client: AsyncClient, media_fixtures, monkeypatch):
    """Verifies that duration boundary checks reject files shorter than minimum duration."""
    monkeypatch.setattr(settings, "ENFORCE_DURATION_LIMITS", True)
    monkeypatch.setattr(settings, "MIN_VIDEO_DURATION_SECONDS", 300.0)  # 5 minutes

    # 1-second sample video is shorter than 300 seconds
    mp4_path = media_fixtures["mp4"]
    with open(mp4_path, "rb") as f:
        files = {"file": ("too_short.mp4", f, "video/mp4")}
        res = await async_client.post("/api/v1/videos/upload", files=files)

    assert res.status_code == 400
    data = res.json()
    assert data["error_code"] == "INVALID_FILE_FORMAT"
    assert "Minimum required duration is" in data["detail"]


@pytest.mark.asyncio
async def test_duplicate_filename_preserves_unique_records(async_client: AsyncClient, media_fixtures):
    """Uploading two videos with the same original filename assigns distinct UUIDs and files."""
    mp4_path = media_fixtures["mp4"]
    dup_filename = f"Duplicate_Test_{uuid.uuid4().hex[:6]}.mp4"

    # First upload
    with open(mp4_path, "rb") as f1:
        res1 = await async_client.post("/api/v1/videos/upload", files={"file": (dup_filename, f1, "video/mp4")})
    assert res1.status_code == 201
    vid1 = res1.json()

    # Second upload with identical filename
    with open(mp4_path, "rb") as f2:
        res2 = await async_client.post("/api/v1/videos/upload", files={"file": (dup_filename, f2, "video/mp4")})
    assert res2.status_code == 201
    vid2 = res2.json()

    # Verify both exist independently
    assert vid1["id"] != vid2["id"]
    assert vid1["filename"] != vid2["filename"]
    assert vid1["original_filename"] == vid2["original_filename"] == dup_filename

    # Verify both records in Video Library list
    list_res = await async_client.get(f"/api/v1/videos?search={dup_filename}")
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    ids = [item["id"] for item in items]
    assert vid1["id"] in ids
    assert vid2["id"] in ids

    # Cleanup
    for vid_info in [vid1, vid2]:
        p = settings.UPLOAD_DIR / vid_info["filename"]
        if p.exists():
            p.unlink()
        async with AsyncSessionLocal() as session:
            v = await session.get(Video, vid_info["id"])
            if v:
                await session.delete(v)
                await session.commit()


@pytest.mark.asyncio
async def test_upload_valid_mov(async_client: AsyncClient, media_fixtures):
    """Verifies successful upload of a valid QuickTime MOV file through actual FFprobe inspection."""
    mov_path = media_fixtures["mov"]
    with open(mov_path, "rb") as f:
        files = {"file": ("iphone_recording.mov", f, "video/quicktime")}
        res = await async_client.post("/api/v1/videos/upload", files=files)

    assert res.status_code == 201
    data = res.json()
    assert data["original_filename"] == "iphone_recording.mov"
    assert data["filename"].endswith(".mov")
    assert data["status"] == "READY"
    assert data["video_codec"] == "h264"
    assert data["audio_codec"] == "aac"
    assert data["storage_label"] == "Local SSD Storage"
    assert "file_path" not in data

    # Verify physical file existence in storage/uploads/
    final_file = settings.UPLOAD_DIR / data["filename"]
    assert final_file.exists()

    # Cleanup
    final_file.unlink()
    async with AsyncSessionLocal() as session:
        v = await session.get(Video, data["id"])
        if v:
            await session.delete(v)
            await session.commit()


@pytest.mark.asyncio
async def test_path_privacy_no_raw_paths_in_response(async_client: AsyncClient, media_fixtures):
    """Verifies that internal filesystem paths are never leaked in public API responses."""
    mp4_path = media_fixtures["mp4"]
    with open(mp4_path, "rb") as f:
        res = await async_client.post("/api/v1/videos/upload", files={"file": ("privacy_sample.mp4", f, "video/mp4")})

    assert res.status_code == 201
    upload_data = res.json()

    # Assert raw path is not present in upload response
    assert "file_path" not in upload_data
    assert upload_data.get("storage_label") == "Local SSD Storage"

    # Assert raw path is not present in get_video details response
    detail_res = await async_client.get(f"/api/v1/videos/{upload_data['id']}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert "file_path" not in detail_data
    assert detail_data.get("storage_label") == "Local SSD Storage"
    assert detail_data.get("file_exists") is True

    # Cleanup
    final_file = settings.UPLOAD_DIR / upload_data["filename"]
    if final_file.exists():
        final_file.unlink()
    async with AsyncSessionLocal() as session:
        v = await session.get(Video, upload_data["id"])
        if v:
            await session.delete(v)
            await session.commit()


@pytest.mark.asyncio
async def test_ffprobe_timeout_cleanup(async_client: AsyncClient, media_fixtures, monkeypatch):
    """FFprobe timeout triggers process kill, temporary file cleanup, and leaves no DB record."""
    from backend.app.services import video_ingestion
    from backend.app.core.exceptions import InvalidFileFormatError

    async def mock_timeout(file_path: Path, timeout_seconds: float = 30.0):
        # Create a lingering subproc to verify cleanup
        proc = await asyncio.create_subprocess_exec("timeout", "5", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            await asyncio.wait_for(proc.communicate(), timeout=0.01)
        except asyncio.TimeoutError:
            proc.kill()
            try:
                await proc.wait()
            except Exception:
                pass
            raise InvalidFileFormatError(f"FFprobe timed out while validating video container ({timeout_seconds:.0f}s watchdog limit).")

    monkeypatch.setattr(video_ingestion, "inspect_with_ffprobe", mock_timeout)

    mp4_path = media_fixtures["mp4"]
    with open(mp4_path, "rb") as f:
        res = await async_client.post("/api/v1/videos/upload", files={"file": ("timeout_test.mp4", f, "video/mp4")})

    assert res.status_code == 400
    assert "FFprobe timed out" in res.json()["detail"]

    # Verify temporary scratch file is completely unlinked
    temp_files = list(settings.TEMP_DIR.glob("upload_*.tmp"))
    assert len(temp_files) == 0

    # Verify no orphaned records in database
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Video).where(Video.original_filename == "timeout_test.mp4"))
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_ffprobe_missing_binary(async_client: AsyncClient, media_fixtures, monkeypatch):
    """Missing ffprobe executable on PATH returns 500 FFPROBE_NOT_FOUND, cleans up temp file, and creates no DB record."""
    orig_create_subprocess_exec = asyncio.create_subprocess_exec

    async def mock_subprocess(*args, **kwargs):
        if args and args[0] == "ffprobe":
            raise FileNotFoundError("ffprobe binary not found")
        return await orig_create_subprocess_exec(*args, **kwargs)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", mock_subprocess)

    mp4_path = media_fixtures["mp4"]
    with open(mp4_path, "rb") as f:
        res = await async_client.post("/api/v1/videos/upload", files={"file": ("missing_ffprobe.mp4", f, "video/mp4")})

    assert res.status_code == 500
    data = res.json()
    assert data["error_code"] == "FFPROBE_NOT_FOUND"

    temp_files = list(settings.TEMP_DIR.glob("upload_*.tmp"))
    assert len(temp_files) == 0

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Video).where(Video.original_filename == "missing_ffprobe.mp4"))
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_disk_write_failure_cleanup(async_client: AsyncClient, media_fixtures, monkeypatch):
    """Disk write failure (e.g. OSError / write error during streaming) unlinks scratch file and leaves no DB record."""
    from backend.app.services import video_ingestion

    async def mock_stream_failure(*args, **kwargs):
        temp_path = kwargs.get("temp_path") or args[1]
        with open(temp_path, "wb") as f:
            f.write(b"partial video bytes written to disk")
        raise OSError("[Errno 28] No space left on device")

    monkeypatch.setattr(video_ingestion, "stream_file_to_disk", mock_stream_failure)

    mp4_path = media_fixtures["mp4"]
    with open(mp4_path, "rb") as f:
        res = await async_client.post("/api/v1/videos/upload", files={"file": ("disk_full.mp4", f, "video/mp4")})

    assert res.status_code == 500
    data = res.json()
    assert data["error_code"] == "STORAGE_WRITE_ERROR"
    assert "No space left on device" in data["detail"]

    temp_files = list(settings.TEMP_DIR.glob("upload_*.tmp"))
    assert len(temp_files) == 0

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Video).where(Video.original_filename == "disk_full.mp4"))
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_db_commit_failure_cleans_persistent_file(async_client: AsyncClient, media_fixtures, monkeypatch):
    """If database commit fails after file is moved to persistent storage, the persistent file is unlinked and no orphan remains."""
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.ext.asyncio import AsyncSession

    async def mock_commit_failure(self):
        raise SQLAlchemyError("Simulated SQLite write error during commit")

    monkeypatch.setattr(AsyncSession, "commit", mock_commit_failure)

    mp4_path = media_fixtures["mp4"]
    with open(mp4_path, "rb") as f:
        res = await async_client.post("/api/v1/videos/upload", files={"file": ("db_fail_test.mp4", f, "video/mp4")})

    assert res.status_code == 500
    data = res.json()
    assert data["error_code"] == "DATABASE_ERROR"

    # Verify no persistent files in storage/uploads/ match this test
    orphan_files = list(settings.UPLOAD_DIR.glob("*db_fail_test*"))
    assert len(orphan_files) == 0

    # Verify temp files are clean
    temp_files = list(settings.TEMP_DIR.glob("upload_*.tmp"))
    assert len(temp_files) == 0

    # Verify no DB record exists
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Video).where(Video.original_filename == "db_fail_test.mp4"))
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_client_cancellation_during_upload(media_fixtures):
    """Simulates client disconnect during streaming, asserting file handle closure, temp-file deletion, and zero DB records."""
    from backend.app.services.video_ingestion import stream_file_to_disk
    from backend.app.core.exceptions import ClientDisconnectError
    from fastapi import UploadFile

    mp4_path = media_fixtures["mp4"]
    temp_path = settings.TEMP_DIR / f"upload_cancel_test_{uuid.uuid4().hex}.tmp"

    class MockDisconnectedRequest:
        async def is_disconnected(self) -> bool:
            return True

    with open(mp4_path, "rb") as f:
        upload_file = UploadFile(file=f, filename="cancel_test.mp4")
        with pytest.raises(ClientDisconnectError) as exc_info:
            await stream_file_to_disk(
                upload_file=upload_file,
                temp_path=temp_path,
                max_bytes=settings.MAX_UPLOAD_SIZE_BYTES,
                chunk_size=1024,
                request=MockDisconnectedRequest(),
            )

    assert "Client disconnected" in str(exc_info.value)
    # File handle closed and temp file removed
    assert not temp_path.exists()


@pytest.mark.asyncio
async def test_route_handles_client_disconnect(async_client: AsyncClient, media_fixtures, monkeypatch):
    """Route returns 499 CLIENT_CLOSED_REQUEST when client disconnects during streaming."""
    from starlette.requests import Request

    async def mock_is_disconnected(self):
        return True

    monkeypatch.setattr(Request, "is_disconnected", mock_is_disconnected)

    mp4_path = media_fixtures["mp4"]
    with open(mp4_path, "rb") as f:
        res = await async_client.post("/api/v1/videos/upload", files={"file": ("disconnect_test.mp4", f, "video/mp4")})

    assert res.status_code == 499
    assert res.json()["error_code"] == "CLIENT_CLOSED_REQUEST"
    assert len(list(settings.TEMP_DIR.glob("upload_*.tmp"))) == 0


@pytest.mark.asyncio
async def test_duplicate_content_behavior(async_client: AsyncClient, media_fixtures):
    """Uploading identical content bytes twice creates two independent records and files without overwriting or collision."""
    mp4_path = media_fixtures["mp4"]

    with open(mp4_path, "rb") as f1:
        res1 = await async_client.post("/api/v1/videos/upload", files={"file": ("original_clip.mp4", f1, "video/mp4")})
    assert res1.status_code == 201
    vid1 = res1.json()

    with open(mp4_path, "rb") as f2:
        res2 = await async_client.post("/api/v1/videos/upload", files={"file": ("copy_of_clip.mp4", f2, "video/mp4")})
    assert res2.status_code == 201
    vid2 = res2.json()

    assert vid1["id"] != vid2["id"]
    assert vid1["filename"] != vid2["filename"]

    file1 = settings.UPLOAD_DIR / vid1["filename"]
    file2 = settings.UPLOAD_DIR / vid2["filename"]
    assert file1.exists()
    assert file2.exists()
    assert file1 != file2
    assert file1.stat().st_size == file2.stat().st_size

    # Deleting vid1 does not delete file2
    del_res = await async_client.delete(f"/api/v1/videos/{vid1['id']}?purge_files=true")
    assert del_res.status_code == 200
    assert not file1.exists()
    assert file2.exists()

    # Cleanup vid2
    await async_client.delete(f"/api/v1/videos/{vid2['id']}?purge_files=true")
    assert not file2.exists()

