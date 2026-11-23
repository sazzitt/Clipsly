import asyncio
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, Optional, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.exceptions import AppException, InvalidFileFormatError, NotFoundError
from backend.app.core.logging import logger
from backend.app.models.video import Video

# In-memory guard to prevent uncontrolled duplicate extraction requests
_active_extractions: Set[str] = set()
_extraction_lock = asyncio.Lock()


def _parse_fps(fps_str: Optional[str]) -> float:
    """Parses fractional or scalar framerate strings (e.g. '30/1', '29.97', '60000/1001')."""
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


def _calculate_aspect_ratio(width: int, height: int, dar: Optional[str] = None) -> str:
    """Calculates display aspect ratio string from pixel dimensions or container DAR."""
    if dar and ":" in dar and dar != "0:1":
        return dar

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
    if common_gcd > 1:
        return f"{width // common_gcd}:{height // common_gcd}"
    return f"{width}:{height}"


def _determine_orientation(width: int, height: int, rotation: int = 0) -> str:
    """Determines video orientation accounting for rotation metadata."""
    eff_width, eff_height = width, height
    if rotation in (90, 270, -90, -270):
        eff_width, eff_height = height, width

    if eff_height > eff_width:
        return "portrait"
    elif eff_height == eff_width:
        return "square"
    return "landscape"


def _format_duration(seconds: float) -> str:
    """Formats duration in seconds to human-readable string (e.g. '12m 34s', '1h 05m 12s')."""
    if seconds <= 0:
        return "0s"
    total_sec = int(round(seconds))
    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    s = total_sec % 60
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    if m > 0:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def _format_bytes(size_bytes: int) -> str:
    """Formats bytes to human-readable string (e.g. '42.5 MB', '1.2 GB')."""
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(size_bytes, 1024))) if size_bytes > 0 else 0
    i = min(i, len(units) - 1)
    val = size_bytes / (1024 ** i)
    return f"{val:.1f} {units[i]}"


def _get_resolution_label(height: int, width: int) -> str:
    """Computes standard video resolution label."""
    min_dim = min(width, height)
    max_dim = max(width, height)
    if max_dim >= 3840 or min_dim >= 2160:
        return "4K"
    if max_dim >= 2560 or min_dim >= 1440:
        return "1440p"
    if max_dim >= 1920 or min_dim >= 1080:
        return "1080p"
    if max_dim >= 1280 or min_dim >= 720:
        return "720p"
    if max_dim >= 854 or min_dim >= 480:
        return "480p"
    if max_dim >= 640 or min_dim >= 360:
        return "360p"
    return f"{min_dim}p"


