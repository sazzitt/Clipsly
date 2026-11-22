# Product Requirements Document (PRD)

**Project Name:** AI Video Clipper (Working Title: Clipsly)  
**Document Version:** 1.0.0  
**Status:** APPROVED (Phase 01 Complete)  
**Author:** Senior Product Manager, Software Architect & Technical Documentation Engineer  
**Target Platform:** Local-First Web Application (Windows 11 / Localhost)  

---

## 1. Project Introduction

**AI Video Clipper** (working title: **Clipsly**) is a sovereign, local-first, single-user desktop web application designed to transform long-form video recordings (such as podcasts, conference talks, educational lectures, interviews, and gameplay streams) into high-engagement, vertical short-form video clips (9:16 aspect ratio) suitable for YouTube Shorts, Instagram Reels, and TikTok.

Operating entirely on the user's local hardware—an **ASUS TUF A15 laptop (AMD Ryzen 7 7000 Series CPU, NVIDIA GeForce RTX 3050 Laptop GPU with 4GB VRAM)**—the system executes the entire media pipeline locally: from video ingestion, audio extraction, and speech-to-text transcription (via Faster-Whisper), to algorithmic and AI-assisted highlight detection, intelligent 9:16 reframing, animated subtitle generation, interactive review, and hardware-accelerated MP4 export via FFmpeg (NVENC).

By maintaining all media processing, database storage (SQLite), and AI inference strictly on the local machine, the application delivers total data sovereignty, zero ongoing subscription or cloud egress costs, and freedom from third-party server queues.

---

## 2. Problem Statement

Modern content creators, educators, streamers, and marketers face significant bottlenecks when repurposing long-form horizontal video into bite-sized vertical shorts:

1. **High Subscription & Cloud Costs:** Existing commercial clipping platforms (e.g., Opus Clip, Munch, Klap) rely on cloud-hosted SaaS models requiring expensive recurring subscriptions, metered minute limits, and costly credit packs.
2. **Privacy, Security & Bandwidth Constraints:** Uploading multi-gigabyte 4K/1080p raw footage to third-party cloud servers takes hours on standard home connections, incurs bandwidth caps, and exposes unreleased, sensitive, or proprietary footage to third-party privacy risks.
3. **Manual Editing Fatigue:** Manually scrubbing through a 60-minute video in traditional Non-Linear Editors (NLEs) such as Premiere Pro or DaVinci Resolve to locate engaging soundbites, transcribe dialogue, cut timestamps, animate captions, and crop to 9:16 takes between 2 to 4 hours per long-form video.
4. **Hardware Incompatibility of Off-the-Shelf AI Models:** Many open-source AI workflows require 8GB–24GB of GPU VRAM (e.g., large multi-modal models, 70B LLMs, or heavy Whisper models), causing Out-Of-Memory (OOM) crashes on standard consumer laptops equipped with budget GPUs like the 4GB NVIDIA RTX 3050.

There is a clear market need for a streamlined, self-hosted, personal clipping studio that automates the end-to-end extraction and styling pipeline while running comfortably within a constrained 4GB VRAM footprint.

---

## 3. Product Vision

To empower individual creators with a zero-cost, private, intelligent desktop production assistant that turns raw, long-form video files into platform-ready, captioned vertical short clips with a single click, pairing local AI automation with complete user editorial control.

---

## 4. Project Objectives

- **O1: Local-First Autonomy:** Provide a complete video clipping workflow that operates 100% offline without mandatory internet connectivity, external API dependencies, or cloud services.
- **O2: Strict 4GB VRAM Stability:** Architect all AI inference (transcription, highlight detection) and hardware video encoding to run reliably on an NVIDIA RTX 3050 (4GB VRAM) without triggering CUDA OOM failures.
- **O3: High-Accuracy Automated Transcription:** Achieve word-level speech-to-text transcription utilizing Faster-Whisper with punctuation, capitalization, and accurate millisecond timestamps.
- **O4: Intelligent Highlight Scoring:** Identify coherent, standalone, and high-impact dialogue segments (15s–90s) using deterministic heuristics combined with lightweight semantic evaluation.
- **O5: Automated 9:16 Vertical Reframing:** Convert 16:9 widescreen footage into 9:16 vertical videos using high-quality background blur-padding and center-crop modes.
- **O6: Dynamic Subtitle Generation:** Burn animated, karaoke-style subtitles into exported clips with customizable typography, colors, borders, and position.
- **O7: Low Latency Interactive Studio:** Offer an in-browser studio to preview candidates, fine-tune start/end trim boundaries with millisecond precision, edit subtitle text, and trigger fast NVENC-accelerated exports.

---

## 5. Target User

- **Primary Persona:** The Solo Creator / Developer / Podcaster
  - **Profile:** Creator running an ASUS TUF A15 gaming laptop (Ryzen 7, RTX 3050 4GB).
  - **Workflow:** Records 30–90 minute interviews, podcasts, technical walkthroughs, or tutorials.
  - **Needs:** Fast turnaround of 3 to 10 viral-ready clips per episode for social distribution without manual transcript scrubbing or recurring SaaS fees.
  - **Technical Comfort:** High comfort running local desktop software, comfortable with standard browser interfaces, values complete ownership of local media files.

---

## 6. User Stories

### Epic 1: Video Ingestion & Analysis
- **US1.1:** As a user, I want to drag and drop a local video file (MP4, MKV, MOV, WEBM) into the browser so that the app validates the file and extracts its technical metadata (resolution, frame rate, duration, audio channels).
- **US1.2:** As a user, I want to see an immediate in-browser preview of my uploaded video along with a progress bar indicating audio extraction status.

### Epic 2: Local AI Transcription
- **US2.1:** As a user, I want the system to transcribe the audio track automatically using Faster-Whisper on my RTX 3050 GPU so that I get accurate, word-level timestamps without uploading audio to the cloud.
- **US2.2:** As a user, I want transcription to fall back to CPU seamlessly if GPU VRAM is constrained, with clear status indicators in the UI.
- **US2.3:** As a user, I want to read, search, and review the full generated transcript alongside the video player.

### Epic 3: Highlight Detection & Ranking
- **US3.1:** As a user, I want the application to automatically analyze the transcript and propose 3 to 10 interesting clip segments ranked by engagement score.
- **US3.2:** As a user, I want highlights to start and end on complete sentences and natural speech pauses, rather than cutting speakers off mid-word.
- **US3.3:** As a user, I want to filter highlights by target duration (e.g., 15–30s, 30–60s, 60–90s).

### Epic 4: Vertical Reframing & Subtitle Styling
- **US4.1:** As a user, I want the system to automatically transform widescreen footage into 9:16 vertical format using blurred background pillarboxing or center cropping so that it looks professional on mobile platforms.
- **US4.2:** As a user, I want customizable subtitles (font family, size, highlight color, outline) with animated word-by-word karaoke highlighting.

