import asyncio
import gc
import json
import logging
import math
import os
from pathlib import Path
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import AsyncSessionLocal
from backend.app.core.exceptions import (
    AppException,
    ConflictError,
    InsufficientStorageError,
    InvalidFileFormatError,
    NotFoundError,
)
from backend.app.models.audio_asset import AudioAsset
from backend.app.models.processing_job import ProcessingJob
from backend.app.models.transcript import Transcript
from backend.app.models.transcript_segment import TranscriptSegment
from backend.app.models.video import Video
from backend.app.schemas.transcript import ModelOptionInfo
from backend.app.services.system import check_cuda_available, get_hardware_telemetry

logger = logging.getLogger("clipsly.transcription")

# Supported Faster-Whisper model catalog with resource specifications
SUPPORTED_MODELS: Dict[str, Dict[str, Any]] = {
    "tiny": {
        "description": "Ultra-lightweight 39M parameter model. Fast transcription, minimal memory usage.",
        "parameters": "39M",
        "vram_required_mb": 500,
        "recommended_for": "Low-resource environments, fast testing, speech alignment",
        "devices_supported": ["cuda", "cpu"],
    },
    "base": {
        "description": "Standard 74M parameter model. Excellent balance of speed, accuracy, and VRAM efficiency.",
        "parameters": "74M",
        "vram_required_mb": 1000,
        "recommended_for": "Default candidate for workstation (RTX 3050 4GB VRAM)",
        "devices_supported": ["cuda", "cpu"],
    },
    "small": {
        "description": "High-accuracy 244M parameter model. Enhanced vocabulary and punctuation handling.",
        "parameters": "244M",
        "vram_required_mb": 2000,
        "recommended_for": "Complex dialogue, technical podcasts, multi-speaker content",
        "devices_supported": ["cuda", "cpu"],
    },
}

# Concurrency locks and active job tracking
_transcription_lock = asyncio.Lock()
_active_transcriptions: Set[str] = set()       # Active video IDs
_active_jobs: Dict[str, str] = {}              # job_id -> video_id
_cancelled_jobs: Set[str] = set()              # Set of job IDs flagged for cancellation


