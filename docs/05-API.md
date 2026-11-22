# FastAPI REST API Specification

**Project Name:** AI Video Clipper (Working Title: Clipsly)  
**Document Version:** 0.1.0  
**Status:** PLANNED (To be implemented and verified in Phase 04 / Phase 05)  
**Author:** Software Architect & Backend API Engineer  

---

## 1. Purpose of this Document

This document defines the REST API architectural contracts, endpoint routes, request payloads, response schemas, error protocols, and real-time event streaming interfaces for the AI Video Clipper backend.

The API exposes a clean, asynchronous interface enabling the React frontend to upload raw video, trigger AI transcription, request highlight extraction, inspect media streams via HTTP 206 Partial Content, customize subtitle styles, and initiate hardware-accelerated video exports.

---

## 2. API Design Principles

1. **RESTful Resource Model:** Organized cleanly around core domain resources (`videos`, `transcripts`, `highlights`, `clips`, `exports`, `system`).
2. **Explicit Pydantic Schemas:** Every request body and JSON response is validated via strictly typed Pydantic v2 models.
3. **Real-Time Progress Streaming:** Long-running pipeline jobs stream progress updates using Server-Sent Events (SSE) via `GET /api/system/events`.
4. **Localhost Loopback Only:** Binds strictly to `127.0.0.1:8000`.

---

## 3. Proposed Core Endpoint Catalog

### 3.1 Media Ingestion & Video Management
- `POST /api/videos/upload` — Multipart chunked streaming video upload.
- `GET /api/videos` — List all ingested videos with thumbnail and duration metadata.
- `GET /api/videos/{video_id}` — Retrieve detailed technical metadata and status for a specific video.
- `GET /api/videos/{video_id}/stream` — HTTP 206 Partial Content video stream for browser playback.
- `DELETE /api/videos/{video_id}` — Delete video file, transcripts, clips, and associated database records.

### 3.2 Transcription Management
- `POST /api/videos/{video_id}/transcribe` — Enqueue speech-to-text transcription (Faster-Whisper).
- `GET /api/videos/{video_id}/transcript` — Retrieve full word-level timestamped transcript.
- `PATCH /api/transcripts/{transcript_id}/utterances/{utterance_id}` — In-place edit of misheard words.

### 3.3 Highlight Detection & Selection
- `POST /api/videos/{video_id}/highlights/detect` — Trigger highlight detection engine with target duration parameters.
- `GET /api/videos/{video_id}/highlights` — Retrieve ranked candidate highlight segments with scores and rationale.

### 3.4 Clip Studio & Styling
- `POST /api/clips` — Create a new clip candidate with custom trim timestamps and reframing settings.
- `GET /api/clips/{clip_id}` — Retrieve clip configuration, preview state, and assigned subtitle styling.
- `PATCH /api/clips/{clip_id}` — Update trim boundaries, aspect ratio mode, or subtitle configuration.
- `GET /api/clips/{clip_id}/subtitles.ass` — Download generated ASS subtitle file for client preview.

### 3.5 Video Export & Rendering
- `POST /api/clips/{clip_id}/export` — Enqueue final NVENC render job.
- `GET /api/exports/{job_id}` — Check export status and rendering percentage.
- `GET /api/exports/{job_id}/download` — Stream rendered MP4 file for browser download.
- `POST /api/exports/{job_id}/reveal` — Trigger Windows File Explorer to highlight the file on disk.

### 3.6 System Health & Telemetry
- `GET /api/system/health` — Returns backend uptime, CUDA availability, and active job status.
- `GET /api/system/hardware` — Real-time GPU VRAM utilization, CPU load, and free SSD space.
- `GET /api/system/events` — Server-Sent Events (SSE) stream broadcasting pipeline task progress.

---

## 4. Planned Sections for Phase 04 Specification

During Phase 04, this document will be expanded to include:
- Complete JSON Request/Response schemas for all 20+ endpoints.
- OpenAPI / Swagger auto-generation configuration.
- Standardized error response envelope (`{ "error": { "code": "...", "message": "...", "details": ... } }`).
- Streaming chunk size standards for high-bandwidth video upload and playback.

---

## 5. Current Status & Next Steps

- **Status:** PLANNED.
- **Immediate Dependency:** Database Schema & Storage Engine (Phase 03).
- **Execution Target:** Phase 04.
