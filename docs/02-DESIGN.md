# UI/UX Design Specifications & Design System

**Project Name:** AI Video Clipper (Working Title: Clipsly)  
**Document Version:** 1.0.0  
**Status:** APPROVED & FINALIZED (Phase 05 Baseline)  
**Author:** Lead UI/UX Architect & Design Systems Engineer  
**Design Paradigm:** Premium Desktop Dark-Mode Video Editing Workstation  
**Component Ecosystem:** React 18 + Tailwind CSS v3.4+ + shadcn/ui + Lucide Icons  

---

## 1. Executive Summary & Design Philosophy

Clipsly is built from the ground up as a **sovereign, local-first multimedia workstation** for content creators. Rather than imitating generic, low-density SaaS dashboards, the user interface follows the design principles of high-end Non-Linear Editors (such as DaVinci Resolve, Final Cut Pro, and Adobe Premiere Pro) streamlined for rapid, single-click short-form video generation.

### Core Design Principles:
1. **Workstation Dark Aesthetic:** Deep neutral zinc/slate backgrounds (`#09090b` / `#18181b`) maximize contrast for video footage, minimize eye fatigue during extended editing sessions, and eliminate distracting bright white borders.
2. **Dense, Tabular Information Architecture:** Essential technical metrics (durations, start/end timestamps, frame rates, audio sample rates, confidence probabilities) are prominently displayed using tabular monospace figures (`font-mono`) to prevent layout shifts.
3. **Direct Manipulation & Zero Latency:** Sliders, handles, and transcript words are directly interactive. Clicking any word in the transcript seeks the video instantly; dragging timeline trim handles updates the 9:16 mobile crop preview with zero rendering lag.
4. **Predictable Feedback & State Transparency:** Long-running pipeline stages (audio extraction, Faster-Whisper transcription, highlight scoring, and NVENC rendering) provide real-time percentage progress, stage badges, and time remaining via Server-Sent Events (SSE).
5. **Single-User Focus:** No auth dialogs, no onboarding barriers, no billing banners, and no modal upsells. The creator opens the application and immediately interacts with their local workspace.

---

## 2. Design System Tokens & Foundations

### 2.1 Color Tokens (Dark Theme Palette)

The application utilizes strict semantic CSS variables matching Tailwind CSS convention:

```css
:root {
  /* Surfaces & Backgrounds */
  --background: 240 10% 3.9%;          /* #09090b - Deep Canvas Root */
  --card: 240 10% 5.9%;                /* #0f0f12 - Panel & Card Surface */
  --card-hover: 240 10% 8.5%;          /* #16161a - Interactive Hover Surface */
  --popover: 240 10% 4.9%;             /* #0c0c0e - Menus & Dropdowns */
  --border: 240 3.7% 15.9%;            /* #27272a - Panel Dividers */
  --input: 240 3.7% 15.9%;             /* #27272a - Form Input Borders */

  /* Typography */
  --foreground: 0 0% 98%;              /* #fafafa - Primary High-Contrast Text */
  --muted-foreground: 240 5% 64.9%;    /* #a1a1aa - Subtitles & Secondary Metrics */

  /* Accents & States */
  --primary: 263.4 70% 50.4%;          /* #7c3aed - Electric Violet (Action Accent) */
  --primary-foreground: 0 0% 100%;
  --secondary: 240 3.7% 15.9%;        /* #27272a - Subdued Action */
  --destructive: 0 84.2% 60.2%;        /* #ef4444 - Danger / Stop */

  /* Subtitle Highlight & Karaoke Tokens */
  --karaoke-amber: 45 93% 47%;         /* #f59e0b - Warm Viral Hook Gold */
  --karaoke-cyan: 189 94% 43%;         /* #06b6d4 - Cyber Neon Cyan */
  --karaoke-mint: 160 84% 39%;         /* #10b981 - Fresh Mint Green */
  --karaoke-rose: 350 89% 60%;         /* #f43f5e - High-Energy Rose */

  /* System Telemetry Badges */
  --telemetry-gpu: 142 71% 45%;        /* #22c55e - Green VRAM Safe */
  --telemetry-warn: 38 92% 50%;        /* #f59e0b - VRAM Contested */
  --telemetry-err: 0 84% 60%;          /* #ef4444 - OOM Warning */
}
```

