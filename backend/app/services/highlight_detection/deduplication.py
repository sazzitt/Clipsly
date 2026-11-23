"""Clipsly Phase 16: Highlight Candidate Deduplication and Overlap Suppression.

Implements greedy Non-Maximum Suppression (NMS) over temporal candidate windows
to eliminate redundant, near-duplicate, or nested highlight segments while
preserving the highest-scoring candidate for each distinct moment.
"""
from typing import Any, List, Tuple
from backend.app.services.highlight_detection.schemas import ScoredCandidate


def calculate_temporal_overlap(
    start_a: int,
    end_a: int,
    start_b: int,
    end_b: int,
) -> float:
    """Calculates temporal overlap ratio between two time intervals in milliseconds.

    Uses Intersection over Minimum Duration (IoM):
        overlap = max(0, min(end_a, end_b) - max(start_a, start_b)) / min(dur_a, dur_b)

    This ensures that if a shorter window is substantially contained within a longer
    window covering the same core thought, the overlap is recognized and suppressed.
    """
    dur_a = end_a - start_a
    dur_b = end_b - start_b

    if dur_a <= 0 or dur_b <= 0:
        return 0.0

    inter_start = max(start_a, start_b)
    inter_end = min(end_a, end_b)
    intersection = max(0, inter_end - inter_start)

    if intersection == 0:
        return 0.0

    min_dur = min(dur_a, dur_b)
    return intersection / min_dur


def calculate_candidate_overlap(
    cand_a: ScoredCandidate,
    cand_b: ScoredCandidate,
) -> float:
    """Calculates temporal overlap between two ScoredCandidate instances."""
    return calculate_temporal_overlap(
        cand_a.start_ms,
        cand_a.end_ms,
        cand_b.start_ms,
        cand_b.end_ms,
    )


def deduplicate_candidates(
    candidates: List[ScoredCandidate],
    overlap_threshold: float = 0.45,
) -> List[ScoredCandidate]:
    """Applies greedy Non-Maximum Suppression to filter out overlapping candidates.

    Candidates are first sorted by:
    1. Composite Score (descending)
    2. Hook Score (descending)
    3. Start Time ms (ascending)
    4. Duration ms (ascending)

    Args:
        candidates: List of scored candidate windows.
        overlap_threshold: Maximum allowed overlap ratio before suppression (default 0.45).

    Returns:
        Deduplicated list of ScoredCandidate instances.
    """
    if not candidates:
        return []

    # Deterministic sort
    sorted_candidates = sorted(
        candidates,
        key=lambda c: (
            -c.composite_score,
            -c.scores.hook_score,
            c.start_ms,
            c.duration_ms,
        ),
    )

    retained: List[ScoredCandidate] = []

    for candidate in sorted_candidates:
        should_keep = True
        for kept in retained:
            overlap = calculate_candidate_overlap(candidate, kept)
            if overlap >= overlap_threshold:
                should_keep = False
                break

        if should_keep:
            retained.append(candidate)

    return retained
