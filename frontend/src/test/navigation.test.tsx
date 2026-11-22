import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AppLayout } from "../components/layout/AppLayout";
import { NotFoundPage } from "../components/common/NotFoundPage";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { VideoLibraryPage } from "../features/videos/VideoLibraryPage";
import { UploadPage } from "../features/videos/UploadPage";
import { ClipsLibraryPage } from "../features/clips/ClipsLibraryPage";
import { ExportsPage } from "../features/exports/ExportsPage";
import { SettingsPage } from "../features/settings/SettingsPage";
import { BackendHealthProvider } from "../components/providers/BackendHealthProvider";

// Test helper to render memory router
function renderWithRouter(initialRoute = "/") {
  const routes = [
    {
      path: "/",
      element: (
        <BackendHealthProvider autoPoll={false}>
          <AppLayout />
        </BackendHealthProvider>
      ),
      children: [
        { index: true, element: <DashboardPage /> },
        { path: "videos", element: <VideoLibraryPage /> },
        { path: "upload", element: <UploadPage /> },
        { path: "clips", element: <ClipsLibraryPage /> },
        { path: "exports", element: <ExportsPage /> },
        { path: "settings", element: <SettingsPage /> },
        { path: "*", element: <NotFoundPage /> },
      ],
    },
  ];

  const router = createMemoryRouter(routes, {
    initialEntries: [initialRoute],
    future: {
      v7_relativeSplatPath: true,
    },
  });

  return render(<RouterProvider router={router} future={{ v7_startTransition: true }} />);
}

describe("Application Routing & Navigation", () => {
  beforeEach(() => {
    global.fetch = vi.fn().mockImplementation(async (url: string) => {
      if (url.includes("/api/v1/system/dashboard")) {
        return {
          ok: true,
          json: async () => ({
            counts: {
              total_videos: 0,
              total_clips: 0,
              active_jobs: 0,
              completed_exports: 0,
              total_transcripts: 0,
              total_highlights: 0,
            },
            storage: {
              ssd_free_gb: 250.5,
              ssd_total_gb: 512.0,
              clipsly_storage_bytes: 0,
              storage_path: "data/videos",
              is_critical: false,
            },
            hardware: {
              gpu_vram_used_mb: 850,
              gpu_vram_total_mb: 4096,
              gpu_vram_free_mb: 3246,
              gpu_utilization_percent: 12,
              cpu_load_percent: 25,
              system_ram_used_gb: 7.2,
              system_ram_total_gb: 16.0,
              ssd_free_space_gb: 250.5,
            },
            system: {
              status: "healthy",
              version: "1.0.0",
              database_connected: true,
              cuda_available: true,
              nvenc_available: true,
              active_jobs_count: 0,
              uptime_seconds: 120.0,
            },
            recent_videos: [],
            recent_jobs: [],
          }),
        };
      }

      return {
        ok: true,
        json: async () => ({
          status: "healthy",
          version: "1.0.0",
          database_connected: true,
          cuda_available: true,
          nvenc_available: true,
          active_jobs_count: 0,
          uptime_seconds: 120.0,
        }),
      };
    });
  });

  it("renders the Dashboard on root route '/'", async () => {
    renderWithRouter("/");
    expect(await screen.findByText("Clipsly Workstation Dashboard")).toBeInTheDocument();
  });

  it("renders the Video Library page on '/videos'", async () => {
    renderWithRouter("/videos");
    expect(await screen.findByRole("heading", { name: "Video Library" })).toBeInTheDocument();
    expect(screen.getByText("No Videos Ingested Yet")).toBeInTheDocument();
  });

  it("renders the Upload page on '/upload'", async () => {
    renderWithRouter("/upload");
    expect(await screen.findByRole("heading", { name: "Upload Video" })).toBeInTheDocument();
    expect(screen.getByText(/Drop your local video file here/i)).toBeInTheDocument();
  });

  it("renders the Clips Library page on '/clips'", async () => {
    renderWithRouter("/clips");
    expect(await screen.findByRole("heading", { name: "Clips Library" })).toBeInTheDocument();
    expect(screen.getByText("No Clips Created Yet")).toBeInTheDocument();
  });

  it("renders the Export Queue page on '/exports'", async () => {
    renderWithRouter("/exports");
    expect(await screen.findByRole("heading", { name: "Export Queue" })).toBeInTheDocument();
    expect(screen.getByText("No Rendered Exports")).toBeInTheDocument();
  });

  it("renders the Settings page on '/settings'", async () => {
    renderWithRouter("/settings");
    expect(await screen.findByRole("heading", { name: "Application Settings" })).toBeInTheDocument();
    expect(screen.getByText("NVIDIA GPU Acceleration")).toBeInTheDocument();
  });

  it("renders the 404 NotFoundPage on unknown route '/nonexistent'", async () => {
    renderWithRouter("/nonexistent");
    expect(await screen.findByText("404")).toBeInTheDocument();
    expect(screen.getByText("Route Not Found")).toBeInTheDocument();
  });
});
