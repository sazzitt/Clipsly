# Feature Development Workflow

**Project Name:** AI Video Clipper (Working Title: Clipsly)  
**Document Version:** 0.1.0  
**Status:** PLANNED (To guide feature development in Phases 06 through 16)  
**Author:** Software Architect & Engineering Manager  

---

## 1. Purpose of this Document

This document establishes the Standard Operating Procedure (SOP) for developing, testing, and integrating new features into the AI Video Clipper platform.

Because this application operates on constrained local hardware (4GB VRAM GPU), every new feature—whether an audio analysis routine, an AI scoring heuristic, or a video filtergraph—must undergo strict memory, latency, and regression checks before merging into the main codebase.

---

## 2. Feature Development Lifecycle

Every feature follows a disciplined 5-stage lifecycle:

```
[1. Proposal & Memory Audit] ──> [2. Backend Service Draft] ──> [3. REST / SSE Contract]
                                                                        │
                                                                        ▼
[5. Regression & VRAM Benchmarking] <── [4. Frontend Studio Integration]
```

1. **Stage 1: Proposal & Memory Audit:** Evaluate VRAM and CPU impact. If a proposed feature consumes GPU memory during an existing task, it must be refactored into a sequential lifecycle stage.
2. **Stage 2: Backend Service Draft:** Implement pure Python logic in `backend/app/services/` with comprehensive pytest unit tests.
3. **Stage 3: REST / SSE Contract:** Expose typed Pydantic models and endpoint routes in `backend/app/api/v1/`.
4. **Stage 4: Frontend Studio Integration:** Build UI components with Tailwind CSS and shadcn/ui; connect API client services.
5. **Stage 5: Regression & VRAM Benchmarking:** Run the end-to-end test suite on the ASUS TUF A15 to ensure peak VRAM remains $\le 3.5\text{ GB}$.

---

## 3. Extension Guides (Cookbooks)

### 3.1 Adding a New Subtitle Style Template
1. Create a new ASS styling profile in `backend/app/services/subtitles/templates.py`.
2. Define font name, primary color, karaoke highlight color, stroke, outline, and shadow values.
3. Add a corresponding visual preview card in `frontend/src/components/studio/StylePicker.tsx`.
4. Verify rendering output using `pytest tests/test_subtitles.py`.

### 3.2 Extending Highlight Detection Heuristics
1. Implement the scoring function in `backend/app/services/ai/highlight_heuristics.py`.
2. Ensure input accepts standard sentence utterance models with timestamps.
3. Normalize scoring output to a deterministic range $[0, 100]$.
4. Verify performance: scoring a 1-hour transcript must execute in $< 5\text{ seconds}$ on CPU.

### 3.3 Adding a New Video Output Aspect Ratio (e.g., 1:1 Square or 4:5 Portrait)
1. Add new enum key to `backend/app/models/clip.py` (`AspectRatioMode`).
2. Add corresponding FFmpeg filtergraph formula in `backend/app/services/media/reframer.py`.
3. Update aspect ratio toggle in `frontend/src/components/studio/AspectRatioToggle.tsx`.

---

## 4. Planned Sections for Phase 06–16 Specification

As feature development progresses, this document will be updated with:
- Standardized Git branch naming conventions (`feat/`, `fix/`, `perf/`).
- Subprocess error handling templates.
- End-to-end integration checklist before PR approval.

---

## 5. Current Status & Next Steps

- **Status:** PLANNED.
- **Immediate Dependency:** Scaffolding complete in Phase 04 and Phase 05.
- **Execution Target:** Phase 06 through Phase 16.
