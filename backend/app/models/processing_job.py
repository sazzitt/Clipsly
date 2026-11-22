from datetime import datetime
from typing import Optional
import uuid
from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class ProcessingJob(Base, TimestampMixin):
    """Entity: processing_jobs
    Tracks execution state, percentage progress, and errors for background pipeline tasks.
    (docs/04-DATABASE.md section 2.2)
    """
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED")
    progress_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_step: Mapped[str] = mapped_column(String(64), nullable=False, default="Queued")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    process_pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship back to parent Video
    video: Mapped["Video"] = relationship("Video", back_populates="processing_jobs")

    __table_args__ = (
        CheckConstraint("progress_percent >= 0.0 AND progress_percent <= 100.0", name="chk_job_progress"),
        Index("idx_jobs_video_id", "video_id"),
        Index("idx_jobs_status", "status"),
        Index("idx_jobs_created_at", "created_at"),
    )
