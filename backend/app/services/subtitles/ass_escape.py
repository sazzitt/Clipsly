"""Safe ASS text escaping and Unicode sanitization utilities.

Guarantees:
1. Prevents arbitrary ASS override-tag injection (e.g., {\\pos}, {\\clip}, {\\alpha})
   by sanitizing literal curly braces in spoken dialogue to full-width unicode braces (｛ and ｝).
2. Converts newlines and carriage returns to the standard ASS line-break tag (\\N).
3. Sanitizes literal backslashes to forward slashes (/) to prevent unintended escape sequences.
4. Preserves commas, punctuation, unicode accents, CJK/Arabic/Cyrillic scripts, and emoji.
"""

import re


def sanitize_ass_text(text: str) -> str:
    """Sanitizes raw transcript or subtitle text for safe inclusion in ASS dialogue events.

    Rules:
    - Literal curly braces '{' and '}' are sanitized to full-width unicode braces '｛' (U+FF5B)
      and '｝' (U+FF5D). This neutralizes any ASS override-tag injection attempts while visually
      preserving the bracket glyph in rendered video.
    - Literal backslashes are sanitized to '/' to prevent accidental control codes (e.g., \\k, \\c).
    - Newline sequences (\\r\\n, \\r, \\n) are normalized to the explicit ASS line break '\\N'.
    - Commas are safely preserved: since Text is the 10th (last) field in ASS Dialogue lines,
      commas in text do not trigger field splitting.
    - All Unicode text, accents, international scripts, and emoji are preserved unmodified.
    """
    if not text:
        return ""

    # 1. Normalize line endings to ASS hard break \N
    sanitized = text.replace("\r\n", r"\N").replace("\r", r"\N").replace("\n", r"\N")

    # 2. Prevent override-tag injection by converting literal braces to full-width unicode braces
    sanitized = sanitized.replace("{", "\uff5b").replace("}", "\uff5d")

    # 3. Sanitize lone backslashes that are not part of our explicit \N line breaks
    # Replace any backslash not immediately followed by 'N' with '/'
    sanitized = re.sub(r"\\(?!N)", "/", sanitized)

    return sanitized


def sanitize_word_token(word: str) -> str:
    """Sanitizes an individual word token for karaoke tag formatting.

    Preserves attached punctuation (e.g., 'hello,' or 'world!') while neutralizing
    any characters that could break ASS tag formatting.
    """
    if not word:
        return ""

    sanitized = word.strip()
    if not sanitized:
        return ""

    # Sanitize braces in individual tokens
    sanitized = sanitized.replace("{", "\uff5b").replace("}", "\uff5d")

    # Sanitize backslashes in words
    sanitized = sanitized.replace("\\", "/")

    return sanitized
