from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_database
from backend.app.core.exceptions import NotFoundError, NotImplementedFeatureError
from backend.app.models.highlight import Highlight

router = APIRouter(prefix="/highlights", tags=["Highlights"])


class HighlightUpdateRequest(BaseModel):
    status: Optional[str] = Field(None, description="Status update (e.g. CANDIDATE, ACCEPTED, REJECTED)")
    summary: Optional[str] = Field(None, description="Updated editorial summary")


@router.get(
    "/{video_id}",
    status_code=status.HTTP_200_OK,
    summary="List Video Highlights",
    description="Retrieves ranked highlight candidates for a video ordered by viral composite score."
)
async def list_highlights(
    video_id: str,
    min_score: float = Query(0.0, ge=0.0, le=100.0, description="Minimum composite score filter"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by candidate status"),
    db: AsyncSession = Depends(get_database)
):
    """Retrieves ranked highlights for a video."""
    filters = [Highlight.video_id == video_id, Highlight.composite_score >= min_score]
    if status_filter:
        filters.append(Highlight.status == status_filter)

    stmt = select(Highlight).where(*filters).order_by(Highlight.composite_score.desc())
    result = await db.execute(stmt)
    highlights = result.scalars().all()

    items = [
        {
            "id": h.id,
            "video_id": h.video_id,
            "transcript_id": h.transcript_id,
            "start_ms": h.start_ms,
            "end_ms": h.end_ms,
            "duration_ms": h.duration_ms,
            "hook_sentence": h.hook_sentence,
            "summary": h.summary,
            "hook_score": h.hook_score,
            "coherence_score": h.coherence_score,
            "density_score": h.density_score,
            "sentiment_score": h.sentiment_score,
            "composite_score": h.composite_score,
            "category": h.category,
            "detection_method": h.detection_method,
            "status": h.status,
            "created_at": h.created_at.isoformat() if h.created_at else None,
            "updated_at": h.updated_at.isoformat() if h.updated_at else None,
        }
        for h in highlights
    ]

    return {"video_id": video_id, "total": len(items), "highlights": items}


@router.get(
    "/detail/{highlight_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Highlight Details",
    description="Retrieves granular multi-dimensional scores for a specific highlight."
)
async def get_highlight(
    highlight_id: str,
    db: AsyncSession = Depends(get_database)
):
    """Retrieves single highlight details."""
    stmt = select(Highlight).where(Highlight.id == highlight_id)
    result = await db.execute(stmt)
    h = result.scalar_one_or_none()

    if not h:
        raise NotFoundError(f"Highlight with id '{highlight_id}' was not found.")

    return {
        "id": h.id,
        "video_id": h.video_id,
        "transcript_id": h.transcript_id,
        "start_ms": h.start_ms,
        "end_ms": h.end_ms,
        "duration_ms": h.duration_ms,
        "hook_sentence": h.hook_sentence,
        "summary": h.summary,
        "hook_score": h.hook_score,
        "coherence_score": h.coherence_score,
        "density_score": h.density_score,
        "sentiment_score": h.sentiment_score,
        "composite_score": h.composite_score,
        "category": h.category,
        "detection_method": h.detection_method,
        "status": h.status,
        "created_at": h.created_at.isoformat() if h.created_at else None,
        "updated_at": h.updated_at.isoformat() if h.updated_at else None,
    }


@router.patch(
    "/{highlight_id}",
    status_code=status.HTTP_200_OK,
    summary="Update Highlight",
    description="Updates candidate review status or editorial summary."
)
async def update_highlight(
    highlight_id: str,
    payload: HighlightUpdateRequest,
    db: AsyncSession = Depends(get_database)
):
    """Updates candidate highlight status."""
    stmt = select(Highlight).where(Highlight.id == highlight_id)
    result = await db.execute(stmt)
    h = result.scalar_one_or_none()

    if not h:
        raise NotFoundError(f"Highlight with id '{highlight_id}' was not found.")

    if payload.status is not None:
        h.status = payload.status
    if payload.summary is not None:
        h.summary = payload.summary

    await db.commit()
    await db.refresh(h)

    return {
        "id": h.id,
        "video_id": h.video_id,
        "status": h.status,
        "summary": h.summary,
    }


@router.post(
    "/detect",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Detect Highlights",
    description="Runs heuristic or LLM highlight scoring pipeline (activates in Phase 14)."
)
async def detect_highlights():
    """Placeholder endpoint for highlight detection. Activates in Phase 14."""
    raise NotImplementedFeatureError("AI highlight detection and scoring engine activates in Phase 14.")
