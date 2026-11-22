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

## 6. Phase 07 Frontend Architecture Test Run Results

The following test suites and quality gates have been executed and passed for Phase 07:

### 6.1 Frontend Vitest Suite (`npm test`)
```
 RUN  v5.1.1 Clipsly/frontend

 ✓ src/test/api.test.ts (3 tests) 25ms
 ✓ src/test/health.test.tsx (3 tests) 253ms
 ✓ src/test/ui.test.tsx (7 tests) 367ms
 ✓ src/test/navigation.test.tsx (7 tests) 811ms

 Test Files  4 passed (4)
      Tests  20 passed (20)
   Start at  15:47:35
   Duration  6.91s
```
- **Tests Passing:** 20/20.
- **Coverage Areas:** Router navigation, active links, 404 handler, API client error unwrapping, timeout handling, backend connected/offline indicator, UI primitives (Button, Card, Badge, Progress, EmptyState, LoadingState, ConfirmationDialog).

### 6.2 Frontend Production Build & TypeScript Check (`npm run build`)
```
> clipsly-frontend@1.0.0 build
> tsc -b && vite build

vite v6.4.6 building for production...
✓ 1624 modules transformed.
dist/index.html                   0.91 kB │ gzip:  0.51 kB
dist/assets/index-DzSigL6H.css   27.55 kB │ gzip:  5.67 kB
dist/assets/index-BUFMaoXA.js   309.72 kB │ gzip: 93.33 kB
✓ built in 9.08s
```
- **TypeScript strict check:** 0 errors.

### 6.3 Frontend ESLint Execution (`npm run lint`)
```
> clipsly-frontend@1.0.0 lint
> eslint .
(0 errors, 0 warnings)
```

---

## 7. Phase 08 Backend Foundation & API Infrastructure Test Run Results

The following backend test suites, database migration checks, and quality gates have been executed and passed for Phase 08:

### 7.1 Backend Pytest Suite (`pytest -v backend/tests`)
```
backend/tests/test_api_v1_endpoints.py::test_videos_endpoints PASSED     [  4%]
backend/tests/test_api_v1_endpoints.py::test_jobs_endpoints PASSED       [  8%]
backend/tests/test_api_v1_endpoints.py::test_transcripts_endpoints PASSED [ 12%]
backend/tests/test_api_v1_endpoints.py::test_highlights_endpoints PASSED [ 16%]
backend/tests/test_api_v1_endpoints.py::test_clips_lifecycle PASSED      [ 20%]
backend/tests/test_api_v1_endpoints.py::test_exports_endpoints PASSED    [ 25%]
backend/tests/test_config.py::test_settings_defaults PASSED              [ 29%]
backend/tests/test_config.py::test_directory_paths_exist PASSED          [ 33%]
backend/tests/test_config.py::test_cors_origins_contain_local_vite PASSED [ 37%]
backend/tests/test_database.py::test_check_db_connection PASSED          [ 41%]
backend/tests/test_database.py::test_sqlite_pragmas PASSED               [ 45%]
backend/tests/test_error_handling.py::test_not_found_error_envelope PASSED [ 50%]
backend/tests/test_error_handling.py::test_validation_error_envelope PASSED [ 54%]
backend/tests/test_error_handling.py::test_not_implemented_error_envelope PASSED [ 58%]
backend/tests/test_health.py::test_root_endpoint PASSED                  [ 62%]
backend/tests/test_health.py::test_system_health_endpoint PASSED         [ 66%]
backend/tests/test_middleware.py::test_correlation_id_generated PASSED   [ 70%]
backend/tests/test_middleware.py::test_correlation_id_propagated PASSED  [ 75%]
backend/tests/test_middleware.py::test_request_timing_header PASSED      [ 79%]
backend/tests/test_middleware.py::test_localhost_security_blocks_external_host PASSED [ 83%]
backend/tests/test_models.py::test_models_lifecycle_and_relationships PASSED [ 87%]
backend/tests/test_system_api.py::test_system_info_endpoint PASSED       [ 91%]
backend/tests/test_system_api.py::test_system_hardware_endpoint PASSED   [ 95%]
backend/tests/test_system_api.py::test_system_settings_get_and_patch PASSED [100%]

============================= 24 passed in 1.21s ==============================
```
- **Tests Passing:** 24/24.
- **Coverage Areas:** Configuration validation, SQLite WAL mode, foreign keys, full lifecycle & cascade deletion across all 8 ORM models, hardware telemetry, settings mutation, correlation ID assignment and propagation, request timing headers, localhost loopback isolation (blocking non-local Host headers), and standardized error responses.

