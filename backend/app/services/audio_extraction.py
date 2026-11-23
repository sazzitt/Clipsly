import asyncio
import json
import logging
import os
from pathlib import Path
import shutil
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select
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
from backend.app.models.video import Video

logger = logging.getLogger("clipsly.audio_extraction")

# Active locks and process tracking for concurrency and cancellation
_active_extractions: Set[str] = set()
_extraction_lock = asyncio.Lock()
_active_processes: Dict[str, asyncio.subprocess.Process] = {}
_active_temp_files: Dict[str, Path] = {}
_cancelled_jobs: Set[str] = set()


async def inspect_audio_streams(file_path: Path, timeout_seconds: float = 30.0) -> List[Dict[str, Any]]:
    """Inspects all audio streams in a media file using FFprobe.

    Returns structured audio stream info including stream index, codec,
    sample rate, channels, channel layout, language tags, and default disposition.
    """
    if not file_path.exists():
        raise NotFoundError(f"Video file not found at path: {file_path.name}")

    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a",
        "-show_entries",
        "stream=index,codec_name,channels,sample_rate,channel_layout,bit_rate,disposition:"
        "stream_tags=language,title",
        "-of", "json",
        str(file_path),
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            proc.kill()
            try:
                await proc.wait()
            except Exception:
                pass
            raise InvalidFileFormatError(f"FFprobe timed out inspecting audio streams ({timeout_seconds:.0f}s limit).")
    except FileNotFoundError:
        logger.error("FFprobe executable not found on workstation PATH.")
        raise AppException(
            status_code=500,
            detail="FFprobe binary was not found on workstation PATH. Please ensure FFmpeg is installed.",
            error_code="FFPROBE_NOT_FOUND",
        )

    if proc.returncode != 0:
        err_msg = stderr.decode("utf-8", errors="replace").strip()
        logger.warning("FFprobe audio inspection failed (code %d): %s", proc.returncode, err_msg)
        raise InvalidFileFormatError(f"Failed to inspect audio streams: {err_msg}")

    try:
        raw = json.loads(stdout.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        raise InvalidFileFormatError("Failed to parse FFprobe JSON stream output.")

    streams = raw.get("streams", [])
    parsed_streams: List[Dict[str, Any]] = []

    for s in streams:
        idx = int(s.get("index", 0))
        codec_name = str(s.get("codec_name") or "unknown")
        channels = int(s.get("channels") or 1)
        sample_rate = int(s.get("sample_rate") or 16000)
        channel_layout = s.get("channel_layout") or ("mono" if channels == 1 else "stereo")
        
        bit_rate = None
        if s.get("bit_rate") and str(s["bit_rate"]).isdigit():
            bit_rate = int(s["bit_rate"])

        tags = s.get("tags", {}) or {}
        language = tags.get("language")
        title = tags.get("title")

        disposition = s.get("disposition", {}) or {}
        is_default = bool(disposition.get("default", 0) == 1)

        parsed_streams.append({
            "index": idx,
            "codec_name": codec_name,
            "channels": channels,
            "sample_rate": sample_rate,
            "channel_layout": channel_layout,
            "bit_rate": bit_rate,
            "language": language,
            "title": title,
            "is_default": is_default,
        })

    return parsed_streams


def select_target_audio_stream(
    streams: List[Dict[str, Any]], requested_index: Optional[int] = None
) -> Dict[str, Any]:
    """Selects the target audio stream based on requested stream index or primary default policy.

    Default policy:
    1. If requested_index is provided, matches stream with that index.
    2. Else if an audio stream has disposition default=True, selects it.
    3. Else selects the first available audio stream.
    """
    if not streams:
        raise InvalidFileFormatError("No audio streams found in the media file.")

    if requested_index is not None:
        matched = next((s for s in streams if s["index"] == requested_index), None)
        if not matched:
            available = [s["index"] for s in streams]
            raise InvalidFileFormatError(
                f"Requested audio stream index {requested_index} does not exist. Available audio streams: {available}"
            )
        return matched

    # Primary default policy: disposition default == True, else first
    default_stream = next((s for s in streams if s.get("is_default")), None)
    return default_stream or streams[0]


async def validate_extracted_wav(wav_path: Path, expected_duration: float) -> Dict[str, Any]:
    """Validates the generated audio asset using FFprobe against the Phase 14 target profile:

    - Format: WAV
    - Codec: pcm_s16le
    - Sample rate: 16000 Hz
    - Channels: 1 (Mono)
    - Duration within acceptable tolerance (±1.5s of expected video duration).
    """
    if not wav_path.exists() or wav_path.stat().st_size == 0:
        raise InvalidFileFormatError("Generated audio file is missing or empty.")

    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries",
        "stream=codec_name,channels,sample_rate,duration,bits_per_raw_sample:format=duration,size",
        "-of", "json",
        str(wav_path),
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15.0)
    except FileNotFoundError:
        raise AppException(
            status_code=500,
            detail="FFprobe binary was not found on workstation PATH.",
            error_code="FFPROBE_NOT_FOUND",
        )
    except asyncio.TimeoutError:
        raise InvalidFileFormatError("FFprobe timed out validating generated WAV output.")

    if proc.returncode != 0:
        raise InvalidFileFormatError(f"FFprobe failed to inspect extracted WAV: {stderr.decode()}")

    try:
        raw = json.loads(stdout.decode())
    except json.JSONDecodeError:
        raise InvalidFileFormatError("Failed to parse FFprobe validation output.")

    streams = raw.get("streams", [])
    if not streams:
        raise InvalidFileFormatError("Extracted WAV contains no readable audio streams.")

    audio_stream = streams[0]
    codec = audio_stream.get("codec_name")
    channels = int(audio_stream.get("channels") or 0)
    sample_rate = int(audio_stream.get("sample_rate") or 0)

    format_info = raw.get("format", {})
    duration = float(format_info.get("duration") or audio_stream.get("duration") or 0.0)
    file_size = int(format_info.get("size") or wav_path.stat().st_size)

    if codec != "pcm_s16le":
        raise InvalidFileFormatError(f"Audio codec mismatch: expected 'pcm_s16le', got '{codec}'.")
    if channels != 1:
        raise InvalidFileFormatError(f"Audio channel mismatch: expected mono (1 channel), got {channels} channels.")
    if sample_rate != 16000:
        raise InvalidFileFormatError(f"Audio sample rate mismatch: expected 16000 Hz, got {sample_rate} Hz.")
    if duration <= 0.0:
        raise InvalidFileFormatError(f"Extracted audio duration is invalid ({duration}s).")

    return {
        "codec": codec,
        "channels": channels,
        "sample_rate": sample_rate,
        "channel_layout": "mono",
        "bit_depth": 16,
        "duration_seconds": duration,
        "file_size_bytes": file_size,
    }


