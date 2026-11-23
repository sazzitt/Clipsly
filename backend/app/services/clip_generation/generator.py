import asyncio
import logging
import os
from pathlib import Path
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Set

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
    ValidationError,
)
from backend.app.models.clip import Clip
from backend.app.models.processing_job import ProcessingJob
from backend.app.models.video import Video
from backend.app.services.clip_generation.filtergraphs import get_filter_args
from backend.app.services.clip_generation.nvenc import get_video_encoder_args
from backend.app.services.clip_generation.schemas import (
    ClipGenerationRequest,
    normalize_conversion_mode,
)
from backend.app.services.clip_generation.validator import validate_clip_output

logger = logging.getLogger("clipsly.clip_generation.generator")

_active_processes: Dict[str, asyncio.subprocess.Process] = {}
_active_temp_files: Dict[str, Path] = {}
_cancelled_jobs: Set[str] = set()


async def execute_clip_generation(
    job_id: str,
    clip_id: str,
    req_dict: dict,
    force_cpu: bool = False,
    timeout_seconds: float = 300.0,
) -> None:
    """Sequential worker task for generating an individual 9:16 vertical video clip.
    Executed through JobQueueManager (ADR-001/ADR-002).
    """
    req = ClipGenerationRequest(**req_dict)
    temp_path: Optional[Path] = None

    try:
        # 1. Fetch DB records
        async with AsyncSessionLocal() as session:
            job = await session.get(ProcessingJob, job_id)
            clip = await session.get(Clip, clip_id)
            video = await session.get(Video, req.video_id)

            if not job or not clip or not video:
                logger.error("Job %s, Clip %s, or Video %s not found in DB.", job_id, clip_id, req.video_id)
                return

            if job_id in _cancelled_jobs:
                logger.info("Job %s was cancelled before execution started.", job_id)
                job.status = "CANCELLED"
                job.current_step = "Cancelled while queued"
                job.completed_at = datetime.now(timezone.utc)
                clip.status = "CANCELLED"
                clip.error_message = "Generation cancelled before execution."
                await session.commit()
                return

            # Check disk space (minimum 1GB for clip generation)
            try:
                free_bytes = shutil_disk_free(settings.STORAGE_DIR)
                if free_bytes < 1024 * 1024 * 1024:
                    raise InsufficientStorageError("Insufficient disk space on local storage (less than 1GB free).")
            except Exception as e:
                if isinstance(e, InsufficientStorageError):
                    raise

            # 2. Validate source video file
            src_path = Path(video.file_path)
            if not src_path.is_absolute():
                src_path = settings.STORAGE_DIR.parent / video.file_path
            src_path = src_path.resolve()

            if not src_path.exists():
                raise NotFoundError(f"Physical source video file not found on disk: {src_path.name}")

            # 3. Validate timing bounds
            if req.end_ms <= req.start_ms:
                raise ValidationError("Clip end_ms must be greater than start_ms.")

            duration_ms = req.end_ms - req.start_ms
            if duration_ms < 5000:
                raise ValidationError("Clip duration must be at least 5000 milliseconds (5.0s).")

            start_s = req.start_ms / 1000.0
            duration_s = duration_ms / 1000.0

            # 4. Check source audio
            has_audio = bool(video.audio_codec and video.audio_codec.lower() not in ("none", "unknown", ""))

            # 5. Determine output and temp paths
            output_filename = f"{clip_id}.mp4"
            final_path = settings.CLIPS_DIR / output_filename
            temp_path = settings.TEMP_DIR / f"{clip_id}.tmp.mp4"
            _active_temp_files[job_id] = temp_path

            # Remove existing temp file if any
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

            mode = normalize_conversion_mode(req.conversion_mode or req.aspect_ratio_mode)

            # 6. Build encoder and filter args
            backend_name, encoder_args = await get_video_encoder_args(
                target_fps=req.target_fps,
                force_cpu=force_cpu,
            )
            filter_args = get_filter_args(
                conversion_mode=mode,
                target_width=req.target_width,
                target_height=req.target_height,
            )

            # Audio args
            if has_audio:
                audio_args = ["-map", "0:a:0?", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
            else:
                audio_args = ["-an"]

            # 7. Assemble complete FFmpeg command
            cmd = [
                "ffmpeg",
                "-y",
                "-ss", f"{start_s:.3f}",
                "-i", str(src_path),
                "-t", f"{duration_s:.3f}",
                *filter_args,
                *encoder_args,
                *audio_args,
                "-movflags", "+faststart",
                "-progress", "pipe:1",
                str(temp_path),
            ]

            logger.info("Executing FFmpeg clip generation: %s", " ".join(cmd))

            # 8. Launch subprocess
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _active_processes[job_id] = proc

            job.status = "PROCESSING"
            job.current_step = f"Encoding 9:16 clip ({backend_name})..."
            job.process_pid = proc.pid
            job.started_at = datetime.now(timezone.utc)
            clip.status = "PROCESSING"
            clip.aspect_ratio_mode = mode
            clip.conversion_mode = mode
            clip.encoding_backend = backend_name
            await session.commit()

        # 9. Real-time progress monitoring
        last_progress_time = time.time()

        async def read_progress():
            nonlocal last_progress_time
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
                        pct = min(99.0, max(0.0, (sec_val / duration_s) * 100.0))
                        now = time.time()
                        if now - last_progress_time >= 0.5:
                            last_progress_time = now
                            async with AsyncSessionLocal() as s:
                                j = await s.get(ProcessingJob, job_id)
                                if j and j.status == "PROCESSING":
                                    j.progress_percent = round(pct, 1)
                                    j.current_step = f"Encoding 9:16 clip ({pct:.0f}%)..."
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
            stderr_bytes = stderr_task.result()
        except asyncio.TimeoutError:
            proc.kill()
            try:
                await proc.wait()
            except Exception:
                pass
            raise InvalidFileFormatError(f"FFmpeg clip generation timed out after {timeout_seconds:.0f} seconds.")

        # Check if cancelled during run
        if job_id in _cancelled_jobs:
            logger.info("Clip generation job %s cancelled during processing.", job_id)
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            return

        if proc.returncode != 0:
            err_msg = stderr_bytes.decode("utf-8", errors="replace").strip()
            raise InvalidFileFormatError(f"FFmpeg failed with exit code {proc.returncode}: {err_msg}")

        # 10. Validate output with FFprobe
        probe_res = await validate_clip_output(
            file_path=temp_path,
            expected_duration_seconds=duration_s,
            expected_width=req.target_width,
            expected_height=req.target_height,
            source_has_audio=has_audio,
        )

        if not probe_res.valid:
            raise InvalidFileFormatError(f"Generated clip failed validation: {probe_res.error_message}")

        # 11. Atomic replace to final storage path
        if final_path.exists():
            try:
                final_path.unlink()
            except OSError:
                pass
        os.replace(str(temp_path), str(final_path))
        temp_path = None  # successfully placed

        # 12. Update DB records to COMPLETED
        async with AsyncSessionLocal() as session:
            j = await session.get(ProcessingJob, job_id)
            c = await session.get(Clip, clip_id)

            if j:
                j.status = "COMPLETED"
                j.progress_percent = 100.0
                j.current_step = "Completed"
                j.completed_at = datetime.now(timezone.utc)

            if c:
                c.status = "COMPLETED"
                c.output_path = str(final_path)
                c.output_filename = output_filename
                c.width = probe_res.width
                c.height = probe_res.height
                c.fps = probe_res.fps
                c.video_codec = probe_res.video_codec
                c.audio_codec = probe_res.audio_codec
                c.file_size_bytes = probe_res.file_size_bytes
                c.encoding_backend = backend_name
                c.completed_at = datetime.now(timezone.utc)

            await session.commit()
            logger.info("Clip generation %s completed successfully: %s", clip_id, final_path.name)

    except Exception as exc:
        logger.error("Clip generation job %s failed: %s", job_id, exc)
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass

        async with AsyncSessionLocal() as session:
            j = await session.get(ProcessingJob, job_id)
            c = await session.get(Clip, clip_id)

            if j and j.status != "CANCELLED":
                j.status = "FAILED"
                j.error_message = str(exc)
                j.completed_at = datetime.now(timezone.utc)

            if c and c.status != "CANCELLED":
                c.status = "FAILED"
                c.error_message = str(exc)

            await session.commit()

    finally:
        _active_processes.pop(job_id, None)
        _active_temp_files.pop(job_id, None)
        _cancelled_jobs.discard(job_id)


def shutil_disk_free(path: Path) -> int:
    """Helper to return free disk space in bytes."""
    import shutil
    return shutil.disk_usage(str(path)).free


async def cancel_clip_generation(job_id: str, db: AsyncSession) -> bool:
    """Safely terminates an actively running or queued clip generation job on Windows."""
    _cancelled_jobs.add(job_id)

    proc = _active_processes.get(job_id)
    if proc:
        try:
            logger.info("Terminating FFmpeg clip generation process PID %s for job %s", proc.pid, job_id)
            proc.kill()
            await proc.wait()
        except Exception as e:
            logger.warning("Error terminating process for job %s: %s", job_id, e)
        finally:
            _active_processes.pop(job_id, None)

    # Clean up temp file
    temp_file = _active_temp_files.pop(job_id, None)
    if temp_file and temp_file.exists():
        try:
            temp_file.unlink()
        except OSError:
            pass

    job = await db.get(ProcessingJob, job_id)
    if job:
        job.status = "CANCELLED"
        job.current_step = "Cancelled by user"
        job.completed_at = datetime.now(timezone.utc)

    # Also update associated clip
    stmt = select(Clip).where(Clip.id == job_id)  # or find clip
    res = await db.execute(select(Clip).where(Clip.status == "PROCESSING"))
    clips = res.scalars().all()
    for c in clips:
        # Check if output_filename or temp file matches
        if c.id in str(temp_file) or c.status == "PROCESSING":
            c.status = "CANCELLED"
            c.error_message = "Generation cancelled by user."

    await db.commit()
    return True
