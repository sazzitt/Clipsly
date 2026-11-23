import asyncio
import os
from pathlib import Path
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient
import pytest
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.database import AsyncSessionLocal
from backend.app.core.exceptions import (
    AppException,
    ConflictError,
    InvalidFileFormatError,
    NotFoundError,
)
from backend.app.models.audio_asset import AudioAsset
from backend.app.models.processing_job import ProcessingJob
from backend.app.models.video import Video
from backend.app.services.audio_extraction import (
    _active_extractions,
    cancel_audio_extraction,
    extract_and_preprocess_audio,
    inspect_audio_streams,
    select_target_audio_stream,
    validate_extracted_wav,
)


@pytest.fixture(scope="session")
def audio_test_media(tmp_path_factory):
    """Generates valid media fixtures using local FFmpeg for audio extraction testing."""
    fixture_dir = tmp_path_factory.mktemp("audio_test_media")
    mp4_path = fixture_dir / "sample_stereo.mp4"
    mkv_path = fixture_dir / "sample.mkv"
    webm_path = fixture_dir / "sample.webm"
    mov_path = fixture_dir / "sample.mov"
    no_audio_path = fixture_dir / "no_audio.mp4"
    multi_stream_path = fixture_dir / "multi_stream.mkv"
    corrupt_path = fixture_dir / "corrupted.mp4"

    # 1. MP4 with 48kHz stereo AAC audio (1.5 seconds)
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=1.5:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=48000:duration=1.5",
            "-ac", "2",
            "-c:v", "libx264", "-c:a", "aac",
            "-y", str(mp4_path),
        ],
        check=True,
    )

    # 2. MKV with AC3 audio (1.0 second)
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=800:duration=1",
            "-c:v", "libx264", "-c:a", "ac3",
            "-y", str(mkv_path),
        ],
        check=True,
    )

    # 3. WebM with Opus audio (1.0 second)
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=600:duration=1",
            "-c:v", "libvpx", "-c:a", "libopus",
            "-y", str(webm_path),
        ],
        check=True,
    )

    # 4. MOV with PCM audio (1.0 second)
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-c:v", "libx264", "-c:a", "aac",
            "-y", str(mov_path),
        ],
        check=True,
    )

    # 5. Video with NO audio track
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
            "-c:v", "libx264", "-an",
            "-y", str(no_audio_path),
        ],
        check=True,
    )

    # 6. Multi-stream MKV (Stream 0: video, Stream 1: AAC stereo [en], Stream 2: MP3 mono [es])
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=1.2:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=500:duration=1.2",
            "-f", "lavfi", "-i", "sine=frequency=1200:duration=1.2",
            "-map", "0:v", "-map", "1:a", "-map", "2:a",
            "-c:v", "libx264",
            "-c:a:0", "aac", "-metadata:s:a:0", "language=eng", "-metadata:s:a:0", "title=English",
            "-c:a:1", "libmp3lame", "-metadata:s:a:1", "language=spa", "-metadata:s:a:1", "title=Spanish",
            "-y", str(multi_stream_path),
        ],
        check=True,
    )

    # 7. Corrupt video
    corrupt_path.write_bytes(b"CORRUPT_NOT_A_REAL_VIDEO_HEADER_AUDIO_EXTRACTION")

    return {
        "mp4": mp4_path,
        "mkv": mkv_path,
        "webm": webm_path,
        "mov": mov_path,
        "no_audio": no_audio_path,
        "multi_stream": multi_stream_path,
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
# Unit Tests: inspect_audio_streams & select_target_audio_stream
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_inspect_audio_streams_mp4(audio_test_media):
    streams = await inspect_audio_streams(audio_test_media["mp4"])
    assert len(streams) == 1
    s = streams[0]
    assert s["index"] == 1
    assert s["codec_name"] == "aac"
    assert s["channels"] == 2
    assert s["sample_rate"] == 48000
    assert s["channel_layout"] in ("stereo", "2 channels")


@pytest.mark.asyncio
async def test_inspect_audio_streams_no_audio(audio_test_media):
    streams = await inspect_audio_streams(audio_test_media["no_audio"])
    assert streams == []


@pytest.mark.asyncio
async def test_inspect_audio_streams_multi_stream(audio_test_media):
    streams = await inspect_audio_streams(audio_test_media["multi_stream"])
    assert len(streams) == 2
    assert streams[0]["index"] == 1
    assert streams[0]["codec_name"] == "aac"
    assert streams[0]["language"] == "eng"
    assert streams[1]["index"] == 2
    assert streams[1]["codec_name"] == "mp3"
    assert streams[1]["language"] == "spa"


@pytest.mark.asyncio
async def test_inspect_audio_streams_missing_file():
    with pytest.raises(NotFoundError):
        await inspect_audio_streams(Path("non_existent_audio_video_12345.mp4"))


def test_select_target_audio_stream_default():
    streams = [
        {"index": 1, "codec_name": "aac", "is_default": False},
        {"index": 2, "codec_name": "mp3", "is_default": True},
    ]
    selected = select_target_audio_stream(streams)
    assert selected["index"] == 2


def test_select_target_audio_stream_by_index():
    streams = [
        {"index": 1, "codec_name": "aac", "is_default": True},
        {"index": 2, "codec_name": "mp3", "is_default": False},
    ]
    selected = select_target_audio_stream(streams, requested_index=2)
    assert selected["index"] == 2


def test_select_target_audio_stream_invalid_index():
    streams = [{"index": 1, "codec_name": "aac"}]
    with pytest.raises(InvalidFileFormatError) as exc_info:
        select_target_audio_stream(streams, requested_index=99)
    assert "Requested audio stream index 99 does not exist" in str(exc_info.value)


def test_select_target_audio_stream_empty():
    with pytest.raises(InvalidFileFormatError):
        select_target_audio_stream([])


# ---------------------------------------------------------------------------
# Unit Tests: validate_extracted_wav
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_extracted_wav_valid(tmp_path):
    wav_path = tmp_path / "valid.wav"
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            "-y", str(wav_path),
        ],
        check=True,
    )
    val = await validate_extracted_wav(wav_path, expected_duration=1.0)
    assert val["codec"] == "pcm_s16le"
    assert val["channels"] == 1
    assert val["sample_rate"] == 16000
    assert val["bit_depth"] == 16
    assert val["duration_seconds"] > 0.8
    assert val["file_size_bytes"] > 0


