"""Clipsly Phase 16: Highlight Candidate Ranking and Filtering.

Filters deduplicated highlight candidates by score threshold, limits to max results,
and assigns sequential 1-based ranks.
"""
from typing import List
from backend.app.services.highlight_detection.schemas import ScoredCandidate


def rank_and_filter_candidates(
    candidates: List[ScoredCandidate],
    min_score: float = 50.0,
    max_results: int = 10,
) -> List[ScoredCandidate]:
    """Filters candidates by minimum score threshold and limits to top ranked candidates.

    Args:
        candidates: Deduplicated candidate list.
        min_score: Minimum composite score required for retention (default 50.0).
        max_results: Maximum count of candidates to return (default 10).

    Returns:
        Ranked list of ScoredCandidate objects with 1-based rank assigned.
    """
    if not candidates:
        return []

    # Filter by minimum score
    eligible = [c for c in candidates if c.composite_score >= min_score]

    if not eligible:
        return []

    # Sort deterministically
    sorted_candidates = sorted(
        eligible,
        key=lambda c: (
            -c.composite_score,
            -c.scores.hook_score,
            c.start_ms,
            c.duration_ms,
        ),
    )

    # Slice top max_results
    top_candidates = sorted_candidates[:max_results]

    # Assign sequential 1-based rank
    for rank_idx, candidate in enumerate(top_candidates, 1):
        candidate.rank = rank_idx

    return top_candidates
