import json
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.clip import Clip
from backend.app.models.subtitle_event import SubtitleEvent
from backend.app.models.subtitle_track import SubtitleTrack
from backend.app.models.transcript import Transcript
from backend.app.models.transcript_segment import TranscriptSegment
from backend.app.models.video import Video
from backend.app.services.subtitles.schemas import NormalizedWord, SubtitleGenerateRequest
from backend.app.services.subtitles.sync_service import (
    create_subtitle_track_for_clip,
    extract_words_from_segment,
    generate_caption_events_for_clip,
    get_active_subtitle_track_for_clip,
    sync_transcript_words_to_clip,
)
from backend.app.services.subtitles.timing_engine import (
    chunk_words_into_events,
    interpolate_missing_word_timestamps,
)
from backend.app.services.subtitles.validators import (
    SubtitleValidationError,
    validate_caption_events,
    validate_clip_timing,
    validate_normalized_words,
)


# --- Unit Tests: Timing Engine & Interpolation ---

def test_interpolate_missing_word_timestamps_normal():
    """Verifies duration-safe proportional interpolation across standard tokens."""
    text = "The secret to massive productivity"
    start_ms = 1000
    end_ms = 3500
    words = interpolate_missing_word_timestamps(text, start_ms, end_ms)

    assert len(words) == 5
    assert words[0].text == "The"
    assert words[-1].text == "productivity"

    # Strict boundary containment
    assert words[0].start_ms == start_ms
    assert words[-1].end_ms == end_ms

    # Strictly monotonic non-overlapping intervals
    for i in range(len(words) - 1):
        assert words[i].end_ms == words[i + 1].start_ms
        assert words[i].end_ms > words[i].start_ms

    # Sum of durations equals segment duration exactly
    total_dur = sum(w.end_ms - w.start_ms for w in words)
    assert total_dur == (end_ms - start_ms)


def test_interpolate_missing_word_timestamps_very_short_segment():
    """Verifies that short segments (e.g. 80ms) do NOT inflate duration beyond segment bounds."""
    text = "one two three"
    start_ms = 500
    end_ms = 580  # 80ms total
    words = interpolate_missing_word_timestamps(text, start_ms, end_ms)

    assert len(words) == 3
    assert words[0].start_ms == 500
    assert words[-1].end_ms == 580

    total_dur = sum(w.end_ms - w.start_ms for w in words)
    assert total_dur == 80  # Does not exceed 80ms!


def test_interpolate_missing_word_timestamps_many_words_tiny_duration():
    """Verifies pathological case: 5 tokens inside a 2ms window safely groups tokens without overlap."""
    text = "word1 word2 word3 word4 word5"
    start_ms = 100
    end_ms = 102  # 2ms total for 5 tokens
    words = interpolate_missing_word_timestamps(text, start_ms, end_ms)

    # Must be bounded within 100 to 102
    assert len(words) > 0
    assert words[0].start_ms == 100
    assert words[-1].end_ms == 102
    total_dur = sum(w.end_ms - w.start_ms for w in words)
    assert total_dur == 2


def test_interpolate_punctuation_preservation():
    """Verifies punctuation attached to words is fully preserved."""
    text = "Wait, what? Really! Yes..."
    words = interpolate_missing_word_timestamps(text, 0, 2000)
    assert [w.text for w in words] == ["Wait,", "what?", "Really!", "Yes..."]


def test_interpolate_empty_text():
    """Verifies empty or whitespace text yields empty list."""
    assert interpolate_missing_word_timestamps("", 0, 1000) == []
    assert interpolate_missing_word_timestamps("   ", 0, 1000) == []
    assert interpolate_missing_word_timestamps("Hello", 1000, 1000) == []


# --- Unit Tests: Caption Event Chunking ---

def test_chunk_words_into_events_word_limit():
    """Verifies splitting when max_words_per_line is reached."""
    words = [
        NormalizedWord(text=f"word{i}", start_ms=i * 500, end_ms=(i + 1) * 500)
        for i in range(10)
    ]
    events = chunk_words_into_events(words, max_words_per_line=3, min_pause_ms=1000)
    # 10 words with max 3 per line should produce 4 events (3, 3, 3, 1)
    assert len(events) == 4
    assert len(events[0].words) == 3
    assert len(events[1].words) == 3
    assert len(events[2].words) == 3
    assert len(events[3].words) == 1
    assert events[0].text == "word0 word1 word2"


