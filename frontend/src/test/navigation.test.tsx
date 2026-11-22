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
    global.fetch = vi.fn().mockResolvedValue({
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
