/**
 * Clipsly Centralized Design System Tokens
 * Source of Truth: docs/02-DESIGN.md
 */

export const colors = {
  background: {
    canvas: "#09090b",
    card: "#0f0f12",
    cardHover: "#16161a",
    popover: "#0c0c0e",
    border: "#27272a",
    input: "#27272a",
  },
  brand: {
    primary: "#7c3aed",
    primaryHover: "#6d28d9",
    secondary: "#27272a",
    secondaryHover: "#3f3f46",
    destructive: "#ef4444",
    destructiveHover: "#dc2626",
  },
  text: {
    primary: "#fafafa",
    muted: "#a1a1aa",
    subtle: "#71717a",
  },
  karaoke: {
    amber: "#f59e0b",
    cyan: "#06b6d4",
    mint: "#10b981",
    rose: "#f43f5e",
  },
  telemetry: {
    safe: "#22c55e",
    warn: "#f59e0b",
    err: "#ef4444",
  },
} as const;

export const typography = {
  fontSans: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  fontMono: '"JetBrains Mono", monospace',
  scale: {
    display: "text-2xl font-semibold tracking-tight",
    sectionTitle: "text-lg font-medium text-foreground",
    cardTitle: "text-base font-semibold leading-none text-foreground",
    body: "text-sm text-foreground leading-normal",
    metadata: "text-xs text-muted-foreground",
    timecode: "font-mono text-xs font-bold tabular-nums",
  },
} as const;

export const radius = {
  sm: "0.25rem",
  md: "0.375rem",
  lg: "0.5rem",
  xl: "0.75rem",
  full: "9999px",
} as const;

export const breakpoints = {
  mobile: 640,
  tablet: 768,
  laptop: 1024,
  desktop: 1280,
  wide: 1536,
} as const;
