import uuid
import pytest
from sqlalchemy import select
from backend.app.core.database import AsyncSessionLocal
from backend.app.models import (
    ApplicationSetting,
    Clip,
    ExportJob,
    Highlight,
    ProcessingJob,
    Transcript,
    TranscriptSegment,
    Video,
)


@pytest.mark.asyncio
async def test_models_lifecycle_and_relationships():
    """Verifies creation, querying, and cascade deletion across all 8 ORM models."""
    async with AsyncSessionLocal() as session:
        # 1. Create Video
        video_id = str(uuid.uuid4())
        video = Video(
            id=video_id,
            filename=f"{video_id}.mp4",
            original_filename="interview_sample.mp4",
            file_path=f"data/uploads/{video_id}.mp4",
            file_size_bytes=10485760,
            duration_seconds=120.5,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            audio_codec="aac",
            audio_sample_rate=48000,
            audio_channels=2,
            status="READY",
        )
        session.add(video)
        await session.commit()

        # 2. Create ProcessingJob
        job_id = str(uuid.uuid4())
        job = ProcessingJob(
            id=job_id,
            video_id=video_id,
            job_type="TRANSCRIPTION",
            status="QUEUED",
            progress_percent=0.0,
            current_step="Queued for processing",
        )
        session.add(job)

        # 3. Create Transcript
        transcript_id = str(uuid.uuid4())
        transcript = Transcript(
            id=transcript_id,
            video_id=video_id,
            model_name="base.en",
            compute_type="float16",
            language="en",
            full_text="Welcome to the Clipsly system test.",
            word_count=6,
            processing_time_seconds=1.2,
            is_active=True,
        )
        session.add(transcript)
        await session.commit()

        # 4. Create TranscriptSegment
        seg_id = str(uuid.uuid4())
        seg = TranscriptSegment(
            id=seg_id,
            transcript_id=transcript_id,
            segment_index=0,
            start_ms=0,
            end_ms=2500,
            text="Welcome to the Clipsly system test.",
            words_json='[{"word": "Welcome", "start_ms": 0, "end_ms": 500, "confidence": 0.98}]',
            avg_confidence=0.98,
        )
        session.add(seg)

        # 5. Create Highlight
        highlight_id = str(uuid.uuid4())
        highlight = Highlight(
            id=highlight_id,
            video_id=video_id,
            transcript_id=transcript_id,
            start_ms=0,
            end_ms=10000,
            duration_ms=10000,
            hook_sentence="Welcome to the Clipsly system test.",
            summary="Introductory hook statement.",
            hook_score=92.0,
            coherence_score=88.5,
            density_score=85.0,
            sentiment_score=78.0,
            composite_score=89.5,
            category="Insight",
            status="CANDIDATE",
        )
        session.add(highlight)
        await session.commit()

        # 6. Create Clip
        clip_id = str(uuid.uuid4())
        clip = Clip(
            id=clip_id,
            video_id=video_id,
            highlight_id=highlight_id,
            title="Intro Hook",
            start_ms=0,
            end_ms=10000,
            duration_ms=10000,
            aspect_ratio_mode="BLUR_PAD",
            subtitle_enabled=True,
            subtitle_style_preset="KARAOKE_AMBER",
            status="DRAFT",
        )
        session.add(clip)
        await session.commit()

        # 7. Create ExportJob
        export_id = str(uuid.uuid4())
        export_job = ExportJob(
            id=export_id,
            clip_id=clip_id,
            video_id=video_id,
            output_filename=f"{clip_id}_9x16.mp4",
            output_path=f"data/exports/{clip_id}_9x16.mp4",
            resolution="1080x1920",
            fps=30.0,
            encoder="h264_nvenc",
            status="QUEUED",
            progress_percent=0.0,
        )
        session.add(export_job)

        # 8. Create ApplicationSetting
        setting_key = f"test_key_{uuid.uuid4().hex[:8]}"
        setting = ApplicationSetting(
            key=setting_key,
            value="test_value",
            category="testing",
            description="Ephemeral setting for testing",
        )
        session.add(setting)
        await session.commit()

        # Verify all records queryable
        v_fetched = (await session.execute(select(Video).where(Video.id == video_id))).scalar_one_or_none()
        assert v_fetched is not None
        assert v_fetched.original_filename == "interview_sample.mp4"

        s_fetched = (await session.execute(select(ApplicationSetting).where(ApplicationSetting.key == setting_key))).scalar_one_or_none()
        assert s_fetched is not None
        assert s_fetched.value == "test_value"

        # Test Cascade Deletion: deleting video should cascade to jobs, transcripts, segments, highlights, clips, exports
        await session.delete(v_fetched)
        await session.delete(s_fetched)
        await session.commit()

        # Verify cascade removed child rows
        assert (await session.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one_or_none() is None
        assert (await session.execute(select(Transcript).where(Transcript.id == transcript_id))).scalar_one_or_none() is None
        assert (await session.execute(select(TranscriptSegment).where(TranscriptSegment.id == seg_id))).scalar_one_or_none() is None
        assert (await session.execute(select(Highlight).where(Highlight.id == highlight_id))).scalar_one_or_none() is None
        assert (await session.execute(select(Clip).where(Clip.id == clip_id))).scalar_one_or_none() is None
        assert (await session.execute(select(ExportJob).where(ExportJob.id == export_id))).scalar_one_or_none() is None
