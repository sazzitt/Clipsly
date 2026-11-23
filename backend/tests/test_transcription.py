import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

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
from backend.app.models.transcript import Transcript
from backend.app.models.transcript_segment import TranscriptSegment
from backend.app.models.video import Video
from backend.app.services.queue import job_queue
from backend.app.services.transcription import (
    SUPPORTED_MODELS,
    WhisperModelManager,
    cancel_transcription,
    model_manager,
    transcribe_audio_pipeline,
)


# Mock Faster-Whisper data structures
class MockWord:
    def __init__(self, word: str, start: float, end: float, probability: float = 0.95):
        self.word = word
        self.start = start
        self.end = end
        self.probability = probability


class MockSegment:
    def __init__(self, start: float, end: float, text: str, words=None, avg_logprob=-0.2, no_speech_prob=0.01):
        self.start = start
        self.end = end
        self.text = text
        self.words = words or []
        self.avg_logprob = avg_logprob
        self.no_speech_prob = no_speech_prob


class MockInfo:
    def __init__(self, language="en", language_probability=0.98, duration=2.5):
        self.language = language
        self.language_probability = language_probability
        self.duration = duration


@pytest.fixture(scope="session")
def transcription_test_wav(tmp_path_factory):
    """Generates a valid 16kHz mono WAV audio file fixture."""
    fixture_dir = tmp_path_factory.mktemp("transcription_wav_dir")
    wav_path = fixture_dir / "test_audio_16k_mono.wav"

    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=16000:duration=2.0",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            "-y", str(wav_path),
        ],
        check=True,
    )
    return wav_path


async def _create_test_video(src_path: Path, filename: str = "test.mp4") -> str:
    vid_id = str(uuid.uuid4())
    unique_name = f"{vid_id}_{filename}"
    dest_path = settings.STORAGE_DIR / "videos" / unique_name
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if src_path.exists():
        shutil.copy2(src_path, dest_path)
    else:
        dest_path.write_bytes(b"dummy")

    async with AsyncSessionLocal() as session:
        vid = Video(
            id=vid_id,
            filename=unique_name,
            original_filename=filename,
            file_path=str(dest_path),
            file_size_bytes=dest_path.stat().st_size,
            duration_seconds=2.0,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            audio_codec="aac",
            status="READY",
            metadata_status="COMPLETED",
        )
        session.add(vid)
        await session.commit()
    return vid_id


async def _create_test_audio_asset(video_id: str, src_wav: Path, status: str = "COMPLETED") -> AudioAsset:
    dest_wav = settings.AUDIO_DIR / f"{video_id}.wav"
    dest_wav.parent.mkdir(parents=True, exist_ok=True)
    if src_wav.exists() and "missing" not in str(src_wav):
        shutil.copy2(src_wav, dest_wav)
        file_path_str = str(dest_wav)
    else:
        file_path_str = str(src_wav)

    asset_id = str(uuid.uuid4())
    asset = AudioAsset(
        id=asset_id,
        video_id=video_id,
        filename=f"{video_id}.wav",
        file_path=file_path_str,
        format="wav",
        codec="pcm_s16le",
        sample_rate=16000,
        channels=1,
        channel_layout="mono",
        bit_depth=16,
        duration_seconds=2.0,
        file_size_bytes=64000,
        source_stream_index=0,
        status=status,
    )
    async with AsyncSessionLocal() as session:
        session.add(asset)
        await session.commit()
    return asset


# ---------------------------------------------------------------------------
# 1. Model Manager Unit Tests
# ---------------------------------------------------------------------------

def test_whisper_model_manager_supported_models():
    """Verifies that model manager returns supported models catalog."""
    manager = WhisperModelManager()
    models = manager.get_supported_models()
    assert len(models) >= 3
    names = [m.model_name for m in models]
    assert "tiny" in names
    assert "base" in names
    assert "small" in names

    base_meta = next(m for m in models if m.model_name == "base")
    assert base_meta.vram_required_mb >= 500
    assert "cuda" in base_meta.devices_supported


