# Troubleshooting & Diagnostics Guide

**Project Name:** AI Video Clipper (Working Title: Clipsly)  
**Document Version:** 0.1.0  
**Status:** PLANNED (To be maintained and expanded across Phases 18 through 20)  
**Author:** Systems Support & Diagnostics Engineer  

---

## 1. Purpose of this Document

This document provides diagnostic procedures, error code indexes, troubleshooting playbooks, and self-healing mechanisms for common failure modes encountered during the development and execution of the AI Video Clipper application.

Due to the complex interactions between Windows 11 host environments, NVIDIA GPU drivers, CUDA libraries, FFmpeg subprocesses, and multimedia file codecs, this guide acts as the definitive operational manual for diagnosing and resolving system anomalies.

---

## 2. Common Failure Modes & Diagnostic Playbooks

### 2.1 CUDA Out-Of-Memory (OOM) Errors
- **Symptom:** Faster-Whisper crashes with `RuntimeError: CUDA out of memory` or `CUDA error: out of memory`.
- **Root Cause:** GPU VRAM exceeded the 4GB physical ceiling of the RTX 3050 (often caused by background desktop applications, browser hardware acceleration, or residual model allocations).
- **Resolution Playbook:**
  1. Check VRAM usage: Run `nvidia-smi` in PowerShell to identify rogue processes consuming VRAM.
  2. Switch Whisper model to a lower memory footprint: Set `model_size="small"` or `model_size="base"` with `compute_type="int8_float16"`.
  3. Force garbage collection: Ensure `del model` and Python memory cleanup runs immediately following transcription.
  4. Trigger automatic CPU fallback: Configure the backend setting `FORCE_CPU_TRANSCRIPTION=true` to utilize the 8-core AMD Ryzen 7 processor.

### 2.2 Missing FFmpeg NVENC Hardware Acceleration
- **Symptom:** FFmpeg video rendering fails with `Unknown encoder 'h264_nvenc'` or `Cannot load nvcuda.dll`.
- **Root Cause:** The installed FFmpeg binary was compiled without NVENC support or NVIDIA display drivers are outdated.
- **Resolution Playbook:**
  1. Verify encoder support: `ffmpeg -encoders | findstr nvenc`.
  2. If missing, install a full GPL build of FFmpeg (e.g., from `gyan.dev` or via `winget install Gyan.FFmpeg`).
  3. Update NVIDIA drivers to version 550+ from the official NVIDIA website.
  4. Fall back to CPU encoding: Set video codec to `libx264` with `preset=fast`.

### 2.3 Audio-Video Drift (Desynchronization)
- **Symptom:** In exported clips, speaker lip movements do not match audio, or subtitles gradually drift out of sync over time.
- **Root Cause:** Source video was recorded with Variable Frame Rate (VFR) (common in smartphone recordings and OBS game captures without constant frame rate enforcement).
- **Resolution Playbook:**
  1. Inspect container with `ffprobe` for variable frame rate markers.
  2. Normalize during ingestion: Apply the FFmpeg video filter `-vsync cfr -r 30` during intermediate clip cutting to lock frame intervals to Constant Frame Rate (CFR).

### 2.4 SQLite "Database is Locked" (`sqlite3.OperationalError`)
- **Symptom:** API requests fail with 500 status when background tasks update progress.
- **Root Cause:** Concurrency collision where multiple worker threads attempt simultaneous writes to SQLite in standard rollback journal mode.
- **Resolution Playbook:**
  1. Confirm Write-Ahead Logging is active: Run `PRAGMA journal_mode=WAL;`.
  2. Increase busy timeout: Ensure SQLite connections set `PRAGMA busy_timeout=30000;` (30 seconds).
  3. Use single-writer async queue architecture for state updates.

### 2.5 SQLite Corruption or Failed Migrations
- **Symptom:** Application startup fails with `sqlite3.DatabaseError: file is not a database` or Alembic throws `Target database is not up to date`.
- **Resolution Playbook:**
  1. Check database integrity: Run `sqlite3 data/clipsly.db "PRAGMA integrity_check;"`.
  2. If corrupted, restore from latest snapshot in `data/backups/`.
  3. If migration fails, inspect current revision with `alembic current` and reconcile with `alembic stamp head` or roll back with `alembic downgrade -1`.

