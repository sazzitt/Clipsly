# Environment Setup & Developer Guide

**Project Name:** AI Video Clipper (Working Title: Clipsly)  
**Document Version:** 0.1.0  
**Status:** PLANNED (To be finalized and verified in Phase 04 / Phase 05)  
**Author:** DevOps & Technical Documentation Engineer  

---

## 1. Purpose of this Document

This document provides complete instructions for configuring the local developer environment, installing required host dependencies (Python, Node.js, FFmpeg with NVENC, CUDA/cuDNN), initializing virtual environments, configuring database storage, and running the application on the target **ASUS TUF A15 (AMD Ryzen 7, NVIDIA RTX 3050 4GB VRAM)** laptop.

---

## 2. Host System Prerequisites

| Dependency | Minimum Version | Recommended / Target | Verification Command |
|---|---|---|---|
| **Operating System** | Windows 10 (64-bit) | Windows 11 Home/Pro (Build 22621+) | `cmd /c ver` |
| **Python** | 3.10.x | 3.11.x (64-bit) | `python --version` |
| **Node.js** | 18.x LTS | 20.x LTS | `node --version` |
| **Package Manager** | npm 9+ | pnpm 9+ or npm 10+ | `pnpm --version` |
| **FFmpeg** | 6.0 (GPL build) | 7.0+ with `h264_nvenc` & `libass` | `ffmpeg -version` |
| **NVIDIA Driver** | 535.xx | 550.xx+ Game Ready or Studio Driver | `nvidia-smi` |
| **CUDA / cuDNN** | CUDA 12.1 | CUDA 12.2 / cuDNN 8.9+ | `nvcc --version` |

---

## 3. Hardware Verification Checklist

Before running the application, verify that GPU acceleration is active:

1. **Verify NVIDIA GPU & VRAM:**
   ```powershell
   nvidia-smi
   ```
   *Expected Output:* Confirms `NVIDIA GeForce RTX 3050 Laptop GPU` with `4096MiB` VRAM.
2. **Verify FFmpeg NVENC Acceleration:**
   ```powershell
   ffmpeg -encoders | findstr nvenc
   ```
   *Expected Output:* `h264_nvenc` and `hevc_nvenc` listed.
3. **Verify FFmpeg Subtitle Support (libass):**
   ```powershell
   ffmpeg -filters | findstr ass
   ```
   *Expected Output:* `ass` and `subtitles` filter availability.

---

## 4. Planned Setup Sequence (Phase 04 / Phase 05)

When Phase 04 begins, setup will proceed via the following structured sequence:

```powershell
# 1. Clone repository & enter workspace
cd clipsly

# 2. Setup Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install backend dependencies (Phase 04)
pip install --upgrade pip
pip install -r backend/requirements.txt

# 4. Setup frontend dependencies (Phase 05)
cd frontend
npm install
cd ..

# 5. Initialize SQLite Database & Local Storage Directories (Phase 04)
# Creates data/, data/backups/, storage/{uploads,audio,transcripts,clips,subtitles,exports,temp}
python -m backend.app.core.init_storage
alembic upgrade head

# 6. Launch development servers
# Terminal 1: Backend
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
# Terminal 2: Frontend
cd frontend && npm run dev
```

---

## 5. Planned Sections for Phase 04 Specification

During Phase 04, this document will be expanded to include:
- Automated single-command installation script (`setup.bat`).
- Pre-built FFmpeg Windows binary bundle instructions.
- Faster-Whisper CTranslate2 CUDA DLL resolution guide.
- Troubleshooting common Windows permission and path length issues.

---

## 6. Current Status & Next Steps

- **Status:** PLANNED.
- **Immediate Dependency:** Scaffolding in Phase 04.
- **Execution Target:** Phase 04.
