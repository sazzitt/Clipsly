"""Clipsly Phase 16: Highlight Feature Extractor.

Extracts explainable linguistic, structural, and temporal features from transcript
candidate windows:
1. Hook features (opening sentence, interrogatives, provocative assertions, direct address).
2. Coherence features (sentence boundaries, dangling conjunctions, complete thoughts).
3. Information density features (WPM pacing, filler ratio, pause gaps, lexical variety).
4. Text-based sentiment signals (emotive vocabulary, excitement markers, conviction).
"""
import re
from typing import Any, Dict, List, Optional, Set, Tuple

# Pre-compiled regex patterns for deterministic matching
INTERROGATIVE_HOOKS = re.compile(
    r"^(why|how|what|who|when|where|can you|did you|have you|do you|is there|are you|what if|could you)\b",
    re.IGNORECASE,
)

PROVOCATIVE_HOOKS = re.compile(
    r"\b(biggest mistake|secret to|nobody talks about|nobody understands|nobody knows|truth about|stop doing|here is why|the problem with|"
    r"one thing that|number one reason|what happens when|never ever|single biggest|game changer|most people don'?t)\b",
    re.IGNORECASE,
)

DIRECT_ADDRESS = re.compile(r"\b(you|your|everyone|look|listen|watch|notice)\b", re.IGNORECASE)

IMPERATIVE_VERBS = re.compile(r"^(stop|listen|look|remember|think|avoid|watch|never|always|learn|check)\b", re.IGNORECASE)

DANGLING_CONJUNCTIONS = re.compile(r"^(and|but|so|because|or|then|like|which means|so that)\b", re.IGNORECASE)

TRAILING_INCOMPLETE = re.compile(r"\b(and|or|but|with|at|for|to|of|the|a|an|in|on|because|so|that)$", re.IGNORECASE)

FILLER_WORDS: Set[str] = {
    "um", "uh", "you know", "like", "basically", "actually", "literally",
    "sort of", "kind of", "i mean", "right", "yeah", "hmm"
}

EMOTIVE_WORDS: Set[str] = {
    "incredible", "insane", "amazing", "devastating", "brilliant", "disaster",
    "genius", "horrible", "mind-blowing", "shocking", "massive", "game-changer",
    "breakthrough", "worst", "best", "legendary", "unbelievable", "crazy",
    "terrifying", "unreal", "extraordinary", "miracle", "catastrophe"
}

CONVICTION_WORDS: Set[str] = {
    "absolutely", "definitely", "never", "always", "guarantee", "crucial",
    "essential", "undeniable", "certainly", "100%", "proven", "fundamental"
}

HUMOR_WORDS: Set[str] = {
    "hilarious", "laughing", "joke", "funny", "ridiculous", "absurd", "ironic"
}

STORY_STARTERS: Set[str] = {
    "when i was", "one day", "years ago", "i remember", "i used to", "in the past",
    "first time", "back when", "story time"
}


