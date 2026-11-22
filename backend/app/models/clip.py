from typing import List, Optional
import uuid
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class Clip(Base, TimestampMixin):
    """Entity: clips
    Stores user-customized short-form clips configured for 9:16 export.
    (docs/04-DATABASE.md section 2.6)
    """
    __tablename__ = "clips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    highlight_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("highlights.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled Clip")
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    aspect_ratio_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="BLUR_PAD")
    subtitle_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    subtitle_style_preset: Mapped[str] = mapped_column(String(64), nullable=False, default="KARAOKE_AMBER")
    subtitle_font_family: Mapped[str] = mapped_column(String(64), nullable=False, default="Montserrat")
    subtitle_font_size: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    subtitle_primary_color: Mapped[str] = mapped_column(String(16), nullable=False, default="#FFFFFF")
    subtitle_highlight_color: Mapped[str] = mapped_column(String(16), nullable=False, default="#FFD700")
    subtitle_outline_color: Mapped[str] = mapped_column(String(16), nullable=False, default="#000000")
    subtitle_outline_width: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    subtitle_vertical_position: Mapped[str] = mapped_column(String(16), nullable=False, default="BOTTOM")
    custom_subtitle_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")

    # Relationships
    video: Mapped["Video"] = relationship("Video", back_populates="clips")
    highlight: Mapped[Optional["Highlight"]] = relationship("Highlight", back_populates="clips")
    export_jobs: Mapped[List["ExportJob"]] = relationship(
        "ExportJob", back_populates="clip", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("start_ms >= 0 AND end_ms > start_ms", name="chk_clip_timing"),
        CheckConstraint("duration_ms >= 5000", name="chk_clip_duration"),
        Index("idx_clips_video_id", "video_id"),
        Index("idx_clips_status", "status"),
    )