@pytest.mark.asyncio
async def test_whisper_model_manager_resolution_unsupported_model():
    """Verifies that requesting an unsupported model raises AppException."""
    manager = WhisperModelManager()
    with pytest.raises(AppException) as exc_info:
        await manager.get_or_load_model(model_name="unsupported_huge_model")
    assert exc_info.value.error_code == "UNSUPPORTED_WHISPER_MODEL"


def test_whisper_model_manager_resolve_device_cpu():
    """Verifies CPU resolution assigns int8 compute type."""
    manager = WhisperModelManager()
    device, compute = manager.resolve_device_and_compute_type(requested_device="cpu")
    assert device == "cpu"
    assert compute in ("int8", "float32")


def test_whisper_model_manager_resolve_explicit_compute_type():
    """Verifies explicit valid compute type request is honored."""
    manager = WhisperModelManager()
    device, compute = manager.resolve_device_and_compute_type(
        requested_device="cpu",
        requested_compute_type="float32"
    )
    assert device == "cpu"
    assert compute == "float32"


@pytest.mark.asyncio
async def test_whisper_model_manager_caching_and_unloading():
    """Verifies singleton caching mechanism and explicit memory unloading."""
    manager = WhisperModelManager()

    fake_model = MagicMock()
    with patch.object(manager, "_create_whisper_model", return_value=fake_model) as mock_create:
        m1, dev1, comp1 = await manager.get_or_load_model("tiny", requested_device="cpu", requested_compute_type="int8")
        assert m1 is fake_model
        assert mock_create.call_count == 1

        # Second call with same parameters should return cached model
        m2, dev2, comp2 = await manager.get_or_load_model("tiny", requested_device="cpu", requested_compute_type="int8")
        assert m2 is fake_model
        assert mock_create.call_count == 1  # Reused from cache!

        # Unload model
        await manager.unload_model()
        assert manager._loaded_model is None
        assert manager._loaded_key is None


@pytest.mark.asyncio
async def test_whisper_model_manager_cpu_fallback_on_cuda_failure():
    """Verifies that if CUDA model creation raises an error, automatic CPU fallback is attempted."""
    manager = WhisperModelManager()
    cpu_model = MagicMock()

    def side_effect(model_name, device, compute_type, download_root):
        if device == "cuda":
            raise RuntimeError("CUDA out of memory simulation")
        return cpu_model

    with patch.object(manager, "_create_whisper_model", side_effect=side_effect):
        model, dev, comp = await manager.get_or_load_model("tiny", requested_device="cuda", requested_compute_type="float16")
        assert dev == "cpu"
        assert comp == "int8"
        assert model is cpu_model


# ---------------------------------------------------------------------------
# 2. Pipeline Error Handling & Precondition Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pipeline_missing_video_raises_not_found():
    """Verifies that transcribing a nonexistent video raises NotFoundError."""
    with pytest.raises(NotFoundError) as exc:
        await transcribe_audio_pipeline(video_id=str(uuid.uuid4()))
    assert "was not found" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_pipeline_missing_audio_asset_raises_not_found(transcription_test_wav):
    """Verifies that a video without an extracted AudioAsset raises NotFoundError."""
    video_id = await _create_test_video(transcription_test_wav, "no_audio_asset.mp4")

    with pytest.raises(NotFoundError) as exc:
        await transcribe_audio_pipeline(video_id=video_id)
    assert "No completed audio asset" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_pipeline_incomplete_audio_asset_raises_not_found(transcription_test_wav):
    """Verifies that an AudioAsset with status != COMPLETED raises NotFoundError."""
    video_id = await _create_test_video(transcription_test_wav, "pending_asset.mp4")
    await _create_test_audio_asset(video_id, transcription_test_wav, status="PROCESSING")

    with pytest.raises(NotFoundError) as exc:
        await transcribe_audio_pipeline(video_id=video_id)
    assert "No completed audio asset" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_pipeline_missing_physical_wav_file_raises_not_found(transcription_test_wav):
    """Verifies that an AudioAsset referencing a nonexistent physical file raises NotFoundError."""
    video_id = await _create_test_video(transcription_test_wav, "missing_disk.mp4")
    missing_wav = settings.AUDIO_DIR / f"missing_{video_id}.wav"
    await _create_test_audio_asset(video_id, missing_wav, status="COMPLETED")

    with pytest.raises(NotFoundError) as exc:
        await transcribe_audio_pipeline(video_id=video_id)
    assert "not found on local disk" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_pipeline_unsupported_model_raises_invalid_format(transcription_test_wav):
    """Verifies that requesting an unsupported model size raises InvalidFileFormatError."""
    video_id = await _create_test_video(transcription_test_wav, "invalid_model.mp4")
    await _create_test_audio_asset(video_id, transcription_test_wav)

    with pytest.raises(InvalidFileFormatError) as exc:
        await transcribe_audio_pipeline(video_id=video_id, model_name="gigantic_model_v9")
    assert "Unsupported Faster-Whisper model" in str(exc.value.detail)


