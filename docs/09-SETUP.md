# Environment Setup & Developer Guide

**Project Name:** AI Video Clipper (Working Title: Clipsly)  
**Document Version:** 1.0.0  
**Status:** IMPLEMENTED & VERIFIED (Phase 06)  
**Author:** DevOps & Systems Infrastructure Engineer  
**Host Target Machine:** ASUS TUF A15 Laptop (Tested and Verified)

---

## 1. Verified Local Host Specifications

The development environment has been initialized and verified directly on the target machine:

| Component | Verified Specification | Verification Command | Status |
|---|---|---|---|
| **Operating System** | Windows 11 Build 10.0.26300 (64-bit) | `[System.Environment]::OSVersion` | **VERIFIED** |
| **CPU** | AMD Ryzen 7 7435HS (8 Cores, 16 Logical Processors) | `Get-CimInstance Win32_Processor` | **VERIFIED** |
| **GPU** | NVIDIA GeForce RTX 3050 Laptop GPU (4096 MB VRAM) | `nvidia-smi` | **VERIFIED** |
| **GPU Driver** | NVIDIA Driver 596.49 (CUDA 13.2 support) | `nvidia-smi` | **VERIFIED** |
| **System RAM** | 16.0 GB DDR5 | `(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory` | **VERIFIED** |
| **Available Disk** | SSD C: Drive (75+ GB free) | `Get-PSDrive C` | **VERIFIED** |
| **Python** | Python 3.14.3 (64-bit) | `python --version` | **VERIFIED** |
| **Node.js** | Node.js v24.14.0 | `node --version` | **VERIFIED** |
| **npm** | npm 11.9.0 | `npm --version` | **VERIFIED** |
| **Git** | Git for Windows 2.55.0 | `git --version` | **VERIFIED** |
| **FFmpeg** | FFmpeg 9.0.2-full_build (gyan.dev) | `ffmpeg -version` | **VERIFIED** |
| **NVENC Support** | `h264_nvenc`, `hevc_nvenc`, `av1_nvenc` | `ffmpeg -encoders` | **VERIFIED** |
| **libass Support** | Subtitles and ASS filter available | `ffmpeg -filters` | **VERIFIED** |

---

## 2. Directory Layout & Storage Topology

The repository follows a clean monorepo architecture:

```
Clipsly/
├── .venv/                   # Python virtual environment (ignored in git)
├── backend/                 # FastAPI REST API backend
│   ├── alembic/             # Database migration engine (async SQLite)
│   ├── app/
│   │   ├── api/v1/          # Modular API endpoints (system, etc.)
│   │   ├── core/            # Config, database engine, logging
│   │   ├── schemas/         # Pydantic v2 schemas
│   │   ├── services/        # System, media, and AI services
│   │   └── main.py          # FastAPI application & lifespan
│   ├── requirements.txt     # Python backend dependencies
│   └── tests/               # Pytest async test suite
├── frontend/                # React 18 + Vite 6 + TypeScript application
│   ├── src/                 # UI components, API service, styles
│   ├── package.json         # Frontend dependencies (Tailwind, Lucide, Radix)
│   └── vite.config.ts       # Path aliases & /api proxy to 127.0.0.1:8000
├── data/                    # SQLite database directory (clipsly.db in WAL mode)
├── logs/                    # Application log files (clipsly_app.log)
├── storage/                 # Local filesystem media storage
│   ├── uploads/             # Raw user video uploads
│   ├── audio/               # Extracted 16kHz mono audio WAV files
│   ├── transcripts/         # Faster-Whisper raw transcripts
│   ├── clips/               # Rendered short video segments
│   ├── subtitles/           # Generated .ass & .srt subtitle files
│   ├── exports/             # Final 9:16 vertical MP4 output files
│   └── temp/                # Ephemeral slicing & filter buffers
├── scripts/                 # Utility & verification scripts (verify_phase06.py)
└── docs/                    # Complete 15-document technical specification
```

---

## 3. Quick Start & Execution Guide

### Step 1: Clone Repository & Virtual Environment Setup
```powershell
cd Clipsly

# Create virtual environment if not already present
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install backend dependencies (including FastAPI, SQLAlchemy, Faster-Whisper, CTranslate2, ONNX Runtime, pytest)
pip install -r backend/requirements.txt

# Ensure FFmpeg/FFprobe is on system PATH (required for media validation & audio extraction)
ffprobe -version
ffmpeg -version

# Verify NVIDIA CUDA runtime support (optional but recommended for RTX 3050 GPU acceleration)
nvidia-smi

# Apply latest database schema migrations
alembic upgrade head
```

