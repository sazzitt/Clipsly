# UI/UX Design Specifications

**Project Name:** AI Video Clipper (Working Title: Clipsly)  
**Document Version:** 0.1.0  
**Status:** PLANNED (Scheduled for Detailed Specification in Phase 02 / Implementation in Phase 05)  
**Author:** Software Architect & UI/UX Design Engineer  

---

## 1. Purpose of this Document

This document defines the user interface (UI) and user experience (UX) architectural standards for the AI Video Clipper application. It establishes the visual design language, design tokens, layout grids, interaction paradigms, component library specifications (Tailwind CSS + shadcn/ui), and screen hierarchy.

The primary objective is to deliver a fast, responsive, high-contrast dark workstation interface tailored for creators who need to quickly review transcripts, scrub waveforms, fine-tune clip timestamps, customize animated subtitles, and monitor export jobs.

---

## 2. Core UI/UX Design Principles

1. **Dark-Mode-First Workstation Aesthetic:** Video editing demands high contrast and minimal eye strain. The UI utilizes a deep slate/zinc neutral backdrop (`#09090b` / `#18181b`) with vibrant accent highlights.
2. **Direct Manipulation & Zero Friction:** Sliders, handles, and transcript words are directly interactive. Clicking a word in the transcript seeks the video immediately; dragging timeline handles updates preview framing in real time.
3. **Information Density with Visual Hierarchy:** Provide essential technical metrics (timestamps, duration, word confidence, resolution) without overwhelming the creator.
4. **Predictable Feedback & State Visibility:** Every stage of the 16-step processing pipeline is communicated through subtle spinners, progress percentages, and animated status badges.
5. **Single-User Simplicity:** No registration dialogs, no onboarding tours, and no account settings modals. The user opens the web application and immediately enters the workspace.

---

## 3. Design System Foundation

### 3.1 Component Library & Primitives
- **Base Framework:** React 18 with TypeScript.
- **Styling Utility:** Tailwind CSS v3.4+ with custom CSS variables.
- **Component Primitives:** `shadcn/ui` (built on Radix UI unstyled primitives).
- **Icons:** `lucide-react` (clean, 24px stroke-width icons).
- **Animation Primitives:** Framer Motion / Tailwind transitions for smooth panel expansions and karaoke word glows.

### 3.2 Proposed Color Palette (Dark Theme Tokens)
- **Background Root:** `zinc-950` (`#09090b`)
- **Card / Surface Background:** `zinc-900` (`#18181b`)
- **Card Border / Dividers:** `zinc-800` (`#27272a`)
- **Primary Text:** `zinc-50` (`#fafafa`)
- **Muted Text / Metadata:** `zinc-400` (`#a1a1aa`)
- **Primary Brand Accent:** Indigo/Violet `violet-500` (`#8b5cf6`)
- **Highlight / Active Karaoke Accents:** Electric Amber (`#f59e0b`), Neon Cyan (`#06b6d4`), and Mint Green (`#10b981`)
- **Destructive / Error:** Crimson `rose-500` (`#f43f5e`)

### 3.3 Typography
- **UI & Controls:** Inter or Geist Sans (`sans-serif`, clean modern geometric sans).
- **Timecode & Metrics:** JetBrains Mono or Geist Mono (`monospace`, tabular numerals to prevent layout jitter during video scrubbing).
- **Video Subtitle Presets:** Bundled web/system fonts: Montserrat (Bold/Black), Inter (ExtraBold), Impact, and Bangers.

---

## 4. Screen & View Hierarchy

The application interface is structured into four primary views:

1. **Workspace Dashboard (`/`):**
   - Central drag-and-drop zone for local video files.
   - List/Grid of previously processed videos with thumbnail, title, duration, and processed clip counts.
   - System resource status badge (GPU VRAM usage, available SSD storage).
2. **Transcription & Candidate Review (`/video/:id`):**
   - Source 16:9 video player with scrubbing controls.
   - Synchronized scrollable transcript pane with search, speaker pause markers, and inline word editing.
   - Proposed highlight cards ranked by score (Hook, Topic, Duration, Play button).
3. **Interactive Clip Studio (`/studio/:clipId`):**
   - Dual-mode preview: 9:16 vertical mobile framing toggle.
   - Visual timeline ruler with dual draggable trim handles (start/end millisecond precision).
   - Subtitle styling inspector: Preset selector, font picker, size slider, color pickers, and vertical position buttons.
   - Live karaoke preview overlay reflecting chosen font, color, and animation.
4. **Export Manager & Queue (`/exports`):**
   - List of active and completed render jobs.
   - Live rendering progress bar (percentage, estimated time remaining, NVENC encoding speed).
   - One-click "Download MP4" and "Reveal in Explorer" actions.

---

## 5. Planned Sections for Phase 05 Specification

The following sections will be fully specified during Phase 02 and implemented in Phase 05:

- Detailed Figma/Wireframe Layouts for Desktop Views ($1920\times 1080$ and $1440\times 900$).
- Interactive Trim Handle Drag & Snap Physics.
- Karaoke Subtitle Canvas & DOM Layer Synchronization.
- Accessibility (a11y) Keyboard Shortcuts (Space to play/pause, J/K/L scrubbing, [ / ] to set in/out trim points).
- Toast Notification and Error Banner Specifications.

---

## 6. Current Status & Next Steps

- **Status:** PLANNED.
- **Immediate Dependency:** Completion of System Architecture (Phase 02).
- **Execution Target:** UI component scaffolding begins in Phase 05.