# ---------------------------------------------------------------------------
# 3. Pipeline Execution & Persistence Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_transcribe_pipeline_success(transcription_test_wav):
    """Verifies full end-to-end transcription run with mock Whisper inference."""
    video_id = await _create_test_video(transcription_test_wav, "podcast.mp4")
    await _create_test_audio_asset(video_id, transcription_test_wav)

    job_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        job = ProcessingJob(
            id=job_id,
            video_id=video_id,
            job_type="TRANSCRIPTION",
            status="QUEUED",
            progress_percent=0.0,
            current_step="Queued",
        )
        db.add(job)
        await db.commit()

    # Mock Whisper inference
    mock_words_1 = [MockWord("Hello", 0.0, 0.4, 0.99), MockWord("world", 0.45, 0.9, 0.95)]
    mock_words_2 = [MockWord("Welcome", 1.0, 1.5, 0.97), MockWord("to", 1.55, 1.7, 0.98), MockWord("Clipsly", 1.75, 2.3, 0.94)]
    mock_segments = [
        MockSegment(0.0, 0.9, "Hello world", mock_words_1),
        MockSegment(1.0, 2.3, "Welcome to Clipsly", mock_words_2),
    ]
    mock_info = MockInfo(language="en", language_probability=0.99, duration=2.5)

    fake_model = MagicMock()
    fake_model.transcribe.return_value = (iter(mock_segments), mock_info)

    with patch.object(model_manager, "get_or_load_model", return_value=(fake_model, "cpu", "int8")):
        transcript = await transcribe_audio_pipeline(
            video_id=video_id,
            job_id=job_id,
            model_name="base",
            device="cpu",
            compute_type="int8",
        )

    assert transcript is not None
    assert transcript.video_id == video_id
    assert transcript.model_name == "base"
    assert transcript.language == "en"
    assert transcript.language_probability == 0.99
    assert transcript.full_text == "Hello world Welcome to Clipsly"
    assert transcript.word_count == 5
    assert transcript.segment_count == 2
    assert transcript.status == "COMPLETED"
    assert transcript.is_active is True

    # Verify segments in database
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(TranscriptSegment)
            .where(TranscriptSegment.transcript_id == transcript.id)
            .order_by(TranscriptSegment.segment_index.asc())
        )
        segs = res.scalars().all()
        assert len(segs) == 2
        assert segs[0].text == "Hello world"
        assert segs[0].start_ms == 0
        assert segs[0].end_ms == 900
        assert segs[1].text == "Welcome to Clipsly"
        assert segs[1].start_ms == 1000
        assert segs[1].end_ms == 2300

        # Check word-level timestamps JSON
        words = json.loads(segs[0].words_json)
        assert len(words) == 2
        assert words[0]["word"] == "Hello"
        assert words[0]["start_ms"] == 0
        assert words[0]["end_ms"] == 400

        # Check job status
        res_job = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
        j = res_job.scalar_one()
        assert j.status == "COMPLETED"
        assert j.progress_percent == 100.0