### 2.2 Typography Scale

- **Primary UI Font:** `Inter`, system `-apple-system`, `BlinkMacSystemFont`, `sans-serif`.
- **Timecode & Data Font:** `JetBrains Mono`, `Geist Mono`, `monospace` (strict `font-feature-settings: "tnum"` tabular numbers).
- **Subtitle Preview Fonts:** Montserrat (Bold 700 / Black 900), Inter (ExtraBold 800), Impact, Bangers.

| Role | Font Family | Size | Weight | Tracking / Line Height |
|---|---|---|---|---|
| **Display Header** | Inter | 24px (`1.5rem`) | SemiBold (600) | `-0.025em`, `2rem` |
| **Section Title** | Inter | 18px (`1.125rem`)| Medium (500) | `-0.015em`, `1.5rem` |
| **Component Label**| Inter | 13px (`0.8125rem`)| Medium (500) | `normal`, `1.25rem` |
| **Body Text** | Inter | 14px (`0.875rem`)| Regular (400) | `normal`, `1.25rem` |
| **Metadata / Caption**| Inter | 12px (`0.75rem`) | Regular (400) | `0.01em`, `1rem` |
| **Timeline Timecode**| JetBrains Mono| 13px (`0.8125rem`)| Bold (700) | `tabular-nums`, `1rem` |

### 2.3 Component Primitives (shadcn/ui Standards)

1. **Buttons (`<Button />`):**
   - `variant="default"`: Violet `#7c3aed` solid background, white text. Used exclusively for primary operations (e.g., *"Upload Video"*, *"Export Clip"*).
   - `variant="secondary"`: Dark zinc surface `#27272a`, hover `#3f3f46`. Used for secondary actions (e.g., *"Add Padding"*, *"Reset Trims"*).
   - `variant="outline"`: Transparent background with `#27272a` border.
   - `variant="ghost"`: Zero border, hover highlight. Used for timeline controls and play/pause toggles.
   - `variant="destructive"`: Dark crimson `#991b1b` hover `#ef4444`. Used for deleting videos or canceling render jobs.
2. **Range Trim Sliders (`<TrimSlider />`):**
   - Dual-handle range track for `start_ms` and `end_ms`.
   - Visual waveform background thumbnail cached in memory.
   - Active range highlighted in translucent violet (`rgba(124, 58, 237, 0.3)`).
   - Millisecond readout tooltip hovering directly over active drag handles.
3. **Card Containers (`<Card />`):**
   - Background `#0f0f12`, border `1px solid #27272a`, border-radius `8px` (`rounded-lg`).
   - Zero drop-shadow to maintain a flat, modern technical workstation feel.
4. **Progress Bars (`<Progress />`):**
   - Determinate linear bar (`h-2 rounded-full`) with smooth CSS transition (`transition-all duration-300`).
   - Color shifts to amber when processing CPU fallback, violet during NVENC rendering.
5. **Toasts (`<Sonner />` / `<Toast />`):**
   - Fixed bottom-right notifications with automatic 4-second dismissal.
   - Explicit action buttons for file system interactions (e.g., *"Show in Explorer"*).

---