### Epic 5: Review, Fine-Tuning & Export
- **US5.1:** As a user, I want an interactive timeline where I can scrub the proposed clip, adjust start and end handles, and preview subtitle sync in real time.
- **US5.2:** As a user, I want to edit subtitle wording directly in the studio if a word was misheard by the transcription model.
- **US5.3:** As a user, I want to click "Export Clip" and have the application render a production-ready 1080x1920 MP4 file to my local SSD using NVIDIA NVENC hardware acceleration in under 30 seconds.

---

## 7. Complete Feature List

### Feature Group A: Media Ingestion & Storage
- **F-A1:** Local file picker and drag-and-drop zone.
- **F-A2:** Subprocess-driven media validation via `ffprobe` (container check, audio stream presence, duration limits).
- **F-A3:** Metadata extraction (resolution, FPS, aspect ratio, audio sample rate, bitrate).
- **F-A4:** Local structured file management (`/storage/uploads`, `/storage/audio`, `/storage/clips`, `/storage/exports`).
- **F-A5:** SQLite database persistence for video metadata, job records, and configuration.

### Feature Group B: Speech-to-Text Transcription Engine
- **F-B1:** Subprocess or in-process execution of `faster-whisper`.
- **F-B2:** Model size selection (defaulting to `base` or `small` with `float16` or `int8_float16` for 4GB VRAM safety).
- **F-B3:** Word-level timestamp extraction with punctuation and capitalization formatting.
- **F-B4:** VAD (Voice Activity Detection) pre-filtering using Silero VAD to eliminate silence processing.
- **F-B5:** Auto-detection of spoken language (primary: English, with multi-language fallback).

### Feature Group C: Highlight Detection & Scoring Engine
- **F-C1:** Transcript text segmentation into topical sentences and paragraphs.
- **F-C2:** Heuristic scoring algorithm assessing speech density, keyword hooks, sentiment inflection, and structural completeness.
- **F-C3:** AI LLM evaluation integration (supporting local quantized models via Ollama/llama.cpp or optional API fallback) evaluated within strict memory bounds.
- **F-C4:** Highlight ranking and categorization (e.g., "Insight", "Story", "Punchline", "Discussion").
- **F-C5:** Automatic padding buffer (0.5s–1.0s) around clip boundaries for natural speech cadence.

### Feature Group D: Video Re-Framing & Transformation Engine
- **F-D1:** 9:16 vertical canvas composition (target: 1080x1920).
- **F-D2:** Mode 1: Blurred background pillarbox (scaled, heavily blurred background layer with sharp centered foreground).
- **F-D3:** Mode 2: Center crop with configurable horizontal offset anchor.
- **F-D4:** Fast cutting using FFmpeg stream copying where possible or high-speed re-encoding.

### Feature Group E: Dynamic Subtitle Generation Engine
- **F-E1:** Automated generation of ASS (Advanced SubStation Alpha) and SRT subtitle tracks.
- **F-E2:** Karaoke word-by-word animation styles (active word color highlight, scale bump).
- **F-E3:** Configurable font typography, font size, stroke width, shadow depth, and vertical placement.
- **F-E4:** Burned-in (hardcoded) subtitle rendering via FFmpeg `libass` filter graph.

### Feature Group F: Interactive Studio & Clip Editor
- **F-F1:** Dual-player UI: Long-form source player and 9:16 vertical clip preview player.
- **F-F2:** Interactive dual-handle range slider for precision start/end trimming.
- **F-F3:** In-place editable transcript text synchronizing with video playback.
- **F-F4:** Real-time subtitle styling control panel with instant visual feedback.

### Feature Group G: Hardware-Accelerated Export Engine
- **F-G1:** NVIDIA NVENC hardware-accelerated video encoding (`h264_nvenc`).
- **F-G2:** CPU fallback encoding (`libx264` with `preset=fast`) if GPU is busy or unsupported.
- **F-G3:** Target MP4 container creation with AAC stereo audio.
- **F-G4:** One-click download or direct local folder reveal in Windows File Explorer.

---

## 8. Functional Requirements

| Req ID | Category | Description | Input | Output | Error Condition |
|---|---|---|---|---|---|
| **FR-01** | Ingestion | Validate uploaded video file container, codec, and presence of an audio stream | Binary file path / stream | JSON metadata object | Reject invalid container or silent video with 400 error |
| **FR-02** | Ingestion | Store uploaded file in designated local SSD directory with sanitized UUID filename | Raw file upload | Persistent file path | Storage disk full (>95%) triggers 507 error |
| **FR-03** | Audio | Extract single-channel 16kHz WAV audio optimized for speech recognition | Source video path | 16kHz Mono WAV file | FFmpeg extraction failure triggers job error state |
| **FR-04** | Transcribe | Transcribe audio using Faster-Whisper on RTX 3050 GPU (VRAM bounded) | 16kHz Mono WAV | Word-level JSON transcript with start/end ms | CUDA OOM triggers automatic retry on CPU (`device=cpu`) |
| **FR-05** | Transcribe | Persist full transcript and segmented sentences into SQLite database | JSON transcript | Database records in `transcripts` table | Database lock / write failure triggers transaction rollback |
| **FR-06** | Highlights | Segment transcript into candidate chunks between 15s and 90s | Full transcript records | Array of candidate text chunks with timestamps | Empty transcript produces zero candidates warning |
| **FR-07** | Highlights | Score candidate chunks based on hook intensity, topic closure, and pacing | Candidate text chunks | Scored highlights (0–100) sorted descending | Scoring engine failure defaults to heuristic density ranking |
| **FR-08** | Highlights | Expand start/end timestamps to nearest sentence boundary and pause | Raw timestamp range | Snapped timestamp range (+0.5s padding) | Boundary exceeds video duration clamped to [0, duration] |
| **FR-09** | Video | Generate precise cut from source video using FFmpeg without audio desync | Source video + start/end ms | Lossless intermediate clip MP4 | Demuxer timestamp discontinuity triggers keyframe re-encode |
| **FR-10** | Transform | Apply 9:16 vertical filtergraph (blur background or center crop) | Intermediate clip MP4 | 1080x1920 reframed MP4 | Invalid aspect ratio parameters trigger fallback to blur |
| **FR-11** | Subtitles | Generate ASS subtitle script with word-level `\k` karaoke timing tags | Highlight word list + style config | Formatted `.ass` subtitle file | Malformed timing tags trigger fallback to static SRT |
| **FR-12** | Render | Burn subtitles into 9:16 video using NVENC hardware encoder | Reframed video + ASS file | Final production MP4 file | NVENC failure triggers automatic fallback to `libx264` CPU |
| **FR-13** | Studio | Allow manual timeline adjustment of start and end timestamps in UI | Drag handle event (ms) | Updated clip duration and preview sync | Invalid range (start >= end) disables save/render button |
| **FR-14** | Studio | Allow in-place editing of transcript text before final render | Updated text string | Updated subtitle file and database record | Empty text string prevents subtitle generation |
| **FR-15** | Export | Save rendered clip to `/storage/exports` and trigger browser file download | Clip ID | File stream / Windows path reveal | File not found returns 404 with audit log |

