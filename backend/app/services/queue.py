import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Set, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import AsyncSessionLocal
from backend.app.core.exceptions import ConflictError, NotFoundError
from backend.app.models.processing_job import ProcessingJob

logger = logging.getLogger("clipsly.job_queue")


class JobQueueManager:
    """SQLite-backed sequential asyncio worker queue for long-running media processing jobs.
    Implements ADR-001 (SQLite-Backed Asyncio Worker Queue) and ADR-002 (Sequential Execution).

    Ensures:
    1. Exactly one heavy processing task executes at any given time.
    2. Jobs are persisted in SQLite (processing_jobs table) and tracked in an in-process asyncio.Queue.
    3. Queued and running jobs can be cancelled cleanly with immediate resource release.
    4. Safe shutdown lifecycle handling on application termination.
    """

    def __init__(self) -> None:
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._queue: Optional[asyncio.Queue[Tuple[str, str, Callable[..., Any], tuple, dict]]] = None
        self._lock: Optional[asyncio.Lock] = None
        self._worker_task: Optional[asyncio.Task] = None
        self._is_running: bool = False
        self._current_job_id: Optional[str] = None
        self._current_video_id: Optional[str] = None
        self._queued_video_ids: Set[str] = set()
        self._cancelled_job_ids: Set[str] = set()

    def _ensure_initialized(self) -> None:
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self._loop != current_loop or self._queue is None or self._lock is None:
            self._loop = current_loop
            self._queue = asyncio.Queue()
            self._lock = asyncio.Lock()
            self._worker_task = None
            self._is_running = False

    async def start(self) -> None:
        """Starts the sequential background worker loop."""
        self._ensure_initialized()
        async with self._lock:
            if self._is_running and self._worker_task and not self._worker_task.done():
                return
            self._is_running = True
            self._worker_task = asyncio.create_task(self._worker_loop(), name="clipsly_worker_loop")
            logger.info("Sequential JobQueue worker loop started.")

    async def stop(self) -> None:
        """Gracefully terminates the background worker loop and cancels any running job."""
        self._ensure_initialized()
        async with self._lock:
            if not self._is_running:
                return
            self._is_running = False

            # Cancel current active job if executing
            if self._current_job_id:
                logger.info("Application shutdown: cancelling active job %s", self._current_job_id)
                try:
                    async with AsyncSessionLocal() as session:
                        db_j = await session.get(ProcessingJob, self._current_job_id)
                        if db_j:
                            if db_j.job_type == "AUDIO_EXTRACTION":
                                from backend.app.services.audio_extraction import cancel_audio_extraction
                                await cancel_audio_extraction(self._current_job_id, session)
                            elif db_j.job_type == "TRANSCRIPTION":
                                from backend.app.services.transcription import cancel_transcription
                                await cancel_transcription(self._current_job_id, session)
                except Exception as e:
                    logger.warning("Error cancelling active job during shutdown: %s", e)

            if self._worker_task:
                self._worker_task.cancel()
                try:
                    await self._worker_task
                except asyncio.CancelledError:
                    pass
                self._worker_task = None

            logger.info("Sequential JobQueue worker loop stopped.")

    async def submit_job(
        self,
        job_id: str,
        video_id: str,
        handler: Callable[..., Any],
        job_args: tuple = (),
        job_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Submits a job to the sequential processing queue.
        Enforces ADR-001 sequential processing and prevents competing concurrent jobs.
        """
        self._ensure_initialized()
        async with self._lock:
            # Check if this video already has a queued or running job
            if video_id in self._queued_video_ids or video_id == self._current_video_id:
                raise ConflictError(
                    f"A processing job is already queued or executing for video '{video_id}'.",
                    details={"video_id": video_id},
                )

            if not self._is_running or not self._worker_task or self._worker_task.done():
                self._is_running = True
                self._worker_task = asyncio.create_task(self._worker_loop(), name="clipsly_worker_loop")
                logger.info("JobQueue worker loop auto-started on submit.")

            self._queued_video_ids.add(video_id)
            kwargs = job_kwargs or {}
            await self._queue.put((job_id, video_id, handler, job_args, kwargs))
            logger.info("Job %s (%s) submitted to sequential queue (queue size: %d).", job_id, handler.__name__, self._queue.qsize())

    def is_video_active(self, video_id: str) -> bool:
        """Checks if a video currently has a queued or actively executing job."""
        return video_id in self._queued_video_ids or video_id == self._current_video_id

    async def cancel_job(self, job_id: str, db: AsyncSession) -> bool:
        """Cancels a job whether it is currently executing or still waiting in the queue."""
        self._ensure_initialized()
        job = await db.get(ProcessingJob, job_id)
        if not job:
            raise NotFoundError(f"Processing job with id '{job_id}' not found.")

        if job.status in ("COMPLETED", "FAILED", "CANCELLED"):
            raise ConflictError(f"Job '{job_id}' is already in terminal state '{job.status}'.")

        async with self._lock:
            from backend.app.services.audio_extraction import _active_processes, cancel_audio_extraction
            from backend.app.services.transcription import _active_jobs as active_transcription_jobs, cancel_transcription

            # Case 1: Job is currently executing (either tracked by queue or in _active_processes / active transcriptions)
            if self._current_job_id == job_id or job_id in _active_processes or job_id in active_transcription_jobs:
                logger.info("Cancelling actively executing job %s", job_id)
                self._queued_video_ids.discard(job.video_id)
                if job.job_type == "AUDIO_EXTRACTION":
                    return await cancel_audio_extraction(job_id, db)
                elif job.job_type == "TRANSCRIPTION":
                    return await cancel_transcription(job_id, db)
                else:
                    job.status = "CANCELLED"
                    job.current_step = "Cancelled by user"
                    job.completed_at = datetime.now(timezone.utc)
                    await db.commit()
                    return True

            # Case 2: Job is still queued waiting to run
            logger.info("Marking queued job %s as cancelled before execution", job_id)
            self._cancelled_job_ids.add(job_id)
            self._queued_video_ids.discard(job.video_id)

            job.status = "CANCELLED"
            job.current_step = "Cancelled while queued"
            job.error_message = "Job was cancelled by user while waiting in queue."
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(job)
            return True

    async def _worker_loop(self) -> None:
        """The single, continuous sequential worker loop processing one job at a time."""
        logger.info("JobQueue worker loop is active and waiting for tasks.")
        while self._is_running:
            try:
                # Wait for next job item with timeout to allow checking self._is_running
                try:
                    job_id, video_id, handler, args, kwargs = await asyncio.wait_for(
                        self._queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                async with self._lock:
                    self._queued_video_ids.discard(video_id)

                    # Check if job was cancelled while waiting in queue
                    if job_id in self._cancelled_job_ids:
                        self._cancelled_job_ids.discard(job_id)
                        self._queue.task_done()
                        logger.info("Skipping queued job %s because it was cancelled.", job_id)
                        continue

                    # Also verify status from database
                    async with AsyncSessionLocal() as session:
                        db_job = await session.get(ProcessingJob, job_id)
                        if not db_job or db_job.status == "CANCELLED":
                            self._queue.task_done()
                            logger.info("Skipping queued job %s (DB status is terminal or missing).", job_id)
                            continue

                    self._current_job_id = job_id
                    self._current_video_id = video_id

                logger.info("Starting execution of queued job %s for video %s", job_id, video_id)
                try:
                    await handler(*args, **kwargs)
                    logger.info("Completed execution of job %s", job_id)
                except Exception as exc:
                    logger.error("Job %s execution failed: %s", job_id, exc)
                finally:
                    async with self._lock:
                        self._current_job_id = None
                        self._current_video_id = None
                    self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Unexpected error in JobQueue worker loop: %s", e)
                await asyncio.sleep(0.5)


# Global singleton instance
job_queue = JobQueueManager()
