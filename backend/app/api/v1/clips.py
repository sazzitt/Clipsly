from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_database
from backend.app.core.exceptions import NotFoundError, NotImplementedFeatureError, ValidationError
from backend.app.models.clip import Clip
from backend.app.models.video import Video
from backend.app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/clips", tags=["Clips"])


class CreateClipRequest(BaseModel):
    video_id: str = Field(..., description="Parent Video UUID")
    highlight_id: Optional[str] = Field(None, description="Optional source Highlight UUID")
    title: str = Field("Untitled Clip", min_length=1, max_length=255)
    start_ms: int = Field(..., ge=0, description="Start timestamp in milliseconds")
    end_ms: int = Field(..., description="End timestamp in milliseconds")
    aspect_ratio_mode: str = Field("BLUR_PAD", description="CROP_CENTER, BLUR_PAD, FIT_LETTERBOX, AUTO_TRACK")
    subtitle_enabled: bool = Field(True)
    subtitle_style_preset: str = Field("KARAOKE_AMBER")
    subtitle_font_family: str = Field("Montserrat")
    subtitle_font_size: int = Field(24, ge=10, le=72)
    subtitle_primary_color: str = Field("#FFFFFF")
    subtitle_highlight_color: str = Field("#FFD700")
    subtitle_outline_color: str = Field("#000000")
    subtitle_outline_width: int = Field(3, ge=0, le=10)
    subtitle_vertical_position: str = Field("BOTTOM")
    custom_subtitle_text: Optional[str] = Field(None)


class UpdateClipRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    start_ms: Optional[int] = Field(None, ge=0)
    end_ms: Optional[int] = Field(None)
    aspect_ratio_mode: Optional[str] = Field(None)
    subtitle_enabled: Optional[bool] = Field(None)
    subtitle_style_preset: Optional[str] = Field(None)
    subtitle_font_family: Optional[str] = Field(None)
    subtitle_font_size: Optional[int] = Field(None, ge=10, le=72)
    subtitle_primary_color: Optional[str] = Field(None)
    subtitle_highlight_color: Optional[str] = Field(None)
    subtitle_outline_color: Optional[str] = Field(None)
    subtitle_outline_width: Optional[int] = Field(None, ge=0, le=10)
    subtitle_vertical_position: Optional[str] = Field(None)
    custom_subtitle_text: Optional[str] = Field(None)
    status: Optional[str] = Field(None)


def _serialize_clip(clip: Clip, video_filename: Optional[str] = None) -> Dict[str, Any]:
    return {
        "id": clip.id,
        "video_id": clip.video_id,
        "video_filename": video_filename,
        "highlight_id": clip.highlight_id,
        "title": clip.title,
        "start_ms": clip.start_ms,
        "end_ms": clip.end_ms,
        "duration_ms": clip.duration_ms,
        "aspect_ratio_mode": clip.aspect_ratio_mode,
        "subtitle_enabled": clip.subtitle_enabled,
        "subtitle_style_preset": clip.subtitle_style_preset,
        "subtitle_font_family": clip.subtitle_font_family,
        "subtitle_font_size": clip.subtitle_font_size,
        "subtitle_primary_color": clip.subtitle_primary_color,
        "subtitle_highlight_color": clip.subtitle_highlight_color,
        "subtitle_outline_color": clip.subtitle_outline_color,
        "subtitle_outline_width": clip.subtitle_outline_width,
        "subtitle_vertical_position": clip.subtitle_vertical_position,
        "custom_subtitle_text": clip.custom_subtitle_text,
        "status": clip.status,
        "created_at": clip.created_at.isoformat() if clip.created_at else None,
        "updated_at": clip.updated_at.isoformat() if clip.updated_at else None,
    }


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create Clip",
    description="Creates a new customized clip draft from timestamps or an approved highlight."
)
async def create_clip(
    payload: CreateClipRequest,
    db: AsyncSession = Depends(get_database)
):
    """Creates a new clip record."""
    if payload.end_ms <= payload.start_ms:
        raise ValidationError("Clip end_ms must be greater than start_ms.")

    duration_ms = payload.end_ms - payload.start_ms
    if duration_ms < 5000:
        raise ValidationError("Clip duration must be at least 5000 milliseconds (5.0s).")

    # Verify video existence
    v_stmt = select(Video).where(Video.id == payload.video_id)
    v_result = await db.execute(v_stmt)
    video = v_result.scalar_one_or_none()
    if not video:
        raise NotFoundError(f"Source video '{payload.video_id}' was not found.")

    clip = Clip(
        video_id=payload.video_id,
        highlight_id=payload.highlight_id,
        title=payload.title,
        start_ms=payload.start_ms,
        end_ms=payload.end_ms,
        duration_ms=duration_ms,
        aspect_ratio_mode=payload.aspect_ratio_mode,
        subtitle_enabled=payload.subtitle_enabled,
        subtitle_style_preset=payload.subtitle_style_preset,
        subtitle_font_family=payload.subtitle_font_family,
        subtitle_font_size=payload.subtitle_font_size,
        subtitle_primary_color=payload.subtitle_primary_color,
        subtitle_highlight_color=payload.subtitle_highlight_color,
        subtitle_outline_color=payload.subtitle_outline_color,
        subtitle_outline_width=payload.subtitle_outline_width,
        subtitle_vertical_position=payload.subtitle_vertical_position,
        custom_subtitle_text=payload.custom_subtitle_text,
        status="DRAFT",
    )
    db.add(clip)
    await db.commit()
    await db.refresh(clip)

    return _serialize_clip(clip, video_filename=video.filename)