---

## 9. Non-Functional Requirements

### 9.1 Performance & Latency
- **NFR-P1 (Transcription Speed):** Faster-Whisper `base` model running on RTX 3050 must achieve a Real-Time Factor (RTF) of $\le 0.15\times$ (i.e., a 60-minute video transcribes in $\le 9$ minutes).
- **NFR-P2 (Clip Rendering Speed):** A 30-second 1080x1920 vertical clip with burned subtitles must render in $\le 20$ seconds using NVENC (`h264_nvenc`).
- **NFR-P3 (UI Responsiveness):** All API responses for local metadata, state queries, and transcript retrieval must respond in $<100\text{ ms}$.
- **NFR-P4 (Memory Ceiling):** Backend process peak GPU VRAM usage must never exceed 3.5GB to avoid OS compositor starvation and driver crashes on the 4GB RTX 3050.

### 9.2 Reliability & Fault Tolerance
- **NFR-R1 (Graceful Recovery):** Background job worker must catch unhandled exceptions, record detailed error logs in SQLite, and transition the job to an `ERROR` state with actionable user guidance.
- **NFR-R2 (OOM Prevention):** AI models (Whisper and any LLM) must be loaded sequentially or isolated so that two heavy GPU models never reside in VRAM simultaneously.
- **NFR-R3 (Process Isolation):** Heavy FFmpeg rendering must execute as isolated asynchronous subprocesses with explicit timeout watchdogs (max 10 minutes per clip).

### 9.3 Usability & UX Standards
- **NFR-U1 (Clean Modern Interface):** Built with React, Tailwind CSS, and shadcn/ui components, adhering to a high-contrast dark theme optimized for video editing.
- **NFR-U2 (Progress Transparency):** Every pipeline phase (uploading, extracting audio, transcribing, detecting highlights, rendering) must display real-time percentage and step indicators.
- **NFR-U3 (Zero Command-Line Requirement):** Once launched, the user must never be required to touch a terminal or execute manual FFmpeg commands.

### 9.4 Security & Data Privacy
- **NFR-S1 (Air-Gapped Sovereign Operation):** Application listens strictly on loopback (`127.0.0.1` / `localhost`). External inbound connections are blocked by default.
- **NFR-S2 (Path Traversal Protection):** All file upload names, export paths, and media queries must be strictly validated against path traversal (`..`, absolute paths, symlinks).
- **NFR-S3 (Zero Telemetry):** No user media, transcripts, metadata, or telemetry shall be transmitted to external servers.

---

## 10. Complete Application Workflow

The application executes a strictly ordered 16-step pipeline from raw upload to finished MP4:

```
[1. Upload Video] ──> [2. Validate Video] ──> [3. Extract Metadata] ──> [4. Preview Video]
         │
         ▼
[5. Extract Audio] ──> [6. Generate Transcript] ──> [7. Analyze Transcript] ──> [8. Detect Highlights]
         │
         ▼
[9. Score & Rank] ──> [10. Select Timestamps] ──> [11. Generate Clips] ──> [12. Convert to Vertical]
         │
         ▼
[13. Add Subtitles] ──> [14. Preview Clips] ──> [15. Edit if Necessary] ──> [16. Export Final MP4]
```

### Detailed Step-by-Step Breakdown:

1. **Upload Video:**
   - User drags and drops a local video file or selects it via the OS native file dialog.
   - Streamed chunk-by-chunk to the local backend `/storage/uploads/` directory to conserve system RAM.
2. **Validate Video:**
   - Backend invokes `ffprobe` to verify valid container structure, confirm container integrity, and confirm presence of at least one valid video stream and one valid audio stream.
3. **Extract Metadata:**
   - `ffprobe` parses container for duration, resolution (width/height), display aspect ratio, frame rate, audio sample rate, channel count, and bitrate. Stored in SQLite `videos` table.
4. **Preview Video:**
   - Video file is made available immediately to the frontend HTML5 video player via HTTP Range requests (`206 Partial Content`) for instant scrubbing without waiting for transcription.
5. **Extract Audio:**
   - FFmpeg extracts the audio track into a normalized, single-channel (mono), 16,000 Hz, 16-bit PCM WAV file (`/storage/audio/{video_id}.wav`).
6. **Generate Transcript:**
   - Faster-Whisper loads the 16kHz WAV file, applies Silero Voice Activity Detection (VAD) to trim silence, and runs GPU-accelerated speech-to-text inference.
   - Generates tokens, sentence groupings, and word-level timestamps (start time, end time, confidence score).
7. **Analyze Transcript:**
   - Backend parses transcript words into sentences, detects natural discourse boundaries, paragraphs, and speaker pauses ($>0.6\text{s}$).
8. **Detect Highlights:**
   - Algorithmic scanner evaluates sentences in sliding windows matching user-configured clip duration targets (e.g., 30–60s).
   - Identifies high-value narrative segments containing strong introductory hooks, high information density, and conclusive thoughts.
9. **Score and Rank Highlights:**
   - Each candidate window receives a normalized score (0 to 100) combining hook punchiness, emotional valence, speech tempo, and topic coherence.
   - Highlights are sorted descending by score; top $N$ candidates are preserved.
10. **Select Timestamps:**
    - High-ranking candidates have their boundaries snapped to the nearest preceding and succeeding sentence pause, adding a 0.5s pre-roll and 0.5s post-roll padding to prevent speech clipping.
11. **Generate Clips:**
    - Fast sub-clip slicing extracts the raw video and audio segments from the source video according to the calculated start/end timestamps.
12. **Convert to Vertical Format (9:16):**
    - FFmpeg filtergraph builds the 1080x1920 canvas:
      - *Blur-Pad Mode:* Source is split into two streams. Stream 1 is cropped and scaled to 1080x1920 with a 40px Gaussian blur. Stream 2 is scaled to 1080px width preserving aspect ratio, then centered on top of Stream 1.
      - *Center-Crop Mode:* Source is cropped to 9:16 aspect ratio centered horizontally, then scaled to 1080x1920.
13. **Add Subtitles:**
    - Word timestamps within the clip boundaries are compiled into an ASS (Advanced SubStation Alpha) subtitle file.
    - Word-level karaoke timing (`\k`) tags highlight the active spoken word in real-time.
14. **Preview Generated Clips:**
    - Reframed clip with draft subtitle overlays renders in the interactive Studio UI for immediate user inspection.
