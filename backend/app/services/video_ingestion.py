import asyncio
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
from typing import Any, Dict, Optional, Tuple
import uuid

from fastapi import Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.exceptions import (
    AppException,
    ClientDisconnectError,
    FileTooLargeError,
    InsufficientStorageError,
    InvalidFileFormatError,
)
from backend.app.core.logging import logger
from backend.app.models.video import Video


def validate_extension(filename: str) -> str:
    """Validates that the uploaded filename has an allowed video extension."""
    if not filename:
        raise InvalidFileFormatError("Filename cannot be empty.")

    suffix = Path(filename).suffix.lower()
    if suffix not in settings.ALLOWED_VIDEO_EXTENSIONS:
        allowed = ", ".join(ext.upper().lstrip(".") for ext in settings.ALLOWED_VIDEO_EXTENSIONS)
        raise InvalidFileFormatError(
            f"Unsupported video file extension '{suffix}'. Allowed formats: {allowed}."
        )
    return suffix


def check_storage_space() -> None:
    """Verifies that the SSD has sufficient headroom before accepting incoming video bytes."""
    try:
        usage = shutil.disk_usage(str(settings.STORAGE_DIR))
        free_gb = usage.free / (1024 ** 3)
        if free_gb < settings.MIN_FREE_DISK_SPACE_GB:
            raise InsufficientStorageError(
                f"Insufficient local SSD storage. At least {settings.MIN_FREE_DISK_SPACE_GB} GB free space "
                f"required, but only {free_gb:.2f} GB is currently available."
            )
    except OSError as e:
        logger.error("Failed to query local disk space: %s", e)


async def stream_file_to_disk(
    upload_file: UploadFile,
    temp_path: Path,
    max_bytes: int,
    chunk_size: int,
    request: Optional[Request] = None,
) -> Tuple[int, str]:
    """Streams incoming multipart chunks to a temporary disk path with bounded memory, cancellation detection, and size limit enforcement."""
    total_bytes = 0
    hasher = hashlib.sha256()

    try:
        with open(temp_path, "wb") as f:
            while True:
                if request is not None and await request.is_disconnected():
                    logger.warning("Client disconnected during upload streaming. Terminating stream.")
                    raise ClientDisconnectError("Client disconnected during upload.")

                chunk = await upload_file.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise FileTooLargeError(
                        f"File size exceeds maximum allowed upload size of {max_bytes / (1024 ** 3):.1f} GB."
                    )
                hasher.update(chunk)
                f.write(chunk)
    except (Exception, asyncio.CancelledError):
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise

    if total_bytes == 0:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise InvalidFileFormatError("The uploaded file is empty (0 bytes).")

    return total_bytes, hasher.hexdigest()


def _parse_fps(fps_str: str) -> float:
    """Parses a fractional or scalar frame rate string from FFprobe."""
    if not fps_str or fps_str == "0/0":
        return 30.0
    try:
        if "/" in fps_str:
            num, den = fps_str.split("/", 1)
            denominator = float(den)
            return round(float(num) / denominator, 2) if denominator != 0 else 30.0
        return round(float(fps_str), 2)
    except (ValueError, ZeroDivisionError):
        return 30.0


def _calculate_aspect_ratio(width: int, height: int) -> str:
    """Calculates canonical aspect ratio string from pixel dimensions."""
    if height == 0 or width == 0:
        return "16:9"

    ratio = width / height
    if abs(ratio - 16 / 9) < 0.05:
        return "16:9"
    if abs(ratio - 9 / 16) < 0.05:
        return "9:16"
    if abs(ratio - 4 / 3) < 0.05:
        return "4:3"
    if abs(ratio - 1.0) < 0.05:
        return "1:1"
    if abs(ratio - 21 / 9) < 0.08:
        return "21:9"

    common_gcd = math.gcd(width, height)
    return f"{width // common_gcd}:{height // common_gcd}"


