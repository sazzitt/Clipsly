import asyncio
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient
import pytest
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.database import AsyncSessionLocal
from backend.app.core.exceptions import (
    NotFoundError,
    InvalidFileFormatError,
    AppException,
)
from backend.app.models.video import Video
from backend.app.services.metadata_extraction import (
    extract_video_metadata,
    extract_and_persist_metadata,
    _active_extractions,
)


@pytest.fixture(scope="session")
def phase13_media_fixtures(tmp_path_factory):
    """Generates small, valid media test fixtures using local FFmpeg."""
    fixture_dir = tmp_path_factory.mktemp("phase13_media")
    mp4_path = fixture_dir / "landscape_audio.mp4"
    portrait_path = fixture_dir / "portrait_video.mp4"
    no_audio_path = fixture_dir / "no_audio.mp4"
    mkv_path = fixture_dir / "test.mkv"
    webm_path = fixture_dir / "test.webm"
    mov_path = fixture_dir / "test.mov"
    corrupt_path = fixture_dir / "corrupted.mp4"

    # 1. Landscape MP4 with audio (1 second, 320x240, 30fps, H.264 + AAC)
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

    # 2. Portrait MP4 (1 second, 240x320, 30fps)
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=240x320:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-c:v", "libx264", "-c:a", "aac",
            "-y", str(portrait_path)
        ],
        check=True
    )

    # 3. Video without audio (1 second, 320x240, no audio track)
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
            "-c:v", "libx264", "-an",
            "-y", str(no_audio_path)
        ],
        check=True
    )

    # 4. MKV format
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

    # 5. WebM format (VP8/VP9 + Opus)
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

    # 6. QuickTime MOV
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

    # 7. Corrupt video
    corrupt_path.write_bytes(b"CORRUPT_NOT_A_REAL_VIDEO_HEADER_1234567890")

    return {
        "mp4": mp4_path,
        "portrait": portrait_path,
        "no_audio": no_audio_path,
        "mkv": mkv_path,
        "webm": webm_path,
        "mov": mov_path,
        "corrupt": corrupt_path,
    }


@pytest.fixture(autouse=True)
def bypass_duration_limits():
    """Temporarily disables 5-min minimum duration check for unit test media fixtures."""
    original_enforce = settings.ENFORCE_DURATION_LIMITS
    settings.ENFORCE_DURATION_LIMITS = False
    yield
    settings.ENFORCE_DURATION_LIMITS = original_enforce


# ---------------------------------------------------------------------------
# Metadata Extraction Service Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_metadata_landscape_mp4(phase13_media_fixtures):
    """Verifies complete metadata extraction on a standard landscape MP4 with audio."""
    path = phase13_media_fixtures["mp4"]
    meta = await extract_video_metadata(path)

    assert meta["duration_seconds"] > 0.8
    assert meta["width"] == 320
    assert meta["height"] == 240
    assert meta["aspect_ratio"] == "4:3"
    assert meta["orientation"] == "landscape"
    assert meta["video_codec"] == "h264"
    assert meta["fps"] == 30.0
    assert meta["has_audio"] is True
    assert meta["audio_codec"] == "aac"
    assert meta["audio_sample_rate"] > 0
    assert meta["audio_channels"] >= 1
    assert meta["container_format"] is not None
    assert meta["pixel_format"] is not None
    assert meta["bit_depth"] is not None


@pytest.mark.asyncio
async def test_extract_metadata_portrait(phase13_media_fixtures):
    """Verifies orientation detection computes 'portrait' for vertical videos."""
    path = phase13_media_fixtures["portrait"]
    meta = await extract_video_metadata(path)

    assert meta["width"] == 240
    assert meta["height"] == 320
    assert meta["orientation"] == "portrait"
    assert meta["has_audio"] is True


@pytest.mark.asyncio
async def test_extract_metadata_no_audio(phase13_media_fixtures):
    """Verifies that videos without audio tracks are handled gracefully with null audio fields."""
    path = phase13_media_fixtures["no_audio"]
    meta = await extract_video_metadata(path)

    assert meta["has_audio"] is False
    assert meta["audio_codec"] is None
    assert meta["audio_sample_rate"] is None
    assert meta["audio_channels"] is None
    assert meta["audio_bitrate"] is None
    assert meta["channel_layout"] is None
    assert meta["width"] == 320
    assert meta["height"] == 240


@pytest.mark.asyncio
async def test_extract_metadata_mkv(phase13_media_fixtures):
    """Verifies metadata extraction on Matroska (MKV) container."""
    path = phase13_media_fixtures["mkv"]
    meta = await extract_video_metadata(path)

    assert meta["width"] == 320
    assert "matroska" in meta["container_format"].lower()
    assert meta["video_codec"] == "h264"


