# Clipsly Phase 18 — Subtitle API Contracts & Data Model Specification

## 1. Specification Overview

This document defines the REST API endpoints, Pydantic v2 schemas, and relational database data models for the **Clipsly Subtitle & Caption Engine (Phase 18)**.

All endpoints strictly follow Clipsly's API conventions:
- Base prefix: `/api/v1/`
- JSON payloads with `camelCase` or standard Pydantic snake_case serialization matching existing endpoints.
- Consistent error envelopes conforming to `ErrorResponse` (`error_code`, `detail`, `error`).
- Local loopback isolation (`127.0.0.1`).

---

## 2. Database Schema & Entities

The subtitle architecture introduces two primary normalized tables (`subtitle_tracks` and `subtitle_events`) and one declarative configuration table (`subtitle_presets`).

```
+-----------------------------------------------------------------------------------------+
|                                SUBTITLE RELATIONAL SCHEMA                               |
+-----------------------------------------------------------------------------------------+
|                                                                                         |
|   CLIPS (Existing)                                                                      |
|   - id (PK)                                                                             |
|   - video_id (FK -> videos.id)                                                          |
|   - start_ms, end_ms, duration_ms                                                       |
|                                                                                         |
|       | 1                                                                               |
|       |                                                                                 |
|       | 0..N (Cascade Delete)                                                           |
|       v                                                                                 |
|   SUBTITLE_TRACKS                                                                       |
|   - id: VARCHAR(36) PK                                                                  |
|   - clip_id: VARCHAR(36) FK -> clips.id ON DELETE CASCADE                               |
|   - transcript_id: VARCHAR(36) FK -> transcripts.id ON DELETE SET NULL                  |
|   - preset_name: VARCHAR(64) NOT NULL DEFAULT 'KARAOKE_AMBER'                           |
|   - is_enabled: BOOLEAN NOT NULL DEFAULT 1                                              |
|   - is_active: BOOLEAN NOT NULL DEFAULT 1                                               |
|   - language: VARCHAR(16) NOT NULL DEFAULT 'en'                                         |
|   - ass_file_path: VARCHAR(512) NULL                                                    |
|   - compile_status: VARCHAR(32) NOT NULL DEFAULT 'DRAFT'                                |
|   - custom_style_overrides: TEXT NULL (JSON Object)                                     |
|   - created_at, updated_at                                                              |
|                                                                                         |
|       | 1                                                                               |
|       |                                                                                 |
|       | 1..N (Cascade Delete)                                                           |
|       v                                                                                 |
|   SUBTITLE_EVENTS                                                                       |
|   - id: VARCHAR(36) PK                                                                  |
|   - track_id: VARCHAR(36) FK -> subtitle_tracks.id ON DELETE CASCADE                     |
|   - sequence_index: INTEGER NOT NULL                                                    |
|   - start_ms: INTEGER NOT NULL (Clip-relative)                                          |
|   - end_ms: INTEGER NOT NULL (Clip-relative)                                            |
|   - text: TEXT NOT NULL                                                                 |
|   - words_json: TEXT NOT NULL (JSON array of word objects with karaoke timings)         |
|   - style_name: VARCHAR(64) NOT NULL DEFAULT 'Default'                                  |
|   - is_modified: BOOLEAN NOT NULL DEFAULT 0                                             |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
```

### 2.1 Table: `subtitle_tracks`
Represents a generated or customized subtitle track associated with a specific clip.

