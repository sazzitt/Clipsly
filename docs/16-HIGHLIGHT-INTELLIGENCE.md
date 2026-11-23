# Clipsly Phase 16 — AI Highlight Detection & Clip Intelligence Engine

## 1. Executive Summary

Clipsly Phase 16 implements an explainable, CPU-first, local AI highlight detection and clip intelligence engine. The engine transforms continuous Faster-Whisper speech transcripts into ranked, candidate short-form video clips (15–30s, 30–60s, 60–90s, and custom duration presets up to 180s) optimized for vertical publishing (YouTube Shorts, TikTok, Instagram Reels) and long-form narrative extraction.

In strict compliance with **ADR-002 (Sequential Execution & Resource Isolation)** and local-first hardware constraints (AMD Ryzen 7 7435HS, RTX 3050 4GB VRAM), the highlight engine runs purely on CPU text intelligence using mathematical heuristics and deterministic linguistic analysis. It loads **zero weights into GPU VRAM**, leaving the RTX 3050 free for Faster-Whisper transcription and NVENC video rendering.

---

## 2. Architectural Design

```
+-----------------------------------------------------------------------------------+
|                           PHASE 16 ARCHITECTURE PIPELINE                          |
+-----------------------------------------------------------------------------------+
|  1. Completed Transcript & Word Timestamps (from Faster-Whisper & Silero VAD)    |
|                                       v                                           |
|  2. Candidate Window Generator (candidate_generator.py)                           |
|     - Sliding segment window accumulation across duration presets (15-90s)        |
|     - Word-level timestamp trimming: aligns boundaries, trims pause silence        |
|     - Strict zero mid-word cuts                                                   |
|                                       v                                           |
|  3. Linguistic Feature Extractor (feature_extractor.py)                           |
|     - Hook detection (questions, provocative assertions, direct address)          |
|     - Coherence detection (terminal punctuation, dangling conjunctions)           |
|     - Density metrics (WPM pacing, filler ratio, pause penalties, TTR)            |
|     - Text sentiment (emotive words, conviction markers, exclamation, humor)      |
|                                       v                                           |
|  4. Deterministic Scoring Engine (scoring_engine.py)                              |
|     - Normalized 0-100 component scores across 4 dimensions                       |
|     - Composite Viral Score: 30% Hook + 30% Flow + 25% Density + 15% Energy       |
|     - Natural-language explanation builder + automatic editorial summary snippet  |
|                                       v                                           |
|  5. Non-Maximum Suppression (deduplication.py)                                    |
|     - Greedy temporal NMS using Intersection over Minimum Duration (IoM >= 0.45)  |
|     - Eliminates redundant sub-window variations                                  |
|                                       v                                           |
|  6. Ranking & Filtering (ranking.py)                                              |
|     - Filters by min_score (default 50.0), slices top max_results (default 10)    |
|     - Assigns sequential 1-based ranks (#1, #2, #3, ...)                          |
|                                       v                                           |
|  7. Transactional Persistence & Sequential Queue (detector.py & queue.py)         |
|     - Persists to `highlights` SQLite table                                       |
|     - Supersedes unreviewed CANDIDATE records; preserves ACCEPTED/REJECTED        |
|     - Fully cooperatively cancellable via JobQueueManager                         |
|                                       v                                           |
|  8. Workstation UI (HighlightDetectionPanel, HighlightCard, HighlightEditDialog)  |
|     - Card review, live progress, timeline seek, fine-tune editing, accept/reject |
+-----------------------------------------------------------------------------------+
```

---

## 3. Candidate Window Generation

The candidate generator (`backend/app/services/highlight_detection/candidate_generator.py`) explores candidate speech intervals from valid, non-empty transcript segments:

1. **Natural Boundary Anchoring:** Every candidate window begins at the natural opening of an utterance segment.
2. **Forward Accumulation:** Successive transcript segments are accumulated until the cumulative duration satisfies one of the target duration buckets (e.g., `15-30s`, `30-60s`, `60-90s`, or custom `10-180s`).
3. **Word-Level Boundary Trimming:**
   - If word timestamps are present in the segment, the candidate start time is refined to the exact `start_ms` of the first spoken word, stripping leading pause silence.
   - The candidate end time is refined to the exact `end_ms` of the last spoken word, eliminating trailing pauses.
   - Speech boundaries are never cut mid-word.
4. **Physical Bounds Validation:** Windows failing timing requirements ($start\_ms < 0$, $end\_ms \le start\_ms$, $duration < 10s$, $duration > 180s$, or $end\_ms > video\_duration + 1s$) or having fewer than 3 words are strictly filtered out.

---

## 4. Explainable Scoring Engine

