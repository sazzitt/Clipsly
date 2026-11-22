# Clipsly — Local-First AI Video Clipper

Clipsly is a sovereign, local-first multimedia desktop web application engineered to transform long-form video recordings (podcasts, lectures, interviews) into high-engagement, captioned 9:16 vertical short clips.

Operating entirely on local hardware (optimized for ASUS TUF A15 with NVIDIA RTX 3050 4GB VRAM), Clipsly processes media strictly on your machine with zero cloud dependencies, zero subscription fees, and complete data privacy.

---

## Technical Stack

- **Frontend:** React 18, Vite 5, TypeScript 5, Tailwind CSS, shadcn/ui, Lucide Icons
- **Backend:** Python 3.14 / 3.10+, FastAPI, Uvicorn, Pydantic v2
- **Database:** SQLite 3 (WAL mode) via SQLAlchemy 2.0 Async & aiosqlite, Alembic
- **Media Pipeline:** FFmpeg 7+ (with NVIDIA NVENC `h264_nvenc` and `libass`)
- **Speech-to-Text:** Faster-Whisper (CTranslate2) with Silero VAD
- **Highlight Engine:** Heuristic 4D Scoring Engine with optional external AI augmentation

---

## Quick Start (Development)

### 1. Prerequisites
- **Windows 11 (64-bit)**
- **Python 3.10+ (64-bit)**
- **Node.js 18+ LTS** and **npm**
- **FFmpeg 6.0+** with `h264_nvenc` and `libass` on system `PATH`
- **NVIDIA GPU** with updated Studio/Game-Ready drivers

### 2. Backend Setup
```powershell
# In repository root
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
alembic upgrade head
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```

---

## Documentation Index

The complete 15-file architectural and product documentation suite resides in [`docs/`](docs/):

- [`docs/01-PRD.md`](docs/01-PRD.md) — Product Requirements Document (29 sections + 20-phase roadmap)
- [`docs/02-DESIGN.md`](docs/02-DESIGN.md) — UI/UX Design System & 14 screen wireframes
- [`docs/03-ARCHITECTURE.md`](docs/03-ARCHITECTURE.md) — System Architecture, 4GB VRAM strategy, ADRs
- [`docs/04-DATABASE.md`](docs/04-DATABASE.md) — SQLite Schema, ER diagram, local storage engine
- [`docs/05-API.md`](docs/05-API.md) — 40 REST endpoints, Pydantic schemas, SSE protocol
- [`docs/06-AGENTS.md`](docs/06-AGENTS.md) — 12 processing modules/agents & pipeline workflow
- [`docs/07-README.md`](docs/07-README.md) — Master documentation index
- [`docs/08-PROJECT-IMPLEMENTATION.md`](docs/08-PROJECT-IMPLEMENTATION.md) — Implementation blueprint
- [`docs/09-SETUP.md`](docs/09-SETUP.md) — Developer setup guide
- [`docs/14-TESTING-AND-QA.md`](docs/14-TESTING-AND-QA.md) — Testing strategy & QA plan
- [`docs/15-DEBUGGING.md`](docs/15-DEBUGGING.md) — Troubleshooting playbooks
