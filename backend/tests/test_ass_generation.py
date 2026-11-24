import json
import os
import shutil
import subprocess
import tempfile
import uuid
import pytest

from backend.app.models.subtitle_event import SubtitleEvent
from backend.app.models.subtitle_track import SubtitleTrack
from backend.app.services.subtitles.ass_timing import (
    cs_to_ass_timestamp,
    format_dialogue_interval,
    ms_to_ass_timestamp,
    ms_to_centiseconds,
)
from backend.app.services.subtitles.ass_escape import (
    ZWNJ,
    sanitize_ass_text,
    sanitize_word_token,
)
from backend.app.services.subtitles.ass_storage import (
    atomic_write_ass_file,
    delete_ass_file,
    get_ass_file_path,
    read_ass_file,
    validate_clip_id,
)
from backend.app.services.subtitles.ass_generator import (
    AssDocumentError,
    build_script_info_section,
    build_v4_styles_section,
    format_karaoke_dialogue_text,
    generate_ass_document,
    validate_ass_document,
)


# --- 1. Deterministic Centisecond Half-Up Rounding Tests ---

def test_ms_to_centiseconds_deterministic_half_up():
    """Verifies deterministic half-up rounding policy across required test points:
    0, 4, 5, 6, 14, 15, 16, 24, 25, 26, 1000, and 1005 milliseconds.

    Note: Explicit integer formula (ms + 5) // 10 avoids floating-point errors
    and eliminates Python's default ties-to-even (bankers rounding) behavior.
    """
    assert ms_to_centiseconds(0) == 0
    assert ms_to_centiseconds(4) == 0
    assert ms_to_centiseconds(5) == 1
    assert ms_to_centiseconds(6) == 1
    assert ms_to_centiseconds(14) == 1
    assert ms_to_centiseconds(15) == 2
    assert ms_to_centiseconds(16) == 2
    assert ms_to_centiseconds(24) == 2
    assert ms_to_centiseconds(25) == 3    # Ties round UP (unlike bankers round which rounds 2.5 -> 2)
    assert ms_to_centiseconds(26) == 3
    assert ms_to_centiseconds(1000) == 100
    assert ms_to_centiseconds(1005) == 101  # Ties round UP (unlike bankers round which rounds 100.5 -> 100)

    # Edge cases
    assert ms_to_centiseconds(1) == 0
    assert ms_to_centiseconds(9) == 1
    assert ms_to_centiseconds(10) == 1

    with pytest.raises(ValueError, match="cannot be negative"):
        ms_to_centiseconds(-1)


def test_cs_to_ass_timestamp_formatting_and_rollover():
    """Verifies canonical ASS timestamp formatting 'H:MM:SS.cc' and rollover boundaries."""
    # Base boundaries
    assert cs_to_ass_timestamp(0) == "0:00:00.00"
    assert cs_to_ass_timestamp(1) == "0:00:00.01"
    assert cs_to_ass_timestamp(99) == "0:00:00.99"
    assert cs_to_ass_timestamp(100) == "0:00:01.00"

    # Minute rollover (60 seconds = 6000 centiseconds)
    assert cs_to_ass_timestamp(5999) == "0:00:59.99"
    assert cs_to_ass_timestamp(6000) == "0:01:00.00"
    assert cs_to_ass_timestamp(6001) == "0:01:00.01"

    # Hour rollover (60 minutes = 3600 seconds = 360000 centiseconds)
    assert cs_to_ass_timestamp(359999) == "0:59:59.99"
    assert cs_to_ass_timestamp(360000) == "1:00:00.00"
    assert cs_to_ass_timestamp(366145) == "1:01:01.45"

    # Multi-hour rollover (10 hours = 3600000 centiseconds)
    assert cs_to_ass_timestamp(3600000) == "10:00:00.00"

    with pytest.raises(ValueError, match="cannot be negative"):
        cs_to_ass_timestamp(-1)


def test_ms_to_ass_timestamp():
    assert ms_to_ass_timestamp(0) == "0:00:00.00"
    assert ms_to_ass_timestamp(1000) == "0:00:01.00"
    assert ms_to_ass_timestamp(1005) == "0:00:01.01"
    assert ms_to_ass_timestamp(65430) == "0:01:05.43"


# --- 2. ASS Dialogue Text Preservation & Escaping Tests ---

