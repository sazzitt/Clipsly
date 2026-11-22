from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base


class ApplicationSetting(Base):
    """Entity: application_settings
    Key-value configuration store for hardware settings, default styling presets, and user preferences.
    (docs/04-DATABASE.md section 2.8)
    """
    __tablename__ = "application_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="GENERAL")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