### 2.6 CORS Rejections & Server-Sent Events (SSE) Disconnections
- **Symptom:** Browser console logs `Cross-Origin Request Blocked` or `EventSource's response has a MIME type ("text/html") that is not "text/event-stream"`.
- **Resolution Playbook:**
  1. Confirm FastAPI CORS middleware includes `http://localhost:5173` and `http://127.0.0.1:5173`.
  2. Confirm SSE endpoint returns `text/event-stream` with headers `Cache-Control: no-cache` and `Connection: keep-alive`.
  3. Verify client `EventSource` reconnects with exponential backoff on network drop.

### 2.7 Windows Long Path & PowerShell Execution Policy Issues
- **Symptom:** File access fails with `FileNotFoundError` on nested directories, or PowerShell refuses to run the activation script (`.\.venv\Scripts\Activate.ps1`).
- **Resolution Playbook:**
  1. Enable Windows Long Path support in registry: Set `LongPathsEnabled=1` under `HKLM\SYSTEM\CurrentControlSet\Control\FileSystem`.
  2. Update PowerShell execution policy: Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`.

### 2.8 Python 3.14 & SQLAlchemy AsyncIO Greenlet Requirement
- **Symptom:** Backend crashes with `ImportError: The SQLAlchemy asyncio module requires that the Python 'greenlet' library is installed`.
- **Root Cause:** In Python 3.14+, `sqlalchemy.ext.asyncio` requires the native binary `greenlet` package for coroutine context switching.
- **Resolution Playbook:**
  1. Add `greenlet>=3.0.0` explicitly to `requirements.txt`.
  2. Install via pip: `pip install greenlet`.
  3. Run async engine verification via `python -c "from backend.app.core.database import check_db_connection"`.

### 2.9 Vite React TypeScript CSS Module Resolution Error
- **Symptom:** `npm run build` fails with `src/main.tsx: error TS2307: Cannot find module './index.css' or its corresponding type declarations`.
- **Root Cause:** TypeScript strict mode cannot resolve raw `.css` or asset imports without Vite client type definitions.
- **Resolution Playbook:**
  1. Ensure `frontend/src/vite-env.d.ts` exists.
  2. Add `/// <reference types="vite/client" />` inside `vite-env.d.ts`.
  3. Ensure `tsconfig.app.json` includes `src` in its `"include"` array.

### 2.10 React Refresh Only-Export-Components Lint Warnings
- **Symptom:** `npm run lint` warns `Fast refresh only works when a file only exports components`.
- **Root Cause:** Exporting both a React component and a non-component object or function (such as `cva()` variant objects or `createContext()` instances) in the same `.tsx` file violates fast refresh rules.
- **Resolution Playbook:**
  1. Extract CVA variants to dedicated TypeScript modules (e.g., `button-variants.ts`, `badge-variants.ts`).
  2. Extract React Context instances into `src/context/` (e.g., `ToastContext.ts`, `BackendHealthContext.ts`).
  3. Keep `.tsx` files strictly focused on exporting UI components or hooks.

### 2.11 React Router 6.28 Data Router Future Flag Types
- **Symptom:** TypeScript throws `TS2353: 'v7_startTransition' does not exist in type 'Partial<Omit<FutureConfig, "v7_prependBasename">>'`.
- **Root Cause:** In React Router 6.28+, `v7_startTransition` belongs to `<RouterProvider future={{ v7_startTransition: true }} />`, whereas `v7_relativeSplatPath` is passed to `createBrowserRouter(routes, { future: { ... } })`.
- **Resolution Playbook:**
  1. Configure `v7_relativeSplatPath: true` in `createBrowserRouter()`.
  2. Configure `v7_startTransition: true` on `<RouterProvider router={router} />`.

### 2.12 Pydantic v2 Schema Generation with Built-in `any` vs `typing.Any`
- **Symptom:** `pydantic.errors.PydanticSchemaGenerationError: Unable to generate pydantic-core schema for <built-in function any>`.
- **Root Cause:** Accidentally using lowercase Python built-in `any` (a function) instead of `typing.Any` in Pydantic schema type annotations (`Optional[any]` vs `Optional[Any]`).
- **Resolution Playbook:**
  1. Ensure `from typing import Any` is explicitly imported.
  2. Use uppercase `Any` for all wildcard generic type annotations in Pydantic models.