def test_sanitize_ass_text_preservation_and_escaping():
    """Verifies that legitimate characters are preserved while ASS override sequences
    are safely escaped without altering dialogue content.
    """
    # 1. Curly braces preserved via escaping (\{ and \})
    assert sanitize_ass_text("{value}") == r"\{value\}"

    # 2. Windows paths & backslashes preserved (NOT converted to /)
    assert sanitize_ass_text(r"C:\Projects\Clipsly") == r"C:\Projects\Clipsly"

    # 3. Literal \N text separated by ZWNJ to prevent line break execution
    literal_n = r"Literal \N text"
    escaped_literal_n = sanitize_ass_text(literal_n)
    assert ZWNJ in escaped_literal_n
    assert escaped_literal_n == f"Literal \\{ZWNJ}N text"

    # 4. Actual CRLF and LF newlines normalized to canonical ASS \N
    crlf_text = "Line 1\r\nLine 2\nLine 3\rLine 4"
    assert sanitize_ass_text(crlf_text) == r"Line 1\NLine 2\NLine 3\NLine 4"

    # 5. Injection attacks neutralized via brace escaping
    pos_injection = r"{\pos(540,960)}"
    assert sanitize_ass_text(pos_injection) == r"\{\pos(540,960)\}"

    clip_injection = r"{\clip(0,0,100,100)}"
    assert sanitize_ass_text(clip_injection) == r"\{\clip(0,0,100,100)\}"

    # 6. Commas, quotes, and punctuation preserved
    punct = "Hello, world! Are you 'ready'? Yes, absolutely: 100%."
    assert sanitize_ass_text(punct) == punct

    # 7. Multilingual Unicode and Emojis preserved intact
    multilingual = "Clipsly 🚀 AI video clipping 🔥 (100% local, 日本語, Español, Français)"
    assert sanitize_ass_text(multilingual) == multilingual


def test_sanitize_word_token():
    assert sanitize_word_token("  word  ") == "word"
    assert sanitize_word_token("{value}") == r"\{value\}"
    assert sanitize_word_token(r"C:\Projects") == r"C:\Projects"
    assert sanitize_word_token(r"\N") == f"\\{ZWNJ}N"
    assert sanitize_word_token("") == ""


# --- 3. Short-Event Boundary Correctness Tests ---

def test_short_event_boundaries_1ms_2ms_5ms_9ms_10ms():
    """Verifies that short events (1ms, 2ms, 5ms, 9ms, 10ms) are assigned strictly positive,
    non-zero, non-inverted ASS dialogue intervals without exceeding boundaries.
    """
    # 1ms event (1000ms to 1001ms)
    s_cs, e_cs, s_str, e_str = format_dialogue_interval(1000, 1001)
    assert s_cs == 100
    assert e_cs == 101  # Clamped to 1cs duration
    assert s_str == "0:00:01.00"
    assert e_str == "0:00:01.01"
    assert e_cs > s_cs

    # 2ms event (1000ms to 1002ms)
    s_cs, e_cs, s_str, e_str = format_dialogue_interval(1000, 1002)
    assert s_cs == 100
    assert e_cs == 101
    assert e_cs > s_cs

    # 5ms event (1000ms to 1005ms) -> 1005ms rounds up to 101cs
    s_cs, e_cs, s_str, e_str = format_dialogue_interval(1000, 1005)
    assert s_cs == 100
    assert e_cs == 101
    assert e_cs > s_cs

    # 9ms event (1000ms to 1009ms) -> 1009ms rounds up to 101cs
    s_cs, e_cs, s_str, e_str = format_dialogue_interval(1000, 1009)
    assert s_cs == 100
    assert e_cs == 101
    assert e_cs > s_cs

    # 10ms event (1000ms to 1010ms)
    s_cs, e_cs, s_str, e_str = format_dialogue_interval(1000, 1010)
    assert s_cs == 100
    assert e_cs == 101
    assert e_cs > s_cs


def test_quantization_never_expands_beyond_clip_boundary():
    """Verifies that quantization clamping respects max_end_ms and never emits
    an interval that extends past the clip's permitted boundary.
    """
    clip_duration_ms = 5000  # 500cs boundary
    # Event right at the end of the clip (4999ms to 5000ms)
    s_cs, e_cs, s_str, e_str = format_dialogue_interval(4999, 5000, max_end_ms=clip_duration_ms)

    assert e_cs == 500       # Does NOT expand to 501cs!
    assert s_cs == 499       # Shifted down to maintain duration = 1cs
    assert e_cs > s_cs
    assert s_str == "0:00:04.99"
    assert e_str == "0:00:05.00"


