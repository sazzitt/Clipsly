/**
 * Centralized API Client for Clipsly
 * Implements typed endpoints, timeout handling, error unwrapping, and AbortController integration.
 * Strictly adheres to Phase 04 REST API Contracts (docs/05-API.md).
 */

import {
  ApiError,
  Clip,
  ExportJob,
  Highlight,
  PaginatedResponse,
  ProcessingJob,
  RootApiResponse,
  SystemHardwareTelemetry,
  SystemHealth,
  Transcript,
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

// Scoped API Methods
export const api = {
  system: {
    getHealth: (signal?: AbortSignal) =>
      request<SystemHealth>("/system/health", { method: "GET", signal }),
    getInfo: (signal?: AbortSignal) =>
      request<Record<string, unknown>>("/system/info", { method: "GET", signal }),
    getHardware: (signal?: AbortSignal) =>
      request<SystemHardwareTelemetry>("/system/hardware", { method: "GET", signal }),
  },

  videos: {
    list: (page = 1, limit = 20, signal?: AbortSignal) =>
      request<PaginatedResponse<Video>>(`/videos?page=${page}&limit=${limit}`, { method: "GET", signal }),
    get: (id: string, signal?: AbortSignal) =>
      request<Video>(`/videos/${id}`, { method: "GET", signal }),
    delete: (id: string, signal?: AbortSignal) =>
      request<{ success: boolean; id: string }>(`/videos/${id}`, { method: "DELETE", signal }),
  },

  jobs: {
    get: (jobId: string, signal?: AbortSignal) =>
      request<ProcessingJob>(`/jobs/${jobId}`, { method: "GET", signal }),
    cancel: (jobId: string, signal?: AbortSignal) =>
      request<{ success: boolean; message: string }>(`/jobs/${jobId}/cancel`, { method: "POST", signal }),
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
    list: (videoId?: string, signal?: AbortSignal) => {
      const query = videoId ? `?video_id=${videoId}` : "";
      return request<Clip[]>(`/clips${query}`, { method: "GET", signal });
    },
    get: (clipId: string, signal?: AbortSignal) =>
      request<Clip>(`/clips/${clipId}`, { method: "GET", signal }),
  },

  exports: {
    list: (signal?: AbortSignal) =>
      request<ExportJob[]>("/exports", { method: "GET", signal }),
    get: (exportId: string, signal?: AbortSignal) =>
      request<ExportJob>(`/exports/${exportId}`, { method: "GET", signal }),
  },
};

// Backward-compatibility helpers for Phase 06 components
export async function fetchSystemHealth(signal?: AbortSignal): Promise<SystemHealth> {
  return api.system.getHealth(signal);
}

export async function fetchRootMeta(signal?: AbortSignal): Promise<RootApiResponse> {
  return request<RootApiResponse>("/", { method: "GET", signal });
}