@pytest.mark.asyncio
async def test_transcribe_pipeline_silence_only(transcription_test_wav):
    """Verifies honest handling of audio containing no speech (0 segments)."""
    video_id = await _create_test_video(transcription_test_wav, "silent.mp4")
    await _create_test_audio_asset(video_id, transcription_test_wav)

    fake_model = MagicMock()
    fake_model.transcribe.return_value = (iter([]), MockInfo(language="en", duration=2.0))

    with patch.object(model_manager, "get_or_load_model", return_value=(fake_model, "cpu", "int8")):
        transcript = await transcribe_audio_pipeline(video_id=video_id, model_name="base")

    assert transcript.full_text == ""
    assert transcript.word_count == 0
    assert transcript.segment_count == 0
    assert transcript.status == "COMPLETED"


@pytest.mark.asyncio
async def test_transcribe_pipeline_concurrency_lock(transcription_test_wav):
    """Verifies that starting two simultaneous transcriptions on the same video raises ConflictError."""
    video_id = await _create_test_video(transcription_test_wav, "concurrent.mp4")
    await _create_test_audio_asset(video_id, transcription_test_wav)

    from backend.app.services.transcription import _active_transcriptions
    _active_transcriptions.add(video_id)

    try:
        with pytest.raises(ConflictError) as exc:
            await transcribe_audio_pipeline(video_id=video_id)
        assert "already active or in progress" in str(exc.value.detail)
    finally:
        _active_transcriptions.discard(video_id)


@pytest.mark.asyncio
async def test_transcribe_retranscribe_forces_new_transcript(transcription_test_wav):
    """Verifies that force_retranscribe=True deactivates prior transcript and inserts a new one."""
    video_id = await _create_test_video(transcription_test_wav, "retranscribe.mp4")
    await _create_test_audio_asset(video_id, transcription_test_wav)

    t1_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        old_t = Transcript(
            id=t1_id,
            video_id=video_id,
            model_name="tiny",
            compute_type="int8",
            device="cpu",
            language="en",
            full_text="Old transcription text",
            word_count=3,
            segment_count=1,
            status="COMPLETED",
            is_active=True,
        )
        db.add(old_t)
        await db.commit()

    mock_segments = [MockSegment(0.0, 1.0, "New refined text", [])]
    fake_model = MagicMock()
    fake_model.transcribe.return_value = (iter(mock_segments), MockInfo(language="en", duration=1.0))

    with patch.object(model_manager, "get_or_load_model", return_value=(fake_model, "cpu", "int8")):
        new_t = await transcribe_audio_pipeline(video_id=video_id, force_retranscribe=True)

    assert new_t.id != t1_id
    assert new_t.is_active is True
    assert new_t.full_text == "New refined text"

    # Verify old transcript is now deactivated
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Transcript).where(Transcript.id == t1_id))
        old = res.scalar_one()
        assert old.is_active is False


@pytest.mark.asyncio
async def test_transcribe_pipeline_cancellation(transcription_test_wav):
    """Verifies cooperative cancellation sets status CANCELLED and unlinks incomplete record."""
    video_id = await _create_test_video(transcription_test_wav, "cancel_pipeline.mp4")
    await _create_test_audio_asset(video_id, transcription_test_wav)

    job_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        job = ProcessingJob(
            id=job_id,
            video_id=video_id,
            job_type="TRANSCRIPTION",
            status="PROCESSING",
            progress_percent=20.0,
            current_step="Processing segments...",
        )
        db.add(job)
        await db.commit()

    from backend.app.services.transcription import _cancelled_jobs

    def slow_generator():
        for i in range(10):
            if i == 2:
                _cancelled_jobs.add(job_id)
            yield MockSegment(float(i), float(i + 1), f"Segment {i}", [])

    fake_model = MagicMock()
    fake_model.transcribe.return_value = (slow_generator(), MockInfo(language="en", duration=10.0))

    with patch.object(model_manager, "get_or_load_model", return_value=(fake_model, "cpu", "int8")):
        with pytest.raises(asyncio.CancelledError):
            await transcribe_audio_pipeline(video_id=video_id, job_id=job_id)

    # Verify job marked CANCELLED in database
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
        j = res.scalar_one()
        assert j.status == "CANCELLED"


