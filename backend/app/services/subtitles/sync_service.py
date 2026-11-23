import json
import logging
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.clip import Clip
from backend.app.models.subtitle_event import SubtitleEvent
from backend.app.models.subtitle_track import SubtitleTrack
from backend.app.models.transcript import Transcript
from backend.app.models.transcript_segment import TranscriptSegment
from backend.app.services.subtitles.schemas import (
    CaptionEventData,
    NormalizedWord,
    SubtitleGenerateRequest,
)
from backend.app.services.subtitles.timing_engine import (
    chunk_words_into_events,
    interpolate_missing_word_timestamps,
)
from backend.app.services.subtitles.validators import (
    validate_caption_events,
    validate_clip_timing,
    validate_normalized_words,
)

logger = logging.getLogger("clipsly.subtitles.sync_service")


def extract_words_from_segment(seg: TranscriptSegment) -> List[NormalizedWord]:
    """Extracts words from a transcript segment, falling back to interpolation if words_json is missing."""
    words: List[NormalizedWord] = []
    has_valid_json = False

    if seg.words_json and seg.words_json.strip():
        try:
            raw_data = json.loads(seg.words_json)
            if isinstance(raw_data, list) and len(raw_data) > 0:
                for item in raw_data:
                    w_text = item.get("word", "").strip()
                    if not w_text:
                        continue
                    w_start = int(round(item.get("start_ms", 0)))
                    w_end = int(round(item.get("end_ms", 0)))
                    w_prob = item.get("prob")
                    if w_end > w_start:
                        words.append(
                            NormalizedWord(
                                text=w_text,
                                start_ms=w_start,
                                end_ms=w_end,
                                confidence=float(w_prob) if w_prob is not None else None,
                            )
                        )
                if words:
                    has_valid_json = True
        except Exception as e:
            logger.warning("Failed parsing words_json for segment %s: %s", seg.id, e)

    # Fallback: If words_json was empty or yielded no words, interpolate from segment text
    if not has_valid_json and seg.text and seg.text.strip():
        words = interpolate_missing_word_timestamps(
            segment_text=seg.text,
            start_ms=seg.start_ms,
            end_ms=seg.end_ms,
            confidence=seg.avg_confidence,
        )

    return words


def sync_transcript_words_to_clip(
    segments: List[TranscriptSegment],
    clip_start_ms: int,
    clip_end_ms: int,
) -> List[NormalizedWord]:
    """Extracts, filters, clips, and remaps transcript words into clip-relative coordinates."""
    validate_clip_timing(clip_start_ms, clip_end_ms)
    clip_duration_ms = clip_end_ms - clip_start_ms

    raw_words: List[NormalizedWord] = []
    # Sort segments sequentially
    sorted_segments = sorted(segments, key=lambda s: (s.start_ms, s.segment_index))

    for seg in sorted_segments:
        # Segment intersection check with clip window
        if seg.end_ms <= clip_start_ms or seg.start_ms >= clip_end_ms:
            continue

        seg_words = extract_words_from_segment(seg)
        raw_words.extend(seg_words)

    # Intersect individual words with clip boundaries and remap to relative coordinates
    relative_words: List[NormalizedWord] = []
    for w in raw_words:
        # Ignore words strictly outside clip boundaries
        if w.end_ms <= clip_start_ms or w.start_ms >= clip_end_ms:
            continue

        # Convert to clip-relative coordinates: t_rel = t_abs - clip_start_ms
        rel_start = max(0, w.start_ms - clip_start_ms)
        rel_end = min(clip_duration_ms, w.end_ms - clip_start_ms)

        # Boundary straddling clamp: ensure rel_end > rel_start
        if rel_end <= rel_start:
            if rel_start < clip_duration_ms:
                rel_end = min(clip_duration_ms, rel_start + 1)
            else:
                rel_start = max(0, clip_duration_ms - 1)
                rel_end = clip_duration_ms

        relative_words.append(
            NormalizedWord(
                text=w.text,
                start_ms=rel_start,
                end_ms=rel_end,
                confidence=w.confidence,
            )
        )

    # Deterministic sort by start_ms, end_ms
    relative_words.sort(key=lambda w: (w.start_ms, w.end_ms))

    # Resolve artificial overlaps between consecutive words
    for i in range(len(relative_words) - 1):
        curr_w = relative_words[i]
        next_w = relative_words[i + 1]
        if curr_w.end_ms > next_w.start_ms:
            # Clamp current word end to next word start
            clamped_end = next_w.start_ms
            if clamped_end > curr_w.start_ms:
                curr_w.end_ms = clamped_end
            else:
                # If next word starts at or before curr start, shift next word start
                next_w.start_ms = min(clip_duration_ms - 1, curr_w.end_ms)
                if next_w.end_ms <= next_w.start_ms:
                    next_w.end_ms = min(clip_duration_ms, next_w.start_ms + 1)

    # Final validation on normalized words
    validate_normalized_words(relative_words, clip_duration_ms)
    return relative_words


