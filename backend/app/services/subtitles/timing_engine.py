import re
from typing import List, Optional
from backend.app.services.subtitles.schemas import CaptionEventData, NormalizedWord


TERMINAL_PUNCTUATION = (".", "?", "!", "...", "—", ":")


def interpolate_missing_word_timestamps(
    segment_text: str,
    start_ms: int,
    end_ms: int,
    confidence: Optional[float] = None,
) -> List[NormalizedWord]:
    """Interpolates word-level timestamps when words_json is missing or empty.

    Guarantees:
    1. Timestamps remain strictly within [start_ms, end_ms].
    2. Sum of allocated word durations equals segment duration exactly.
    3. Monotonic ordering with zero artificial overlaps (start_{i+1} = end_i).
    4. Duration-safe allocation: does not inflate short segments beyond segment duration.
    5. Preserves all punctuation and words.
    """
    if not segment_text or not segment_text.strip():
        return []

    duration_ms = end_ms - start_ms
    if duration_ms <= 0:
        return []

    tokens = segment_text.strip().split()
    if not tokens:
        return []

    k = len(tokens)

    # Edge case: If duration_ms is smaller than token count, group tokens so every word has >= 1ms
    if duration_ms < k:
        grouped_tokens: List[str] = []
        tokens_per_group = (k + duration_ms - 1) // duration_ms
        for i in range(0, k, tokens_per_group):
            grouped_tokens.append(" ".join(tokens[i : i + tokens_per_group]))
        tokens = grouped_tokens[:duration_ms]
        k = len(tokens)

    # Character length-weighted proportional duration allocation
    char_lengths = [max(1, len(tok)) for tok in tokens]
    total_chars = sum(char_lengths)

    # Base allocation with floor to ensure integer millisecond precision
    base_durations = [max(1, (duration_ms * length) // total_chars) for length in char_lengths]
    allocated_sum = sum(base_durations)

    # If base allocation exceeded total duration (due to max(1, ...)), decrement largest
    if allocated_sum > duration_ms:
        excess = allocated_sum - duration_ms
        for idx in sorted(range(k), key=lambda i: base_durations[i], reverse=True):
            if excess <= 0:
                break
            can_reduce = base_durations[idx] - 1
            reduction = min(can_reduce, excess)
            base_durations[idx] -= reduction
            excess -= reduction

    # If base allocation left a remainder, distribute across longest tokens
    allocated_sum = sum(base_durations)
    remainder = duration_ms - allocated_sum
    if remainder > 0:
        sorted_indices = sorted(range(k), key=lambda i: char_lengths[i], reverse=True)
        for i in range(remainder):
            idx = sorted_indices[i % k]
            base_durations[idx] += 1

    # Build normalized word objects with contiguous timestamps
    words: List[NormalizedWord] = []
    current_time = start_ms
    for i, tok in enumerate(tokens):
        word_dur = base_durations[i]
        w_start = current_time
        # Final token snaps exactly to end_ms to eliminate floating remainder drift
        w_end = end_ms if i == k - 1 else w_start + word_dur
        if w_end <= w_start:
            w_end = w_start + 1

        words.append(
            NormalizedWord(
                text=tok,
                start_ms=w_start,
                end_ms=w_end,
                confidence=confidence,
            )
        )
        current_time = w_end

    return words


def chunk_words_into_events(
    words: List[NormalizedWord],
    max_words_per_line: int = 4,
    max_chars_per_line: int = 28,
    min_pause_ms: int = 350,
) -> List[CaptionEventData]:
    """Deterministically groups word tokens into readable caption events.

    Rules:
    - Splits on word limit (max_words_per_line).
    - Splits on character limit (max_chars_per_line).
    - Splits on natural sentence-ending punctuation (., ?, !, etc.).
    - Splits on speech pauses >= min_pause_ms.
    - Preserves deterministic sequence ordering.
    - Never creates empty events.
    """
    if not words:
        return []

    events: List[CaptionEventData] = []
    current_chunk: List[NormalizedWord] = []
    current_char_count = 0

    def finalize_chunk() -> None:
        nonlocal current_chunk, current_char_count
        if not current_chunk:
            return

        seq_idx = len(events)
        event_start = current_chunk[0].start_ms
        event_end = current_chunk[-1].end_ms
        # Ensure event_end > event_start
        if event_end <= event_start:
            event_end = event_start + 1

        full_text = " ".join(w.text for w in current_chunk)
        events.append(
            CaptionEventData(
                sequence_index=seq_idx,
                start_ms=event_start,
                end_ms=event_end,
                text=full_text,
                words=list(current_chunk),
                style_name="Default",
                is_modified=False,
            )
        )
        current_chunk = []
        current_char_count = 0

    for i, word in enumerate(words):
        if not current_chunk:
            current_chunk.append(word)
            current_char_count = len(word.text)
            # If single word has terminal punctuation and there are more words, finalize
            if any(word.text.endswith(p) for p in TERMINAL_PUNCTUATION) and i < len(words) - 1:
                finalize_chunk()
            continue

        prev_word = current_chunk[-1]

        # Condition 1: Speech pause of at least min_pause_ms
        pause_duration = word.start_ms - prev_word.end_ms
        has_pause = pause_duration >= min_pause_ms

        # Condition 2: Previous word ended with terminal punctuation
        has_terminal_punct = any(prev_word.text.endswith(p) for p in TERMINAL_PUNCTUATION)

        # Condition 3: Word count limit reached
        reached_word_limit = len(current_chunk) >= max_words_per_line

        # Condition 4: Character limit would be exceeded
        projected_chars = current_char_count + 1 + len(word.text)
        exceeds_char_limit = projected_chars > max_chars_per_line

        if has_pause or has_terminal_punct or reached_word_limit or exceeds_char_limit:
            finalize_chunk()

        current_chunk.append(word)
        current_char_count += (1 + len(word.text)) if current_char_count > 0 else len(word.text)

        # Check if the newly added word ends a sentence and more words follow
        if any(word.text.endswith(p) for p in TERMINAL_PUNCTUATION) and i < len(words) - 1:
            finalize_chunk()

    # Finalize remaining words
    if current_chunk:
        finalize_chunk()

    return events
