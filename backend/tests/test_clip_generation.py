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
    ValidationError,
)
from backend.app.models.clip import Clip
from backend.app.models.processing_job import ProcessingJob
from backend.app.models.video import Video
from backend.app.services.clip_generation import (
    ConversionMode,
    build_filtergraph,
    cancel_clip_generation,
    check_nvenc_hardware_support,
    execute_clip_generation,
    get_filter_args,
    get_video_encoder_args,
    normalize_conversion_mode,
    set_nvenc_availability_for_testing,
    validate_clip_output,
)
from backend.app.services.queue import job_queue


@pytest.fixture(scope="session")
def clip_test_media(tmp_path_factory):
    """Generates real MP4 media fixtures using local FFmpeg for clip generation tests."""
    fixture_dir = tmp_path_factory.mktemp("clip_test_media")
    sample_mp4 = fixture_dir / "source_video.mp4"
    sample_no_audio = fixture_dir / "source_no_audio.mp4"

    # 1. 10.0s 1280x720 MP4 with stereo AAC audio
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=10.0:size=1280x720:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=10.0",
            "-ac", "2",
            "-c:v", "libx264", "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            "-y", str(sample_mp4),
        ],
        check=True,
    )

    # 2. 8.0s 1280x720 MP4 without audio
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=8.0:size=1280x720:rate=30",
            "-an",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-y", str(sample_no_audio),
        ],
        check=True,
    )

    return {
        "with_audio": sample_mp4,
        "no_audio": sample_no_audio,
    }


# ============================================================================
# 1. Conversion Mode Normalization Tests
# ============================================================================

def test_normalize_conversion_mode_aliases():
    """Verifies that all mode variations and aliases resolve to standard enums."""
    assert normalize_conversion_mode("BLUR_PAD") == ConversionMode.BLUR_PAD.value
    assert normalize_conversion_mode("BLURRED_BACKGROUND") == ConversionMode.BLUR_PAD.value
    assert normalize_conversion_mode("blur") == ConversionMode.BLUR_PAD.value
    assert normalize_conversion_mode("BLURRED") == ConversionMode.BLUR_PAD.value

    assert normalize_conversion_mode("CROP_CENTER") == ConversionMode.CROP_CENTER.value
    assert normalize_conversion_mode("CENTER_CROP") == ConversionMode.CROP_CENTER.value
    assert normalize_conversion_mode("crop") == ConversionMode.CROP_CENTER.value

    assert normalize_conversion_mode("FIT_LETTERBOX") == ConversionMode.FIT_LETTERBOX.value
    assert normalize_conversion_mode("FIT_WITH_BACKGROUND") == ConversionMode.FIT_LETTERBOX.value
    assert normalize_conversion_mode("letterbox") == ConversionMode.FIT_LETTERBOX.value
    assert normalize_conversion_mode("fit") == ConversionMode.FIT_LETTERBOX.value

    assert normalize_conversion_mode(None) == ConversionMode.BLUR_PAD.value
    assert normalize_conversion_mode("") == ConversionMode.BLUR_PAD.value
    assert normalize_conversion_mode("UNKNOWN_MODE") == ConversionMode.BLUR_PAD.value


# ============================================================================
# 2. Filtergraph Generation Tests
# ============================================================================

def test_build_filtergraph_blur_pad():
    """Mode A: Verifies blurred background filter includes boxblur, overlay, and 1080x1920 scaling."""
    fg, label = build_filtergraph("BLUR_PAD", target_width=1080, target_height=1920)
    assert label == "[outv]"
    assert "boxblur=25:5" in fg
    assert "scale=1080:1920:force_original_aspect_ratio=increase" in fg
    assert "scale=1080:1920:force_original_aspect_ratio=decrease" in fg
    assert "overlay=(W-w)/2:(H-h)/2" in fg
    assert "setsar=1" in fg


def test_build_filtergraph_crop_center():
    """Mode B: Verifies center crop filter scales and crops central 1080x1920."""
    fg, label = build_filtergraph("CROP_CENTER", target_width=1080, target_height=1920)
    assert label == "[outv]"
    assert "scale=1080:1920:force_original_aspect_ratio=increase" in fg
    assert "crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2" in fg
    assert "setsar=1" in fg


def test_build_filtergraph_fit_letterbox():
    """Mode C: Verifies letterbox fit scales to bounds and pads with black background."""
    fg, label = build_filtergraph("FIT_LETTERBOX", target_width=1080, target_height=1920, background_color="black")
    assert label == "[outv]"
    assert "scale=1080:1920:force_original_aspect_ratio=decrease" in fg
    assert "pad=1080:1920:(1080-iw)/2:(1920-ih)/2:color=black" in fg
    assert "setsar=1" in fg


