import os
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_database
from backend.app.core.config import settings
from backend.app.core.exceptions import AppException, InvalidFileFormatError, NotFoundError
from backend.app.models.clip import Clip
from backend.app.models.highlight import Highlight
from backend.app.models.processing_job import ProcessingJob
from backend.app.models.transcript import Transcript
from backend.app.models.video import Video
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.video import VideoDetailResponse, VideoUploadResponse
from backend.app.services.metadata_extraction import extract_and_persist_metadata
from backend.app.services.video_ingestion import ingest_video

router = APIRouter(prefix="/videos", tags=["Videos"])


@router.post(
    "/upload",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Video File",
    description="Streamingly ingests and validates an uploaded video file to local SSD storage."
)
async def upload_video(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_database)
):
    """Handles multipart video file upload, chunked streaming, validation, and registration."""
    video = await ingest_video(upload_file=file, db=db, request=request)
    return VideoUploadResponse(
        id=video.id,
        filename=video.filename,
        original_filename=video.original_filename,
        file_size_bytes=video.file_size_bytes,
        duration_seconds=video.duration_seconds,
        width=video.width,
        height=video.height,
        aspect_ratio=video.aspect_ratio,
        fps=video.fps,
        video_codec=video.video_codec,
        audio_codec=video.audio_codec,
        audio_sample_rate=video.audio_sample_rate,
        audio_channels=video.audio_channels,
        status=video.status,
        created_at=video.created_at.isoformat() if video.created_at else "",
        storage_label="Local SSD Storage",
    )


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
            "container_format": v.container_format,
            "orientation": v.orientation or ("portrait" if v.height > v.width else "square" if v.height == v.width else "landscape"),
            "metadata_status": v.metadata_status,
            "status": v.status,
            "error_message": v.error_message,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "updated_at": v.updated_at.isoformat() if v.updated_at else None,
        }
        for v in videos
    ]

    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


async def _build_video_detail_response(video: Video, db: AsyncSession) -> VideoDetailResponse:
    """Builds a comprehensive VideoDetailResponse including child entity counts and SSD verification."""
    video_id = video.id

    jobs_count_stmt = select(func.count(ProcessingJob.id)).where(ProcessingJob.video_id == video_id)
    jobs_count = (await db.execute(jobs_count_stmt)).scalar_one()

    clips_count_stmt = select(func.count(Clip.id)).where(Clip.video_id == video_id)
    clips_count = (await db.execute(clips_count_stmt)).scalar_one()

    transcripts_count_stmt = select(func.count(Transcript.id)).where(Transcript.video_id == video_id)
    transcripts_count = (await db.execute(transcripts_count_stmt)).scalar_one()

    highlights_count_stmt = select(func.count(Highlight.id)).where(Highlight.video_id == video_id)
    highlights_count = (await db.execute(highlights_count_stmt)).scalar_one()

    # Verify physical file existence on disk
    file_exists = False
    if video.file_path:
        p = Path(video.file_path)
        if not p.is_absolute():
            p = settings.STORAGE_DIR.parent / video.file_path
        file_exists = p.exists()

    has_audio = bool(video.audio_codec and video.audio_codec.lower() not in ("none", "unknown", ""))

    return VideoDetailResponse(
        id=video.id,
        filename=video.filename,
        original_filename=video.original_filename,
        storage_label="Local SSD Storage",
        file_size_bytes=video.file_size_bytes,
        duration_seconds=video.duration_seconds,
        width=video.width,
        height=video.height,
        aspect_ratio=video.aspect_ratio,
        fps=video.fps,
        video_codec=video.video_codec,
        video_codec_profile=video.video_codec_profile,
        pixel_format=video.pixel_format,
        bit_depth=video.bit_depth,
        video_bitrate=video.video_bitrate,
        rotation=video.rotation or 0,
        orientation=video.orientation or ("portrait" if video.height > video.width else "square" if video.height == video.width else "landscape"),
        has_audio=has_audio,
        audio_codec=video.audio_codec,
        audio_sample_rate=video.audio_sample_rate,
        audio_channels=video.audio_channels,
        channel_layout=video.channel_layout,
        audio_bitrate=video.audio_bitrate,
        container_format=video.container_format,
        bitrate=video.bitrate,
        status=video.status,
        metadata_status=video.metadata_status or "COMPLETED",
        metadata_extracted_at=video.metadata_extracted_at.isoformat() if video.metadata_extracted_at else None,
        error_message=video.error_message,
        file_exists=file_exists,
        processing_jobs_count=jobs_count,
        clips_count=clips_count,
        transcripts_count=transcripts_count,
        highlights_count=highlights_count,
        created_at=video.created_at.isoformat() if video.created_at else None,
        updated_at=video.updated_at.isoformat() if video.updated_at else None,
    )