def test_chunk_words_into_events_terminal_punctuation():
    """Verifies splitting on sentence-ending punctuation even before word limit."""
    words = [
        NormalizedWord(text="Hello", start_ms=0, end_ms=300),
        NormalizedWord(text="world.", start_ms=350, end_ms=700),  # Terminal dot
        NormalizedWord(text="How", start_ms=750, end_ms=900),
        NormalizedWord(text="are", start_ms=920, end_ms=1100),
        NormalizedWord(text="you?", start_ms=1150, end_ms=1400),
    ]
    events = chunk_words_into_events(words, max_words_per_line=5)
    assert len(events) == 2
    assert events[0].text == "Hello world."
    assert events[1].text == "How are you?"


def test_chunk_words_into_events_speech_pause():
    """Verifies splitting on silences >= 350ms."""
    words = [
        NormalizedWord(text="First", start_ms=0, end_ms=400),
        NormalizedWord(text="part", start_ms=450, end_ms=800),
        # 500ms pause here: 1300 - 800 = 500ms >= 350ms
        NormalizedWord(text="Second", start_ms=1300, end_ms=1700),
        NormalizedWord(text="part", start_ms=1750, end_ms=2100),
    ]
    events = chunk_words_into_events(words, max_words_per_line=5, min_pause_ms=350)
    assert len(events) == 2
    assert events[0].text == "First part"
    assert events[1].text == "Second part"


# --- Unit Tests: Transcript Synchronization Service ---

def test_sync_words_clip_boundary_crossing():
    """Verifies handling of words crossing clip boundaries and words outside clip."""
    # Clip window: 5000ms to 15000ms (10000ms duration)
    clip_start = 5000
    clip_end = 15000

    # Segments
    seg1 = TranscriptSegment(
        id=str(uuid.uuid4()),
        transcript_id=str(uuid.uuid4()),
        segment_index=0,
        start_ms=3000,
        end_ms=7000,
        text="Outside StartInside",
        words_json=json.dumps([
            {"word": "Outside", "start_ms": 3000, "end_ms": 4800},         # Strictly outside before start
            {"word": "StartCrossing", "start_ms": 4600, "end_ms": 5500},   # Straddles clip_start (4600 -> 5500)
            {"word": "InsideOne", "start_ms": 5600, "end_ms": 6800},       # Fully inside
        ]),
    )
    seg2 = TranscriptSegment(
        id=str(uuid.uuid4()),
        transcript_id=str(uuid.uuid4()),
        segment_index=1,
        start_ms=13000,
        end_ms=18000,
        text="EndCrossing OutsideAfter",
        words_json=json.dumps([
            {"word": "InsideTwo", "start_ms": 13500, "end_ms": 14200},     # Fully inside
            {"word": "EndCrossing", "start_ms": 14500, "end_ms": 16000},   # Straddles clip_end (14500 -> 16000)
            {"word": "OutsideAfter", "start_ms": 16200, "end_ms": 17800},  # Strictly outside after end
        ]),
    )

    words = sync_transcript_words_to_clip([seg1, seg2], clip_start, clip_end)

    # 4 words should be retained
    assert [w.text for w in words] == ["StartCrossing", "InsideOne", "InsideTwo", "EndCrossing"]

    # StartCrossing was 4600..5500. Clamped to clip_start (5000):
    # relative start = max(0, 4600 - 5000) = 0
    # relative end = min(10000, 5500 - 5000) = 500
    assert words[0].start_ms == 0
    assert words[0].end_ms == 500

    # InsideOne was 5600..6800:
    # rel start = 600, rel end = 1800
    assert words[1].start_ms == 600
    assert words[1].end_ms == 1800

    # InsideTwo was 13500..14200:
    # rel start = 8500, rel end = 9200
    assert words[2].start_ms == 8500
    assert words[2].end_ms == 9200

    # EndCrossing was 14500..16000. Clamped to clip_end (15000):
    # rel start = 9500, rel end = min(10000, 16000 - 5000) = 10000
    assert words[3].start_ms == 9500
    assert words[3].end_ms == 10000


def test_sync_words_clip_silent_no_overlap():
    """Verifies that a clip slice covering silence returns empty word list without errors."""
    seg = TranscriptSegment(
        id=str(uuid.uuid4()),
        transcript_id=str(uuid.uuid4()),
        segment_index=0,
        start_ms=0,
        end_ms=5000,
        text="Early speech",
        words_json=json.dumps([{"word": "Early", "start_ms": 0, "end_ms": 2000}]),
    )
    # Clip is from 10000 to 20000
    words = sync_transcript_words_to_clip([seg], 10000, 20000)
    assert words == []


