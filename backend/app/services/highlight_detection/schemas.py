"""Clipsly Phase 16: Highlight Detection Schemas and Data Models.

Defines internal data structures for candidate generation, feature extraction,
heuristic scoring, and pipeline configuration.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DetectionConfig(BaseModel):
    """Configuration options for an AI highlight detection pipeline run."""

    target_duration_presets: List[str] = Field(
        default=["15-30", "30-60", "60-90"],
        description="Duration window buckets in seconds (e.g., '15-30', '30-60', '60-90')",
    )
    min_duration_seconds: float = Field(
        default=15.0,
        ge=10.0,
        le=180.0,
        description="Minimum candidate duration in seconds",
    )
    max_duration_seconds: float = Field(
        default=90.0,
        ge=10.0,
        le=180.0,
        description="Maximum candidate duration in seconds",
    )
    min_score: float = Field(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="Minimum overall composite score required for candidate retention",
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of ranked highlight candidates to return",
    )
    overlap_threshold: float = Field(
        default=0.45,
        ge=0.1,
        le=0.9,
        description="Temporal intersection threshold above which lower-scoring candidates are suppressed",
    )
    hook_weight: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="Weight of Hook Strength in composite score (default 30%)",
    )
    coherence_weight: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="Weight of Coherence in composite score (default 30%)",
    )
    density_weight: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Weight of Information Density in composite score (default 25%)",
    )
    sentiment_weight: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight of Emotional / Sentiment Signal in composite score (default 15%)",
    )
    force_redetect: bool = Field(
        default=False,
        description="If true, supersedes previous candidate highlights for this video",
    )


@dataclass
class CandidateWindow:
    """A contiguous slice of transcript utterances forming a potential highlight."""

    start_ms: int
    end_ms: int
    duration_ms: int
    start_segment_idx: int
    end_segment_idx: int
    text: str
    segments: List[Any] = field(default_factory=list)
    words: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        return self.duration_ms / 1000.0


@dataclass
class ScoringBreakdown:
    """Detailed component scores, explanations, and warnings for a candidate."""

    hook_score: float  # 0.0 to 100.0
    coherence_score: float  # 0.0 to 100.0
    density_score: float  # 0.0 to 100.0
    sentiment_score: float  # 0.0 to 100.0
    composite_score: float  # 0.0 to 100.0
    hook_sentence: str
    summary: str
    category: str  # "Insight", "Story", "Punchline", "Discussion", "Question"
    explanation: str
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScoredCandidate:
    """A fully scored, ranked, and explainable highlight candidate."""

    window: CandidateWindow
    scores: ScoringBreakdown
    rank: int = 0
    scoring_version: str = "v1"

    @property
    def start_ms(self) -> int:
        return self.window.start_ms

    @property
    def end_ms(self) -> int:
        return self.window.end_ms

    @property
    def duration_ms(self) -> int:
        return self.window.duration_ms

    @property
    def composite_score(self) -> float:
        return self.scores.composite_score
