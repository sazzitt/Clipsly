# Database Schema & Storage Engine

**Project Name:** AI Video Clipper (Working Title: Clipsly)  
**Document Version:** 0.1.0  
**Status:** PLANNED (Scheduled for Detailed Specification & Schema Finalization in Phase 03)  
**Author:** Software Architect & Database Engineer  

---

## 1. Purpose of this Document

This document defines the relational database architecture, entity relationships, data schemas, indexing strategies, and local filesystem directory conventions for the AI Video Clipper application.

The database must reliably persist metadata for ingested videos, raw and segmented speech transcripts, word-level timestamps, candidate highlights, user-customized clip configurations, and background export job logs, while operating with zero server administration overhead.

---

## 2. Confirmed Architectural Decisions

1. **Database Engine:** Embedded **SQLite 3** (`data/clipsly.db`).
2. **Journaling Mode:** Write-Ahead Logging (`PRAGMA journal_mode=WAL;`), enabling concurrent non-blocking reads while background workers execute writes.
3. **Synchronous Mode:** `PRAGMA synchronous=NORMAL;` for optimal SSD write throughput without risking file corruption.
4. **Busy Timeout:** `PRAGMA busy_timeout=30000;` (30 seconds) to prevent lock contention between the API server and async background workers.
5. **Foreign Key Enforcement:** `PRAGMA foreign_keys=ON;` enabled on every connection.

---

## 3. Proposed Schema Entities (Under Evaluation for Phase 03)

The system plans seven core relational tables:

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    videos    │──────<│ transcripts  │──────<│  utterances  │
└──────┬───────┘       └──────────────┘       └──────────────┘
       │
       │               ┌──────────────┐       ┌──────────────┐
       ├──────────────<│  highlights  │──────<│    clips     │
       │               └──────────────┘       └──────┬───────┘
       │                                             │
       │               ┌──────────────┐              │
       └──────────────<│ export_jobs  │>─────────────┘
                       └──────────────┘
```

### Entity Overview:
1. **`videos`:** Stores file metadata (original filename, storage path, file size, duration, width, height, FPS, audio codecs, ingestion timestamp, status).
2. **`transcripts`:** Stores high-level transcription metadata (video ID reference, Faster-Whisper model used, spoken language, full text body, processing duration).
3. **`utterances` (or `transcript_segments`):** Stores fine-grained dialogue chunks and individual word-level timestamp arrays (start ms, end ms, word text, confidence score).
4. **`highlights`:** Stores algorithmically detected candidate segments (video ID reference, start ms, end ms, duration, hook score, coherence score, composite score, category).
5. **`clips`:** Stores configured short-form clips (highlight reference, custom start/end trim offsets, aspect ratio mode, subtitle styling preset ID, status).
6. **`export_jobs`:** Tracks rendering tasks (clip ID reference, export profile, output MP4 path, progress percentage, error message, execution duration).
7. **`settings`:** Key-value store for user preferences (default clip duration, default subtitle font, Whisper model preference, hardware flags).

---

## 4. Local Filesystem Storage Organization

All non-relational binary assets reside in the `/storage` directory on the local SSD:

- `/storage/uploads/`: Raw uploaded source video files.
- `/storage/audio/`: Extracted 16kHz mono PCM WAV files.
- `/storage/transcripts/`: Raw JSON backup exports of Whisper transcripts.
- `/storage/clips/`: Lossless intermediate video cuts.
- `/storage/subtitles/`: Generated `.ass` and `.srt` subtitle scripts.
- `/storage/exports/`: Production-ready rendered 1080x1920 MP4 files.
- `/storage/temp/`: Scratch directory for FFmpeg intermediate filter passes.

---

## 5. Planned Sections for Phase 03 Specification

During Phase 03, this document will be fully expanded to include:
- Complete SQL DDL definitions (`CREATE TABLE`, constraints, defaults).
- Indexing specifications (`CREATE INDEX`) optimizing timestamp and status queries.
- ORM decision and implementation (SQLModel vs. SQLAlchemy 2.0 Async).
- Database migration strategy using Alembic.
- Storage retention and automatic orphan cleanup algorithms.

---

## 6. Current Status & Next Steps

- **Status:** PLANNED.
- **Immediate Dependency:** Phase 02 Architecture finalization.
- **Execution Target:** Phase 03.
