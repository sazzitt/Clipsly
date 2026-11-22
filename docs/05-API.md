# FastAPI REST API Specification & Contracts

**Project Name:** AI Video Clipper (Working Title: Clipsly)  
**Document Version:** 1.0.0  
**Status:** APPROVED & FINALIZED (Phase 04 Specification Baseline)  
**Author:** Senior Backend Architect & REST API Designer  
**API Prefix:** `/api/v1`  
**Host Binding:** `127.0.0.1:8000` (Localhost loopback only)  

---

## 1. Executive Summary & Design Standards

This document establishes the definitive REST API contracts, Pydantic v2 schemas, endpoint catalog, Server-Sent Events (SSE) protocol, and error envelopes governing all communication between the React frontend and the FastAPI backend.

### 1.1 Architectural Standards
- **RESTful Resource Model:** Nouns in plural kebab-case (`/api/v1/videos`, `/api/v1/processing-jobs`, `/api/v1/clips`).
- **HTTP Methods:**
  - `GET`: Safe, idempotent retrieval. Supports HTTP 206 Partial Content for media streaming.
  - `POST`: Creation of entities and dispatching of background jobs.
  - `PATCH`: Partial updates to entities (e.g., trim timestamps, subtitle styling).
  - `DELETE`: Idempotent removal of entities.
- **Strict Typing:** All request bodies and response payloads are strictly validated using Pydantic v2 models.
- **Localhost Loopback Only:** Server binds exclusively to `127.0.0.1:8000`. External network interfaces are rejected.
- **Standardized Timecodes:** All media offsets are represented as non-negative integer milliseconds (`INTEGER start_ms`, `INTEGER end_ms`).

---

## 2. Standard Request & Response Envelopes

### 2.1 Standard Paginated Response Envelope
For listing endpoints (`GET /api/v1/videos`, `GET /api/v1/exports`), results follow this envelope:

```json
{
  "items": [],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

### 2.2 Standard Error Response Envelope
Every non-2xx HTTP response adheres strictly to this format:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Video with id 'a1b2c3d4-e5f6-7890-abcd-ef1234567890' was not found.",
    "details": null
  }
}
```

#### Standard Error Code Catalog:
- `VALIDATION_ERROR` (422): Input payload failed Pydantic schema validation.
- `RESOURCE_NOT_FOUND` (404): Target database record does not exist.
- `INVALID_FILE_FORMAT` (400): Uploaded container is not supported or corrupted.
- `INSUFFICIENT_STORAGE` (507): Free SSD space is below safety threshold ($< 10\text{ GB}$).
- `JOB_ALREADY_RUNNING` (409): Another heavy GPU pipeline task is active (ADR-002).
- `PROCESS_TIMEOUT` (504): Background FFmpeg subprocess exceeded 10-minute watchdog.
- `CUDA_OUT_OF_MEMORY` (503): GPU memory exhausted; automatic fallback triggered.

---