class WhisperModelManager:
    """Singleton model lifecycle manager for Faster-Whisper inference.
    Enforces ADR-002: Exactly one model loaded in VRAM at a time.
    Provides controlled unloading, automatic CPU fallback, and telemetry measurement.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._loaded_model: Optional[Any] = None
        self._loaded_key: Optional[Tuple[str, str, str]] = None  # (model_name, device, compute_type)
        self._device_used: str = "cpu"
        self._compute_type_used: str = "int8"

    def get_supported_models(self) -> List[ModelOptionInfo]:
        """Returns metadata specifications for all supported Faster-Whisper model sizes."""
        return [
            ModelOptionInfo(
                model_name=k,
                description=v["description"],
                parameters=v["parameters"],
                vram_required_mb=v["vram_required_mb"],
                recommended_for=v["recommended_for"],
                devices_supported=v["devices_supported"],
            )
            for k, v in SUPPORTED_MODELS.items()
        ]

    def resolve_device_and_compute_type(
        self,
        requested_device: Optional[str] = None,
        requested_compute_type: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Resolves target compute device and quantization type based on hardware capabilities."""
        cuda_ok = check_cuda_available() and not settings.FORCE_CPU_TRANSCRIPTION

        if requested_device:
            device = requested_device.lower().strip()
            if device == "cuda" and not cuda_ok:
                logger.warning("CUDA requested but GPU/CUDA unavailable. Falling back to CPU.")
                device = "cpu"
        else:
            device = "cuda" if cuda_ok else "cpu"

        if requested_compute_type:
            compute_type = requested_compute_type.lower().strip()
        else:
            if device == "cuda":
                compute_type = settings.TRANSCRIPTION_COMPUTE_TYPE or "float16"
            else:
                compute_type = "int8"

        return device, compute_type

    async def get_or_load_model(
        self,
        model_name: str = "base",
        requested_device: Optional[str] = None,
        requested_compute_type: Optional[str] = None,
    ) -> Tuple[Any, str, str]:
        """Loads or reuses the Faster-Whisper model instance without blocking the event loop."""
        async with self._lock:
            if model_name not in SUPPORTED_MODELS:
                raise AppException(
                    status_code=400,
                    detail=f"Unsupported model size '{model_name}'. Choose from: {list(SUPPORTED_MODELS.keys())}.",
                    error_code="UNSUPPORTED_WHISPER_MODEL",
                )

            device, compute_type = self.resolve_device_and_compute_type(
                requested_device, requested_compute_type
            )
            model_key = (model_name, device, compute_type)

            # Reuse currently loaded model if specifications match
            if self._loaded_model is not None and self._loaded_key == model_key:
                logger.info("Reusing cached Faster-Whisper model: %s (%s, %s)", model_name, device, compute_type)
                return self._loaded_model, device, compute_type

            # Unload previous model from VRAM/RAM before loading new one
            if self._loaded_model is not None:
                await self._unload_internal()

            # Record initial memory telemetry
            telemetry_before = get_hardware_telemetry()
            logger.info(
                "Loading Faster-Whisper model '%s' (device=%s, compute_type=%s, VRAM used=%sMB)...",
                model_name, device, compute_type, telemetry_before.gpu_vram_used_mb or "N/A"
            )

            load_start = time.time()
            try:
                # Load model in a separate thread so event loop remains responsive
                model = await asyncio.to_thread(
                    self._create_whisper_model,
                    model_name=model_name,
                    device=device,
                    compute_type=compute_type,
                    download_root=str(settings.WHISPER_MODELS_DIR),
                )
                self._loaded_model = model
                self._loaded_key = model_key
                self._device_used = device
                self._compute_type_used = compute_type

                load_duration = time.time() - load_start
                telemetry_after = get_hardware_telemetry()
                logger.info(
                    "Faster-Whisper model '%s' loaded in %.2fs (device=%s, VRAM used=%sMB)",
                    model_name, load_duration, device, telemetry_after.gpu_vram_used_mb or "N/A"
                )
                return self._loaded_model, device, compute_type

            except Exception as e:
                logger.error("Failed to load Whisper model on %s (%s): %s", device, compute_type, e)
                # If CUDA load failed, attempt automatic CPU fallback
                if device == "cuda":
                    logger.warning("Attempting automatic CPU fallback for model '%s'...", model_name)
                    fallback_device = "cpu"
                    fallback_compute = "int8"
                    try:
                        model = await asyncio.to_thread(
                            self._create_whisper_model,
                            model_name=model_name,
                            device=fallback_device,
                            compute_type=fallback_compute,
                            download_root=str(settings.WHISPER_MODELS_DIR),
                        )
                        self._loaded_model = model
                        self._loaded_key = (model_name, fallback_device, fallback_compute)
                        self._device_used = fallback_device
                        self._compute_type_used = fallback_compute
                        logger.info("Faster-Whisper CPU fallback initialized successfully.")
                        return self._loaded_model, fallback_device, fallback_compute
                    except Exception as fallback_err:
                        logger.error("CPU fallback also failed: %s", fallback_err)
                        raise AppException(
                            status_code=500,
                            detail=f"Faster-Whisper model loading failed on both CUDA and CPU: {fallback_err}",
                            error_code="MODEL_INITIALIZATION_FAILED",
                        )
                raise AppException(
                    status_code=500,
                    detail=f"Failed to initialize Faster-Whisper model: {e}",
                    error_code="MODEL_INITIALIZATION_FAILED",
                )

    def _create_whisper_model(
        self,
        model_name: str,
        device: str,
        compute_type: str,
        download_root: str,
    ) -> Any:
        """Instantiates Faster-Whisper WhisperModel (runs in worker thread)."""
        from faster_whisper import WhisperModel
        return WhisperModel(
            model_size_or_path=model_name,
            device=device,
            compute_type=compute_type,
            download_root=download_root,
            cpu_threads=4,
            num_workers=1,
        )

    async def unload_model(self) -> None:
        """Explicitly unloads loaded model and triggers garbage collection to free VRAM."""
        async with self._lock:
            await self._unload_internal()

    async def _unload_internal(self) -> None:
        """Internal synchronous model unloader."""
        if self._loaded_model is not None:
            logger.info("Unloading cached Faster-Whisper model '%s'...", self._loaded_key[0] if self._loaded_key else "unknown")
            del self._loaded_model
            self._loaded_model = None
            self._loaded_key = None
            gc.collect()