def extract_window_features(
    text: str,
    duration_seconds: float,
    words: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Extracts linguistic, structural, and temporal features from text and word timestamps."""
    cleaned_text = text.strip()
    sentences = _split_into_sentences(cleaned_text)
    opening_sentence = sentences[0] if sentences else cleaned_text
    
    # Tokenize words for density and filler calculations
    raw_tokens = [w.strip().lower() for w in re.findall(r"\b\w+(?:'\w+)?\b", cleaned_text)]
    total_tokens = len(raw_tokens)
    
    # 1. Hook Features
    hook_data = _analyze_hook(opening_sentence, cleaned_text)
    
    # 2. Coherence Features
    coherence_data = _analyze_coherence(opening_sentence, cleaned_text, sentences)
    
    # 3. Information Density Features
    density_data = _analyze_density(raw_tokens, total_tokens, duration_seconds, words)
    
    # 4. Text-Based Sentiment Features
    sentiment_data = _analyze_sentiment(cleaned_text, raw_tokens)
    
    # 5. Narrative / Category Classification
    category = _classify_category(opening_sentence, cleaned_text, hook_data, sentiment_data)
    
    return {
        "text": cleaned_text,
        "sentences": sentences,
        "opening_sentence": opening_sentence,
        "total_words": total_tokens,
        "duration_seconds": duration_seconds,
        "hook": hook_data,
        "coherence": coherence_data,
        "density": density_data,
        "sentiment": sentiment_data,
        "category": category,
    }


def _split_into_sentences(text: str) -> List[str]:
    """Splits text into sentences based on punctuation, preserving punctuation."""
    raw = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in raw if s.strip()]


def _analyze_hook(opening_sentence: str, full_text: str) -> Dict[str, Any]:
    """Evaluates hook potential of the candidate opening."""
    clean_open = opening_sentence.strip()
    words_open = clean_open.split()
    first_5_words = " ".join(words_open[:5]) if words_open else ""
    
    is_question = clean_open.endswith("?") or bool(INTERROGATIVE_HOOKS.search(first_5_words))
    is_provocative = bool(PROVOCATIVE_HOOKS.search(clean_open))
    has_direct_address = bool(DIRECT_ADDRESS.search(first_5_words))
    is_imperative = bool(IMPERATIVE_VERBS.search(first_5_words))
    
    length_penalty = 0.0
    if len(words_open) < 4:
        length_penalty = 0.3  # Too short to be a substantive hook
    elif len(words_open) > 28:
        length_penalty = 0.2  # Run-on opening sentence
        
    return {
        "hook_sentence": clean_open,
        "is_question": is_question,
        "is_provocative": is_provocative,
        "has_direct_address": has_direct_address,
        "is_imperative": is_imperative,
        "length_penalty": length_penalty,
        "word_count": len(words_open),
    }


def _analyze_coherence(
    opening_sentence: str,
    full_text: str,
    sentences: List[str]
) -> Dict[str, Any]:
    """Evaluates completeness, start/end boundaries, and grammatical independence."""
    starts_mid_clause = bool(DANGLING_CONJUNCTIONS.search(opening_sentence.strip()))
    
    clean_end = full_text.strip()
    ends_cleanly = clean_end.endswith((".", "!", "?"))
    ends_incomplete = bool(TRAILING_INCOMPLETE.search(clean_end.rstrip(".!?,")))
    
    has_terminal_punct = any(s.endswith((".", "!", "?")) for s in sentences)
    sentence_count = len(sentences)
    
    return {
        "starts_mid_clause": starts_mid_clause,
        "ends_cleanly": ends_cleanly,
        "ends_incomplete": ends_incomplete,
        "sentence_count": sentence_count,
        "has_terminal_punct": has_terminal_punct,
    }


def _analyze_density(
    tokens: List[str],
    total_tokens: int,
    duration_seconds: float,
    words: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Calculates words per minute (WPM), filler word ratio, and pause duration gaps."""
    wpm = (total_tokens / duration_seconds) * 60.0 if duration_seconds > 0 else 0.0
    
    # Filler word count
    filler_count = 0
    i = 0
    while i < len(tokens):
        # Check two-word fillers first
        if i < len(tokens) - 1:
            two_word = f"{tokens[i]} {tokens[i+1]}"
            if two_word in FILLER_WORDS:
                filler_count += 2
                i += 2
                continue
        if tokens[i] in FILLER_WORDS:
            filler_count += 1
        i += 1
        
    filler_ratio = (filler_count / total_tokens) if total_tokens > 0 else 0.0
    
    # Lexical diversity (Type-Token Ratio for content words)
    content_tokens = [t for t in tokens if len(t) > 3 and t not in FILLER_WORDS]
    unique_content = set(content_tokens)
    ttr = (len(unique_content) / len(content_tokens)) if content_tokens else 1.0
    
    # Pause analysis if word timestamps are present
    long_pause_count = 0
    max_pause_seconds = 0.0
    total_pause_seconds = 0.0
    
    if words and len(words) > 1:
        for j in range(len(words) - 1):
            w_curr_end = words[j].get("end_ms", 0)
            w_next_start = words[j+1].get("start_ms", 0)
            if w_next_start > w_curr_end:
                gap_s = (w_next_start - w_curr_end) / 1000.0
                total_pause_seconds += gap_s
                if gap_s > max_pause_seconds:
                    max_pause_seconds = gap_s
                if gap_s >= 1.5:
                    long_pause_count += 1
                    
    return {
        "wpm": round(wpm, 1),
        "filler_count": filler_count,
        "filler_ratio": round(filler_ratio, 3),
        "ttr": round(ttr, 3),
        "long_pause_count": long_pause_count,
        "max_pause_seconds": round(max_pause_seconds, 2),
        "total_pause_seconds": round(total_pause_seconds, 2),
    }


def _analyze_sentiment(text: str, tokens: List[str]) -> Dict[str, Any]:
    """Identifies textual indicators of sentiment, excitement, and emphasis."""
    exclamation_count = text.count("!")
    
    emotive_count = sum(1 for t in tokens if t in EMOTIVE_WORDS)
    conviction_count = sum(1 for t in tokens if t in CONVICTION_WORDS)
    humor_count = sum(1 for t in tokens if t in HUMOR_WORDS)
    
    return {
        "exclamation_count": exclamation_count,
        "emotive_count": emotive_count,
        "conviction_count": conviction_count,
        "humor_count": humor_count,
        "total_signal_words": emotive_count + conviction_count + humor_count,
    }


def _classify_category(
    opening_sentence: str,
    full_text: str,
    hook_data: Dict[str, Any],
    sentiment_data: Dict[str, Any]
) -> str:
    """Categorizes highlight into Insight, Story, Question, Punchline, or Discussion."""
    lower_open = opening_sentence.lower()
    lower_full = full_text.lower()
    
    if hook_data.get("is_question"):
        return "Question"
        
    if any(starter in lower_open or starter in lower_full for starter in STORY_STARTERS):
        return "Story"
        
    if sentiment_data.get("humor_count", 0) > 0 or (sentiment_data.get("exclamation_count", 0) > 1 and len(full_text.split()) < 35):
        return "Punchline"
        
    if hook_data.get("is_provocative") or sentiment_data.get("conviction_count", 0) > 1:
        return "Insight"
        
    return "Discussion"
