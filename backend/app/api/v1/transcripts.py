import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_database
from backend.app.core.config import settings
from backend.app.core.exceptions import NotFoundError
from backend.app.models.transcript import Transcript
from backend.app.models.transcript_segment import TranscriptSegment
from backend.app.schemas.transcript import (
    AvailableModelsResponse,
    SegmentUpdateRequest,
    TranscriptResponse,
    TranscriptSegmentListResponse,
    TranscriptSegmentResponse,
    TranscriptionJobResponse,
    TranscriptionVideoRequest,
    WordTimestampSchema,
)
from backend.app.services.system import check_cuda_available, get_system_info
from backend.app.services.transcription import model_manager

logger = logging.getLogger("clipsly.transcripts_api")

router = APIRouter(prefix="/transcripts", tags=["Transcripts"])


@router.get(
    "/models",
    response_model=AvailableModelsResponse,
    status_code=status.HTTP_200_OK,
    summary="List Available Faster-Whisper Models",
    description="Returns supported Faster-Whisper model catalog and current local hardware compute capability."
)
async def list_available_models():
    """Returns available Whisper models, memory footprints, and CUDA compute availability."""
    models = model_manager.get_supported_models()
    cuda_ok = check_cuda_available() and not settings.FORCE_CPU_TRANSCRIPTION
    sys_info = get_system_info()
    detected_gpu = sys_info.gpu if cuda_ok else None

    cuda_compute_types = ["float16", "int8_float16", "int8"] if cuda_ok else []
    cpu_compute_types = ["int8", "float32"]

    return AvailableModelsResponse(
        models=models,
        default_model=settings.TRANSCRIPTION_MODEL,
        cuda_available=cuda_ok,
        detected_gpu=detected_gpu,
        cuda_compute_types=cuda_compute_types,
        cpu_compute_types=cpu_compute_types,
    )


@router.post(
    "/transcribe",
    response_model=TranscriptionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Transcription",
    description="Submits an asynchronous transcription job for a video using local Faster-Whisper."
)
async def trigger_transcription(
    body: TranscriptionVideoRequest,
    db: AsyncSession = Depends(get_database)
):
    """Queues a speech-to-text transcription job for the specified video."""
    # Delegate to the canonical video transcription endpoint logic
    from backend.app.api.v1.videos import transcribe_video_endpoint
    return await transcribe_video_endpoint(video_id=body.video_id, body=body, db=db)


@router.get(
    "/{video_or_transcript_id}",
    response_model=TranscriptResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Transcript",
    description="Retrieves the active transcript by Video UUID or Transcript UUID."
)
async def get_transcript(
    video_or_transcript_id: str,
    db: AsyncSession = Depends(get_database)
):
    """Retrieves active transcript for a video, or by direct transcript ID."""
    # First search by video_id with is_active=True
    stmt = (
        select(Transcript)
        .where(Transcript.video_id == video_or_transcript_id, Transcript.is_active == True)
        .order_by(Transcript.created_at.desc())
    )
    result = await db.execute(stmt)
    transcript = result.scalars().first()

    # Fallback to direct transcript ID lookup
    if not transcript:
        stmt = select(Transcript).where(Transcript.id == video_or_transcript_id)
        result = await db.execute(stmt)
        transcript = result.scalar_one_or_none()

    if not transcript:
        raise NotFoundError(f"No active transcript found for id '{video_or_transcript_id}'.")

    return TranscriptResponse(
        id=transcript.id,
        video_id=transcript.video_id,
        audio_asset_id=transcript.audio_asset_id,
        model_name=transcript.model_name,
        compute_type=transcript.compute_type,
        device=transcript.device or "cuda",
        language=transcript.language,
        language_probability=transcript.language_probability,
        status=transcript.status or "COMPLETED",
        full_text=transcript.full_text,
        word_count=transcript.word_count,
        segment_count=transcript.segment_count or 0,
        audio_duration_seconds=transcript.audio_duration_seconds,
        processing_time_seconds=transcript.processing_time_seconds or 0.0,
        error_message=transcript.error_message,
        is_active=transcript.is_active,
        created_at=transcript.created_at.isoformat() if transcript.created_at else None,
        updated_at=transcript.updated_at.isoformat() if transcript.updated_at else None,
    )


