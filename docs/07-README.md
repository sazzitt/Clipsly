# AI Video Clipper (Clipsly) — Project Documentation Index

Welcome to the central technical documentation suite for **AI Video Clipper** (working title: **Clipsly**), a sovereign, local-first web application designed to automatically convert long-form video files into high-impact, captioned 9:16 vertical short clips.

All project requirements, architecture specifications, database designs, API contracts, security profiles, and operational guides are documented across this 15-file suite located in `docs/`.

---

## Master Documentation Index

| File | Document Title | Description & Purpose | Phase | Current Status |
|---|---|---|---|---|
| [01-PRD.md](file:///c:/Users/SAJIT%20THAKUR/OneDrive/Pictures/Documents/clipsly/docs/01-PRD.md) | **Product Requirements Document** | Complete product requirements, user stories, functional/non-functional requirements, hardware constraints, 16-step user workflow, and 20-phase roadmap. | Phase 01 | **COMPLETE (APPROVED)** |
| [02-DESIGN.md](file:///c:/Users/SAJIT%20THAKUR/OneDrive/Pictures/Documents/clipsly/docs/02-DESIGN.md) | **UI/UX Design Specifications** | Design system tokens, 14 screen wireframes, dark workstation UI styling, layout grids, shadcn/ui components, and interactive studio UX patterns. | Phase 05 | **COMPLETE (APPROVED)** |
| [03-ARCHITECTURE.md](file:///c:/Users/SAJIT%20THAKUR/OneDrive/Pictures/Documents/clipsly/docs/03-ARCHITECTURE.md) | **System Architecture & Hardware Strategy** | High-level system topology, process boundaries, 4GB VRAM allocation budget, FFmpeg media pipeline, sequential model lifecycle, and ADRs. | Phase 02 | **COMPLETE (APPROVED)** |
| [04-DATABASE.md](file:///c:/Users/SAJIT%20THAKUR/OneDrive/Pictures/Documents/clipsly/docs/04-DATABASE.md) | **Database Schema & Storage Engine** | SQLite database architecture, Entity-Relationship (ER) model, 8 table schemas, index strategies, WAL mode configuration, and local filesystem directory tree. | Phase 03 | **COMPLETE (APPROVED)** |
| [05-API.md](file:///c:/Users/SAJIT%20THAKUR/OneDrive/Pictures/Documents/clipsly/docs/05-API.md) | **FastAPI REST API Specification** | Comprehensive OpenAPI contracts, 40 endpoint schemas, error status codes, video upload contracts, and Server-Sent Events (SSE) progress streams. | Phase 04 | **COMPLETE (APPROVED)** |
| [06-AGENTS.md](file:///c:/Users/SAJIT%20THAKUR/OneDrive/Pictures/Documents/clipsly/docs/06-AGENTS.md) | **AI Agent Architecture & Processing Pipeline** | 12 logical processing modules/agents, end-to-end 14-stage pipeline sequence diagram, 4D heuristic scoring formulas, and hardware execution rules. | Phase 05 | **COMPLETE (APPROVED)** |
| [07-README.md](file:///c:/Users/SAJIT%20THAKUR/OneDrive/Pictures/Documents/clipsly/docs/07-README.md) | **Master Documentation Index** | Central index, document navigation, stack summary, hardware guidelines, and phase tracker (this document). | Phase 01 / 02 | **COMPLETE (ACTIVE)** |
| [08-PROJECT-IMPLEMENTATION.md](file:///c:/Users/SAJIT%20THAKUR/OneDrive/Pictures/Documents/clipsly/docs/08-PROJECT-IMPLEMENTATION.md) | **Project Implementation Blueprint** | Codebase directory structure, module separation of concerns, coding conventions, typing standards, and design patterns. | Phase 06 | **IMPLEMENTED (FOUNDATIONS ACTIVE)** |
| [09-SETUP.md](file:///c:/Users/SAJIT%20THAKUR/OneDrive/Pictures/Documents/clipsly/docs/09-SETUP.md) | **Environment Setup & Developer Guide** | Host prerequisites (Python 3.14+, Node.js 24+, FFmpeg 9.0+ with NVENC, CUDA), virtual environment configuration, and tested startup instructions. | Phase 06 | **VERIFIED (TESTED ON ASUS TUF A15)** |
| [10-FEATURE-DEVELOPMENT.md](file:///c:/Users/SAJIT%20THAKUR/OneDrive/Pictures/Documents/clipsly/docs/10-FEATURE-DEVELOPMENT.md) | **Feature Development Workflow** | Standard operating procedure for introducing new features, adding subtitle styling templates, extending aspect ratios, and adding video codecs. | Phase 10–16 | *PLANNED* |
| [11-AUTHENTICATION-AND-SECURITY.md](file:///c:/Users/SAJIT%20THAKUR/OneDrive/Pictures/Documents/clipsly/docs/11-AUTHENTICATION-AND-SECURITY.md) | **Security & Privacy Architecture** | Threat model, local loopback isolation, path traversal sanitization, subprocess sandboxing, and zero-telemetry enforcement. | Phase 04 | *PLANNED* |
| [12-MCP-CONNECTION.md](file:///c:/Users/SAJIT%20THAKUR/OneDrive/Pictures/Documents/clipsly/docs/12-MCP-CONNECTION.md) | **Model Context Protocol (MCP) Integration** | MCP server schemas and tool definitions allowing external AI agents to query local transcripts, trigger clips, and inspect render jobs. | Phase 17+ | *PLANNED* |
| [13-INTEGRATIONS.md](file:///c:/Users/SAJIT%20THAKUR/OneDrive/Pictures/Documents/clipsly/docs/13-INTEGRATIONS.md) | **Subprocess & Library Integrations** | Detailed integration contracts for FFmpeg/FFprobe, Faster-Whisper, Silero VAD, NVIDIA NVENC, and managed subprocess isolation. | Phase 06–16 | **FINALIZED (ADR-006)** |
| [14-TESTING-AND-QA.md](file:///c:/Users/SAJIT%20THAKUR/OneDrive/Pictures/Documents/clipsly/docs/14-TESTING-AND-QA.md) | **Testing Strategy & QA Plan** | Backend test suite (pytest), frontend build & lint verification, health check testing, and automated foundation validator script. | Phase 06 / 19 | **ACTIVE (PHASE 06 SUITE PASSING)** |
| [15-DEBUGGING.md](file:///c:/Users/SAJIT%20THAKUR/OneDrive/Pictures/Documents/clipsly/docs/15-DEBUGGING.md) | **Troubleshooting & Diagnostics** | Diagnostic playbooks for CUDA OOM errors, missing FFmpeg codecs, long Windows path issues, greenlet async SQLite, and subprocess hangs. | Phase 06 / 18 | **ACTIVE (FOUNDATION PLAYBOOKS ADDED)** |

---

## Core Technology Stack Summary

- **Platform:** Single-user, local-first desktop web application.
- **Frontend:** React 18, Vite 6, TypeScript 5, Tailwind CSS 3, shadcn/ui foundation, Lucide Icons.
- **Backend:** Python 3.14.3, FastAPI 0.115+, Uvicorn, Pydantic v2.10+, SQLAlchemy 2.0+ (asyncio with greenlet), aiosqlite, Alembic 1.13+.
- **Database:** SQLite 3 (WAL mode, foreign_keys=ON, busy_timeout=30000ms).
- **Video & Audio Processing:** FFmpeg 9.0.2 with FFprobe, NVIDIA NVENC (`h264_nvenc`) hardware acceleration, and CPU fallback (`libx264`).
- **Speech-to-Text:** Faster-Whisper (CTranslate2) with Silero VAD.
- **Highlight Detection:** Hybrid architecture with deterministic heuristic baseline + optional external API (ADR-003).
- **Target Hardware:** ASUS TUF A15 Laptop (AMD Ryzen 7 7435HS, NVIDIA RTX 3050 Laptop GPU with 4GB VRAM, 16GB DDR5 RAM, 512GB NVMe SSD).

---

## Target Hardware Constraint Rule

> [!CAUTION]
> **Strict 4GB VRAM Budget:**
> The NVIDIA RTX 3050 Laptop GPU has **4GB of GDDR6 VRAM**. Approximately 1300MB is utilized by Windows DWM and background desktop applications.
> 
> **Execution Rule (ADR-002):** Whisper transcription, highlight inference, and NVENC video encoding must execute **sequentially**. Faster-Whisper is deallocated and memory explicitly evacuated before video rendering begins.

---

## Development Phase Progress

- [x] **Phase 01:** Complete Project Documentation & PRD *(Approved)*
- [x] **Phase 02:** System Architecture & Hardware Strategy *(Approved)*
- [x] **Phase 03:** Database Schema & Local Storage Engine *(Approved)*
- [x] **Phase 04:** API Design & Contracts *(Approved)*
- [x] **Phase 05:** UI/UX Design + AI Agents & Processing Workflow *(Complete)*
- [x] **Phase 06:** Development Environment & Project Setup *(Completed & Verified)*
- [x] **Phase 07:** Frontend Foundation & Application Architecture *(Completed & Verified)*
- [x] **Phase 08:** Backend Foundation & API Infrastructure *(Completed & Verified)*
- [ ] **Phase 09:** Local Video Upload & Ingestion Pipeline *(Next)*
- [ ] **Phase 10:** Audio Extraction & Media Metadata Pipeline
- [ ] **Phase 11:** AI Highlight Detection & Scoring Engine
- [ ] **Phase 12:** Candidate Selection & Clip Timestamp Generator
- [ ] **Phase 13:** FFmpeg Cutting & Clip Generation Engine
- [ ] **Phase 14:** Vertical 9:16 Re-Framing Engine (Crop & Blur-Fill)
- [ ] **Phase 15:** Subtitle Generation & Karaoke Styler (.ass/burned-in)
- [ ] **Phase 16:** Interactive Clip Studio (Preview & Fine Trimming)
- [ ] **Phase 17:** Video Export & NVENC Hardware Acceleration
- [ ] **Phase 18:** Job Queue & Background Task Management
- [ ] **Phase 19:** End-to-End Testing & Performance Profiling
- [ ] **Phase 20:** Packaging, Documentation Finalization & Release
