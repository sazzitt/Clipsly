"""Clipsly Phase 16: Highlight Scoring Engine.

Computes explainable, deterministic heuristic scores for candidate windows across
four core dimensions:
1. Hook Strength (30%)
2. Coherence (30%)
3. Information Density (25%)
4. Text-Based Sentiment Signal (15%)
"""
from typing import Any, Dict, List, Tuple
from backend.app.services.highlight_detection.schemas import (
    CandidateWindow,
    DetectionConfig,
    ScoringBreakdown,
)
from backend.app.services.highlight_detection.feature_extractor import extract_window_features


def score_candidate_window(
    window: CandidateWindow,
    config: DetectionConfig,
) -> ScoringBreakdown:
    """Evaluates and scores a candidate window deterministically."""
    features = extract_window_features(
        text=window.text,
        duration_seconds=window.duration_seconds,
        words=window.words,
    )

    hook_score, hook_reasons, hook_warnings = _calculate_hook_score(features["hook"])
    coherence_score, coherence_reasons, coherence_warnings = _calculate_coherence_score(features["coherence"])
    density_score, density_reasons, density_warnings = _calculate_density_score(features["density"])
    sentiment_score, sentiment_reasons, sentiment_warnings = _calculate_sentiment_score(features["sentiment"])

    # Weighted Composite Score
    w_hook = config.hook_weight
    w_coh = config.coherence_weight
    w_den = config.density_weight
    w_sent = config.sentiment_weight

    raw_composite = (
        (hook_score * w_hook)
        + (coherence_score * w_coh)
        + (density_score * w_den)
        + (sentiment_score * w_sent)
    )
    composite_score = round(max(0.0, min(100.0, raw_composite)), 1)

    # Compile warnings
    all_warnings = hook_warnings + coherence_warnings + density_warnings + sentiment_warnings

    # Compile explanation
    explanation = _build_explanation(
        hook_reasons=hook_reasons,
        coherence_reasons=coherence_reasons,
        density_reasons=density_reasons,
        sentiment_reasons=sentiment_reasons,
        composite_score=composite_score,
        features=features,
    )

    # Compile summary
    summary = _build_summary(features["sentences"], features["opening_sentence"])

    metadata = {
        "scoring_version": "v1",
        "wpm": features["density"]["wpm"],
        "filler_count": features["density"]["filler_count"],
        "filler_ratio": features["density"]["filler_ratio"],
        "pause_seconds": features["density"]["total_pause_seconds"],
        "component_weights": {
            "hook": w_hook,
            "coherence": w_coh,
            "density": w_den,
            "sentiment": w_sent,
        },
    }

    return ScoringBreakdown(
        hook_score=round(hook_score, 1),
        coherence_score=round(coherence_score, 1),
        density_score=round(density_score, 1),
        sentiment_score=round(sentiment_score, 1),
        composite_score=composite_score,
        hook_sentence=features["hook"]["hook_sentence"],
        summary=summary,
        category=features["category"],
        explanation=explanation,
        warnings=all_warnings,
        metadata=metadata,
    )