The scoring engine (`backend/app/services/highlight_detection/scoring_engine.py`) deterministically scores candidate windows across four core dimensions:

### 4.1. Hook Strength ($W_{\text{hook}} = 30\%$)
- **Base Score:** 50.0.
- **Interrogative Opening:** +25.0 bonus for questions (`why`, `how`, `what`, `who`, `when`, `where`, `can you`, `what if`).
- **Provocative Assertion:** +30.0 bonus for high-curiosity phrases (`secret to`, `biggest mistake`, `nobody talks about`, `nobody understands`, `the truth about`, `stop doing`, `game changer`).
- **Direct Audience Address:** +15.0 bonus for second-person pronouns (`you`, `your`, `everyone`, `look`, `listen`).
- **Imperative Verb:** +12.0 bonus for action verbs (`stop`, `listen`, `watch`, `remember`, `think`, `never`).
- **Length Penalty:** Penalty up to -30.0 if the opening sentence is either too brief (< 4 words) or run-on (> 28 words).
- **Output Range:** Clamped to $[0.0, 100.0]$.

### 4.2. Structural Coherence ($W_{\text{coh}} = 30\%$)
- **Base Score:** 75.0.
- **Clean Termination:** +15.0 bonus when ending on complete sentence punctuation (`.`, `?`, `!`); -20.0 penalty if punctuation is missing.
- **Mid-Clause Conjunction Penalty:** -25.0 penalty and warning (`starts_on_conjunction`) if starting on dangling coordinating conjunctions (`and`, `but`, `so`, `because`, `or`).
- **Incomplete Ending Penalty:** -25.0 penalty and warning (`ends_abruptly_incomplete`) if ending on a preposition or dangling connector (`with`, `at`, `for`, `to`, `of`, `the`, `that`).
- **Self-Contained Narrative Flow:** +10.0 bonus for structured multi-sentence thoughts.
- **Output Range:** Clamped to $[0.0, 100.0]$.

### 4.3. Information Density & Delivery Pacing ($W_{\text{den}} = 25\%$)
- **Base Score:** 80.0.
- **Spoken Delivery Pacing:**
  - Optimal ($130 \le \text{WPM} \le 180$): +10.0 bonus.
  - Moderate ($110 \le \text{WPM} < 130$ or $180 < \text{WPM} \le 210$): +5.0 bonus.
  - Sluggish ($\text{WPM} < 90$): -20.0 penalty + `low_speech_pacing` warning.
  - Overly Rapid ($\text{WPM} > 220$): -15.0 penalty + `rapid_speech_pacing` warning.
- **Filler Word Ratio:**
  - Clean ($\le 2\%$ fillers): +10.0 bonus.
  - High ($> 6\%$ fillers): Penalty up to -25.0 + `high_filler_word_ratio` warning.
- **Long Pauses:** Cumulative penalty of -6.0 per intra-window pause $\ge 1.5$ seconds (clamped to -20.0 max).
- **Lexical Diversity (Type-Token Ratio):** Bonus for $\text{TTR} \ge 0.70$; penalty up to -15.0 for repetitive vocabulary ($\text{TTR} < 0.45$).
- **Output Range:** Clamped to $[0.0, 100.0]$.

### 4.4. Sentiment & Conviction ($W_{\text{sent}} = 15\%$)
- **Base Score:** 50.0.
- **Emotive Vocabulary:** Bonus up to +25.0 (+8.0 per emotive adjective, e.g., `incredible`, `massive`, `shocking`, `mind-blowing`).
- **Conviction Markers:** Bonus up to +20.0 (+7.0 per certainty term, e.g., `absolutely`, `definitely`, `guarantee`, `undeniable`, `essential`).
- **Exclamations:** Bonus up to +15.0 (+7.5 per exclamation mark `!`).
- **Humor / Lighthearted Tone:** Bonus up to +15.0 (+8.0 per humor marker, e.g., `hilarious`, `funny`, `ridiculous`).
- **Output Range:** Clamped to $[0.0, 100.0]$.

### 4.5. Composite Score Formula
$$\text{Composite} = \text{round}\left(\min\left(100.0, \max\left(0.0, 0.30 \cdot S_{\text{hook}} + 0.30 \cdot S_{\text{coh}} + 0.25 \cdot S_{\text{den}} + 0.15 \cdot S_{\text{sent}}\right)\right), 1\right)$$

---

## 5. Non-Maximum Suppression (Deduplication)

When sliding windows across multiple duration presets, overlapping intervals often capture the exact same speech topic. The engine implements greedy Non-Maximum Suppression (`deduplication.py`):