15. **Edit if Necessary:**
    - User can drag timeline handles to trim or lengthen the clip, alter subtitle font/color/size presets, or fix any misrecognized transcript text.
16. **Export Final MP4 Files:**
    - User clicks "Export". FFmpeg burns subtitles permanently into the video stream via `libass` and encodes the video using NVIDIA NVENC (`h264_nvenc`) to produce an optimized, platform-compliant MP4 file saved in `/storage/exports/`.

---

## 11. Video Input Requirements

- **Input Method:** Local file system upload via drag-and-drop or native OS file picker.
- **Streaming URL Input:** Strictly **out of scope** (No YouTube, Vimeo, Twitch, or HTTP stream downloads).
- **Audio Requirement:** Video file **must** contain an active audio stream. Silent video files are rejected immediately during Step 2 (Validation).
- **Resolution Ceiling:** Supports inputs up to 3840x2160 (4K UHD) at up to 60 FPS; downscales to 1080x1920 during vertical export.
- **Audio Channels:** Stereo and Mono inputs supported; multi-channel audio (5.1, 7.1) is automatically downmixed to mono for transcription and stereo for clip export.

---

## 12. Supported Video Formats

| Container | Extension | Video Codecs Supported | Audio Codecs Supported | Status |
|---|---|---|---|---|
| **MP4** | `.mp4`, `.m4v` | H.264 (AVC), H.265 (HEVC), AV1 | AAC, MP3, Opus, PCM | **CONFIRMED (Tier 1)** |
| **Matroska** | `.mkv` | H.264, H.265, VP9, AV1 | AAC, MP3, Opus, FLAC, AC3 | **CONFIRMED (Tier 1)** |
| **QuickTime** | `.mov` | H.264, H.265, Apple ProRes | AAC, PCM, ALAC | **CONFIRMED (Tier 1)** |
| **WebM** | `.webm` | VP8, VP9, AV1 | Opus, Vorbis | **CONFIRMED (Tier 1)** |
| **AVI** | `.avi` | MPEG-4, DivX, Xvid | MP3, PCM | *PROPOSED (Tier 2)* |
| **MPEG-TS** | `.ts`, `.mts` | H.264, MPEG-2 | AAC, AC3, MP2 | *PROPOSED (Tier 2)* |

*Decision Rule:* Tier 1 formats are natively handled by FFmpeg and modern browser engines (or easily demuxed). Tier 2 formats will be converted to MP4 intermediates during ingestion if enabled in future phases.

---

## 13. Video Duration and Size Considerations

- **Maximum Recommended Duration:** 120 minutes (2 hours). Videos up to 4 hours can be ingested, but processing times increase linearly.
- **Maximum Recommended File Size:** 10 GB per file. Local SSD storage must maintain at least 20 GB free space before starting an ingestion job.
- **Chunked Processing Strategy:** For videos $>45$ minutes, audio extraction and Whisper transcription use chunked VAD segmentation to prevent memory accumulation in Python process memory.
- **Disk Space Management:** The application provides a storage indicator showing available SSD space, warning the user if free space falls below 15 GB.

---

## 14. AI Transcription Requirements

- **Transcription Engine:** `faster-whisper` (CTranslate2-based Whisper implementation).
- **Model Sizes & Hardware Allocation on 4GB RTX 3050:**
  - `tiny` (~75MB VRAM): Ultra-fast draft mode, lower accuracy.
  - `base` (~150MB VRAM): Fast, adequate accuracy for clean studio audio.
  - `small` (~500MB VRAM): **Recommended Default.** Excellent balance of word accuracy, punctuation, and low VRAM footprint.
  - `medium` (~1.5GB VRAM): High accuracy, viable on RTX 3050 if compute type is quantized (`int8_float16`).
  - `large-v3` (~3.1GB VRAM): *Not recommended* for primary pipeline as it leaves inadequate headroom for NVENC encoding and system compositor.
- **Compute Type:** `float16` or `int8_float16` when running on CUDA; `int8` when falling back to CPU.
- **Timestamp Precision:** Word-level timestamps mandatory for karaoke subtitle synchronization.
- **VAD Pre-filtering:** Silero VAD enabled to skip silent sections, reducing hallucination and speeding up inference by 20–35%.

---

## 15. Highlight Detection Requirements

To produce compelling short-form clips without exceeding local hardware limits, the highlight engine evaluates candidate chunks on four key dimensions:

1. **Hook Strength (0–30 pts):** Evaluates the first 3–5 seconds of a candidate chunk. Looks for provocative questions, contrarian statements, storytelling openers ("So the crazy thing was...", "The secret to..."), or exclamation.
2. **Thematic Coherence & Closure (0–30 pts):** Assesses whether the chunk represents a complete thought with a premise, elaboration, and natural conclusion, avoiding abrupt cut-offs.
3. **Pacing & Information Density (0–25 pts):** Analyzes words-per-minute (optimal: 130–170 WPM) and speech variance to ensure the speaker is energetic and engaging rather than monotonous.
4. **Sentiment & Emotional Modulation (0–15 pts):** Measures vocal intensity and vocabulary valence (excitement, revelation, urgency).

### Architectural Implementation:
- **Phase 10 Baseline (Deterministic Heuristic):** Rule-based lexical analysis, keyword density scoring, sentence boundary parsing, and silence duration metrics.
- **AI LLM Expansion (Evaluated for Phase 10):** Integration with an ultra-lightweight local quantized model (e.g., Qwen2.5-3B-Instruct or Llama-3.2-3B via Ollama/llama.cpp in 4-bit quantization, requiring ~1.8GB VRAM) loaded *after* Whisper has unloaded from VRAM, or an optional user-provided cloud LLM API key (OpenAI/Anthropic/Gemini) if the user desires cloud-grade semantic reasoning without hardware strain.

---

## 16. Clip Duration Configuration

The application allows users to configure target duration presets or custom ranges:

- **Preset 1 (Micro-Shorts):** 15s to 30s (Optimized for quick tips, jokes, viral soundbites).
- **Preset 2 (Standard Shorts / Reels):** 30s to 60s (**Default**; optimal retention curve for YouTube Shorts and Instagram Reels).
- **Preset 3 (Extended Insight):** 60s to 90s (Optimized for detailed tutorials, philosophical insights, long stories).
- **Custom Range:** User specifies minimum duration ($T_{\min} \ge 10\text{s}$) and maximum duration ($T_{\max} \le 180\text{s}$).
- **Boundary Snapping:** Clips are never cut strictly at the duration limit; boundaries snap to the closest natural pause within $\pm 3.0\text{s}$ of the target range.

---

## 17. Automatic Vertical Conversion

Converts 16:9 (horizontal) or other aspect ratios into 9:16 (vertical 1080x1920) format:

### Reframing Modes:
1. **Blurred Background Pillarbox (Default / Universal):**
   - Background: Source video scaled and cropped to fill 1080x1920, darkened by 25%, and processed with a high-radius Gaussian blur filter (`boxblur=20:5` or `gblur=sigma=30`).
   - Foreground: Original aspect ratio video scaled to fit 1080px width, centered vertically at coordinates `(0, (1920-h)/2)`.
   - Advantage: Zero loss of visual context, works for multi-speaker interviews, screen shares, and landscape views.
2. **Center Crop (Action / Single Speaker Focus):**
   - Crops a 9:16 slice (`w = in_h * 9/16`, `h = in_h`) from the center of the 16:9 source and scales to 1080x1920.
   - Configurable horizontal pan offset (left, center, right) in the Studio UI.
3. **Smart Face Tracking (Proposed for Future Phase):**
   - MediaPipe or OpenCV face detection to dynamically center the active speaker. Marked as **PLANNED** for post-MVP due to 4GB VRAM and processing overhead considerations.

---

## 18. Subtitle Customization Requirements

High-impact, synchronized subtitles are essential for short-form mobile engagement:

- **Format:** ASS (Advanced SubStation Alpha) v4+ style burned directly into the video stream via FFmpeg `subtitles` / `ass` filter.
- **Word-Level Highlighting (Karaoke Animation):**
  - Displays 3 to 6 words on screen per line to maximize readability on mobile screens.
  - Active word currently being spoken illuminates in a vibrant accent color (e.g., `#FFD700` Yellow, `#00FFCC` Cyan, `#FF3366` Neon Red) while inactive words remain white/light gray.
- **Customization Options:**
  - **Font Family:** Montserrat, Inter, Roboto, Arial, Impact, Bangers (bundled local TTF fonts).
  - **Font Size:** 18pt to 36pt (scaled for 1080x1920 canvas).
  - **Primary Color:** Hex color picker with presets.
  - **Highlight Color:** Hex color picker with presets.
  - **Outline / Stroke:** Black outline with configurable thickness (1px–6px) for legibility over any background.
  - **Drop Shadow:** Optional soft shadow offset.
  - **Vertical Positioning:** Bottom third (default, 75% down canvas), Center (50%), or Upper third (25%).

---

## 19. Preview and Editing Requirements

The Studio interface provides a real-time editing workspace:

- **Interactive Clip Timeline:**
  - Visual waveform and sentence marker representations.
  - Dual draggable trim handles allowing millisecond-accurate adjustment of `clip_start` and `clip_end`.
  - Minimum clip duration enforcement (10 seconds).
- **Synchronized Dual Video Player:**
  - Fast-seeking HTML5 video player reflecting trim boundaries.
  - Live subtitle overlay reflecting timing and style choices before final burn-in export.
- **In-Place Subtitle Editor:**
  - Interactive transcript table showing each spoken segment with start/end timestamps.
  - Double-click to edit any misheard word or fix spelling without re-running transcription.
- **Aspect Ratio Preview Toggle:**
  - Instantly switch between 9:16 vertical preview, 1:1 square preview, and 16:9 source preview.

---

## 20. Export Requirements

- **Output Container:** MP4 (MPEG-4 Part 14).
- **Video Codec:**
  - Primary: `h264_nvenc` (NVIDIA NVENC hardware encoding on RTX 3050) using `preset=p4`, `rc=vbr`, `cq=23`, `profile=high`.
  - Fallback: `libx264` (CPU encoding) using `preset=fast`, `crf=22`.
- **Audio Codec:** AAC (Advanced Audio Coding), 192 kbps, 48,000 Hz, Stereo.
- **Output Resolution:** 1080 x 1920 pixels (9:16 vertical orientation).
- **Frame Rate:** Matches source frame rate (standardized to 30 FPS or 60 FPS).
- **File Naming Convention:** `{original_video_title}_clip_{index}_{timestamp}.mp4` (sanitized against special characters).
- **Destination:** Rendered to `/storage/exports/` and made available for instant browser download or "Show in File Explorer" on Windows.

---

## 21. Local Storage Requirements

All media, database files, and caches reside in structured local SSD directories:

```
clipsly/
├── storage/
│   ├── uploads/       # Raw uploaded video files
│   ├── audio/         # Extracted 16kHz WAV audio files
│   ├── transcripts/   # Raw JSON transcript files
│   ├── clips/         # Intermediate sliced raw video clips
│   ├── subtitles/     # Generated .ass and .srt subtitle files
│   ├── exports/       # Final rendered 1080x1920 MP4 video clips
│   └── temp/          # Scratch directory for FFmpeg intermediate filter passes
└── data/
    └── clipsly.db     # SQLite 3 database file
```

- **Storage Thresholds:** The app monitors disk space via `shutil.disk_usage`. Prevents new uploads if free SSD space is $<10\text{ GB}$.
- **Retention & Cleanup:** User can purge intermediate audio, clips, and uploads from the settings page with a single click, keeping only final exports and metadata.

---

## 22. Error Handling Requirements

- **Corrupt / Unreadable Video:** If `ffprobe` fails to read container or finds no valid video/audio streams, immediately mark job as `FAILED`, display a descriptive error toast in the UI, and unlink the temporary upload file.
- **CUDA / VRAM Out-Of-Memory (OOM):** If Faster-Whisper or NVENC throws a CUDA OOM error:
  1. Release all GPU memory caches (`torch.cuda.empty_cache()` if PyTorch loaded, or CTranslate2 memory release).
  2. Fall back automatically to CPU execution (`device="cpu"`, `compute_type="int8"` for Whisper, `libx264` for FFmpeg).
  3. Notify user with an informational badge: *"GPU memory full; completed using CPU."*
- **FFmpeg Subprocess Hangs:** All FFmpeg execution threads are monitored by an asynchronous watchdog with a 10-minute timeout. If exceeded, the subprocess is killed gracefully, temporary files unlinked, and the job flagged as `TIMED_OUT`.
- **Database Concurrency:** SQLite configured with WAL (Write-Ahead Logging) mode and a 30-second busy timeout to prevent "database locked" errors during concurrent pipeline updates.

---

## 23. Hardware Limitations

The target execution machine is an **ASUS TUF A15 Laptop**:
- **Processor (CPU):** AMD Ryzen 7 7000 Series (8 Cores, 16 Threads) — Excellent multi-core performance for CPU fallback and audio processing.
- **Discrete GPU:** NVIDIA GeForce RTX 3050 Laptop GPU.
- **VRAM Capacity:** **4 GB GDDR6.**
- **System RAM:** 16 GB DDR5 (typical TUF A15 configuration).
- **Storage:** NVMe PCIe SSD.