def test_get_filter_args():
    """Verifies CLI filter arguments array structure."""
    args = get_filter_args("BLUR_PAD", 1080, 1920)
    assert args[0] == "-filter_complex"
    assert "boxblur" in args[1]
    assert args[2] == "-map"
    assert args[3] == "[outv]"


# ============================================================================
# 3. NVENC & Encoder Selection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_nvenc_hardware_probe():
    """Verifies that NVENC hardware probe executes and returns a boolean."""
    supported = await check_nvenc_hardware_support()
    assert isinstance(supported, bool)


@pytest.mark.asyncio
async def test_encoder_args_forced_cpu():
    """Verifies that force_cpu=True always returns libx264 with appropriate flags."""
    backend_name, args = await get_video_encoder_args(target_fps=30.0, crf=22, force_cpu=True)
    assert backend_name == "libx264"
    assert "-c:v" in args
    assert "libx264" in args
    assert "-pix_fmt" in args
    assert "yuv420p" in args


@pytest.mark.asyncio
async def test_encoder_args_nvenc_fallback():
    """Verifies that when NVENC is mocked as available, h264_nvenc args are returned."""
    try:
        set_nvenc_availability_for_testing(True)
        backend_name, args = await get_video_encoder_args(target_fps=30.0, force_cpu=False)
        assert backend_name == "h264_nvenc"
        assert "h264_nvenc" in args
        assert "-preset" in args
        assert "p4" in args
    finally:
        set_nvenc_availability_for_testing(None)


# ============================================================================
# 4. Output Validation (FFprobe) Tests
# ============================================================================

@pytest.mark.asyncio
async def test_validate_clip_output_file_missing(tmp_path):
    """Probing nonexistent file returns valid=False."""
    missing = tmp_path / "nonexistent.mp4"
    res = await validate_clip_output(missing, expected_duration_seconds=5.0)
    assert not res.valid
    assert "does not exist" in res.error_message


@pytest.mark.asyncio
async def test_validate_clip_output_file_empty(tmp_path):
    """Probing 0-byte file returns valid=False."""
    empty = tmp_path / "empty.mp4"
    empty.touch()
    res = await validate_clip_output(empty, expected_duration_seconds=5.0)
    assert not res.valid
    assert "0 bytes" in res.error_message


@pytest.mark.asyncio
async def test_validate_clip_output_dimension_mismatch(clip_test_media):
    """Probing 1280x720 video when expecting 1080x1920 returns valid=False."""
    src = clip_test_media["with_audio"]
    res = await validate_clip_output(src, expected_duration_seconds=10.0, expected_width=1080, expected_height=1920)
    assert not res.valid
    assert "dimensions" in res.error_message


@pytest.mark.asyncio
async def test_validate_clip_output_real_fixture(clip_test_media):
    """Probing 1280x720 video with correct expected dimensions returns valid=True."""
    src = clip_test_media["with_audio"]
    res = await validate_clip_output(
        src,
        expected_duration_seconds=10.0,
        expected_width=1280,
        expected_height=720,
        source_has_audio=True,
    )
    assert res.valid
    assert res.width == 1280
    assert res.height == 720
    assert res.file_size_bytes > 0
    assert res.video_codec in ("h264", "avc1")
    assert res.audio_codec == "aac"


@pytest.mark.asyncio
async def test_validate_clip_output_audio_presence_check(clip_test_media):
    """Fails if source expected audio but none is present."""
    no_audio_src = clip_test_media["no_audio"]
    res = await validate_clip_output(
        no_audio_src,
        expected_duration_seconds=8.0,
        expected_width=1280,
        expected_height=720,
        source_has_audio=True,  # Expect audio
    )
    assert not res.valid
    assert "no audio stream was found" in res.error_message


@pytest.mark.asyncio
async def test_validate_clip_output_no_audio_allowed(clip_test_media):
    """Passes if source had no audio and output has no audio."""
    no_audio_src = clip_test_media["no_audio"]
    res = await validate_clip_output(
        no_audio_src,
        expected_duration_seconds=8.0,
        expected_width=1280,
        expected_height=720,
        source_has_audio=False,  # No audio expected
    )
    assert res.valid
    assert res.audio_codec is None


