import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_database
from backend.app.core.config import settings
from backend.app.core.exceptions import (
    AppException,
    ConflictError,
    InvalidFileFormatError,
    NotFoundError,
    NotImplementedFeatureError,
    ValidationError,
)
from backend.app.models.clip import Clip
from backend.app.models.processing_job import ProcessingJob
from backend.app.models.video import Video
from backend.app.schemas.common import PaginatedResponse
from backend.app.services.clip_generation import (
    execute_clip_generation,
    normalize_conversion_mode,
)
from backend.app.services.queue import job_queue
from backend.app.services.subtitles import (
    SubtitleGenerateRequest,
    SubtitleTrackResponse,
    SubtitleValidationError,
    create_subtitle_track_for_clip,
    get_active_subtitle_track_for_clip,
)
from backend.app.models.subtitle_track import SubtitleTrack

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


class GenerateClipRequest(BaseModel):
    video_id: str = Field(..., description="Parent Video UUID")
    highlight_id: Optional[str] = Field(None, description="Optional source Highlight UUID")
    title: Optional[str] = Field("Untitled Clip", min_length=1, max_length=255)
    start_ms: int = Field(..., ge=0, description="Start timestamp in milliseconds")
    end_ms: int = Field(..., description="End timestamp in milliseconds")
    aspect_ratio_mode: Optional[str] = Field(None, description="Aspect ratio conversion mode")
    conversion_mode: Optional[str] = Field("BLUR_PAD", description="BLUR_PAD, CROP_CENTER, or FIT_LETTERBOX")
    target_width: int = Field(1080, ge=360, le=3840)
    target_height: int = Field(1920, ge=640, le=3840)
    target_fps: float = Field(30.0, ge=15.0, le=60.0)
    force_cpu: bool = Field(False, description="Force CPU libx264 encoding")


class UpdateClipRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    start_ms: Optional[int] = Field(None, ge=0)
    end_ms: Optional[int] = Field(None)
    aspect_ratio_mode: Optional[str] = Field(None)
    conversion_mode: Optional[str] = Field(None)
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
        "conversion_mode": clip.conversion_mode or clip.aspect_ratio_mode,
        "status": clip.status,
        "output_path": clip.output_path,
        "output_filename": clip.output_filename,
        "width": clip.width or 1080,
        "height": clip.height or 1920,
        "fps": clip.fps or 30.0,
        "video_codec": clip.video_codec or "h264",
        "audio_codec": clip.audio_codec,
        "file_size_bytes": clip.file_size_bytes,
        "encoding_backend": clip.encoding_backend,
        "error_message": clip.error_message,
        "completed_at": clip.completed_at.isoformat() if clip.completed_at else None,
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

    mode = normalize_conversion_mode(payload.aspect_ratio_mode)
    clip = Clip(
        video_id=payload.video_id,
        highlight_id=payload.highlight_id,
        title=payload.title,
        start_ms=payload.start_ms,
        end_ms=payload.end_ms,
        duration_ms=duration_ms,
        aspect_ratio_mode=mode,
        conversion_mode=mode,
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


@router.post(
    "/generate",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate 9:16 Vertical Clip",
    description="Submits a background job to slice and convert a video highlight into a vertical 9:16 MP4 clip."
)
async def generate_clip(
    payload: GenerateClipRequest,
    db: AsyncSession = Depends(get_database)
):
    """Initiates automatic 9:16 clip generation via the sequential JobQueueManager."""
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

    # Check if a job is already queued or executing for this video
    if job_queue.is_video_active(payload.video_id):
        raise ConflictError(
            f"A processing job is already queued or executing for video '{payload.video_id}'.",
            details={"video_id": payload.video_id},
        )

    mode = normalize_conversion_mode(payload.conversion_mode or payload.aspect_ratio_mode)

    clip = Clip(
        video_id=payload.video_id,
        highlight_id=payload.highlight_id,
        title=payload.title or "Untitled Clip",
        start_ms=payload.start_ms,
        end_ms=payload.end_ms,
        duration_ms=duration_ms,
        aspect_ratio_mode=mode,
        conversion_mode=mode,
        status="QUEUED",
    )
    db.add(clip)
    await db.flush()

    job = ProcessingJob(
        video_id=payload.video_id,
        job_type="CLIP_GENERATION",
        status="QUEUED",
        progress_percent=0.0,
        current_step="Queued for clip generation",
    )
    db.add(job)
    await db.commit()
    await db.refresh(clip)
    await db.refresh(job)

    # Submit to sequential background worker queue
    await job_queue.submit_job(
        job_id=job.id,
        video_id=payload.video_id,
        handler=execute_clip_generation,
        job_args=(job.id, clip.id, payload.model_dump(), payload.force_cpu),
    )

    return {
        "job_id": job.id,
        "clip_id": clip.id,
        "video_id": payload.video_id,
        "status": "QUEUED",
        "message": "Clip generation job successfully enqueued.",
        "clip": _serialize_clip(clip, video_filename=video.filename),
    }


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


@router.get(
    "/{clip_id}/stream",
    summary="Stream Clip Video (RFC 9110 HTTP Range)",
    description="Streams generated 9:16 vertical MP4 video clip supporting byte ranges for seeking in browsers."
)
async def stream_clip(
    clip_id: str,
    request: Request,
    db: AsyncSession = Depends(get_database)
):
    """Streams generated 9:16 vertical MP4 video clip supporting HTTP Range headers."""
    stmt = select(Clip).where(Clip.id == clip_id)
    res = await db.execute(stmt)
    clip = res.scalar_one_or_none()

    if not clip:
        raise NotFoundError(f"Clip with id '{clip_id}' was not found.")

    if not clip.output_path:
        raise NotFoundError(f"Clip '{clip_id}' has not been generated yet or has no output file.")

    file_path = Path(clip.output_path)
    if not file_path.is_absolute():
        file_path = settings.STORAGE_DIR.parent / clip.output_path

    resolved_path = file_path.resolve()
    if not resolved_path.is_relative_to(settings.STORAGE_DIR.resolve()):
        raise AppException(status_code=400, detail="Path traversal security violation detected.")

    if not resolved_path.exists():
        raise NotFoundError(f"Physical clip file '{resolved_path.name}' was not found on local storage disk.")

    file_size = resolved_path.stat().st_size
    if file_size == 0:
        raise InvalidFileFormatError("Clip file on disk is empty (0 bytes).")

    media_type = "video/mp4"

    range_header = request.headers.get("range")
    if not range_header or not range_header.startswith("bytes="):
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

    range_val = range_header.replace("bytes=", "").strip()
    try:
        if "-" not in range_val:
            return Response(
                status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
                headers={"Content-Range": f"bytes */{file_size}"}
            )

        parts = range_val.split("-", 1)
        if parts[0] == "":
            suffix_len = int(parts[1])
            if suffix_len == 0:
                start_byte = file_size
            else:
                start_byte = max(0, file_size - suffix_len)
            end_byte = file_size - 1
        elif parts[1] == "":
            start_byte = int(parts[0])
            end_byte = file_size - 1
        else:
            start_byte = int(parts[0])
            end_byte = int(parts[1])

        if start_byte >= file_size or end_byte >= file_size or start_byte > end_byte or start_byte < 0:
            return Response(
                status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
                headers={"Content-Range": f"bytes */{file_size}"}
            )

        content_length = (end_byte - start_byte) + 1

        async def range_stream():
            chunk_size = 128 * 1024
            with open(resolved_path, "rb") as f:
                f.seek(start_byte)
                bytes_left = content_length
                while bytes_left > 0:
                    read_amount = min(chunk_size, bytes_left)
                    data = f.read(read_amount)
                    if not data:
                        break
                    bytes_left -= len(data)
                    yield data

        headers = {
            "Content-Range": f"bytes {start_byte}-{end_byte}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": media_type,
        }
        return StreamingResponse(range_stream(), status_code=status.HTTP_206_PARTIAL_CONTENT, headers=headers, media_type=media_type)

    except (ValueError, IndexError):
        return Response(
            status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
            headers={"Content-Range": f"bytes */{file_size}"}
        )


@router.get(
    "/{clip_id}/download",
    summary="Download Clip MP4",
    description="Downloads the generated 9:16 MP4 video clip as a file attachment."
)
async def download_clip(
    clip_id: str,
    db: AsyncSession = Depends(get_database)
):
    """Downloads the generated clip MP4 file."""
    stmt = select(Clip).where(Clip.id == clip_id)
    res = await db.execute(stmt)
    clip = res.scalar_one_or_none()

    if not clip:
        raise NotFoundError(f"Clip with id '{clip_id}' was not found.")

    if not clip.output_path:
        raise NotFoundError(f"Clip '{clip_id}' has not been generated yet.")

    file_path = Path(clip.output_path)
    if not file_path.is_absolute():
        file_path = settings.STORAGE_DIR.parent / clip.output_path

    resolved_path = file_path.resolve()
    if not resolved_path.is_relative_to(settings.STORAGE_DIR.resolve()):
        raise AppException(status_code=400, detail="Path traversal security violation detected.")

    if not resolved_path.exists():
        raise NotFoundError(f"Physical clip file '{resolved_path.name}' was not found on disk.")

    download_filename = clip.output_filename or f"{clip.title.replace(' ', '_')}_{clip.id[:8]}.mp4"
    if not download_filename.endswith(".mp4"):
        download_filename = f"{download_filename}.mp4"

    return FileResponse(
        path=str(resolved_path),
        filename=download_filename,
        media_type="video/mp4",
    )


@router.post(
    "/{clip_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel Clip Generation",
    description="Cancels an active or queued clip generation job and safely releases resources."
)
async def cancel_clip(
    clip_id: str,
    db: AsyncSession = Depends(get_database)
):
    """Cancels a queued or executing clip generation task."""
    stmt = select(Clip).where(Clip.id == clip_id)
    res = await db.execute(stmt)
    clip = res.scalar_one_or_none()

    if not clip:
        raise NotFoundError(f"Clip with id '{clip_id}' was not found.")

    if clip.status in ("COMPLETED", "FAILED", "CANCELLED"):
        raise ConflictError(f"Clip '{clip_id}' is already in terminal state '{clip.status}'.")

    # Find associated ProcessingJob
    j_stmt = (
        select(ProcessingJob)
        .where(
            ProcessingJob.video_id == clip.video_id,
            ProcessingJob.job_type == "CLIP_GENERATION",
            ProcessingJob.status.in_(["QUEUED", "PROCESSING"]),
        )
        .order_by(ProcessingJob.created_at.desc())
    )
    j_res = await db.execute(j_stmt)
    job = j_res.scalar_one_or_none()

    if job:
        await job_queue.cancel_job(job.id, db)

    clip.status = "CANCELLED"
    clip.error_message = "Generation cancelled by user."
    await db.commit()
    await db.refresh(clip)
    return {"success": True, "id": clip_id, "status": clip.status}


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
        "title", "aspect_ratio_mode", "conversion_mode", "subtitle_enabled", "subtitle_style_preset",
        "subtitle_font_family", "subtitle_font_size", "subtitle_primary_color",
        "subtitle_highlight_color", "subtitle_outline_color", "subtitle_outline_width",
        "subtitle_vertical_position", "custom_subtitle_text", "status"
    ]
    for field in update_fields:
        val = getattr(payload, field, None)
        if val is not None:
            if field in ("aspect_ratio_mode", "conversion_mode"):
                val = normalize_conversion_mode(val)
                setattr(clip, "aspect_ratio_mode", val)
                setattr(clip, "conversion_mode", val)
            else:
                setattr(clip, field, val)

    await db.commit()
    await db.refresh(clip)

    return _serialize_clip(clip)


