"""Clipsly Phase 16: Highlight Detection Pipeline Orchestrator.

Orchestrates transcript analysis, candidate generation, feature extraction,
scoring, deduplication, ranking, and database persistence.
Integrates with the sequential JobQueueManager and supports cooperative cancellation.
"""
import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional, Set
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import AsyncSessionLocal
from backend.app.core.exceptions import (
    ConflictError,
    NotFoundError,
)
from backend.app.models.highlight import Highlight
from backend.app.models.processing_job import ProcessingJob
from backend.app.models.transcript import Transcript
from backend.app.models.transcript_segment import TranscriptSegment
from backend.app.models.video import Video
from backend.app.services.highlight_detection.candidate_generator import generate_candidate_windows
from backend.app.services.highlight_detection.deduplication import deduplicate_candidates
from backend.app.services.highlight_detection.ranking import rank_and_filter_candidates
from backend.app.services.highlight_detection.schemas import (
    DetectionConfig,
    ScoredCandidate,
)
from backend.app.services.highlight_detection.scoring_engine import score_candidate_window
from backend.app.services.highlight_detection.validators import validate_detection_config

logger = logging.getLogger("clipsly.highlight_detection")

# Concurrency locks and active job tracking
_detection_lock = asyncio.Lock()
_active_detections: Set[str] = set()       # Active video IDs
_active_jobs: Dict[str, str] = {}          # job_id -> video_id
_cancelled_jobs: Set[str] = set()          # Set of job IDs flagged for cancellation


async def _update_job_progress(job_id: Optional[str], progress: float, step: str) -> None:
    """Updates progress percent and step string in the processing_jobs table."""
    if not job_id:
        return
    try:
        async with AsyncSessionLocal() as session:
            job = await session.get(ProcessingJob, job_id)
            if job and job.status == "PROCESSING":
                job.progress_percent = progress
                job.current_step = step
                await session.commit()
    except Exception as e:
        logger.debug("Failed to update progress for job %s: %s", job_id, e)


async def _check_cancelled(job_id: Optional[str], video_id: str) -> None:
    """Checks whether the job was flagged for cancellation and raises CancelledError."""
    if not job_id:
        return
    if job_id in _cancelled_jobs:
        logger.info("Cooperative cancellation triggered for highlight detection job %s", job_id)
        raise asyncio.CancelledError(f"Highlight detection job {job_id} was cancelled by user.")


async def cancel_highlight_detection(job_id: str, db: Optional[AsyncSession] = None) -> bool:
    """Flags an active or queued highlight detection job for cooperative cancellation."""
    _cancelled_jobs.add(job_id)

    async def _cancel_in_session(s: AsyncSession) -> None:
        job = await s.get(ProcessingJob, job_id)
        if not job:
            raise NotFoundError(f"Processing job with id '{job_id}' not found.")

        if job.status in ("COMPLETED", "FAILED", "CANCELLED"):
            raise ConflictError(f"Job '{job_id}' is already in terminal state '{job.status}'.")

        job.status = "CANCELLED"
        job.current_step = "Cancelled by user"
        job.error_message = "Highlight detection job was cancelled by user."
        job.completed_at = datetime.now(timezone.utc)
        await s.commit()

    if db is not None:
        await _cancel_in_session(db)
    else:
        async with AsyncSessionLocal() as s:
            await _cancel_in_session(s)

    # Discard active video lock
    vid_id = _active_jobs.pop(job_id, None)
    if vid_id:
        async with _detection_lock:
            _active_detections.discard(vid_id)

    logger.info("Signaled cooperative cancellation for highlight detection job %s", job_id)
    return True