## 3. Comprehensive UI Screen Specifications (14 Screens & States)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Screen Hierarchy Overview                       │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Dashboard & Workspace Shell                                         │
│ 2. Video Library View                                                  │
│ 3. Video Upload Dropzone                                               │
│ 4. Video Source Preview Player                                         │
│ 5. Processing Status & Real-Time Pipeline Modal                        │
│ 6. Transcript Viewer & Sentence Navigator                              │
│ 7. AI Highlight Candidate Results                                      │
│ 8. Clip Selection & Promotion Shelf                                    │
│ 9. Interactive Clip Studio & Timeline Trimmer                          │
│ 10. Subtitle Styling & Karaoke Inspector                               │
│ 11. Export Manager & Queue View                                        │
│ 12. Application Settings Panel                                         │
│ 13. Storage Management & Disk Telemetry                                │
│ 14. Error Handling & Recovery Modals                                   │
└────────────────────────────────────────────────────────────────────────┘
```

---

### Screen 1: Dashboard & Workspace Shell (`/`)
- **Purpose:** Central entry point showing hardware health, quick actions, and recent clipping projects.
- **Layout Structure:**
  - **Top Navigation Bar:** Persistent header with Clipsly logo, active project breadcrumb, hardware telemetry badge (VRAM/CPU/SSD), and Settings shortcut icon.
  - **Main Work Area:** Two-column split layout (Left 65%: Video Library / Upload Dropzone; Right 35%: Recent Exports and System Status).
- **Main Components:** `<TopNav />`, `<HardwareBadge />`, `<UploadDropzone />`, `<RecentVideosList />`, `<RecentExportsShelf />`.
- **User Actions:** Drag video onto canvas, click "Browse Files", click existing video to open review studio, click exported clip to download.
- **Empty State:** High-contrast dashed border upload zone with prompt: *"Drag a horizontal video here or select from disk (MP4, MKV, MOV, WebM up to 10GB)"*.
- **Responsive Behaviour:** Desktop first ($1920\times 1080$ and $1440\times 900$). On viewports $< 1200\text{px}$, columns stack vertically with upload dropzone on top.

```
+---------------------------------------------------------------------------------------+
| [Clipsly]  Projects / Recent              [GPU: 940MB/4GB] [SSD: 128GB Free]  [Settings] |
+---------------------------------------------------------------------------------------+
|  +-----------------------------------------------+  +-------------------------------+ |
|  |             UPLOAD & DROP ZONE                |  |       RECENT EXPORTS          | |
|  |     [ Icon: Film ]                            |  | - Clip_01.mp4 (30s) [Play]    | |
|  |   Drag & Drop local video file here           |  | - Clip_02.mp4 (45s) [Play]    | |
|  |   or [ Browse Local SSD ]                     |  | - Clip_03.mp4 (60s) [Play]    | |
|  +-----------------------------------------------+  +-------------------------------+ |
|  +-----------------------------------------------+  +-------------------------------+ |
|  |             VIDEO LIBRARY (3)                 |  |       SYSTEM TELEMETRY        | |
|  |  [Thmb] Tech_Talk_Ep12.mp4  (42m)  [Status]   |  | RTX 3050: Healthy (12%)       | |
|  |  [Thmb] AI_Tutorial.mkv     (18m)  [Status]   |  | Ryzen 7:  8 Cores Active      | |
|  +-----------------------------------------------+  +-------------------------------+ |
+---------------------------------------------------------------------------------------+
```

---

### Screen 2: Video Library View (`/videos`)
- **Purpose:** Browse, search, filter, and delete previously ingested source videos.
- **Layout Structure:** Responsive grid of media cards (3 cards per row on $1920\text{px}$).
- **Main Components:** `<SearchBar />`, `<FilterDropdown />` (All, Ready, Processing, Error), `<VideoCard />` (thumbnail preview, duration badge, resolution, clip count badge, action menu).
- **User Actions:** Click card to open review workspace, delete video (triggers confirm dialog), search by original filename.
- **Empty State:** Centered folder illustration with text *"No videos ingested yet. Upload your first video to start clipping."*
- **Loading State:** 6-item skeleton grid matching card aspect ratio with shimmering `#1f1f23` placeholders.
- **Error State:** Alert banner at top: *"Failed to load video library from SQLite database."* with *"Retry"* button.

---

### Screen 3: Video Upload Screen (`/upload`)
- **Purpose:** Dedicated drag-and-drop ingestion interface with instant pre-flight validation.
- **Layout Structure:** Full-screen modal or dedicated route with large central drop target.
- **Main Components:** `<DropZone />`, `<FileValidator />`, `<UploadProgressBar />`, `<DiskSpaceWarningBanner />`.
- **User Actions:** Select file, inspect pre-flight metrics (size, format), click *"Start Ingestion"*, cancel upload.
- **Empty State:** Large pulsing dashed border with supported formats badges (`.mp4`, `.mkv`, `.mov`, `.webm`).
- **Loading State:** Determinate progress bar showing uploaded bytes, transfer speed (e.g., `120 MB/s`), and estimated time remaining.
- **Success State:** Checkmark icon with extracted duration and button: *"Proceed to Transcription & Highlights"*.
- **Error State:** Red border with specific reason: *"Audio stream missing in container"* or *"Insufficient SSD space (<10 GB available)"*.

---