def test_sync_words_with_empty_words_json_fallback():
    """Verifies fallback interpolation when words_json is empty."""
    seg = TranscriptSegment(
        id=str(uuid.uuid4()),
        transcript_id=str(uuid.uuid4()),
        segment_index=0,
        start_ms=1000,
        end_ms=4000,
        text="Fallback speech words",
        words_json="[]",  # Empty words json!
    )
    words = sync_transcript_words_to_clip([seg], 1000, 4000)
    assert len(words) == 3
    assert [w.text for w in words] == ["Fallback", "speech", "words"]
    assert words[0].start_ms == 0
    assert words[-1].end_ms == 3000


def test_sync_words_overlapping_timestamps_resolved_monotonically():
    """Verifies that artificially overlapping timestamps between consecutive words are clamped monotonically."""
    seg = TranscriptSegment(
        id=str(uuid.uuid4()),
        transcript_id=str(uuid.uuid4()),
        segment_index=0,
        start_ms=0,
        end_ms=5000,
        text="Overlapping words test",
        words_json=json.dumps([
            {"word": "Overlapping", "start_ms": 0, "end_ms": 1500},
            {"word": "words", "start_ms": 1200, "end_ms": 2500},  # Overlaps with Overlapping (1200 < 1500)
            {"word": "test", "start_ms": 2200, "end_ms": 3500},   # Overlaps with words (2200 < 2500)
        ]),
    )
    words = sync_transcript_words_to_clip([seg], 0, 5000)
    assert len(words) == 3
    # First word end should be clamped to next word start (1200)
    assert words[0].end_ms == 1200
    assert words[1].start_ms == 1200
    # Second word end clamped to third word start (2200)
    assert words[1].end_ms == 2200
    assert words[2].start_ms == 2200
    assert words[2].end_ms == 3500



# --- Integration Tests: Database Persistence & Cascades ---

@pytest.mark.asyncio
async def test_database_persistence_and_cascades():
    """Tests end-to-end SQLite persistence of SubtitleTrack and SubtitleEvents,
    verifying cascade deletion on Clip removal and SET NULL on Transcript removal.
    """
    video_id = str(uuid.uuid4())
    clip_id = str(uuid.uuid4())
    transcript_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        # Create Video
        video = Video(
            id=video_id,
            filename=f"{video_id}.mp4",
            original_filename="cascade_test.mp4",
            file_path=f"storage/uploads/{video_id}.mp4",
            file_size_bytes=1024 * 1024,
            duration_seconds=60.0,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            status="READY",
        )
        session.add(video)

        # Create Transcript with 2 segments
        tx = Transcript(
            id=transcript_id,
            video_id=video_id,
            model_name="tiny",
            compute_type="int8",
            device="cpu",
            language="en",
            status="COMPLETED",
            full_text="First sentence here. Second sentence follows.",
            word_count=6,
            segment_count=2,
            is_active=True,
        )
        session.add(tx)

        seg1 = TranscriptSegment(
            id=str(uuid.uuid4()),
            transcript_id=transcript_id,
            segment_index=0,
            start_ms=0,
            end_ms=3000,
            text="First sentence here.",
            words_json=json.dumps([
                {"word": "First", "start_ms": 0, "end_ms": 800},
                {"word": "sentence", "start_ms": 900, "end_ms": 1800},
                {"word": "here.", "start_ms": 1900, "end_ms": 2800},
            ]),
        )
        seg2 = TranscriptSegment(
            id=str(uuid.uuid4()),
            transcript_id=transcript_id,
            segment_index=1,
            start_ms=3500,
            end_ms=6500,
            text="Second sentence follows.",
            words_json=json.dumps([
                {"word": "Second", "start_ms": 3500, "end_ms": 4200},
                {"word": "sentence", "start_ms": 4300, "end_ms": 5200},
                {"word": "follows.", "start_ms": 5300, "end_ms": 6400},
            ]),
        )
        session.add_all([seg1, seg2])

        # Create Clip covering 0..7000ms
        clip = Clip(
            id=clip_id,
            video_id=video_id,
            title="Cascade Test Clip",
            start_ms=0,
            end_ms=7000,
            duration_ms=7000,
            status="DRAFT",
        )
        session.add(clip)
        await session.commit()

        # Generate subtitle track
        req = SubtitleGenerateRequest(preset_name="KARAOKE_AMBER", max_words_per_line=3)
        track = await create_subtitle_track_for_clip(session, clip_id, req)

        assert track.clip_id == clip_id
        assert track.transcript_id == transcript_id
        assert len(track.events) == 2
        assert track.events[0].text == "First sentence here."
        assert track.events[1].text == "Second sentence follows."

        track_id = track.id

    # Verify querying track and events from fresh session
    async with AsyncSessionLocal() as session:
        loaded_track = await get_active_subtitle_track_for_clip(session, clip_id)
        assert loaded_track is not None
        assert loaded_track.id == track_id
        assert len(loaded_track.events) == 2

    # Verify Clip cascade deletion: Deleting Clip must delete SubtitleTrack and SubtitleEvents
    async with AsyncSessionLocal() as session:
        clip_to_delete = await session.get(Clip, clip_id)
        await session.delete(clip_to_delete)
        await session.commit()

    async with AsyncSessionLocal() as session:
        # Check track is deleted
        track_check = await session.get(SubtitleTrack, track_id)
        assert track_check is None

        # Check events are deleted
        events_check = (
            await session.execute(select(SubtitleEvent).where(SubtitleEvent.track_id == track_id))
        ).scalars().all()
        assert len(events_check) == 0


