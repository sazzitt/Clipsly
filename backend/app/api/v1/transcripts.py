import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_database
from backend.app.core.exceptions import NotFoundError, NotImplementedFeatureError
from backend.app.models.transcript import Transcript
from backend.app.models.transcript_segment import TranscriptSegment

router = APIRouter(prefix="/transcripts", tags=["Transcripts"])


class SegmentUpdateRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Updated segment text")


@router.get(
    "/{video_or_transcript_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Transcript",
    description="Retrieves the active transcript by Video UUID or Transcript UUID."
)
async def get_transcript(
    video_or_transcript_id: str,
    db: AsyncSession = Depends(get_database)
):
    """Retrieves active transcript for a video, or by transcript ID."""
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

    return {
        "id": transcript.id,
        "video_id": transcript.video_id,
        "model_name": transcript.model_name,
        "compute_type": transcript.compute_type,
        "language": transcript.language,
        "full_text": transcript.full_text,
        "word_count": transcript.word_count,
        "processing_time_seconds": transcript.processing_time_seconds,
        "is_active": transcript.is_active,
        "created_at": transcript.created_at.isoformat() if transcript.created_at else None,
        "updated_at": transcript.updated_at.isoformat() if transcript.updated_at else None,
    }


@router.get(
    "/{transcript_id}/segments",
    status_code=status.HTTP_200_OK,
    summary="Get Transcript Segments",
    description="Returns ordered sentence-level segments with word-level timing arrays."
)
async def get_transcript_segments(
    transcript_id: str,
    db: AsyncSession = Depends(get_database)
):
    """Retrieves ordered segments for a transcript."""
    # Verify transcript existence
    t_stmt = select(Transcript).where(Transcript.id == transcript_id)
    t_result = await db.execute(t_stmt)
    if not t_result.scalar_one_or_none():
        raise NotFoundError(f"Transcript with id '{transcript_id}' was not found.")

    stmt = (
        select(TranscriptSegment)
        .where(TranscriptSegment.transcript_id == transcript_id)
        .order_by(TranscriptSegment.segment_index.asc())
    )
    result = await db.execute(stmt)
    segments = result.scalars().all()

    items = []
    for s in segments:
        words = []
        if s.words_json:
            try:
                words = json.loads(s.words_json)
            except Exception:
                words = []

        items.append({
            "id": s.id,
            "transcript_id": s.transcript_id,
            "segment_index": s.segment_index,
            "start_ms": s.start_ms,
            "end_ms": s.end_ms,
            "text": s.text,
            "words": words,
            "avg_confidence": s.avg_confidence,
            "speaker_id": s.speaker_id,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })

    return {"transcript_id": transcript_id, "total": len(items), "segments": items}


@router.patch(
    "/{transcript_id}/segments/{segment_id}",
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

    segment.text = payload.text
    await db.commit()
    await db.refresh(segment)

    return {
        "id": segment.id,
        "transcript_id": segment.transcript_id,
        "text": segment.text,
        "start_ms": segment.start_ms,
        "end_ms": segment.end_ms,
    }


@router.post(
    "/transcribe",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Trigger Transcription",
    description="Starts GPU-accelerated Faster-Whisper transcription (activates in Phase 13)."
)
async def trigger_transcription():
    """Placeholder endpoint for transcription. Activates in Phase 13."""
    raise NotImplementedFeatureError("Faster-Whisper GPU transcription pipeline activates in Phase 13.")