### Screen 4: Video Source Preview Player (`/video/:id`)
- **Purpose:** Review raw horizontal source footage and navigate transcript in lockstep.
- **Layout Structure:** Split view (Left 60%: HTML5 16:9 Video Player with seekbar; Right 40%: Scrollable Transcript Pane).
- **Main Components:** `<VideoPlayer />` (Play/Pause, Timecode Display, Volume, J/K/L keyboard scrubbers), `<AudioWaveform />`, `<TranscriptPane />`.
- **User Actions:** Scrub video, seek to specific timestamp, play at $1.0\times, 1.25\times, 1.5\times$, jump by frame.
- **Loading State:** Shimmering black rectangle with centered spinner while HTTP 206 stream initializes.
- **Error State:** Alert box: *"Video file missing on local disk. Has it been moved or renamed?"*

---

### Screen 5: Processing Status & Real-Time Pipeline Modal (`/jobs/:id`)
- **Purpose:** Displays live execution state during background audio extraction, Faster-Whisper transcription, and highlight detection.
- **Layout Structure:** Multi-stage vertical stepper or segmented progress bar.
- **Main Components:** `<StepIndicator />` (4 steps: Audio Extraction $\to$ Speech Transcription $\to$ Discourse Analysis $\to$ Highlight Scoring), `<SSELiveFeed />`, `<CancelJobButton />`.
- **User Actions:** Watch live progress, view stdout log snippet, click *"Cancel Job"*.
- **States:**
  - *Active:* Current step highlighted with glowing violet spinner and percentage counter.
  - *Fallback:* Amber warning badge: *"VRAM tight; transcribing smoothly on AMD Ryzen 7 CPU"*.
  - *Failure:* Detailed error box with *"Retry on CPU"* action button.

```
+---------------------------------------------------------------------------------------+
|  PIPELINE PROCESSING: Tech_Talk_Ep12.mp4                                              |
+---------------------------------------------------------------------------------------+
|  [✓] 1. Extracting 16kHz Audio .................................... Done (12s)        |
|  [●] 2. Transcribing Speech with Faster-Whisper (CUDA) ............ 64%               |
|      >> Words processed: 2,750 / 4,250 | RTF: 0.12x | Model: small (float16)          |
|      [========================================>                  ]                    |
|  [ ] 3. Segmenting Discourse & Detecting Pauses ................... Waiting           |
|  [ ] 4. Algorithmic Highlight Scoring & Snapping .................. Waiting           |
|                                                                                       |
|  [ Cancel Job ]                                           GPU VRAM: 1.1 GB / 4.0 GB   |
+---------------------------------------------------------------------------------------+
```

---

### Screen 6: Transcript Viewer (`/video/:id/transcript`)
- **Purpose:** Interactive, searchable transcript synchronized with video playback.
- **Layout Structure:** Scrollable vertical list of timestamped sentence blocks.
- **Main Components:** `<SearchInput />`, `<SentenceBlock />` (timestamp badge, speaker label, sentence text, word chips with confidence tooltips).
- **User Actions:** Click any word to jump video to that millisecond; double-click a word or sentence to edit misheard text in-place (`PATCH /api/v1/transcripts/{id}/segments/{seg_id}`); filter by keyword search.
- **Active State:** The currently spoken sentence has a subtle violet border; the active spoken word illuminates in electric amber.

---

### Screen 7: AI Highlight Results Shelf (`/video/:id/highlights`)
- **Purpose:** Presents candidate short-form highlights proposed by the highlight detection engine.
- **Layout Structure:** Horizontal carousel or 2-column card shelf below the video player.
- **Main Components:** `<HighlightCard />` (Rank badge, Composite Score `0–100`, Duration `34s`, Opening Hook text snippet, Category tag: *"Insight"* / *"Story"*, *"Preview Clip"* button, *"Create Clip"* button).
- **User Actions:** Hover over card to preview start/end snippet in player; click *"Open in Studio"* to promote candidate to active clip.
- **Empty State:** Text: *"No highlights detected within configured duration bounds. Try lowering minimum duration in Settings."*

---

