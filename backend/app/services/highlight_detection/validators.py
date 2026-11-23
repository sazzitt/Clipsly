"""Clipsly Phase 16: Highlight Candidate Validators.

Validates candidate windows, timing constraints, and detection configurations.
"""
from typing import List, Optional, Tuple
from backend.app.core.exceptions import InvalidFileFormatError
from backend.app.services.highlight_detection.schemas import CandidateWindow, DetectionConfig


def validate_detection_config(config: DetectionConfig, video_duration_seconds: Optional[float] = None) -> None:
    """Validates highlight detection configuration parameters."""
    if config.min_duration_seconds > config.max_duration_seconds:
        raise InvalidFileFormatError(
            f"min_duration_seconds ({config.min_duration_seconds}s) cannot be greater than "
            f"max_duration_seconds ({config.max_duration_seconds}s)."
        )

    if config.min_duration_seconds < 10.0 or config.max_duration_seconds > 180.0:
        raise InvalidFileFormatError(
            "Candidate duration must be bounded between 10.0 and 180.0 seconds."
        )

    weight_sum = config.hook_weight + config.coherence_weight + config.density_weight + config.sentiment_weight
    if abs(weight_sum - 1.0) > 0.01:
        raise InvalidFileFormatError(
            f"Scoring weights must sum to 1.0 (current sum: {weight_sum:.3f})."
        )

    if video_duration_seconds is not None and video_duration_seconds > 0:
        if config.min_duration_seconds > video_duration_seconds:
            # Adjust min duration to video duration if video is shorter than default min duration
            config.min_duration_seconds = max(5.0, min(config.min_duration_seconds, video_duration_seconds))


def validate_candidate_window(
    window: CandidateWindow,
    video_duration_seconds: Optional[float] = None,
    min_duration_ms: int = 10000,
    max_duration_ms: int = 180000,
) -> Tuple[bool, Optional[str]]:
    """Checks whether a candidate window meets physical timing and content requirements.

    Returns:
        (is_valid, rejection_reason)
    """
    if window.start_ms < 0:
        return False, "Negative start timestamp"

    if window.end_ms <= window.start_ms:
        return False, "End timestamp must be strictly greater than start timestamp"

    duration_ms = window.end_ms - window.start_ms
    if duration_ms < min_duration_ms:
        return False, f"Window duration ({duration_ms}ms) is less than minimum ({min_duration_ms}ms)"

    if duration_ms > max_duration_ms:
        return False, f"Window duration ({duration_ms}ms) exceeds maximum ({max_duration_ms}ms)"

    if video_duration_seconds is not None and video_duration_seconds > 0:
        video_max_ms = int(round((video_duration_seconds + 1.0) * 1000))
        if window.end_ms > video_max_ms:
            return False, f"End timestamp ({window.end_ms}ms) exceeds video duration ({video_max_ms}ms)"

    cleaned_text = window.text.strip()
    if not cleaned_text:
        return False, "Candidate window contains no speech text"

    words = cleaned_text.split()
    if len(words) < 3:
        return False, f"Insufficient word count ({len(words)} words) for standalone highlight"

    return True, None
