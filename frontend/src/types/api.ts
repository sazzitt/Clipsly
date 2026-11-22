/**
 * Canonical TypeScript Interfaces for Clipsly Frontend
 * Strictly aligns with Phase 04 REST API contracts (docs/05-API.md) and Phase 03 Database Schema (docs/04-DATABASE.md).
 */

export interface ApiError {
  detail: string;
  error_code?: string;
  status_code?: number;
}

export interface RootApiResponse {
  application: string;
  version: string;
  docs: string;
  health: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface SystemHealth {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  database_connected: boolean;
  cuda_available: boolean;
  nvenc_available: boolean;
  active_jobs_count: number;
  uptime_seconds: number;
}

export interface SystemHardwareTelemetry {
  gpu_vram_used_mb: number;
  gpu_vram_total_mb: number;
  gpu_vram_free_mb: number;
  gpu_utilization_percent: number;
  cpu_load_percent: number;
  system_ram_used_gb: number;
  system_ram_total_gb: number;
  ssd_free_space_gb: number;
}

export type VideoStatus = "uploaded" | "processing" | "ready" | "failed" | string;

export interface Video {
  id: string;
  filename: string;
  original_filename: string;
  original_name?: string;
  file_path?: string;
  file_size_bytes: number;
  duration_seconds: number;
  width: number;
  height: number;
  aspect_ratio: string;
  fps: number;
  video_codec: string;
  audio_codec: string;
  audio_sample_rate?: number;
  audio_channels?: number;
  status: VideoStatus;
  error_message?: string | null;
  file_exists?: boolean;
  processing_jobs_count?: number;
  clips_count?: number;
  transcripts_count?: number;
  highlights_count?: number;
  created_at: string;
  updated_at?: string | null;
}

export type JobStatus =
  | "queued"
  | "extracting_audio"
  | "transcribing"
  | "scoring"
  | "completed"
  | "failed"
  | "cancelled"
  | string;

export interface ProcessingJob {
  id: string;
  video_id: string;
  job_type: string;
  status: JobStatus;
  current_step: string;
  current_stage?: string;
  progress_percent: number;
  error_message?: string | null;
  process_pid?: number | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface Transcript {
  id: string;
  video_id: string;
  language: string;
  duration_seconds?: number;
  model_name: string;
  compute_type?: string;
  full_text?: string;
  word_count?: number;
  processing_time_seconds?: number;
  is_active?: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
  score: number;
}

export interface TranscriptSegment {
  id: string;
  transcript_id: string;
  start_time: number;
  end_time: number;
  text: string;
  confidence: number;
  words?: WordTimestamp[];
}

export interface Highlight {
  id: string;
  video_id: string;
  transcript_id?: string;
  start_ms?: number;
  end_ms?: number;
  start_time?: number;
  end_time?: number;
  duration_ms?: number;
  duration_seconds?: number;
  hook_sentence?: string;
  summary?: string;
  hook_score?: number;
  flow_score?: number;
  coherence_score?: number;
  density_score?: number;
  energy_score?: number;
  sentiment_score?: number;
  composite_score: number;
  category?: string;
  detection_method?: string;
  status: string;
  rank?: number;
  explanation?: string | null;
  created_at?: string | null;
}

export type AspectRatio = "9:16" | "1:1" | "16:9" | string;
export type CropMode = "blur_fill" | "center_crop" | string;
export type ClipStatus = "draft" | "rendered" | "exported" | string;

export interface Clip {
  id: string;
  video_id: string;
  video_filename?: string | null;
  highlight_id?: string | null;
  title: string;
  start_ms: number;
  end_ms: number;
  duration_ms: number;
  aspect_ratio_mode: string;
  subtitle_enabled: boolean;
  subtitle_style_preset: string;
  subtitle_font_family?: string;
  subtitle_font_size?: number;
  subtitle_primary_color?: string;
  subtitle_highlight_color?: string;
  subtitle_outline_color?: string;
  subtitle_outline_width?: number;
  subtitle_vertical_position?: string;
  custom_subtitle_text?: string | null;
  status: ClipStatus;
  file_path?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export type ExportStatus = "pending" | "rendering" | "completed" | "failed" | string;

export interface ExportJob {
  id: string;
  clip_id: string;
  clip_title?: string | null;
  video_id?: string;
  output_filename: string;
  output_path?: string | null;
  resolution: string;
  fps: number;
  encoder: string;
  render_time_seconds?: number | null;
  file_size_bytes?: number | null;
  status: ExportStatus;
  progress_percent: number;
  error_message?: string | null;
  process_pid?: number | null;
  file_exists?: boolean;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface DashboardCounts {
  total_videos: number;
  total_clips: number;
  active_jobs: number;
  completed_exports: number;
  total_transcripts: number;
  total_highlights: number;
}

export interface DashboardStorageSummary {
  ssd_free_gb: number;
  ssd_total_gb: number;
  clipsly_storage_bytes: number;
  storage_path: string;
  is_critical: boolean;
}

export interface DashboardRecentVideoItem {
  id: string;
  filename: string;
  original_filename: string;
  file_size_bytes: number;
  duration_seconds: number;
  width: number;
  height: number;
  fps: number;
  status: string;
  created_at?: string | null;
}

export interface DashboardRecentJobItem {
  id: string;
  video_id: string;
  job_type: string;
  status: string;
  progress_percent: number;
  current_step: string;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface DashboardSummary {
  counts: DashboardCounts;
  storage: DashboardStorageSummary;
  hardware: SystemHardwareTelemetry;
  system: SystemHealth;
  recent_videos: DashboardRecentVideoItem[];
  recent_jobs: DashboardRecentJobItem[];
}

