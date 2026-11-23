"""Clipsly Phase 16: Highlight REST API Endpoints.

Provides endpoints for listing, viewing, updating, reviewing (accept/reject),
and triggering AI highlight detection.
"""
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_database
from backend.app.core.exceptions import ConflictError, InvalidFileFormatError, NotFoundError
from backend.app.models.highlight import Highlight
from backend.app.models.processing_job import ProcessingJob
from backend.app.models.video import Video
from backend.app.schemas.highlight import (
    HighlightDetectionJobResponse,
    HighlightDetectionRequest,
    HighlightListResponse,
    HighlightRejectRequest,
    HighlightResponse,
    HighlightUpdateRequest,
)
from backend.app.services.highlight_detection.detector import (
    _active_detections,
    detect_highlights_pipeline,
)
from backend.app.services.highlight_detection.schemas import DetectionConfig
from backend.app.services.queue import job_queue

logger = logging.getLogger("clipsly.highlights_api")

router = APIRouter(prefix="/highlights", tags=["Highlights"])


class DetectHighlightBodyWithVideo(HighlightDetectionRequest):
    """Payload for global /detect endpoint containing video_id."""

    video_id: str = Field(..., description="ID of the video to detect highlights for")


@router.post(
    "/detect",
    response_model=HighlightDetectionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Detect Highlights (Global Route)",
    description="Submits an asynchronous highlight detection job via sequential JobQueueManager.",
)
async def detect_highlights_global(
    payload: DetectHighlightBodyWithVideo,
    db: AsyncSession = Depends(get_database),
):
    """Triggers highlight detection job for a specified video."""
    video = await db.get(Video, payload.video_id)
    if not video:
        raise NotFoundError(f"Video with id '{payload.video_id}' was not found.")

    if job_queue.is_video_active(payload.video_id) or payload.video_id in _active_detections:
        raise ConflictError(
            f"A job is already executing or queued for video '{payload.video_id}'.",
            details={"video_id": payload.video_id},
        )

    config = DetectionConfig(
        target_duration_presets=payload.target_duration_presets,
        min_duration_seconds=payload.min_duration_seconds,
        max_duration_seconds=payload.max_duration_seconds,
        min_score=payload.min_score,
        max_results=payload.max_results,
        overlap_threshold=payload.overlap_threshold,
        hook_weight=payload.hook_weight,
        coherence_weight=payload.coherence_weight,
        density_weight=payload.density_weight,
        sentiment_weight=payload.sentiment_weight,
        force_redetect=payload.force_redetect,
    )

    job_id = str(uuid.uuid4())
    job = ProcessingJob(
        id=job_id,
        video_id=payload.video_id,
        job_type="HIGHLIGHT_DETECTION",
        status="PENDING",
        progress_percent=0.0,
        current_step="Highlight detection job queued...",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    await job_queue.submit_job(
        job_id=job.id,
        video_id=payload.video_id,
        handler=detect_highlights_pipeline,
        job_kwargs={
            "video_id": payload.video_id,
            "job_id": job.id,
            "config": config,
        },
    )

    return HighlightDetectionJobResponse(
        job_id=job.id,
        video_id=payload.video_id,
        status="PENDING",
        progress_percent=0.0,
        current_step="Highlight detection job queued...",
        created_at=job.created_at.isoformat() if job.created_at else datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/{video_id}",
    response_model=HighlightListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Video Highlights",
    description="Retrieves ranked highlight candidates for a video ordered by rank and score.",
)
async def list_highlights(
    video_id: str,
    min_score: float = Query(0.0, ge=0.0, le=100.0, description="Minimum composite score filter"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by candidate status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: AsyncSession = Depends(get_database),
):
    """Retrieves ranked highlights for a video."""
    filters = [Highlight.video_id == video_id, Highlight.composite_score >= min_score]
    if status_filter:
        filters.append(Highlight.status == status_filter)
    if category:
        filters.append(Highlight.category == category)

    stmt = select(Highlight).where(*filters).order_by(Highlight.rank.asc(), Highlight.composite_score.desc())
    result = await db.execute(stmt)
    highlights = result.scalars().all()

    items = [HighlightResponse.from_orm_model(h) for h in highlights]
    return HighlightListResponse(video_id=video_id, total=len(items), highlights=items)


@router.get(
    "/detail/{highlight_id}",
    response_model=HighlightResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Highlight Details",
    description="Retrieves granular multi-dimensional scores and explanations for a specific highlight.",
)
async def get_highlight(
    highlight_id: str,
    db: AsyncSession = Depends(get_database),
):
    """Retrieves single highlight details."""
    stmt = select(Highlight).where(Highlight.id == highlight_id)
    result = await db.execute(stmt)
    h = result.scalar_one_or_none()

    if not h:
        raise NotFoundError(f"Highlight with id '{highlight_id}' was not found.")

    return HighlightResponse.from_orm_model(h)


@router.patch(
    "/{highlight_id}",
    response_model=HighlightResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Highlight",
    description="Updates candidate timestamps, editorial summary, or status.",
)
async def update_highlight(
    highlight_id: str,
    payload: HighlightUpdateRequest,
    db: AsyncSession = Depends(get_database),
):
    """Updates candidate highlight timestamps, summary, or status."""
    stmt = select(Highlight).where(Highlight.id == highlight_id)
    result = await db.execute(stmt)
    h = result.scalar_one_or_none()

    if not h:
        raise NotFoundError(f"Highlight with id '{highlight_id}' was not found.")

    if payload.start_ms is not None:
        if payload.start_ms < 0:
            raise InvalidFileFormatError("start_ms must be non-negative.")
        h.start_ms = payload.start_ms

    if payload.end_ms is not None:
        h.end_ms = payload.end_ms

    if h.end_ms <= h.start_ms:
        raise InvalidFileFormatError("end_ms must be strictly greater than start_ms.")

    h.duration_ms = h.end_ms - h.start_ms

    if payload.summary is not None:
        h.summary = payload.summary

    if payload.status is not None:
        valid_statuses = {"CANDIDATE", "ACCEPTED", "REJECTED"}
        if payload.status not in valid_statuses:
            raise InvalidFileFormatError(f"Status must be one of {valid_statuses}")
        h.status = payload.status
        h.reviewed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(h)
    return HighlightResponse.from_orm_model(h)


@router.post(
    "/{highlight_id}/accept",
    response_model=HighlightResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept Highlight",
    description="Marks a candidate highlight as ACCEPTED for export/clipping.",
)
async def accept_highlight(
    highlight_id: str,
    db: AsyncSession = Depends(get_database),
):
    """Marks highlight status as ACCEPTED."""
    stmt = select(Highlight).where(Highlight.id == highlight_id)
    result = await db.execute(stmt)
    h = result.scalar_one_or_none()

    if not h:
        raise NotFoundError(f"Highlight with id '{highlight_id}' was not found.")

    h.status = "ACCEPTED"
    h.reviewed_at = datetime.now(timezone.utc)
    h.rejection_reason = None

    await db.commit()
    await db.refresh(h)
    return HighlightResponse.from_orm_model(h)


@router.post(
    "/{highlight_id}/reject",
    response_model=HighlightResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject Highlight",
    description="Marks a candidate highlight as REJECTED with an optional reason.",
)
async def reject_highlight(
    highlight_id: str,
    payload: Optional[HighlightRejectRequest] = None,
    db: AsyncSession = Depends(get_database),
):
    """Marks highlight status as REJECTED."""
    stmt = select(Highlight).where(Highlight.id == highlight_id)
    result = await db.execute(stmt)
    h = result.scalar_one_or_none()

    if not h:
        raise NotFoundError(f"Highlight with id '{highlight_id}' was not found.")

    h.status = "REJECTED"
    h.reviewed_at = datetime.now(timezone.utc)
    h.rejection_reason = payload.rejection_reason if payload else None

    await db.commit()
    await db.refresh(h)
    return HighlightResponse.from_orm_model(h)
