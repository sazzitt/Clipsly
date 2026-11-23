"""Clipsly Phase 16: Highlight Schemas and Data Transfer Objects.

Defines Pydantic request and response schemas for AI highlight detection,
retrieval, candidate ranking, fine-tuning, and review lifecycle.
"""
from datetime import datetime
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class HighlightDetectionRequest(BaseModel):
    """Parameters for initiating an AI highlight detection job."""

    target_duration_presets: List[str] = Field(
        default=["15-30", "30-60", "60-90"],
        description="Target duration windows in seconds",
    )
    min_duration_seconds: float = Field(
        default=15.0,
        ge=10.0,
        le=180.0,
        description="Minimum highlight duration in seconds",
    )
    max_duration_seconds: float = Field(
        default=90.0,
        ge=10.0,
        le=180.0,
        description="Maximum highlight duration in seconds",
    )
    min_score: float = Field(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="Minimum composite viral score threshold (0-100)",
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of candidate highlights to retain",
    )
    overlap_threshold: float = Field(
        default=0.45,
        ge=0.1,
        le=0.9,
        description="Non-maximum suppression overlap threshold",
    )
    hook_weight: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="Weight of hook strength (default 30%)",
    )
    coherence_weight: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="Weight of thought completeness / coherence (default 30%)",
    )
    density_weight: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Weight of information density / pacing (default 25%)",
    )
    sentiment_weight: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight of sentiment / conviction / emotion (default 15%)",
    )
    force_redetect: bool = Field(
        default=False,
        description="If true, supersedes previous candidate highlights for this video",
    )


class HighlightResponse(BaseModel):
    """Detailed representation of a detected or reviewed highlight."""

    id: str
    video_id: str
    transcript_id: str
    start_ms: int
    end_ms: int
    duration_ms: int
    hook_sentence: str
    summary: Optional[str] = None
    transcript_excerpt: Optional[str] = None
    hook_score: float
    coherence_score: float
    density_score: float
    sentiment_score: float
    composite_score: float
    rank: Optional[int] = None
    scoring_version: str = "v1"
    explanation: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    detection_metadata: Optional[Dict[str, Any]] = None
    category: str = "Insight"
    detection_method: str = "HEURISTIC"
    status: str = "CANDIDATE"
    reviewed_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, h: Any) -> "HighlightResponse":
        """Constructs response model from SQLAlchemy Highlight instance."""
        warnings: List[str] = []
        if getattr(h, "warnings_json", None):
            try:
                parsed = json.loads(h.warnings_json)
                if isinstance(parsed, list):
                    warnings = parsed
            except Exception:
                pass

        metadata: Dict[str, Any] = {}
        if getattr(h, "detection_metadata_json", None):
            try:
                parsed = json.loads(h.detection_metadata_json)
                if isinstance(parsed, dict):
                    metadata = parsed
            except Exception:
                pass

        return cls(
            id=h.id,
            video_id=h.video_id,
            transcript_id=h.transcript_id,
            start_ms=h.start_ms,
            end_ms=h.end_ms,
            duration_ms=h.duration_ms,
            hook_sentence=h.hook_sentence,
            summary=h.summary,
            transcript_excerpt=h.transcript_excerpt,
            hook_score=h.hook_score,
            coherence_score=h.coherence_score,
            density_score=h.density_score,
            sentiment_score=h.sentiment_score,
            composite_score=h.composite_score,
            rank=h.rank,
            scoring_version=h.scoring_version,
            explanation=h.explanation,
            warnings=warnings,
            detection_metadata=metadata,
            category=h.category,
            detection_method=h.detection_method,
            status=h.status,
            reviewed_at=h.reviewed_at.isoformat() if h.reviewed_at else None,
            rejection_reason=h.rejection_reason,
            created_at=h.created_at.isoformat() if h.created_at else None,
            updated_at=h.updated_at.isoformat() if h.updated_at else None,
        )


class HighlightListResponse(BaseModel):
    """List response for candidate highlights."""

    video_id: str
    total: int
    highlights: List[HighlightResponse]


class HighlightDetectionJobResponse(BaseModel):
    """Response returned upon submitting an asynchronous highlight detection job."""

    job_id: str
    video_id: str
    status: str
    progress_percent: float
    current_step: str
    created_at: str
    highlights: Optional[List[HighlightResponse]] = None


class HighlightUpdateRequest(BaseModel):
    """Request payload for updating or fine-tuning a highlight."""

    start_ms: Optional[int] = Field(None, ge=0, description="Updated start time in milliseconds")
    end_ms: Optional[int] = Field(None, gt=0, description="Updated end time in milliseconds")
    summary: Optional[str] = Field(None, description="Updated editorial summary")
    status: Optional[str] = Field(None, description="Status update (CANDIDATE, ACCEPTED, REJECTED)")


class HighlightRejectRequest(BaseModel):
    """Request payload for rejecting a candidate highlight."""

    rejection_reason: Optional[str] = Field(
        None,
        description="Optional rationale for rejection (e.g., 'Weak hook', 'Off-topic')",
    )
