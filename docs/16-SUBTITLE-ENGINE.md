# Clipsly Phase 18 — Subtitle & Caption Engine Architecture

## 1. Executive Summary

The **Clipsly Subtitle & Caption Engine** transforms raw, word-level speech transcription data into animated, platform-ready captions burned into 1080x1920 vertical video clips. Built specifically for short-form video consumption (TikTok, YouTube Shorts, Instagram Reels), the engine delivers synchronized, word-by-word karaoke highlighting, customizable typographic styles, and intelligent caption formatting with millisecond accuracy.

In accordance with **ADR-002 (Sequential Execution & Resource Isolation)** and Clipsly's local hardware constraints (ASUS TUF A15, AMD Ryzen 7 7435HS, NVIDIA GeForce RTX 3050 4GB Laptop GPU, 16GB DDR5 RAM, Windows 11), the subtitle engine operates with **zero additional GPU VRAM allocation**. It reads existing word-level timestamps already persisted in the SQLite database by Faster-Whisper, generates Advanced SubStation Alpha (`.ass`) subtitle scripts in pure Python on CPU in under 50ms, and burns captions into video streams using FFmpeg's optimized `libass` rasterizer during final clip export.

---

## 2. High-Level System Architecture

```
+---------------------------------------------------------------------------------------------------+
|                                  PHASE 18 SUBTITLE ENGINE PIPELINE                                |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  1. DATABASE TRANSCRIPT SOURCE                                                                    |
|     - transcripts (status = 'COMPLETED')                                                          |
|     - transcript_segments (start_ms, end_ms, text, words_json)                                    |
|                                       v                                                           |
|  2. TRANSCRIPT SYNCHRONIZATION SERVICE (sync_service.py)                                          |
|     - Intersects transcript words with clip bounds [clip.start_ms, clip.end_ms]                   |
|     - Normalizes absolute media timestamps into clip-relative timestamps:                         |
|         t_rel = t_abs - clip.start_ms                                                             |
|     - Handles boundary-straddling words and punctuation attachment                                |
|                                       v                                                           |
|  3. WORD-LEVEL TIMING & CHUNKING ENGINE (timing_engine.py)                                        |
|     - Missing timestamp interpolation (length-weighted distribution)                              |
|     - Pause boundary detection (breaks chunks on silences > 350ms)                                |
|     - Max words/line rules (2-5 words per caption chunk based on preset)                          |
|     - Overlap clamp and duration anomaly smoothing                                                |
|                                       v                                                           |
|  4. CAPTION STYLING & POSITIONING ENGINE (styling_engine.py)                                      |
|     - Preset loader (Minimal, Modern, Bold, Karaoke Amber, Podcast, Cinematic)                   |
|     - Translates RGB/Hex to ASS &HAABBGGRR color notation                                         |
|     - Computes 1080x1920 vertical placement, margins, safe zones, and font scaling                |
|                                       v                                                           |
|  5. ASS SUBTITLE GENERATOR (ass_generator.py)                                                     |
|     - Constructs canonical ASS v4.00+ document ([Script Info], [V4+ Styles], [Events])            |
|     - Injects \k, \kf, or \K centisecond karaoke tags into dialogue events                        |
|     - Escapes special characters, escapes Windows paths, and outputs UTF-8 .ass file              |
|                                       v                                                           |
|  6. INTERACTIVE CLIENT-SIDE PREVIEW (StudioPage / Web-ASS)                                        |
|     - Studio canvas renders real-time HTML/CSS subtitle overlay synced to HTML5 video             |
|     - In-place text editing and style tuning without video re-rendering                           |
|                                       v                                                           |
|  7. FFMPEG BURN-IN SERVICE (burn_service.py)                                                      |
|     - Assembled into sequential JobQueueManager                                                   |
|     - FFmpeg libass filter: -vf "ass='path_escaped.ass'" or subtitles filter                      |
|     - Real-time progress monitoring via pipe:1                                                    |
|     - Atomic replacement to storage/exports/{clip_id}.mp4                                         |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Subsystem Modules and Responsibilities

The Subtitle & Caption Engine is structured into isolated, testable services under `backend/app/services/subtitles/`:

### 3.1 `sync_service.py` (Transcript Synchronization Service)
- **Role:** Extracts and filters speech segments from SQLite for the specific clip time window.
- **Inputs:** `video_id`, `clip_start_ms`, `clip_end_ms`.
- **Logic:**
  1. Retrieves all `TranscriptSegment` rows where `start_ms < clip_end_ms` AND `end_ms > clip_start_ms`.
  2. Parses `words_json` for each segment.
  3. Excludes words completely outside `[clip_start_ms, clip_end_ms]`.
  4. Trims boundary-crossing words so their start or end aligns with clip edges.
  5. Remaps all timestamps from absolute video timeline to clip-relative timeline ($0\text{ms} \dots \text{duration\_ms}$).

### 3.2 `timing_engine.py` (Word-Level Timing & Chunking Engine)
- **Role:** Normalizes timestamps, resolves missing word data, and groups words into readable caption bursts.
- **Key Algorithms:**
  - **Missing Timestamp Interpolation:** If `words_json` is empty or missing, interpolates word intervals proportional to character lengths within the segment interval.
  - **Chunk Partitioning:** Groups words into 1–5 word chunks according to the active preset's `max_words_per_line` and `max_chars_per_line`.
  - **Pause Splitting:** Forces a new caption chunk whenever inter-word silence $\Delta t \ge 350\text{ms}$.
  - **Timestamp Clamping:** Enforces strictly monotonic timestamps ($w_{i+1}.\text{start} \ge w_{i}.\text{end}$) and minimum word duration ($50\text{ms}$).

### 3.3 `styling_engine.py` (Caption Styling & Positioning Engine)
- **Role:** Maps high-level styling configurations and preset templates to ASS Style declarations and layout coordinates.
- **Key Functions:**
  - Converts CSS/Hex colors (`#RRGGBB`, `#RRGGBBAA`) into ASS BGR format (`&HAABBGGRR`).
  - Calculates margins and safe zones for 1080x1920 vertical video, avoiding UI clutter from TikTok/Reels controls.
  - Generates ASS `[V4+ Styles]` definition blocks with font family, size, outlines, shadows, and alignments.