async def detect_highlights_pipeline(
    video_id: str,
    job_id: Optional[str] = None,
    config: Optional[DetectionConfig] = None,
    db: Optional[AsyncSession] = None,
) -> List[Highlight]:
    """Main execution pipeline for AI highlight detection and clip intelligence.

    Args:
        video_id: Target video ID.
        job_id: Optional tracking processing job ID.
        config: Optional detection configuration overrides.
        db: Optional database session. If omitted, creates and manages local session.

    Returns:
        List of created and persisted Highlight database model instances.
    """
    if config is None:
        config = DetectionConfig()

    # Track concurrency
    async with _detection_lock:
        if video_id in _active_detections:
            raise ConflictError(
                f"Highlight detection is already running for video '{video_id}'.",
                details={"video_id": video_id},
            )
        _active_detections.add(video_id)
        if job_id:
            _active_jobs[job_id] = video_id

    owns_session = False
    session = db
    if session is None:
        session = AsyncSessionLocal()
        owns_session = True

    try:
        # Check initial cancellation
        await _check_cancelled(job_id, video_id)

        # Mark job as PROCESSING if applicable
        if job_id:
            db_job = await session.get(ProcessingJob, job_id)
            if db_job:
                db_job.status = "PROCESSING"
                db_job.progress_percent = 5.0
                db_job.current_step = "Initializing highlight detection engine"
                db_job.started_at = datetime.now(timezone.utc)
                await session.commit()

        # Step 1: Validate Video and Transcript
        video = await session.get(Video, video_id)
        if not video:
            raise NotFoundError(f"Video with id '{video_id}' not found.")

        # Find latest completed transcript
        stmt = (
            select(Transcript)
            .where(Transcript.video_id == video_id, Transcript.status == "COMPLETED")
            .order_by(Transcript.created_at.desc())
        )
        res = await session.execute(stmt)
        transcript = res.scalars().first()

        if not transcript:
            raise ConflictError(
                f"No completed transcript found for video '{video_id}'. Run transcription before detecting highlights."
            )

        validate_detection_config(config, video_duration_seconds=video.duration_seconds)

        await _check_cancelled(job_id, video_id)
        await _update_job_progress(job_id, 15.0, "Loading transcript segments")

        # Step 2: Load transcript segments
        seg_stmt = (
            select(TranscriptSegment)
            .where(TranscriptSegment.transcript_id == transcript.id)
            .order_by(TranscriptSegment.start_ms.asc())
        )
        seg_res = await session.execute(seg_stmt)
        segments = seg_res.scalars().all()

        if not segments or not transcript.full_text or not transcript.full_text.strip():
            logger.info("Video %s transcript has no speech segments. Returning 0 highlights.", video_id)
            if job_id:
                db_job = await session.get(ProcessingJob, job_id)
                if db_job:
                    db_job.status = "COMPLETED"
                    db_job.progress_percent = 100.0
                    db_job.current_step = "Completed (no speech content in transcript)"
                    db_job.completed_at = datetime.now(timezone.utc)
                    await session.commit()
            return []

        await _check_cancelled(job_id, video_id)
        await _update_job_progress(job_id, 30.0, "Generating candidate windows")

        # Step 3: Generate candidate windows
        candidate_windows = generate_candidate_windows(
            segments=segments,
            config=config,
            video_duration_seconds=video.duration_seconds,
        )

        if not candidate_windows:
            logger.info("No valid candidate windows found for video %s within duration limits.", video_id)
            if job_id:
                db_job = await session.get(ProcessingJob, job_id)
                if db_job:
                    db_job.status = "COMPLETED"
                    db_job.progress_percent = 100.0
                    db_job.current_step = "Completed (0 highlights met duration constraints)"
                    db_job.completed_at = datetime.now(timezone.utc)
                    await session.commit()
            return []

        await _check_cancelled(job_id, video_id)
        await _update_job_progress(job_id, 55.0, f"Scoring {len(candidate_windows)} candidate windows")

        # Step 4: Score candidates
        scored_candidates: List[ScoredCandidate] = []
        for window in candidate_windows:
            breakdown = score_candidate_window(window, config)
            scored_candidates.append(
                ScoredCandidate(
                    window=window,
                    scores=breakdown,
                    scoring_version="v1",
                )
            )

        await _check_cancelled(job_id, video_id)
        await _update_job_progress(job_id, 75.0, "Deduplicating overlapping candidates")

        # Step 5: Deduplicate overlapping windows
        deduped_candidates = deduplicate_candidates(
            scored_candidates,
            overlap_threshold=config.overlap_threshold,
        )

        await _check_cancelled(job_id, video_id)
        await _update_job_progress(job_id, 88.0, "Ranking and filtering top highlights")

        # Step 6: Rank and filter candidates
        ranked_candidates = rank_and_filter_candidates(
            deduped_candidates,
            min_score=config.min_score,
            max_results=config.max_results,
        )

        await _check_cancelled(job_id, video_id)
        await _update_job_progress(job_id, 94.0, "Persisting highlights to database")

        # Step 7: Transactional Persistence
        # Supersede/delete previous CANDIDATE highlights for this video, preserving user-reviewed ones
        del_stmt = (
            delete(Highlight)
            .where(
                Highlight.video_id == video_id,
                Highlight.status == "CANDIDATE",
            )
        )
        await session.execute(del_stmt)

        created_highlights: List[Highlight] = []
        for cand in ranked_candidates:
            highlight = Highlight(
                id=str(uuid.uuid4()),
                video_id=video_id,
                transcript_id=transcript.id,
                start_ms=cand.start_ms,
                end_ms=cand.end_ms,
                duration_ms=cand.duration_ms,
                hook_sentence=cand.scores.hook_sentence,
                summary=cand.scores.summary,
                transcript_excerpt=cand.window.text,
                hook_score=cand.scores.hook_score,
                coherence_score=cand.scores.coherence_score,
                density_score=cand.scores.density_score,
                sentiment_score=cand.scores.sentiment_score,
                composite_score=cand.scores.composite_score,
                rank=cand.rank,
                scoring_version=cand.scoring_version,
                explanation=cand.scores.explanation,
                warnings_json=json.dumps(cand.scores.warnings),
                detection_metadata_json=json.dumps(cand.scores.metadata),
                category=cand.scores.category,
                detection_method="HEURISTIC",
                status="CANDIDATE",
            )
            session.add(highlight)
            created_highlights.append(highlight)

        # Mark job COMPLETED
        if job_id:
            db_job = await session.get(ProcessingJob, job_id)
            if db_job:
                db_job.status = "COMPLETED"
                db_job.progress_percent = 100.0
                db_job.current_step = f"Detected {len(created_highlights)} highlights"
                db_job.completed_at = datetime.now(timezone.utc)

        await session.commit()

        # Refresh instances so all fields are available
        for h in created_highlights:
            await session.refresh(h)

        logger.info(
            "Highlight detection completed for video %s: %d highlights created.",
            video_id,
            len(created_highlights),
        )
        return created_highlights

    except asyncio.CancelledError:
        logger.info("Highlight detection cancelled for video %s (job %s)", video_id, job_id)
        if job_id:
            try:
                db_job = await session.get(ProcessingJob, job_id)
                if db_job and db_job.status != "CANCELLED":
                    db_job.status = "CANCELLED"
                    db_job.current_step = "Cancelled by user"
                    db_job.error_message = "Highlight detection job was cancelled by user."
                    db_job.completed_at = datetime.now(timezone.utc)
                    await session.commit()
            except Exception as e:
                logger.debug("Failed to record cancellation for job %s: %s", job_id, e)
        raise

    except Exception as exc:
        logger.exception("Highlight detection failed for video %s: %s", video_id, exc)
        if job_id:
            try:
                db_job = await session.get(ProcessingJob, job_id)
                if db_job:
                    db_job.status = "FAILED"
                    db_job.current_step = "Detection failed"
                    db_job.error_message = str(exc)
                    db_job.completed_at = datetime.now(timezone.utc)
                    await session.commit()
            except Exception as e:
                logger.debug("Failed to record failure for job %s: %s", job_id, e)
        raise

    finally:
        if owns_session and session is not None:
            await session.close()

        # Clean up tracking and concurrency locks
        async with _detection_lock:
            _active_detections.discard(video_id)
            if job_id:
                _active_jobs.pop(job_id, None)
                _cancelled_jobs.discard(job_id)