# ---------------------------------------------------------------------------
# 4. REST API Endpoint Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_get_models(async_client: AsyncClient):
    """Verifies GET /api/v1/transcripts/models returns hardware catalog."""
    res = await async_client.get("/api/v1/transcripts/models")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert len(data["models"]) >= 3
    assert data["default_model"] in ("base", "tiny", "small")
    assert isinstance(data["cuda_available"], bool)
    assert isinstance(data["cpu_compute_types"], list)
    assert "int8" in data["cpu_compute_types"]


@pytest.mark.asyncio
async def test_api_transcribe_video_endpoint_prerequisite_validation(async_client: AsyncClient, transcription_test_wav):
    """Verifies POST /api/v1/videos/{video_id}/transcribe rejects missing audio asset with 404."""
    video_id = await _create_test_video(transcription_test_wav, "no_audio.mp4")

    res = await async_client.post(f"/api/v1/videos/{video_id}/transcribe", json={})
    assert res.status_code == 404
    assert "No completed audio asset found" in res.json()["detail"]


@pytest.mark.asyncio
async def test_api_transcribe_video_endpoint_success(async_client: AsyncClient, transcription_test_wav):
    """Verifies POST /api/v1/videos/{video_id}/transcribe queues job and returns 202."""
    video_id = await _create_test_video(transcription_test_wav, "ready.mp4")
    await _create_test_audio_asset(video_id, transcription_test_wav)

    with patch.object(job_queue, "submit_job", return_value="test_job"):
        res = await async_client.post(
            f"/api/v1/videos/{video_id}/transcribe",
            json={"model_name": "base", "vad_filter": True}
        )

    assert res.status_code == 202
    data = res.json()
    assert data["status"] == "QUEUED"
    assert data["video_id"] == video_id
    assert "job_id" in data


@pytest.mark.asyncio
async def test_api_transcribe_conflict_when_already_active(async_client: AsyncClient, transcription_test_wav):
    """Verifies POST /api/v1/videos/{video_id}/transcribe returns 409 Conflict if already in queue."""
    video_id = await _create_test_video(transcription_test_wav, "active.mp4")
    await _create_test_audio_asset(video_id, transcription_test_wav)

    with patch.object(job_queue, "is_video_active", return_value=True):
        res = await async_client.post(f"/api/v1/videos/{video_id}/transcribe", json={})
        assert res.status_code == 409
        assert "already queued or active" in res.json()["detail"]


@pytest.mark.asyncio
async def test_api_get_transcript_and_segments(async_client: AsyncClient, transcription_test_wav):
    """Verifies GET /transcripts/{id} and GET /transcripts/{id}/segments."""
    video_id = await _create_test_video(transcription_test_wav, "with_transcript.mp4")
    t_id = str(uuid.uuid4())
    seg_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as db:
        t = Transcript(
            id=t_id,
            video_id=video_id,
            model_name="base",
            compute_type="float16",
            device="cuda",
            language="en",
            language_probability=0.97,
            status="COMPLETED",
            full_text="Test dialogue segment.",
            word_count=3,
            segment_count=1,
            is_active=True,
        )
        db.add(t)
        words_data = [
            {"word": "Test", "start_ms": 0, "end_ms": 400, "probability": 0.99},
            {"word": "dialogue", "start_ms": 450, "end_ms": 800, "probability": 0.95},
            {"word": "segment.", "start_ms": 850, "end_ms": 1200, "probability": 0.98},
        ]
        s = TranscriptSegment(
            id=seg_id,
            transcript_id=t_id,
            segment_index=0,
            start_ms=0,
            end_ms=1200,
            text="Test dialogue segment.",
            words_json=json.dumps(words_data),
            avg_confidence=0.97,
        )
        db.add(s)
        await db.commit()

    # 1. GET by transcript_id
    res_t = await async_client.get(f"/api/v1/transcripts/{t_id}")
    assert res_t.status_code == 200
    assert res_t.json()["id"] == t_id
    assert res_t.json()["full_text"] == "Test dialogue segment."

    # 2. GET by video_id
    res_v = await async_client.get(f"/api/v1/videos/{video_id}/transcript")
    assert res_v.status_code == 200
    assert res_v.json()["id"] == t_id

    # 3. GET segments paginated
    res_segs = await async_client.get(f"/api/v1/transcripts/{t_id}/segments?limit=10&offset=0")
    assert res_segs.status_code == 200
    seg_data = res_segs.json()
    assert seg_data["total"] == 1
    assert len(seg_data["segments"]) == 1
    assert seg_data["segments"][0]["id"] == seg_id
    assert len(seg_data["segments"][0]["words"]) == 3
    assert seg_data["segments"][0]["words"][0]["word"] == "Test"