### 3.4 `ass_generator.py` (ASS Subtitle Generator)
- **Role:** Synthesizes the final Advanced SubStation Alpha (`.ass`) document string and writes it to disk.
- **Key Functions:**
  - Emits canonical headers: `ScriptType: v4.00+`, `PlayResX: 1080`, `PlayResY: 1920`.
  - Formats dialogue lines: `Dialogue: 0,H:MM:SS.cs,H:MM:SS.cs,StyleName,,0,0,0,,Text`.
  - Constructs karaoke tags: `{\kf<duration_cs>}Word ` with centisecond precision.
  - Sanitizes curly braces, backslashes, and line breaks to prevent parser breakage.

### 3.5 `burn_service.py` (FFmpeg Subtitle Burn-In Service)
- **Role:** Executes the FFmpeg subprocess that burns compiled `.ass` subtitles permanently into the MP4 video.
- **Key Functions:**
  - Constructs safe FFmpeg command arguments utilizing `-vf "ass='<escaped_path>'"` or `subtitles` filter.
  - Escapes Windows file paths (drive colons and backslashes) for FFmpeg filtergraphs.
  - Discovers local font directories (`C:\Windows\Fonts` and local application font bundles).
  - Integrates with `JobQueueManager` for cooperative job cancellation, progress tracking, and atomic file replacement.

---

## 4. End-to-End Execution Lifecycle