async def inspect_with_ffprobe(file_path: Path, timeout_seconds: float = 30.0) -> Dict[str, Any]:
    """Inspects container and streams using an asynchronous FFprobe child process."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries",
        "format=format_name,duration,size:stream=index,codec_name,codec_type,width,height,r_frame_rate,avg_frame_rate,sample_rate,channels",
        "-of", "json",
        str(file_path)
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            proc.kill()
            try:
                await proc.wait()
            except Exception:
                pass
            raise InvalidFileFormatError(f"FFprobe timed out while validating video container ({timeout_seconds:.0f}s watchdog limit).")
    except FileNotFoundError:
        logger.error("FFprobe binary not found on PATH.")
        raise AppException(
            status_code=500,
            detail="FFprobe binary was not found on workstation PATH. Please ensure FFmpeg is installed.",
            error_code="FFPROBE_NOT_FOUND"
        )

    if proc.returncode != 0:
        err_msg = stderr.decode("utf-8", errors="replace").strip()
        logger.warning("FFprobe inspection failed with exit code %d: %s", proc.returncode, err_msg)
        raise InvalidFileFormatError(
            "FFprobe failed to inspect container. The file may be corrupt, truncated, or an unreadable video format."
        )

    try:
        data = json.loads(stdout.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        raise InvalidFileFormatError("Failed to parse technical stream metadata from FFprobe output.")

    streams = data.get("streams", [])
    format_info = data.get("format", {})

    # Detect video stream
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video_stream:
        raise InvalidFileFormatError("No valid video stream detected in uploaded file.")

    # Detect audio stream (audio track presence; actual speech transcription occurs in Phase 13/14)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not audio_stream:
        raise InvalidFileFormatError(
            "No valid audio stream detected in uploaded file. Clipsly requires an audio track for speech transcription."
        )

    # Dimensions
    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)
    if width <= 0 or height <= 0:
        raise InvalidFileFormatError(f"Invalid video dimensions ({width}x{height}) reported by FFprobe.")

    # Framerate
    fps = _parse_fps(video_stream.get("r_frame_rate") or video_stream.get("avg_frame_rate") or "30/1")

    # Duration
    duration_str = format_info.get("duration") or video_stream.get("duration") or "0.0"
    try:
        duration_seconds = round(float(duration_str), 2)
    except ValueError:
        duration_seconds = 0.0

    if duration_seconds <= 0.0:
        raise InvalidFileFormatError("Unable to determine valid video duration from media container.")

    # Duration limits check
    if settings.ENFORCE_DURATION_LIMITS:
        if duration_seconds < settings.MIN_VIDEO_DURATION_SECONDS:
            raise InvalidFileFormatError(
                f"Video duration is {duration_seconds:.1f}s. Minimum required duration is "
                f"{int(settings.MIN_VIDEO_DURATION_SECONDS // 60)} minutes ({int(settings.MIN_VIDEO_DURATION_SECONDS)}s)."
            )
        if duration_seconds > settings.MAX_VIDEO_DURATION_SECONDS:
            raise InvalidFileFormatError(
                f"Video duration is {duration_seconds:.1f}s. Maximum allowed duration is "
                f"{int(settings.MAX_VIDEO_DURATION_SECONDS // 60)} minutes ({int(settings.MAX_VIDEO_DURATION_SECONDS)}s)."
            )

    aspect_ratio = _calculate_aspect_ratio(width, height)
    video_codec = str(video_stream.get("codec_name") or "unknown")
    audio_codec = str(audio_stream.get("codec_name") or "unknown")

    sample_rate = int(audio_stream.get("sample_rate") or 48000)
    channels = int(audio_stream.get("channels") or 2)

    return {
        "width": width,
        "height": height,
        "aspect_ratio": aspect_ratio,
        "fps": fps,
        "duration_seconds": duration_seconds,
        "video_codec": video_codec,
        "audio_codec": audio_codec,
        "audio_sample_rate": sample_rate,
        "audio_channels": channels,
    }


async def ingest_video(
    upload_file: UploadFile,
    db: AsyncSession,
    request: Optional[Request] = None,
    ffprobe_timeout_seconds: float = 30.0,
) -> Video:
    """Orchestrates complete upload pipeline: storage check, streaming, validation, atomic finalization, and DB registration."""
    # 1. Storage check
    check_storage_space()

    # 2. Extension validation
    original_filename = upload_file.filename or "video.mp4"
    extension = validate_extension(original_filename)

    # 3. Stream to temp file
    upload_uuid = uuid.uuid4().hex
    temp_file_path: Optional[Path] = settings.TEMP_DIR / f"upload_{upload_uuid}.tmp"
    final_file_path: Optional[Path] = None

    try:
        total_bytes, sha256_hash = await stream_file_to_disk(
            upload_file=upload_file,
            temp_path=temp_file_path,
            max_bytes=settings.MAX_UPLOAD_SIZE_BYTES,
            chunk_size=settings.UPLOAD_CHUNK_SIZE_BYTES,
            request=request,
        )

        # 4. FFprobe validation
        metadata = await inspect_with_ffprobe(temp_file_path, timeout_seconds=ffprobe_timeout_seconds)

        # 5. Move to final storage location with UUID
        video_id = str(uuid.uuid4())
        final_filename = f"{video_id}{extension}"
        final_file_path = settings.UPLOAD_DIR / final_filename

        # Path confinement check
        resolved_final = final_file_path.resolve()
        if not resolved_final.is_relative_to(settings.STORAGE_DIR.resolve()):
            raise AppException(status_code=400, detail="Path traversal security violation detected.")

        # Atomic move
        shutil.move(str(temp_file_path), str(final_file_path))

        # 6. Database record creation
        relative_db_path = f"storage/uploads/{final_filename}"
        video = Video(
            id=video_id,
            filename=final_filename,
            original_filename=original_filename,
            file_path=relative_db_path,
            file_size_bytes=total_bytes,
            duration_seconds=metadata["duration_seconds"],
            width=metadata["width"],
            height=metadata["height"],
            aspect_ratio=metadata["aspect_ratio"],
            fps=metadata["fps"],
            video_codec=metadata["video_codec"],
            audio_codec=metadata["audio_codec"],
            audio_sample_rate=metadata["audio_sample_rate"],
            audio_channels=metadata["audio_channels"],
            container_format=extension.lstrip(".").lower(),
            orientation="portrait" if metadata["height"] > metadata["width"] else "square" if metadata["height"] == metadata["width"] else "landscape",
            metadata_status="COMPLETED",
            metadata_extracted_at=datetime.now(timezone.utc),
            status="READY",
        )

        db.add(video)
        await db.commit()
        await db.refresh(video)

        logger.info(
            "Video ingested successfully: ID=%s, Filename=%s, Size=%d bytes, Duration=%.2fs",
            video.id,
            video.filename,
            video.file_size_bytes,
            video.duration_seconds
        )
        return video

    except (Exception, asyncio.CancelledError) as exc:
        # Rollback any uncommitted database state
        try:
            await db.rollback()
        except Exception:
            pass

        # Cleanup temp file if still present
        if temp_file_path is not None and temp_file_path.exists():
            try:
                temp_file_path.unlink()
            except OSError:
                pass

        # Cleanup persistent file if moved before DB failure
        if final_file_path is not None and final_file_path.exists():
            try:
                final_file_path.unlink()
            except OSError:
                pass

        if isinstance(exc, OSError):
            logger.error("Disk I/O failure during video ingestion: %s", exc)
            raise AppException(
                status_code=500,
                detail=f"Local storage disk write failure: {exc}",
                error_code="STORAGE_WRITE_ERROR",
            )

        raise