### 2.13 SQLite NOT NULL Constraints on Audio Stream Properties
- **Symptom:** `sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) NOT NULL constraint failed: videos.audio_sample_rate`.
- **Root Cause:** The `Video` model strictly enforces `audio_sample_rate` and `audio_channels` per `docs/04-DATABASE.md`. When constructing test video fixtures or mocking records, omitting these technical stream fields causes an immediate constraint violation.
- **Resolution Playbook:**
  1. Always provide valid audio properties (`audio_sample_rate=48000`, `audio_channels=2`) when instantiating `Video` instances.
  2. During video upload ingestion (Phase 09), verify that `ffprobe` extracts these fields before committing the parent record.

### 2.14 Starlette `HTTP_422_UNPROCESSABLE_ENTITY` Deprecation Warning
- **Symptom:** `StarletteDeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.`
- **Root Cause:** RFC 9110 renames HTTP status code 422 to "Unprocessable Content". Newer Starlette versions deprecate the older symbol.
- **Resolution Playbook:**
  1. Use `fastapi.status.HTTP_422_UNPROCESSABLE_CONTENT` (or raw status `422`) in all custom exception handlers.

### 2.15 Vite Fast Refresh Component Export Boundary Warning
- **Symptom:** ESLint warning: `Fast refresh only works when a file only exports components. Use a new file to share constants or functions between components (react-refresh/only-export-components)`.
- **Root Cause:** Exporting both CVA variant helper functions (`cardVariants`) and React components (`Card`, `CardHeader`) from the same `.tsx` file breaks Vite HMR fast refresh boundaries.
- **Resolution Playbook:**
  1. Separate CVA variants into a dedicated `*-variants.ts` file (e.g. `card-variants.ts`, `button-variants.ts`, `badge-variants.ts`).
  2. Re-export variants from the centralized `ui/index.ts`.

### 2.16 TypeScript ESLint `no-empty-object-type` on Props Interfaces
- **Symptom:** ESLint error: `An interface declaring no members is equivalent to its supertype (@typescript-eslint/no-empty-object-type)`.
- **Root Cause:** Declaring an empty interface extending HTMLAttributes without additional members (e.g., `export interface KbdProps extends React.HTMLAttributes<HTMLElement> {}`).
- **Resolution Playbook:**
  1. Declare as a type alias instead: `export type KbdProps = React.HTMLAttributes<HTMLElement>;`.

### 2.17 High Frontend Network Overhead from Multiple Polling Telemetry Requests
- **Symptom:** Workstation dashboard initial load triggered 5+ individual HTTP requests (`/health`, `/hardware`, `/videos`, `/jobs`, `/settings`), leading to request waterfall delays and redundant roundtrips.
- **Root Cause:** Decentralized endpoints requiring the client to stitch together high-level telemetry and entity counters.
- **Resolution Playbook:**
  1. Consolidate workstation overview data into `GET /api/v1/system/dashboard`.
  2. Aggregate entity counts, storage diagnostics, hardware telemetry, and top 5 recent videos/jobs inside a single async SQLAlchemy session with sub-15ms execution time under SQLite WAL.

### 2.18 Ambiguous Testing-Library DOM Matchers When Workstation Components Reuse Status Badges
- **Symptom:** Vitest error: `TestingLibraryElementError: Found multiple elements with the text: Processing` (or `42%`, `0`).
- **Root Cause:** Workstation cards and list items share badge strings and numerical progress values (e.g., video status badge and background job status badge both rendering "Processing").
- **Resolution Playbook:**
  1. Use `screen.getAllByText(...)` with assertions on element count (`expect(screen.getAllByText("Processing").length).toBeGreaterThanOrEqual(1)`) or scope queries to specific container elements (`within(container).getByText(...)`).