async def extract_and_preprocess_audio(
    video_id: str,
    stream_index: Optional[int] = None,
    job_id: Optional[str] = None,
    force_reextract: bool = False,
    timeout_seconds: float = 600.0,
) -> AudioAsset:
    """Executes the complete FFmpeg audio extraction and preprocessing pipeline for a video.

    1. Checks concurrency lock to prevent duplicate simultaneous extractions.
    2. Validates disk space (at least settings.MIN_FREE_DISK_SPACE_GB required).
    3. Resolves source video path and enforces storage directory containment.
    4. Inspects container streams and selects primary/requested stream.
    5. Executes FFmpeg via safe subprocess (pcm_s16le, 16000Hz, mono).
    6. Monitors real-time machine-readable progress via `-progress pipe:1`.
    7. Validates generated WAV output with FFprobe.
    8. Atomically moves output from temp space into storage/audio/{uuid}.wav.
    9. Persists AudioAsset and updates ProcessingJob status to COMPLETED.
    """
    async with _extraction_lock:
        if video_id in _active_extractions:
            logger.warning("Audio extraction already in progress for video %s", video_id)
            raise ConflictError(
                f"Audio extraction is already in progress for video '{video_id}'.",
                details={"video_id": video_id},
            )
        _active_extractions.add(video_id)

    temp_path: Optional[Path] = None
    proc: Optional[asyncio.subprocess.Process] = None
    current_job_id: Optional[str] = job_id

    try:
        # Check disk space
        try:
            usage = shutil.disk_usage(settings.STORAGE_DIR)
            free_gb = usage.free / (1024 ** 3)
            if free_gb < settings.MIN_FREE_DISK_SPACE_GB:
                raise InsufficientStorageError(
                    f"Insufficient disk space for audio extraction: {free_gb:.1f} GB free, "
                    f"minimum {settings.MIN_FREE_DISK_SPACE_GB} GB required."
                )
        except OSError as e:
            logger.error("Disk usage check failed: %s", e)

        async with AsyncSessionLocal() as session:
            # 1. Fetch Video Record
            video = await session.get(Video, video_id)
            if not video:
                raise NotFoundError(f"Video with id '{video_id}' was not found.")

            # 2. Check if AudioAsset already exists and force_reextract is False
            if not force_reextract:
                stmt = select(AudioAsset).where(AudioAsset.video_id == video_id)
                res = await session.execute(stmt)
                existing_asset = res.scalar_one_or_none()
                if existing_asset:
                    # Check physical file exists
                    asset_path = Path(existing_asset.file_path)
                    if asset_path.exists():
                        logger.info("Reusing existing audio asset for video %s", video_id)
                        session.expunge(existing_asset)
                        return existing_asset

            # 3. Resolve physical video file path
            video_file_path = Path(video.file_path)
            if not video_file_path.is_absolute():
                video_file_path = settings.STORAGE_DIR.parent / video.file_path

            resolved_video_path = video_file_path.resolve()
            if not resolved_video_path.is_relative_to(settings.STORAGE_DIR.resolve()):
                raise AppException(status_code=400, detail="Path traversal security violation detected.")
            if not resolved_video_path.exists():
                raise NotFoundError(f"Source video file was not found on local storage ({resolved_video_path.name}).")

            # 4. Inspect audio streams
            audio_streams = await inspect_audio_streams(resolved_video_path)
            if not audio_streams:
                raise InvalidFileFormatError("Video file contains no audio streams to extract.")

            target_stream = select_target_audio_stream(audio_streams, stream_index)
            target_stream_idx = target_stream["index"]

            # 5. Initialize or update ProcessingJob
            job: Optional[ProcessingJob] = None
            if job_id:
                job = await session.get(ProcessingJob, job_id)

            if not job:
                job = ProcessingJob(
                    id=str(uuid.uuid4()),
                    video_id=video_id,
                    job_type="AUDIO_EXTRACTION",
                    status="PROCESSING",
                    progress_percent=0.0,
                    current_step="Initializing audio extraction...",
                    started_at=datetime.now(timezone.utc),
                )
                session.add(job)
                await session.commit()
                await session.refresh(job)
            else:
                job.status = "PROCESSING"
                job.progress_percent = 0.0
                job.current_step = "Initializing audio extraction..."
                job.started_at = datetime.now(timezone.utc)
                await session.commit()
                await session.refresh(job)

            current_job_id = job.id

        # 6. Prepare paths
        asset_id = str(uuid.uuid4())
        final_filename = f"{asset_id}.wav"
        final_path = (settings.AUDIO_DIR / final_filename).resolve()
        temp_filename = f"temp_{asset_id}.wav"
        temp_path = (settings.TEMP_DIR / temp_filename).resolve()

        # Path containment assertion
        if not final_path.is_relative_to(settings.AUDIO_DIR.resolve()):
            raise AppException(status_code=400, detail="Destination path traversal security violation.")

        if final_path.exists():
            raise ConflictError("Target audio asset path already exists on disk.")

        if current_job_id:
            _active_temp_files[current_job_id] = temp_path

        # 7. Build FFmpeg command for PCM 16kHz mono WAV extraction
        ffmpeg_cmd = [
            "ffmpeg",
            "-v", "error",
            "-progress", "pipe:1",
            "-nostats",
            "-i", str(resolved_video_path),
            "-map", f"0:{target_stream_idx}",
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y",
            str(temp_path),
        ]

        logger.info("Executing audio extraction: %s", " ".join(ffmpeg_cmd))

        try:
            proc = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            if current_job_id:
                _active_processes[current_job_id] = proc
        except FileNotFoundError:
            raise AppException(
                status_code=500,
                detail="FFmpeg binary was not found on workstation PATH. Please ensure FFmpeg is installed.",
                error_code="FFMPEG_NOT_FOUND",
            )

        # 8. Real-time machine-readable progress tracking
        last_progress_update = time.time()
        total_duration = max(0.1, video.duration_seconds)

        async def read_progress():
            nonlocal last_progress_update
            if not proc or not proc.stdout:
                return

            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").strip()
                if decoded.startswith("out_time_us="):
                    try:
                        us_val = int(decoded.split("=")[1])
                        sec_val = us_val / 1_000_000.0
                        pct = min(99.0, max(0.0, (sec_val / total_duration) * 100.0))
                        # Throttle DB updates to once per 500ms
                        if time.time() - last_progress_update >= 0.5:
                            last_progress_update = time.time()
                            async with AsyncSessionLocal() as s:
                                j = await s.get(ProcessingJob, current_job_id)
                                if j and j.status == "PROCESSING":
                                    j.progress_percent = round(pct, 1)
                                    j.current_step = f"Extracting PCM audio ({pct:.0f}%)..."
                                    await s.commit()
                    except (ValueError, IndexError):
                        pass

        async def read_stderr() -> bytes:
            if not proc or not proc.stderr:
                return b""
            return await proc.stderr.read()

        progress_task = asyncio.create_task(read_progress())
        stderr_task = asyncio.create_task(read_stderr())

        try:
            await asyncio.wait_for(asyncio.gather(progress_task, stderr_task), timeout=timeout_seconds)
            await proc.wait()
            stderr_data = stderr_task.result()
        except asyncio.TimeoutError:
            proc.kill()
            try:
                await proc.wait()
            except Exception:
                pass
            raise InvalidFileFormatError(f"FFmpeg audio extraction timed out after {timeout_seconds:.0f} seconds.")

        if proc.returncode != 0:
            err_details = stderr_data.decode("utf-8", errors="replace").strip()
            raise InvalidFileFormatError(f"FFmpeg failed with return code {proc.returncode}: {err_details}")

        # 9. Validate generated output with FFprobe
        validation = await validate_extracted_wav(temp_path, expected_duration=video.duration_seconds)

        # 10. Atomically move output into final storage location
        shutil.move(str(temp_path), str(final_path))
        temp_path = None  # moved successfully

        # 11. Persist AudioAsset in database and mark ProcessingJob COMPLETED
        async with AsyncSessionLocal() as session:
            # Check if an existing asset is being replaced
            stmt = select(AudioAsset).where(AudioAsset.video_id == video_id)
            res = await session.execute(stmt)
            asset = res.scalar_one_or_none()

            if asset:
                # Remove previous physical file if different
                old_file = Path(asset.file_path)
                if old_file.exists() and old_file != final_path:
                    try:
                        old_file.unlink()
                    except OSError:
                        pass
                asset.filename = final_filename
                asset.file_path = str(final_path)
                asset.file_size_bytes = validation["file_size_bytes"]
                asset.duration_seconds = validation["duration_seconds"]
                asset.format = "wav"
                asset.codec = validation["codec"]
                asset.sample_rate = validation["sample_rate"]
                asset.channels = validation["channels"]
                asset.channel_layout = validation["channel_layout"]
                asset.bit_depth = validation["bit_depth"]
                asset.source_stream_index = target_stream_idx
                asset.status = "COMPLETED"
                asset.error_message = None
                asset.job_id = current_job_id
            else:
                asset = AudioAsset(
                    id=asset_id,
                    video_id=video_id,
                    job_id=current_job_id,
                    filename=final_filename,
                    file_path=str(final_path),
                    file_size_bytes=validation["file_size_bytes"],
                    duration_seconds=validation["duration_seconds"],
                    format="wav",
                    codec=validation["codec"],
                    sample_rate=validation["sample_rate"],
                    channels=validation["channels"],
                    channel_layout=validation["channel_layout"],
                    bit_depth=validation["bit_depth"],
                    source_stream_index=target_stream_idx,
                    status="COMPLETED",
                )
                session.add(asset)

            # Update job state
            if current_job_id:
                job_to_update = await session.get(ProcessingJob, current_job_id)
                if job_to_update:
                    job_to_update.status = "COMPLETED"
                    job_to_update.progress_percent = 100.0
                    job_to_update.current_step = "Audio extraction and preprocessing complete"
                    job_to_update.completed_at = datetime.now(timezone.utc)
                    job_to_update.error_message = None

            await session.commit()
            await session.refresh(asset)
            session.expunge(asset)
            return asset

    except Exception as exc:
        logger.error("Audio extraction failed for video %s: %s", video_id, exc)
        # Update job to FAILED only if not already cancelled
        if current_job_id:
            try:
                if current_job_id in _cancelled_jobs:
                    logger.info("Job %s was cancelled; skipping FAILED state update.", current_job_id)
                else:
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
        # Cleanup temporary files
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass

        if current_job_id:
            _active_processes.pop(current_job_id, None)
            _active_temp_files.pop(current_job_id, None)
            _cancelled_jobs.discard(current_job_id)

        async with _extraction_lock:
            _active_extractions.discard(video_id)