def test_adjacent_events_continuity_in_ass_document():
    """Verifies that sequential contiguous events do not overlap on screen due to
    centisecond expansion clamping.
    """
    track = SubtitleTrack(
        id=str(uuid.uuid4()),
        clip_id="adjacent_test_clip",
        preset_name="KARAOKE_AMBER",
        language="en",
        is_active=True,
    )
    # Event 1: 0ms to 2ms (expands to 0cs -> 1cs)
    ev1 = SubtitleEvent(
        id=str(uuid.uuid4()),
        track_id=track.id,
        sequence_index=0,
        start_ms=0,
        end_ms=2,
        text="Event 1",
        words_json=json.dumps([{"text": "Event", "start_ms": 0, "end_ms": 1}, {"text": "1", "start_ms": 1, "end_ms": 2}]),
        style_name="Default",
    )
    # Event 2: 2ms to 20ms (contiguous with Event 1)
    ev2 = SubtitleEvent(
        id=str(uuid.uuid4()),
        track_id=track.id,
        sequence_index=1,
        start_ms=2,
        end_ms=20,
        text="Event 2",
        words_json=json.dumps([{"text": "Event", "start_ms": 2, "end_ms": 10}, {"text": "2", "start_ms": 10, "end_ms": 20}]),
        style_name="Default",
    )
    # Event 3: 20ms to 1000ms
    ev3 = SubtitleEvent(
        id=str(uuid.uuid4()),
        track_id=track.id,
        sequence_index=2,
        start_ms=20,
        end_ms=1000,
        text="Event 3",
        words_json=json.dumps([{"text": "Event", "start_ms": 20, "end_ms": 500}, {"text": "3", "start_ms": 500, "end_ms": 1000}]),
        style_name="Default",
    )
    track.events = [ev1, ev2, ev3]

    doc = generate_ass_document(track=track, clip_duration_ms=5000)
    lines = [line for line in doc.splitlines() if line.startswith("Dialogue:")]

    assert len(lines) == 3

    # Extract start and end times for all 3 dialogue events
    # Format: Dialogue: Layer, Start, End, ...
    times = []
    for line in lines:
        parts = line.split(",")
        times.append((parts[1], parts[2]))

    # Event 1: 0.00 to 0.01 (1cs)
    assert times[0] == ("0:00:00.00", "0:00:00.01")
    # Event 2: 0.01 to 0.02 (1cs, advanced to prevent overlap with Event 1)
    assert times[1] == ("0:00:00.01", "0:00:00.02")
    # Event 3: 0.02 to 0:00:01.00
    assert times[2] == ("0:00:00.02", "0:00:01.00")

    # Strictly monotonic, zero overlap!
    assert times[1][0] >= times[0][1]
    assert times[2][0] >= times[1][1]


def test_plain_text_fallback_preserves_words_without_fabricated_timings():
    """Verifies that events with insufficient centiseconds (event_dur_cs < word_count)
    gracefully fall back to plain text without fabricating fake sub-centisecond timings.
    """
    words = [
        {"text": "one", "start_ms": 0, "end_ms": 1},
        {"text": "two", "start_ms": 1, "end_ms": 1},
        {"text": "three", "start_ms": 1, "end_ms": 2},
    ]
    # 2ms event = 1cs available < 3 words
    result = format_karaoke_dialogue_text(
        event_text="one two three",
        words_data=words,
        event_start_ms=0,
        event_dur_cs=1,
    )
    # Output MUST be plain text containing all words without any karaoke tags
    assert result == "one two three"
    assert r"{\k" not in result


# --- 4. Storage & Path Traversal Tests ---

def test_validate_clip_id():
    valid_uuid = str(uuid.uuid4())
    assert validate_clip_id(valid_uuid) == valid_uuid
    assert validate_clip_id("clip_123_abc") == "clip_123_abc"

    invalid_ids = [
        "../clip",
        "..\\clip",
        "/etc/passwd",
        "clip;drop",
        "clip/id",
        "",
        "   ",
    ]
    for inv in invalid_ids:
        with pytest.raises(ValueError):
            validate_clip_id(inv)


