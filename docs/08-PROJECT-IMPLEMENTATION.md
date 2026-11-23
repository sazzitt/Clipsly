# Project Implementation Blueprint

**Project Name:** AI Video Clipper (Working Title: Clipsly)  
**Document Version:** 1.0.0  
**Status:** ARCHITECTURALLY FINALIZED (Phase 02 Baseline; Scaffolding in Phases 04 & 05)  
**Author:** Senior Software Architect & Lead Full-Stack Engineer  
**Target Hardware:** ASUS TUF A15 (AMD Ryzen 7 7000 Series, NVIDIA RTX 3050 Laptop GPU, 4GB VRAM)  

---

## 1. Purpose of this Document

This document defines the physical directory layout, module separation of concerns, coding conventions, typing requirements, and development guidelines for the Clipsly codebase.

It translates the architectural standards finalized in `03-ARCHITECTURE.md` into concrete, maintainable, modular software packages across the Python FastAPI backend, the React Vite frontend, and the local storage subsystem.

---

## 2. Definitive Codebase Directory Structure

```
clipsly/
├── docs/                        # Complete technical documentation suite (01 to 15)
├── backend/                     # Python 3.10+ FastAPI Application
│   ├── app/
│   │   ├── api/                 # REST routing endpoints (ADR-009)
│   │   │   ├── v1/
│   │   │   │   ├── system.py    # Health, info, telemetry, settings
│   │   │   │   ├── videos.py    # Ingestion, listing, streaming
│   │   │   │   ├── jobs.py      # Background pipeline job management & SSE
│   │   │   │   ├── transcripts.py# Transcription queries, edits
│   │   │   │   ├── highlights.py# Detection triggers, scores
│   │   │   │   ├── clips.py     # Trim updates, aspect ratio, styles
│   │   │   │   ├── exports.py   # NVENC render execution, downloads
│   │   │   │   └── storage.py   # Disk usage, cleanup, database backup
│   │   │   └── router.py        # Centralized APIRouter aggregation
│   │   ├── core/                # Core configuration & lifecycle
│   │   │   ├── config.py        # Pydantic Settings & environment variables
│   │   │   ├── database.py      # SQLAlchemy 2.0 async engine & sessionmaker
│   │   │   ├── logging.py       # Structured log formatters
│   │   │   ├── security.py      # Path sanitization & local loopback checks
│   │   │   └── subprocess.py    # SafeSubprocessRunner with timeout watchdogs
│   │   ├── models/              # SQLAlchemy 2.0 ORM database models (ADR-005)
│   │   │   ├── base.py          # DeclarativeBase with timestamp mixins
│   │   │   ├── video.py         # Video metadata table
│   │   │   ├── processing_job.py# Background task table (ADR-001)
│   │   │   ├── transcript.py    # Transcript header table
│   │   │   ├── transcript_segment.py # Word-level timestamp utterances
│   │   │   ├── highlight.py     # Highlight candidate scores table
│   │   │   ├── clip.py          # User clip configurations table
│   │   │   ├── export_job.py    # Render job records table
│   │   │   └── setting.py       # Application settings table
│   │   ├── schemas/             # Pydantic v2 validation & response schemas
│   │   │   ├── video.py
│   │   │   ├── processing_job.py
│   │   │   ├── transcript.py
│   │   │   ├── transcript_segment.py
│   │   │   ├── highlight.py
│   │   │   ├── clip.py
│   │   │   ├── export.py
│   │   │   ├── setting.py
│   │   │   └── system.py
│   │   ├── services/            # Pure business logic domain services
│   │   │   ├── media/           # FFmpeg / FFprobe wrapper services
│   │   │   │   ├── inspector.py # Metadata extraction via ffprobe
│   │   │   │   ├── audio.py     # 16kHz WAV extraction
│   │   │   │   ├── cutter.py    # Sample-accurate video slicing
│   │   │   │   ├── reframer.py  # 9:16 vertical blur-pad & center crop
│   │   │   │   └── renderer.py  # NVENC export & libass subtitle burning
│   │   │   ├── ai/              # AI inference services
│   │   │   │   ├── whisper.py   # Faster-Whisper GPU/CPU runner & GC cleanup
│   │   │   │   ├── heuristic_engine.py # Deterministic highlight scoring (ADR-003)
│   │   │   │   └── cloud_ai.py  # Optional Gemini/OpenAI Flash client
│   │   │   └── subtitles/       # Subtitle generation
│   │   │       ├── ass_builder.py# Karaoke timing & styling generator
│   │   │       └── srt_builder.py# Standard SRT generator
│   │   ├── workers/             # Async background pipeline worker
│   │   │   ├── queue.py         # SQLite-backed sequential job queue (ADR-001)
│   │   │   └── sse.py           # SSE event broadcaster
│   │   └── main.py              # Application entrypoint & lifespan lifecycle
│   ├── pyproject.toml           # uv / Poetry dependency manifest
│   └── tests/                   # Pytest automated test suite
├── frontend/                    # React 18 + Vite 6 + TypeScript (Strict)
│   ├── src/
│   │   ├── app/                 # Root application setup & router
│   │   │   ├── App.tsx          # Root provider tree & RouterProvider
│   │   │   ├── router.tsx       # React Router 6.28 Data Router with 11 routes
│   │   │   └── providers.tsx    # BackendHealthProvider & ToastProvider
│   │   ├── components/          # Reusable component library
│   │   │   ├── layout/          # AppLayout, Sidebar, Header, PageContainer
│   │   │   ├── common/          # EmptyState, ErrorState, LoadingState, OfflineBanner, NotFoundPage
│   │   │   ├── providers/       # BackendHealthProvider
│   │   │   └── ui/              # Button, Card, Badge, Input, Dialog, Dropdown, Progress, Tabs, Tooltip, Skeleton, Toast
│   │   ├── context/             # React contexts (BackendHealthContext, ToastContext)
│   │   ├── features/            # Feature-scoped modular pages
│   │   │   ├── dashboard/       # DashboardPage
│   │   │   ├── videos/          # VideoLibraryPage, UploadPage, VideoDetailPage
│   │   │   ├── transcripts/     # TranscriptViewerPage
│   │   │   ├── highlights/      # HighlightsPage
│   │   │   ├── clips/           # ClipsLibraryPage, StudioPage
│   │   │   ├── exports/         # ExportsPage
│   │   │   └── settings/        # SettingsPage, StoragePage
│   │   ├── hooks/               # Custom hooks (useBackendHealth, useToast)
│   │   ├── services/            # api.ts (Centralized typed API client)
│   │   ├── types/               # api.ts (Strict TypeScript contracts matching OpenAPI)
│   │   └── test/                # Vitest & React Testing Library test suites
│   ├── tailwind.config.js       # Tailwind CSS configuration & dark workstation tokens
│   ├── package.json             # React 18, React Router, Vitest, Lucide
│   └── tsconfig.json            # Strict TypeScript configuration
└── storage/                     # Local SSD binary asset storage (gitignored)
```