@pytest.mark.asyncio
async def test_validate_extracted_wav_missing_or_empty(tmp_path):
    empty_wav = tmp_path / "empty.wav"
    empty_wav.touch()
    with pytest.raises(InvalidFileFormatError):
        await validate_extracted_wav(empty_wav, expected_duration=1.0)

    non_existent = tmp_path / "does_not_exist.wav"
    with pytest.raises(InvalidFileFormatError):
        await validate_extracted_wav(non_existent, expected_duration=1.0)


@pytest.mark.asyncio
async def test_validate_extracted_wav_wrong_codec(tmp_path):
    wrong_wav = tmp_path / "wrong.wav"
    # Create MP3 inside a file named .wav
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-c:a", "libmp3lame",
            "-y", str(wrong_wav),
        ],
        check=True,
    )
    with pytest.raises(InvalidFileFormatError) as exc_info:
        await validate_extracted_wav(wrong_wav, expected_duration=1.0)
    assert "Audio codec mismatch" in str(exc_info.value) or "Audio channel mismatch" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Service Pipeline Tests: extract_and_preprocess_audio
# ---------------------------------------------------------------------------

async def _create_test_video(file_path: Path, filename: str, has_audio: bool = True) -> str:
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
            duration_seconds=1.5 if "stereo" in filename else 1.0,
            width=320,
            height=240,
            aspect_ratio="4:3",
            fps=30.0,
            video_codec="h264",
            audio_codec="aac" if has_audio else None,
            audio_channels=2 if has_audio else None,
            audio_sample_rate=48000 if has_audio else None,
            status="READY",
            metadata_status="COMPLETED",
        )
        session.add(vid)
        await session.commit()
    return vid_id


@pytest.mark.asyncio
async def test_extract_and_preprocess_mp4_pcm16k_mono(audio_test_media):
    vid_id = await _create_test_video(audio_test_media["mp4"], "stereo.mp4")

    asset = await extract_and_preprocess_audio(vid_id)
    assert asset is not None
    assert asset.video_id == vid_id
    assert asset.format == "wav"
    assert asset.codec == "pcm_s16le"
    assert asset.sample_rate == 16000
    assert asset.channels == 1
    assert asset.channel_layout == "mono"
    assert asset.bit_depth == 16
    assert asset.duration_seconds > 1.0
    assert asset.status == "COMPLETED"

    # Physical file verification
    p = Path(asset.file_path)
    assert p.exists()
    assert p.is_relative_to(settings.AUDIO_DIR.resolve())
    assert p.stat().st_size > 0


@pytest.mark.asyncio
async def test_extract_and_preprocess_mkv(audio_test_media):
    vid_id = await _create_test_video(audio_test_media["mkv"], "sample.mkv")
    asset = await extract_and_preprocess_audio(vid_id)
    assert asset.codec == "pcm_s16le"
    assert asset.sample_rate == 16000
    assert asset.channels == 1


@pytest.mark.asyncio
async def test_extract_and_preprocess_webm(audio_test_media):
    vid_id = await _create_test_video(audio_test_media["webm"], "sample.webm")
    asset = await extract_and_preprocess_audio(vid_id)
    assert asset.codec == "pcm_s16le"
    assert asset.sample_rate == 16000
    assert asset.channels == 1