async def extract_video_metadata(
    file_path: Path,
    timeout_seconds: float = 30.0
) -> Dict[str, Any]:
    """Extracts comprehensive stream and container metadata from a local video file using FFprobe.
    
    Safe subprocess execution using asyncio.create_subprocess_exec (NEVER shell=True).
    Bounded timeout with proper child process termination and handle closure.
    """
    if not file_path.exists():
        raise NotFoundError(f"Video file not found at path: {file_path.name}")

    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries",
        "format=format_name,duration,size,bit_rate:format_tags=rotate:"
        "stream=index,codec_name,profile,codec_type,width,height,pix_fmt,bits_per_raw_sample,"
        "r_frame_rate,avg_frame_rate,sample_rate,channels,channel_layout,bit_rate,display_aspect_ratio:stream_tags=rotate:"
        "stream_side_data=rotation,side_data_type",
        "-of", "json",
        str(file_path),
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
            raise InvalidFileFormatError(
                f"FFprobe timed out while extracting metadata ({timeout_seconds:.0f}s watchdog limit)."
            )
    except FileNotFoundError:
        logger.error("FFprobe binary not found on workstation PATH.")
        raise AppException(
            status_code=500,
            detail="FFprobe binary was not found on workstation PATH. Please ensure FFmpeg is installed.",
            error_code="FFPROBE_NOT_FOUND"
        )
    except OSError as e:
        logger.error("Subprocess execution error during FFprobe: %s", e)
        raise AppException(
            status_code=500,
            detail=f"Failed to execute FFprobe subprocess: {e}",
            error_code="FFPROBE_EXECUTION_ERROR"
        )

    if proc.returncode != 0:
        err_msg = stderr.decode("utf-8", errors="replace").strip()
        logger.warning("FFprobe metadata extraction failed (code %d): %s", proc.returncode, err_msg)
        raise InvalidFileFormatError(
            f"FFprobe failed to inspect container ({file_path.suffix}). The file may be corrupt or unreadable."
        )

    try:
        raw_data = json.loads(stdout.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        raise InvalidFileFormatError("Failed to parse technical stream metadata from FFprobe JSON output.")

    streams = raw_data.get("streams", [])
    format_info = raw_data.get("format", {})

    # Detect video stream
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video_stream:
        raise InvalidFileFormatError("No valid video stream detected in media file.")

    # Container & File Info
    container_format = format_info.get("format_name") or file_path.suffix.lstrip(".").lower()
    try:
        file_size_bytes = int(format_info.get("size") or file_path.stat().st_size)
    except (ValueError, OSError):
        file_size_bytes = file_path.stat().st_size

    # Duration
    duration_str = format_info.get("duration") or video_stream.get("duration") or "0.0"
    try:
        duration_seconds = round(float(duration_str), 2)
    except ValueError:
        duration_seconds = 0.0

    # Overall Bitrate
    bitrate_str = format_info.get("bit_rate")
    try:
        bitrate = int(bitrate_str) if bitrate_str else None
    except ValueError:
        bitrate = None

    # Video Stream Details
    video_codec = str(video_stream.get("codec_name") or "unknown")
    video_codec_profile = video_stream.get("profile")
    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)
    if width <= 0 or height <= 0:
        raise InvalidFileFormatError(f"Invalid video dimensions ({width}x{height}) reported by FFprobe.")

    fps = _parse_fps(video_stream.get("r_frame_rate") or video_stream.get("avg_frame_rate"))
    avg_fps = _parse_fps(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate"))

    pixel_format = video_stream.get("pix_fmt")
    
    # Bit depth
    bit_depth = None
    raw_depth = video_stream.get("bits_per_raw_sample")
    if raw_depth and str(raw_depth).isdigit():
        bit_depth = int(raw_depth)
    elif pixel_format:
        if "10" in pixel_format:
            bit_depth = 10
        elif "12" in pixel_format:
            bit_depth = 12
        elif "8" in pixel_format or "yuv420p" in pixel_format:
            bit_depth = 8

    # Video Bitrate
    video_bitrate = None
    if video_stream.get("bit_rate") and str(video_stream["bit_rate"]).isdigit():
        video_bitrate = int(video_stream["bit_rate"])

    # Rotation detection (tags, side_data)
    rotation = 0
    # 1. Check stream tags
    tags = video_stream.get("tags", {})
    if "rotate" in tags and str(tags["rotate"]).lstrip("-").isdigit():
        rotation = int(tags["rotate"])
    # 2. Check format tags
    format_tags = format_info.get("tags", {})
    if "rotate" in format_tags and str(format_tags["rotate"]).lstrip("-").isdigit():
        rotation = int(format_tags["rotate"])
    # 3. Check side_data_list
    for side in video_stream.get("side_data_list", []):
        if "rotation" in side:
            try:
                rotation = int(side["rotation"])
            except (ValueError, TypeError):
                pass

    dar = video_stream.get("display_aspect_ratio")
    aspect_ratio = _calculate_aspect_ratio(width, height, dar)
    orientation = _determine_orientation(width, height, rotation)

    # Audio Stream Details (Optional - videos without audio supported gracefully)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    has_audio = audio_stream is not None

    audio_codec: Optional[str] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    channel_layout: Optional[str] = None
    audio_bitrate: Optional[int] = None

    if audio_stream:
        audio_codec = str(audio_stream.get("codec_name") or "unknown")
        try:
            sample_rate = int(audio_stream.get("sample_rate") or 48000)
        except ValueError:
            sample_rate = 48000
        try:
            channels = int(audio_stream.get("channels") or 2)
        except ValueError:
            channels = 2
        channel_layout = audio_stream.get("channel_layout") or ("mono" if channels == 1 else "stereo")
        if audio_stream.get("bit_rate") and str(audio_stream["bit_rate"]).isdigit():
            audio_bitrate = int(audio_stream["bit_rate"])

    # Derived UI fields
    resolution = f"{width}x{height}"
    resolution_label = _get_resolution_label(height, width)
    formatted_duration = _format_duration(duration_seconds)
    formatted_file_size = _format_bytes(file_size_bytes)
    fps_label = f"{fps:.1f} fps"

    return {
        "container_format": container_format,
        "file_size_bytes": file_size_bytes,
        "duration_seconds": duration_seconds,
        "bitrate": bitrate,
        "file_extension": file_path.suffix.lower(),
        "video_codec": video_codec,
        "video_codec_profile": video_codec_profile,
        "width": width,
        "height": height,
        "resolution": resolution,
        "resolution_label": resolution_label,
        "aspect_ratio": aspect_ratio,
        "fps": fps,
        "avg_fps": avg_fps,
        "fps_label": fps_label,
        "pixel_format": pixel_format,
        "bit_depth": bit_depth,
        "video_bitrate": video_bitrate,
        "rotation": rotation,
        "orientation": orientation,
        "has_audio": has_audio,
        "audio_codec": audio_codec,
        "audio_sample_rate": sample_rate,
        "audio_channels": channels,
        "channel_layout": channel_layout,
        "audio_bitrate": audio_bitrate,
        "formatted_duration": formatted_duration,
        "formatted_file_size": formatted_file_size,
        "raw_json": json.dumps(raw_data),
    }


async def extract_and_persist_metadata(
    video_id: str,
    db: AsyncSession,
    timeout_seconds: float = 30.0
) -> Video:
    """Orchestrates metadata extraction for a video entity, updating DB with concurrency guard.
    
    Prevents duplicate simultaneous extraction requests for the same video.
    Guarantees that extraction failures do not wipe previously valid metadata.
    """
    async with _extraction_lock:
        if video_id in _active_extractions:
            logger.warning("Metadata extraction already in progress for video %s", video_id)
            raise AppException(
                status_code=409,
                detail="Metadata extraction is already in progress for this video.",
                error_code="EXTRACTION_ALREADY_IN_PROGRESS"
            )
        _active_extractions.add(video_id)

    try:
        stmt = select(Video).where(Video.id == video_id)
        result = await db.execute(stmt)
        video = result.scalar_one_or_none()

        if not video:
            raise NotFoundError(f"Video with id '{video_id}' was not found.")

        # Resolve storage file path
        if not video.file_path:
            video.metadata_status = "FAILED"
            video.error_message = "No storage file path associated with video record."
            await db.commit()
            raise NotFoundError("Video record contains no physical storage path.")

        file_path = Path(video.file_path)
        if not file_path.is_absolute():
            file_path = settings.STORAGE_DIR.parent / video.file_path

        # Verify containment within storage directory
        resolved_path = file_path.resolve()
        if not resolved_path.is_relative_to(settings.STORAGE_DIR.resolve()):
            video.metadata_status = "FAILED"
            video.error_message = "Security path containment violation."
            await db.commit()
            raise AppException(status_code=400, detail="Path traversal security violation detected.")

        if not resolved_path.exists():
            video.metadata_status = "FAILED"
            video.error_message = f"Physical video file missing on disk: {resolved_path.name}"
            await db.commit()
            raise NotFoundError(f"Physical video file was not found on local storage disk ({resolved_path.name}).")

        # Mark metadata status as PROCESSING
        video.metadata_status = "PROCESSING"
        await db.commit()
        await db.refresh(video)

        # Execute extraction
        try:
            meta = await extract_video_metadata(resolved_path, timeout_seconds=timeout_seconds)
        except Exception as exc:
            # Record failure state without destroying previously existing metadata
            video.metadata_status = "FAILED"
            video.error_message = str(exc)
            await db.commit()
            raise

        # Update video record with extracted metadata
        video.container_format = meta["container_format"]
        video.file_size_bytes = meta["file_size_bytes"]
        video.duration_seconds = meta["duration_seconds"]
        video.bitrate = meta["bitrate"]
        video.width = meta["width"]
        video.height = meta["height"]
        video.aspect_ratio = meta["aspect_ratio"]
        video.fps = meta["fps"]
        video.video_codec = meta["video_codec"]
        video.video_codec_profile = meta["video_codec_profile"]
        video.pixel_format = meta["pixel_format"]
        video.bit_depth = meta["bit_depth"]
        video.video_bitrate = meta["video_bitrate"]
        video.rotation = meta["rotation"]
        video.orientation = meta["orientation"]
        video.audio_codec = meta["audio_codec"]
        video.audio_sample_rate = meta["audio_sample_rate"]
        video.audio_channels = meta["audio_channels"]
        video.channel_layout = meta["channel_layout"]
        video.audio_bitrate = meta["audio_bitrate"]
        video.metadata_status = "COMPLETED"
        video.metadata_extracted_at = datetime.now(timezone.utc)
        video.metadata_json = meta["raw_json"]
        video.error_message = None

        await db.commit()
        await db.refresh(video)

        logger.info(
            "Metadata extracted and persisted for video %s (%s, %dx%d, %s, %s)",
            video.id,
            video.container_format,
            video.width,
            video.height,
            video.video_codec,
            video.orientation
        )
        return video

    finally:
        async with _extraction_lock:
            _active_extractions.discard(video_id)