@router.get(
    "/{video_id}",
    response_model=VideoDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Video Details",
    description="Retrieves technical stream metadata, audio characteristics, and entity counts for an individual video."
)
async def get_video(
    video_id: str,
    db: AsyncSession = Depends(get_database)
):
    """Retrieves a single video by its UUID with full technical metadata and associated counts."""
    stmt = select(Video).where(Video.id == video_id)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()

    if not video:
        raise NotFoundError(f"Video with id '{video_id}' was not found.")

    return await _build_video_detail_response(video, db)


@router.post(
    "/{video_id}/metadata/refresh",
    response_model=VideoDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh Video Metadata",
    description="Forces FFprobe re-extraction and updates stored technical metadata for a source video asset."
)
async def refresh_video_metadata(
    video_id: str,
    db: AsyncSession = Depends(get_database)
):
    """Forces FFprobe re-extraction on the physical disk asset and updates the database record."""
    video = await extract_and_persist_metadata(video_id=video_id, db=db)
    return await _build_video_detail_response(video, db)


@router.get(
    "/{video_id}/stream",
    summary="Stream Video (HTTP Range Support)",
    description="Streams video content supporting partial byte ranges (HTTP 206) for smooth seeking in browsers."
)
async def stream_video(
    video_id: str,
    request: Request,
    db: AsyncSession = Depends(get_database)
):
    """Secure local video streaming endpoint supporting HTTP Range headers (RFC 9110) for HTML5 video seeking."""
    stmt = select(Video).where(Video.id == video_id)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()

    if not video:
        raise NotFoundError(f"Video with id '{video_id}' was not found.")

    if not video.file_path:
        raise NotFoundError("Video record contains no physical storage path.")

    file_path = Path(video.file_path)
    if not file_path.is_absolute():
        file_path = settings.STORAGE_DIR.parent / video.file_path

    # Security: Path confinement validation
    resolved_path = file_path.resolve()
    if not resolved_path.is_relative_to(settings.STORAGE_DIR.resolve()):
        raise AppException(status_code=400, detail="Path traversal security violation detected.")

    if not resolved_path.exists():
        raise NotFoundError(f"Physical video file was not found on local storage disk ({resolved_path.name}).")

    file_size = resolved_path.stat().st_size
    if file_size == 0:
        raise InvalidFileFormatError("Video file on disk is empty (0 bytes).")

    ext = resolved_path.suffix.lower()
    media_type_map = {
        ".mp4": "video/mp4",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
    }
    media_type = media_type_map.get(ext, "application/octet-stream")

    range_header = request.headers.get("range")
    if not range_header or not range_header.startswith("bytes="):
        # Full content stream (200 OK)
        async def full_stream():
            chunk_size = 128 * 1024
            with open(resolved_path, "rb") as f:
                while chunk := f.read(chunk_size):
                    yield chunk

        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": media_type,
        }
        return StreamingResponse(full_stream(), status_code=status.HTTP_200_OK, headers=headers, media_type=media_type)

    # Parse Range header (RFC 9110)
    range_val = range_header.replace("bytes=", "").strip()
    try:
        if "-" not in range_val:
            return Response(
                status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
                headers={"Content-Range": f"bytes */{file_size}"}
            )

        parts = range_val.split("-", 1)
        if parts[0] == "":
            # Suffix range: bytes=-500 (last 500 bytes)
            suffix_len = int(parts[1])
            start = max(0, file_size - suffix_len)
            end = file_size - 1
        elif parts[1] == "":
            # Prefix range: bytes=500- (from 500 to end)
            start = int(parts[0])
            end = file_size - 1
        else:
            # Full range: bytes=500-1000
            start = int(parts[0])
            end = int(parts[1])

        if start >= file_size or start < 0 or end >= file_size or start > end:
            return Response(
                status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
                headers={"Content-Range": f"bytes */{file_size}"}
            )
    except (ValueError, TypeError):
        return Response(
            status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
            headers={"Content-Range": f"bytes */{file_size}"}
        )

    content_length = end - start + 1

    async def range_stream():
        chunk_size = 128 * 1024
        bytes_left = content_length
        with open(resolved_path, "rb") as f:
            f.seek(start)
            while bytes_left > 0:
                read_amount = min(chunk_size, bytes_left)
                chunk = f.read(read_amount)
                if not chunk:
                    break
                bytes_left -= len(chunk)
                yield chunk

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": media_type,
    }
    return StreamingResponse(range_stream(), status_code=status.HTTP_206_PARTIAL_CONTENT, headers=headers, media_type=media_type)


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
