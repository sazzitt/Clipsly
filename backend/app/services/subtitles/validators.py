from typing import List
from backend.app.services.subtitles.schemas import CaptionEventData, NormalizedWord


class SubtitleValidationError(ValueError):
    """Raised when subtitle data structures or timing parameters fail validation."""
    pass


def validate_clip_timing(start_ms: int, end_ms: int, min_duration_ms: int = 1000) -> None:
    """Validates that clip boundaries are valid and non-inverted."""
    if start_ms < 0:
        raise SubtitleValidationError(f"Clip start_ms ({start_ms}) must be non-negative.")
    if end_ms <= start_ms:
        raise SubtitleValidationError(
            f"Clip end_ms ({end_ms}) must be strictly greater than start_ms ({start_ms})."
        )
    duration = end_ms - start_ms
    if duration < min_duration_ms:
        raise SubtitleValidationError(
            f"Clip duration ({duration}ms) is less than minimum permitted duration ({min_duration_ms}ms)."
        )


def validate_normalized_words(words: List[NormalizedWord], clip_duration_ms: int) -> None:
    """Validates that a list of normalized words is monotonic and strictly inside clip duration."""
    for i, word in enumerate(words):
        if word.start_ms < 0:
            raise SubtitleValidationError(
                f"Word '{word.text}' at index {i} has negative start_ms ({word.start_ms})."
            )
        if word.end_ms <= word.start_ms:
            raise SubtitleValidationError(
                f"Word '{word.text}' at index {i} has end_ms ({word.end_ms}) <= start_ms ({word.start_ms})."
            )
        if word.end_ms > clip_duration_ms:
            raise SubtitleValidationError(
                f"Word '{word.text}' at index {i} has end_ms ({word.end_ms}) exceeding clip duration ({clip_duration_ms}ms)."
            )
        if i > 0 and word.start_ms < words[i - 1].end_ms:
            raise SubtitleValidationError(
                f"Word '{word.text}' at index {i} overlaps previous word '{words[i - 1].text}' "
                f"({word.start_ms} < {words[i - 1].end_ms})."
            )


def validate_caption_events(events: List[CaptionEventData], clip_duration_ms: int) -> None:
    """Validates structured caption events for consistency and strict boundary containment."""
    for i, event in enumerate(events):
        if event.sequence_index != i:
            raise SubtitleValidationError(
                f"Event at position {i} has non-sequential sequence_index ({event.sequence_index})."
            )
        if event.start_ms < 0 or event.end_ms > clip_duration_ms:
            raise SubtitleValidationError(
                f"Event {i} timing [{event.start_ms}, {event.end_ms}] exceeds clip duration [0, {clip_duration_ms}]."
            )
        if not event.words:
            raise SubtitleValidationError(f"Event {i} has empty word list.")
        if i > 0 and event.start_ms < events[i - 1].end_ms:
            raise SubtitleValidationError(
                f"Event {i} starts ({event.start_ms}) before previous event ends ({events[i - 1].end_ms})."
            )
