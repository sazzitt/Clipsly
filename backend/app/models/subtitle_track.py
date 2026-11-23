from typing import List, Optional
import uuid
from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class SubtitleTrack(Base, TimestampMixin):
    """Entity: subtitle_tracks
    Represents an authored or generated subtitle track linked to a short-form clip.
    (docs/19-SUBTITLE-API-CONTRACTS.md section 2.1)
    """
    __tablename__ = "subtitle_tracks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    clip_id: Mapped[str] = mapped_column(String(36), ForeignKey("clips.id", ondelete="CASCADE"), nullable=False)
    transcript_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("transcripts.id", ondelete="SET NULL"), nullable=True
    )
    preset_name: Mapped[str] = mapped_column(String(64), nullable=False, default="KARAOKE_AMBER")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    ass_file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    compile_status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    custom_style_overrides: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    clip: Mapped["Clip"] = relationship("Clip", back_populates="subtitle_tracks")
    transcript: Mapped[Optional["Transcript"]] = relationship("Transcript")
    events: Mapped[List["SubtitleEvent"]] = relationship(
        "SubtitleEvent",
        back_populates="track",
        cascade="all, delete-orphan",
        order_by="SubtitleEvent.sequence_index",
    )

    __table_args__ = (
        Index("idx_subtitle_tracks_clip_id", "clip_id"),
        Index("idx_subtitle_tracks_transcript_id", "transcript_id"),
        Index("idx_subtitle_tracks_is_active", "clip_id", "is_active"),
    )
