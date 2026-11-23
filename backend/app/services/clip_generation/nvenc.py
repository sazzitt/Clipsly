import asyncio
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger("clipsly.clip_generation.nvenc")

_NVENC_AVAILABLE: Optional[bool] = None
_NVENC_PROBE_LOCK = asyncio.Lock()


async def check_nvenc_hardware_support(timeout_seconds: float = 5.0) -> bool:
    """Probes FFmpeg on the workstation to verify whether h264_nvenc encoder operates
    successfully on the local NVIDIA GPU and driver stack.
    """
    global _NVENC_AVAILABLE
    if _NVENC_AVAILABLE is not None:
        return _NVENC_AVAILABLE

    async with _NVENC_PROBE_LOCK:
        if _NVENC_AVAILABLE is not None:
            return _NVENC_AVAILABLE

        cmd = [
            "ffmpeg",
            "-v", "error",
            "-f", "lavfi",
            "-i", "nullsrc=s=256x256:d=0.1",
            "-c:v", "h264_nvenc",
            "-f", "null",
            "-",
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
                if proc.returncode == 0:
                    logger.info("NVENC hardware encoder (h264_nvenc) verified and active.")
                    _NVENC_AVAILABLE = True
                else:
                    err_msg = stderr.decode("utf-8", errors="replace").strip()
                    logger.warning(
                        "NVENC hardware encoder unavailable (code %d: %s). Falling back to CPU libx264.",
                        proc.returncode,
                        err_msg,
                    )
                    _NVENC_AVAILABLE = False
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                logger.warning("NVENC probe timed out (%0.1fs limit). Falling back to CPU libx264.", timeout_seconds)
                _NVENC_AVAILABLE = False
        except (FileNotFoundError, OSError) as e:
            logger.warning("FFmpeg executable failed during NVENC probe: %s. Falling back to CPU libx264.", e)
            _NVENC_AVAILABLE = False

        return _NVENC_AVAILABLE


def is_nvenc_cached() -> Optional[bool]:
    """Returns cached NVENC availability, or None if probe has not executed."""
    return _NVENC_AVAILABLE


def set_nvenc_availability_for_testing(available: Optional[bool]) -> None:
    """Testing helper to simulate hardware presence or driver absence."""
    global _NVENC_AVAILABLE
    _NVENC_AVAILABLE = available


async def get_video_encoder_args(
    target_fps: float = 30.0,
    crf: int = 22,
    force_cpu: bool = False,
) -> Tuple[str, List[str]]:
    """Returns tuple of (backend_name, ffmpeg_video_args).
    Gracefully falls back to high-performance AVX2 CPU libx264 when NVENC is unavailable.
    """
    nvenc_supported = False if force_cpu else await check_nvenc_hardware_support()

    if nvenc_supported:
        args = [
            "-c:v", "h264_nvenc",
            "-preset", "p4",
            "-rc", "vbr",
            "-cq", "23",
            "-b:v", "5M",
            "-maxrate", "8M",
            "-r", f"{target_fps:.2f}",
            "-pix_fmt", "yuv420p",
        ]
        return "h264_nvenc", args
    else:
        args = [
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", str(crf),
            "-r", f"{target_fps:.2f}",
            "-pix_fmt", "yuv420p",
        ]
        return "libx264", args