@pytest.mark.asyncio
async def test_api_patch_segment_text(async_client: AsyncClient, transcription_test_wav):
    """Verifies PATCH /transcripts/{id}/segments/{seg_id} updates segment text."""
    video_id = await _create_test_video(transcription_test_wav, "edit_seg.mp4")
    t_id = str(uuid.uuid4())
    seg_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as db:
        t = Transcript(id=t_id, video_id=video_id, model_name="base", compute_type="float16", language="en", full_text="Original text", word_count=2, segment_count=1, is_active=True)
        db.add(t)
        s = TranscriptSegment(id=seg_id, transcript_id=t_id, segment_index=0, start_ms=0, end_ms=1000, text="Original text", words_json=json.dumps([]))
        db.add(s)
        await db.commit()

    res = await async_client.patch(
        f"/api/v1/transcripts/{t_id}/segments/{seg_id}",
        json={"text": "Corrected transcript text."}
    )
    assert res.status_code == 200
    assert res.json()["text"] == "Corrected transcript text."

    # Verify database update
    async with AsyncSessionLocal() as db:
        s_db = await db.get(TranscriptSegment, seg_id)
        assert s_db.text == "Corrected transcript text."


@pytest.mark.asyncio
async def test_api_delegating_transcribe_endpoint(async_client: AsyncClient, transcription_test_wav):
    """Verifies POST /api/v1/transcripts/transcribe delegates cleanly with 202."""
    video_id = await _create_test_video(transcription_test_wav, "delegate.mp4")
    await _create_test_audio_asset(video_id, transcription_test_wav)

    with patch.object(job_queue, "submit_job", return_value="test_job"):
        res = await async_client.post(
            "/api/v1/transcripts/transcribe",
            json={"video_id": video_id, "model_name": "base"}
        )
    assert res.status_code == 202
    assert res.json()["video_id"] == video_id


@pytest.mark.asyncio
async def test_api_path_privacy_no_internal_paths_in_response(async_client: AsyncClient, transcription_test_wav):
    """Verifies transcript responses do not leak host absolute or filesystem paths."""
    video_id = await _create_test_video(transcription_test_wav, "video_priv.mp4")
    t_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as db:
        t = Transcript(id=t_id, video_id=video_id, model_name="base", compute_type="float16", language="en", full_text="Privacy text", word_count=2, segment_count=1, is_active=True)
        db.add(t)
        await db.commit()

    res = await async_client.get(f"/api/v1/transcripts/{t_id}")
    assert res.status_code == 200
    res_str = res.text
    assert "C:\\" not in res_str
    assert "storage_path" not in res_str


@pytest.mark.asyncio
async def test_cascade_delete_video_purges_transcripts(async_client: AsyncClient, transcription_test_wav):
    """Verifies deleting a video cascades and removes associated transcripts and segments."""
    video_id = await _create_test_video(transcription_test_wav, "cascade_t.mp4")
    t_id = str(uuid.uuid4())
    seg_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as db:
        t = Transcript(id=t_id, video_id=video_id, model_name="base", compute_type="float16", language="en", full_text="Cascade text", word_count=2, segment_count=1, is_active=True)
        db.add(t)
        s = TranscriptSegment(id=seg_id, transcript_id=t_id, segment_index=0, start_ms=0, end_ms=1000, text="Cascade text", words_json=json.dumps([]))
        db.add(s)
        await db.commit()

    # Delete video
    del_res = await async_client.delete(f"/api/v1/videos/{video_id}?purge_files=false")
    assert del_res.status_code == 200

    # Verify transcript and segment are deleted
    async with AsyncSessionLocal() as db:
        t_check = await db.get(Transcript, t_id)
        assert t_check is None
        s_check = await db.get(TranscriptSegment, seg_id)
        assert s_check is None


