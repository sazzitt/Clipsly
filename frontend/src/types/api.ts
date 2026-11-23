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
  storage_label?: string;
  file_path?: string;
  file_size_bytes: number;
  duration_seconds: number;
  width: number;
  height: number;
  aspect_ratio: string;
  fps: number;
  video_codec: string;
  video_codec_profile?: string | null;
  pixel_format?: string | null;
  bit_depth?: number | null;
  video_bitrate?: number | null;
  rotation?: number;
  orientation?: "landscape" | "portrait" | "square" | string;
  has_audio?: boolean;
  audio_codec?: string | null;
  audio_sample_rate?: number | null;
  audio_channels?: number | null;
  channel_layout?: string | null;
  audio_bitrate?: number | null;
  container_format?: string | null;
  bitrate?: number | null;
  status: VideoStatus;
  metadata_status?: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED" | string;
  metadata_extracted_at?: string | null;
  error_message?: string | null;
  file_exists?: boolean;
  audio_asset?: AudioAsset | null;
  audio_streams?: AudioStreamInfo[] | null;
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

export interface AudioStreamInfo {
  index: number;
  codec_name: string;
  channels: number;
  sample_rate: number;
  channel_layout?: string | null;
  bit_rate?: number | null;
  language?: string | null;
  title?: string | null;
  is_default: boolean;
}

export interface AudioAsset {
  id: string;
  video_id: string;
  job_id?: string | null;
  filename: string;
  format: string;
  codec: string;
  sample_rate: number;
  channels: number;
  channel_layout: string;
  bit_depth: number;
  duration_seconds: number;
  file_size_bytes: number;
  source_stream_index: number;
  status: string;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AudioExtractionRequest {
  stream_index?: number | null;
  force_reextract?: boolean;
}

export interface AudioExtractionJobResponse {
  job_id: string;
  video_id: string;
  status: string;
  progress_percent: number;
  current_step: string;
  audio_asset?: AudioAsset | null;
}

export interface Transcript {
  id: string;
  video_id: string;
  audio_asset_id?: string | null;
  model_name: string;
  compute_type?: string;
  device?: string;
  language: string;
  language_probability?: number | null;
  status?: string;
  full_text?: string;
  word_count?: number;
  segment_count?: number;
  audio_duration_seconds?: number | null;
  duration_seconds?: number | null;
  processing_time_seconds?: number;
  error_message?: string | null;
  is_active?: boolean;
  created_at: string;
  updated_at?: string | null;
  segments?: TranscriptSegment[] | null;
}

export interface WordTimestamp {
  word: string;
  start_ms: number;
  end_ms: number;
  probability?: number | null;
  start?: number;
  end?: number;
  score?: number;
}

export interface TranscriptSegment {
  id: string;
  transcript_id: string;
  segment_index?: number;
  start_ms: number;
  end_ms: number;
  text: string;
  words?: WordTimestamp[];
  avg_confidence?: number;
  no_speech_prob?: number | null;
  speaker_id?: string | null;
  created_at?: string | null;
  start_time?: number;
  end_time?: number;
  confidence?: number;
}

export interface TranscriptSegmentListResponse {
  transcript_id: string;
  total: number;
  offset: number;
  limit: number;
  segments: TranscriptSegment[];
}

export interface TranscriptionRequest {
  model_name?: string | null;
  device?: string | null;
  compute_type?: string | null;
  language?: string | null;
  vad_filter?: boolean | null;
  word_timestamps?: boolean | null;
  force_retranscribe?: boolean;
}

export interface TranscriptionJobResponse {
  job_id: string;
  video_id: string;
  status: string;
  progress_percent: number;
  current_step: string;
  transcript?: Transcript | null;
}

export interface ModelOptionInfo {
  model_name: string;
  description: string;
  parameters: string;
  vram_required_mb: number;
  recommended_for: string;
  devices_supported: string[];
}

export interface AvailableModelsResponse {
  models: ModelOptionInfo[];
  default_model: string;
  cuda_available: boolean;
  detected_gpu?: string | null;
  cuda_compute_types: string[];
  cpu_compute_types: string[];
}

export interface SegmentUpdateRequest {
  text: string;
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
  transcript_excerpt?: string | null;
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
  scoring_version?: string;
  explanation?: string | null;
  warnings?: string[];
  detection_metadata?: Record<string, unknown>;
  reviewed_at?: string | null;
  rejection_reason?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface HighlightListResponse {
  video_id: string;
  total: number;
  highlights: Highlight[];
}

export interface HighlightDetectionRequest {
  target_duration_presets?: string[];
  min_duration_seconds?: number;
  max_duration_seconds?: number;
  min_score?: number;
  max_results?: number;
  overlap_threshold?: number;
  hook_weight?: number;
  coherence_weight?: number;
  density_weight?: number;
  sentiment_weight?: number;
  force_redetect?: boolean;
}

export interface HighlightDetectionJobResponse {
  job_id: string;
  video_id: string;
  status: string;
  progress_percent: number;
  current_step: string;
  created_at: string;
  highlights?: Highlight[];
}

export interface HighlightUpdateRequest {
  start_ms?: number;
  end_ms?: number;
  summary?: string;
  status?: string;
}

export interface HighlightRejectRequest {
  rejection_reason?: string;
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

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
  speedBytesPerSec: number;
  remainingSeconds: number | null;
}

export interface UploadOptions {
  onProgress?: (progress: UploadProgress) => void;
  signal?: AbortSignal;
}