### Screen 8: Clip Selection & Shelf (`/clips`)
- **Purpose:** Manage all created short-form clips across videos.
- **Layout Structure:** 9:16 vertical card grid displaying rendered or draft vertical clips.
- **Main Components:** `<ClipCard />` (9:16 aspect ratio thumbnail with blurred background preview, Title, Duration badge, Subtitle preset badge, Status: DRAFT / EXPORTED, Action buttons: Edit, Export, Delete).
- **User Actions:** Click clip to open in Studio, click quick export, delete clip.

---

### Screen 9: Interactive Clip Studio & Timeline Trimmer (`/studio/:clipId`)
- **Purpose:** Precision editing environment for fine-tuning start/end boundaries, framing, and live subtitle preview.
- **Layout Structure:** 3-Panel Professional Layout:
  - **Left Panel (50%):** Vertical 9:16 Video Canvas preview with live subtitle rendering and CSS aspect-ratio masking.
  - **Right Panel (50%):** Subtitle styling inspector, typography controls, and transcript segment text editor.
  - **Bottom Panel (Full Width):** Multi-track timeline ruler with dual draggable trim handles (`start_ms` and `end_ms`), visual waveform, and sentence boundary snap points.
- **Main Components:** `<StudioCanvas916 />`, `<DualHandleTrimSlider />`, `<SubtitleInspector />`, `<SnapToSentenceToggle />`, `<ExportButton />`.
- **User Actions:** Drag start/end handles to trim clip (updates preview in real time); toggle snap to nearest speech pause ($\pm 0.5\text{s}$); edit subtitle text; change font/colors; click *"Export 1080x1920 MP4"*.

```
+---------------------------------------------------------------------------------------+
|  [< Back to Video]   CLIP STUDIO: "The Biggest Mistake Creators Make"     [ Export MP4 ]|
+---------------------------------------------------------------------------------------+
|  +------------------------+  +------------------------------------------------------+ |
|  |   9:16 VERTICAL CANVAS |  |  SUBTITLE & FRAMING INSPECTOR                        | |
|  |   +----------------+   |  |                                                      | |
|  |   | [Blurred BG]   |   |  |  Aspect Ratio Mode:   (●) Blur-Pad    ( ) Center-Crop| |
|  |   |                |   |  |  Preset Template:     [ Karaoke Amber v ]            | |
|  |   | [Sharp 16:9 FG]|   |  |  Font Family:         [ Montserrat Bold v ]          | |
|  |   |                |   |  |  Font Size:           [ 24pt ]  (Slider 18 - 36pt)   | |
|  |   | "The single"   |   |  |  Highlight Color:     [ #FFD700 ] (Gold ColorPicker) | |
|  |   | "biggest"      |   |  |  Vertical Position:   [ Top ]  (●) Bottom  [ Middle] | |
|  |   | [MISTAKE]      |   |  +------------------------------------------------------+ |
|  |   |                |   |  |  EDIT SPOKEN TEXT FOR THIS CLIP:                     | |
|  |   | [Blurred BG]   |   |  |  "The single biggest mistake creators make is..."    | |
|  |   +----------------+   |  |  [ Save Text Edit ]                                  | |
|  +------------------------+  +------------------------------------------------------+ |
+---------------------------------------------------------------------------------------+
|  TIMELINE: [00:45.000 - 01:18.500] (Duration: 33.5s)                     [Snap: ON]   |
|  [Waveform] ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| |
|  Ruler: ----|--[==== ACTIVE CLIP RANGE ====================]--|---------------------- |
|             ^ start: 45.000s                               ^ end: 78.500s             |
+---------------------------------------------------------------------------------------+
```

---

### Screen 10: Subtitle Styling & Karaoke Inspector
- **Purpose:** Dedicated styling tool for custom subtitle fonts, animated karaoke color transitions, outlines, and positions.
- **Main Components:** `<PresetPicker />` (Karaoke Amber, Neon Cyan, Mint Glow, Clean Minimal), `<FontFamilySelect />`, `<FontSizeSlider />`, `<ColorPicker />` (Primary text color, Active spoken word color), `<StrokeWidthSlider />`, `<VerticalPositionToggle />`.
- **User Actions:** Click preset to apply instantly; fine-tune stroke thickness; test preview playback.

---

