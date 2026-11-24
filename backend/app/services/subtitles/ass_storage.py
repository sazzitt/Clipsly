"""Atomic filesystem storage and containment utilities for compiled ASS subtitle files.

Enforces:
1. UUID-safe file naming and strict path containment within storage/subtitles/.
2. Path traversal attack prevention (rejects '..', slashes, control chars).
3. Two-phase atomic file replacement via temporary files (write -> flush -> os.replace).
4. Automatic scratch cleanup on write failure.
"""

import os
from pathlib import Path
import re
import uuid
from backend.app.core.config import settings

# Strict validation pattern for clip IDs: UUID or alphanumeric with hyphens
SAFE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def validate_clip_id(clip_id: str) -> str:
    """Validates that a clip_id string is safe for filesystem path construction.

    Raises:
        ValueError: If clip_id contains path traversal patterns, slashes, or invalid characters.
    """
    if not clip_id or not isinstance(clip_id, str):
        raise ValueError("clip_id must be a non-empty string.")

    cleaned = clip_id.strip()
    if not SAFE_ID_PATTERN.match(cleaned):
        raise ValueError(
            f"Invalid clip_id '{clip_id}': Contains unsafe characters or path traversal sequence."
        )

    return cleaned


def get_ass_file_path(clip_id: str) -> Path:
    """Returns the validated absolute Path for a clip's compiled ASS subtitle file.

    Raises:
        ValueError: If path escapes the configured subtitles directory.
    """
    safe_id = validate_clip_id(clip_id)
    subtitles_dir = settings.SUBTITLES_DIR.resolve()
    target_path = (subtitles_dir / f"{safe_id}.ass").resolve()

    try:
        target_path.relative_to(subtitles_dir)
    except ValueError:
        raise ValueError(f"Path containment violation: '{clip_id}' escapes subtitles directory.")

    return target_path


def atomic_write_ass_file(clip_id: str, content: str) -> Path:
    """Atomically writes UTF-8 encoded ASS document content to storage/subtitles/{clip_id}.ass.

    Writes to a unique temporary file first, flushes to disk, and replaces destination atomically.
    Scratch files are unlinked in finally block if replacement fails.

    Returns:
        The destination Path of the compiled .ass file.
    """
    if not content or not content.strip():
        raise ValueError("Cannot write empty or whitespace-only ASS content.")

    safe_id = validate_clip_id(clip_id)
    dest_path = get_ass_file_path(safe_id)
    subtitles_dir = dest_path.parent
    subtitles_dir.mkdir(parents=True, exist_ok=True)

    temp_path = subtitles_dir / f"{safe_id}.tmp_{uuid.uuid4().hex}.ass"

    try:
        with open(temp_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        # Atomic replacement
        os.replace(temp_path, dest_path)
        return dest_path
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def read_ass_file(clip_id: str) -> Optional[str]:
    """Reads and returns the UTF-8 content of a compiled ASS file for a clip,
    or None if the file does not exist on disk.
    """
    try:
        path = get_ass_file_path(clip_id)
        if not path.is_file():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (ValueError, OSError):
        return None


def delete_ass_file(clip_id: str) -> bool:
    """Safely unlinks a clip's compiled ASS file if present on disk."""
    try:
        path = get_ass_file_path(clip_id)
        if path.is_file():
            path.unlink()
            return True
    except (ValueError, OSError):
        pass
    return False
