"""ASS timestamp and centisecond timing utilities.

Advanced SubStation Alpha (ASS) format utilizes centisecond (1/100th second = 10ms)
precision for all timeline events and karaoke tags.

Documented Precision Loss:
- 1 centisecond = 10 milliseconds.
- Any timecode delta smaller than 10ms cannot be uniquely represented in ASS format.
- Timestamps are rounded to the nearest centisecond via round(ms / 10.0).
- Dialogue events with duration < 10ms (which round to start_cs == end_cs) are
  promoted to end_cs = start_cs + 1 (10ms minimum) to ensure Start < End.
"""

from typing import Tuple


def ms_to_centiseconds(milliseconds: int) -> int:
    """Converts integer milliseconds to integer centiseconds with deterministic rounding.

    Raises:
        ValueError: If milliseconds is negative.
    """
    if milliseconds < 0:
        raise ValueError(f"Timestamp cannot be negative, got {milliseconds}ms.")
    return int(round(milliseconds / 10.0))


def cs_to_ass_timestamp(total_centiseconds: int) -> str:
    """Formats integer centiseconds into the canonical ASS format 'H:MM:SS.cc'.

    Examples:
        0 -> '0:00:00.00'
        150 -> '0:00:01.50'
        366125 -> '1:01:01.25'
    """
    if total_centiseconds < 0:
        raise ValueError(f"Centiseconds cannot be negative, got {total_centiseconds}.")

    cs = total_centiseconds % 100
    total_seconds = total_centiseconds // 100
    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60

    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def ms_to_ass_timestamp(milliseconds: int) -> str:
    """Converts integer milliseconds to canonical ASS format 'H:MM:SS.cc'.

    Precision Notice:
        Values are rounded to the nearest 10ms boundary. Sub-10ms precision is lost.
    """
    cs = ms_to_centiseconds(milliseconds)
    return cs_to_ass_timestamp(cs)


def format_dialogue_interval(start_ms: int, end_ms: int) -> Tuple[int, int, str, str]:
    """Calculates valid start and end centiseconds and canonical timestamp strings for an ASS dialogue line.

    Guarantees:
    - start_cs >= 0
    - end_cs > start_cs (strictly earlier start time, minimum 1 centisecond duration)
    - Returns: (start_cs, end_cs, start_time_str, end_time_str)

    Raises:
        ValueError: If start_ms < 0 or end_ms <= start_ms.
    """
    if start_ms < 0:
        raise ValueError(f"Event start_ms cannot be negative, got {start_ms}ms.")
    if end_ms <= start_ms:
        raise ValueError(
            f"Event end_ms ({end_ms}ms) must be strictly greater than start_ms ({start_ms}ms)."
        )

    start_cs = ms_to_centiseconds(start_ms)
    end_cs = ms_to_centiseconds(end_ms)

    # Prevent zero-duration dialogue event caused by centisecond rounding loss
    if end_cs <= start_cs:
        end_cs = start_cs + 1

    start_str = cs_to_ass_timestamp(start_cs)
    end_str = cs_to_ass_timestamp(end_cs)

    return start_cs, end_cs, start_str, end_str
