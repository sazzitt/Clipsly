import os
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_database
from backend.app.core.exceptions import NotFoundError, NotImplementedFeatureError
from backend.app.models.clip import Clip
from backend.app.models.highlight import Highlight
from backend.app.models.processing_job import ProcessingJob
from backend.app.models.transcript import Transcript
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
    description="Returns a paginated list of ingested source videos with search, filtering, and sorting."
)
async def list_videos(
    search: Optional[str] = Query(None, description="Search by filename or original filename"),
    video_status: Optional[str] = Query(None, alias="status", description="Filter by status (e.g. UPLOADED, READY, PROCESSING, FAILED)"),
    sort_by: str = Query("created_at", description="Field to sort by: created_at, duration_seconds, filename, file_size_bytes"),
    order: str = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_database)
):
    """Retrieves all ingested videos from the database with filtering and sorting."""
    offset = (page - 1) * limit
    filters = []

    if search:
        search_term = f"%{search.strip()}%"
        filters.append(
            or_(
                Video.filename.ilike(search_term),
                Video.original_filename.ilike(search_term),
            )
        )

    if video_status and video_status.strip() and video_status.upper() != "ALL":
        filters.append(Video.status == video_status.strip().upper())

    total_stmt = select(func.count(Video.id)).where(*filters)
    total_result = await db.execute(total_stmt)
    total = total_result.scalar_one()

    sort_mapping = {
        "created_at": Video.created_at,
        "duration_seconds": Video.duration_seconds,
        "filename": Video.filename,
        "file_size_bytes": Video.file_size_bytes,
        "original_filename": Video.original_filename,
    }
    sort_column = sort_mapping.get(sort_by, Video.created_at)
    order_clause = sort_column.asc() if order.lower() == "asc" else sort_column.desc()

    stmt = select(Video).where(*filters).order_by(order_clause).offset(offset).limit(limit)
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
            "audio_sample_rate": v.audio_sample_rate,
            "audio_channels": v.audio_channels,
            "status": v.status,
            "error_message": v.error_message,
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
    description="Retrieves technical stream metadata and entity counts for an individual video."
)
async def get_video(
    video_id: str,
    db: AsyncSession = Depends(get_database)
):
    """Retrieves a single video by its UUID with associated counts."""
    stmt = select(Video).where(Video.id == video_id)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()

    if not video:
        raise NotFoundError(f"Video with id '{video_id}' was not found.")

    # Count child entities
    jobs_count_stmt = select(func.count(ProcessingJob.id)).where(ProcessingJob.video_id == video_id)
    jobs_count = (await db.execute(jobs_count_stmt)).scalar_one()

    clips_count_stmt = select(func.count(Clip.id)).where(Clip.video_id == video_id)
    clips_count = (await db.execute(clips_count_stmt)).scalar_one()

    transcripts_count_stmt = select(func.count(Transcript.id)).where(Transcript.video_id == video_id)
    transcripts_count = (await db.execute(transcripts_count_stmt)).scalar_one()

    highlights_count_stmt = select(func.count(Highlight.id)).where(Highlight.video_id == video_id)
    highlights_count = (await db.execute(highlights_count_stmt)).scalar_one()

    file_exists = os.path.exists(video.file_path) if video.file_path else False

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
        "audio_sample_rate": video.audio_sample_rate,
        "audio_channels": video.audio_channels,
        "status": video.status,
        "error_message": video.error_message,
        "file_exists": file_exists,
        "processing_jobs_count": jobs_count,
        "clips_count": clips_count,
        "transcripts_count": transcripts_count,
        "highlights_count": highlights_count,
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
    purge_files: bool = Query(False, description="Also purge source video file from disk if present"),
    db: AsyncSession = Depends(get_database)
):
    """Deletes a video from the database, cascading relational children."""
    stmt = select(Video).where(Video.id == video_id)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()

    if not video:
        raise NotFoundError(f"Video with id '{video_id}' was not found.")

    file_unlinked = False
    if purge_files and video.file_path:
        try:
            if os.path.exists(video.file_path):
                os.remove(video.file_path)
                file_unlinked = True
        except OSError:
            pass

    await db.delete(video)
    await db.commit()
    return {"success": True, "id": video_id, "file_unlinked": file_unlinked}