---

## 3. Confirmed Technical Standards

1. **Strict Type Annotations:** Python code must be 100% typed using Python 3.10+ typing syntax (`str | None`, `list[int]`). Frontend code must enable TypeScript strict mode with zero `any` types.
2. **Asynchronous I/O:** All FastAPI route handlers, database queries, and subprocess invocations must use Python `asyncio`.
3. **Subprocess Isolation:** FFmpeg, FFprobe, and Faster-Whisper workers are isolated into managed child processes to protect the main web server loop (ADR-006).
4. **No External CDN Dependencies:** All fonts, icons, and styling assets must be bundled locally.
5. **Centralized Backend Connection:** Global `BackendHealthProvider` single-instance polling to eliminate duplicate interval requests.

---

## 4. Current Status & Next Steps

- **Status:** PHASE 12 COMPLETED & VERIFIED.
- **Frontend Architecture (Phase 07):** Clean modular directories, 11 routes, 12 UI primitives, typed API client, and 20 passing unit tests.
- **Backend Architecture (Phase 08):** Centralized Pydantic Settings v2, structured rotating logging, standardized error envelopes, 3 middlewares (security, correlation, timing), 8 SQLAlchemy 2.0 Async ORM models, Alembic migrations, and 7 API v1 domain routers with 24 passing pytest tests.
- **Design System & UI Components (Phase 09):**
  - **Design Token System:** Strict HSL CSS variables and TypeScript constants (`frontend/src/styles/tokens.ts`) for surfaces, typography, karaoke highlights, and telemetry.
  - **UI Primitives:** 17 standardized components (`Button`, `Card`, `Badge`, `Input`, `Label`, `Select`, `Checkbox`, `Switch`, `Slider`, `Textarea`, `Progress`, `Table`, `ScrollArea`, `Kbd`, `StatusIndicator`, `Dialog`, `Toast`).
  - **Workstation-Specific Modules:** 9 reusable components (`VideoThumbnail`, `VideoMetadataRow`, `ProcessingStatus`, `StorageUsageBar`, `HardwareMetricCard`, `EmptyVideoLibrary`, `FeatureUnavailable`, `SectionHeader`, `PageToolbar`).
  - **Component Showcase Route:** Live interactive showcase page accessible at `/design-system` and linked from Settings.
