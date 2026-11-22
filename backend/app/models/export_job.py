from datetime import datetime
from typing import Optional
import uuid
from sqlalchemy import BigInteger, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base


class ExportJob(Base):
    """Entity: export_jobs
    Tracks final MP4 rendering jobs executed via NVIDIA NVENC hardware acceleration.
    (docs/04-DATABASE.md section 2.7)
    """
    __tablename__ = "export_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    clip_id: Mapped[str] = mapped_column(String(36), ForeignKey("clips.id", ondelete="CASCADE"), nullable=False)
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    output_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    output_path: Mapped[str] = mapped_column(String(512), nullable=False)
    resolution: Mapped[str] = mapped_column(String(16), nullable=False, default="1080x1920")
    fps: Mapped[float] = mapped_column(Float, nullable=False, default=30.0)
    encoder: Mapped[str] = mapped_column(String(32), nullable=False, default="h264_nvenc")
    render_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED")
    progress_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    process_pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    clip: Mapped["Clip"] = relationship("Clip", back_populates="export_jobs")
    video: Mapped["Video"] = relationship("Video", back_populates="export_jobs")

    __table_args__ = (
        CheckConstraint("progress_percent >= 0.0 AND progress_percent <= 100.0", name="chk_export_progress"),
        Index("idx_exports_clip_id", "clip_id"),
        Index("idx_exports_video_id", "video_id"),
        Index("idx_exports_status", "status"),
    )