### Screen 11: Export Manager & Queue View (`/exports`)
- **Purpose:** Displays queue of active and completed video renders.
- **Layout Structure:** Tabular list of render jobs with status, output resolution, file size, and download buttons.
- **Main Components:** `<ExportJobRow />`, `<NVENCStatusBadge />`, `<DownloadButton />`, `<RevealInExplorerButton />`.
- **User Actions:** Download finished MP4; click *"Show in Folder"* to highlight file in Windows File Explorer via `POST /api/v1/exports/{id}/reveal`; cancel active render.

---

### Screen 12: Application Settings Panel (`/settings`)
- **Purpose:** Configure local hardware parameters, default model sizes, duration bounds, and optional external AI keys.
- **Layout Structure:** Tabbed settings card (Tabs: General, Transcription, Highlights, Storage).
- **Main Components:**
  - *Transcription Tab:* Whisper model size dropdown (`base`, `small` [recommended], `medium`), compute type (`float16`, `int8_float16`).
  - *Highlights Tab:* Default clip min/max duration sliders (15s–90s); Optional external API key input field (Google Gemini / OpenAI) with show/hide password toggle.
  - *Export Tab:* Default encoder selection (`h264_nvenc` with automatic CPU `libx264` fallback).
- **User Actions:** Adjust sliders, save preferences, test API key connection.

---

### Screen 13: Storage Management & Disk Telemetry (`/settings/storage`)
- **Purpose:** Visual breakdown of SSD usage across media categories with safe cleanup triggers.
- **Layout Structure:** Segmented storage usage bar (Uploads, Extracted Audio, Intermediate Clips, Rendered Exports, Database).
- **Main Components:** `<StorageSegmentBar />`, `<DiskCapacityIndicator />`, `<PurgeTempFilesButton />`, `<BackupDatabaseButton />`.
- **User Actions:** Click *"Clean Temporary Files"* (safely purges `storage/temp/` and intermediate cuts without touching user exports); click *"Create Database Backup"*.
- **Safety Safeguard:** Exported MP4s in `storage/exports/` are explicitly excluded from automatic purge.

---

### Screen 14: Error Handling & Recovery Modals
- **Purpose:** User-friendly, non-technical recovery dialogs for runtime anomalies.
- **Scenarios Handled:**
  1. *GPU VRAM Exhaustion:* Dialog explains: *"GPU memory was fully utilized by other applications. Clipsly automatically finished your task using the high-speed AMD Ryzen 7 CPU."* Action: *"Acknowledge"*.
  2. *Low Disk Space Alert:* Warning modal when SSD space falls below 10GB: *"Less than 10GB available on local drive. Please clean temporary files or free up disk space to continue exporting."*
  3. *Missing Media File:* Alert badge showing broken link icon: *"Source video could not be found at storage/uploads/{id}.mp4. Has the file been moved?"*
  4. *Subprocess Timeout:* Modal notifying user that an FFmpeg process hung and was terminated gracefully after 10 minutes without corrupting the database.

---

## 4. Design System Component Catalog

### 4.1 UI Primitives (`frontend/src/components/ui/`)