# Global singleton model manager
model_manager = WhisperModelManager()


# ---------------------------------------------------------------------------
# Core Pipeline: transcribe_audio_pipeline
# ---------------------------------------------------------------------------

async def transcribe_audio_pipeline(
    video_id: str,
    job_id: Optional[str] = None,
    model_name: Optional[str] = None,
    device: Optional[str] = None,
    compute_type: Optional[str] = None,
    language: Optional[str] = None,
    vad_filter: Optional[bool] = None,
    word_timestamps: Optional[bool] = None,
    force_retranscribe: bool = False,
) -> Transcript:
    """Executes the complete Faster-Whisper speech-to-text pipeline with Silero VAD.

    1. Validates normalized AudioAsset existence and physical file integrity.
    2. Enforces storage directory confinement against path traversal.
    3. Handles duplicate prevention via concurrency locks.
    4. Initializes or updates ProcessingJob state and progress telemetry.
    5. Loads or reuses Faster-Whisper model with cooperative cancellation checks.
    6. Applies Silero VAD options (threshold, min speech/silence duration, padding).
    7. Extracts word-level timestamps and segment probabilities.
    8. Handles silence-only audio honestly (0 segments, empty full text).
    9. Persists Transcript and TranscriptSegment records transactionally.
    10. Marks ProcessingJob COMPLETED and cleans up tracking locks.
    """
    async with _transcription_lock:
        if video_id in _active_transcriptions:
            raise ConflictError(
                f"Transcription is already active or in progress for video '{video_id}'.",
                details={"video_id": video_id},
            )
        _active_transcriptions.add(video_id)
        if job_id:
            _active_jobs[job_id] = video_id

    current_job_id = job_id
    start_time = time.time()

    try:
        # 1. Fetch Video and AudioAsset
        async with AsyncSessionLocal() as session:
            video = await session.get(Video, video_id)
            if not video:
                raise NotFoundError(f"Video with id '{video_id}' was not found.")

            stmt = select(AudioAsset).where(AudioAsset.video_id == video_id)
            res = await session.execute(stmt)
            audio_asset = res.scalar_one_or_none()

            if not audio_asset or audio_asset.status != "COMPLETED":
                raise NotFoundError(
                    f"No completed audio asset found for video '{video_id}'. "
                    "Please extract audio via /api/v1/videos/{video_id}/extract-audio first."
                )

            # Check if active transcript already exists and force_retranscribe is False
            if not force_retranscribe:
                stmt_t = select(Transcript).where(Transcript.video_id == video_id, Transcript.is_active == True)
                res_t = await session.execute(stmt_t)
                existing_transcript = res_t.scalar_one_or_none()
                if existing_transcript:
                    logger.info("Reusing existing active transcript for video %s", video_id)
                    session.expunge(existing_transcript)
                    return existing_transcript

            # Validate physical audio file existence and containment
            audio_path = Path(audio_asset.file_path).resolve()
            if not audio_path.is_relative_to(settings.AUDIO_DIR.resolve()):
                raise AppException(status_code=400, detail="Path traversal security violation on audio asset.")

            if not audio_path.exists():
                raise NotFoundError(f"Physical audio asset file was not found on local disk ({audio_path.name}).")

            # Initialize / update ProcessingJob
            job: Optional[ProcessingJob] = None
            if current_job_id:
                job = await session.get(ProcessingJob, current_job_id)

            if not job:
                job = ProcessingJob(
                    id=str(uuid.uuid4()),
                    video_id=video_id,
                    job_type="TRANSCRIPTION",
                    status="PROCESSING",
                    progress_percent=5.0,
                    current_step="Validating audio asset...",
                    started_at=datetime.now(timezone.utc),
                )
                session.add(job)
                await session.commit()
                await session.refresh(job)
                current_job_id = job.id
            else:
                job.status = "PROCESSING"
                job.progress_percent = 5.0
                job.current_step = "Validating audio asset..."
                job.started_at = datetime.now(timezone.utc)
                await session.commit()
                await session.refresh(job)

        # Check early cancellation
        if current_job_id in _cancelled_jobs:
            logger.info("Job %s was cancelled before model loading.", current_job_id)
            return await _abort_cancelled(current_job_id, video_id)

        # 2. Resolve Model and Parameters
        if model_name and model_name not in SUPPORTED_MODELS:
            raise InvalidFileFormatError(
                f"Unsupported Faster-Whisper model size '{model_name}'. "
                f"Supported options: {list(SUPPORTED_MODELS.keys())}."
            )
        target_model = model_name or settings.TRANSCRIPTION_MODEL

        # Update progress: Model loading
        await _update_job_progress(current_job_id, 15.0, f"Loading Faster-Whisper {target_model} model...")

        # 3. Load or Retrieve Cached Model
        model, actual_device, actual_compute = await model_manager.get_or_load_model(
            model_name=target_model,
            requested_device=device,
            requested_compute_type=compute_type,
        )

        if current_job_id in _cancelled_jobs:
            logger.info("Job %s was cancelled during model loading.", current_job_id)
            return await _abort_cancelled(current_job_id, video_id)

        # 4. Configure Silero VAD Options
        use_vad = vad_filter if vad_filter is not None else settings.VAD_ENABLED
        vad_params = None
        if use_vad:
            vad_params = {
                "threshold": settings.VAD_THRESHOLD,
                "min_speech_duration_ms": settings.VAD_MIN_SPEECH_DURATION_MS,
                "max_speech_duration_s": settings.VAD_MAX_SPEECH_DURATION_S,
                "min_silence_duration_ms": settings.VAD_MIN_SILENCE_DURATION_MS,
                "speech_pad_ms": settings.VAD_SPEECH_PAD_MS,
            }

        use_word_timestamps = word_timestamps if word_timestamps is not None else settings.ENABLE_WORD_TIMESTAMPS
        beam_size = settings.WHISPER_BEAM_SIZE

        # 5. Run Transcription Generator in Background Thread
        await _update_job_progress(current_job_id, 20.0, f"Transcribing audio with {target_model} ({actual_device})...")

        # Run transcribe generator
        segments_gen, info = await asyncio.to_thread(
            model.transcribe,
            audio=str(audio_path),
            language=language or settings.DEFAULT_WHISPER_LANGUAGE,
            beam_size=beam_size,
            word_timestamps=use_word_timestamps,
            vad_filter=use_vad,
            vad_parameters=vad_params,
        )

        detected_language = info.language or "en"
        lang_prob = round(float(info.language_probability or 1.0), 4)
        audio_duration = float(info.duration or audio_asset.duration_seconds or 0.0)

        logger.info(
            "Transcription started for %s: detected_lang=%s (prob=%.2f), duration=%.1fs, vad=%s",
            audio_path.name, detected_language, lang_prob, audio_duration, use_vad
        )

        # 6. Consume Segments with Real-Time Progress and Cooperative Cancellation
        raw_segments: List[Any] = []
        last_progress_time = time.time()
        last_progress_pct = 20.0

        def _get_next_segment(generator_iter):
            try:
                return next(generator_iter), False
            except StopIteration:
                return None, True

        seg_iter = iter(segments_gen)
        while True:
            # Check cooperative cancellation at segment boundaries
            if current_job_id in _cancelled_jobs:
                logger.info("Cooperative cancellation triggered for job %s during segment iteration.", current_job_id)
                return await _abort_cancelled(current_job_id, video_id)

            segment, is_done = await asyncio.to_thread(_get_next_segment, seg_iter)
            if is_done:
                break
            if segment is None:
                continue

            raw_segments.append(segment)

            # Update progress based on processed audio timestamp
            if audio_duration > 0:
                current_audio_time = min(audio_duration, segment.end)
                pct = 20.0 + (current_audio_time / audio_duration) * 70.0
                pct = min(90.0, max(20.0, pct))

                # Throttle database progress updates to once every 500ms
                now = time.time()
                if now - last_progress_time >= 0.5 and pct > last_progress_pct:
                    last_progress_time = now
                    last_progress_pct = pct
                    await _update_job_progress(
                        current_job_id,
                        round(pct, 1),
                        f"Transcribing: {current_audio_time:.0f}s / {audio_duration:.0f}s ({pct:.0f}%)...",
                    )

        # Check cancellation before persisting
        if current_job_id in _cancelled_jobs:
            return await _abort_cancelled(current_job_id, video_id)

        # 7. Persist Transcript and Segments Transactionally
        await _update_job_progress(current_job_id, 95.0, "Persisting transcript and word alignments...")

        elapsed_time = round(time.time() - start_time, 2)
        transcript_id = str(uuid.uuid4())

        # Construct full plain text and segment entities
        full_text_parts: List[str] = []
        total_word_count = 0
        db_segments: List[TranscriptSegment] = []

        for idx, seg in enumerate(raw_segments):
            seg_text = seg.text.strip()
            if seg_text:
                full_text_parts.append(seg_text)

            # Parse word-level timing
            words_data: List[Dict[str, Any]] = []
            if seg.words:
                for w in seg.words:
                    w_start_ms = int(round(w.start * 1000))
                    w_end_ms = int(round(w.end * 1000))
                    w_prob = round(float(w.probability), 3) if w.probability is not None else 1.0
                    words_data.append({
                        "word": w.word,
                        "start_ms": w_start_ms,
                        "end_ms": w_end_ms,
                        "prob": w_prob,
                    })
                total_word_count += len(words_data)
            else:
                # Fallback word count from text
                words_in_text = seg_text.split()
                total_word_count += len(words_in_text)

            start_ms = max(0, int(round(seg.start * 1000)))
            end_ms = max(start_ms + 1, int(round(seg.end * 1000)))
            avg_conf = round(float(math.exp(seg.avg_logprob)), 3) if seg.avg_logprob is not None else 1.0
            avg_conf = max(0.0, min(1.0, avg_conf))
            no_speech = round(float(seg.no_speech_prob), 3) if seg.no_speech_prob is not None else 0.0

            db_segment = TranscriptSegment(
                id=str(uuid.uuid4()),
                transcript_id=transcript_id,
                segment_index=idx,
                start_ms=start_ms,
                end_ms=end_ms,
                text=seg_text,
                words_json=json.dumps(words_data, ensure_ascii=False),
                avg_confidence=avg_conf,
                no_speech_prob=no_speech,
                speaker_id=None,
            )
            db_segments.append(db_segment)

        concatenated_text = " ".join(full_text_parts)

        async with AsyncSessionLocal() as session:
            # Deactivate any previous active transcripts for this video
            stmt_deactivate = (
                update(Transcript)
                .where(Transcript.video_id == video_id, Transcript.is_active == True)
                .values(is_active=False)
            )
            await session.execute(stmt_deactivate)

            # Insert new active transcript
            new_transcript = Transcript(
                id=transcript_id,
                video_id=video_id,
                audio_asset_id=audio_asset.id,
                model_name=target_model,
                compute_type=actual_compute,
                device=actual_device,
                language=detected_language,
                language_probability=lang_prob,
                status="COMPLETED",
                full_text=concatenated_text,
                word_count=total_word_count,
                segment_count=len(db_segments),
                audio_duration_seconds=audio_duration,
                processing_time_seconds=elapsed_time,
                error_message=None,
                is_active=True,
            )
            session.add(new_transcript)

            # Insert all segments
            session.add_all(db_segments)

            # Finalize ProcessingJob
            if current_job_id:
                job_record = await session.get(ProcessingJob, current_job_id)
                if job_record and job_record.status != "CANCELLED":
                    job_record.status = "COMPLETED"
                    job_record.progress_percent = 100.0
                    job_record.current_step = (
                        f"Transcription complete ({len(db_segments)} segments, {total_word_count} words)"
                    )
                    job_record.completed_at = datetime.now(timezone.utc)
                    job_record.error_message = None

            await session.commit()
            await session.refresh(new_transcript)
            session.expunge(new_transcript)

        logger.info(
            "Transcription completed for video %s: transcript_id=%s, %d segments, %d words in %.2fs",
            video_id, transcript_id, len(db_segments), total_word_count, elapsed_time
        )
        return new_transcript

    except Exception as exc:
        logger.error("Transcription pipeline failed for video %s: %s", video_id, exc)
        if current_job_id and current_job_id not in _cancelled_jobs:
            try:
                async with AsyncSessionLocal() as session:
                    failed_job = await session.get(ProcessingJob, current_job_id)
                    if failed_job and failed_job.status != "CANCELLED":
                        failed_job.status = "FAILED"
                        failed_job.error_message = str(exc)
                        failed_job.completed_at = datetime.now(timezone.utc)
                        await session.commit()
            except Exception:
                pass
        raise
    finally:
        async with _transcription_lock:
            _active_transcriptions.discard(video_id)
            if current_job_id:
                _active_jobs.pop(current_job_id, None)
                _cancelled_jobs.discard(current_job_id)