```
User in Studio UI / API Request
   |
   +--> POST /api/v1/clips/{clip_id}/subtitles/generate
         |
         +--> Retrieve Clip & Active Transcript from SQLite
         |
         +--> sync_service.sync_words_to_clip(clip, segments)
         |     [Extracts words, shifts t_rel = t_abs - clip.start_ms]
         |
         +--> timing_engine.build_caption_chunks(words, preset_config)
         |     [Breaks text into 2-5 word lines with pause awareness]
         |
         +--> styling_engine.resolve_style(clip.preset, overrides)
         |     [Generates ASS styles, colors, positioning]
         |
         +--> ass_generator.generate_ass_file(chunks, style, output_path)
         |     [Writes storage/subtitles/{clip_id}.ass]
         |
         +--> Save subtitle_track & subtitle_events to DB
         |
         +--> Return HTTP 200 / 201 with track metadata
```

When the user triggers a final export or preview render:

```
Export Triggered
   |
   +--> POST /api/v1/clips/{clip_id}/export (or studio burn action)
         |
         +--> Check that .ass file exists in storage/subtitles/
         |
         +--> Queue burn job in JobQueueManager
         |
         +--> burn_service.execute_burn(clip, ass_path, output_path)
         |     [FFmpeg runs on CPU libass + NVENC/libx264 video encoding]
         |     [Monitors progress pipe:1, reports percent]
         |
         +--> Validate output with FFprobe (resolution, duration, streams)
         |
         +--> Atomically replace storage/exports/{clip_id}.mp4
         |
         +--> Update database status to COMPLETED
```

---

## 5. Subtitle Synchronization Strategy

### 5.1 Timestamp Normalization & Boundaries
Let a video clip have start boundary $T_{\text{start}}$ and end boundary $T_{\text{end}}$ in milliseconds.
The clip duration is:
$$D = T_{\text{end}} - T_{\text{start}}$$

For every transcript word $w$ with absolute speech interval $[w.t_0, w.t_1]$:
1. **Inclusion Condition:** The word is retained if and only if:
   $$w.t_1 > T_{\text{start}} \quad \text{and} \quad w.t_0 < T_{\text{end}}$$
2. **Boundary Trimming:**
   $$t_{0,\text{rel}} = \max(0, w.t_0 - T_{\text{start}})$$
   $$t_{1,\text{rel}} = \min(D, w.t_1 - T_{\text{start}})$$
3. **Word Centisecond Duration for Karaoke:**
   $$\Delta t_{\text{cs}} = \max\left(1, \operatorname{round}\left(\frac{t_{1,\text{rel}} - t_{0,\text{rel}}}{10}\right)\right)$$

### 5.2 Missing Word Timestamps Handling (Duration-Safe Interpolation)
If a transcript segment contains text but lacks word-level timestamps (e.g. Faster-Whisper produced segment-level timestamps without word alignments or fallback speech models were used):
1. The segment text is split into tokens: $W = [w_1, w_2, \dots, w_k]$ ($k \ge 1$).
2. Let $L_i = \max(1, \operatorname{len}(w_i))$ be the character length of word $w_i$.
3. Total character weight: $L_{\text{total}} = \sum_{i=1}^k L_i$.
4. Segment duration: $D_{\text{seg}} = \text{seg.end\_ms} - \text{seg.start\_ms}$.
5. **Duration-Safe Constraint Rule:** To prevent total duration from ever exceeding $D_{\text{seg}}$, the engine **must not** blindly enforce an arbitrary minimum (such as $60\text{ms}$) that would inflate short segments beyond their actual duration.
6. Proportional allocation with remainder distribution:
   $$\text{base\_dur}_i = \left\lfloor D_{\text{seg}} \times \frac{L_i}{L_{\text{total}}} \right\rfloor$$
   If $D_{\text{seg}} \ge k$, enforce $\text{dur}_i \ge 1\text{ms}$. The integer division remainder $R = D_{\text{seg}} - \sum \text{base\_dur}_i$ is distributed $+1\text{ms}$ at a time across the longest tokens until $\sum_{i=1}^k \text{dur}_i = D_{\text{seg}}$ exactly.