def test_vad_options_defaults():
    """Verifies Silero VAD parameters are configured to production standards."""
    assert settings.VAD_ENABLED is True
    assert 0.0 < settings.VAD_THRESHOLD < 1.0
    assert settings.VAD_MIN_SPEECH_DURATION_MS >= 100
    assert settings.VAD_MIN_SILENCE_DURATION_MS >= 100
    assert settings.VAD_SPEECH_PAD_MS >= 50


@pytest.mark.asyncio
async def test_job_queue_transcription_integration(transcription_test_wav):
    """Verifies sequential queue submits and executes transcription task."""
    video_id = await _create_test_video(transcription_test_wav, "queue_test.mp4")
    await _create_test_audio_asset(video_id, transcription_test_wav)

    job_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        job = ProcessingJob(
            id=job_id,
            video_id=video_id,
            job_type="TRANSCRIPTION",
            status="QUEUED",
            progress_percent=0.0,
            current_step="Queued",
        )
        db.add(job)
        await db.commit()

    called = False

    async def fake_handler(**kwargs):
        nonlocal called
        called = True

    await job_queue.submit_job(
        job_id=job_id,
        video_id=video_id,
        handler=fake_handler,
        job_kwargs={"video_id": video_id, "job_id": job_id},
    )

    # Wait for queue worker to execute
    await asyncio.sleep(0.3)
    assert called is True


@pytest.mark.asyncio
async def test_api_get_segments_pagination_limit_and_offset(async_client: AsyncClient, transcription_test_wav):
    """Verifies pagination offset and limit parameters on GET /transcripts/{id}/segments."""
    video_id = await _create_test_video(transcription_test_wav, "paginate.mp4")
    t_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as db:
        t = Transcript(id=t_id, video_id=video_id, model_name="base", compute_type="float16", language="en", full_text="One Two Three Four", word_count=4, segment_count=4, is_active=True)
        db.add(t)
        for i in range(4):
            s = TranscriptSegment(
                id=str(uuid.uuid4()),
                transcript_id=t_id,
                segment_index=i,
                start_ms=i * 1000,
                end_ms=(i + 1) * 1000,
                text=f"Segment #{i}",
                words_json=json.dumps([]),
                avg_confidence=0.95,
            )
            db.add(s)
        await db.commit()

    # Query offset=1, limit=2
    res = await async_client.get(f"/api/v1/transcripts/{t_id}/segments?offset=1&limit=2")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 4
    assert data["offset"] == 1
    assert data["limit"] == 2
    assert len(data["segments"]) == 2
    assert data["segments"][0]["segment_index"] == 1
    assert data["segments"][1]["segment_index"] == 2


@pytest.mark.asyncio
async def test_api_patch_segment_nonexistent_returns_404(async_client: AsyncClient):
    """Verifies PATCH on nonexistent transcript or segment returns 404."""
    fake_tid = str(uuid.uuid4())
    fake_sid = str(uuid.uuid4())
    res = await async_client.patch(
        f"/api/v1/transcripts/{fake_tid}/segments/{fake_sid}",
        json={"text": "Hello"}
    )
    assert res.status_code == 404
    assert "was not found" in res.json()["detail"]


@pytest.mark.asyncio
async def test_api_get_transcript_nonexistent_video_returns_404(async_client: AsyncClient):
    """Verifies GET /videos/{id}/transcript returns 404 if video has no active transcript."""
    fake_vid = str(uuid.uuid4())
    res = await async_client.get(f"/api/v1/videos/{fake_vid}/transcript")
    assert res.status_code == 404
    assert "No active transcript found" in res.json()["detail"]


@pytest.mark.asyncio
async def test_api_get_segments_nonexistent_transcript_returns_404(async_client: AsyncClient):
    """Verifies GET /transcripts/{id}/segments returns 404 if transcript does not exist."""
    fake_tid = str(uuid.uuid4())
    res = await async_client.get(f"/api/v1/transcripts/{fake_tid}/segments")
    assert res.status_code == 404
    assert "was not found" in res.json()["detail"]