### Hardware Budget Strategy:
The 4GB VRAM ceiling is the most critical constraint of the system. Windows OS Desktop Window Manager (DWM) and display drivers permanently consume ~400MB–600MB of VRAM, leaving approximately **3.4 GB of usable VRAM**.

| Component | VRAM Budget | Model & Compute Mode | Strategy |
|---|---|---|---|
| **Faster-Whisper** | ~500 MB – 1.2 GB | `small` or `base` (`float16`) | Loaded during transcription, unloaded immediately after |
| **Highlight AI (LLM)** | ~1.5 GB – 2.0 GB | Quantized 3B (Q4_K_M) or Heuristic | Evaluated sequentially; never co-loaded with Whisper |
| **FFmpeg NVENC** | ~350 MB – 600 MB | `h264_nvenc` hardware session | Session created per render, closed immediately |
| **System Headroom** | ~800 MB | Windows OS, Chrome/Edge GPU rendering | Mandatory safety cushion to prevent driver TDR reset |

*Golden Rule:* **Sequential Execution.** Never attempt to run Whisper transcription, LLM highlight extraction, and NVENC video encoding concurrently. Each stage runs as an isolated step in the job queue.

---

## 24. Privacy and Security Requirements

- **Local Host Binding:** Backend server binds explicitly to `127.0.0.1:8000` (not `0.0.0.0`), preventing local area network (LAN) access unless explicitly configured by the user.
- **Zero Cloud Leakage:** All processing is performed strictly offline. No audio, video, or transcripts are sent to third-party endpoints.
- **Path Sanitization:** User-provided file names are sanitized using regex (`[^a-zA-Z0-9_\-\.]`) and assigned UUID prefixes to eliminate path traversal vulnerabilities (`../../`).
- **CORS Configuration:** Frontend origins strictly restricted to `http://localhost:5173` (Vite dev) and `http://127.0.0.1:8000` (production bundle).

---

## 25. Performance Expectations

- **Ingestion & Validation:** $< 3\text{ seconds}$ for a 1-hour 1080p MP4 file.
- **Audio Extraction:** $< 15\text{ seconds}$ for a 1-hour video file via FFmpeg stream copy / fast PCM resample.
- **Whisper Transcription (`small` model, RTX 3050):** Real-Time Factor (RTF) $\approx 0.10\times$ to $0.15\times$ (approx. 6 to 9 minutes for a 60-minute video).
- **Highlight Detection (Heuristic Engine):** $< 5\text{ seconds}$ across a 60-minute transcript.
- **Clip Cutting & 9:16 Blur-Pad Composition:** $\approx 0.4\times$ real-time using NVENC (approx. 12 seconds to render a 30-second clip).
- **End-to-End Pipeline:** From upload to 5 proposed, ready-to-preview vertical clips: $< 12\text{ minutes}$ for a 60-minute raw video.

---

## 26. Known Limitations

1. **VRAM Concurrency Limit:** The system cannot process multiple video files concurrently on the GPU without risking memory exhaustion. Video jobs are strictly queued sequentially.
2. **Heavy LLM Incompatibility:** Large Language Models $\ge 7\text{B}$ parameters cannot run locally alongside the desktop UI and NVENC encoder on a 4GB VRAM GPU. Local AI is constrained to $\le 3\text{B}$ quantized models or CPU execution.
3. **Complex Visual Scene Analysis:** Phase 01–Phase 14 highlight detection is driven primarily by audio and transcript discourse rather than computer vision / facial emotion tracking.
4. **Variable Frame Rate (VFR) Video:** Phone recordings with VFR may experience minor audio desync if not normalized during ingestion. The pipeline includes an FFmpeg filter to standardize to Constant Frame Rate (CFR).

---

## 27. Out-of-Scope Features

The following features are intentionally **excluded** from the MVP / initial releases to maintain sharp focus on core value and local performance:

- ❌ **YouTube / Twitch / TikTok URL Downloaders:** Adding `yt-dlp` creates ongoing maintenance overhead due to platform anti-bot changes, legal ambiguity, and rate-limiting. Local files only.
- ❌ **Multi-User Accounts & Authentication:** The app is a single-user local tool. User login, passwords, session management, and multi-tenant isolation are unnecessary overhead.
- ❌ **Cloud Storage Integrations (AWS S3, Google Drive):** All storage is local SSD.
- ❌ **Social Media Direct Auto-Posting APIs:** Meta Graph API, TikTok API, and YouTube Data API require developer business verification, OAuth refresh token rotation, and privacy audits.
- ❌ **Paid Subscriptions / Paywalls / Stripe Integration:** Completely free, open-source personal software.
- ❌ **Multi-Speaker Face-Tracking Motion Crop (v1):** Dynamic keyframed camera movement tracking speakers across widescreen shots is reserved for post-v1 updates.

---

## 28. Acceptance Criteria

The system is considered functionally complete when the following criteria are validated on the target ASUS TUF A15 machine:

1. **End-to-End Execution:** A 30-minute 1080p MP4 file can be uploaded, transcribed with Faster-Whisper, analyzed for highlights, reframed to 9:16 with animated subtitles, edited in the studio, and exported as a valid 1080x1920 MP4 file without manual CLI intervention.
2. **Hardware Stability:** Peak GPU VRAM during the entire pipeline does not exceed 3.5GB; zero CUDA OOM crashes occur.
3. **Accurate Word Sync:** Exported MP4 subtitles synchronize precisely with spoken audio (word highlight corresponds to audible utterance within $\pm 100\text{ms}$).
4. **Export Integrity:** Rendered MP4 plays smoothly in standard media players (VLC, Windows Media Player) and mobile platforms without audio desynchronization or visual artifacts.
5. **Data Persistence:** Closing and restarting the application retains all ingested videos, transcripts, highlight scores, and custom clip edits in SQLite.

---

## 29. Future Improvements (Roadmap Post-Phase 20)

- **F-1: Active Speaker Face Tracking:** Utilize lightweight MediaPipe Face Mesh on CPU/GPU to dynamically center the active speaker during 9:16 cropping.
- **F-2: Multi-Speaker Split-Screen:** Automatically generate stacked vertical layouts (top speaker, bottom speaker) for interview-style podcasts.
- **F-3: Automatic B-Roll & Visual Bumps:** Insert subtle zoom-ins, screen shakes, sound effects, or relevant local overlay images at high-energy punctuation marks.
- **F-4: Local Folder Watchdog:** Automatically ingest and process new recordings dropped into a designated local OBS/recording folder.
- **F-5: Custom Fine-Tuned Highlight Models:** Support user fine-tuning on high-performing clips to personalize highlight scoring to individual creator niches.

---

## 30. Complete 20-Phase Development Plan

Below is the definitive development roadmap for the entire project lifecycle. Each phase defines its objective, scope, deliverables, dependencies, and completion criteria.

