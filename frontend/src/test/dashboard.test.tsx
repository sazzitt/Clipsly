import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { DashboardSummary } from "../types/api";

const mockPopulatedDashboard: DashboardSummary = {
  counts: {
    total_videos: 3,
    total_clips: 8,
    active_jobs: 1,
    completed_exports: 5,
    total_transcripts: 3,
    total_highlights: 12,
  },
  storage: {
    ssd_free_gb: 215.4,
    ssd_total_gb: 512.0,
    clipsly_storage_bytes: 145000000, // ~138.3 MB
    storage_path: "C:\\Clipsly\\data\\videos",
    is_critical: false,
  },
  hardware: {
    gpu_vram_used_mb: 1850,
    gpu_vram_total_mb: 4096,
    gpu_vram_free_mb: 2246,
    gpu_utilization_percent: 42,
    cpu_load_percent: 34,
    system_ram_used_gb: 8.5,
    system_ram_total_gb: 16.0,
    ssd_free_space_gb: 215.4,
  },
  system: {
    status: "healthy",
    version: "1.0.0",
    database_connected: true,
    cuda_available: true,
    nvenc_available: true,
    active_jobs_count: 1,
    uptime_seconds: 420.5,
  },
  recent_videos: [
    {
      id: "vid-1",
      filename: "podcast_ep12.mp4",
      original_filename: "Tech Podcast Episode 12.mp4",
      file_size_bytes: 84000000,
      duration_seconds: 1245.0,
      width: 1920,
      height: 1080,
      fps: 30.0,
      status: "ready",
      created_at: "2026-11-22T10:00:00Z",
    },
    {
      id: "vid-2",
      filename: "interview_dan.mp4",
      original_filename: "Interview with Dan.mp4",
      file_size_bytes: 61000000,
      duration_seconds: 820.0,
      width: 1920,
      height: 1080,
      fps: 60.0,
      status: "processing",
      created_at: "2026-11-22T11:30:00Z",
    },
  ],
  recent_jobs: [
    {
      id: "job-101",
      video_id: "vid-2",
      job_type: "WHISPER_TRANSCRIPTION",
      status: "PROCESSING",
      progress_percent: 65,
      current_step: "Transcribing audio chunks...",
      error_message: null,
      created_at: "2026-11-22T11:32:00Z",
    },
    {
      id: "job-100",
      video_id: "vid-1",
      job_type: "INGESTION",
      status: "COMPLETED",
      progress_percent: 100,
      current_step: "Metadata probe extracted",
      error_message: null,
      created_at: "2026-11-22T10:02:00Z",
    },
  ],
};

const mockEmptyDashboard: DashboardSummary = {
  counts: {
    total_videos: 0,
    total_clips: 0,
    active_jobs: 0,
    completed_exports: 0,
    total_transcripts: 0,
    total_highlights: 0,
  },
  storage: {
    ssd_free_gb: 340.0,
    ssd_total_gb: 512.0,
    clipsly_storage_bytes: 0,
    storage_path: "data/videos",
    is_critical: false,
  },
  hardware: {
    gpu_vram_used_mb: 500,
    gpu_vram_total_mb: 4096,
    gpu_vram_free_mb: 3596,
    gpu_utilization_percent: 5,
    cpu_load_percent: 12,
    system_ram_used_gb: 6.2,
    system_ram_total_gb: 16.0,
    ssd_free_space_gb: 340.0,
  },
  system: {
    status: "healthy",
    version: "1.0.0",
    database_connected: true,
    cuda_available: true,
    nvenc_available: true,
    active_jobs_count: 0,
    uptime_seconds: 60.0,
  },
  recent_videos: [],
  recent_jobs: [],
};