7. Synthetic start and end times are mapped sequentially within $[\text{seg.start\_ms}, \text{seg.end\_ms}]$:
   $$t_{0,i} = \text{seg.start\_ms} + \sum_{j=1}^{i-1} \text{dur}_j$$
   $$t_{1,i} = t_{0,i} + \text{dur}_i$$
   This guarantees:
   - Strictly monotonic non-overlapping intervals ($t_{0, i+1} = t_{1, i}$).
   - Boundary containment: $t_{0, 1} = \text{seg.start\_ms}$ and $t_{1, k} = \text{seg.end\_ms}$.
   - Zero duration overflow regardless of token count or segment duration.

---

## 6. Safe Mobile UI Zone Positioning

Short-form platforms overlay interactive UI elements on vertical 1080x1920 videos. Subtitles placed inside overlay areas suffer severe legibility degradation.

```
+-----------------------------------------+ 0px (Top)
|  [ TOP SAFE ZONE: 0 - 240px ]           |  Avoid: Platform header, search bar,
|                                         |         device camera notch
+-----------------------------------------+ 240px
|                                         |
|                                         |
|  [ OPTIMAL CONTENT & TITLE ZONE ]       |
|                                         |
|                                         |
|  [ MIDDLE CAPTION POSITION ]            |  Y = 960px (Center)
|                                         |
|                                         |
|  [ OPTIMAL BOTTOM CAPTION ZONE ]        |  Y = 1350px - 1550px
|                                         |  MarginV = 370px - 450px from bottom
+-----------------------------------------+ 1600px
|  [ BOTTOM OVERLAY DANGER ZONE ]         |  Avoid: Author name, sound title,
|  1600px - 1920px                        |         captions, engagement buttons
+-----------------------------------------+ 1920px (Bottom)
```

- **Bottom Alignment (`Alignment=2`):** `MarginV = 380px` (positions captions directly above platform description text).
- **Middle Alignment (`Alignment=5`):** `MarginV = 0px` (centered at Y = 960px, popular for podcast clips).
- **Top Alignment (`Alignment=8`):** `MarginV = 280px` (below header elements, used when video bottom features critical screen graphics).

---

## 7. Architectural Decisions (ADRs)

### ADR-018-01: Native ASS File Generation Over SRT/VTT
- **Context:** Mobile short-form videos require word-by-word karaoke animations, explicit font sizing, custom outline strokes, and exact pixel positioning on 1080x1920 canvases.
- **Decision:** Use Advanced SubStation Alpha (`.ass` v4.00+) as the primary internal subtitle format.
- **Rationale:** SRT lacks styling, animation, and positioning tags. WebVTT has inconsistent player support and lacks native `\k` karaoke tags. ASS is universally supported by FFmpeg's `libass` filter with microsecond rendering speed and precise typographic control.

- **CPU Performance Targets (Architectural Estimates — Unverified until runtime benchmarking):**
  - ASS subtitle generation is designed to run purely in Python on the AMD Ryzen 7 7435HS CPU.
  - The design target for compiling a 60-second clip's ASS script is estimated at $< 50\text{ms}$ CPU time and $< 10\text{MB}$ host RAM (subject to verification in Phase 18 runtime benchmarks).
  - No Whisper models are re-loaded into the RTX 3050's 4GB VRAM.
- **Canonical Documentation Policy:**
  - The root `docs/` directory of the project is the **sole canonical documentation repository**.
  - Duplicate, divergent, or secondary copies of documentation files must not be maintained.

---

## 8. Architectural Decisions (ADRs)

### ADR-018-03: Two-Tier Subtitle Storage (Database + Filesystem)
- **Context:** Users need fast subtitle editing in Studio, while FFmpeg requires physical files on disk for video burning.
- **Decision:** Persist structured subtitle events in the database (`subtitle_tracks` and `subtitle_events`), and compile on-demand to physical `.ass` files in `storage/subtitles/{clip_id}.ass`.
- **Rationale:** Storing events in SQLite allows word-level corrections and style updates without re-parsing raw text, while generating `.ass` files gives FFmpeg clean disk assets.
