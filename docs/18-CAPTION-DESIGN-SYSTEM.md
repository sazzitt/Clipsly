# Clipsly Phase 18 — Caption Design System & Preset Specifications

## 1. Design System Overview

The **Clipsly Caption Design System** establishes a consistent, high-impact typographic foundation for burned and previewed short-form video subtitles. On mobile devices, viewers watch vertical videos in diverse, noisy environments where high contrast, instantaneous readability, and clean animation pacing are essential.

All styling rules are specified against a standard **$1080 \times 1920$ vertical canvas**. The design system guarantees:
- **Zero UI Collision:** Captions remain outside TikTok, Instagram Reels, and YouTube Shorts system chrome (top status bar, bottom description text, right-side action buttons).
- **Universal Legibility:** Every style utilizes a solid outline (`Outline >= 5px`) or high-contrast backing box (`BorderStyle=3`) ensuring text is readable against bright backgrounds, outdoor footage, or dark scenes.
- **Separation of Concerns:** Styling parameters are defined as declarative JSON configurations in SQLite (`subtitle_presets`), decoupling design rules from FFmpeg command execution.

---

## 2. Typographic Foundation & Font Stacks

Fonts used by Clipsly must be installed locally on Windows (`C:\Windows\Fonts`) or bundled in `backend/assets/fonts/`:

| Font Family | Weight / Style | Characteristics | Target Use Cases |
|---|---|---|---|
| **Montserrat** | Black (900) / ExtraBold (800) | Geometric, wide aperture, punchy capitals | Default short-form hook, viral speech, bold captions |
| **Inter** | ExtraBold (800) / Bold (700) | Ultra-clean, neutral neo-grotesque, high x-height | Modern tech, tutorials, business interviews |
| **Impact** | Condensed Heavy | Ultra-dense, maximum height-to-width ratio | Classic internet viral memes, aggressive emphasis |
| **Arial** | Black (900) | Universally available Windows system fallback | Guaranteed zero-fail fallback across any host |
| **Roboto** | Medium (500) / Bold (700) | Friendly, open curves, soft rhythm | Long-form narrative, relaxed podcast discussions |
| **Merriweather** | Bold (700) / Italic | Warm modern serif with high legibility | Cinematic documentaries, essay clips, storytelling |

---

## 3. The 6 Canonical Caption Presets

```
+-----------------------------------------------------------------------------------------------------------------------------------------+
| Preset Name      Font Family     Fontsize  Primary Color   Highlight Color Outline Color   Stroke Shadow Align MarginV MaxWords BoxStyle|
+-----------------------------------------------------------------------------------------------------------------------------------------+
| 1. Minimal       Inter           76        #FFFFFF         #38BDF8 (Sky)   #000000         6.0px  2.0px   2     380px   4-6      Outline|
| 2. Modern        Montserrat      84        #FFFFFF         #06B6D4 (Cyan)  #000000         8.0px  3.0px   2     380px   3-5      Outline|
| 3. Bold          Impact          96        #FFFFFF         #FACC15 (Yellow)#000000         10.0px 4.0px   2     400px   2-4      Outline|
| 4. Karaoke Amber Montserrat      88        #FFFFFF         #F59E0B (Amber) #000000         8.0px  3.0px   2     380px   2-4      Outline|
| 5. Podcast       Inter           72        #F8FAFC         #10B981 (Mint)  #000000         0.0px  0.0px   2     360px   4-6      Box 50%|
| 6. Cinematic     Merriweather    74        #FEF08A         #F43F5E (Rose)  #000000         4.0px  6.0px   2     320px   4-6      Shadow |
+-----------------------------------------------------------------------------------------------------------------------------------------+
```

---

### Preset 1: Minimal
- **Concept:** Understated, clean, and legible. Designed for instructional, tech, and conversational videos where heavy meme styling would distract.
- **Font:** `Inter`, Bold (700), Size: 76
- **Case:** Title Case or Sentence Case
- **Colors:**
  - Primary (Spoken): `#FFFFFF` (Solid White, `&H00FFFFFF`)
  - Highlight (Active Word): `#38BDF8` (Sky Blue, `&H00F8BD38`)
  - Outline: `#000000` (Solid Black, `&H00000000`), Stroke Width: `6.0px`
  - Shadow: `#000000` with 40% Alpha (`&H66000000`), Depth: `2.0px`
- **Positioning:** `Alignment=2` (Bottom Center), `MarginV=380px`, `MarginL=120px`, `MarginR=120px`
- **Pacing:** 4 to 6 words per line.

---

### Preset 2: Modern
- **Concept:** Sleek, high-energy tech look. Uses uppercase typography with vibrant electric cyan word illumination.
- **Font:** `Montserrat`, ExtraBold (800), Size: 84
- **Case:** ALL UPPERCASE (`text-transform: uppercase`)
- **Colors:**
  - Primary (Base): `#FFFFFF` (`&H00FFFFFF`)
  - Highlight (Active Word): `#06B6D4` (Neon Cyan, `&H00D4B606`)
  - Outline: `#000000` (`&H00000000`), Stroke Width: `8.0px`
  - Shadow: `#000000` with 60% Alpha (`&H99000000`), Depth: `3.0px`
- **Animation:** `\kf` smooth fill transition across words.
- **Positioning:** `Alignment=2` (Bottom Center), `MarginV=380px`
- **Pacing:** 3 to 5 words per line.

---