@pytest.mark.asyncio
async def test_extract_and_preprocess_mov(audio_test_media):
    vid_id = await _create_test_video(audio_test_media["mov"], "sample.mov")
    asset = await extract_and_preprocess_audio(vid_id)
    assert asset.codec == "pcm_s16le"
    assert asset.sample_rate == 16000
    assert asset.channels == 1


@pytest.mark.asyncio
async def test_extract_multi_stream_selection(audio_test_media):
    vid_id = await _create_test_video(audio_test_media["multi_stream"], "multi.mkv")

    # Extract stream 2 (Spanish MP3 -> 16k mono WAV)
    asset = await extract_and_preprocess_audio(vid_id, stream_index=2, force_reextract=True)
    assert asset.source_stream_index == 2
    assert asset.codec == "pcm_s16le"
    assert asset.sample_rate == 16000
    assert asset.channels == 1


@pytest.mark.asyncio
async def test_extract_no_audio_raises_error(audio_test_media):
    vid_id = await _create_test_video(audio_test_media["no_audio"], "no_audio.mp4", has_audio=False)
    with pytest.raises(InvalidFileFormatError) as exc_info:
        await extract_and_preprocess_audio(vid_id)
    assert "no audio streams" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_extract_corrupted_file_raises_error(audio_test_media):
    vid_id = await _create_test_video(audio_test_media["corrupt"], "corrupt.mp4")
    with pytest.raises(InvalidFileFormatError):
        await extract_and_preprocess_audio(vid_id)


