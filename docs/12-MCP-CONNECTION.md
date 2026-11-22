# Model Context Protocol (MCP) Integration

**Project Name:** AI Video Clipper (Working Title: Clipsly)  
**Document Version:** 0.1.0  
**Status:** PLANNED (Scheduled for Specification & Implementation in Phase 17+)  
**Author:** AI Integration & Systems Architect  

---

## 1. Purpose of this Document

This document defines the Model Context Protocol (MCP) integration layer for AI Video Clipper.

The Model Context Protocol (developed by Anthropic and adopted across the AI ecosystem) provides an open standard for exposing local application tools, data resources, and system state to external AI agents (such as Antigravity, Claude Desktop, and local LLMs).

By implementing an MCP server interface, AI Video Clipper can be queried, controlled, and automated directly by conversational agents—enabling workflows such as *"Find the funniest 30-second clip from yesterday's podcast and render it in vertical format with yellow subtitles."*

---

## 2. Architecture of the MCP Layer

```
┌─────────────────────────────────────────────────────────────┐
│                 External AI Agent Host                      │
│     (Antigravity Assistant / Claude Desktop / CLI)          │
└──────────────────────────────┬──────────────────────────────┘
                               │ JSON-RPC 2.0 (stdio or SSE)
┌──────────────────────────────▼──────────────────────────────┐
│                  Clipsly MCP Server Layer                   │
│                                                             │
│  ┌─────────────────────────┐   ┌─────────────────────────┐  │
│  │     Tool Handlers       │   │   Resource Providers    │  │
│  │ (detect, clip, export)  │   │  (transcripts, stats)   │  │
│  └────────────┬────────────┘   └────────────┬────────────┘  │
└───────────────┼─────────────────────────────┼───────────────┘
                │                             │
┌───────────────▼─────────────────────────────▼───────────────┐
│               Clipsly Core Application Engine               │
│               (FastAPI / SQLite / Media Services)           │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Proposed MCP Toolset Catalog

The MCP server plans to expose six core tool capabilities:

1. **`clipsly_list_videos`:**
   - *Description:* Lists all ingested videos with duration, file size, and processing status.
   - *Parameters:* `limit: int`, `status: Optional[str]`.
2. **`clipsly_get_transcript`:**
   - *Description:* Retrieves the full or segmented transcript for a given video, including word-level timestamps.
   - *Parameters:* `video_id: str`, `format: str ("json" | "markdown" | "text")`.
3. **`clipsly_detect_highlights`:**
   - *Description:* Triggers the highlight detection engine on a video transcript and returns ranked candidate segments.
   - *Parameters:* `video_id: str`, `min_duration: int`, `max_duration: int`, `target_count: int`.
4. **`clipsly_create_clip`:**
   - *Description:* Creates a tailored clip configuration with custom start/end timestamps and subtitle styling.
   - *Parameters:* `video_id: str`, `start_ms: int`, `end_ms: int`, `aspect_ratio: str`, `style_preset: str`.
5. **`clipsly_render_clip`:**
   - *Description:* Initiates NVENC hardware-accelerated video rendering for a specified clip.
   - *Parameters:* `clip_id: str`, `burn_subtitles: bool`.
6. **`clipsly_get_hardware_status`:**
   - *Description:* Returns current GPU VRAM utilization, CPU load, and active background rendering jobs.
   - *Parameters:* None.

---

## 4. Proposed Resource URI Schemes

- `clipsly://videos/{video_id}/transcript` — Full transcript text and metadata.
- `clipsly://videos/{video_id}/highlights` — Summary table of candidate highlights.
- `clipsly://system/hardware` — Real-time telemetry payload.

---

## 5. Planned Sections for Phase 17+ Specification

During Phase 17+, this document will be expanded to include:
- Complete JSON Schema definitions for all MCP tool arguments and return payloads.
- Transport configuration (`stdio` mode for CLI agents vs. `sse` for remote/desktop agents).
- MCP client configuration examples for `claude_desktop_config.json` and Antigravity workspace settings.

---

## 6. Current Status & Next Steps

- **Status:** PLANNED.
- **Immediate Dependency:** Completion of core video pipeline (Phases 04 through 16).
- **Execution Target:** Phase 17+.