@pytest.mark.asyncio
async def test_transcript_deletion_set_null_behavior():
    """Verifies that deleting a Transcript sets SubtitleTrack.transcript_id to NULL."""
    video_id = str(uuid.uuid4())
    clip_id = str(uuid.uuid4())
    transcript_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        video = Video(
            id=video_id,
            filename=f"{video_id}.mp4",
            original_filename="setnull_test.mp4",
            file_path=f"storage/uploads/{video_id}.mp4",
            file_size_bytes=1024,
            duration_seconds=60.0,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            status="READY",
        )
        session.add(video)

        tx = Transcript(
            id=transcript_id,
            video_id=video_id,
            model_name="tiny",
            compute_type="int8",
            device="cpu",
            language="en",
            status="COMPLETED",
            full_text="Test dialogue.",
            word_count=2,
            segment_count=1,
            is_active=True,
        )
        session.add(tx)

        seg = TranscriptSegment(
            id=str(uuid.uuid4()),
            transcript_id=transcript_id,
            segment_index=0,
            start_ms=0,
            end_ms=3000,
            text="Test dialogue.",
            words_json=json.dumps([
                {"word": "Test", "start_ms": 0, "end_ms": 1000},
                {"word": "dialogue.", "start_ms": 1100, "end_ms": 2500},
            ]),
        )
        session.add(seg)

        clip = Clip(
            id=clip_id,
            video_id=video_id,
            title="SetNull Test Clip",
            start_ms=0,
            end_ms=5000,
            duration_ms=5000,
            status="DRAFT",
        )
        session.add(clip)
        await session.commit()

        req = SubtitleGenerateRequest()
        track = await create_subtitle_track_for_clip(session, clip_id, req)
        track_id = track.id

    # Delete Transcript
    async with AsyncSessionLocal() as session:
        tx_to_delete = await session.get(Transcript, transcript_id)
        await session.delete(tx_to_delete)
        await session.commit()

    # SubtitleTrack should still exist, but transcript_id must be None
    async with AsyncSessionLocal() as session:
        track_check = await session.get(SubtitleTrack, track_id)
        assert track_check is not None
        assert track_check.transcript_id is None


# --- API Endpoint Tests ---

