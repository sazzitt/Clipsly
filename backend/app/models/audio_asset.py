import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class AudioAsset(Base, TimestampMixin):
    """Entity: audio_assets
    Stores preprocessed, transcription-ready 16kHz mono PCM WAV audio assets extracted from source videos.
    (docs/04-DATABASE.md section 2.10)
    """
    __tablename__ = "audio_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, unique=True)
    job_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("processing_jobs.id", ondelete="SET NULL"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False, default="wav")
    codec: Mapped[str] = mapped_column(String(32), nullable=False, default="pcm_s16le")
    sample_rate: Mapped[int] = mapped_column(Integer, nullable=False, default=16000)
    channels: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    channel_layout: Mapped[str] = mapped_column(String(32), nullable=False, default="mono")
    bit_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=16)
    source_stream_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="COMPLETED")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    video: Mapped["Video"] = relationship("Video", back_populates="audio_asset")
    job: Mapped[Optional["ProcessingJob"]] = relationship("ProcessingJob")

    __table_args__ = (
        CheckConstraint("file_size_bytes > 0", name="chk_audio_size"),
        CheckConstraint("duration_seconds > 0.0", name="chk_audio_duration"),
        CheckConstraint("sample_rate = 16000", name="chk_audio_sample_rate"),
        CheckConstraint("channels = 1", name="chk_audio_channels"),
        Index("idx_audio_assets_video_id", "video_id"),
        Index("idx_audio_assets_status", "status"),
    )