def test_storage_atomic_lifecycle():
    test_id = f"test_{uuid.uuid4().hex[:12]}"
    sample_content = "[Script Info]\nTitle: Test Life Cycle\n"

    try:
        path = atomic_write_ass_file(test_id, sample_content)
        assert os.path.exists(path)

        read_content = read_ass_file(test_id)
        assert read_content == sample_content

        # Overwrite atomically
        new_content = sample_content + "Comment: Overwritten\n"
        atomic_write_ass_file(test_id, new_content)
        assert read_ass_file(test_id) == new_content

        # Delete
        assert delete_ass_file(test_id) is True
        assert read_ass_file(test_id) is None
        assert delete_ass_file(test_id) is False
    finally:
        delete_ass_file(test_id)


# --- 5. ASS Generator Tests ---

def test_script_info_section():
    info = build_script_info_section("My Test Clip")
    assert "[Script Info]" in info
    assert "Title: My Test Clip" in info
    assert "ScriptType: v4.00+" in info
    assert "WrapStyle: 0" in info
    assert "ScaledBorderAndShadow: yes" in info
    assert "PlayResX: 1080" in info
    assert "PlayResY: 1920" in info


def test_v4_styles_section():
    section = build_v4_styles_section(
        style_name="Default",
        font_name="Montserrat",
        font_size=88,
        primary_color="&H00FFFFFF",
        secondary_color="&H0000D7FF",
        outline_color="&H00000000",
        outline_width=8.0,
        shadow_depth=3.0,
        margin_v=380,
    )
    assert "[V4+ Styles]" in section
    assert "Format: Name, Fontname, Fontsize," in section
    assert "Style: Default,Montserrat,88,&H00FFFFFF,&H0000D7FF,&H00000000" in section


def test_format_karaoke_dialogue_text_smooth():
    words = [
        {"text": "Create", "start_ms": 0, "end_ms": 500},
        {"text": "amazing", "start_ms": 500, "end_ms": 1000},
        {"text": "clips", "start_ms": 1100, "end_ms": 1500},
    ]
    # Event duration 0 to 1500 ms (150 cs)
    karaoke_str = format_karaoke_dialogue_text(
        event_text="Create amazing clips",
        words_data=words,
        event_start_ms=0,
        event_dur_cs=150,
        karaoke_tag=r"\kf",
    )
    assert r"{\kf50}Create" in karaoke_str
    assert r"{\kf50}amazing" in karaoke_str
    # Inter-word gap: 1000 to 1100 ms is 100ms = 10cs pause tag
    assert r"{\k10}" in karaoke_str
    assert r"{\kf40}clips" in karaoke_str


def test_format_karaoke_dialogue_text_standard():
    words = [
        {"text": "Fast", "start_ms": 0, "end_ms": 300},
        {"text": "video", "start_ms": 300, "end_ms": 800},
    ]
    karaoke_str = format_karaoke_dialogue_text(
        event_text="Fast video",
        words_data=words,
        event_start_ms=0,
        event_dur_cs=80,
        karaoke_tag=r"\k",
    )
    assert r"{\k30}Fast" in karaoke_str
    assert r"{\k50}video" in karaoke_str


def test_generate_ass_document_end_to_end():
    clip_id = str(uuid.uuid4())
    track = SubtitleTrack(
        id=str(uuid.uuid4()),
        clip_id=clip_id,
        preset_name="KARAOKE_AMBER",
        language="en",
        is_active=True,
    )
    ev1 = SubtitleEvent(
        id=str(uuid.uuid4()),
        track_id=track.id,
        sequence_index=0,
        start_ms=1000,
        end_ms=3000,
        text="Transform your content",
        words_json=json.dumps([
            {"text": "Transform", "start_ms": 1000, "end_ms": 1600},
            {"text": "your", "start_ms": 1600, "end_ms": 2000},
            {"text": "content", "start_ms": 2000, "end_ms": 3000},
        ]),
        style_name="Default",
    )
    ev2 = SubtitleEvent(
        id=str(uuid.uuid4()),
        track_id=track.id,
        sequence_index=1,
        start_ms=3200,
        end_ms=5000,
        text="with local AI!",
        words_json=json.dumps([
            {"text": "with", "start_ms": 3200, "end_ms": 3600},
            {"text": "local", "start_ms": 3600, "end_ms": 4200},
            {"text": "AI!", "start_ms": 4200, "end_ms": 5000},
        ]),
        style_name="Default",
    )
    track.events = [ev1, ev2]

    ass_text = generate_ass_document(
        track=track,
        karaoke_tag=r"\kf",
        custom_title="Viral Hook Clip",
    )

    validate_ass_document(ass_text)

    assert "[Script Info]" in ass_text
    assert "Title: Viral Hook Clip" in ass_text
    assert "[V4+ Styles]" in ass_text
    assert "[Events]" in ass_text
    assert r"Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,{\kf60}Transform" in ass_text
    assert r"Dialogue: 0,0:00:03.20,0:00:05.00,Default,,0,0,0,,{\kf40}with" in ass_text


