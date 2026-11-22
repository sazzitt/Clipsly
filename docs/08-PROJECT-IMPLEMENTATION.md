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

- **Status:** PHASE 09 COMPLETED & VERIFIED.
- **Frontend Architecture (Phase 07):** Clean modular directories, 11 routes, 12 UI primitives, typed API client, and 20 passing unit tests.
- **Backend Architecture (Phase 08):** Centralized Pydantic Settings v2, structured rotating logging, standardized error envelopes, 3 middlewares (security, correlation, timing), 8 SQLAlchemy 2.0 Async ORM models, Alembic migrations, and 7 API v1 domain routers with 24 passing pytest tests.
- **Design System & UI Components (Phase 09):**
  - **Design Token System:** Strict HSL CSS variables and TypeScript constants (`frontend/src/styles/tokens.ts`) for surfaces, typography, karaoke highlights, and telemetry.
  - **UI Primitives:** 17 standardized components (`Button`, `Card`, `Badge`, `Input`, `Label`, `Select`, `Checkbox`, `Switch`, `Slider`, `Textarea`, `Progress`, `Table`, `ScrollArea`, `Kbd`, `StatusIndicator`, `Dialog`, `Toast`).
  - **Workstation-Specific Modules:** 9 reusable components (`VideoThumbnail`, `VideoMetadataRow`, `ProcessingStatus`, `StorageUsageBar`, `HardwareMetricCard`, `EmptyVideoLibrary`, `FeatureUnavailable`, `SectionHeader`, `PageToolbar`).
  - **Component Showcase Route:** Live interactive showcase page accessible at `/design-system` and linked from Settings.
  - **Quality Gates:** 51 frontend Vitest tests passing in 7.97s; 24 backend pytest tests passing in 1.19s; ESLint clean (0 errors, 0 warnings); TypeScript strict build clean (`tsc -b && vite build`).
- **Execution Target:** Audio Extraction & Media Metadata Pipeline begins in **Phase 10**.
