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


# --- 1. Timing Engine Tests ---

def test_ms_to_centiseconds():
    assert ms_to_centiseconds(0) == 0
    assert ms_to_centiseconds(10) == 1
    assert ms_to_centiseconds(14) == 1
    assert ms_to_centiseconds(16) == 2
    assert ms_to_centiseconds(1000) == 100
    assert ms_to_centiseconds(65432) == 6543

    with pytest.raises(ValueError, match="cannot be negative"):
        ms_to_centiseconds(-1)


def test_cs_to_ass_timestamp():
    assert cs_to_ass_timestamp(0) == "0:00:00.00"
    assert cs_to_ass_timestamp(1) == "0:00:00.01"
    assert cs_to_ass_timestamp(99) == "0:00:00.99"
    assert cs_to_ass_timestamp(100) == "0:00:01.00"
    assert cs_to_ass_timestamp(6000) == "0:01:00.00"
    assert cs_to_ass_timestamp(360000) == "1:00:00.00"
    assert cs_to_ass_timestamp(366145) == "1:01:01.45"
    # Multi-hour rollover
    assert cs_to_ass_timestamp(3600000) == "10:00:00.00"


def test_ms_to_ass_timestamp():
    assert ms_to_ass_timestamp(0) == "0:00:00.00"
    assert ms_to_ass_timestamp(1250) == "0:00:01.25"
    assert ms_to_ass_timestamp(65430) == "0:01:05.43"


def test_format_dialogue_interval():
    # Normal interval
    s_cs, e_cs, start_ts, end_ts = format_dialogue_interval(1000, 2500)
    assert start_ts == "0:00:01.00"
    assert end_ts == "0:00:02.50"
    assert s_cs == 100
    assert e_cs == 250
    assert s_cs < e_cs

    # Pathological short interval (2ms)
    s_cs, e_cs, start_ts, end_ts = format_dialogue_interval(1000, 1002)
    assert s_cs == 100
    assert e_cs == 101  # Clamped to start_cs + 1
    assert start_ts == "0:00:01.00"
    assert end_ts == "0:00:01.01"
    assert s_cs < e_cs

    # Zero or inverted interval raises ValueError
    with pytest.raises(ValueError, match="strictly greater than"):
        format_dialogue_interval(500, 500)

    with pytest.raises(ValueError, match="strictly greater than"):
        format_dialogue_interval(2000, 1000)


# --- 2. Text Escaping & Sanitization Tests ---

def test_sanitize_ass_text():
    # Curly braces sanitized to fullwidth
    assert sanitize_ass_text("{test}") == "｛test｝"

    # Backslashes converted to forward slashes
    assert sanitize_ass_text("C:\\Windows\\System32") == "C:/Windows/System32"

    # Newlines normalized to \N
    assert sanitize_ass_text("Line 1\r\nLine 2\nLine 3") == "Line 1\\NLine 2\\NLine 3"

    # Commas, quotes, exclamation marks preserved
    raw = "Hello, world! Are you 'ready'? Yes, absolutely."
    assert sanitize_ass_text(raw) == raw

    # Unicode and emojis preserved
    unicode_text = "Clipsly 🚀 AI video clipping 🔥 (100% local, 日本語)"
    assert sanitize_ass_text(unicode_text) == unicode_text


def test_sanitize_injection_attack():
    # Malicious ASS override tags are neutralized
    malicious = "{\\an5\\pos(540,960)\\c&H0000FF&\\b1}Hacked Subtitle!"
    sanitized = sanitize_ass_text(malicious)
    assert sanitized.startswith("｛/an5/pos(540,960)/c&H0000FF&/b1｝")
    assert "{" not in sanitized
    assert "\\" not in sanitized


def test_sanitize_word_token():
    assert sanitize_word_token("  word  ") == "word"
    assert sanitize_word_token("{word}") == "｛word｝"
    assert sanitize_word_token("") == ""


# --- 3. Storage & Path Traversal Tests ---

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


# --- 4. ASS Generator Tests ---

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
    assert "{\\kf50}Create" in karaoke_str
    assert "{\\kf50}amazing" in karaoke_str
    # Inter-word gap: 1000 to 1100 ms is 100ms = 10cs pause tag
    assert "{\\k10}" in karaoke_str
    assert "{\\kf40}clips" in karaoke_str


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
    assert "{\\k30}Fast" in karaoke_str
    assert "{\\k50}video" in karaoke_str


