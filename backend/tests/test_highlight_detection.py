"""Clipsly Phase 16: AI Highlight Detection and Clip Intelligence Test Suite.

Verifies:
1. Candidate window generation and duration preset parsing
2. Word boundary pause trimming
3. Heuristic scoring across Hook (30%), Coherence (30%), Density (25%), Sentiment (15%)
4. Temporal overlap calculation and greedy Non-Maximum Suppression (NMS)
5. Candidate ranking, filtering, and 1-based rank assignment
6. Pipeline orchestrator execution, transactional persistence, and redetection semantics
7. Cooperative cancellation and Sequential JobQueueManager integration
8. REST API endpoints (detection, listing, retrieval, fine-tuning, accept, reject)
"""
import asyncio
from datetime import datetime, timezone
import json
import uuid
from typing import Any, Dict, List

from httpx import AsyncClient
import pytest
from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.core.exceptions import (
    ConflictError,
    InvalidFileFormatError,
    NotFoundError,
)
from backend.app.models.highlight import Highlight
from backend.app.models.processing_job import ProcessingJob
from backend.app.models.transcript import Transcript
from backend.app.models.transcript_segment import TranscriptSegment
from backend.app.models.video import Video
from backend.app.services.highlight_detection import (
    CandidateWindow,
    DetectionConfig,
    ScoredCandidate,
    calculate_candidate_overlap,
    calculate_temporal_overlap,
    cancel_highlight_detection,
    deduplicate_candidates,
    detect_highlights_pipeline,
    extract_window_features,
    generate_candidate_windows,
    parse_duration_presets,
    rank_and_filter_candidates,
    score_candidate_window,
    validate_candidate_window,
    validate_detection_config,
)
from backend.app.services.queue import job_queue


# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------

class DummySegment:
    def __init__(
        self,
        start_ms: int,
        end_ms: int,
        text: str,
        words: List[Dict[str, Any]] = None,
        segment_index: int = 0,
    ):
        self.start_ms = start_ms
        self.end_ms = end_ms
        self.text = text
        self.words = words or []
        self.segment_index = segment_index


