from datetime import datetime
from typing import List, Optional
import uuid
from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class Highlight(Base, TimestampMixin):
    """Entity: highlights
    Stores algorithmically scored candidate segments detected across the transcript.
    (docs/04-DATABASE.md section 2.5)
    """
    __tablename__ = "highlights"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    transcript_id: Mapped[str] = mapped_column(String(36), ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    hook_sentence: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transcript_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hook_score: Mapped[float] = mapped_column(Float, nullable=False)
    coherence_score: Mapped[float] = mapped_column(Float, nullable=False)
    density_score: Mapped[float] = mapped_column(Float, nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scoring_version: Mapped[str] = mapped_column(String(16), nullable=False, default="v1")
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    warnings_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detection_metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="Insight")
    detection_method: Mapped[str] = mapped_column(String(32), nullable=False, default="HEURISTIC")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="CANDIDATE")
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    video: Mapped["Video"] = relationship("Video", back_populates="highlights")
    transcript: Mapped["Transcript"] = relationship("Transcript", back_populates="highlights")
    clips: Mapped[List["Clip"]] = relationship("Clip", back_populates="highlight")

    __table_args__ = (
        CheckConstraint("start_ms >= 0 AND end_ms > start_ms", name="chk_highlight_timing"),
        CheckConstraint("composite_score >= 0.0 AND composite_score <= 100.0", name="chk_composite_score"),
        Index("idx_highlights_video_score", "video_id", "composite_score"),
        Index("idx_highlights_status", "video_id", "status"),
        Index("idx_highlights_transcript_id", "transcript_id"),
    )
