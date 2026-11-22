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
   - **Backend (Pytest):** Models, Pydantic validation, subtitle ASS formatting, timestamp calculation, heuristic scoring math.
   - **Frontend (Vitest + React Testing Library):** UI component rendering, trim slider drag bounds, state management.
2. **Integration Testing:**
   - Database operations (SQLite WAL concurrent reads/writes).
   - FastAPI endpoint response models and error status codes.
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

## 5. Planned Sections for Phase 19 Specification

During Phase 19, this document will be expanded to include:
- Complete automated test suite commands (`pytest --cov`, `pnpm test`).
- Continuous integration (CI) workflow for GitHub Actions (running CPU mock suites).
- Benchmarking report template recording RTF, render times, and memory logs across 10-minute, 30-minute, and 60-minute test inputs.

---

## 6. Current Status & Next Steps

- **Status:** PLANNED.
- **Immediate Dependency:** Completion of functional phases (Phases 04 through 18).
- **Execution Target:** Phase 19.
