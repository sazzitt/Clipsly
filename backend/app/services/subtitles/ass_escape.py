"""Safe ASS text escaping and Unicode preservation utilities.

Advanced SubStation Alpha (ASS) v4.00+ Text Preservation & Escaping Architecture:
1. Curly Braces '{' and '}':
   - In ASS dialogue, any unescaped '{' marks the opening of an override tag block.
     Plain text inside '{...}' is treated as comment/unrecognized override codes and
     is completely suppressed from display by libass.
   - Escaping literal braces as '\\{' and '\\}' instructs libass to render the curly
     braces literally while strictly preventing override block execution (e.g. {\\pos}, {\\clip}).
2. Newlines vs Literal '\\N' Sequences:
   - Genuine newline characters (\\r\\n, \\r, \\n) represent intentional subtitle line breaks
     and are normalized to the canonical ASS hard-break tag '\\N'.
   - Literal text containing '\\N', '\\n', or '\\h' (e.g. discussing code or regex) is preserved
     on the same line by inserting a zero-width non-joiner (\\u200c) between the backslash and the
     character ('\\' + ZWNJ + 'N'). This renders '\\N' visibly on a single line without triggering a line break.
3. Literal Backslashes:
   - Literal backslashes in Windows paths (e.g. 'C:\\Projects\\Clipsly') or ordinary text are
     preserved unmodified. They are NOT converted to forward slashes.
4. Commas, Multilingual Characters & Emojis:
   - In ASS v4.00+ Dialogue lines, the 'Text' field is the 10th and final field
     ('Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text').
     Therefore, commas in dialogue text never cause field splitting and are preserved intact.
   - Accents, CJK, Cyrillic, Arabic scripts, symbols, and emojis are preserved in standard UTF-8.
"""

import re

# Zero-Width Non-Joiner (U+200C) used to prevent ASS control code interpretation
# without altering visible character glyphs or line layout.
ZWNJ = "\u200c"


def sanitize_ass_text(text: str) -> str:
    """Sanitizes dialogue text for safe inclusion in ASS Dialogue events.

    Rules:
    - Normalizes actual newlines (CRLF, CR, LF) to ASS line-break tag '\\N'.
    - Protects literal '\\N', '\\n', and '\\h' from triggering formatting breaks by separating with ZWNJ.
    - Escapes literal '{' and '}' to '\\{' and '\\}' to display brackets without executing override tags.
    - Preserves literal backslashes (e.g. Windows file paths) without altering spoken content.
    - Preserves commas, Unicode text, accents, international scripts, and emoji unmodified.
    """
    if not text:
        return ""

    # 1. Temporarily isolate genuine newline characters (CRLF, CR, LF)
    masked = text.replace("\r\n", "\x00NEWLINE\x00")
    masked = masked.replace("\r", "\x00NEWLINE\x00")
    masked = masked.replace("\n", "\x00NEWLINE\x00")

    # 2. Defend literal ASS control sequences (\N, \n, \h) so they render as literal characters
    # instead of executing line breaks or hard spacing
    masked = re.sub(r"\\([Nnh])", lambda m: "\\" + ZWNJ + m.group(1), masked)

    # 3. Escape curly braces so user text (e.g. '{value}' or '{\pos(540,960)}') cannot
    # trigger ASS override tags while visibly preserving the braces
    masked = masked.replace("{", r"\{").replace("}", r"\}")

    # 4. Restore genuine newlines as canonical ASS line breaks (\N)
    sanitized = masked.replace("\x00NEWLINE\x00", r"\N")

    return sanitized


def sanitize_word_token(word: str) -> str:
    """Sanitizes an individual word token for karaoke tag formatting.

    Preserves attached punctuation and legitimate word characters while ensuring
    braces and backslash control sequences cannot break ASS tag formatting.
    """
    if not word:
        return ""

    token = word.strip()
    if not token:
        return ""

    # Protect literal \N, \n, \h in single word tokens
    token = re.sub(r"\\([Nnh])", lambda m: "\\" + ZWNJ + m.group(1), token)

    # Escape braces so word tokens like '{value}' render visibly without breaking karaoke tags
    token = token.replace("{", r"\{").replace("}", r"\}")

    return token