1. **Temporal Overlap Ratio (Intersection over Minimum Duration - IoM):**
   $$\text{Overlap}(A, B) = \frac{\max(0, \min(A.\text{end}, B.\text{end}) - \max(A.\text{start}, B.\text{start}))}{\min(A.\text{duration}, B.\text{duration})}$$
2. **Deterministic Sort:** Candidates are sorted by:
   - Composite Score (descending)
   - Hook Score (descending)
   - Start Time ms (ascending)
   - Duration ms (ascending)
3. **Greedy Selection:** A candidate is retained only if its temporal overlap with all previously accepted candidates is less than `overlap_threshold` (default `0.45`). Any candidate with $\ge 45\%$ overlap is suppressed.

---

## 6. Ranking & Sequential Queue Orchestration

- **Filtering:** Candidates with $\text{composite\_score} < \text{min\_score}$ (default 50.0) are discarded.
- **Rank Assignment:** Top $N \le \text{max\_results}$ candidates are assigned 1-based ranks (`rank = 1, 2, ...`).
- **Sequential Queue Integration:** Highlight detection runs as a background task via `JobQueueManager`. If the user cancels the job, cooperative cancellation checks immediately exit the pipeline and mark the `ProcessingJob` as `CANCELLED`.
- **Database Persistence & Redetection:**
  - Previous `CANDIDATE` highlights for the video are deleted/superseded.
  - User-reviewed highlights with status `ACCEPTED` or `REJECTED` are strictly preserved across re-detection runs.

---

## 7. REST API Endpoints

| Method | Path | Status | Description |
|---|---|---|---|
| `POST` | `/api/v1/videos/{video_id}/highlights/detect` | `202 Accepted` | Submits asynchronous detection job to queue. |
| `POST` | `/api/v1/highlights/detect` | `202 Accepted` | Global detection endpoint accepting `{ "video_id": "..." }`. |
| `GET` | `/api/v1/videos/{video_id}/highlights` | `200 OK` | Retrieves ranked highlights with optional score/status/category filters. |
| `GET` | `/api/v1/highlights/{video_id}` | `200 OK` | Alias route for listing highlights. |
| `GET` | `/api/v1/highlights/detail/{highlight_id}` | `200 OK` | Retrieves single highlight with full explanation and metadata. |
| `PATCH` | `/api/v1/highlights/{highlight_id}` | `200 OK` | Fine-tunes start/end timestamps and editorial summary. |
| `POST` | `/api/v1/highlights/{highlight_id}/accept` | `200 OK` | Marks status as `ACCEPTED` with `reviewed_at` timestamp. |
| `POST` | `/api/v1/highlights/{highlight_id}/reject` | `200 OK` | Marks status as `REJECTED` with optional `rejection_reason`. |

---

## 8. Frontend Workstation Experience

- **`HighlightDetectionPanel`:**
  - Duration preset buttons (`Short 15-30s`, `Medium 30-60s`, `Long 60-90s`).
  - Score threshold and max results sliders.
  - Live progress display during active jobs with "Cancel Detection" button.
  - Interactive filter toolbar (Status: All/Candidate/Accepted/Rejected, Category: All/Insight/Story/Punchline/Discussion/Question, Sort: Rank/Score/Timestamp).
  - Metrics summary bar (Total Candidates, Accepted, Rejected, Top Score).
- **`HighlightCard`:**
  - Rank badge (`#1 Top Pick`, `#2 Runner Up`, `#3 Strong`).
  - Score badge with flame icon and dynamic color coding.
  - Timestamp pill `[00:15 - 00:45 (30s)]`.
  - Quoted hook sentence with custom typography.
  - Natural-language explanation and warning tags.
  - Four granular score bars (Hook, Flow, Density, Energy).
  - Actions: Seek to timestamp in video player, Edit dialog, Accept, Reject.
- **`HighlightEditDialog`:**
  - Bounds-validated start/end timestamp adjustment with live duration feedback.
  - Editorial summary textarea.
- **Workstation Integration:**
  - Full workstation page at `/video/:id/highlights`.
  - Direct integration into Tab 4 (Highlights) of `VideoDetailPage`.
  - Seeking jumps video player directly to highlight timestamp.

---

## 9. Verification & Quality Assurance

- **Backend Pytest Suite:** 27 unit and integration tests in `backend/tests/test_highlight_detection.py`.
- **Full Backend Regression:** 167 of 167 tests passed (100% green).
- **Frontend Vitest Suite:** 11 unit and component tests in `frontend/src/test/highlight-detection.test.tsx`.
- **Full Frontend Regression:** 124 of 124 tests passed (100% green).
- **TypeScript & Linting:** `tsc -b` and `eslint` passed with 0 errors and 0 warnings.
- **Production Build:** Vite production bundle created cleanly.
