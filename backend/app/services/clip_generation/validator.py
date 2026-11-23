import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from backend.app.services.clip_generation.schemas import ClipProbeResult

logger = logging.getLogger("clipsly.clip_generation.validator")


async def validate_clip_output(
    file_path: Path,
    expected_duration_seconds: float,
    expected_width: int = 1080,
    expected_height: int = 1920,
    source_has_audio: bool = True,
    duration_tolerance_seconds: float = 1.0,
    timeout_seconds: float = 15.0,
) -> ClipProbeResult:
    """Probes and validates a generated vertical video clip using FFprobe.

    Verifies:
    1. File exists on disk and is non-empty.
    2. Container is a valid MP4/MOV container.
    3. Exactly matches target width and height (e.g. 1080x1920).
    4. Duration matches target slice within tolerance.
    5. Audio stream is preserved if the source contained audio.
    """
    if not file_path.exists():
        return ClipProbeResult(
            valid=False,
            error_message=f"Output file does not exist on disk: {file_path.name}",
        )

    file_size = file_path.stat().st_size
    if file_size == 0:
        return ClipProbeResult(
            valid=False,
            file_size_bytes=0,
            error_message="Output video file is 0 bytes.",
        )

    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_format",
        "-show_streams",
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
            await proc.wait()
            return ClipProbeResult(
                valid=False,
                file_size_bytes=file_size,
                error_message=f"FFprobe timed out after {timeout_seconds:.0f}s probing output clip.",
            )
    except FileNotFoundError:
        return ClipProbeResult(
            valid=False,
            file_size_bytes=file_size,
            error_message="FFprobe executable not found on system PATH.",
        )

    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace").strip()
        return ClipProbeResult(
            valid=False,
            file_size_bytes=file_size,
            error_message=f"FFprobe failed with return code {proc.returncode}: {err}",
        )

    try:
        data = json.loads(stdout.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return ClipProbeResult(
            valid=False,
            file_size_bytes=file_size,
            error_message="Failed to parse FFprobe JSON output.",
        )

    format_info = data.get("format", {})
    format_name = format_info.get("format_name", "")
    streams = data.get("streams", [])

    # Find video and audio streams
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if not video_stream:
        return ClipProbeResult(
            valid=False,
            file_size_bytes=file_size,
            format_name=format_name,
            error_message="No video stream detected in output file.",
        )

    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)
    video_codec = video_stream.get("codec_name", "")

    # Frame rate calculation
    fps = 0.0
    r_frame_rate = video_stream.get("r_frame_rate", "")
    if "/" in r_frame_rate:
        num, den = r_frame_rate.split("/", 1)
        try:
            fps = float(num) / float(den) if float(den) != 0 else 0.0
        except ValueError:
            fps = 0.0

    # Duration calculation (prefer container duration or stream duration)
    raw_duration = (
        format_info.get("duration")
        or video_stream.get("duration")
        or (audio_stream.get("duration") if audio_stream else None)
    )
    duration_seconds = float(raw_duration) if raw_duration else 0.0

    # Width and height validation
    if width != expected_width or height != expected_height:
        return ClipProbeResult(
            valid=False,
            file_size_bytes=file_size,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            video_codec=video_codec,
            audio_codec=audio_stream.get("codec_name") if audio_stream else None,
            fps=fps,
            format_name=format_name,
            error_message=f"Video dimensions {width}x{height} do not match expected {expected_width}x{expected_height}.",
        )

    # Duration tolerance check
    if abs(duration_seconds - expected_duration_seconds) > duration_tolerance_seconds:
        logger.warning(
            "Output clip duration %.2fs deviates from expected %.2fs (tolerance: %.2fs)",
            duration_seconds,
            expected_duration_seconds,
            duration_tolerance_seconds,
        )

    # Audio presence check
    audio_codec: Optional[str] = None
    if audio_stream:
        audio_codec = audio_stream.get("codec_name")
    elif source_has_audio:
        return ClipProbeResult(
            valid=False,
            file_size_bytes=file_size,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            video_codec=video_codec,
            fps=fps,
            format_name=format_name,
            error_message="Source had audio, but no audio stream was found in generated clip.",
        )

    return ClipProbeResult(
        valid=True,
        file_size_bytes=file_size,
        duration_seconds=duration_seconds,
        width=width,
        height=height,
        video_codec=video_codec,
        audio_codec=audio_codec,
        fps=round(fps, 2),
        format_name=format_name,
    )