| Column | Type | Nullable | Constraints / Defaults | Description |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK, UUIDv4 | Subtitle track identifier |
| `clip_id` | `VARCHAR(36)` | No | FK -> `clips.id` ON DELETE CASCADE | Associated clip |
| `transcript_id` | `VARCHAR(36)` | Yes | FK -> `transcripts.id` ON DELETE SET NULL | Source transcript |
| `preset_name` | `VARCHAR(64)` | No | Default: `'KARAOKE_AMBER'` | Active style preset |
| `is_enabled` | `BOOLEAN` | No | Default: `1` | Whether subtitles appear in renders |
| `is_active` | `BOOLEAN` | No | Default: `1` | Currently selected track |
| `language` | `VARCHAR(16)` | No | Default: `'en'` | BCP-47 language tag |
| `ass_file_path` | `VARCHAR(512)` | Yes | Nullable | Path to compiled `.ass` on disk |
| `compile_status` | `VARCHAR(32)` | No | Default: `'DRAFT'` | `DRAFT`, `COMPILED`, `ERROR` |
| `custom_style_overrides` | `TEXT` | Yes | Nullable | JSON object containing styling overrides |
| `created_at` | `DATETIME` | No | `CURRENT_TIMESTAMP` | Creation timestamp |
| `updated_at` | `DATETIME` | No | `CURRENT_TIMESTAMP` | Last updated timestamp |

### 2.2 Table: `subtitle_events`
Stores parsed, line-level dialogue bursts with word timings for interactive client editing.

| Column | Type | Nullable | Constraints / Defaults | Description |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK, UUIDv4 | Event line identifier |
| `track_id` | `VARCHAR(36)` | No | FK -> `subtitle_tracks.id` ON DELETE CASCADE | Parent subtitle track |
| `sequence_index` | `INTEGER` | No | Check: `>= 0` | 0-based ordering within track |
| `start_ms` | `INTEGER` | No | Check: `>= 0` | Line start time relative to clip (ms) |
| `end_ms` | `INTEGER` | No | Check: `> start_ms` | Line end time relative to clip (ms) |
| `text` | `TEXT` | No | Plain string | Full unformatted text of caption line |
| `words_json` | `TEXT` | No | JSON Array string | Word array: `[{"word":"The","start_ms":0,"end_ms":300,"duration_cs":30}]` |
| `style_name` | `VARCHAR(64)` | No | Default: `'Default'` | Style identifier |
| `is_modified` | `BOOLEAN` | No | Default: `0` | Set to 1 if manually edited by user |

---

## 3. API Endpoints Specification

### 3.1 `POST /api/v1/clips/{clip_id}/subtitles/generate`
Synchronizes transcript words with clip boundaries, generates caption chunks, compiles `.ass` file, and creates database records.