@router.get(
    "/{transcript_id}/segments",
    response_model=TranscriptSegmentListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Transcript Segments",
    description="Returns ordered sentence-level segments with word-level timing arrays."
)
async def get_transcript_segments(
    transcript_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Max segments to return"),
    offset: int = Query(0, ge=0, description="Segments offset"),
    db: AsyncSession = Depends(get_database)
):
    """Retrieves paginated ordered segments for a transcript."""
    # Verify transcript existence
    t_stmt = select(Transcript).where(Transcript.id == transcript_id)
    t_result = await db.execute(t_stmt)
    transcript = t_result.scalar_one_or_none()
    if not transcript:
        # Check if transcript_id is actually a video_id
        t_stmt_video = (
            select(Transcript)
            .where(Transcript.video_id == transcript_id, Transcript.is_active == True)
            .order_by(Transcript.created_at.desc())
        )
        t_res_video = await db.execute(t_stmt_video)
        transcript = t_res_video.scalars().first()

    if not transcript:
        raise NotFoundError(f"Transcript with id '{transcript_id}' was not found.")

    actual_transcript_id = transcript.id

    # Count total segments
    count_stmt = (
        select(func.count())
        .select_from(TranscriptSegment)
        .where(TranscriptSegment.transcript_id == actual_transcript_id)
    )
    count_res = await db.execute(count_stmt)
    total = count_res.scalar_one()

    # Query paginated segments
    stmt = (
        select(TranscriptSegment)
        .where(TranscriptSegment.transcript_id == actual_transcript_id)
        .order_by(TranscriptSegment.segment_index.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    segments = result.scalars().all()

    items: List[TranscriptSegmentResponse] = []
    for s in segments:
        words: List[WordTimestampSchema] = []
        if s.words_json:
            try:
                raw_words = json.loads(s.words_json)
                words = [WordTimestampSchema(**w) for w in raw_words]
            except Exception:
                words = []

        items.append(
            TranscriptSegmentResponse(
                id=s.id,
                transcript_id=s.transcript_id,
                segment_index=s.segment_index,
                start_ms=s.start_ms,
                end_ms=s.end_ms,
                text=s.text,
                words=words,
                avg_confidence=s.avg_confidence if s.avg_confidence is not None else 1.0,
                no_speech_prob=s.no_speech_prob,
                speaker_id=s.speaker_id,
                created_at=s.created_at.isoformat() if s.created_at else None,
            )
        )

    return TranscriptSegmentListResponse(
        transcript_id=actual_transcript_id,
        total=total,
        offset=offset,
        limit=limit,
        segments=items,
    )


@router.patch(
    "/{transcript_id}/segments/{segment_id}",
    response_model=TranscriptSegmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Transcript Segment",
    description="Updates text for an individual transcript segment."
)
async def update_segment(
    transcript_id: str,
    segment_id: str,
    payload: SegmentUpdateRequest,
    db: AsyncSession = Depends(get_database)
):
    """Updates segment text."""
    stmt = (
        select(TranscriptSegment)
        .where(TranscriptSegment.transcript_id == transcript_id, TranscriptSegment.id == segment_id)
    )
    result = await db.execute(stmt)
    segment = result.scalar_one_or_none()

    if not segment:
        raise NotFoundError(f"Segment '{segment_id}' in transcript '{transcript_id}' was not found.")

    segment.text = payload.text.strip()
    await db.commit()
    await db.refresh(segment)

    words: List[WordTimestampSchema] = []
    if segment.words_json:
        try:
            raw_words = json.loads(segment.words_json)
            words = [WordTimestampSchema(**w) for w in raw_words]
        except Exception:
            words = []

    return TranscriptSegmentResponse(
        id=segment.id,
        transcript_id=segment.transcript_id,
        segment_index=segment.segment_index,
        start_ms=segment.start_ms,
        end_ms=segment.end_ms,
        text=segment.text,
        words=words,
        avg_confidence=segment.avg_confidence if segment.avg_confidence is not None else 1.0,
        no_speech_prob=segment.no_speech_prob,
        speaker_id=segment.speaker_id,
        created_at=segment.created_at.isoformat() if segment.created_at else None,
    )