# ============================================================================
# 5. REST API & End-to-End Generation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_api_create_clip_draft_and_validation(async_client: AsyncClient):
    """Verifies POST /api/v1/clips creates draft and enforces bounds."""
    # Create source video in DB
    v_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        v = Video(
            id=v_id,
            filename=f"{v_id}.mp4",
            original_filename="source.mp4",
            file_path=f"data/uploads/{v_id}.mp4",
            file_size_bytes=1000000,
            duration_seconds=30.0,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            audio_codec="aac",
            status="READY",
        )
        session.add(v)
        await session.commit()

    # Timing validation error
    bad_res = await async_client.post(
        "/api/v1/clips",
        json={"video_id": v_id, "start_ms": 5000, "end_ms": 6000},  # 1s duration < 5s
    )
    assert bad_res.status_code == 422

    # Valid creation
    ok_res = await async_client.post(
        "/api/v1/clips",
        json={"video_id": v_id, "title": "My Highlight Clip", "start_ms": 2000, "end_ms": 12000},
    )
    assert ok_res.status_code == 201
    clip_id = ok_res.json()["id"]
    assert ok_res.json()["status"] == "DRAFT"
    assert ok_res.json()["duration_ms"] == 10000

    # Clean up
    del_res = await async_client.delete(f"/api/v1/clips/{clip_id}")
    assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_api_generate_clip_nonexistent_video(async_client: AsyncClient):
    """POST /api/v1/clips/generate returns 404 for unknown video."""
    res = await async_client.post(
        "/api/v1/clips/generate",
        json={"video_id": str(uuid.uuid4()), "start_ms": 0, "end_ms": 6000},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_api_generate_clip_validation_timing(async_client: AsyncClient):
    """POST /api/v1/clips/generate validates start_ms < end_ms and duration >= 5000ms."""
    res = await async_client.post(
        "/api/v1/clips/generate",
        json={"video_id": str(uuid.uuid4()), "start_ms": 5000, "end_ms": 2000},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_api_generate_clip_real_blurred_background(clip_test_media, tmp_path, async_client: AsyncClient):
    """End-to-end test: generates a real 9:16 vertical clip with blurred background (Mode A)."""
    v_id = str(uuid.uuid4())
    src = tmp_path / f"{v_id}.mp4"
    shutil.copy(clip_test_media["with_audio"], src)

    async with AsyncSessionLocal() as session:
        v = Video(
            id=v_id,
            filename=src.name,
            original_filename="source_video.mp4",
            file_path=str(src),
            file_size_bytes=src.stat().st_size,
            duration_seconds=10.0,
            width=1280,
            height=720,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            audio_codec="aac",
            status="READY",
        )
        session.add(v)
        await session.commit()

    # Request clip generation: 1.0s to 7.0s (6.0s duration)
    gen_res = await async_client.post(
        "/api/v1/clips/generate",
        json={
            "video_id": v_id,
            "title": "Blurred Background Test Clip",
            "start_ms": 1000,
            "end_ms": 7000,
            "conversion_mode": "BLUR_PAD",
            "force_cpu": True,
        },
    )
    assert gen_res.status_code == 202
    data = gen_res.json()
    clip_id = data["clip_id"]
    job_id = data["job_id"]

    # Wait for sequential worker to process job
    for _ in range(60):
        await asyncio.sleep(0.5)
        async with AsyncSessionLocal() as session:
            job = await session.get(ProcessingJob, job_id)
            if job and job.status in ("COMPLETED", "FAILED"):
                break

    async with AsyncSessionLocal() as session:
        job = await session.get(ProcessingJob, job_id)
        clip = await session.get(Clip, clip_id)

    assert job is not None
    assert job.status == "COMPLETED", f"Job failed: {job.error_message}"
    assert clip is not None
    assert clip.status == "COMPLETED"
    assert clip.width == 1080
    assert clip.height == 1920
    assert clip.output_path is not None
    assert Path(clip.output_path).exists()
    assert clip.file_size_bytes > 0
    assert clip.conversion_mode == "BLUR_PAD"
    assert clip.audio_codec == "aac"

    # Verify streaming 200 OK
    stream_res = await async_client.get(f"/api/v1/clips/{clip_id}/stream")
    assert stream_res.status_code == 200
    assert stream_res.headers["Content-Type"] == "video/mp4"
    assert stream_res.headers["Accept-Ranges"] == "bytes"

    # Verify streaming partial range 206 Partial Content
    range_res = await async_client.get(
        f"/api/v1/clips/{clip_id}/stream",
        headers={"Range": "bytes=0-511"},
    )
    assert range_res.status_code == 206
    assert "bytes 0-511/" in range_res.headers["Content-Range"]
    assert len(range_res.content) == 512

    # Verify download attachment
    down_res = await async_client.get(f"/api/v1/clips/{clip_id}/download")
    assert down_res.status_code == 200
    assert "attachment" in down_res.headers.get("content-disposition", "")

    # Clean up clip
    del_res = await async_client.delete(f"/api/v1/clips/{clip_id}")
    assert del_res.status_code == 200
    assert not Path(clip.output_path).exists()


@pytest.mark.asyncio
async def test_api_generate_clip_center_crop_mode(clip_test_media, tmp_path, async_client: AsyncClient):
    """End-to-end test: generates a real 9:16 vertical clip with center crop (Mode B)."""
    v_id = str(uuid.uuid4())
    src = tmp_path / f"{v_id}.mp4"
    shutil.copy(clip_test_media["with_audio"], src)

    async with AsyncSessionLocal() as session:
        v = Video(
            id=v_id,
            filename=src.name,
            original_filename="source_video.mp4",
            file_path=str(src),
            file_size_bytes=src.stat().st_size,
            duration_seconds=10.0,
            width=1280,
            height=720,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            audio_codec="aac",
            status="READY",
        )
        session.add(v)
        await session.commit()

    gen_res = await async_client.post(
        "/api/v1/clips/generate",
        json={
            "video_id": v_id,
            "title": "Center Crop Test Clip",
            "start_ms": 0,
            "end_ms": 5500,
            "conversion_mode": "CROP_CENTER",
            "force_cpu": True,
        },
    )
    assert gen_res.status_code == 202
    clip_id = gen_res.json()["clip_id"]
    job_id = gen_res.json()["job_id"]

    for _ in range(60):
        await asyncio.sleep(0.5)
        async with AsyncSessionLocal() as session:
            job = await session.get(ProcessingJob, job_id)
            if job and job.status in ("COMPLETED", "FAILED"):
                break

    async with AsyncSessionLocal() as session:
        clip = await session.get(Clip, clip_id)

    assert clip is not None
    assert clip.status == "COMPLETED"
    assert clip.width == 1080
    assert clip.height == 1920
    assert clip.conversion_mode == "CROP_CENTER"

    # Delete clip
    await async_client.delete(f"/api/v1/clips/{clip_id}")


@pytest.mark.asyncio
async def test_api_generate_clip_fit_letterbox_mode(clip_test_media, tmp_path, async_client: AsyncClient):
    """End-to-end test: generates a real 9:16 vertical clip with fit letterbox (Mode C)."""
    v_id = str(uuid.uuid4())
    src = tmp_path / f"{v_id}.mp4"
    shutil.copy(clip_test_media["no_audio"], src)

    async with AsyncSessionLocal() as session:
        v = Video(
            id=v_id,
            filename=src.name,
            original_filename="source_no_audio.mp4",
            file_path=str(src),
            file_size_bytes=src.stat().st_size,
            duration_seconds=8.0,
            width=1280,
            height=720,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            status="READY",
        )
        session.add(v)
        await session.commit()

    gen_res = await async_client.post(
        "/api/v1/clips/generate",
        json={
            "video_id": v_id,
            "title": "Fit Letterbox Test Clip",
            "start_ms": 1000,
            "end_ms": 6500,
            "conversion_mode": "FIT_LETTERBOX",
            "force_cpu": True,
        },
    )
    assert gen_res.status_code == 202
    clip_id = gen_res.json()["clip_id"]
    job_id = gen_res.json()["job_id"]

    for _ in range(60):
        await asyncio.sleep(0.5)
        async with AsyncSessionLocal() as session:
            job = await session.get(ProcessingJob, job_id)
            if job and job.status in ("COMPLETED", "FAILED"):
                break

    async with AsyncSessionLocal() as session:
        clip = await session.get(Clip, clip_id)

    assert clip is not None
    assert clip.status == "COMPLETED"
    assert clip.width == 1080
    assert clip.height == 1920
    assert clip.conversion_mode == "FIT_LETTERBOX"

    # Delete clip
    await async_client.delete(f"/api/v1/clips/{clip_id}")


@pytest.mark.asyncio
async def test_api_cancel_clip_generation(clip_test_media, tmp_path, async_client: AsyncClient):
    """Verifies that POST /api/v1/clips/{id}/cancel cancels queued or executing clip."""
    v_id = str(uuid.uuid4())
    src = tmp_path / f"{v_id}.mp4"
    shutil.copy(clip_test_media["with_audio"], src)

    async with AsyncSessionLocal() as session:
        v = Video(
            id=v_id,
            filename=src.name,
            original_filename="source_video.mp4",
            file_path=str(src),
            file_size_bytes=src.stat().st_size,
            duration_seconds=10.0,
            width=1280,
            height=720,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            status="READY",
        )
        session.add(v)
        await session.commit()

    gen_res = await async_client.post(
        "/api/v1/clips/generate",
        json={
            "video_id": v_id,
            "title": "To Be Cancelled",
            "start_ms": 0,
            "end_ms": 8000,
            "force_cpu": True,
        },
    )
    assert gen_res.status_code == 202
    clip_id = gen_res.json()["clip_id"]

    # Cancel immediately
    cancel_res = await async_client.post(f"/api/v1/clips/{clip_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # Verify clip status is CANCELLED
    async with AsyncSessionLocal() as session:
        clip = await session.get(Clip, clip_id)
    assert clip.status == "CANCELLED"


@pytest.mark.asyncio
async def test_api_list_and_filter_clips(async_client: AsyncClient):
    """Verifies listing clips with status, search, and video_id filters."""
    v_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        v = Video(
            id=v_id,
            filename=f"{v_id}.mp4",
            original_filename="search_test.mp4",
            file_path=f"data/uploads/{v_id}.mp4",
            file_size_bytes=1000000,
            duration_seconds=30.0,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            status="READY",
        )
        session.add(v)

        c1 = Clip(
            video_id=v_id,
            title="Searchable Alpha Clip",
            start_ms=1000,
            end_ms=7000,
            duration_ms=6000,
            status="COMPLETED",
        )
        c2 = Clip(
            video_id=v_id,
            title="Searchable Beta Clip",
            start_ms=2000,
            end_ms=8000,
            duration_ms=6000,
            status="DRAFT",
        )
        session.add_all([c1, c2])
        await session.commit()

    # Filter by search
    res = await async_client.get("/api/v1/clips", params={"search": "Alpha"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert any("Alpha" in item["title"] for item in items)
    assert not any("Beta" in item["title"] for item in items)

    # Filter by status
    res = await async_client.get("/api/v1/clips", params={"status": "DRAFT"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert all(item["status"] == "DRAFT" for item in items)

    # Filter by video_id
    res = await async_client.get("/api/v1/clips", params={"video_id": v_id})
    assert res.status_code == 200
    assert res.json()["total"] >= 2


def test_build_filtergraph_custom_dimensions():
    """Verifies that custom dimensions (e.g. 720x1280) are properly formatted in filters."""
    fg, label = build_filtergraph("CROP_CENTER", target_width=720, target_height=1280)
    assert label == "[outv]"
    assert "scale=720:1280" in fg
    assert "crop=720:1280" in fg


@pytest.mark.asyncio
async def test_validate_clip_output_corrupted_file(tmp_path):
    """Probing non-video junk data returns valid=False with error message."""
    junk = tmp_path / "corrupt.mp4"
    junk.write_bytes(b"NOT A VALID MP4 FILE AT ALL JUST RANDOM BYTES 1234567890")
    res = await validate_clip_output(junk, expected_duration_seconds=5.0)
    assert not res.valid
    assert "FFprobe failed" in res.error_message


@pytest.mark.asyncio
async def test_api_stream_clip_not_found(async_client: AsyncClient):
    """GET /api/v1/clips/{id}/stream returns 404 for unknown clip."""
    res = await async_client.get(f"/api/v1/clips/{uuid.uuid4()}/stream")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_api_stream_clip_no_output_path(async_client: AsyncClient):
    """GET /api/v1/clips/{id}/stream returns 404 if clip is not yet completed."""
    v_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        v = Video(
            id=v_id,
            filename=f"{v_id}.mp4",
            original_filename="draft.mp4",
            file_path=f"data/uploads/{v_id}.mp4",
            file_size_bytes=1000,
            duration_seconds=10.0,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            status="READY",
        )
        c = Clip(
            video_id=v_id,
            title="Unrendered Draft",
            start_ms=0,
            end_ms=6000,
            duration_ms=6000,
            status="DRAFT",
            output_path=None,
        )
        session.add_all([v, c])
        await session.commit()
        clip_id = c.id

    res = await async_client.get(f"/api/v1/clips/{clip_id}/stream")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_api_download_clip_not_found(async_client: AsyncClient):
    """GET /api/v1/clips/{id}/download returns 404 for unknown clip."""
    res = await async_client.get(f"/api/v1/clips/{uuid.uuid4()}/download")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_api_delete_clip_nonexistent(async_client: AsyncClient):
    """DELETE /api/v1/clips/{id} returns 404 for nonexistent clip."""
    res = await async_client.delete(f"/api/v1/clips/{uuid.uuid4()}")
    assert res.status_code == 404

