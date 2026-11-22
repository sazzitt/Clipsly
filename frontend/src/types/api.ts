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

export type VideoStatus = "uploaded" | "processing" | "ready" | "failed";

export interface Video {
  id: string;
  filename: string;
  original_name: string;
  file_path: string;
  file_size_bytes: number;
  duration_seconds: number;
  width: number;
  height: number;
  aspect_ratio: string;
  fps: number;
  video_codec: string;
  audio_codec: string;
  status: VideoStatus;
  created_at: string;
  updated_at: string;
}

export type JobStatus =
  | "queued"
  | "extracting_audio"
  | "transcribing"
  | "scoring"
  | "completed"
  | "failed"
  | "cancelled";

export interface ProcessingJob {
  id: string;
  video_id: string;
  status: JobStatus;
  current_stage: string;
  progress_percent: number;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface Transcript {
  id: string;
  video_id: string;
  language: string;
  duration_seconds: number;
  model_name: string;
  created_at: string;
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
  start_time: number;
  end_time: number;
  duration_seconds: number;
  rank: number;
  composite_score: number;
  hook_score: number;
  flow_score: number;
  density_score: number;
  energy_score: number;
  explanation?: string | null;
}

export type AspectRatio = "9:16" | "1:1" | "16:9";
export type CropMode = "blur_fill" | "center_crop";
export type ClipStatus = "draft" | "rendered" | "exported";

export interface Clip {
  id: string;
  video_id: string;
  highlight_id?: string | null;
  title: string;
  start_time: number;
  end_time: number;
  duration_seconds: number;
  aspect_ratio: AspectRatio;
  crop_mode: CropMode;
  subtitle_style?: string;
  status: ClipStatus;
  file_path?: string | null;
  created_at: string;
  updated_at: string;
}

export type ExportStatus = "pending" | "rendering" | "completed" | "failed";

export interface ExportJob {
  id: string;
  clip_id: string;
  status: ExportStatus;
  progress_percent: number;
  output_file_path?: string | null;
  encoder_used?: string;
  render_duration_seconds?: number | null;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
}
