"""Clipsly Phase 16: Highlight Detection and Clip Intelligence Package.

Provides CPU-first, explainable heuristic highlight detection from speech transcripts.
"""
from backend.app.services.highlight_detection.candidate_generator import (
    generate_candidate_windows,
    parse_duration_presets,
)
from backend.app.services.highlight_detection.deduplication import (
    calculate_candidate_overlap,
    calculate_temporal_overlap,
    deduplicate_candidates,
)
from backend.app.services.highlight_detection.detector import (
    cancel_highlight_detection,
    detect_highlights_pipeline,
)
from backend.app.services.highlight_detection.feature_extractor import (
    extract_window_features,
)
from backend.app.services.highlight_detection.ranking import (
    rank_and_filter_candidates,
)
from backend.app.services.highlight_detection.schemas import (
    CandidateWindow,
    DetectionConfig,
    ScoredCandidate,
    ScoringBreakdown,
)
from backend.app.services.highlight_detection.scoring_engine import (
    score_candidate_window,
)
from backend.app.services.highlight_detection.validators import (
    validate_candidate_window,
    validate_detection_config,
)

__all__ = [
    "CandidateWindow",
    "DetectionConfig",
    "ScoredCandidate",
    "ScoringBreakdown",
    "calculate_candidate_overlap",
    "calculate_temporal_overlap",
    "cancel_highlight_detection",
    "deduplicate_candidates",
    "detect_highlights_pipeline",
    "extract_window_features",
    "generate_candidate_windows",
    "parse_duration_presets",
    "rank_and_filter_candidates",
    "score_candidate_window",
    "validate_candidate_window",
    "validate_detection_config",
]
