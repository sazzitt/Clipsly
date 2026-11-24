"""ASS timestamp and centisecond timing utilities.

Advanced SubStation Alpha (ASS) format utilizes centisecond (1/100th second = 10ms)
precision for all timeline events and karaoke tags.

Deterministic Half-Up Rounding Policy:
- 1 centisecond = 10 milliseconds.
- Non-negative millisecond values are converted using explicit half-up rounding:
    centiseconds = (milliseconds + 5) // 10
  Ties (ending in .5ms / 5ms after division) are deterministically rounded UP to the
  next integer centisecond.
- This explicit integer formulation avoids floating-point inaccuracies and avoids
  Python's built-in round() ties-to-even (bankers rounding) behavior.
- Examples:
    0ms -> 0cs
    4ms -> 0cs
    5ms -> 1cs
    6ms -> 1cs
    14ms -> 1cs
    15ms -> 2cs
    16ms -> 2cs
    24ms -> 2cs
    25ms -> 3cs
    26ms -> 3cs
    1000ms -> 100cs
    1005ms -> 101cs

Boundary and Monotonicity Guarantees:
- start_cs >= 0
- end_cs > start_cs (strictly earlier start time, minimum 1 centisecond duration)
- Dialogue events with duration < 10ms that round to start_cs == end_cs (e.g. 1ms-9ms)
  are guaranteed at least 1 centisecond duration (end_cs = start_cs + 1).
- When a clip upper bound (max_end_ms) is provided, quantization will never expand
  the event past that boundary: if end_cs reaches max_end_cs, start_cs is shifted
  backwards (start_cs = max(0, end_cs - 1)).
"""

from typing import Optional, Tuple


def ms_to_centiseconds(milliseconds: int) -> int:
    """Converts integer milliseconds to integer centiseconds using deterministic half-up rounding.

    Formula:
        (milliseconds + 5) // 10

    Raises:
        ValueError: If milliseconds is negative.
    """
    if milliseconds < 0:
        raise ValueError(f"Timestamp cannot be negative, got {milliseconds}ms.")
    return (milliseconds + 5) // 10


def cs_to_ass_timestamp(total_centiseconds: int) -> str:
    """Formats integer centiseconds into canonical ASS format 'H:MM:SS.cc'.

    Examples:
        0 -> '0:00:00.00'
        150 -> '0:00:01.50'
        366125 -> '1:01:01.25'
        3600000 -> '10:00:00.00'
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
    """Converts integer milliseconds to canonical ASS format 'H:MM:SS.cc' via half-up rounding."""
    cs = ms_to_centiseconds(milliseconds)
    return cs_to_ass_timestamp(cs)


def format_dialogue_interval(
    start_ms: int,
    end_ms: int,
    max_end_ms: Optional[int] = None,
) -> Tuple[int, int, str, str]:
    """Calculates valid start and end centiseconds and canonical timestamp strings for an ASS dialogue line.

    Guarantees:
    - start_cs >= 0
    - end_cs > start_cs (strictly positive duration >= 1 centisecond)
    - If bounded by max_end_ms, end_cs never exceeds ms_to_centiseconds(max_end_ms)
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
    max_end_cs = ms_to_centiseconds(max_end_ms) if max_end_ms is not None else None

    # Guarantee minimum 1 centisecond duration
    if end_cs <= start_cs:
        if max_end_cs is not None and start_cs >= max_end_cs:
            # At or past upper boundary: clamp end_cs to max_end_cs, move start_cs down
            end_cs = max_end_cs
            start_cs = max(0, end_cs - 1)
        else:
            end_cs = start_cs + 1

    # Ensure quantization never silently expands beyond permitted boundary
    if max_end_cs is not None and end_cs > max_end_cs:
        end_cs = max_end_cs
        if start_cs >= end_cs:
            start_cs = max(0, end_cs - 1)

    # In case max_end_cs == 0
    if end_cs <= start_cs:
        end_cs = start_cs + 1

    start_str = cs_to_ass_timestamp(start_cs)
    end_str = cs_to_ass_timestamp(end_cs)

    return start_cs, end_cs, start_str, end_str