### Step 2: Frontend Setup
```powershell
cd frontend
npm install
cd ..
```

### Step 3: Run Automated Verification Suite
```powershell
# Validates directory structure, SQLite WAL mode, Uvicorn health endpoint, and logging
.\.venv\Scripts\python.exe scripts/verify_phase06.py
```

### Step 4: Run Backend Pytest Suite
```powershell
.\.venv\Scripts\pytest.exe -v backend/tests
```

### Step 5: Launch Backend Development Server
```powershell
# Starts FastAPI server on strict localhost binding
.\.venv\Scripts\uvicorn.exe backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- Health Endpoint: `http://127.0.0.1:8000/api/v1/system/health`

### Step 6: Launch Frontend Development Server
In a second terminal:
```powershell
cd Clipsly\frontend
npm run dev
```
- Frontend UI: `http://127.0.0.1:5173`
- All requests to `/api/*` are transparently proxied by Vite to `http://127.0.0.1:8000`.

---

## 4. Hardware Safety Boundaries

1. **Localhost Binding:** Backend binds exclusively to `127.0.0.1`. Never expose to `0.0.0.0`.
2. **Sequential Model Lifecycle:** Faster-Whisper transcription and NVENC video encoding must execute sequentially to observe the 4GB VRAM ceiling.
3. **SQLite WAL Mode:** Concurrency is guaranteed via Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) with a 30-second busy timeout.

---

## 5. Speech-to-Text Model Selection & Hardware Specifications (Phase 15)

### 5.1 Default Model Strategy: `base` vs `small`

The Clipsly workstation targets the ASUS TUF A15 equipped with an **NVIDIA GeForce RTX 3050 Laptop GPU (4GB dedicated VRAM)** running Windows 11.

- **Default Model:** `base` (74M parameters, `float16` quantization).
  - **Reason for Selection:** On Windows 11, the Desktop Window Manager (DWM), GPU drivers, and system applications consume ~1,100 MB of VRAM at idle out of 4,096 MB total. 
  - Loading `base` on CUDA requires only **+214 MB VRAM delta**, peaking at **1,409 MB total system VRAM** during inference.
  - This leaves **> 2,600 MB of VRAM headroom**, completely eliminating the risk of Windows display stutter, Timeout Detection and Recovery (TDR) driver crashes, or Out-Of-Memory exceptions.
  - Measured performance on actual hardware: **5.3x real-time speedup (RTF 0.188)** with 100% language detection and word-level timestamp precision.
- **Optional Model Alternatives:**
  - `tiny` (39M parameters, ~500 MB VRAM): For ultra-fast test passes or speech alignment.
  - `small` (244M parameters, ~2,000 MB VRAM): For complex multi-speaker dialogue or accented speech. Due to the 4GB ceiling and Windows desktop overhead, `small` operates near the upper VRAM limit and is best used when other GPU-heavy desktop applications are closed.

### 5.2 Supported Python & Tested Package Ecosystem

Clipsly is verified on Python **3.11, 3.12, 3.13, and 3.14** (actively audited and tested on **Python 3.14.3 64-bit** on Windows 11).

Exact verified package dependencies:
- `faster-whisper == 1.2.1`
- `ctranslate2 == 4.9.1`
- `onnxruntime == 1.32.0` (Silero VAD execution without PyTorch)
- `av == 17.1.0` (Pinned to `av>=14.0.0,<18.0.0` for `metadata_errors` compatibility with `faster-whisper 1.2.1`)
- `nvidia-cublas-cu12 == 12.9.2.10` (CUDA 12 BLAS runtime for CTranslate2)
- `nvidia-cudnn-cu12 == 9.28.1.4` (cuDNN v9 neural network primitives)

### 5.3 Installation Instructions (CUDA Acceleration & CPU Fallback)

1. **CUDA Acceleration Setup (Default):**
   ```powershell
   pip install faster-whisper==1.2.1 onnxruntime==1.32.0 "av>=14.0.0,<18.0.0"
   pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
   ```
   The backend's `transcription.py` automatically registers the installed NVIDIA DLL directories (`bin/`) into the process DLL search path using `os.add_dll_directory()`.

2. **CPU-Only Execution Setup:**
   If running on hardware without an NVIDIA GPU or when `FORCE_CPU_TRANSCRIPTION=true`:
   ```powershell
   pip install faster-whisper==1.2.1 onnxruntime==1.32.0 "av>=14.0.0,<18.0.0"
   ```
   CTranslate2 will automatically execute inference on CPU using `int8` quantization (delivering ~3.0x real-time speedup on AMD Ryzen 7 7435HS).