@pytest.mark.asyncio
async def test_extract_metadata_webm(phase13_media_fixtures):
    """Verifies metadata extraction on WebM container."""
    path = phase13_media_fixtures["webm"]
    meta = await extract_video_metadata(path)

    assert meta["width"] == 320
    assert "webm" in meta["container_format"].lower() or "matroska" in meta["container_format"].lower()
    assert meta["audio_codec"] == "opus"


@pytest.mark.asyncio
async def test_extract_metadata_mov(phase13_media_fixtures):
    """Verifies metadata extraction on QuickTime MOV container."""
    path = phase13_media_fixtures["mov"]
    meta = await extract_video_metadata(path)

    assert meta["width"] == 320
    assert "mov" in meta["container_format"].lower() or "quicktime" in meta["container_format"].lower()
    assert meta["video_codec"] == "h264"


@pytest.mark.asyncio
async def test_extract_metadata_corrupted_file(phase13_media_fixtures):
    """Verifies corrupt media files raise InvalidFileFormatError during extraction."""
    path = phase13_media_fixtures["corrupt"]
    with pytest.raises(InvalidFileFormatError):
        await extract_video_metadata(path)


@pytest.mark.asyncio
async def test_extract_metadata_missing_file():
    """Verifies non-existent video files raise NotFoundError."""
    missing = Path(tempfile.gettempdir()) / f"non_existent_{uuid.uuid4().hex}.mp4"
    with pytest.raises(NotFoundError):
        await extract_video_metadata(missing)


@pytest.mark.asyncio
async def test_extract_metadata_timeout():
    """Verifies timeout triggers process termination and raises InvalidFileFormatError."""
    path = Path(__file__)
    with pytest.raises(InvalidFileFormatError):
        await extract_video_metadata(path, timeout_seconds=0.00001)


# ---------------------------------------------------------------------------
# Concurrency & Database Refresh Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_and_persist_metadata(phase13_media_fixtures):
    """Verifies extract_and_persist_metadata updates the database and marks status COMPLETED."""
    src_file = phase13_media_fixtures["mp4"]
    unique_name = f"persist_test_{uuid.uuid4().hex}.mp4"
    dest_file = settings.UPLOAD_DIR / unique_name
    shutil.copy2(src_file, dest_file)

    async with AsyncSessionLocal() as session:
        vid = Video(
            id=str(uuid.uuid4()),
            filename=unique_name,
            original_filename="PersistTest.mp4",
            file_path=str(dest_file),
            file_size_bytes=dest_file.stat().st_size,
            duration_seconds=1.0,
            width=320,
            height=240,
            aspect_ratio="4:3",
            fps=30.0,
            video_codec="h264",
            status="READY",
            metadata_status="PENDING",
        )
        session.add(vid)
        await session.commit()
        await session.refresh(vid)
        vid_id = vid.id

    try:
        async with AsyncSessionLocal() as session:
            updated_vid = await extract_and_persist_metadata(vid_id, session)
            assert updated_vid.metadata_status == "COMPLETED"
            assert updated_vid.orientation == "landscape"
            assert updated_vid.metadata_extracted_at is not None
            assert updated_vid.container_format is not None
    finally:
        if dest_file.exists():
            dest_file.unlink()
        async with AsyncSessionLocal() as session:
            v = await session.get(Video, vid_id)
            if v:
                await session.delete(v)
                await session.commit()


@pytest.mark.asyncio
async def test_refresh_metadata_concurrency_lock():
    """Verifies that active extraction locks prevent concurrent re-extractions."""
    fake_id = f"test-concurrent-{uuid.uuid4().hex}"
    _active_extractions.add(fake_id)

    try:
        async with AsyncSessionLocal() as session:
            with pytest.raises(AppException) as exc_info:
                await extract_and_persist_metadata(fake_id, session)
            assert exc_info.value.status_code == 409
    finally:
        _active_extractions.discard(fake_id)


# ---------------------------------------------------------------------------
# API Endpoints: Refresh & Detail Schema Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_refresh_metadata_endpoint(async_client: AsyncClient, phase13_media_fixtures):
    """Verifies POST /api/v1/videos/{video_id}/metadata/refresh triggers re-extraction."""
    src_file = phase13_media_fixtures["mp4"]
    unique_name = f"api_refresh_{uuid.uuid4().hex}.mp4"
    dest_file = settings.UPLOAD_DIR / unique_name
    shutil.copy2(src_file, dest_file)

    vid_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        vid = Video(
            id=vid_id,
            filename=unique_name,
            original_filename="ApiRefresh.mp4",
            file_path=str(dest_file),
            file_size_bytes=dest_file.stat().st_size,
            duration_seconds=1.0,
            width=320,
            height=240,
            aspect_ratio="4:3",
            fps=30.0,
            video_codec="h264",
            status="READY",
            metadata_status="PENDING",
        )
        session.add(vid)
        await session.commit()

    try:
        res = await async_client.post(f"/api/v1/videos/{vid_id}/metadata/refresh")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == vid_id
        assert data["metadata_status"] == "COMPLETED"
        assert data["orientation"] == "landscape"
        assert data["has_audio"] is True
        assert data["metadata_extracted_at"] is not None

        # Also verify GET /api/v1/videos/{video_id} returns enriched fields
        get_res = await async_client.get(f"/api/v1/videos/{vid_id}")
        assert get_res.status_code == 200
        detail = get_res.json()
        assert detail["orientation"] == "landscape"
        assert detail["container_format"] is not None
        assert detail["pixel_format"] is not None
        assert detail["bit_depth"] is not None
    finally:
        if dest_file.exists():
            dest_file.unlink()
        async with AsyncSessionLocal() as session:
            v = await session.get(Video, vid_id)
            if v:
                await session.delete(v)
                await session.commit()


