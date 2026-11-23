from typing import List, Optional
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
    audio_asset_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("audio_assets.id", ondelete="SET NULL"), nullable=True
    )
    model_name: Mapped[str] = mapped_column(String(32), nullable=False)
    compute_type: Mapped[str] = mapped_column(String(32), nullable=False)
    device: Mapped[str] = mapped_column(String(16), nullable=False, default="cuda")
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    language_probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="COMPLETED")
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    segment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    audio_duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    processing_time_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    video: Mapped["Video"] = relationship("Video", back_populates="transcripts")
    audio_asset: Mapped[Optional["AudioAsset"]] = relationship("AudioAsset")
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
        Index("idx_transcripts_audio_asset_id", "audio_asset_id"),
        Index("idx_transcripts_status", "status"),
    )