### Preset 3: Bold (High-Impact Viral)
- **Concept:** Massive, dense lettering inspired by viral short-form hooks. High stroke weight ensures 100% readability even over chaotic video backgrounds.
- **Font:** `Impact`, Regular (Heavy), Size: 96
- **Case:** ALL UPPERCASE
- **Colors:**
  - Primary (Base): `#FFFFFF` (`&H00FFFFFF`)
  - Highlight (Active Word): `#FACC15` (Intense Yellow, `&H0015CCFA`)
  - Outline: `#000000` (`&H00000000`), Stroke Width: `10.0px`
  - Shadow: `#000000` (`&H00000000`), Depth: `4.0px`
- **Animation:** Instant pop `\k` with active scale pulse `{\fscx110\fscy110}`.
- **Positioning:** `Alignment=2` (Bottom Center), `MarginV=400px`
- **Pacing:** 2 to 4 words per line.

---

### Preset 4: Karaoke Amber (Clipsly Default)
- **Concept:** The flagship Clipsly style. Warm gold/amber illumination that naturally draws viewer attention without eye fatigue.
- **Font:** `Montserrat`, Black (900), Size: 88
- **Case:** ALL UPPERCASE
- **Colors:**
  - Primary (Base): `#FFFFFF` (`&H00FFFFFF`)
  - Highlight (Active Word): `#F59E0B` (Warm Amber Gold, `&H000B9EF5`)
  - Outline: `#000000` (`&H00000000`), Stroke Width: `8.0px`
  - Shadow: `#000000` with 50% Alpha (`&H80000000`), Depth: `3.0px`
- **Animation:** Smooth sweep `\kf` timing.
- **Positioning:** `Alignment=2` (Bottom Center), `MarginV=380px`
- **Pacing:** 2 to 4 words per line.

---

### Preset 5: Podcast (Boxed Subtitles)
- **Concept:** Broadcaster style with a semi-transparent black backing box. Eliminates outline clutter and mimics professional television / Netflix broadcast captions.
- **Font:** `Inter`, SemiBold (600), Size: 72
- **Case:** Sentence Case
- **Colors:**
  - Primary (Base): `#F8FAFC` (Off-white Slate, `&H00FCFAF8`)
  - Highlight (Active Word): `#10B981` (Fresh Mint Green, `&H0081B910`)
  - Outline: None (`Outline=0.0`)
  - Backing Box: `#000000` with 65% Opacity (`&HA6000000`)
- **Border Style:** `BorderStyle=3` (Enclosed rectangular bounding box with padding)
- **Positioning:** `Alignment=2` (Bottom Center), `MarginV=360px`, `MarginL=100px`, `MarginR=100px`
- **Pacing:** 4 to 6 words per line.

---

### Preset 6: Cinematic
- **Concept:** Elegant letterspaced styling for dramatic essays, artistic narratives, and documentary clips.
- **Font:** `Merriweather`, Bold (700) Italic, Size: 74
- **Case:** Sentence Case with wider letterspacing (`Spacing=3`)
- **Colors:**
  - Primary (Base): `#FEF08A` (Soft Ivory Yellow, `&H008AF0FE`)
  - Highlight (Active Word): `#F43F5E` (High-Energy Rose, `&H005E3FF4`)
  - Outline: `#1E1B4B` (Deep Navy, `&H004B1B1E`), Stroke Width: `4.0px`
  - Shadow: `#000000` (`&H00000000`), Depth: `6.0px` (Deep offset shadow)
- **Positioning:** `Alignment=2` (Bottom Center), `MarginV=320px`
- **Pacing:** 4 to 6 words per line.

---

## 4. Vertical Position Mapping

Clipsly provides three primary vertical positions configurable in the UI:

| Setting Key | ASS Alignment | Vertical Anchor | MarginV Value | Description |
|---|---|---|---|---|
| `BOTTOM` (Default) | `Alignment=2` | Bottom of frame | `380px` | Positioned above TikTok/Reels captions and username. |
| `MIDDLE` | `Alignment=5` | Center of frame | `0px` | Centered horizontally and vertically at $Y = 960\text{px}$. Ideal for talking-head podcast framing. |
| `TOP` | `Alignment=8` | Top of frame | `280px` | Positioned below smartphone camera notch and platform search bars. |

---

## 5. Client-Side CSS Preview Equivalents

To allow instant subtitle previews in `StudioPage.tsx` without waiting for FFmpeg renders, the frontend maps ASS styles directly to HTML/CSS:

```css
/* CSS Token Mapping for Studio Canvas Overlay (1080x1920 normalized coordinates) */

.clipsly-caption-container {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  width: 85%;
  text-align: center;
  pointer-events: none;
  user-select: none;
}

.clipsly-caption-bottom {
  bottom: 20%; /* Corresponds to MarginV=380px on 1920px canvas */
}

.clipsly-caption-middle {
  top: 50%;
  transform: translate(-50%, -50%);
}

.clipsly-caption-top {
  top: 15%; /* Corresponds to MarginV=280px */
}

/* Preset 4: Karaoke Amber Text Effect */
.clipsly-style-karaoke-amber {
  font-family: 'Montserrat', sans-serif;
  font-weight: 900;
  font-size: clamp(18px, 4.4vw, 44px);
  text-transform: uppercase;
  color: #FFFFFF;
  text-shadow:
    -2px -2px 0 #000,
     2px -2px 0 #000,
    -2px  2px 0 #000,
     2px  2px 0 #000,
     0px  3px 6px rgba(0, 0, 0, 0.7);
}

.clipsly-word-active {
  color: #F59E0B !important; /* Active Word Gold */
  transform: scale(1.08);
  display: inline-block;
  transition: transform 0.08s ease, color 0.08s ease;
}
```