| Component | Selector / Usage | Visual Styling | Supported Variants & States |
|---|---|---|---|
| **Button** | `<Button variant="..." size="..." loading={...}>` | Rounded 8px, font-medium, 14px text | `default`, `secondary`, `destructive`, `outline`, `ghost`, `link`, `subtle`; `loading` with spinner, `disabled`, `asChild` |
| **Card** | `<Card variant="...">` | Background `#0f0f12`, border `#27272a`, rounded-xl | `default`, `interactive` (hover border & surface), `metric`, `section`, `compact` |
| **Badge** | `<Badge variant="..." size="...">` | Pill shape, 12px font-medium, border | `default`, `secondary`, `destructive`, `outline`, `success`, `warning`, `info`, `subtle`, `disabled` |
| **Input** | `<Input error={...} />` | Background `#0f0f12`, border `#27272a`, ring violet | Default, Focused, Invalid (destructive border & ring, `aria-invalid`), Disabled |
| **Label** | `<Label required>` | Font-medium 12px, optional asterisk | Default, Required (red asterisk) |
| **Textarea** | `<Textarea error={...} />` | Multi-line auto-resizing dark textarea | Default, Focused, Invalid, Disabled |
| **Select** | `<Select error={...}>` | Native accessible dropdown with chevron | Default, Focused, Invalid, Disabled |
| **Checkbox** | `<Checkbox checked={...} />` | Accessible checkbox with SVG checkmark | Checked, Unchecked, Disabled, with Label & Description |
| **Switch** | `<Switch checked={...} />` | Smooth sliding toggle switch | Checked, Unchecked, Disabled, with Label & Description |
| **Slider** | `<Slider value={...} />` | Precision single-handle slider with percentage fill | Single value, Range, with Label and Tabular value readout |
| **Progress** | `<Progress value={...} />` | Determinate / Indeterminate bar | Determinate (0-100%), Indeterminate (pulsing), `success`, `warning`, `destructive` |
| **Table** | `<Table>`, `<TableHeader>`, `<TableRow>`, etc. | High-density semantic tabular layout | Default, Hover row highlight, font-mono tabular data |
| **ScrollArea** | `<ScrollArea maxHeight={...}>` | Subtle custom dark scrollbar container | Vertical, Horizontal, Auto |
| **Kbd** | `<Kbd>Ctrl + K</Kbd>` | Workstation keyboard hotkey badge | Monospace 10px uppercase |
| **StatusIndicator**| `<StatusIndicator status="...">` | Status dot with optional ping animation | `healthy`, `degraded`, `error`, `processing`, `offline`, `neutral` |
| **Dialog** | `<Dialog>`, `<DialogContent>` | Accessible modal with backdrop blur | Open, Close, Escape key dismissal, Focus trap |
| **Toast** | `toast.success()`, `error()`, etc. | Floating alerts fixed at bottom-right | `success`, `error`, `warning`, `info` with auto-dismissal |

### 4.2 Workstation-Specific Modules (`frontend/src/components/workstation/`)

| Component | Selector / Usage | Purpose & Technical Contract |
|---|---|---|
| **VideoThumbnail** | `<VideoThumbnail aspectRatio="16:9" durationSeconds={...} />` | 16:9, 9:16 or 1:1 container with duration badge, resolution tag, play overlay, and clean fallback |
| **VideoMetadataRow** | `<VideoMetadataRow durationSeconds={...} width={...} fps={...} />` | Compact technical pill row: duration, resolution, fps, video/audio codecs, and formatted file size |
| **ProcessingStatus** | `<ProcessingStatus status="..." progressPercent={...} />` | Pipeline task state (`QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`, `CANCELLED`) with progress and step log |
| **StorageUsageBar** | `<StorageUsageBar freeSpaceGb={...} totalSpaceGb={...} />` | Visual SSD capacity bar with GB readouts and critical warning if free space &lt; 10GB |
| **HardwareMetricCard** | `<HardwareMetricCard title="..." value="..." percent={...} />` | Real-time GPU VRAM, compute utilization, RAM, and disk metrics with safe/warn/error thresholds |
| **EmptyVideoLibrary** | `<EmptyVideoLibrary onUploadClick={...} />` | Workstation empty state with upload CTA and local SSD storage guarantee notes |
| **FeatureUnavailable** | `<FeatureUnavailable featureName="..." activationPhase="..." />` | Transparent banner explaining which upcoming phase activates the feature |
| **SectionHeader** | `<SectionHeader title="..." description="..." badge={...} />` | Reusable section/page title container with actions and badge slots |
| **PageToolbar** | `<PageToolbar searchSlot={...} filterSlot={...} actionSlot={...} />` | Workstation toolbar for search filters, sorting dropdowns, and batch operations |

### 4.3 Component Showcase Route

The application includes an internal showcase at route `/design-system` (`ComponentShowcasePage.tsx`) which renders live interactive instances of all tokens, primitives, form controls, and workstation components.

---

## 5. Current Status & Next Steps

- **Status:** **PHASE 09 (DESIGN SYSTEM & UI COMPONENTS) COMPLETED & VERIFIED.**
- **Implementation Highlights:**
  - Token scale with HSL CSS variables, dark palette (#09090b canvas, #0f0f12 panels, #7c3aed primary violet), karaoke accents, and telemetry tokens.
  - 17 UI primitives and 9 workstation-specific components implemented and tested.
  - Component Showcase view mounted at `/design-system` and linked from Settings.
  - 51/51 frontend Vitest tests passing; ESLint clean; TypeScript strict build clean.
- **Immediate Next Step:** Proceed to Phase 10 (Audio Extraction & Media Metadata Pipeline) upon user approval.
