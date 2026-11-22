import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { BackendHealthProvider } from "../components/providers/BackendHealthProvider";
import { Header } from "../components/layout/Header";
import { OfflineBanner } from "../components/common/OfflineBanner";
import { HealthStatusCard } from "../components/HealthStatusCard";

describe("Backend Health State & Telemetry", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("displays connected indicator when backend health check succeeds", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "healthy",
        version: "1.0.0",
        database_connected: true,
        cuda_available: true,
        nvenc_available: true,
        active_jobs_count: 0,
        uptime_seconds: 50.0,
      }),
    });

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <BackendHealthProvider autoPoll={false}>
          <Header />
          <OfflineBanner />
        </BackendHealthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("127.0.0.1:8000")).toBeInTheDocument();
    });

    // Offline banner should not be in document
    expect(screen.queryByText(/Local Backend Offline/i)).not.toBeInTheDocument();
  });

  it("displays offline pill and offline banner when backend is unreachable", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("Connection refused"));

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <BackendHealthProvider autoPoll={false}>
          <Header />
          <OfflineBanner />
        </BackendHealthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Offline")).toBeInTheDocument();
      expect(screen.getByText(/Local Backend Offline/i)).toBeInTheDocument();
    });
  });

  it("preserves HealthStatusCard metrics and renders SQLite WAL and CUDA status", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "healthy",
        version: "1.0.0",
        database_connected: true,
        cuda_available: true,
        nvenc_available: true,
        active_jobs_count: 0,
        uptime_seconds: 180.0,
      }),
    });

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <BackendHealthProvider autoPoll={false}>
          <HealthStatusCard />
        </BackendHealthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Backend Healthy")).toBeInTheDocument();
      expect(screen.getByText("SQLite 3 (WAL Mode)")).toBeInTheDocument();
      expect(screen.getByText("NVIDIA CUDA Ready")).toBeInTheDocument();
      expect(screen.getByText("FFmpeg h264_nvenc")).toBeInTheDocument();
      expect(screen.getByText("180.0s")).toBeInTheDocument();
    });
  });
});