- **Dashboard Development & Workstation Overview (Phase 10):**
  - **Aggregated Backend Endpoint:** `GET /api/v1/system/dashboard` queries SQLite WAL for entity counts (`videos`, `clips`, `jobs`, `exports`, `transcripts`, `highlights`), calculates true Clipsly storage consumption vs NVMe partition space, checks low headroom (<10GB) status, queries hardware telemetry (`nvidia-smi`/Windows `ctypes`), and returns top 5 recent videos and jobs.
  - **Modular UI Feature Architecture:** `frontend/src/features/dashboard/components/` with `DashboardHeader`, `DashboardMetrics`, `DashboardStorage`, `DashboardHardware`, `DashboardRecentVideos`, `DashboardRecentActivity`, `DashboardQuickActions`, and `DashboardSystemStatus`.
  - **Zero Fake Mock Data:** In an empty database, clean empty states are rendered (`EmptyVideoLibrary`, idle jobs card) with direct CTAs to `/upload`.
- **Project Management System (Phase 11):**
  - **Management Interfaces:** Video Library (`/videos`), Video Details (`/video/:id`), Processing Jobs (`/jobs`), Clips Library (`/clips`), Export Records (`/exports`).
  - **Reusable Components:** `frontend/src/components/management/` (`SearchInput`, `FilterSelect`, `SortSelector`, `PaginationControls`, `DeleteConfirmationDialog`, `NoResultsState`, `EntityStatusBadge`).
  - **Cascade Management:** SQLite foreign key cascade with optional SSD source file purge, preserving rendered MP4 exports according to ADR-008.
- **Local Video Upload & Ingestion Pipeline (Phase 12):**
  - **Ingestion Engine:**
    - Asynchronous chunked streaming upload (`POST /api/v1/videos/upload`) with 1MB bounded buffer, supporting files up to 10 GB without buffering into system RAM.
    - SSD storage headroom pre-check ($\ge 10\text{ GB}$ required) raising 507 Insufficient Storage on low disk space.
    - Real-time SHA256 checksum calculation and size accounting during stream consumption.
    - Asynchronous subprocess FFprobe container validation (verifying valid video stream, audio track presence — with actual speech activity detection reserved for Phase 13/14 Faster-Whisper processing — frame rate, resolution, duration bounds $5\text{m}-120\text{m}$).
    - Filesystem path privacy: internal filesystem paths are strictly withheld from public API responses to protect host filesystem privacy; safe storage labels (`Local SSD Storage`) are displayed in the UI.
    - Atomic file relocation from scratch space (`storage/temp/upload_{uuid}.tmp`) to persistent store (`storage/uploads/{video_id}.{ext}`) with path confinement checks.
    - Zero orphaned files: guaranteed cleanup of partial scratch files upon client cancellation, timeout, validation failure, or database rollback.
    - Zero orphaned persistent files: if database commit fails after file relocation, the persistent file is immediately unlinked and the transaction rolled back.
    - Duplicate upload policy: identical original filenames or identical binary content are assigned unique UUIDs and stored independently without collisions or overwrites.
  - **Frontend Upload Experience (`/upload`):**
    - Drag-and-drop dropzone with container badges (`MP4, MKV, MOV, WebM`), max size indicator (`10 GB`), duration guidance (`5 - 120 Min`).
    - Client-side pre-validation (extension, size, empty file checks).
    - Real-time progress bar reflecting actual network transmitted bytes via `XMLHttpRequest.upload.onprogress`.
    - Accurately measured upload speed (`MB/s`) and moving-average time remaining calculation.
    - Full client cancellation support via `AbortController`.
    - Finalization spinner during FFprobe container validation.
    - Success summary card with direct one-click navigation to Video Details (`/video/:id`) and Video Library (`/videos`).
  - **Quality Gates (Phase 12):** 51 backend pytest tests passing (100%); 73 frontend Vitest tests passing (100%); ESLint clean (0 errors, 0 warnings); TypeScript strict check (`tsc -b`) clean; Vite production build clean (8.44s).