@router.delete(
    "/{clip_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Clip",
    description="Deletes a clip, its disk asset in storage/clips/, and related export records."
)
async def delete_clip(
    clip_id: str,
    db: AsyncSession = Depends(get_database)
):
    """Deletes a clip record and removes its physical file from disk."""
    stmt = select(Clip).where(Clip.id == clip_id)
    result = await db.execute(stmt)
    clip = result.scalar_one_or_none()

    if not clip:
        raise NotFoundError(f"Clip with id '{clip_id}' was not found.")

    # Delete physical video file if present
    if clip.output_path:
        file_path = Path(clip.output_path)
        if not file_path.is_absolute():
            file_path = settings.STORAGE_DIR.parent / clip.output_path
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass

    await db.delete(clip)
    await db.commit()
    return {"success": True, "id": clip_id}


def _serialize_subtitle_track(track: SubtitleTrack) -> Dict[str, Any]:
    events_data = []
    if track.events:
        for ev in track.events:
            words = []
            if ev.words_json:
                try:
                    words = json.loads(ev.words_json)
                except Exception:
                    words = []
            events_data.append({
                "id": ev.id,
                "sequence_index": ev.sequence_index,
                "start_ms": ev.start_ms,
                "end_ms": ev.end_ms,
                "text": ev.text,
                "words": words,
                "style_name": ev.style_name,
                "is_modified": ev.is_modified,
            })
    overrides = None
    if track.custom_style_overrides:
        try:
            overrides = json.loads(track.custom_style_overrides)
        except Exception:
            overrides = None

    return {
        "id": track.id,
        "clip_id": track.clip_id,
        "transcript_id": track.transcript_id,
        "preset_name": track.preset_name,
        "is_enabled": track.is_enabled,
        "is_active": track.is_active,
        "language": track.language,
        "ass_file_path": track.ass_file_path,
        "compile_status": track.compile_status,
        "custom_style_overrides": overrides,
        "event_count": len(events_data),
        "events": events_data,
        "created_at": track.created_at,
        "updated_at": track.updated_at,
    }