### Phase 01: Complete Project Documentation & PRD (CURRENT)
- **Objective:** Establish the comprehensive architectural blueprint, product requirements, user workflow, and documentation suite.
- **Scope:** Author all 15 documentation files in `docs/`, with complete depth in `01-PRD.md` and indexed in `07-README.md`.
- **Expected Deliverables:** 15 structured Markdown documents in `docs/` detailing all facets of the application.
- **Dependencies:** None.
- **Completion Criteria:** All 29 PRD sections complete, 20 phases documented, 15 files verified, zero unapproved architectural assumptions.

### Phase 02: System Architecture & Hardware Strategy
- **Objective:** Finalize component architecture, inter-process communication, and VRAM management strategies for the 4GB RTX 3050.
- **Scope:** Define data flow between Vite frontend, FastAPI backend, FFmpeg worker, and Faster-Whisper; map memory budgets and sequential model execution.
- **Expected Deliverables:** Complete `03-ARCHITECTURE.md` with sequence diagrams, VRAM allocation charts, and process boundary definitions.
- **Dependencies:** Phase 01 approval.
- **Completion Criteria:** Memory budget verified under 3.5GB VRAM; process isolation strategy approved.

### Phase 03: Database Schema & Local Storage Engine
- **Objective:** Design and document the SQLite relational data model and local directory storage architecture.
- **Scope:** Define tables for `videos`, `transcripts`, `utterances`, `highlights`, `clips`, `export_jobs`, and `settings`; define migration and storage cleanup strategies.
- **Expected Deliverables:** Complete `04-DATABASE.md` with DDL schemas, ER diagrams, indices, and filesystem organization rules.
- **Dependencies:** Phase 02.
- **Completion Criteria:** Schema accommodates full word-level timestamp storage and clip versioning; WAL mode and timeout policies specified.

### Phase 04: Backend Foundation & FastAPI Scaffolding
- **Objective:** Scaffold the Python FastAPI backend with structured routing, dependency injection, and health monitoring.
- **Scope:** Initialize project structure, Poetry/uv configuration, CORS middleware, global exception handlers, and basic ping/health endpoints.
- **Expected Deliverables:** Running FastAPI server on `127.0.0.1:8000`, API documentation (`/docs`), modular folder structure.
- **Dependencies:** Phase 03.
- **Completion Criteria:** Server boots cleanly, passes health checks, and connects reliably to SQLite database.

### Phase 05: Frontend Foundation & shadcn/ui Design System
- **Objective:** Scaffold the React + Vite + TypeScript frontend with Tailwind CSS and shadcn/ui components.
- **Scope:** Set up Vite, Tailwind configuration, dark-mode color tokens, Lucide icons, base layout shell, navigation bar, and state management.
- **Expected Deliverables:** Running frontend at `http://localhost:5173`, responsive dashboard shell, accessible UI primitives.
- **Dependencies:** Phase 04.
- **Completion Criteria:** Clean component build with zero TypeScript errors; dark theme matching video editing workstation aesthetic.

### Phase 06: Local Video Upload & Ingestion Pipeline
- **Objective:** Implement robust local video file ingestion with drag-and-drop support, chunked streaming, and storage persistence.
- **Scope:** Frontend file uploader with progress tracking; FastAPI streaming endpoint saving to `/storage/uploads/`; file sanitization.
- **Expected Deliverables:** Working drag-and-drop UI, upload API endpoint, file persistence verification.
- **Dependencies:** Phase 05.
- **Completion Criteria:** 2GB+ video files upload cleanly to local SSD without buffering into system RAM; progress bar accurate to $\pm 1\%$.

### Phase 07: Audio Extraction & Media Metadata Pipeline
- **Objective:** Integrate `ffprobe` for technical metadata inspection and `ffmpeg` for high-speed 16kHz WAV audio extraction.
- **Scope:** Subprocess wrapper for `ffprobe` and `ffmpeg`; extraction of duration, codecs, FPS, bitrate; audio conversion to mono 16kHz WAV.
- **Expected Deliverables:** `MediaInspector` and `AudioExtractor` backend services; database metadata population.
- **Dependencies:** Phase 06.
- **Completion Criteria:** 60-minute video extracts to 16kHz WAV in $< 20\text{ seconds}$; technical metadata populated in SQLite.

### Phase 08: Faster-Whisper Transcription Engine
- **Objective:** Implement GPU-accelerated speech-to-text transcription with word-level timestamps using Faster-Whisper.
- **Scope:** Service wrapper managing Faster-Whisper model loading/unloading, Silero VAD filtering, CUDA execution, and CPU fallback.
- **Expected Deliverables:** `TranscriptionService` generating word-level timestamped tokens; background task worker.
- **Dependencies:** Phase 07.
- **Completion Criteria:** 10-minute test audio transcribes on RTX 3050 in $< 60\text{ seconds}$ with word-level timing precision; zero VRAM leaks.

### Phase 09: Transcript Management & Interactive Review UI
- **Objective:** Persist transcript data in SQLite and build an interactive in-browser transcript viewer.
- **Scope:** Database relational mapping of segments and words; frontend transcript component with search, word clicking to seek video, and text editing.
- **Expected Deliverables:** Fully interactive transcript UI synced bidirectionally with HTML5 video player.
- **Dependencies:** Phase 08.
- **Completion Criteria:** Clicking any word in the transcript seeks the video player to that exact millisecond; inline edits persist to database.

### Phase 10: AI Highlight Detection & Scoring Engine
- **Objective:** Implement the highlight detection algorithm to identify engaging segments within user-specified duration targets.
- **Scope:** Algorithmic scoring evaluating hook quality, topic closure, speech pacing, and sentiment; ranking and selection of top candidates.
- **Expected Deliverables:** `HighlightEngine` service producing scored candidate segments with rationale and confidence metrics.
- **Dependencies:** Phase 09.
- **Completion Criteria:** System proposes 3–10 distinct, non-overlapping candidate highlights from a 30-minute transcript within 5 seconds.

### Phase 11: Candidate Selection & Clip Timestamp Generator
- **Objective:** Refine candidate highlight boundaries by snapping to natural speech pauses and adding protective padding.
- **Scope:** Boundary adjustment logic; pre-roll (0.5s) and post-roll (0.5s) padding; duration filtering (15–30s, 30–60s, 60–90s); candidate review UI cards.
- **Expected Deliverables:** Candidate highlight cards in UI showing title, duration, score badge, and preview button.
- **Dependencies:** Phase 10.
- **Completion Criteria:** All generated clips start and end cleanly between words without cutting off syllables or mid-sentence dialogue.