# ---------------------------------------------------------------------------
# Progress & Cancellation Helpers
# ---------------------------------------------------------------------------

async def _update_job_progress(job_id: Optional[str], progress: float, step: str) -> None:
    """Updates progress percent and step string in the processing_jobs table."""
    if not job_id:
        return
    try:
        async with AsyncSessionLocal() as session:
            job = await session.get(ProcessingJob, job_id)
            if job and job.status == "PROCESSING":
                job.progress_percent = progress
                job.current_step = step
                await session.commit()
    except Exception as e:
        logger.debug("Failed to update progress for job %s: %s", job_id, e)


async def _abort_cancelled(job_id: str, video_id: str) -> Any:
    """Handles cooperative cancellation exit, marking job CANCELLED in DB."""
    async with AsyncSessionLocal() as session:
        job = await session.get(ProcessingJob, job_id)
        if job and job.status != "CANCELLED":
            job.status = "CANCELLED"
            job.current_step = "Cancelled by user"
            job.error_message = "Transcription job was cancelled by user."
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()
    raise asyncio.CancelledError(f"Transcription job {job_id} was cancelled by user.")


async def cancel_transcription(job_id: str, db: Optional[AsyncSession] = None) -> bool:
    """Flags an active or queued transcription job for immediate cooperative cancellation."""
    _cancelled_jobs.add(job_id)

    async def _cancel_in_session(s: AsyncSession):
        job = await s.get(ProcessingJob, job_id)
        if not job:
            raise NotFoundError(f"Processing job with id '{job_id}' not found.")

        if job.status in ("COMPLETED", "FAILED", "CANCELLED"):
            raise ConflictError(f"Job '{job_id}' is already in terminal state '{job.status}'.")

        job.status = "CANCELLED"
        job.current_step = "Cancelled by user"
        job.error_message = "Transcription job was cancelled by user."
        job.completed_at = datetime.now(timezone.utc)
        await s.commit()

    if db is not None:
        await _cancel_in_session(db)
    else:
        async with AsyncSessionLocal() as s:
            await _cancel_in_session(s)

    # Discard active video lock
    vid_id = _active_jobs.pop(job_id, None)
    if vid_id:
        async with _transcription_lock:
            _active_transcriptions.discard(vid_id)

    logger.info("Signaled cooperative cancellation for transcription job %s", job_id)
    return True

    logger.info("Transcription job %s marked CANCELLED.", job_id)
    return True