def _calculate_hook_score(hook: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
    """Scores opening hook strength (0.0 to 100.0)."""
    score = 50.0
    reasons = []
    warnings = []

    if hook.get("is_question"):
        score += 25.0
        reasons.append("engaging question opening")

    if hook.get("is_provocative"):
        score += 30.0
        reasons.append("provocative or high-curiosity assertion")

    if hook.get("has_direct_address"):
        score += 15.0
        reasons.append("direct audience address")

    if hook.get("is_imperative"):
        score += 12.0
        reasons.append("action-oriented imperative verb")

    penalty = hook.get("length_penalty", 0.0)
    if penalty > 0:
        score -= (penalty * 30.0)
        if hook.get("word_count", 0) < 4:
            warnings.append("hook_too_brief")
        elif hook.get("word_count", 0) > 28:
            warnings.append("hook_run_on_sentence")

    return max(0.0, min(100.0, score)), reasons, warnings


def _calculate_coherence_score(coh: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
    """Scores structural coherence and standalone thought completeness (0.0 to 100.0)."""
    score = 75.0
    reasons = []
    warnings = []

    if coh.get("ends_cleanly"):
        score += 15.0
        reasons.append("complete sentence termination")
    else:
        score -= 20.0

    if coh.get("starts_mid_clause"):
        score -= 25.0
        warnings.append("starts_on_conjunction")

    if coh.get("ends_incomplete"):
        score -= 25.0
        warnings.append("ends_abruptly_incomplete")

    if coh.get("sentence_count", 0) >= 1 and coh.get("has_terminal_punct"):
        score += 10.0
        reasons.append("self-contained narrative flow")

    return max(0.0, min(100.0, score)), reasons, warnings


def _calculate_density_score(density: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
    """Scores information delivery pacing, lexical variety, and filler ratio (0.0 to 100.0)."""
    wpm = density.get("wpm", 0.0)
    filler_ratio = density.get("filler_ratio", 0.0)
    long_pauses = density.get("long_pause_count", 0)
    ttr = density.get("ttr", 1.0)

    score = 80.0
    reasons = []
    warnings = []

    # WPM pacing evaluation
    if 130.0 <= wpm <= 180.0:
        score += 10.0
        reasons.append(f"optimal spoken delivery pacing ({wpm:.0f} WPM)")
    elif 110.0 <= wpm < 130.0 or 180.0 < wpm <= 210.0:
        score += 5.0
    elif wpm < 90.0:
        score -= 20.0
        warnings.append("low_speech_pacing")
    elif wpm > 220.0:
        score -= 15.0
        warnings.append("rapid_speech_pacing")

    # Filler words penalty
    if filler_ratio <= 0.02:
        score += 10.0
        reasons.append("clean dialogue with minimal fillers")
    elif filler_ratio > 0.06:
        penalty = min(25.0, (filler_ratio - 0.05) * 200.0)
        score -= penalty
        warnings.append("high_filler_word_ratio")

    # Long pauses penalty
    if long_pauses > 0:
        penalty = min(20.0, long_pauses * 6.0)
        score -= penalty
        if long_pauses >= 2:
            warnings.append("contains_long_pauses")

    # Lexical variety
    if ttr >= 0.70:
        score += 5.0
    elif ttr < 0.45:
        score -= 15.0
        warnings.append("repetitive_vocabulary")

    return max(0.0, min(100.0, score)), reasons, warnings


def _calculate_sentiment_score(sent: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
    """Scores text-based emotional, emphasis, and conviction signals (0.0 to 100.0)."""
    emotive = sent.get("emotive_count", 0)
    conviction = sent.get("conviction_count", 0)
    exclamations = sent.get("exclamation_count", 0)
    humor = sent.get("humor_count", 0)

    score = 50.0
    reasons = []
    warnings = []

    if emotive > 0:
        bonus = min(25.0, emotive * 8.0)
        score += bonus
        reasons.append("emotive and descriptive vocabulary")

    if conviction > 0:
        bonus = min(20.0, conviction * 7.0)
        score += bonus
        reasons.append("strong conviction markers")

    if exclamations > 0:
        bonus = min(15.0, exclamations * 7.5)
        score += bonus

    if humor > 0:
        bonus = min(15.0, humor * 8.0)
        score += bonus
        reasons.append("humor or lighthearted tone")

    return max(0.0, min(100.0, score)), reasons, warnings


def _build_explanation(
    hook_reasons: List[str],
    coherence_reasons: List[str],
    density_reasons: List[str],
    sentiment_reasons: List[str],
    composite_score: float,
    features: Dict[str, Any],
) -> str:
    """Builds a human-readable, transparent explanation for why the candidate was selected."""
    parts = []
    if hook_reasons:
        parts.append(f"Opens with a {', '.join(hook_reasons)}")
    else:
        parts.append("Opens with a steady conversational introduction")

    coh_and_dens = []
    if coherence_reasons:
        coh_and_dens.append(", ".join(coherence_reasons))
    if density_reasons:
        coh_and_dens.append(", ".join(density_reasons))

    if coh_and_dens:
        parts.append(f"Demonstrates {'; '.join(coh_and_dens)}.")

    if sentiment_reasons:
        parts.append(f"Supported by {', '.join(sentiment_reasons)}.")

    return " ".join(parts)


def _build_summary(sentences: List[str], opening_sentence: str) -> str:
    """Generates an editorial summary snippet from the candidate's core thoughts."""
    if len(sentences) <= 2:
        return " ".join(sentences)
    # Take first and last sentence
    return f"{sentences[0]} ... {sentences[-1]}"
