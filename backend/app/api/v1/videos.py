from typing import Any, Dict
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_database
from backend.app.core.exceptions import NotFoundError, NotImplementedFeatureError
from backend.app.models.video import Video
from backend.app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/videos", tags=["Videos"])


@router.post(
    "/upload",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Upload Video File",
    description="Video file upload and ingestion pipeline (activates in Phase 12)."
)
async def upload_video():
    """Placeholder endpoint for video file upload. Activates in Phase 12."""
    raise NotImplementedFeatureError("Video upload and chunked file ingestion pipeline will be activated in Phase 12.")


@router.get(
    "",
    response_model=PaginatedResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List Videos",
    description="Returns a paginated list of ingested source videos."
)
async def list_videos(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_database)
):
    """Retrieves all ingested videos from the database."""
    offset = (page - 1) * limit
    total_stmt = select(func.count(Video.id))
    total_result = await db.execute(total_stmt)
    total = total_result.scalar_one()

    stmt = select(Video).order_by(Video.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    videos = result.scalars().all()

    items = [
        {
            "id": v.id,
            "filename": v.filename,
            "original_filename": v.original_filename,
            "file_size_bytes": v.file_size_bytes,
            "duration_seconds": v.duration_seconds,
            "width": v.width,
            "height": v.height,
            "aspect_ratio": v.aspect_ratio,
            "fps": v.fps,
            "video_codec": v.video_codec,
            "audio_codec": v.audio_codec,
            "status": v.status,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "updated_at": v.updated_at.isoformat() if v.updated_at else None,
        }
        for v in videos
    ]

    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{video_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Video Details",
    description="Retrieves technical stream metadata for an individual video."
)
async def get_video(
    video_id: str,
    db: AsyncSession = Depends(get_database)
):
    """Retrieves a single video by its UUID."""
    stmt = select(Video).where(Video.id == video_id)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()

    if not video:
        raise NotFoundError(f"Video with id '{video_id}' was not found.")

    return {
        "id": video.id,
        "filename": video.filename,
        "original_filename": video.original_filename,
        "file_path": video.file_path,
        "file_size_bytes": video.file_size_bytes,
        "duration_seconds": video.duration_seconds,
        "width": video.width,
        "height": video.height,
        "aspect_ratio": video.aspect_ratio,
        "fps": video.fps,
        "video_codec": video.video_codec,
        "audio_codec": video.audio_codec,
        "status": video.status,
        "created_at": video.created_at.isoformat() if video.created_at else None,
        "updated_at": video.updated_at.isoformat() if video.updated_at else None,
    }


@router.delete(
    "/{video_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Video",
    description="Deletes a video and its cascading child records from the database."
)
async def delete_video(
    video_id: str,
    db: AsyncSession = Depends(get_database)
):
    """Deletes a video from the database."""
    stmt = select(Video).where(Video.id == video_id)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()

    if not video:
        raise NotFoundError(f"Video with id '{video_id}' was not found.")

    await db.delete(video)
    await db.commit()
    return {"success": True, "id": video_id}