@pytest.mark.asyncio
async def test_extract_missing_file_on_disk_raises_error():
    vid_id = str(uuid.uuid4())
    unique_ghost = f"ghost_{uuid.uuid4().hex}.mp4"
    async with AsyncSessionLocal() as session:
        vid = Video(
            id=vid_id,
            filename=unique_ghost,
            original_filename="ghost.mp4",
            file_path=str(settings.UPLOAD_DIR / unique_ghost),
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

    with pytest.raises(NotFoundError):
        await extract_and_preprocess_audio(vid_id)


@pytest.mark.asyncio
async def test_extract_missing_video_id_raises_error():
    with pytest.raises(NotFoundError):
        await extract_and_preprocess_audio(str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_extract_concurrency_lock_prevents_duplicate(audio_test_media):
    vid_id = await _create_test_video(audio_test_media["mp4"], "lock_test.mp4")
    _active_extractions.add(vid_id)
    try:
        with pytest.raises(ConflictError) as exc_info:
            await extract_and_preprocess_audio(vid_id)
        assert "already in progress" in str(exc_info.value).lower()
    finally:
        _active_extractions.discard(vid_id)


@pytest.mark.asyncio
async def test_extract_reuses_existing_asset_when_not_forced(audio_test_media):
    vid_id = await _create_test_video(audio_test_media["mp4"], "reuse_test.mp4")

    # Initial extraction
    asset1 = await extract_and_preprocess_audio(vid_id)
    assert asset1 is not None

    # Second extraction without force_reextract should return existing record
    asset2 = await extract_and_preprocess_audio(vid_id, force_reextract=False)
    assert asset1.id == asset2.id
    assert asset1.file_path == asset2.file_path


@pytest.mark.asyncio
async def test_extract_force_reextract_overwrites(audio_test_media):
    vid_id = await _create_test_video(audio_test_media["mp4"], "force_test.mp4")

    asset1 = await extract_and_preprocess_audio(vid_id)
    first_path = Path(asset1.file_path)
    assert first_path.exists()

    # Force reextract
    asset2 = await extract_and_preprocess_audio(vid_id, force_reextract=True)
    assert asset2.status == "COMPLETED"
    second_path = Path(asset2.file_path)
    assert second_path.exists()


@pytest.mark.asyncio
async def test_extract_path_confinement_blocks_traversal():
    vid_id = str(uuid.uuid4())
    traversal_path = f"C:/Windows/System32/drivers/etc/hosts_{uuid.uuid4().hex}"
    async with AsyncSessionLocal() as session:
        vid = Video(
            id=vid_id,
            filename="traversal.mp4",
            original_filename="traversal.mp4",
            file_path=traversal_path,
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

    with pytest.raises(AppException) as exc_info:
        await extract_and_preprocess_audio(vid_id)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_cancel_audio_extraction_cleans_up(audio_test_media):
    vid_id = await _create_test_video(audio_test_media["mp4"], "cancel_test.mp4")
    job_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        job = ProcessingJob(
            id=job_id,
            video_id=vid_id,
            job_type="AUDIO_EXTRACTION",
            status="PROCESSING",
            progress_percent=25.0,
            current_step="Extracting audio...",
            started_at=datetime.now(timezone.utc),
        )
        session.add(job)
        await session.commit()

    # Test cancelling the job
    async with AsyncSessionLocal() as session:
        cancelled = await cancel_audio_extraction(job_id, session)
        assert cancelled is True

    # Check job status is CANCELLED
    async with AsyncSessionLocal() as session:
        updated_job = await session.get(ProcessingJob, job_id)
        assert updated_job.status == "CANCELLED"
        assert updated_job.completed_at is not None


# ---------------------------------------------------------------------------
# API Endpoints Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_extract_audio_endpoint_success(async_client: AsyncClient, audio_test_media):
    vid_id = await _create_test_video(audio_test_media["mp4"], "api_extract.mp4")

    resp = await async_client.post(f"/api/v1/videos/{vid_id}/extract-audio", json={"force_reextract": False})
    assert resp.status_code == 202
    data = resp.json()
    assert data["video_id"] == vid_id
    assert "job_id" in data
    assert data["status"] in ("QUEUED", "PROCESSING", "COMPLETED")

    # Wait briefly for extraction to finish
    await asyncio.sleep(1.0)

    # Verify audio asset exists via GET
    get_resp = await async_client.get(f"/api/v1/videos/{vid_id}/audio")
    assert get_resp.status_code == 200
    asset_data = get_resp.json()
    assert asset_data["codec"] == "pcm_s16le"
    assert asset_data["sample_rate"] == 16000
    assert asset_data["channels"] == 1


@pytest.mark.asyncio
async def test_api_extract_audio_no_audio_video_rejected(async_client: AsyncClient, audio_test_media):
    vid_id = await _create_test_video(audio_test_media["no_audio"], "api_no_audio.mp4", has_audio=False)

    resp = await async_client.post(f"/api/v1/videos/{vid_id}/extract-audio", json={})
    assert resp.status_code == 400
    data = resp.json()
    assert "no audio streams" in data["detail"].lower()


@pytest.mark.asyncio
async def test_api_extract_audio_not_found(async_client: AsyncClient):
    fake_id = str(uuid.uuid4())
    resp = await async_client.post(f"/api/v1/videos/{fake_id}/extract-audio", json={})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_extract_audio_conflict_when_active(async_client: AsyncClient, audio_test_media):
    vid_id = await _create_test_video(audio_test_media["mp4"], "api_conflict.mp4")
    _active_extractions.add(vid_id)
    try:
        resp = await async_client.post(f"/api/v1/videos/{vid_id}/extract-audio", json={})
        assert resp.status_code == 409
    finally:
        _active_extractions.discard(vid_id)


@pytest.mark.asyncio
async def test_api_get_audio_endpoint_not_found(async_client: AsyncClient, audio_test_media):
    vid_id = await _create_test_video(audio_test_media["mp4"], "api_not_extracted.mp4")
    resp = await async_client.get(f"/api/v1/videos/{vid_id}/audio")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_get_audio_streams_endpoint(async_client: AsyncClient, audio_test_media):
    vid_id = await _create_test_video(audio_test_media["multi_stream"], "api_streams.mkv")
    resp = await async_client.get(f"/api/v1/videos/{vid_id}/audio/streams")
    assert resp.status_code == 200
    streams = resp.json()
    assert len(streams) == 2
    assert streams[0]["codec_name"] == "aac"
    assert streams[1]["codec_name"] == "mp3"


@pytest.mark.asyncio
async def test_api_video_detail_includes_audio_asset(async_client: AsyncClient, audio_test_media):
    vid_id = await _create_test_video(audio_test_media["mp4"], "api_detail_asset.mp4")

    # Extract audio first
    await extract_and_preprocess_audio(vid_id)

    # Query video detail
    resp = await async_client.get(f"/api/v1/videos/{vid_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["audio_asset"] is not None
    assert data["audio_asset"]["codec"] == "pcm_s16le"
    assert data["audio_asset"]["sample_rate"] == 16000
    assert data["audio_asset"]["channels"] == 1
    assert data["audio_streams"] is not None
    assert len(data["audio_streams"]) >= 1


@pytest.mark.asyncio
async def test_delete_video_purges_audio_file(async_client: AsyncClient, audio_test_media):
    vid_id = await _create_test_video(audio_test_media["mp4"], "delete_audio_test.mp4")
    asset = await extract_and_preprocess_audio(vid_id)
    audio_path = Path(asset.file_path)
    assert audio_path.exists()

    # Delete with purge_files=true
    resp = await async_client.delete(f"/api/v1/videos/{vid_id}?purge_files=true")
    assert resp.status_code == 200

    # Verify physical audio file was unlinked
    assert not audio_path.exists()
