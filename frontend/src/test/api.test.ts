import { describe, it, expect, vi, beforeEach } from "vitest";
import { api, ClipslyApiError } from "../services/api";

describe("Centralized API Client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("successfully fetches system health via GET /api/v1/system/health", async () => {
    const mockHealth = {
      status: "healthy",
      version: "1.0.0",
      database_connected: true,
      cuda_available: true,
      nvenc_available: true,
      active_jobs_count: 0,
      uptime_seconds: 42.0,
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockHealth,
    });

    const data = await api.system.getHealth();
    expect(data.status).toBe("healthy");
    expect(data.database_connected).toBe(true);
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/v1/system/health",
      expect.objectContaining({ method: "GET" })
    );
  });

  it("handles structured API error responses and extracts detail", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: async () => ({
        detail: "Video with ID 123 does not exist",
        error_code: "VIDEO_NOT_FOUND",
      }),
    });

    await expect(api.videos.get("123")).rejects.toThrow(ClipslyApiError);

    try {
      await api.videos.get("123");
    } catch (err) {
      const apiErr = err as ClipslyApiError;
      expect(apiErr.statusCode).toBe(404);
      expect(apiErr.detail).toBe("Video with ID 123 does not exist");
      expect(apiErr.errorCode).toBe("VIDEO_NOT_FOUND");
    }
  });

  it("handles network failures gracefully with 503 error", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("Failed to fetch"));

    await expect(api.system.getHealth()).rejects.toThrow(ClipslyApiError);

    try {
      await api.system.getHealth();
    } catch (err) {
      const apiErr = err as ClipslyApiError;
      expect(apiErr.statusCode).toBe(503);
      expect(apiErr.detail).toContain("Failed to fetch");
    }
  });
});
