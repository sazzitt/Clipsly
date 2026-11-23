import uuid
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class SubtitleEvent(Base, TimestampMixin):
    """Entity: subtitle_events
    Stores individual caption bursts and line-level dialogue with word timings.
    (docs/19-SUBTITLE-API-CONTRACTS.md section 2.2)
    """
    __tablename__ = "subtitle_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    track_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subtitle_tracks.id", ondelete="CASCADE"), nullable=False
    )
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    words_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array of normalized word timing objects
    style_name: Mapped[str] = mapped_column(String(64), nullable=False, default="Default")
    is_modified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    track: Mapped["SubtitleTrack"] = relationship("SubtitleTrack", back_populates="events")

    __table_args__ = (
        CheckConstraint("start_ms >= 0 AND end_ms > start_ms", name="chk_subtitle_event_timing"),
        CheckConstraint("sequence_index >= 0", name="chk_subtitle_event_sequence"),
        Index("idx_subtitle_events_track_id", "track_id"),
        Index("idx_subtitle_events_timing", "track_id", "start_ms", "end_ms"),
    )