@pytest.mark.asyncio
async def test_subtitles_api_endpoints(async_client: AsyncClient):
    """Tests POST and GET endpoints for clip subtitles."""
    video_id = str(uuid.uuid4())
    clip_id = str(uuid.uuid4())
    transcript_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        video = Video(
            id=video_id,
            filename=f"{video_id}.mp4",
            original_filename="api_test.mp4",
            file_path=f"storage/uploads/{video_id}.mp4",
            file_size_bytes=1024,
            duration_seconds=60.0,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            status="READY",
        )
        session.add(video)

        tx = Transcript(
            id=transcript_id,
            video_id=video_id,
            model_name="tiny",
            compute_type="int8",
            device="cpu",
            language="en",
            status="COMPLETED",
            full_text="API subtitle generation test.",
            word_count=4,
            segment_count=1,
            is_active=True,
        )
        session.add(tx)

        seg = TranscriptSegment(
            id=str(uuid.uuid4()),
            transcript_id=transcript_id,
            segment_index=0,
            start_ms=1000,
            end_ms=5000,
            text="API subtitle generation test.",
            words_json=json.dumps([
                {"word": "API", "start_ms": 1000, "end_ms": 1500},
                {"word": "subtitle", "start_ms": 1600, "end_ms": 2400},
                {"word": "generation", "start_ms": 2500, "end_ms": 3600},
                {"word": "test.", "start_ms": 3700, "end_ms": 4800},
            ]),
        )
        session.add(seg)

        clip = Clip(
            id=clip_id,
            video_id=video_id,
            title="API Subtitle Test Clip",
            start_ms=0,
            end_ms=6000,
            duration_ms=6000,
            status="DRAFT",
        )
        session.add(clip)
        await session.commit()

    # 1. Generate subtitle track via POST
    gen_res = await async_client.post(
        f"/api/v1/clips/{clip_id}/subtitles/generate",
        json={"preset_name": "MODERN", "max_words_per_line": 2},
    )
    assert gen_res.status_code == 201
    gen_data = gen_res.json()
    assert gen_data["clip_id"] == clip_id
    assert gen_data["preset_name"] == "MODERN"
    assert gen_data["event_count"] == 2
    assert len(gen_data["events"]) == 2
    assert gen_data["events"][0]["text"] == "API subtitle"
    assert gen_data["events"][1]["text"] == "generation test."

    # 2. Retrieve subtitle track via GET
    get_res = await async_client.get(f"/api/v1/clips/{clip_id}/subtitles")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["id"] == gen_data["id"]
    assert get_data["event_count"] == 2

    # 3. Non-existent clip returns 404
    missing_res = await async_client.get(f"/api/v1/clips/{uuid.uuid4()}/subtitles")
    assert missing_res.status_code == 404

    # 4. ASS endpoint returns 200 OK with compiled ASS content
    ass_res = await async_client.get(f"/api/v1/clips/{clip_id}/subtitles.ass")
    assert ass_res.status_code == 200
    assert "text/x-ssa" in ass_res.headers["content-type"]
    assert "[Script Info]" in ass_res.text
    assert "[Events]" in ass_res.text


@pytest.mark.asyncio
async def test_subtitles_missing_and_incomplete_transcript(async_client: AsyncClient):
    """Verifies that missing transcripts and non-COMPLETED transcripts are rejected cleanly."""
    vid_no_tx = str(uuid.uuid4())
    clip_no_tx = str(uuid.uuid4())

    vid_proc_tx = str(uuid.uuid4())
    clip_proc_tx = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        # Video 1: No transcript at all
        video1 = Video(
            id=vid_no_tx,
            filename=f"{vid_no_tx}.mp4",
            original_filename="no_tx.mp4",
            file_path=f"storage/uploads/{vid_no_tx}.mp4",
            file_size_bytes=1024,
            duration_seconds=60.0,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            status="READY",
        )
        clip1 = Clip(
            id=clip_no_tx,
            video_id=vid_no_tx,
            title="Clip No Transcript",
            start_ms=0,
            end_ms=5000,
            duration_ms=5000,
            status="DRAFT",
        )
        session.add_all([video1, clip1])

        # Video 2: Transcript with status="PROCESSING" (incomplete)
        video2 = Video(
            id=vid_proc_tx,
            filename=f"{vid_proc_tx}.mp4",
            original_filename="proc_tx.mp4",
            file_path=f"storage/uploads/{vid_proc_tx}.mp4",
            file_size_bytes=1024,
            duration_seconds=60.0,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            fps=30.0,
            video_codec="h264",
            status="READY",
        )
        tx_incomplete = Transcript(
            id=str(uuid.uuid4()),
            video_id=vid_proc_tx,
            model_name="tiny",
            compute_type="int8",
            device="cpu",
            language="en",
            status="PROCESSING",  # Incomplete!
            full_text="Incomplete transcript",
            is_active=True,
        )
        clip2 = Clip(
            id=clip_proc_tx,
            video_id=vid_proc_tx,
            title="Clip Incomplete Transcript",
            start_ms=0,
            end_ms=5000,
            duration_ms=5000,
            status="DRAFT",
        )
        session.add_all([video2, tx_incomplete, clip2])
        await session.commit()

    # Generation on video with no transcript should fail (400 InvalidFileFormatError)
    res1 = await async_client.post(
        f"/api/v1/clips/{clip_no_tx}/subtitles/generate",
        json={"preset_name": "MODERN"},
    )
    assert res1.status_code == 400
    assert "no completed active transcript" in res1.json()["detail"].lower()

    # Generation on video with incomplete transcript should fail
    res2 = await async_client.post(
        f"/api/v1/clips/{clip_proc_tx}/subtitles/generate",
        json={"preset_name": "MODERN"},
    )
    assert res2.status_code == 400
    assert "no completed active transcript" in res2.json()["detail"].lower()

