import functools
import shutil
import subprocess
import time
from typing import Dict, Any

# Track backend process start time for uptime calculation
START_TIME = time.time()


def get_uptime_seconds() -> float:
    """Returns uptime in seconds since backend process initialization."""
    return round(time.time() - START_TIME, 2)


@functools.lru_cache(maxsize=1)
def check_cuda_available() -> bool:
    """Detects whether an NVIDIA GPU with CUDA driver support is available."""
    try:
        res = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False
        )
        return res.returncode == 0 and "GPU" in res.stdout
    except Exception:
        return False


@functools.lru_cache(maxsize=1)
def check_nvenc_available() -> bool:
    """Detects whether FFmpeg has h264_nvenc hardware acceleration enabled."""
    try:
        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            return False
        res = subprocess.run(
            [ffmpeg_bin, "-encoders"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False
        )
        return "h264_nvenc" in res.stdout
    except Exception:
        return False