### Phase 12: FFmpeg Cutting & Clip Generation Engine
- **Objective:** Implement fast, sample-accurate video cutting using FFmpeg subprocess execution.
- **Scope:** Python service generating precise sub-clips from source video based on validated start/end timestamps; keyframe handling.
- **Expected Deliverables:** `VideoCutter` service producing standalone MP4 video clips saved in `/storage/clips/`.
- **Dependencies:** Phase 11.
- **Completion Criteria:** Sliced clips have zero audio-video drift; cutting operation completes in $< 5\text{ seconds}$ per clip.

### Phase 13: Vertical 9:16 Re-Framing Engine (Crop & Blur-Fill)
- **Objective:** Implement FFmpeg complex filtergraphs to transform horizontal 16:9 video into 1080x1920 vertical format.
- **Scope:** Implement blurred background pillarbox filter graph and center-crop filter graph; aspect ratio scaling.
- **Expected Deliverables:** `VerticalReframer` service producing 1080x1920 canvas MP4 files.
- **Dependencies:** Phase 12.
- **Completion Criteria:** Output video strictly measures 1080x1920 pixels; blurred background renders smoothly without visible banding or stutter.

### Phase 14: Subtitle Generation & Karaoke Styler (.ass / burned-in)
- **Objective:** Build an ASS subtitle generator that creates animated word-by-word karaoke captions burned into the video.
- **Scope:** Generation of `.ass` scripts with `\k` karaoke timing; style configuration (fonts, colors, strokes, position); FFmpeg `libass` integration.
- **Expected Deliverables:** `SubtitleGenerator` service and burning filtergraph; preset styling templates.
- **Dependencies:** Phase 13.
- **Completion Criteria:** Subtitles render on vertical video with accurate word-level color illumination matching speech within $\pm 100\text{ms}$.

### Phase 15: Interactive Clip Studio (Preview & Fine Trimming)
- **Objective:** Build the interactive web studio for fine-tuning clip boundaries, editing subtitles, and styling previews in real time.
- **Scope:** Dual-handle timeline range slider, live subtitle preview overlay, style control panel (color pickers, font selectors), and instant playback.
- **Expected Deliverables:** Complete Studio page (`/studio/:clipId`) with intuitive controls and real-time visual feedback.
- **Dependencies:** Phase 14.
- **Completion Criteria:** Dragging trim handles updates preview instantly; subtitle text and styling edits reflect live without re-rendering.

### Phase 16: Video Export & NVENC Hardware Acceleration
- **Objective:** Implement high-speed final export pipeline leveraging NVIDIA NVENC hardware acceleration with CPU fallback.
- **Scope:** FFmpeg `h264_nvenc` encoding optimization; progress tracking; final MP4 assembly; browser download and file reveal triggers.
- **Expected Deliverables:** `ExportManager` service, progress modal in UI, downloadable production-ready MP4.
- **Dependencies:** Phase 15.
- **Completion Criteria:** 30-second 1080x1920 clip with burned karaoke subtitles renders in $< 20\text{ seconds}$ via NVENC; file downloads cleanly.

### Phase 17: Job Queue & Background Task Management
- **Objective:** Implement an asynchronous local job queue to orchestrate multi-step pipeline tasks with progress reporting.
- **Scope:** SQLite-backed job queue worker; Server-Sent Events (SSE) or WebSocket progress streaming to frontend; cancellation and retry logic.
- **Expected Deliverables:** `JobWorker` queue, real-time UI progress bars, task state persistence across app reloads.
- **Dependencies:** Phase 16.
- **Completion Criteria:** User can initiate long tasks and observe smooth real-time progress percentages; app recovery resumes or cleanly fails interrupted tasks.

### Phase 18: System Health, VRAM Watchdog & Error Recovery
- **Objective:** Build system monitoring services to track GPU VRAM, CPU utilization, and disk space to prevent hardware crashes.
- **Scope:** Hardware watchdog checking NVML / `nvidia-smi` and system disk space; automatic fallback triggers; user warning toasts.
- **Expected Deliverables:** `SystemMonitor` service, UI hardware telemetry badge, automated CPU fallback handlers.
- **Dependencies:** Phase 17.
- **Completion Criteria:** Low VRAM ($< 500\text{MB}$ free) safely redirects tasks to CPU; disk space warnings trigger when SSD space $< 15\text{GB}$.

### Phase 19: End-to-End Testing & Performance Profiling
- **Objective:** Execute comprehensive unit, integration, and end-to-end performance tests across varied video formats and durations.
- **Scope:** Pytest test suite for backend; Vitest/Playwright tests for frontend; benchmarking RTF, render times, and peak VRAM across sample test videos.
- **Expected Deliverables:** Test suites, automated test runner scripts, and a verified Performance Benchmark Report.
- **Dependencies:** Phase 18.
- **Completion Criteria:** $>85\%$ test coverage on core media services; all acceptance criteria validated on ASUS TUF A15 hardware.

### Phase 20: Packaging, Documentation Finalization & Release
- **Objective:** Package the application for simple local startup and finalize all user and developer documentation.
- **Scope:** One-click launcher script (`run.bat` / PowerShell), updated setup instructions, complete `07-README.md`, and clean Git release tag.
- **Expected Deliverables:** Zero-friction desktop launcher script, release notes, production build verification.
- **Dependencies:** Phase 19.
- **Completion Criteria:** Fresh machine clone starts with a single command and processes a sample video successfully without manual configuration.

---

## 31. Open Questions & Architectural Proposals (Under Evaluation)

To ensure no unapproved assumptions are made, the following architectural options are documented for evaluation in **Phase 02**:

1. **Highlight Detection Model Selection:**
   - *Option A (Pure Heuristic):* Fast, zero VRAM overhead, deterministic, but lacks nuanced semantic understanding of humor or irony.
   - *Option B (Local 3B LLM via Ollama/llama.cpp):* High semantic quality, but consumes ~1.8GB VRAM and requires sequential unloading before NVENC export.
   - *Option C (Hybrid + Optional API Fallback):* Pure heuristic as default; optional user-provided Gemini/OpenAI API key for advanced semantic scoring.
   - *Status:* To be benchmarked and decided in Phase 02 / Phase 10.
2. **Frontend Video Preview Strategy for Trimming:**
   - *Option A:* Browser renders raw video via HTML5 player with JavaScript-based subtitle overlay and CSS 9:16 masking (Instant preview, zero render wait).
   - *Option B:* Backend renders a fast, low-resolution 480p proxy vertical clip for preview (Accurate burn-in preview, but adds 3–5s render wait).
   - *Status:* Option A strongly proposed for rapid interactive responsiveness; to be finalized in Phase 02.
3. **Database ORM Selection:**
   - *Option A:* SQLAlchemy 2.0 with AsyncSession + Alembic migrations.
   - *Option B:* SQLModel (combines Pydantic and SQLAlchemy for seamless FastAPI schema integration).
   - *Status:* SQLModel proposed for clean schema sharing; to be evaluated in Phase 03.