- **Request Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "preset_name": "KARAOKE_AMBER",
    "vertical_position": "BOTTOM",
    "max_words_per_line": 4,
    "force_realign": false
  }
  ```
- **Response Status:** `201 Created`
- **Response Schema:**
  ```json
  {
    "id": "7f8b9c2a-1122-3344-5566-778899aabbcc",
    "clip_id": "d4377c85-a326-4659-8d0a-e245b7529c6b",
    "preset_name": "KARAOKE_AMBER",
    "is_enabled": true,
    "event_count": 8,
    "total_words": 32,
    "compile_status": "COMPILED",
    "ass_download_url": "/api/v1/clips/d4377c85-a326-4659-8d0a-e245b7529c6b/subtitles.ass",
    "created_at": "2026-11-24T03:30:00Z"
  }
  ```

---

### 3.2 `GET /api/v1/clips/{clip_id}/subtitles`
Retrieves the active subtitle track and all child caption events for the Studio UI timeline.

- **Response Status:** `200 OK`
- **Response Schema:**
  ```json
  {
    "id": "7f8b9c2a-1122-3344-5566-778899aabbcc",
    "clip_id": "d4377c85-a326-4659-8d0a-e245b7529c6b",
    "preset_name": "KARAOKE_AMBER",
    "is_enabled": true,
    "compile_status": "COMPILED",
    "custom_style_overrides": {
      "font_size": 88,
      "primary_color": "#FFFFFF",
      "highlight_color": "#F59E0B"
    },
    "events": [
      {
        "id": "e1-8899-aabb",
        "sequence_index": 0,
        "start_ms": 0,
        "end_ms": 2150,
        "text": "The secret to productivity",
        "words": [
          { "word": "The", "start_ms": 0, "end_ms": 300, "duration_cs": 30 },
          { "word": "secret", "start_ms": 320, "end_ms": 770, "duration_cs": 45 },
          { "word": "to", "start_ms": 800, "end_ms": 1050, "duration_cs": 25 },
          { "word": "productivity", "start_ms": 1080, "end_ms": 2150, "duration_cs": 107 }
        ],
        "is_modified": false
      }
    ]
  }
  ```

---

### 3.3 `PUT /api/v1/clips/{clip_id}/subtitles`
Updates high-level subtitle settings (preset, active toggle, vertical position, or global styling overrides) and triggers background ASS re-compilation.

- **Request Body:**
  ```json
  {
    "preset_name": "MODERN",
    "is_enabled": true,
    "vertical_position": "BOTTOM",
    "custom_style_overrides": {
      "font_family": "Montserrat",
      "font_size": 92,
      "highlight_color": "#06B6D4"
    }
  }
  ```
- **Response Status:** `200 OK`

---

### 3.4 `PUT /api/v1/clips/{clip_id}/subtitles/events/{event_id}`
Allows in-place editing of transcript text or timing boundaries for a specific caption burst in the Studio UI without re-running transcription.

- **Request Body:**
  ```json
  {
    "text": "The secret to 10x productivity",
    "start_ms": 0,
    "end_ms": 2200
  }
  ```
- **Response Status:** `200 OK`
- **Behavior:** Recalculates word durations evenly across modified words, marks `is_modified = 1`, and re-compiles the `.ass` file.

---

### 3.5 `GET /api/v1/clips/{clip_id}/subtitles.ass`
Downloads or streams the compiled `.ass` subtitle file directly.

- **Response Status:** `200 OK`
- **Content-Type:** `text/x-ssa; charset=utf-8`
- **Headers:** `Content-Disposition: attachment; filename="{clip_id}.ass"`
- **Response Body:** Raw UTF-8 encoded ASS v4.00+ script string.

---

### 3.6 `GET /api/v1/subtitles/presets`
Lists all available system and custom subtitle styling presets with their full design parameters.

- **Response Status:** `200 OK`
- **Response Schema:**
  ```json
  {
    "presets": [
      {
        "name": "KARAOKE_AMBER",
        "display_name": "Karaoke Amber",
        "font_family": "Montserrat",
        "font_size": 88,
        "primary_color": "#FFFFFF",
        "highlight_color": "#F59E0B",
        "outline_color": "#000000",
        "outline_width": 8.0,
        "shadow_depth": 3.0,
        "vertical_position": "BOTTOM",
        "max_words_per_line": 4,
        "box_style": "OUTLINE"
      },
      {
        "name": "MODERN",
        "display_name": "Modern Neon",
        "font_family": "Montserrat",
        "font_size": 84,
        "primary_color": "#FFFFFF",
        "highlight_color": "#06B6D4",
        "outline_color": "#000000",
        "outline_width": 8.0,
        "shadow_depth": 3.0,
        "vertical_position": "BOTTOM",
        "max_words_per_line": 4,
        "box_style": "OUTLINE"
      }
    ]
  }
  ```

---

### 3.7 `DELETE /api/v1/clips/{clip_id}/subtitles`
Deletes the custom subtitle track and events for a clip, and removes the `.ass` file from `storage/subtitles/`.

- **Response Status:** `204 No Content`

---

## 4. Error Handling Contracts

All endpoints return the standard Clipsly error envelope:

```json
{
  "error_code": "SUBTITLE_NOT_FOUND",
  "detail": "No subtitle track found for clip 'd4377c85-a326-4659-8d0a-e245b7529c6b'.",
  "error": {
    "clip_id": "d4377c85-a326-4659-8d0a-e245b7529c6b",
    "timestamp": "2026-11-24T03:30:00Z"
  }
}
```

### Standard Error Codes:
- `SUBTITLE_NOT_FOUND` (`404`): No subtitle track exists for the requested clip.
- `TRANSCRIPT_UNAVAILABLE` (`400`): Source video has not been transcribed yet.
- `INVALID_TIMING_BOUNDS` (`422`): Event `start_ms` >= `end_ms` or outside clip bounds.
- `ASS_COMPILATION_FAILED` (`500`): Generator encountered syntax or filesystem error writing `.ass`.