def generate_caption_events_for_clip(
    segments: List[TranscriptSegment],
    clip_start_ms: int,
    clip_end_ms: int,
    max_words_per_line: int = 4,
    max_chars_per_line: int = 28,
) -> List[CaptionEventData]:
    """Transforms raw transcript segments into clean, bounded, clip-relative caption events."""
    clip_duration_ms = clip_end_ms - clip_start_ms
    relative_words = sync_transcript_words_to_clip(
        segments=segments,
        clip_start_ms=clip_start_ms,
        clip_end_ms=clip_end_ms,
    )

    if not relative_words:
        return []

    events = chunk_words_into_events(
        words=relative_words,
        max_words_per_line=max_words_per_line,
        max_chars_per_line=max_chars_per_line,
    )

    validate_caption_events(events, clip_duration_ms)
    return events


async def create_subtitle_track_for_clip(
    session: AsyncSession,
    clip_id: str,
    request: SubtitleGenerateRequest,
) -> SubtitleTrack:
    """Asynchronously generates a SubtitleTrack and SubtitleEvents from active transcript and persists to DB."""
    # 1. Fetch clip
    stmt_clip = select(Clip).where(Clip.id == clip_id)
    clip_res = await session.execute(stmt_clip)
    clip = clip_res.scalar_one_or_none()
    if not clip:
        raise ValueError(f"Clip '{clip_id}' not found.")

    # 2. Fetch active transcript for video
    stmt_tx = (
        select(Transcript)
        .options(selectinload(Transcript.segments))
        .where(
            Transcript.video_id == clip.video_id,
            Transcript.is_active == True,
            Transcript.status == "COMPLETED",
        )
    )
    tx_res = await session.execute(stmt_tx)
    transcript = tx_res.scalar_one_or_none()
    if not transcript:
        raise ValueError(f"No completed active transcript found for video '{clip.video_id}'.")

    # 3. Generate clip-relative caption events
    events_data = generate_caption_events_for_clip(
        segments=transcript.segments,
        clip_start_ms=clip.start_ms,
        clip_end_ms=clip.end_ms,
        max_words_per_line=request.max_words_per_line,
        max_chars_per_line=request.max_chars_per_line,
    )

    # 4. Deactivate any existing active subtitle tracks for this clip
    stmt_deactivate = (
        update(SubtitleTrack)
        .where(SubtitleTrack.clip_id == clip_id, SubtitleTrack.is_active == True)
        .values(is_active=False)
    )
    await session.execute(stmt_deactivate)

    # 5. Create new SubtitleTrack
    track_id = str(uuid.uuid4())
    track = SubtitleTrack(
        id=track_id,
        clip_id=clip_id,
        transcript_id=transcript.id,
        preset_name=request.preset_name,
        is_enabled=True,
        is_active=True,
        language=transcript.language or "en",
        ass_file_path=None,
        compile_status="DRAFT",
        custom_style_overrides=None,
    )
    session.add(track)

    # 6. Create SubtitleEvents
    db_events: List[SubtitleEvent] = []
    for ev in events_data:
        words_dicts = [w.model_dump() for w in ev.words]
        db_event = SubtitleEvent(
            id=str(uuid.uuid4()),
            track_id=track_id,
            sequence_index=ev.sequence_index,
            start_ms=ev.start_ms,
            end_ms=ev.end_ms,
            text=ev.text,
            words_json=json.dumps(words_dicts, ensure_ascii=False),
            style_name=ev.style_name,
            is_modified=False,
        )
        session.add(db_event)
        db_events.append(db_event)

    await session.commit()

    # Reload track with events for caller
    stmt_load = (
        select(SubtitleTrack)
        .options(selectinload(SubtitleTrack.events))
        .where(SubtitleTrack.id == track_id)
    )
    res = await session.execute(stmt_load)
    return res.scalar_one()


async def get_active_subtitle_track_for_clip(
    session: AsyncSession,
    clip_id: str,
) -> Optional[SubtitleTrack]:
    """Retrieves the active subtitle track and its events for a given clip."""
    stmt = (
        select(SubtitleTrack)
        .options(selectinload(SubtitleTrack.events))
        .where(SubtitleTrack.clip_id == clip_id, SubtitleTrack.is_active == True)
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()
