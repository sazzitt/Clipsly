from typing import List, Optional
import uuid
from sqlalchemy import BigInteger, CheckConstraint, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class Video(Base, TimestampMixin):
    """Entity: videos
    Stores metadata and technical stream characteristics for uploaded long-form source videos.
    (docs/04-DATABASE.md section 2.1)
    """
    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(16), nullable=False)
    fps: Mapped[float] = mapped_column(Float, nullable=False)
    video_codec: Mapped[str] = mapped_column(String(32), nullable=False)
    audio_codec: Mapped[str] = mapped_column(String(32), nullable=False)
    audio_sample_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    audio_channels: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="UPLOADED")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships with CASCADE deletion
    processing_jobs: Mapped[List["ProcessingJob"]] = relationship(
        "ProcessingJob", back_populates="video", cascade="all, delete-orphan"
    )
    transcripts: Mapped[List["Transcript"]] = relationship(
        "Transcript", back_populates="video", cascade="all, delete-orphan"
    )
    highlights: Mapped[List["Highlight"]] = relationship(
        "Highlight", back_populates="video", cascade="all, delete-orphan"
    )
    clips: Mapped[List["Clip"]] = relationship(
        "Clip", back_populates="video", cascade="all, delete-orphan"
    )
    export_jobs: Mapped[List["ExportJob"]] = relationship(
        "ExportJob", back_populates="video", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("file_size_bytes > 0", name="chk_video_size"),
        CheckConstraint("duration_seconds > 0.0", name="chk_video_duration"),
        CheckConstraint("width > 0 AND height > 0", name="chk_video_dimensions"),
        Index("idx_videos_status", "status"),
        Index("idx_videos_created_at", "created_at"),
    )
