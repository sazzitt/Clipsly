# Testing Strategy & QA Plan

**Project Name:** AI Video Clipper (Working Title: Clipsly)  
**Document Version:** 0.1.0  
**Status:** PLANNED (To be detailed in Phase 02 and fully executed in Phase 19)  
**Author:** QA Lead & Systems Test Engineer  

---

## 1. Purpose of this Document

This document establishes the testing strategy, test harness architecture, automated test suites, quality gates, and hardware benchmarking protocols for AI Video Clipper.

Testing a multimedia application involving audio/video codecs, neural network speech transcription, and GPU hardware acceleration requires rigorous verification across both pure logic layers and real-world media rendering workloads on the **ASUS TUF A15 (RTX 3050 4GB VRAM)** laptop.

---

## 2. Testing Pyramid & Methodology

```
                   ┌───────────────────────┐
                   │   Hardware Benchmark  │
                   │  & VRAM Stress Tests  │
                   ├───────────────────────┤
                   │   End-to-End Media    │
                   │   Pipeline Tests      │
                   ├───────────────────────┤
                   │   Backend / Frontend  │
                   │   Integration Tests   │
                   ├───────────────────────┤
                   │   Unit Tests (Pytest  │
                   │   & Vitest)           │
                   └───────────────────────┘
```

1. **Unit Testing:**
   - **Backend (Pytest):** Models, Pydantic validation schemas, database CHECK constraints, subtitle ASS formatting, timestamp calculation, heuristic scoring math (Hook 30%, Coherence 30%, Density 25%, Sentiment 15%), non-maximum suppression (NMS) overlap de-duplication.
   - **Frontend (Vitest + React Testing Library):** UI component rendering across all 14 screens, dual-handle trim slider drag bounds, millisecond timecode formatting, studio subtitle inspector state management, live canvas/DOM karaoke synchronizer.
2. **Integration Testing:**
   - Database operations (SQLite WAL concurrent reads/writes, foreign key cascades, transaction rollbacks).
   - Alembic migration tests (upgrade head $\to$ downgrade $\to$ upgrade head).
   - FastAPI endpoint contracts and error envelopes across all 40 endpoints (`httpx.AsyncClient`).
   - Server-Sent Events (SSE) stream event validation (`job_progress`, `job_completed`, `hardware_telemetry`).
   - Subprocess invocation of `ffprobe` and `ffmpeg` against deterministic test media.
3. **End-to-End Media Pipeline Testing:**
   - Automated run of the full 16-step pipeline from upload to finished 1080x1920 MP4 file using synthetic sample videos.
4. **Hardware Benchmarking & VRAM Stress Testing:**
   - Continuous VRAM polling during long-form video transcription and NVENC export to ensure usage never exceeds 3.5GB.

---

## 3. Synthetic Test Asset Generation

To enable fast, reproducible tests without committing large video files to Git, tests use an FFmpeg script to generate synthetic test media:

```powershell
# Generate a 60-second 1080p test video with test tones and timestamp burn-in
ffmpeg -y -f lavfi -i testsrc=duration=60:size=1920x1080:rate=30 -f lavfi -i sine=frequency=1000:duration=60 -c:v libx264 -c:a aac -pix_fmt yuv420p tests/fixtures/test_60s.mp4
```

---

## 4. Acceptance Criteria Checklist (PRD Section 28 Verification)

| Test ID | Scenario | Target Requirement | Pass Criteria |
|---|---|---|---|
| **QA-AC1** | Full 30-min Ingestion to Export | PRD Section 28.1 | Completes end-to-end without manual intervention in $< 12\text{ mins}$ |
| **QA-AC2** | Peak VRAM Under Load | PRD Section 28.2 | Peak VRAM does not exceed 3.5GB; zero CUDA OOM |
| **QA-AC3** | Karaoke Subtitle Accuracy | PRD Section 28.3 | Spoken word matches visual highlight within $\pm 100\text{ms}$ |
| **QA-AC4** | Output Video Integrity | PRD Section 28.4 | Valid 1080x1920 MP4; plays cleanly in VLC with no audio desync |
| **QA-AC5** | SQLite Data Durability | PRD Section 28.5 | App restart retains all past videos, transcripts, and edits |

---

## 5. Phase 06 Verification Test Run Results

The following test verification suites have been executed and passed on the ASUS TUF A15 development machine:

### 5.1 Backend Pytest Execution
```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0
rootdir: Clipsly, configfile: pytest.ini, testpaths: backend/tests
plugins: anyio-4.16.0, asyncio-1.5.0
asyncio: mode=Mode.AUTO, loop_scope=function
collected 2 items

backend/tests/test_health.py::test_root_endpoint PASSED                  [ 50%]
backend/tests/test_health.py::test_system_health_endpoint PASSED         [100%]

============================== 2 passed in 0.25s ==============================
```

### 5.2 Frontend Build & TypeScript Check
```
> clipsly-frontend@1.0.0 build
> tsc -b && vite build

vite v6.4.6 building for production...
✓ 1580 modules transformed.
dist/index.html                   0.91 kB │ gzip:  0.51 kB
dist/assets/index-BkuJlEw_.css   15.14 kB │ gzip:  3.71 kB
dist/assets/index-CdXdSLDY.js   166.15 kB │ gzip: 51.26 kB
✓ built in 6.52s
```

### 5.3 Frontend ESLint Execution
```
> clipsly-frontend@1.0.0 lint
> eslint .
(0 errors, 0 warnings)
```

### 5.4 End-to-End Foundation Automated Verification (`scripts/verify_phase06.py`)
```
[VERIFY] Starting Phase 06 Foundation Verification...
[VERIFY] Checking directory structure...
[VERIFY] All required directories exist.
[VERIFY] Checking SQLite database file...
[VERIFY] Database file verified at: Clipsly\data\clipsly.db (Size: 4096 bytes)
[VERIFY] Starting Uvicorn backend process on 127.0.0.1:8000...
[VERIFY] Health check HTTP GET succeeded!
[VERIFY] Response: {
  "status": "healthy",
  "version": "1.0.0",
  "database_connected": true,
  "cuda_available": true,
  "nvenc_available": true,
  "active_jobs_count": 0,
  "uptime_seconds": 0.59
}
[VERIFY] Shutting down Uvicorn backend process...
[VERIFY] Backend shutdown cleanly.
[VERIFY] Checking application log output...
[VERIFY] Log file verified (516 chars). Sample line:
[VERIFY]   2026-11-22 14:56:38 | INFO | clipsly:68 - Database connection validated. SQLite journal mode: wal
[VERIFY] ==================================================
[VERIFY] PHASE 06 FOUNDATION VERIFICATION: ALL CHECKS PASSED
[VERIFY] ==================================================
```

---

## 6. Planned Sections for Phase 19 Specification

During Phase 19, this document will be expanded to include:
- Complete automated test suite commands (`pytest --cov`, `pnpm test`).
- Continuous integration (CI) workflow for GitHub Actions (running CPU mock suites).
- Benchmarking report template recording RTF, render times, and memory logs across 10-minute, 30-minute, and 60-minute test inputs.

---

## 6. Current Status & Next Steps

- **Status:** PLANNED.
- **Immediate Dependency:** Completion of functional phases (Phases 04 through 18).
- **Execution Target:** Phase 19.