@router.get(
    "",
    response_model=PaginatedResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List Clips",
    description="Retrieves a paginated list of clips with search, status filtering, and sorting."
)
async def list_clips(
    video_id: Optional[str] = Query(None, description="Filter clips by video UUID"),
    clip_status: Optional[str] = Query(None, alias="status", description="Filter clips by status"),
    search: Optional[str] = Query(None, description="Search clips by title"),
    sort_by: str = Query("created_at", description="Field to sort by: created_at, title, duration_ms, start_ms"),
    order: str = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_database)
):
    """Lists clips from the database with filtering and search."""
    offset = (page - 1) * limit
    filters = []

    if video_id:
        filters.append(Clip.video_id == video_id)
    if clip_status and clip_status.strip() and clip_status.upper() != "ALL":
        filters.append(Clip.status == clip_status.strip().upper())
    if search:
        filters.append(Clip.title.ilike(f"%{search.strip()}%"))

    count_stmt = select(func.count(Clip.id)).where(*filters)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    sort_mapping = {
        "created_at": Clip.created_at,
        "title": Clip.title,
        "duration_ms": Clip.duration_ms,
        "start_ms": Clip.start_ms,
        "status": Clip.status,
    }
    sort_column = sort_mapping.get(sort_by, Clip.created_at)
    order_clause = sort_column.asc() if order.lower() == "asc" else sort_column.desc()

    stmt = (
        select(Clip, Video.filename)
        .outerjoin(Video, Clip.video_id == Video.id)
        .where(*filters)
        .order_by(order_clause)
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    items = [_serialize_clip(clip, video_filename=v_filename) for clip, v_filename in rows]
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{clip_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Clip Details",
    description="Retrieves full timeline and subtitle styling configuration for a clip."
)
async def get_clip(
    clip_id: str,
    db: AsyncSession = Depends(get_database)
):
    """Retrieves single clip by ID."""
    stmt = (
        select(Clip, Video.filename)
        .outerjoin(Video, Clip.video_id == Video.id)
        .where(Clip.id == clip_id)
    )
    result = await db.execute(stmt)
    row = result.first()

    if not row:
        raise NotFoundError(f"Clip with id '{clip_id}' was not found.")

    clip, v_filename = row
    return _serialize_clip(clip, video_filename=v_filename)


@router.patch(
    "/{clip_id}",
    status_code=status.HTTP_200_OK,
    summary="Update Clip",
    description="Modifies clip timestamps, title, aspect ratio mode, or subtitle configuration."
)
async def update_clip(
    clip_id: str,
    payload: UpdateClipRequest,
    db: AsyncSession = Depends(get_database)
):
    """Updates clip configuration."""
    stmt = select(Clip).where(Clip.id == clip_id)
    result = await db.execute(stmt)
    clip = result.scalar_one_or_none()

    if not clip:
        raise NotFoundError(f"Clip with id '{clip_id}' was not found.")

    # Validate timing if updated
    new_start = payload.start_ms if payload.start_ms is not None else clip.start_ms
    new_end = payload.end_ms if payload.end_ms is not None else clip.end_ms

    if new_end <= new_start:
        raise ValidationError("Clip end_ms must be greater than start_ms.")
    if (new_end - new_start) < 5000:
        raise ValidationError("Clip duration must be at least 5000 milliseconds (5.0s).")

    clip.start_ms = new_start
    clip.end_ms = new_end
    clip.duration_ms = new_end - new_start

    update_fields = [
        "title", "aspect_ratio_mode", "subtitle_enabled", "subtitle_style_preset",
        "subtitle_font_family", "subtitle_font_size", "subtitle_primary_color",
        "subtitle_highlight_color", "subtitle_outline_color", "subtitle_outline_width",
        "subtitle_vertical_position", "custom_subtitle_text", "status"
    ]
    for field in update_fields:
        val = getattr(payload, field)
        if val is not None:
            setattr(clip, field, val)

    await db.commit()
    await db.refresh(clip)

    return _serialize_clip(clip)


@router.delete(
    "/{clip_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Clip",
    description="Deletes a clip and its related export records."
)
async def delete_clip(
    clip_id: str,
    db: AsyncSession = Depends(get_database)
):
    """Deletes a clip record."""
    stmt = select(Clip).where(Clip.id == clip_id)
    result = await db.execute(stmt)
    clip = result.scalar_one_or_none()

    if not clip:
        raise NotFoundError(f"Clip with id '{clip_id}' was not found.")

    await db.delete(clip)
    await db.commit()
    return {"success": True, "id": clip_id}


@router.get(
    "/{clip_id}/subtitles.ass",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Export Subtitles (ASS)",
    description="Generates styled Advanced SubStation Alpha (.ass) subtitle file (activates in Phase 15)."
)
async def get_clip_subtitles(clip_id: str):
    """Placeholder endpoint for ASS subtitle generation. Activates in Phase 15."""
    raise NotImplementedFeatureError("ASS subtitle rendering engine activates in Phase 15.")
