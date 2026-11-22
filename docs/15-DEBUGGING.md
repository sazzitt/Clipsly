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

### 2.5 Windows Long Path & PowerShell Execution Policy Issues
- **Symptom:** File access fails with `FileNotFoundError` on nested directories, or PowerShell refuses to run the activation script (`.\.venv\Scripts\Activate.ps1`).
- **Resolution Playbook:**
  1. Enable Windows Long Path support in registry: Set `LongPathsEnabled=1` under `HKLM\SYSTEM\CurrentControlSet\Control\FileSystem`.
  2. Update PowerShell execution policy: Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`.

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

- **Status:** PLANNED.
- **Immediate Dependency:** Job queue and watchdog implementation in Phase 17 and Phase 18.
- **Execution Target:** Phase 18 through Phase 20.