- **Video Preview & Metadata Extraction Pipeline (Phase 13):**
  - Asynchronous FFprobe engine extracting comprehensive video stream attributes (codecs, profiles, pixel formats, bit depth, rotation, orientation, bitrates) and audio stream characteristics (codecs, channels, sample rate, layout).
  - Handles audio-less videos honestly and gracefully with nullable audio schema and UI states.
  - RFC 9110 HTTP Range video streaming endpoint (`GET /api/v1/videos/{video_id}/stream`) with 128KB bounded streaming, 206 Partial Content, 416 Range Not Satisfiable, and storage path containment checks.
  - Interactive metadata refresh endpoint (`POST /api/v1/videos/{video_id}/metadata/refresh`) guarded against concurrent duplicate extraction runs (409 Conflict).
  - Workstation HTML5 video player component (`VideoPlayer.tsx`) with full playback controls, scrubber with buffered chunks, volume, playback speed dropdown, fullscreen, error recovery, and accessible keyboard shortcuts.
  - Quality Gates: 71 backend pytest tests passing (100%); 84 frontend Vitest tests passing (100%).
- **FFmpeg Audio Extraction & Preprocessing Pipeline (Phase 14):**
  - **Standardized Profile:** Extracts and resamples container audio to 16,000 Hz, 16-bit mono PCM WAV format (`pcm_s16le`) stored in `storage/audio/{uuid}.wav`.
  - **ORM & Database:** `AudioAsset` entity created with Alembic migration `05adc4b773ff` and strict CHECK constraints (`sample_rate = 16000`, `channels = 1`, `duration_seconds > 0.0`, `file_size_bytes > 0`).
  - **Subprocess Engine:** Non-blocking asynchronous FFmpeg execution with real-time machine-readable progress tracking via `-progress pipe:1` parsing `out_time_us`.
  - **Job Lifecycle & Cancellation:** Integrated with `ProcessingJob(job_type='AUDIO_EXTRACTION')`; supports clean cancellation terminating active FFmpeg process and unlinking scratch files.
  - **Stream Selection & Multi-Audio:** Detects all audio streams via FFprobe; supports selecting specific stream index or falling back to default/first audio stream.
  - **Validation & Containment:** FFprobe verification on generated WAV ensuring exact codec, channel, and rate compliance; storage path traversal protection.
  - **Frontend UI:** Dedicated Audio Preprocessing card on Video Details page with stream selector, extract button, real-time progress bar with cancel action, and validated WAV specifications display.
  - **Quality Gates:** 104 backend pytest tests passing (100%); 95 frontend Vitest tests passing (100%); ESLint clean (0 errors, 0 warnings); TypeScript strict check (`tsc -b`) clean; Vite production build clean (11.72s).
- **Execution Target:** **Phase 14 COMPLETE & VERIFIED.** Stop condition enforced; awaiting explicit user approval before beginning Phase 15 (Faster-Whisper Speech-to-Text Pipeline).