async def cancel_audio_extraction(job_id: str, db: AsyncSession) -> bool:
    """Cancels an active audio extraction process and performs immediate resource cleanup."""
    job = await db.get(ProcessingJob, job_id)
    if not job:
        raise NotFoundError(f"Job with id '{job_id}' not found.")

    if job.status in ("COMPLETED", "FAILED", "CANCELLED"):
        raise ConflictError(f"Job '{job_id}' is already in terminal state '{job.status}'.")

    # Mark cancelled immediately to prevent race conditions with failure handler
    _cancelled_jobs.add(job_id)
    job.status = "CANCELLED"
    job.current_step = "Cancelled by user"
    job.error_message = "Audio extraction job was cancelled by user."
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)

    # Kill running process
    proc = _active_processes.get(job_id)
    if proc:
        try:
            proc.kill()
            await proc.wait()
        except Exception as e:
            logger.warning("Error killing process for job %s: %s", job_id, e)

    # Clean up temp file
    temp_file = _active_temp_files.get(job_id)
    if temp_file and temp_file.exists():
        try:
            temp_file.unlink()
        except OSError:
            pass

    _active_processes.pop(job_id, None)
    _active_temp_files.pop(job_id, None)
    async with _extraction_lock:
        _active_extractions.discard(job.video_id)

    return True
