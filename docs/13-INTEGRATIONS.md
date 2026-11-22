# Subprocess & Library Integrations

**Project Name:** AI Video Clipper (Working Title: Clipsly)  
**Document Version:** 1.0.0  
**Status:** ARCHITECTURALLY FINALIZED (Phase 02 Baseline; Implementation Across Phases 06–16)  
**Author:** Senior Software Architect & Systems Integration Engineer  
**Target Hardware:** ASUS TUF A15 (AMD Ryzen 7 7000 Series, NVIDIA RTX 3050 Laptop GPU, 4GB VRAM)  

---

## 1. Purpose of this Document

This document defines the technical integration contracts, subprocess invocation protocols, CLI flags, memory lifecycle management, and library bindings for external tools and AI engines utilized by Clipsly.

The core system coordinates four foundational external technologies:
1. **FFprobe:** Low-latency media container probing and stream metadata extraction.
2. **FFmpeg:** High-speed audio extraction, sample-accurate video cutting, 9:16 vertical complex filtergraphs (`boxblur`), subtitle burning (`libass`), and hardware-accelerated encoding (`h264_nvenc`).
3. **Faster-Whisper (CTranslate2):** GPU-accelerated speech-to-text inference with Silero VAD.
4. **NVIDIA Driver / CUDA / NVML:** GPU memory monitoring and hardware session management.

---

## 2. Integration Catalog & Contracts

### 2.1 FFprobe (Media Metadata Extraction)
- **Invocation:** Subprocess via `asyncio.create_subprocess_exec` using structured argument arrays (no `shell=True`).
- **Command Structure:**
  ```powershell
  ffprobe -v quiet -print_format json -show_format -show_streams input_video.mp4
  ```
- **Output Contract:** Parsed JSON object yielding container duration, stream bitrates, video dimensions ($W \times H$), pixel aspect ratio, FPS, audio sample rate, and channel count.

### 2.2 FFmpeg Audio Extraction Pipeline
- **Command Structure:**
  ```powershell
  ffmpeg -y -i input_video.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 output_audio.wav
  ```
- **Rationale:** Faster-Whisper operates with peak efficiency and lowest memory overhead on 16kHz mono 16-bit PCM WAV. Extraction executes via CPU in $< 15\text{ seconds}$ for a 1-hour file.

### 2.3 FFmpeg 9:16 Vertical Blur-Pad Filtergraph with NVENC
- **Hardware Strategy:** Software decoding on the 8-core AMD Ryzen 7 7000 Series CPU feeds frames to the FFmpeg filtergraph, which outputs directly to the hardware NVENC encoder chip (`h264_nvenc`). This avoids CUDA filter memory allocation bugs while keeping VRAM usage under 600MB.
- **Filtergraph Formula:**
  ```powershell
  ffmpeg -y -ss {start_s} -to {end_s} -i input.mp4 -filter_complex "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];[0:v]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[v]" -map "[v]" -map 0:a -c:v h264_nvenc -preset p4 -cq 23 -c:a aac -b:a 192k output_vertical.mp4
  ```

### 2.4 FFmpeg Subtitle Burn-in (libass)
- **Filter Syntax:** `-vf "ass=subtitles.ass"`
- **Hardware Coordination:** Subtitle rasterization occurs via `libass` in CPU memory during filtergraph composition before frames are encoded by `h264_nvenc`.

### 2.5 Faster-Whisper Integration Contract (CTranslate2)
- **Python Package:** `faster-whisper`
- **Instantiation Contract:**
  ```python
  from faster_whisper import WhisperModel
  model = WhisperModel(
      model_size_or_path="small",  # Default model for 4GB RTX 3050
      device="cuda",
      compute_type="float16",       # or "int8_float16" for strict memory capping
      vad_filter=True,
      vad_parameters=dict(min_silence_duration_ms=500)
  )
  ```
- **Lifecycle & Memory Rule (ADR-002 & ADR-006):**
  1. Faster-Whisper runs inside an isolated execution routine.
  2. Following transcription, the model reference is explicitly deleted (`del model`).
  3. Python garbage collection (`gc.collect()`) is called to immediately release CTranslate2/CUDA memory buffers.
  4. Only after VRAM returns to baseline does the job queue proceed to video rendering.

---

## 3. Confirmed Architectural Integration Summary

| Dependency | Purpose | Mode / Driver | Status (ADR) |
|---|---|---|---|
| **FFmpeg 6.0+** | Video processing, filtergraphs & NVENC export | Subprocess array (No `shell=True`) | **CONFIRMED (ADR-006)** |
| **FFprobe** | Technical container metadata inspection | Subprocess array | **CONFIRMED (ADR-006)** |
| **Faster-Whisper** | Speech-to-text with word timestamps | CTranslate2 / CUDA (VRAM isolated) | **CONFIRMED (ADR-002)** |
| **Silero VAD** | Voice activity silence filtering | Integrated in Faster-Whisper | **CONFIRMED** |
| **Heuristic Highlight Engine** | Deterministic hook, pacing, and boundary scoring | Python CPU service (0 MB VRAM) | **CONFIRMED (ADR-003)** |
| **External LLM APIs (Optional)**| Semantic highlight ranking (Gemini/OpenAI) | HTTPS / TLS client (0 MB VRAM) | **CONFIRMED (ADR-003)** |
| **SQLite-Backed Asyncio Queue** | Long-running task orchestration & persistence | In-process queue + SQLite WAL | **CONFIRMED (ADR-001)** |

---

## 4. Current Status & Next Steps

- **Status:** ARCHITECTURALLY FINALIZED.
- **Dependencies:** Backend Scaffolding (Phase 04).
- **Execution Target:** Progressively implemented across **Phases 06 through 16**.