describe("Dashboard Page & Workstation Overview", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading skeleton while fetching initial dashboard telemetry", () => {
    // Return a promise that never resolves immediately
    global.fetch = vi.fn().mockImplementation(() => new Promise(() => {}));

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(screen.getByTestId("dashboard-loading-skeleton")).toBeInTheDocument();
  });

  it("renders populated workstation dashboard with metrics, hardware, storage, and lists", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockPopulatedDashboard,
    });

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <DashboardPage />
      </MemoryRouter>
    );

    // Header & Titles
    expect(await screen.findByText("Clipsly Workstation Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Backend Healthy")).toBeInTheDocument();

    // Metric Cards
    expect(screen.getByText("Total Videos")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("Generated Clips")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("Completed Exports")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();

    // Quick Actions
    expect(screen.getByText("Import Video")).toBeInTheDocument();
    expect(screen.getByText("Video Library")).toBeInTheDocument();
    expect(screen.getByText("Clips Studio")).toBeInTheDocument();
    expect(screen.getByText("Export Queue")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();

    // Storage Diagnostics
    expect(screen.getByText("Storage Diagnostics")).toBeInTheDocument();
    expect(screen.getByText(/215.4 GB free/i)).toBeInTheDocument();

    // Hardware Telemetry
    expect(screen.getByText("GPU VRAM")).toBeInTheDocument();
    expect(screen.getByText("1850 MB")).toBeInTheDocument();
    expect(screen.getByText("GPU Compute Load")).toBeInTheDocument();
    expect(screen.getAllByText("42%").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("34%").length).toBeGreaterThanOrEqual(1); // CPU Load

    // Recent Videos
    expect(screen.getByText("Tech Podcast Episode 12.mp4")).toBeInTheDocument();
    expect(screen.getByText("Interview with Dan.mp4")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getAllByText("Processing").length).toBeGreaterThanOrEqual(1);

    // Recent Jobs
    expect(screen.getByText("Transcribing audio chunks...")).toBeInTheDocument();
    expect(screen.getByText("Metadata probe extracted")).toBeInTheDocument();

    // Backend Readiness
    expect(screen.getByText("SQLite 3 (WAL Mode)")).toBeInTheDocument();
    expect(screen.getByText("NVIDIA CUDA Ready")).toBeInTheDocument();
    expect(screen.getByText("FFmpeg h264_nvenc")).toBeInTheDocument();
  });

  it("renders empty database state cleanly when 0 videos and 0 jobs exist", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockEmptyDashboard,
    });

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByText("Clipsly Workstation Dashboard")).toBeInTheDocument();

    // Shows 0 counts across metric cards
    expect(screen.getAllByText("0").length).toBeGreaterThanOrEqual(4);

    // Empty video state CTA
    expect(screen.getByText("No Videos Ingested")).toBeInTheDocument();
    expect(screen.getByText("Import Local Video")).toBeInTheDocument();

    // Empty background activity
    expect(screen.getByText("No Background Tasks")).toBeInTheDocument();
  });

  it("renders error state when backend is unreachable and allows retry", async () => {
    let callCount = 0;
    global.fetch = vi.fn().mockImplementation(() => {
      callCount++;
      if (callCount === 1) {
        return Promise.reject(new Error("Failed to communicate with local backend."));
      }
      return Promise.resolve({
        ok: true,
        json: async () => mockPopulatedDashboard,
      });
    });

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <DashboardPage />
      </MemoryRouter>
    );

    // Error state rendered
    expect(await screen.findByTestId("dashboard-error-state")).toBeInTheDocument();
    expect(screen.getByText("Backend Connection Failed")).toBeInTheDocument();

    // Click Retry
    const retryBtn = screen.getByRole("button", { name: /Retry Connection/i });
    fireEvent.click(retryBtn);

    // Successfully loaded on retry
    await waitFor(() => {
      expect(screen.getByText("Clipsly Workstation Dashboard")).toBeInTheDocument();
    });
  });

  it("handles manual telemetry refresh button click", async () => {
    let callCount = 0;
    global.fetch = vi.fn().mockImplementation(() => {
      callCount++;
      return Promise.resolve({
        ok: true,
        json: async () => mockPopulatedDashboard,
      });
    });

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByText("Clipsly Workstation Dashboard")).toBeInTheDocument();

    const refreshBtn = screen.getByRole("button", { name: /Refresh dashboard data/i });
    fireEvent.click(refreshBtn);

    await waitFor(() => {
      expect(callCount).toBeGreaterThanOrEqual(2);
    });
  });
});