## 3. Complete Endpoint Catalog (40 Endpoints)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Catalog by Module                               │
├──────────────────────────────┬─────────────┬───────────────────────────┤
│ Module                       │ Count       │ Routes                    │
├──────────────────────────────┼─────────────┼───────────────────────────┤
│ A. Application & System      │ 5 Endpoints │ `/system/*`               │
│ B. Videos & Media Streaming  │ 5 Endpoints │ `/videos/*`               │
│ C. Processing Jobs & Queue   │ 6 Endpoints │ `/jobs/*`, `/system/events│
│ D. Speech Transcription      │ 4 Endpoints │ `/transcripts/*`          │
│ E. Highlight Detection       │ 4 Endpoints │ `/highlights/*`           │
│ F. Interactive Clips & Studio│ 6 Endpoints │ `/clips/*`                │
│ G. Export & NVENC Rendering  │ 6 Endpoints │ `/exports/*`              │
│ H. Storage & Maintenance     │ 4 Endpoints │ `/storage/*`              │
├──────────────────────────────┼─────────────┼───────────────────────────┤
│ Total Endpoints Documented   │ 40          │ All `/api/v1` routes      │
└──────────────────────────────┴─────────────┴───────────────────────────┘
```

---

## 4. Module A: Application & System Endpoints

### 4.1 `GET /api/v1/system/health`
- **Purpose:** Verifies backend availability, database connection, and CUDA/NVENC status.
- **Request Parameters:** None.
- **Response Status:** `200 OK`.
- **Response Schema (`SystemHealthResponse`):**
  ```json
  {
    "status": "healthy",
    "version": "1.0.0",
    "database_connected": true,
    "cuda_available": true,
    "nvenc_available": true,
    "active_jobs_count": 0,
    "uptime_seconds": 1420.5
  }
  ```

### 4.2 `GET /api/v1/system/info`
- **Purpose:** Returns host hardware specs and platform configurations.
- **Response Status:** `200 OK`.
- **Response Schema (`SystemInfoResponse`):**
  ```json
  {
    "os": "Windows 11",
    "cpu": "AMD Ryzen 7 7000 Series (16 Threads)",
    "gpu": "NVIDIA GeForce RTX 3050 Laptop GPU",
    "vram_total_mb": 4096,
    "python_version": "3.11.8",
    "ffmpeg_version": "7.0-full_build"
  }
  ```

### 4.3 `GET /api/v1/system/hardware`
- **Purpose:** Real-time hardware telemetry for the frontend UI resource badge.
- **Response Status:** `200 OK`.
- **Response Schema (`HardwareTelemetryResponse`):**
  ```json
  {
    "gpu_vram_used_mb": 940,
    "gpu_vram_total_mb": 4096,
    "gpu_vram_free_mb": 3156,
    "gpu_utilization_percent": 12.0,
    "cpu_load_percent": 18.5,
    "system_ram_used_gb": 7.2,
    "system_ram_total_gb": 16.0,
    "ssd_free_space_gb": 128.4
  }
  ```

### 4.4 `GET /api/v1/system/settings`
- **Purpose:** Retrieves all user preferences from `application_settings`.
- **Response Status:** `200 OK`.
- **Response Schema (`SettingsListResponse`):**
  ```json
  {
    "settings": {
      "transcription.default_model": "small",
      "transcription.compute_type": "float16",
      "highlight.min_duration_s": 30,
      "highlight.max_duration_s": 60,
      "highlight.external_api_key": "sk-...masked",
      "export.default_encoder": "h264_nvenc",
      "export.nvenc_preset": "p4",
      "storage.min_free_space_gb": 10,
      "storage.retain_intermediate_clips": false
    }
  }
  ```

### 4.5 `PATCH /api/v1/system/settings`
- **Purpose:** Updates one or more key-value configuration settings.
- **Request Body (`SettingsUpdateRequest`):**
  ```json
  {
    "settings": {
      "transcription.default_model": "base",
      "highlight.external_api_key": "AIzaSyD-new-key"
    }
  }
  ```
- **Response Status:** `200 OK`.

---

## 5. Module B: Videos & Media Streaming

### 5.1 `POST /api/v1/videos/upload`
- **Purpose:** Uploads a local horizontal video file via multipart stream.
- **Request Format:** `multipart/form-data`.
- **Form Fields:** `file: UploadFile` (Binary stream).
- **Validation Rules:**
  - Allowed extensions: `.mp4`, `.mkv`, `.mov`, `.webm`.
  - Max file size: 10 GB.
  - Disk free space must be $\ge 10\text{ GB}$.
  - Must contain valid video and audio streams verified by `ffprobe`.
- **Response Status:** `201 Created`.
- **Response Schema (`VideoUploadResponse`):**
  ```json
  {
    "id": "e4b2d188-7f3c-4a3a-96e7-8b0108ec73d4",
    "filename": "e4b2d188-7f3c-4a3a-96e7-8b0108ec73d4.mp4",
    "original_filename": "Tech_Interview_Episode_12.mp4",
    "file_size_bytes": 1048576000,
    "duration_seconds": 1824.5,
    "width": 1920,
    "height": 1080,
    "fps": 30.0,
    "video_codec": "h264",
    "audio_codec": "aac",
    "status": "READY",
    "created_at": "2026-11-22T13:40:00Z"
  }
  ```
- **Errors:** `400 Bad Request` (Invalid container), `507 Insufficient Storage`.

### 5.2 `GET /api/v1/videos`
- **Purpose:** Lists all ingested videos with pagination and status filtering.
- **Query Parameters:**
  - `limit`: `int` (default 20, max 100).
  - `offset`: `int` (default 0).
  - `status`: `string | null` (e.g., `READY`, `PROCESSING`).
- **Response Status:** `200 OK`.
- **Response Schema:** Standard paginated envelope with `items: list[VideoSummary]`.

### 5.3 `GET /api/v1/videos/{video_id}`
- **Purpose:** Returns comprehensive technical stream metadata and pipeline status for a video.
- **Response Status:** `200 OK`.
- **Errors:** `404 Not Found`.

### 5.4 `GET /api/v1/videos/{video_id}/stream`
- **Purpose:** Low-latency video streaming supporting HTTP Range headers (`206 Partial Content`) for browser scrubbing.
- **Headers Handled:** `Range: bytes=0-1048575`.
- **Response Status:** `206 Partial Content` (or `200 OK` if full stream requested).
- **Headers Returned:**
  - `Content-Range: bytes 0-1048575/1048576000`
  - `Accept-Ranges: bytes`
  - `Content-Type: video/mp4`

### 5.5 `DELETE /api/v1/videos/{video_id}`
- **Purpose:** Deletes video metadata and intermediate files (`storage/audio/`, `storage/clips/`, `storage/transcripts/`).
- **Query Parameter:** `delete_exports: bool = false` (Defaults to preserving rendered MP4s in `storage/exports/` per ADR-008).
- **Response Status:** `204 No Content`.

---

## 6. Module C: Processing Jobs & Queue Management

### 6.1 `POST /api/v1/videos/{video_id}/jobs`
- **Purpose:** Enqueues an asynchronous video pipeline job.
- **Request Body (`JobCreateRequest`):**
  ```json
  {
    "job_type": "FULL_PIPELINE",
    "transcription_model": "small",
    "spoken_language": "en",
    "min_clip_duration_s": 30,
    "max_clip_duration_s": 60
  }
  ```
- **Response Status:** `202 Accepted`.
- **Response Schema (`JobResponse`):**
  ```json
  {
    "id": "7b8e1a3c-5c8e-4b2a-bf34-9e8a7d6c5b4a",
    "video_id": "e4b2d188-7f3c-4a3a-96e7-8b0108ec73d4",
    "job_type": "FULL_PIPELINE",
    "status": "QUEUED",
    "progress_percent": 0.0,
    "current_step": "Job enqueued",
    "created_at": "2026-11-22T13:40:05Z"
  }
  ```

### 6.2 `GET /api/v1/videos/{video_id}/jobs`
- **Purpose:** Lists all historical and active jobs associated with a video.
- **Response Status:** `200 OK`.

### 6.3 `GET /api/v1/jobs/{job_id}`
- **Purpose:** Retrieves real-time execution status, current progress step, and error logs.
- **Response Status:** `200 OK`.

### 6.4 `POST /api/v1/jobs/{job_id}/cancel`
- **Purpose:** Cancels an active job, signals `SIGTERM` to the active FFmpeg/Whisper subprocess, and unlinks scratch files.
- **Response Status:** `200 OK`.
- **Response Schema:** `{ "status": "CANCELLED", "job_id": "..." }`.

### 6.5 `POST /api/v1/jobs/{job_id}/retry`
- **Purpose:** Retries an `INTERRUPTED` or `FAILED` job from the beginning.
- **Response Status:** `202 Accepted`.

### 6.6 `GET /api/v1/system/events` (Server-Sent Events)
- **Purpose:** Real-time push stream broadcasting pipeline progress and hardware telemetry to the frontend.
- **Content-Type:** `text/event-stream`.
- **SSE Event Protocol Specification:**

```
event: job_progress
data: {"job_id":"7b8e1a3c...","video_id":"e4b2d188...","step":"TRANSCRIBING","progress":45.0,"message":"Transcribing speech with Faster-Whisper (CUDA)"}

event: job_completed
data: {"job_id":"7b8e1a3c...","video_id":"e4b2d188...","status":"COMPLETED","total_highlights":8}

event: job_failed
data: {"job_id":"7b8e1a3c...","video_id":"e4b2d188...","error_code":"CUDA_OUT_OF_MEMORY","message":"Fell back to CPU"}

event: hardware_telemetry
data: {"gpu_vram_used_mb":1120,"gpu_vram_free_mb":2976,"cpu_load":24.0}
```

---

## 7. Module D: Speech Transcription

### 7.1 `GET /api/v1/videos/{video_id}/transcript`
- **Purpose:** Retrieves the active transcript summary and complete full-text body.
- **Response Status:** `200 OK`.
- **Response Schema (`TranscriptHeaderResponse`):**
  ```json
  {
    "id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
    "video_id": "e4b2d188-7f3c-4a3a-96e7-8b0108ec73d4",
    "model_name": "small",
    "language": "en",
    "full_text": "Welcome back to the podcast. Today we are talking about...",
    "word_count": 4250,
    "processing_time_seconds": 182.4,
    "created_at": "2026-11-22T13:43:00Z"
  }
  ```

### 7.2 `GET /api/v1/transcripts/{transcript_id}/segments`
- **Purpose:** Retrieves paginated sentence segments with complete word-level timing arrays for karaoke synchronization.
- **Query Parameters:** `limit: int = 100`, `offset: int = 0`.
- **Response Status:** `200 OK`.
- **Response Schema (`TranscriptSegmentListResponse`):**
  ```json
  {
    "items": [
      {
        "id": "seg_001",
        "segment_index": 0,
        "start_ms": 1200,
        "end_ms": 4800,
        "text": "The single biggest mistake creators make is waiting.",
        "avg_confidence": 0.96,
        "words": [
          {"word": "The", "start_ms": 1200, "end_ms": 1400, "prob": 0.99},
          {"word": "single", "start_ms": 1420, "end_ms": 1780, "prob": 0.98},
          {"word": "biggest", "start_ms": 1800, "end_ms": 2200, "prob": 0.97},
          {"word": "mistake", "start_ms": 2220, "end_ms": 2700, "prob": 0.96},
          {"word": "creators", "start_ms": 2720, "end_ms": 3200, "prob": 0.95},
          {"word": "make", "start_ms": 3220, "end_ms": 3600, "prob": 0.98},
          {"word": "is", "start_ms": 3620, "end_ms": 3900, "prob": 0.99},
          {"word": "waiting.", "start_ms": 3920, "end_ms": 4800, "prob": 0.94}
        ]
      }
    ],
    "total": 340
  }
  ```

### 7.3 `PATCH /api/v1/transcripts/{transcript_id}/segments/{segment_id}`
- **Purpose:** In-place edit of misheard segment words.
- **Request Body (`SegmentUpdateRequest`):**
  ```json
  {
    "text": "The single biggest mistake editors make is waiting."
  }
  ```
- **Response Status:** `200 OK`.

### 7.4 `POST /api/v1/videos/{video_id}/transcribe`
- **Purpose:** Re-runs transcription on a video with custom model parameters (`base`, `small`, `medium`).
- **Response Status:** `202 Accepted`.

---

## 8. Module E: Highlight Detection & Scoring

### 8.1 `GET /api/v1/videos/{video_id}/highlights`
- **Purpose:** Retrieves all algorithmically detected highlights ranked by composite score.
- **Response Status:** `200 OK`.
- **Response Schema (`HighlightListResponse`):**
  ```json
  {
    "items": [
      {
        "id": "h_9a8b7c6d",
        "video_id": "e4b2d188...",
        "start_ms": 45000,
        "end_ms": 82000,
        "duration_ms": 37000,
        "hook_sentence": "The single biggest mistake creators make is waiting.",
        "summary": "Discussion on why perfectionism destroys channel growth.",
        "hook_score": 92.5,
        "coherence_score": 88.0,
        "density_score": 84.0,
        "sentiment_score": 78.0,
        "composite_score": 87.2,
        "category": "Insight",
        "detection_method": "HEURISTIC",
        "status": "CANDIDATE"
      }
    ]
  }
  ```

### 8.2 `GET /api/v1/highlights/{highlight_id}`
- **Purpose:** Retrieves detailed scoring breakdown and dialogue text for a highlight.
- **Response Status:** `200 OK`.

### 8.3 `PATCH /api/v1/highlights/{highlight_id}`
- **Purpose:** Allows manual fine-tuning of highlight start/end timestamps or status.
- **Request Body (`HighlightUpdateRequest`):**
  ```json
  {
    "start_ms": 44500,
    "end_ms": 82500,
    "status": "ACCEPTED"
  }
  ```
- **Response Status:** `200 OK`.

### 8.4 `POST /api/v1/videos/{video_id}/highlights/detect`
- **Purpose:** Re-scans the transcript with custom duration filters ($15\text{s}–30\text{s}$, $30\text{s}–60\text{s}$, $60\text{s}–90\text{s}$).
- **Response Status:** `202 Accepted`.

---

## 9. Module F: Interactive Clips & Studio

### 9.1 `POST /api/v1/clips`
- **Purpose:** Creates a new clip from a highlight or custom timestamp selection.
- **Request Body (`ClipCreateRequest`):**
  ```json
  {
    "video_id": "e4b2d188-7f3c-4a3a-96e7-8b0108ec73d4",
    "highlight_id": "h_9a8b7c6d",
    "title": "The Biggest Creator Mistake",
    "start_ms": 44500,
    "end_ms": 82500,
    "aspect_ratio_mode": "BLUR_PAD",
    "subtitle_style_preset": "KARAOKE_AMBER"
  }
  ```
- **Response Status:** `201 Created`.

### 9.2 `GET /api/v1/videos/{video_id}/clips`
- **Purpose:** Lists all configured clips for a video.
- **Response Status:** `200 OK`.

### 9.3 `GET /api/v1/clips/{clip_id}`
- **Purpose:** Retrieves full studio configuration for editing.
- **Response Status:** `200 OK`.

### 9.4 `PATCH /api/v1/clips/{clip_id}`
- **Purpose:** Real-time update of trim boundaries, aspect ratio mode, and subtitle styling.
- **Request Body (`ClipUpdateRequest`):**
  ```json
  {
    "title": "Stop Waiting — Create Now",
    "start_ms": 44000,
    "end_ms": 81500,
    "aspect_ratio_mode": "BLUR_PAD",
    "subtitle_font_family": "Montserrat",
    "subtitle_font_size": 26,
    "subtitle_highlight_color": "#00FFCC",
    "subtitle_vertical_position": "BOTTOM"
  }
  ```
- **Response Status:** `200 OK`.

### 9.5 `DELETE /api/v1/clips/{clip_id}`
- **Purpose:** Deletes clip configuration and intermediate cuts.
- **Response Status:** `204 No Content`.

### 9.6 `GET /api/v1/clips/{clip_id}/subtitles.ass`
- **Purpose:** Downloads dynamically compiled ASS subtitle file for client-side preview rendering.
- **Content-Type:** `text/x-ssa`.
- **Response Status:** `200 OK`.

---

## 10. Module G: Export & NVENC Video Rendering

### 10.1 `POST /api/v1/clips/{clip_id}/export`
- **Purpose:** Enqueues an NVENC hardware-accelerated video rendering job.
- **Request Body (`ExportCreateRequest`):**
  ```json
  {
    "resolution": "1080x1920",
    "fps": 30.0,
    "encoder_preference": "h264_nvenc"
  }
  ```
- **Response Status:** `202 Accepted`.
- **Response Schema (`ExportJobResponse`):**
  ```json
  {
    "id": "exp_1a2b3c4d",
    "clip_id": "clip_5e6f7g8h",
    "video_id": "e4b2d188...",
    "status": "QUEUED",
    "progress_percent": 0.0,
    "output_filename": "The_Biggest_Creator_Mistake_clip_01.mp4",
    "created_at": "2026-11-22T13:45:00Z"
  }
  ```

### 10.2 `GET /api/v1/exports/{export_id}`
- **Purpose:** Checks real-time export progress, render speed, and file metrics.
- **Response Status:** `200 OK`.

### 10.3 `GET /api/v1/exports`
- **Purpose:** Lists all finished export files with download URLs.
- **Response Status:** `200 OK`.

### 10.4 `GET /api/v1/exports/{export_id}/download`
- **Purpose:** Streams the rendered 1080x1920 MP4 video file for browser download.
- **Headers:** `Content-Disposition: attachment; filename="The_Biggest_Creator_Mistake_clip_01.mp4"`.
- **Response Status:** `200 OK`.

### 10.5 `POST /api/v1/exports/{export_id}/reveal`
- **Purpose:** Triggers Windows File Explorer to open and select the exported MP4 file on disk.
- **Response Status:** `200 OK`.

### 10.6 `POST /api/v1/exports/{export_id}/cancel`
- **Purpose:** Cancels an active NVENC render job and terminates the FFmpeg subprocess.
- **Response Status:** `200 OK`.

---

## 11. Module H: Storage & Maintenance

### 11.1 `GET /api/v1/storage/usage`
- **Purpose:** Retrieves a detailed breakdown of local disk space consumed by Clipsly.
- **Response Status:** `200 OK`.
- **Response Schema (`StorageUsageResponse`):**
  ```json
  {
    "total_storage_bytes": 5368709120,
    "uploads_bytes": 4294967296,
    "audio_bytes": 209715200,
    "clips_bytes": 314572800,
    "exports_bytes": 524288000,
    "temp_bytes": 25165824,
    "database_bytes": 8388608
  }
  ```

### 11.2 `GET /api/v1/storage/disk-space`
- **Purpose:** Checks available physical NVMe SSD capacity and safety thresholds.
- **Response Status:** `200 OK`.
- **Response Schema (`DiskSpaceResponse`):**
  ```json
  {
    "free_bytes": 137438953472,
    "total_bytes": 512110190592,
    "free_gb": 128.0,
    "status": "SAFE",
    "can_upload": true
  }
  ```

### 11.3 `POST /api/v1/storage/cleanup`
- **Purpose:** Purges orphaned scratch files in `storage/temp/` and intermediate cuts in `storage/clips/`.
- **Request Body (`StorageCleanupRequest`):**
  ```json
  {
    "purge_temp": true,
    "purge_intermediate_clips": true
  }
  ```
- **Response Status:** `200 OK`.
- **Response Schema:** `{ "reclaimed_bytes": 339738624, "status": "SUCCESS" }`.

### 11.4 `POST /api/v1/system/backup`
- **Purpose:** Executes a non-blocking hot SQLite snapshot to `data/backups/`.
- **Response Status:** `200 OK`.
- **Response Schema:** `{ "backup_file": "clipsly_backup_20261122.db", "status": "COMPLETED" }`.

---

## 12. Frontend-Backend Communication & TypeScript Types

The React frontend communicates via a typed Axios client configured with base URL `http://127.0.0.1:8000/api/v1`:

```typescript
// frontend/src/types/api.ts

export interface Video {
  id: string;
  filename: string;
  original_filename: string;
  file_size_bytes: number;
  duration_seconds: number;
  width: number;
  height: number;
  fps: number;
  status: 'UPLOADED' | 'PROBED' | 'PROCESSING' | 'READY' | 'ERROR';
  created_at: string;
}

export interface WordToken {
  word: string;
  start_ms: number;
  end_ms: number;
  prob: number;
}

export interface TranscriptSegment {
  id: string;
  segment_index: number;
  start_ms: number;
  end_ms: number;
  text: string;
  words: WordToken[];
}

export interface Highlight {
  id: string;
  video_id: string;
  start_ms: number;
  end_ms: number;
  duration_ms: number;
  hook_sentence: string;
  composite_score: number;
  category: string;
  status: 'CANDIDATE' | 'ACCEPTED' | 'DISCARDED';
}

export interface Clip {
  id: string;
  video_id: string;
  title: string;
  start_ms: number;
  end_ms: number;
  duration_ms: number;
  aspect_ratio_mode: 'BLUR_PAD' | 'CENTER_CROP';
  subtitle_enabled: boolean;
  subtitle_style_preset: string;
  subtitle_font_family: string;
  subtitle_font_size: number;
  subtitle_highlight_color: string;
  subtitle_vertical_position: 'BOTTOM' | 'MIDDLE' | 'TOP';
}
```

---

## 13. API Security & Localhost Restrictions

1. **Localhost Binding:** Binds strictly to `127.0.0.1:8000`. Inbound requests from LAN IPs are refused.
2. **CORS Policy:** Whitelist restricted to `http://localhost:5173` and `http://127.0.0.1:5173` (Vite dev server).
3. **No Auth Overhead:** As a sovereign, single-user desktop application, passwords and JWTs are omitted.
4. **External API Key Masking:** In `GET /api/v1/system/settings`, external LLM keys are masked as `sk-...[last 4 chars]` to prevent display leakage.

---

## 14. Architecture Decision Records for API Tier

### ADR-009: Unified REST + Server-Sent Events (SSE) Architecture
- **Context:** Long tasks (transcription, rendering) require real-time progress without polling overhead.
- **Options Considered:** (A) WebSockets, (B) Long-Polling, (C) SSE + REST.
- **Selected Decision:** **Option C (SSE + REST).**
- **Reason:** SSE is lightweight, operates over standard HTTP, auto-reconnects natively, and avoids bidirectional WebSocket state complexity for unilateral progress updates.
- **Status:** **APPROVED.**

### ADR-010: Standardized Millisecond Timecode Representation
- **Context:** Subtitle synchronization and video cutting require sub-second precision.
- **Options Considered:** (A) Floating-point seconds (e.g., `12.456`), (B) Integer milliseconds (e.g., `12456`).
- **Selected Decision:** **Option B (Integer milliseconds).**
- **Reason:** Floating-point representations introduce IEEE 754 rounding errors during JSON serialization. Integer milliseconds guarantee exact sample alignment.
- **Status:** **APPROVED.**

---

## 15. Current Status & Next Steps

- **Status:** **PHASE 08 COMPLETED & VERIFIED.**
- **Implementation Highlights:**
  - Standardized JSON error response envelope (`error_code`, `detail`, `error: {code, message, details}`) active across all exception handlers.
  - Core v1 API routers registered under `/api/v1` (`system`, `videos`, `jobs`, `transcripts`, `highlights`, `clips`, `exports`).
  - Implemented endpoints read/write to the SQLite database with async SQLAlchemy sessions.
  - Unimplemented feature endpoints return honest 501 Not Implemented responses detailing the activation phase.
  - End-to-end API test suite passing in `backend/tests/test_api_v1_endpoints.py` and `backend/tests/test_error_handling.py`.
- **Immediate Next Step:** Proceed to **Phase 09 (Media Pipeline & Chunked Ingestion Architecture)** upon user approval.
