# AI Agent & Highlight Detection Logic

**Project Name:** AI Video Clipper (Working Title: Clipsly)  
**Document Version:** 1.0.0  
**Status:** ARCHITECTURALLY FINALIZED (Phase 02 ADR-003 Baseline; Implementation Scheduled for Phase 10)  
**Author:** Senior Software Architect & AI Systems Engineer  

---

## 1. Purpose of this Document

This document defines the mathematical models, heuristic scoring formulas, transcript chunking rules, and optional external AI augmentation contracts for the Highlight Detection Engine in Clipsly.

The engine must autonomously scan a long-form spoken transcript (ranging from 15 to 120 minutes) and identify the most compelling, coherent, and shareable 15-to-90-second segments, while strictly respecting the **4GB VRAM ceiling of the local NVIDIA RTX 3050 Laptop GPU**.

---

## 2. Highlight Detection Philosophy & Scoring Metrics

A high-retention vertical short clip adheres to specific narrative dynamics:
1. **The Hook (First 3–5 seconds):** Must immediately arrest viewer attention through a provocative question, unexpected assertion, story opener, or acoustic emphasis.
2. **Thematic Coherence (Middle 10–50 seconds):** The segment must develop a single unified topic without requiring prior context from earlier in the video.
3. **The Payoff / Conclusion (Last 3–5 seconds):** The clip must terminate on a definitive punchline, conclusion, or natural speech cadence—never cut off mid-word or mid-sentence.

### Composite Scoring Formula:
$$\text{Score}_{\text{composite}} = 0.30 \times S_{\text{hook}} + 0.30 \times S_{\text{coherence}} + 0.25 \times S_{\text{density}} + 0.15 \times S_{\text{sentiment}}$$

Where:
- $S_{\text{hook}} \in [0, 100]$: Lexical score based on trigger phrases, rhetorical questions, and opening speech cadence.
- $S_{\text{coherence}} \in [0, 100]$: Syntactic measure of sentence completeness and topic closure.
- $S_{\text{density}} \in [0, 100]$: Pacing score measuring optimal words-per-minute ($130 \le \text{WPM} \le 175$).
- $S_{\text{sentiment}} \in [0, 100]$: Emotional inflection, vocal energy variance, and semantic valence.

---

## 3. Architecture Evaluation & Final Selection (ADR-003)

In Phase 02, three architectural approaches were evaluated:

| Approach | Technology | Hardware & VRAM Impact | Decision |
|---|---|---|---|
| **Approach A: Pure Deterministic Heuristic** | Python / Regex / Acoustic Silences | **0 MB VRAM**; $< 5\%$ CPU for $< 2\text{s}$ | **Adopted as Baseline Default** |
| **Approach B: Local Quantized 3B LLM** | Qwen2.5-3B via llama.cpp (Q4_K_M) | **~1.8GB – 2.2GB VRAM**; High OOM risk | **Rejected for v1** (VRAM unsafe) |
| **Approach C: Hybrid Heuristic + Optional API** | Heuristic Core + Optional Gemini/OpenAI Flash | **0 MB VRAM**; $< 2\text{s}$ local or 3–6s TLS call | **APPROVED ARCHITECTURE** |

### Selected Architecture: Hybrid Architecture (Approach C)
- **Baseline Engine (Default):** Runs a 100% deterministic heuristic algorithm locally on the CPU. Consumes zero GPU memory, requires zero network connectivity, costs nothing, runs in $< 2\text{ seconds}$, and guarantees zero hallucination of timestamps.
- **Optional External AI Augmentation:** If the user enters a personal API key in Settings (e.g., Google Gemini 1.5 Flash or OpenAI GPT-4o-mini), the system sends the transcript text to the API to semantically evaluate and re-rank candidate highlights. Because inference occurs in the cloud, local VRAM remains completely unburdened for NVENC video export.
- **Graceful Fallback:** If the external API call fails, times out, or the machine is offline, the system seamlessly falls back to the local heuristic scores without interrupting the user workflow.

---

## 4. Transcript Chunking & Windowing Strategy

To evaluate long transcripts without truncating thoughts:
1. **Discourse Boundary Alignment:** Transcripts are pre-segmented into sentences using punctuation boundaries (`.`, `?`, `!`) and speaker pause markers ($> 0.6\text{s}$).
2. **Sliding Candidate Window:** Windows of duration $T \in [T_{\min}, T_{\max}]$ (e.g., 30s to 60s) slide across the sentence list with a step of $T_{\text{step}} = 10\text{s}$.
3. **Boundary Snapping & Padding:** Selected highlights snap to the nearest silence boundary, adding $+0.5\text{s}$ pre-roll and $+0.5\text{s}$ post-roll padding clamped to natural speech pauses.

---

## 5. Lexical Hook Scanner Heuristics

The heuristic hook engine evaluates the first 5 seconds of each candidate window against weighted lexical patterns:

- **Provocative Questions (Weight: 1.0):** Matches sentences beginning with *"Why does nobody talk about..."*, *"Did you know that..."*, *"What happens when..."*, *"Have you ever wondered..."*.
- **Contrarian & Secret Hooks (Weight: 0.9):** Matches *"The biggest mistake..."*, *"Nobody realizes this, but..."*, *"The real reason why..."*, *"Stop doing this immediately..."*.
- **Storytelling Openers (Weight: 0.85):** Matches *"So the crazy thing was..."*, *"Back in 2020..."*, *"I never told anyone this, but..."*.
- **Statistical / Specific Revelations (Weight: 0.8):** Matches patterns containing concrete numbers and percentages within the first sentence.

---

## 6. Optional External AI Prompt Contract (When Configured)

When an external API key is configured by the user, the service submits a structured JSON prompt:

```json
{
  "system_prompt": "You are an expert viral video editor. Analyze the provided timestamped transcript and identify the top 5 most engaging, coherent short-form video highlights lasting between 30 and 60 seconds.",
  "response_format": {
    "type": "json_object",
    "schema": {
      "highlights": [
        {
          "start_ms": 145000,
          "end_ms": 182000,
          "hook_sentence": "The real secret to scaling is...",
          "score": 94,
          "reasoning": "Strong opening premise with complete standalone takeaway."
        }
      ]
    }
  }
}
```

---

## 7. Current Status & Next Steps

- **Status:** ARCHITECTURALLY FINALIZED.
- **Dependencies:** Transcription Engine (Phase 08) & Transcript Management (Phase 09).
- **Execution Target:** Implementation scheduled for **Phase 10**.
