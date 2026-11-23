"""Clipsly Phase 16: Highlight Candidate Window Generator.

Uses transcript segments and word-level timestamps to generate candidate highlight
windows of variable durations (15-30s, 30-60s, 60-90s, custom) aligned to natural
speech and sentence boundaries without splitting words.
"""
import json
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.services.highlight_detection.schemas import CandidateWindow, DetectionConfig
from backend.app.services.highlight_detection.validators import validate_candidate_window

logger = logging.getLogger("clipsly.highlight_detection.candidate_generator")


def parse_duration_presets(
    presets: List[str],
    global_min_s: float = 15.0,
    global_max_s: float = 90.0,
) -> List[Tuple[float, float]]:
    """Parses duration string presets like '15-30', '30-60' into (min_s, max_s) tuples."""
    buckets: List[Tuple[float, float]] = []
    for p in presets:
        cleaned = p.strip()
        if "-" in cleaned:
            parts = cleaned.split("-")
            try:
                low = float(parts[0].strip())
                high = float(parts[1].strip())
                if low < high:
                    buckets.append((max(10.0, low), min(180.0, high)))
            except ValueError:
                continue
    if not buckets:
        buckets.append((global_min_s, global_max_s))
    return buckets


def generate_candidate_windows(
    segments: List[Any],
    config: DetectionConfig,
    video_duration_seconds: Optional[float] = None,
) -> List[CandidateWindow]:
    """Generates candidate highlight windows from transcript segments.

    1. Uses natural sentence boundaries from Faster-Whisper segments.
    2. Explores configurable duration buckets (e.g. 15-30s, 30-60s, 60-90s).
    3. Refines start/end boundaries using word timestamps to trim extraneous pauses.
    4. Never cuts off words mid-utterance.
    5. Preserves absolute video timeline milliseconds.
    """
    if not segments:
        return []

    # Filter out empty or whitespace-only segments
    valid_segments = []
    for s in segments:
        text = getattr(s, "text", "") or ""
        if text.strip():
            valid_segments.append(s)

    if not valid_segments:
        return []

    duration_buckets = parse_duration_presets(
        config.target_duration_presets,
        config.min_duration_seconds,
        config.max_duration_seconds,
    )

    # Ensure custom min/max bounds are included
    custom_bucket = (config.min_duration_seconds, config.max_duration_seconds)
    if custom_bucket not in duration_buckets:
        duration_buckets.append(custom_bucket)

    candidates: List[CandidateWindow] = []
    seen_ranges: Set[Tuple[int, int]] = set()

    num_segments = len(valid_segments)

    # Iterate over every starting segment
    for start_idx in range(num_segments):
        start_seg = valid_segments[start_idx]
        start_ms = int(round(start_seg.start_ms))

        # Check if words are available on start segment to refine starting speech boundary
        start_words = _extract_segment_words(start_seg)
        if start_words and len(start_words) > 0:
            first_word_start = start_words[0].get("start_ms")
            if first_word_start is not None and first_word_start >= start_ms:
                start_ms = first_word_start

        accumulated_text_parts: List[str] = []
        accumulated_words: List[Dict[str, Any]] = []
        accumulated_segments: List[Any] = []

        # Expand window by accumulating forward segments
        for curr_idx in range(start_idx, num_segments):
            curr_seg = valid_segments[curr_idx]
            accumulated_segments.append(curr_seg)
            seg_text = curr_seg.text.strip()
            if seg_text:
                accumulated_text_parts.append(seg_text)

            curr_words = _extract_segment_words(curr_seg)
            accumulated_words.extend(curr_words)

            end_ms = int(round(curr_seg.end_ms))
            if curr_words and len(curr_words) > 0:
                last_word_end = curr_words[-1].get("end_ms")
                if last_word_end is not None and last_word_end <= end_ms:
                    end_ms = last_word_end

            duration_s = (end_ms - start_ms) / 1000.0

            # Check if this window satisfies any target duration bucket
            is_in_any_bucket = any(low <= duration_s <= high for low, high in duration_buckets)
            
            # Also check if it's within global bounds
            if is_in_any_bucket and config.min_duration_seconds <= duration_s <= config.max_duration_seconds:
                range_key = (start_ms, end_ms)
                if range_key not in seen_ranges:
                    seen_ranges.add(range_key)
                    full_text = " ".join(accumulated_text_parts)
                    window = CandidateWindow(
                        start_ms=start_ms,
                        end_ms=end_ms,
                        duration_ms=end_ms - start_ms,
                        start_segment_idx=start_idx,
                        end_segment_idx=curr_idx,
                        text=full_text,
                        segments=list(accumulated_segments),
                        words=list(accumulated_words),
                    )
                    
                    is_valid, _ = validate_candidate_window(
                        window,
                        video_duration_seconds=video_duration_seconds,
                        min_duration_ms=int(config.min_duration_seconds * 1000),
                        max_duration_ms=int(config.max_duration_seconds * 1000),
                    )
                    if is_valid:
                        candidates.append(window)

            # If current duration exceeds the absolute max of all buckets, stop expanding from this start
            max_bucket_limit = max(high for _, high in duration_buckets)
            if duration_s > max(config.max_duration_seconds, max_bucket_limit) + 2.0:
                break

    logger.debug(
        "Generated %d raw candidate windows across %d segments.",
        len(candidates),
        num_segments,
    )
    return candidates


def _extract_segment_words(seg: Any) -> List[Dict[str, Any]]:
    """Safely extracts word timestamp dictionaries from a segment entity or dict."""
    words_attr = getattr(seg, "words", None)
    if words_attr is not None:
        if isinstance(words_attr, list):
            res = []
            for w in words_attr:
                if isinstance(w, dict):
                    res.append(w)
                else:
                    res.append({
                        "word": getattr(w, "word", ""),
                        "start_ms": int(round(getattr(w, "start", 0.0) * 1000)) if hasattr(w, "start") else getattr(w, "start_ms", 0),
                        "end_ms": int(round(getattr(w, "end", 0.0) * 1000)) if hasattr(w, "end") else getattr(w, "end_ms", 0),
                        "prob": getattr(w, "probability", 1.0) or getattr(w, "prob", 1.0),
                    })
            return res

    words_json = getattr(seg, "words_json", None)
    if words_json:
        try:
            parsed = json.loads(words_json)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass

    return []