@pytest.mark.asyncio
async def test_api_refresh_metadata_missing_video(async_client: AsyncClient):
    """Verifies POST /api/v1/videos/{video_id}/metadata/refresh returns 404 for non-existent video."""
    res = await async_client.post(f"/api/v1/videos/{uuid.uuid4()}/metadata/refresh")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Video Streaming & Range Header Tests (RFC 9110)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stream_video_full_content(async_client: AsyncClient, phase13_media_fixtures):
    """Verifies streaming video without Range header returns 200 OK with full content."""
    src_file = phase13_media_fixtures["mp4"]
    unique_name = f"stream_full_{uuid.uuid4().hex}.mp4"
    dest_file = settings.UPLOAD_DIR / unique_name
    shutil.copy2(src_file, dest_file)
    file_size = dest_file.stat().st_size

    vid_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        vid = Video(
            id=vid_id,
            filename=unique_name,
            original_filename="StreamFull.mp4",
            file_path=str(dest_file),
            file_size_bytes=file_size,
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

    try:
        res = await async_client.get(f"/api/v1/videos/{vid_id}/stream")
        assert res.status_code == 200
        assert res.headers["Accept-Ranges"] == "bytes"
        assert res.headers["Content-Type"] == "video/mp4"
        assert int(res.headers["Content-Length"]) == file_size
        assert len(res.content) == file_size
    finally:
        if dest_file.exists():
            dest_file.unlink()
        async with AsyncSessionLocal() as session:
            v = await session.get(Video, vid_id)
            if v:
                await session.delete(v)
                await session.commit()


@pytest.mark.asyncio
async def test_stream_video_range_slice(async_client: AsyncClient, phase13_media_fixtures):
    """Verifies streaming with standard Range header (bytes=0-499) returns 206 Partial Content."""
    src_file = phase13_media_fixtures["mp4"]
    unique_name = f"stream_slice_{uuid.uuid4().hex}.mp4"
    dest_file = settings.UPLOAD_DIR / unique_name
    shutil.copy2(src_file, dest_file)
    file_size = dest_file.stat().st_size

    vid_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        vid = Video(
            id=vid_id,
            filename=unique_name,
            original_filename="StreamSlice.mp4",
            file_path=str(dest_file),
            file_size_bytes=file_size,
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

    try:
        headers = {"Range": "bytes=0-499"}
        res = await async_client.get(f"/api/v1/videos/{vid_id}/stream", headers=headers)
        assert res.status_code == 206
        assert res.headers["Accept-Ranges"] == "bytes"
        assert res.headers["Content-Range"] == f"bytes 0-499/{file_size}"
        assert int(res.headers["Content-Length"]) == 500
        assert len(res.content) == 500
        with open(dest_file, "rb") as f:
            expected_prefix = f.read(500)
        assert res.content == expected_prefix
    finally:
        if dest_file.exists():
            dest_file.unlink()
        async with AsyncSessionLocal() as session:
            v = await session.get(Video, vid_id)
            if v:
                await session.delete(v)
                await session.commit()


@pytest.mark.asyncio
async def test_stream_video_range_open_ended(async_client: AsyncClient, phase13_media_fixtures):
    """Verifies streaming with open-ended Range header (bytes=200-) returns 206 through EOF."""
    src_file = phase13_media_fixtures["mp4"]
    unique_name = f"stream_open_{uuid.uuid4().hex}.mp4"
    dest_file = settings.UPLOAD_DIR / unique_name
    shutil.copy2(src_file, dest_file)
    file_size = dest_file.stat().st_size

    vid_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        vid = Video(
            id=vid_id,
            filename=unique_name,
            original_filename="StreamOpen.mp4",
            file_path=str(dest_file),
            file_size_bytes=file_size,
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

    try:
        headers = {"Range": "bytes=200-"}
        res = await async_client.get(f"/api/v1/videos/{vid_id}/stream", headers=headers)
        assert res.status_code == 206
        expected_len = file_size - 200
        assert res.headers["Content-Range"] == f"bytes 200-{file_size - 1}/{file_size}"
        assert int(res.headers["Content-Length"]) == expected_len
        assert len(res.content) == expected_len
    finally:
        if dest_file.exists():
            dest_file.unlink()
        async with AsyncSessionLocal() as session:
            v = await session.get(Video, vid_id)
            if v:
                await session.delete(v)
                await session.commit()


@pytest.mark.asyncio
async def test_stream_video_range_suffix(async_client: AsyncClient, phase13_media_fixtures):
    """Verifies streaming with suffix Range header (bytes=-300) returns 206 for the last 300 bytes."""
    src_file = phase13_media_fixtures["mp4"]
    unique_name = f"stream_suffix_{uuid.uuid4().hex}.mp4"
    dest_file = settings.UPLOAD_DIR / unique_name
    shutil.copy2(src_file, dest_file)
    file_size = dest_file.stat().st_size

    vid_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        vid = Video(
            id=vid_id,
            filename=unique_name,
            original_filename="StreamSuffix.mp4",
            file_path=str(dest_file),
            file_size_bytes=file_size,
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

    try:
        headers = {"Range": "bytes=-300"}
        res = await async_client.get(f"/api/v1/videos/{vid_id}/stream", headers=headers)
        assert res.status_code == 206
        assert res.headers["Content-Range"] == f"bytes {file_size - 300}-{file_size - 1}/{file_size}"
        assert int(res.headers["Content-Length"]) == 300
        assert len(res.content) == 300
    finally:
        if dest_file.exists():
            dest_file.unlink()
        async with AsyncSessionLocal() as session:
            v = await session.get(Video, vid_id)
            if v:
                await session.delete(v)
                await session.commit()


@pytest.mark.asyncio
async def test_stream_video_unsatisfiable_range(async_client: AsyncClient, phase13_media_fixtures):
    """Verifies that out-of-bounds Range header returns HTTP 416 Range Not Satisfiable."""
    src_file = phase13_media_fixtures["mp4"]
    unique_name = f"stream_unsatisfiable_{uuid.uuid4().hex}.mp4"
    dest_file = settings.UPLOAD_DIR / unique_name
    shutil.copy2(src_file, dest_file)
    file_size = dest_file.stat().st_size

    vid_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        vid = Video(
            id=vid_id,
            filename=unique_name,
            original_filename="StreamUnsatisfiable.mp4",
            file_path=str(dest_file),
            file_size_bytes=file_size,
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

    try:
        headers = {"Range": "bytes=99999999-"}
        res = await async_client.get(f"/api/v1/videos/{vid_id}/stream", headers=headers)
        assert res.status_code == 416
        assert res.headers["Content-Range"] == f"bytes */{file_size}"
    finally:
        if dest_file.exists():
            dest_file.unlink()
        async with AsyncSessionLocal() as session:
            v = await session.get(Video, vid_id)
            if v:
                await session.delete(v)
                await session.commit()


@pytest.mark.asyncio
async def test_stream_video_missing_file_on_disk(async_client: AsyncClient):
    """Verifies that if video record exists but file is missing on disk, 404 is returned."""
    vid_id = str(uuid.uuid4())
    fake_path = settings.UPLOAD_DIR / f"missing_{vid_id}.mp4"

    async with AsyncSessionLocal() as session:
        vid = Video(
            id=vid_id,
            filename=fake_path.name,
            original_filename="MissingFile.mp4",
            file_path=str(fake_path),
            file_size_bytes=1000,
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

    try:
        res = await async_client.get(f"/api/v1/videos/{vid_id}/stream")
        assert res.status_code in (400, 404)
    finally:
        async with AsyncSessionLocal() as session:
            v = await session.get(Video, vid_id)
            if v:
                await session.delete(v)
                await session.commit()


@pytest.mark.asyncio
async def test_stream_video_path_traversal_blocked(async_client: AsyncClient):
    """Verifies that paths pointing outside settings.STORAGE_DIR are rejected with 404/400."""
    vid_id = str(uuid.uuid4())
    traversal_path = Path(tempfile.gettempdir()) / f"outside_storage_{vid_id}.mp4"
    traversal_path.write_bytes(b"test")

    try:
        async with AsyncSessionLocal() as session:
            vid = Video(
                id=vid_id,
                filename="outside_storage.mp4",
                original_filename="Traversal.mp4",
                file_path=str(traversal_path),
                file_size_bytes=4,
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

        res = await async_client.get(f"/api/v1/videos/{vid_id}/stream")
        assert res.status_code in (400, 404)
    finally:
        if traversal_path.exists():
            traversal_path.unlink()
        async with AsyncSessionLocal() as session:
            v = await session.get(Video, vid_id)
            if v:
                await session.delete(v)
                await session.commit()
