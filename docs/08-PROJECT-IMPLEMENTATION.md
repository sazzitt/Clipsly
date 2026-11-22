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
│   │   ├── api/                 # REST routing endpoints
│   │   │   ├── v1/
│   │   │   │   ├── videos.py    # Ingestion, listing, streaming
│   │   │   │   ├── transcripts.py# Transcription queries, edits
│   │   │   │   ├── highlights.py# Detection triggers, scores
│   │   │   │   ├── clips.py     # Trim updates, aspect ratio
│   │   │   │   ├── exports.py   # Render execution, downloads
│   │   │   │   └── system.py    # Health, hardware telemetry, SSE
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
│   │   │   ├── transcript.py    # Transcript table
│   │   │   ├── utterance.py     # Sentence & word timestamp table
│   │   │   ├── highlight.py     # Highlight candidate scores table
│   │   │   ├── clip.py          # User clip configurations table
│   │   │   ├── export_job.py    # Render job records table
│   │   │   └── pipeline_job.py  # Background queue task table (ADR-001)
│   │   ├── schemas/             # Pydantic v2 validation & response schemas
│   │   │   ├── video.py
│   │   │   ├── transcript.py
│   │   │   ├── highlight.py
│   │   │   ├── clip.py
│   │   │   ├── export.py
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
├── frontend/                    # React 18 + Vite + TypeScript
│   ├── src/
│   │   ├── assets/              # Bundled fonts, icons, placeholders
│   │   ├── components/          # Reusable UI component library (shadcn/ui)
│   │   │   ├── ui/              # Button, Dialog, Slider, Badge, Toast, etc.
│   │   │   ├── layout/          # Navbar, Sidebar, DashboardShell
│   │   │   ├── media/           # VideoPlayer, WaveformTrack, TrimSlider
│   │   │   └── studio/          # SubtitleEditor, StylePicker, AspectRatioToggle
│   │   ├── hooks/               # Custom React hooks (useSSE, useVideoSync)
│   │   ├── pages/               # Top-level view routes
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── VideoReviewPage.tsx
│   │   │   ├── StudioPage.tsx   # Interactive Studio Preview (ADR-004)
│   │   │   └── ExportQueuePage.tsx
│   │   ├── services/            # API client layer (Axios / Fetch)
│   │   ├── types/               # TypeScript interfaces matching Pydantic schemas
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── tailwind.config.js       # Tailwind CSS configuration & tokens
│   ├── package.json
│   └── tsconfig.json
└── storage/                     # Local SSD binary asset storage (gitignored)
```

---

## 3. Confirmed Technical Standards

1. **Strict Type Annotations:** Python code must be 100% typed using Python 3.10+ typing syntax (`str | None`, `list[int]`). Frontend code must enable TypeScript strict mode with zero `any` types.
2. **Asynchronous I/O:** All FastAPI route handlers, database queries, and subprocess invocations must use Python `asyncio`.
3. **Subprocess Isolation:** FFmpeg, FFprobe, and Faster-Whisper workers are isolated into managed child processes to protect the main web server loop (ADR-006).
4. **No External CDN Dependencies:** All fonts, icons, and styling assets must be bundled locally.

---

## 4. Current Status & Next Steps

- **Status:** ARCHITECTURALLY FINALIZED.
- **Dependencies:** Database Schema (Phase 03).
- **Execution Target:** Backend scaffolding begins in **Phase 04**; Frontend scaffolding begins in **Phase 05**.