def test_format_karaoke_pathological_short_duration():
    # 3 words inside a 2ms event -> available cs = 1 < 3 words
    words = [
        {"text": "one", "start_ms": 0, "end_ms": 1},
        {"text": "two", "start_ms": 1, "end_ms": 1},
        {"text": "three", "start_ms": 1, "end_ms": 2},
    ]
    # Should safely degrade to plain text without fake timing
    karaoke_str = format_karaoke_dialogue_text(
        event_text="one two three",
        words_data=words,
        event_start_ms=0,
        event_dur_cs=1,
    )
    assert karaoke_str == "one two three"
    assert "{\\k" not in karaoke_str


def test_format_karaoke_empty_words():
    karaoke_str = format_karaoke_dialogue_text(
        event_text="Plain fallback caption",
        words_data=[],
        event_start_ms=0,
        event_dur_cs=100,
    )
    assert karaoke_str == "Plain fallback caption"


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

    # Validate output
    validate_ass_document(ass_text)

    assert "[Script Info]" in ass_text
    assert "Title: Viral Hook Clip" in ass_text
    assert "[V4+ Styles]" in ass_text
    assert "[Events]" in ass_text
    assert "Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,{\\kf60}Transform" in ass_text
    assert "Dialogue: 0,0:00:03.20,0:00:05.00,Default,,0,0,0,,{\\kf40}with" in ass_text


def test_validate_ass_document_catches_malformed():
    with pytest.raises(AssDocumentError, match="empty"):
        validate_ass_document("")

    with pytest.raises(AssDocumentError, match="missing required structural marker"):
        validate_ass_document("[Script Info]\nTitle: Test\n[Events]\nFormat: ...\n")


# --- 5. Libass / FFmpeg Real Parser Verification ---

def test_ffmpeg_libass_parses_generated_ass():
    """Verifies that generated ASS documents are strictly compliant with libass
    by running ffmpeg's internal ASS parser.
    """
    ffmpeg_cmd = shutil.which("ffmpeg")
    if not ffmpeg_cmd:
        pytest.skip("FFmpeg not installed on host machine.")

    track = SubtitleTrack(
        id=str(uuid.uuid4()),
        clip_id="ffmpeg_test_clip",
        preset_name="KARAOKE_AMBER",
        language="en",
        is_active=True,
    )
    ev1 = SubtitleEvent(
        id=str(uuid.uuid4()),
        track_id=track.id,
        sequence_index=0,
        start_ms=0,
        end_ms=2500,
        text="Local-first AI video editing 🚀",
        words_json=json.dumps([
            {"text": "Local-first", "start_ms": 0, "end_ms": 800},
            {"text": "AI", "start_ms": 800, "end_ms": 1200},
            {"text": "video", "start_ms": 1200, "end_ms": 1800},
            {"text": "editing", "start_ms": 1800, "end_ms": 2300},
            {"text": "🚀", "start_ms": 2300, "end_ms": 2500},
        ]),
        style_name="Default",
    )
    ev2 = SubtitleEvent(
        id=str(uuid.uuid4()),
        track_id=track.id,
        sequence_index=1,
        start_ms=2600,
        end_ms=4500,
        text="Privacy preserved! 100% on device.",
        words_json=json.dumps([
            {"text": "Privacy", "start_ms": 2600, "end_ms": 3200},
            {"text": "preserved!", "start_ms": 3200, "end_ms": 3800},
            {"text": "100%", "start_ms": 3800, "end_ms": 4100},
            {"text": "on", "start_ms": 4100, "end_ms": 4250},
            {"text": "device.", "start_ms": 4250, "end_ms": 4500},
        ]),
        style_name="Default",
    )
    track.events = [ev1, ev2]

    ass_text = generate_ass_document(
        track=track,
        karaoke_tag=r"\kf",
        custom_title="FFmpeg Libass Compliance Test",
    )

    with tempfile.NamedTemporaryFile(suffix=".ass", mode="w", encoding="utf-8", delete=False) as f:
        f.write(ass_text)
        temp_path = f.name

    try:
        # Ask ffmpeg to demux the .ass file and copy subtitle stream to null
        # FFmpeg uses libass demuxer when available
        res = subprocess.run(
            [ffmpeg_cmd, "-f", "ass", "-i", temp_path, "-map", "0:s", "-c:s", "copy", "-f", "null", "-"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert res.returncode == 0, f"FFmpeg failed to demux ASS file: {res.stderr}"
        # Ensure no libass parsing errors in stderr
        assert "libass error" not in res.stderr.lower()
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