### 7.2 Database Migration Verification (`alembic upgrade head`)
- Initial migration revision `c0221816e0e3_create_initial_schema.py` generated from declarative models and applied to `data/clipsly.db`.
- Verified tables: `videos`, `processing_jobs`, `transcripts`, `transcript_segments`, `highlights`, `clips`, `export_jobs`, `application_settings`, `alembic_version`.

---

## 8. Phase 09 Design System & Workstation UI Components Test Run Results

The following test suites and quality gates were executed and passed for Phase 09:

### 8.1 Frontend Vitest Suite (`npm test`)
```
 RUN  v5.1.1 Clipsly/frontend

 ✓ src/test/api.test.ts (3 tests) 16ms
 ✓ src/test/health.test.tsx (3 tests) 289ms
 ✓ src/test/ui.test.tsx (7 tests) 453ms
 ✓ src/test/design-system.test.tsx (18 tests) 489ms
 ✓ src/test/workstation-components.test.tsx (13 tests) 533ms
 ✓ src/test/navigation.test.tsx (7 tests) 858ms

 Test Files  6 passed (6)
      Tests  51 passed (51)
   Start at  17:19:12
   Duration  7.97s
```
- **Tests Passing:** 51/51.
- **Coverage Areas:**
  - `Button`: Loading spinner, `aria-busy`, disabled click prevention, destructive/subtle/outline variants.
  - `Card`: Default, interactive (hover/active), metric, section, compact variants.
  - `Badge`: Default, secondary, destructive, success, warning, info, subtle, disabled feature.
  - `Input` & `Label`: Invalid error state (`aria-invalid="true"`, border-destructive), required asterisk indicator.
  - `Select`, `Checkbox`, `Switch`, `Slider`, `Textarea`, `Table`, `Kbd`, `StatusIndicator`.
  - `Progress`: Determinate, indeterminate with `aria-busy="true"`.
  - `VideoThumbnail`: 16:9, 9:16 aspect ratios, duration badge formatting, resolution tag, empty placeholder fallback.
  - `VideoMetadataRow`: Stream characteristics (fps, resolution, duration, audio/video codecs, formatted file size).
  - `ProcessingStatus`: Queued, processing with percentage, completed, failed with error message box.
  - `StorageUsageBar`: Normal free space, critical warning alert (&lt;10 GB).
  - `HardwareMetricCard`: Telemetry value, subvalue, percent, safe/warn/error threshold colors.
  - `EmptyVideoLibrary`: Empty state with upload button trigger.
  - `FeatureUnavailable`: Inactive feature card with milestone phase badge and roadmap explanation.
  - `SectionHeader` & `PageToolbar`: Workstation headers and toolbars with search, filter, and action slots.
  - `ComponentShowcasePage`: Complete internal design system showcase renders without throwing.

### 8.2 Frontend Production Build & TypeScript Strict Check (`npm run build`)
```
> clipsly-frontend@1.0.0 build
> tsc -b && vite build

vite v6.4.6 building for production...
✓ 1653 modules transformed.
dist/index.html                   0.91 kB │ gzip:   0.51 kB
dist/assets/index-Cw_FpgKg.css   37.20 kB │ gzip:   7.23 kB
dist/assets/index-QNetXaK9.js   356.04 kB │ gzip: 103.47 kB
✓ built in 10.66s
```
- **TypeScript strict check:** 0 errors.

### 8.3 Frontend ESLint Execution (`npm run lint`)
```
> clipsly-frontend@1.0.0 lint
> eslint .
(0 errors, 0 warnings)
```

---

## 9. Planned Sections for Phase 19 Specification

During Phase 19, this document will be expanded to include:
- Complete automated test suite commands (`pytest --cov`, `pnpm test`).
- Continuous integration (CI) workflow for GitHub Actions (running CPU mock suites).
- Benchmarking report template recording RTF, render times, and memory logs across 10-minute, 30-minute, and 60-minute test inputs.

---

## 10. Current Status & Next Steps

- **Status:** PHASE 09 COMPLETED & VERIFIED.
- **Active Suites:** 24 backend pytest tests passing, 51 frontend Vitest tests passing, ESLint clean (0 errors), TypeScript build clean.
- **Next Phase:** Proceed to Phase 10 upon user approval.
