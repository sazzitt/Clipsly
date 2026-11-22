from typing import Optional
import uuid
from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class TranscriptSegment(Base, TimestampMixin):
    """Entity: transcript_segments
    Stores individual sentence-level utterances with complete word-level timestamp JSON arrays.
    (docs/04-DATABASE.md section 2.4)
    """
    __tablename__ = "transcript_segments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transcript_id: Mapped[str] = mapped_column(String(36), ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False)
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    words_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array of word objects
    avg_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    speaker_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Relationship back to Transcript
    transcript: Mapped["Transcript"] = relationship("Transcript", back_populates="segments")

    __table_args__ = (
        CheckConstraint("start_ms >= 0 AND end_ms > start_ms", name="chk_segment_timing"),
        CheckConstraint("segment_index >= 0", name="chk_segment_index"),
        Index("idx_segments_transcript_id", "transcript_id"),
        Index("idx_segments_timing", "transcript_id", "start_ms", "end_ms"),
    )
