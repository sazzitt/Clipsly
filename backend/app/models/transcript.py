from typing import List
import uuid
from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class Transcript(Base, TimestampMixin):
    """Entity: transcripts
    Header record for a speech-to-text transcription run.
    (docs/04-DATABASE.md section 2.3)
    """
    __tablename__ = "transcripts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(32), nullable=False)
    compute_type: Mapped[str] = mapped_column(String(32), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processing_time_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    video: Mapped["Video"] = relationship("Video", back_populates="transcripts")
    segments: Mapped[List["TranscriptSegment"]] = relationship(
        "TranscriptSegment", back_populates="transcript", cascade="all, delete-orphan"
    )
    highlights: Mapped[List["Highlight"]] = relationship(
        "Highlight", back_populates="transcript", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("word_count >= 0", name="chk_word_count"),
        Index("idx_transcripts_video_id", "video_id"),
        Index("idx_transcripts_is_active", "video_id", "is_active"),
    )
