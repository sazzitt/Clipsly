/**
 * Centralized API Client for Clipsly
 * Implements typed endpoints, timeout handling, error unwrapping, and AbortController integration.
 * Strictly adheres to Phase 04 REST API Contracts (docs/05-API.md).
 */

import {
  ApiError,
  AudioAsset,
  AudioExtractionJobResponse,
  AudioExtractionRequest,
  AudioStreamInfo,
  Clip,
  DashboardSummary,
  ExportJob,
  Highlight,
  PaginatedResponse,
  ProcessingJob,
  RootApiResponse,
  SystemHardwareTelemetry,
  SystemHealth,
  Transcript,
  UploadOptions,
  Video,
} from "../types/api";

const API_BASE_URL = "/api/v1";
const DEFAULT_TIMEOUT_MS = 10000;

export class ClipslyApiError extends Error {
  public readonly statusCode: number;
  public readonly errorCode?: string;
  public readonly detail: string;

  constructor(statusCode: number, detail: string, errorCode?: string) {
    super(`[API ${statusCode}] ${detail}`);
    this.name = "ClipslyApiError";
    this.statusCode = statusCode;
    this.errorCode = errorCode;
    this.detail = detail;
  }
}

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, headers, signal, ...rest } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  // Link caller signal if provided
  if (signal) {
    signal.addEventListener("abort", () => controller.abort());
  }

  const url = endpoint.startsWith("http") || endpoint.startsWith("/api") || endpoint === "/"
    ? endpoint
    : `${API_BASE_URL}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...rest,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...headers,
      },
    });

    if (!response.ok) {
      let detail = response.statusText;
      let errorCode: string | undefined;

      try {
        const errorBody: ApiError = await response.json();
        if (errorBody && typeof errorBody.detail === "string") {
          detail = errorBody.detail;
          errorCode = errorBody.error_code;
        }
      } catch {
        // Response body wasn't JSON
      }

      throw new ClipslyApiError(response.status, detail, errorCode);
    }

    return (await response.json()) as T;
  } catch (err: unknown) {
    if (err instanceof ClipslyApiError) {
      throw err;
    }
    if (err instanceof Error) {
      if (err.name === "AbortError") {
        throw new ClipslyApiError(408, `Request timed out after ${timeoutMs}ms`);
      }
      throw new ClipslyApiError(503, err.message);
    }
    throw new ClipslyApiError(500, "Unknown network communication error occurred");
  } finally {
    clearTimeout(timeoutId);
  }
}

export interface VideoListParams {
  page?: number;
  limit?: number;
  search?: string;
  status?: string;
  sort_by?: string;
  order?: "asc" | "desc";
}

export interface JobListParams {
  page?: number;
  limit?: number;
  video_id?: string;
  status?: string;
  job_type?: string;
  search?: string;
  sort_by?: string;
  order?: "asc" | "desc";
}

export interface ClipListParams {
  page?: number;
  limit?: number;
  video_id?: string;
  status?: string;
  search?: string;
  sort_by?: string;
  order?: "asc" | "desc";
}

export interface ExportListParams {
  page?: number;
  limit?: number;
  clip_id?: string;
  video_id?: string;
  status?: string;
  search?: string;
  sort_by?: string;
  order?: "asc" | "desc";
}

function buildQueryString(params: Record<string, unknown> = {}): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.append(key, String(value));
    }
  }
  const str = searchParams.toString();
  return str ? `?${str}` : "";
}

// Scoped API Methods
export const api = {
  system: {
    getHealth: (signal?: AbortSignal) =>
      request<SystemHealth>("/system/health", { method: "GET", signal }),
    getInfo: (signal?: AbortSignal) =>
      request<Record<string, unknown>>("/system/info", { method: "GET", signal }),
    getHardware: (signal?: AbortSignal) =>
      request<SystemHardwareTelemetry>("/system/hardware", { method: "GET", signal }),
    getDashboard: (signal?: AbortSignal) =>
      request<DashboardSummary>("/system/dashboard", { method: "GET", signal }),
  },

  videos: {
    list: (params?: VideoListParams | number, limit = 20, signal?: AbortSignal) => {
      let query = "";
      if (typeof params === "number") {
        query = `?page=${params}&limit=${limit}`;
      } else if (params) {
        query = buildQueryString(params as unknown as Record<string, unknown>);
      }
      return request<PaginatedResponse<Video>>(`/videos${query}`, { method: "GET", signal });
    },
    get: (id: string, signal?: AbortSignal) =>
      request<Video>(`/videos/${id}`, { method: "GET", signal }),
    upload: (file: File, options: UploadOptions = {}): Promise<Video> => {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const startTime = Date.now();

        if (options.signal) {
          if (options.signal.aborted) {
            return reject(new ClipslyApiError(499, "Upload cancelled by client", "CLIENT_CANCELLED"));
          }
          options.signal.addEventListener("abort", () => {
            xhr.abort();
            reject(new ClipslyApiError(499, "Upload cancelled by client", "CLIENT_CANCELLED"));
          });
        }

        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable && options.onProgress) {
            const now = Date.now();
            const elapsedSec = (now - startTime) / 1000;
            const currentSpeed = elapsedSec > 0 ? event.loaded / elapsedSec : 0;
            const remainingBytes = event.total - event.loaded;
            const remainingSeconds = currentSpeed > 0 ? Math.ceil(remainingBytes / currentSpeed) : null;

            options.onProgress({
              loaded: event.loaded,
              total: event.total,
              percentage: Math.min(100, Math.round((event.loaded / event.total) * 100)),
              speedBytesPerSec: Math.round(currentSpeed),
              remainingSeconds,
            });
          }
        };

        xhr.onload = () => {
          let responseData: (Record<string, unknown> & { detail?: string; error?: { message?: string; code?: string }; error_code?: string }) | null = null;
          try {
            responseData = JSON.parse(xhr.responseText);
          } catch {
            responseData = null;
          }

          if (xhr.status >= 200 && xhr.status < 300) {
            resolve((responseData as unknown) as Video);
          } else {
            const detail = responseData?.detail || responseData?.error?.message || xhr.statusText || "Upload failed";
            const errorCode = responseData?.error_code || responseData?.error?.code;
            reject(new ClipslyApiError(xhr.status, detail, errorCode));
          }
        };

        xhr.onerror = () => {
          reject(new ClipslyApiError(503, "Network error occurred during video upload", "NETWORK_ERROR"));
        };

        xhr.ontimeout = () => {
          reject(new ClipslyApiError(408, "Video upload timed out", "TIMEOUT"));
        };

        const formData = new FormData();
        formData.append("file", file);

        xhr.open("POST", `${API_BASE_URL}/videos/upload`);
        xhr.send(formData);
      });
    },
    delete: (id: string, purgeFiles = false, signal?: AbortSignal) =>
      request<{ success: boolean; id: string; file_unlinked?: boolean }>(
        `/videos/${id}?purge_files=${purgeFiles}`,
        { method: "DELETE", signal }
      ),
    refreshMetadata: (id: string, signal?: AbortSignal) =>
      request<Video>(`/videos/${id}/metadata/refresh`, { method: "POST", signal }),
    getStreamUrl: (id: string) => `${API_BASE_URL}/videos/${id}/stream`,
    extractAudio: (id: string, options?: AudioExtractionRequest, signal?: AbortSignal) =>
      request<AudioExtractionJobResponse>(`/videos/${id}/extract-audio`, {
        method: "POST",
        body: JSON.stringify(options || {}),
        signal,
      }),
    getAudio: (id: string, signal?: AbortSignal) =>
      request<AudioAsset>(`/videos/${id}/audio`, { method: "GET", signal }),
    getAudioStreams: (id: string, signal?: AbortSignal) =>
      request<AudioStreamInfo[]>(`/videos/${id}/audio/streams`, { method: "GET", signal }),
  },

  jobs: {
    list: (params?: JobListParams, signal?: AbortSignal) => {
      const query = buildQueryString(params as unknown as Record<string, unknown>);
      return request<PaginatedResponse<ProcessingJob>>(`/jobs${query}`, { method: "GET", signal });
    },
    get: (jobId: string, signal?: AbortSignal) =>
      request<ProcessingJob>(`/jobs/${jobId}`, { method: "GET", signal }),
    cancel: (jobId: string, signal?: AbortSignal) =>
      request<{ id: string; status: string; current_step: string }>(
        `/jobs/${jobId}/cancel`,
        { method: "POST", signal }
      ),
  },

  transcripts: {
    get: (videoId: string, signal?: AbortSignal) =>
      request<Transcript>(`/transcripts/${videoId}`, { method: "GET", signal }),
  },

  highlights: {
    list: (videoId: string, signal?: AbortSignal) =>
      request<Highlight[]>(`/highlights/${videoId}`, { method: "GET", signal }),
  },

  clips: {
    list: (params?: ClipListParams | string, signal?: AbortSignal) => {
      let query = "";
      if (typeof params === "string") {
        query = `?video_id=${params}`;
      } else if (params) {
        query = buildQueryString(params as unknown as Record<string, unknown>);
      }
      return request<PaginatedResponse<Clip>>(`/clips${query}`, { method: "GET", signal });
    },
    get: (clipId: string, signal?: AbortSignal) =>
      request<Clip>(`/clips/${clipId}`, { method: "GET", signal }),
    delete: (clipId: string, signal?: AbortSignal) =>
      request<{ success: boolean; id: string }>(`/clips/${clipId}`, { method: "DELETE", signal }),
  },

  exports: {
    list: (params?: ExportListParams, signal?: AbortSignal) => {
      const query = buildQueryString(params as unknown as Record<string, unknown>);
      return request<PaginatedResponse<ExportJob>>(`/exports${query}`, { method: "GET", signal });
    },
    get: (exportId: string, signal?: AbortSignal) =>
      request<ExportJob>(`/exports/${exportId}`, { method: "GET", signal }),
    delete: (exportId: string, deleteFile = false, signal?: AbortSignal) =>
      request<{ success: boolean; id: string; file_unlinked?: boolean }>(
        `/exports/${exportId}?delete_file=${deleteFile}`,
        { method: "DELETE", signal }
      ),
  },
};

// Backward-compatibility helpers for Phase 06 components
export async function fetchSystemHealth(signal?: AbortSignal): Promise<SystemHealth> {
  return api.system.getHealth(signal);
}

export async function fetchRootMeta(signal?: AbortSignal): Promise<RootApiResponse> {
  return request<RootApiResponse>("/", { method: "GET", signal });
}