@router.post(
    "/{clip_id}/subtitles/generate",
    status_code=status.HTTP_201_CREATED,
    summary="Generate Subtitle Track for Clip",
    description="Synchronizes transcript words with clip bounds and creates clip-relative subtitle events in DB.",
)
async def generate_clip_subtitles(
    clip_id: str,
    payload: SubtitleGenerateRequest,
    db: AsyncSession = Depends(get_database),
):
    """Generates a SubtitleTrack and SubtitleEvents from active video transcript."""
    # Check if clip exists
    stmt_clip = select(Clip).where(Clip.id == clip_id)
    clip_res = await db.execute(stmt_clip)
    clip = clip_res.scalar_one_or_none()
    if not clip:
        raise NotFoundError(f"Clip '{clip_id}' not found.")

    try:
        track = await create_subtitle_track_for_clip(
            session=db,
            clip_id=clip_id,
            request=payload,
        )
        return _serialize_subtitle_track(track)
    except SubtitleValidationError as e:
        raise ValidationError(str(e))
    except ValueError as e:
        err_msg = str(e)
        if "transcript" in err_msg.lower():
            raise InvalidFileFormatError(err_msg)
        if "clip" in err_msg.lower() and "not found" in err_msg.lower():
            raise NotFoundError(err_msg)
        raise ValidationError(err_msg)


@router.get(
    "/{clip_id}/subtitles",
    status_code=status.HTTP_200_OK,
    summary="Get Subtitle Track for Clip",
    description="Retrieves the active subtitle track and its caption events for a clip.",
)
async def get_active_clip_subtitles(
    clip_id: str,
    db: AsyncSession = Depends(get_database),
):
    """Fetches active subtitle track and events for Studio UI."""
    stmt_clip = select(Clip).where(Clip.id == clip_id)
    clip_res = await db.execute(stmt_clip)
    clip = clip_res.scalar_one_or_none()
    if not clip:
        raise NotFoundError(f"Clip '{clip_id}' not found.")

    track = await get_active_subtitle_track_for_clip(session=db, clip_id=clip_id)
    if not track:
        raise NotFoundError(f"No active subtitle track found for clip '{clip_id}'.")

    return _serialize_subtitle_track(track)


@router.get(
    "/{clip_id}/subtitles.ass",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Export Subtitles (ASS)",
    description="Generates styled Advanced SubStation Alpha (.ass) subtitle file (activates in Phase 18 — Subtitle & Caption Engine)."
)
async def get_clip_subtitles(clip_id: str):
    """Placeholder endpoint for ASS subtitle generation."""
    raise NotImplementedFeatureError(
        "ASS subtitle generation is not implemented yet. This functionality belongs to Phase 18 — Subtitle & Caption Engine. The endpoint remains intentionally unavailable during Phase 17."
    )
