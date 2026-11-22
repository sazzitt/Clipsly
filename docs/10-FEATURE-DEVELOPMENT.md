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

### 3.4 Adding a New Frontend Feature Route
1. Create a feature directory inside `frontend/src/features/<feature>/`.
2. Implement the route-level page component using `<PageContainer>` and design system primitives from `components/ui/`.
3. Add typed endpoint methods in `frontend/src/services/api.ts` adhering to `types/api.ts`.
4. Register the route in `frontend/src/app/router.tsx` and add navigation entries to `Sidebar.tsx`.
5. Add unit and route tests under `frontend/src/test/`.
6. Run `npm run lint`, `npm run build`, and `npm test` before committing.

### 3.5 Adding a New API Endpoint or Database Entity
1. **Adding an ORM Model:** Define model inheriting `Base` and `TimestampMixin` in `backend/app/models/`. Export in `backend/app/models/__init__.py`.
2. **Generating Migrations:** Run `alembic revision --autogenerate -m "add_table_name"` and `alembic upgrade head`.
3. **Defining Pydantic Schemas:** Create request/response schemas in `backend/app/schemas/`.
4. **Creating Endpoint Handlers:** Implement router under `backend/app/api/v1/`. Use `get_database` dependency and standard error exceptions (`NotFoundError`, `ValidationError`, etc.).
5. **Mounting Router:** Register router in `backend/app/api/router.py`.
6. **Writing Tests:** Add integration tests in `backend/tests/` verifying success and standardized error envelopes.
7. **Verifying Suite:** Run `.\.venv\Scripts\pytest.exe -v backend/tests` to confirm zero regressions.

---

## 4. Operational Status & Next Steps

- **Status:** ACTIVE (Phase 08 Complete).
- **Current Baseline:** Backend API infrastructure, 8 ORM models, Alembic migrations, 3 middlewares, 24 pytest tests passing; Frontend architecture with 11 routes and 20 Vitest tests passing.
- **Next Phase:** Phase 09 (Local Video Upload & Chunked Ingestion Pipeline).