### 2.19 `MissingGreenlet` Exception During Async SQLAlchemy Serialization
- **Symptom:** Backend 500 error or pytest failure: `sqlalchemy.exc.StatementError: (sqlalchemy.exc.MissingGreenlet) greenlet_spawn has not been called`.
- **Root Cause:** Attempting to access an un-loaded lazy relationship attribute (such as `clip.video.filename` or `export.clip.title`) inside an async route handler without an explicit async greenlet context. SQLAlchemy 2.0 async sessions prohibit synchronous implicit I/O.
- **Resolution Playbook:**
  1. Never access un-eager-loaded relationships inside serialization helper routines.
  2. Perform explicit SQL joins in the query (`outerjoin(Video, Clip.video_id == Video.id)`) and select the required scalar columns directly (e.g., `Video.filename.label("video_filename")`).
  3. Pass the fetched scalar values into serialization functions as explicit arguments.

### 2.20 Option Dropdown Text Collisions in Component Tests
- **Symptom:** Vitest error: `TestingLibraryElementError: Found multiple elements with the text: Ready` when checking `<EntityStatusBadge>`.
- **Root Cause:** Filter select dropdowns render `<option value="READY">Ready</option>` in the DOM alongside rendered badge elements `<Badge>Ready</Badge>`.
- **Resolution Playbook:**
  1. Use `screen.getAllByText("Ready").length >= 1` or query the badge specifically via container scoping `within(container).getByText("Ready")`.

### 2.21 Missing `python-multipart` Dependency for FastAPI Form/File Uploads
- **Symptom:** FastAPI fails at startup or when receiving a multipart upload with: `RuntimeError: Form data requires "python-multipart" to be installed. Run "pip install python-multipart"`.
- **Root Cause:** FastAPI relies on Starlette's `formparser.py`, which lazily imports `python-multipart` when parsing `multipart/form-data` request payloads in endpoints using `UploadFile = File(...)`.
- **Resolution Playbook:**
  1. Add `python-multipart>=0.0.9` directly to `backend/requirements.txt`.
  2. Install via pip in the active virtual environment: `pip install "python-multipart>=0.0.9"`.
  3. Ensure all CI/CD and deployment installation scripts include `python-multipart`.

### 2.22 Duplicate Text Matcher Collisions Between Toast Notifications and Card Error Banners
- **Symptom:** Vitest error: `TestingLibraryElementError: Found multiple elements with the text: Unsupported format '.pdf'` or similar error messages.
- **Root Cause:** When an error occurs (such as client-side or server-side upload validation failure), the application emits both an ephemeral Toast notification (`toast.error(...)`) and an inline actionable error card (`Card variant="error"` or error banner). Both components render the identical error string simultaneously in the test DOM.
- **Resolution Playbook:**
  1. In unit tests asserting error visibility, use `screen.getAllByText(...)` and assert that at least one instance appears: `expect(screen.getAllByText(/Unsupported format/i).length).toBeGreaterThanOrEqual(1)`.
  2. Alternatively, query by accessible role or container: `within(screen.getByRole("alert")).getByText(...)`.

---

## 3. Automated Diagnostics Scripts (Planned for Phase 18)

During Phase 18, a standalone diagnostic script (`backend/scripts/diagnose.py`) will be developed to verify:
- NVIDIA GPU detection and free VRAM headroom via NVML.
- FFmpeg binary version and availability of `h264_nvenc` and `libass`.
- Write permissions and available SSD disk space across all `/storage/` directories.
- SQLite database integrity (`PRAGMA integrity_check;`).

---

## 4. Planned Sections for Phase 18–20 Specification

During Phase 18 through 20, this document will be expanded to include:
- Complete log format specifications and log level configurations.
- Windows Event Viewer integration for driver crash diagnosis.
- End-to-end trace debugging recipes.

---

## 5. Current Status & Next Steps

- **Status:** ACTIVE & EXPANDED (Phase 06, 07, 08, 09, 10, 11, 12 playbooks documented).
- **Phase 12 Ingestion Status:** Complete & Verified (streaming upload, ffprobe integrity checks, path containment, atomic storage).
- **Immediate Dependency:** Phase 13 Audio Extraction & Preprocessing Pipeline.
- **Execution Target:** Phase 18 through Phase 20 for full automation.