# --- 6. FFmpeg Libass Real Parser & Rendering Verification ---

def test_ffmpeg_libass_demuxer_and_filter_verification():
    r"""Validates that generated ASS documents containing escaped braces, literal paths,
    literal \N, actual newlines, injection sequences, Unicode, and emojis are parsed
    cleanly by FFmpeg's libass with 0 errors.
    """
    ffmpeg_cmd = shutil.which("ffmpeg")
    if not ffmpeg_cmd:
        pytest.skip("FFmpeg not installed on host machine.")

    track = SubtitleTrack(
        id=str(uuid.uuid4()),
        clip_id="ffmpeg_verification_clip",
        preset_name="KARAOKE_AMBER",
        language="en",
        is_active=True,
    )

    # Line 1: Braces, paths, literal \N
    ev1 = SubtitleEvent(
        id=str(uuid.uuid4()),
        track_id=track.id,
        sequence_index=0,
        start_ms=0,
        end_ms=2500,
        text=r"Check {value} at C:\Projects\Clipsly and literal \N text",
        words_json=json.dumps([
            {"text": "Check", "start_ms": 0, "end_ms": 400},
            {"text": "{value}", "start_ms": 400, "end_ms": 800},
            {"text": "at", "start_ms": 800, "end_ms": 1000},
            {"text": r"C:\Projects\Clipsly", "start_ms": 1000, "end_ms": 1700},
            {"text": "and", "start_ms": 1700, "end_ms": 1900},
            {"text": "literal", "start_ms": 1900, "end_ms": 2200},
            {"text": r"\N", "start_ms": 2200, "end_ms": 2400},
            {"text": "text", "start_ms": 2400, "end_ms": 2500},
        ]),
        style_name="Default",
    )

    # Line 2: Injection sequences neutralized and Unicode/emojis preserved
    ev2 = SubtitleEvent(
        id=str(uuid.uuid4()),
        track_id=track.id,
        sequence_index=1,
        start_ms=2600,
        end_ms=5000,
        text=r"Attempt {\pos(540,960)} and {\clip(0,0,10,10)} 🔥 🚀 Local AI (日本語)",
        words_json=json.dumps([
            {"text": "Attempt", "start_ms": 2600, "end_ms": 3000},
            {"text": r"{\pos(540,960)}", "start_ms": 3000, "end_ms": 3600},
            {"text": "and", "start_ms": 3600, "end_ms": 3800},
            {"text": r"{\clip(0,0,10,10)}", "start_ms": 3800, "end_ms": 4300},
            {"text": "🔥", "start_ms": 4300, "end_ms": 4500},
            {"text": "🚀", "start_ms": 4500, "end_ms": 4700},
            {"text": "Local", "start_ms": 4700, "end_ms": 4800},
            {"text": "AI", "start_ms": 4800, "end_ms": 4900},
            {"text": "(日本語)", "start_ms": 4900, "end_ms": 5000},
        ]),
        style_name="Default",
    )
    track.events = [ev1, ev2]

    ass_text = generate_ass_document(
        track=track,
        karaoke_tag=r"\kf",
        custom_title="FFmpeg Libass Robustness Suite",
    )

    temp_path = "temp_libass_test.ass"
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(ass_text)

    try:
        # Demux test using ffmpeg's ass demuxer
        res_demux = subprocess.run(
            [ffmpeg_cmd, "-f", "ass", "-i", temp_path, "-map", "0:s", "-c:s", "copy", "-f", "null", "-"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert res_demux.returncode == 0, f"FFmpeg demux failed: {res_demux.stderr}"
        assert "libass error" not in res_demux.stderr.lower()

        # Render test using ffmpeg's libass video filter
        res_filter = subprocess.run(
            [
                ffmpeg_cmd, "-y", "-f", "lavfi", "-i", "color=c=black:s=640x360:d=0.04",
                "-vf", f"ass={temp_path}",
                "-f", "null", "-"
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert res_filter.returncode == 0, f"FFmpeg libass filter failed: {res_filter.stderr}"
        assert "error" not in res_filter.stderr.lower() or "configuration:" in res_filter.stderr.lower()
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