async def create_test_video(
    duration_seconds: float = 120.0,
    filename: str = "test_highlight_vid.mp4",
) -> str:
    """Helper creating a test Video record in SQLite."""
    video_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        v = Video(
            id=video_id,
            filename=filename,
            original_filename="sample_interview.mp4",
            file_path=f"data/uploads/{video_id}.mp4",
            file_size_bytes=10000000,
            duration_seconds=duration_seconds,
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
        session.add(v)
        await session.commit()
    return video_id


async def create_test_transcript_with_segments(
    video_id: str,
    segments_data: List[Dict[str, Any]],
) -> str:
    """Helper creating a completed Transcript and TranscriptSegments in SQLite."""
    transcript_id = str(uuid.uuid4())
    full_text = " ".join(s["text"] for s in segments_data)
    total_words = sum(len(s["text"].split()) for s in segments_data)

    async with AsyncSessionLocal() as session:
        t = Transcript(
            id=transcript_id,
            video_id=video_id,
            audio_asset_id=None,
            model_name="base",
            compute_type="float16",
            device="cuda",
            language="en",
            language_probability=0.99,
            status="COMPLETED",
            full_text=full_text,
            word_count=total_words,
            segment_count=len(segments_data),
            audio_duration_seconds=120.0,
            is_active=True,
        )
        session.add(t)

        for idx, seg in enumerate(segments_data):
            words = seg.get("words", [])
            s_entity = TranscriptSegment(
                id=str(uuid.uuid4()),
                transcript_id=transcript_id,
                segment_index=idx,
                start_ms=seg["start_ms"],
                end_ms=seg["end_ms"],
                text=seg["text"],
                words_json=json.dumps(words),
                avg_confidence=0.98,
            )
            session.add(s_entity)

        await session.commit()
    return transcript_id


# ---------------------------------------------------------------------------
# Unit Tests: Config & Validators
# ---------------------------------------------------------------------------

def test_parse_duration_presets():
    """Verifies duration preset parsing from string formats."""
    presets = ["15-30", "30-60", "60-90", "invalid-str", "50-20"]
    parsed = parse_duration_presets(presets)
    assert len(parsed) == 3
    assert (15.0, 30.0) in parsed
    assert (30.0, 60.0) in parsed
    assert (60.0, 90.0) in parsed

    fallback = parse_duration_presets(["bad"], global_min_s=20.0, global_max_s=40.0)
    assert fallback == [(20.0, 40.0)]


def test_validate_detection_config():
    """Verifies bounds and constraint validation for DetectionConfig."""
    valid_config = DetectionConfig()
    validate_detection_config(valid_config, video_duration_seconds=60.0)

    # Inverted min/max
    bad_bounds = DetectionConfig(min_duration_seconds=60.0, max_duration_seconds=30.0)
    with pytest.raises(InvalidFileFormatError):
        validate_detection_config(bad_bounds)

    # Out of range duration (< 10s or > 180s)
    with pytest.raises(Exception):
        DetectionConfig(min_duration_seconds=5.0)

    # Weights sum not 1.0
    with pytest.raises(Exception):
        bad_weights = DetectionConfig(hook_weight=0.5, coherence_weight=0.5, density_weight=0.5)
        validate_detection_config(bad_weights)


def test_validate_candidate_window():
    """Verifies timing and physical constraints on candidate windows."""
    valid_window = CandidateWindow(
        start_ms=1000,
        end_ms=25000,
        duration_ms=24000,
        start_segment_idx=0,
        end_segment_idx=2,
        text="Why did the rocket explode on launch? It was an extraordinary engineering mistake.",
    )
    is_valid, reason = validate_candidate_window(valid_window, video_duration_seconds=30.0)
    assert is_valid is True
    assert reason is None

    # Negative start
    bad_start = CandidateWindow(start_ms=-100, end_ms=20000, duration_ms=20100, start_segment_idx=0, end_segment_idx=1, text="Sample text")
    assert validate_candidate_window(bad_start)[0] is False

    # End <= start
    bad_end = CandidateWindow(start_ms=5000, end_ms=5000, duration_ms=0, start_segment_idx=0, end_segment_idx=1, text="Sample text")
    assert validate_candidate_window(bad_end)[0] is False

    # Duration too short (< 10s default)
    too_short = CandidateWindow(start_ms=1000, end_ms=4000, duration_ms=3000, start_segment_idx=0, end_segment_idx=1, text="Sample text")
    assert validate_candidate_window(too_short, min_duration_ms=10000)[0] is False

    # Insufficient words
    empty_words = CandidateWindow(start_ms=1000, end_ms=15000, duration_ms=14000, start_segment_idx=0, end_segment_idx=1, text="One two")
    assert validate_candidate_window(empty_words)[0] is False


# ---------------------------------------------------------------------------
# Unit Tests: Candidate Window Generator
# ---------------------------------------------------------------------------

def test_generate_candidate_windows_presets():
    """Verifies that windows are generated conforming to duration presets."""
    segments = [
        DummySegment(0, 8000, "Why is everyone talking about local first AI?"),
        DummySegment(8000, 18000, "Because when your data never leaves your GPU, privacy is truly guaranteed."),
        DummySegment(18000, 29000, "You don't have to worry about external API bills or sudden rate limit outages."),
        DummySegment(29000, 42000, "In fact, running Faster-Whisper locally on an RTX 3050 delivers incredible speed."),
    ]
    config = DetectionConfig(target_duration_presets=["15-30", "30-60"], min_score=40.0)
    windows = generate_candidate_windows(segments, config, video_duration_seconds=60.0)

    assert len(windows) > 0
    for w in windows:
        dur_s = w.duration_seconds
        assert 15.0 <= dur_s <= 60.0
        assert len(w.text.split()) >= 3


def test_generate_candidate_windows_word_trimming():
    """Verifies that word timestamps refine starting and ending pause margins."""
    words_seg1 = [
        {"word": "What", "start_ms": 1500, "end_ms": 2000},
        {"word": "happened?", "start_ms": 2100, "end_ms": 3000},
    ]
    words_seg2 = [
        {"word": "Everything", "start_ms": 8200, "end_ms": 9000},
        {"word": "changed.", "start_ms": 9100, "end_ms": 19500},
    ]
    segments = [
        DummySegment(1000, 8000, "What happened?", words=words_seg1),
        DummySegment(8000, 22000, "Everything changed.", words=words_seg2),
    ]
    config = DetectionConfig(min_duration_seconds=15.0, max_duration_seconds=30.0, target_duration_presets=["15-30"])
    windows = generate_candidate_windows(segments, config, video_duration_seconds=30.0)

    assert len(windows) == 1
    w = windows[0]
    # Starting boundary should be trimmed to first word start (1500ms instead of 1000ms)
    assert w.start_ms == 1500
    # Ending boundary should be trimmed to last word end (19500ms instead of 22000ms)
    assert w.end_ms == 19500


# ---------------------------------------------------------------------------
# Unit Tests: Feature Extraction & Scoring Engine
# ---------------------------------------------------------------------------

def test_feature_extractor_hook_strength():
    """Verifies hook classification for questions, provocative phrases, and imperatives."""
    features_q = extract_window_features(
        text="Why does this simple mistake ruin entire video productions?",
        duration_seconds=20.0,
    )
    assert features_q["hook"]["is_question"] is True

    features_prov = extract_window_features(
        text="Nobody understands how video algorithms actually work.",
        duration_seconds=20.0,
    )
    assert features_prov["hook"]["is_provocative"] is True

    features_direct = extract_window_features(
        text="You need to understand this critical fact about video editing.",
        duration_seconds=20.0,
    )
    assert features_direct["hook"]["has_direct_address"] is True

    features_imp = extract_window_features(
        text="Stop editing your videos like it's 2015.",
        duration_seconds=20.0,
    )
    assert features_imp["hook"]["is_imperative"] is True


def test_scoring_engine_breakdown_and_weights():
    """Verifies that composite score correctly weights hook, flow, density, and energy."""
    window = CandidateWindow(
        start_ms=0,
        end_ms=25000,
        duration_ms=25000,
        start_segment_idx=0,
        end_segment_idx=1,
        text="Why does this trick blow people's minds? Absolutely because it saves ten hours every week!",
    )
    config = DetectionConfig(
        hook_weight=0.30,
        coherence_weight=0.30,
        density_weight=0.25,
        sentiment_weight=0.15,
    )
    score_breakdown = score_candidate_window(window, config)

    assert score_breakdown.hook_score > 60.0
    assert score_breakdown.coherence_score >= 70.0
    assert score_breakdown.composite_score >= 60.0
    assert "Why does this trick blow people's minds?" in score_breakdown.hook_sentence
    assert len(score_breakdown.explanation) > 10


# ---------------------------------------------------------------------------
# Unit Tests: Deduplication & Ranking
# ---------------------------------------------------------------------------

def test_calculate_temporal_overlap():
    """Verifies Intersection over Minimum Duration overlap calculation."""
    # Complete containment: 10-20s inside 0-30s -> overlap should be 1.0 (100% of the shorter window)
    overlap = calculate_temporal_overlap(10000, 20000, 0, 30000)
    assert overlap == 1.0

    # No overlap
    no_overlap = calculate_temporal_overlap(0, 10000, 15000, 25000)
    assert no_overlap == 0.0

    # 50% overlap of shorter window
    half_overlap = calculate_temporal_overlap(0, 10000, 5000, 15000)
    assert half_overlap == 0.5


def test_deduplicate_candidates_nms():
    """Verifies greedy Non-Maximum Suppression eliminates overlapping duplicates."""
    w1 = CandidateWindow(0, 25000, 25000, 0, 1, "Best hook window")
    w2 = CandidateWindow(5000, 25000, 20000, 0, 1, "Slightly shorter overlapping window")
    w3 = CandidateWindow(40000, 65000, 25000, 2, 3, "Distinct completely non-overlapping window")

    config = DetectionConfig()
    scored = [
        ScoredCandidate(window=w1, scores=score_candidate_window(w1, config)),
        ScoredCandidate(window=w2, scores=score_candidate_window(w2, config)),
        ScoredCandidate(window=w3, scores=score_candidate_window(w3, config)),
    ]
    # Artificially set w1 score higher than w2
    scored[0].scores.composite_score = 85.0
    scored[1].scores.composite_score = 72.0
    scored[2].scores.composite_score = 80.0

    deduped = deduplicate_candidates(scored, overlap_threshold=0.45)
    # w2 should be suppressed by w1 because they overlap heavily
    assert len(deduped) == 2
    assert deduped[0].window == w1
    assert deduped[1].window == w3


def test_rank_and_filter_candidates():
    """Verifies score threshold filtering, max results slicing, and 1-based rank."""
    w1 = CandidateWindow(0, 20000, 20000, 0, 1, "Window 1")
    w2 = CandidateWindow(25000, 45000, 20000, 1, 2, "Window 2")
    w3 = CandidateWindow(50000, 70000, 20000, 2, 3, "Window 3")

    config = DetectionConfig()
    cands = [
        ScoredCandidate(window=w1, scores=score_candidate_window(w1, config)),
        ScoredCandidate(window=w2, scores=score_candidate_window(w2, config)),
        ScoredCandidate(window=w3, scores=score_candidate_window(w3, config)),
    ]
    cands[0].scores.composite_score = 45.0  # Below min_score 50
    cands[1].scores.composite_score = 88.0
    cands[2].scores.composite_score = 75.0

    ranked = rank_and_filter_candidates(cands, min_score=50.0, max_results=10)
    assert len(ranked) == 2
    assert ranked[0].composite_score == 88.0
    assert ranked[0].rank == 1
    assert ranked[1].composite_score == 75.0
    assert ranked[1].rank == 2


# ---------------------------------------------------------------------------
# Integration Tests: Pipeline Orchestrator & Persistence
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_detect_highlights_pipeline_full_workflow():
    """Executes the full highlight detection pipeline against a database video and transcript."""
    video_id = await create_test_video(duration_seconds=90.0)
    segments = [
        {"start_ms": 0, "end_ms": 10000, "text": "What is the single most important secret to viral videos?"},
        {"start_ms": 10000, "end_ms": 22000, "text": "You must grab their attention within the first three seconds or they swipe away."},
        {"start_ms": 22000, "end_ms": 35000, "text": "That is why great creators spend hours testing different opening hook sentences."},
        {"start_ms": 40000, "end_ms": 55000, "text": "In addition, always ensure your audio delivery pacing is clear and energetic."},
        {"start_ms": 55000, "end_ms": 70000, "text": "Nobody wants to listen to mumbled dialogue with heavy background noise."},
    ]
    await create_test_transcript_with_segments(video_id, segments)

    config = DetectionConfig(
        target_duration_presets=["15-30", "30-60"],
        min_score=50.0,
        max_results=5,
    )
    highlights = await detect_highlights_pipeline(video_id=video_id, config=config)

    assert len(highlights) >= 1
    top = highlights[0]
    assert top.video_id == video_id
    assert top.rank == 1
    assert top.status == "CANDIDATE"
    assert top.composite_score >= 50.0
    assert top.duration_ms >= 10000
    assert top.hook_sentence is not None
    assert top.explanation is not None


@pytest.mark.asyncio
async def test_detect_highlights_pipeline_empty_transcript():
    """Verifies that an empty transcript yields 0 highlights gracefully without crashing."""
    video_id = await create_test_video(duration_seconds=60.0)
    # Transcript with whitespace only
    await create_test_transcript_with_segments(video_id, [{"start_ms": 0, "end_ms": 5000, "text": "   "}])

    highlights = await detect_highlights_pipeline(video_id=video_id)
    assert len(highlights) == 0


@pytest.mark.asyncio
async def test_detect_highlights_pipeline_no_transcript():
    """Verifies that missing completed transcript raises ConflictError."""
    video_id = await create_test_video(duration_seconds=60.0)
    with pytest.raises(ConflictError) as exc_info:
        await detect_highlights_pipeline(video_id=video_id)
    assert "No completed transcript found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_detect_highlights_pipeline_preserves_reviewed_highlights():
    """Verifies that re-detection replaces CANDIDATE highlights but preserves ACCEPTED/REJECTED ones."""
    video_id = await create_test_video(duration_seconds=90.0)
    segments = [
        {"start_ms": 0, "end_ms": 12000, "text": "Why is local AI dominating content creation today?"},
        {"start_ms": 12000, "end_ms": 26000, "text": "Because creators demand total privacy and zero external cloud subscription costs."},
        {"start_ms": 30000, "end_ms": 48000, "text": "You can generate vertical clips right on your RTX 3050 in seconds."},
    ]
    t_id = await create_test_transcript_with_segments(video_id, segments)

    # First run
    initial_highlights = await detect_highlights_pipeline(video_id=video_id)
    assert len(initial_highlights) >= 1

    # Manually mark first highlight as ACCEPTED
    accepted_id = initial_highlights[0].id
    async with AsyncSessionLocal() as session:
        h = await session.get(Highlight, accepted_id)
        assert h is not None
        h.status = "ACCEPTED"
        h.reviewed_at = datetime.now(timezone.utc)
        await session.commit()

    # Run redetection
    new_highlights = await detect_highlights_pipeline(video_id=video_id)

    # Verify that the ACCEPTED highlight still exists in database
    async with AsyncSessionLocal() as session:
        stmt = select(Highlight).where(Highlight.id == accepted_id)
        res = await session.execute(stmt)
        preserved = res.scalar_one_or_none()
        assert preserved is not None
        assert preserved.status == "ACCEPTED"


# ---------------------------------------------------------------------------
# Integration Tests: REST API Endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_detect_video_highlights_route(async_client: AsyncClient):
    """Verifies POST /api/v1/videos/{video_id}/highlights/detect queues job and returns 202."""
    video_id = await create_test_video(duration_seconds=60.0)
    segments = [
        {"start_ms": 0, "end_ms": 15000, "text": "Why did we build Clipsly this way?"},
        {"start_ms": 15000, "end_ms": 30000, "text": "Because offline local video editing gives users total sovereignty over their media."},
    ]
    await create_test_transcript_with_segments(video_id, segments)

    res = await async_client.post(
        f"/api/v1/videos/{video_id}/highlights/detect",
        json={"target_duration_presets": ["15-30"], "min_score": 40.0},
    )
    assert res.status_code == 202
    data = res.json()
    assert "job_id" in data
    assert data["video_id"] == video_id
    assert data["status"] == "PENDING"


@pytest.mark.asyncio
async def test_api_list_video_highlights_route(async_client: AsyncClient):
    """Verifies GET /api/v1/videos/{video_id}/highlights and GET /api/v1/highlights/{video_id}."""
    video_id = await create_test_video(duration_seconds=60.0)
    segments = [
        {"start_ms": 0, "end_ms": 15000, "text": "How do you achieve 100% reproducible results?"},
        {"start_ms": 15000, "end_ms": 30000, "text": "By using deterministic heuristic rules and mathematical models instead of black-box APIs."},
    ]
    await create_test_transcript_with_segments(video_id, segments)
    await detect_highlights_pipeline(video_id=video_id)

    # Query via /videos/{video_id}/highlights
    res1 = await async_client.get(f"/api/v1/videos/{video_id}/highlights")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["video_id"] == video_id
    assert data1["total"] >= 1
    assert len(data1["highlights"]) >= 1

    # Query via /highlights/{video_id}
    res2 = await async_client.get(f"/api/v1/highlights/{video_id}")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total"] == data1["total"]


@pytest.mark.asyncio
async def test_api_highlight_detail_and_update(async_client: AsyncClient):
    """Verifies GET /highlights/detail/{id} and PATCH /highlights/{id}."""
    video_id = await create_test_video(duration_seconds=60.0)
    segments = [
        {"start_ms": 0, "end_ms": 15000, "text": "Can we edit the boundary timestamps later?"},
        {"start_ms": 15000, "end_ms": 30000, "text": "Absolutely, users can fine-tune start and end timestamps directly from the card."},
    ]
    await create_test_transcript_with_segments(video_id, segments)
    created = await detect_highlights_pipeline(video_id=video_id)
    assert len(created) >= 1
    hl_id = created[0].id

    # Get detail
    res_get = await async_client.get(f"/api/v1/highlights/detail/{hl_id}")
    assert res_get.status_code == 200
    detail = res_get.json()
    assert detail["id"] == hl_id
    assert "explanation" in detail
    assert "warnings" in detail

    # Patch start_ms and summary
    res_patch = await async_client.patch(
        f"/api/v1/highlights/{hl_id}",
        json={"start_ms": 500, "summary": "Updated editorial summary"},
    )
    assert res_patch.status_code == 200
    patched = res_patch.json()
    assert patched["start_ms"] == 500
    assert patched["summary"] == "Updated editorial summary"


@pytest.mark.asyncio
async def test_api_accept_and_reject_lifecycle(async_client: AsyncClient):
    """Verifies POST /highlights/{id}/accept and POST /highlights/{id}/reject."""
    video_id = await create_test_video(duration_seconds=60.0)
    segments = [
        {"start_ms": 0, "end_ms": 15000, "text": "Should we approve or reject this candidate clip?"},
        {"start_ms": 15000, "end_ms": 30000, "text": "Editors can review each candidate clip before slicing and rendering video."},
    ]
    await create_test_transcript_with_segments(video_id, segments)
    created = await detect_highlights_pipeline(video_id=video_id)
    assert len(created) >= 1
    hl_id = created[0].id

    # Accept
    res_accept = await async_client.post(f"/api/v1/highlights/{hl_id}/accept")
    assert res_accept.status_code == 200
    assert res_accept.json()["status"] == "ACCEPTED"
    assert res_accept.json()["reviewed_at"] is not None

    # Reject with reason
    res_reject = await async_client.post(
        f"/api/v1/highlights/{hl_id}/reject",
        json={"rejection_reason": "Hook was not punchy enough for short-form feed"},
    )
    assert res_reject.status_code == 200
    rejected = res_reject.json()
    assert rejected["status"] == "REJECTED"
    assert rejected["rejection_reason"] == "Hook was not punchy enough for short-form feed"


@pytest.mark.asyncio
async def test_highlight_queue_and_cancellation():
    """Verifies that cancel_highlight_detection stops actively executing detection."""
    video_id = await create_test_video(duration_seconds=60.0)
    job_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        job = ProcessingJob(
            id=job_id,
            video_id=video_id,
            job_type="HIGHLIGHT_DETECTION",
            status="PROCESSING",
            progress_percent=25.0,
            current_step="Analyzing candidate windows",
        )
        session.add(job)
        await session.commit()

    # Cancel job
    async with AsyncSessionLocal() as session:
        cancelled = await cancel_highlight_detection(job_id, session)
        assert cancelled is True

    # Verify status in database
    async with AsyncSessionLocal() as session:
        db_job = await session.get(ProcessingJob, job_id)
        assert db_job is not None
        assert db_job.status == "CANCELLED"
        assert db_job.completed_at is not None


def test_feature_extractor_coherence_terminal_punctuation():
    """Verifies complete sentence bonus and dangling conjunction penalties."""
    clean = extract_window_features(
        text="This is an independent thought that terminates properly.",
        duration_seconds=15.0,
    )
    assert clean["coherence"]["ends_cleanly"] is True
    assert clean["coherence"]["starts_mid_clause"] is False

    dangling = extract_window_features(
        text="And so we went to the place because",
        duration_seconds=15.0,
    )
    assert dangling["coherence"]["starts_mid_clause"] is True
    assert dangling["coherence"]["ends_incomplete"] is True


def test_feature_extractor_density_wpm_and_fillers():
    """Verifies WPM and filler word calculations."""
    optimal_text = " ".join(["word"] * 50)
    features_optimal = extract_window_features(optimal_text, duration_seconds=20.0)
    # 50 words / (20/60 min) = 150 WPM (optimal 130-180)
    assert 130.0 <= features_optimal["density"]["wpm"] <= 180.0

    fillers_text = "Um you know basically like literally sort of kind of test."
    features_fillers = extract_window_features(fillers_text, duration_seconds=15.0)
    assert features_fillers["density"]["filler_count"] >= 4
    assert features_fillers["density"]["filler_ratio"] > 0.05


def test_feature_extractor_sentiment_conviction_and_humor():
    """Verifies conviction markers, exclamations, and humorous tone markers."""
    text = "This is absolutely incredible! Haha it was totally hilarious."
    features = extract_window_features(text, duration_seconds=20.0)
    assert features["sentiment"]["conviction_count"] >= 1
    assert features["sentiment"]["exclamation_count"] >= 1
    assert features["sentiment"]["humor_count"] >= 1


def test_candidate_generator_empty_segments():
    """Verifies that candidate generator handles empty or whitespace-only segment inputs safely."""
    config = DetectionConfig()
    assert generate_candidate_windows([], config) == []
    empty_segs = [DummySegment(0, 5000, "   "), DummySegment(5000, 10000, "")]
    assert generate_candidate_windows(empty_segs, config) == []


def test_candidate_generator_max_duration_cutoff():
    """Verifies that window expansion stops when duration exceeds the maximum limit."""
    segments = [
        DummySegment(i * 10000, (i + 1) * 10000, f"Segment number {i} with some content.")
        for i in range(25)
    ]
    config = DetectionConfig(
        min_duration_seconds=15.0,
        max_duration_seconds=30.0,
        target_duration_presets=["15-30"],
    )
    windows = generate_candidate_windows(segments, config)
    assert len(windows) > 0
    for w in windows:
        assert w.duration_seconds <= 30.0


@pytest.mark.asyncio
async def test_api_detect_highlights_conflict(async_client: AsyncClient):
    """Verifies 409 Conflict when submitting a second detection while video is active."""
    video_id = await create_test_video(duration_seconds=60.0)
    segments = [{"start_ms": 0, "end_ms": 20000, "text": "Testing concurrent conflict protection."}]
    await create_test_transcript_with_segments(video_id, segments)

    from backend.app.services.highlight_detection.detector import _active_detections
    _active_detections.add(video_id)
    try:
        res = await async_client.post(
            f"/api/v1/videos/{video_id}/highlights/detect",
            json={"min_score": 40.0},
        )
        assert res.status_code == 409
        assert res.json()["error_code"] == "CONFLICT"
    finally:
        _active_detections.discard(video_id)


@pytest.mark.asyncio
async def test_api_get_nonexistent_highlight(async_client: AsyncClient):
    """Verifies 404 when querying a nonexistent highlight ID."""
    fake_id = str(uuid.uuid4())
    res = await async_client.get(f"/api/v1/highlights/detail/{fake_id}")
    assert res.status_code == 404
    assert res.json()["error_code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_api_update_highlight_invalid_timestamps(async_client: AsyncClient):
    """Verifies validation error when start_ms is negative or end_ms <= start_ms."""
    video_id = await create_test_video(duration_seconds=60.0)
    segments = [
        {"start_ms": 0, "end_ms": 15000, "text": "Valid test candidate for timing validation."},
        {"start_ms": 15000, "end_ms": 30000, "text": "Second segment to ensure sufficient duration."},
    ]
    await create_test_transcript_with_segments(video_id, segments)
    created = await detect_highlights_pipeline(video_id=video_id)
    assert len(created) >= 1
    hl_id = created[0].id

    # end_ms <= start_ms
    res = await async_client.patch(
        f"/api/v1/highlights/{hl_id}",
        json={"start_ms": 20000, "end_ms": 10000},
    )
    assert res.status_code == 400
    assert "end_ms must be strictly greater than start_ms" in res.json()["detail"]
