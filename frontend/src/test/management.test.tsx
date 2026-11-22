import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ToastProvider } from "../components/ui/toast";
import { VideoLibraryPage } from "../features/videos/VideoLibraryPage";
import { VideoDetailPage } from "../features/videos/VideoDetailPage";
import { JobsPage } from "../features/jobs/JobsPage";
import { ClipsLibraryPage } from "../features/clips/ClipsLibraryPage";
import { ExportsPage } from "../features/exports/ExportsPage";
import { Video, ProcessingJob, Clip, ExportJob } from "../types/api";

const mockVideos: Video[] = [
  {
    id: "vid-1",
    filename: "podcast_ep12.mp4",
    original_filename: "Tech Podcast Episode 12.mp4",
    storage_label: "Local SSD Storage",
    file_path: "data/uploads/vid-1.mp4",
    file_size_bytes: 104857600, // 100 MB
    duration_seconds: 1800.0,
    width: 1920,
    height: 1080,
    aspect_ratio: "16:9",
    fps: 30.0,
    video_codec: "h264",
    audio_codec: "aac",
    audio_sample_rate: 48000,
    audio_channels: 2,
    status: "READY",
    file_exists: true,
    processing_jobs_count: 2,
    clips_count: 3,
    transcripts_count: 1,
    highlights_count: 5,
    created_at: "2026-11-22T10:00:00Z",
  },
  {
    id: "vid-2",
    filename: "interview_dan.mp4",
    original_filename: "Interview with Dan.mp4",
    file_path: "data/uploads/vid-2.mp4",
    file_size_bytes: 52428800, // 50 MB
    duration_seconds: 600.0,
    width: 1920,
    height: 1080,
    aspect_ratio: "16:9",
    fps: 60.0,
    video_codec: "h264",
    audio_codec: "aac",
    audio_sample_rate: 48000,
    audio_channels: 2,
    status: "PROCESSING",
    file_exists: true,
    processing_jobs_count: 1,
    clips_count: 0,
    transcripts_count: 0,
    highlights_count: 0,
    created_at: "2026-11-22T11:00:00Z",
  },
];

const mockJobs: ProcessingJob[] = [
  {
    id: "job-1",
    video_id: "vid-2",
    job_type: "WHISPER_TRANSCRIPTION",
    status: "PROCESSING",
    progress_percent: 55.0,
    current_step: "Transcribing audio segment 3/6",
    error_message: null,
    process_pid: 14208,
    created_at: "2026-11-22T11:05:00Z",
  },
  {
    id: "job-2",
    video_id: "vid-1",
    job_type: "INGESTION",
    status: "COMPLETED",
    progress_percent: 100.0,
    current_step: "Metadata probe complete",
    error_message: null,
    process_pid: null,
    created_at: "2026-11-22T10:01:00Z",
  },
];

const mockClips: Clip[] = [
  {
    id: "clip-1",
    video_id: "vid-1",
    video_filename: "Tech Podcast Episode 12.mp4",
    title: "The Future of AI Hardware",
    start_ms: 12000,
    end_ms: 45000,
    duration_ms: 33000,
    aspect_ratio_mode: "BLUR_PAD",
    subtitle_enabled: true,
    subtitle_style_preset: "KARAOKE_AMBER",
    status: "DRAFT",
    created_at: "2026-11-22T10:30:00Z",
  },
];

const mockExports: ExportJob[] = [
  {
    id: "exp-1",
    clip_id: "clip-1",
    clip_title: "The Future of AI Hardware",
    video_id: "vid-1",
    output_filename: "Future_of_AI_Hardware_9x16.mp4",
    output_path: "data/exports/exp-1.mp4",
    resolution: "1080x1920",
    fps: 30.0,
    encoder: "h264_nvenc",
    render_time_seconds: 6.8,
    file_size_bytes: 18500000,
    status: "COMPLETED",
    progress_percent: 100.0,
    file_exists: true,
    created_at: "2026-11-22T10:45:00Z",
  },
];

describe("Phase 11: Project Management System", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("Video Library (/videos)", () => {
    it("renders video cards with metadata, status badges, and pagination", async () => {
      global.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes("/api/v1/videos")) {
          return {
            ok: true,
            json: async () => ({
              items: mockVideos,
              total: 2,
              limit: 12,
              offset: 0,
            }),
          };
        }
        return { ok: true, json: async () => ({}) };
      });

      render(
        <MemoryRouter>
          <ToastProvider>
            <VideoLibraryPage />
          </ToastProvider>
        </MemoryRouter>
      );

      // Title & Header
      expect(await screen.findByRole("heading", { name: "Video Library" })).toBeInTheDocument();

      // Videos rendered
      expect(screen.getByText("Tech Podcast Episode 12.mp4")).toBeInTheDocument();
      expect(screen.getByText("Interview with Dan.mp4")).toBeInTheDocument();

      // Badges
      expect(screen.getAllByText("Ready").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Processing").length).toBeGreaterThanOrEqual(1);

      // Pagination indicator
      expect(screen.getByText(/Showing/i)).toBeInTheDocument();
    });

    it("opens delete confirmation dialog and triggers delete API", async () => {
      let deleteCalled = false;
      global.fetch = vi.fn().mockImplementation(async (url: string, opts?: RequestInit) => {
        if (opts?.method === "DELETE" && url.includes("/api/v1/videos/vid-1")) {
          deleteCalled = true;
          return {
            ok: true,
            json: async () => ({ success: true, id: "vid-1", file_unlinked: false }),
          };
        }
        if (url.includes("/api/v1/videos")) {
          return {
            ok: true,
            json: async () => ({
              items: mockVideos,
              total: 2,
              limit: 12,
              offset: 0,
            }),
          };
        }
        return { ok: true, json: async () => ({}) };
      });

      render(
        <MemoryRouter>
          <ToastProvider>
            <VideoLibraryPage />
          </ToastProvider>
        </MemoryRouter>
      );

      expect(await screen.findByText("Tech Podcast Episode 12.mp4")).toBeInTheDocument();

      // Click delete button for vid-1
      const deleteButtons = screen.getAllByLabelText(/Delete video/i);
      fireEvent.click(deleteButtons[0]);

      // Dialog opens
      expect(screen.getByText("Delete Source Video")).toBeInTheDocument();
      expect(screen.getByText(/Deletion Impact:/i)).toBeInTheDocument();

      // Confirm deletion
      const confirmButton = screen.getByRole("button", { name: /Permanently Delete/i });
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(deleteCalled).toBe(true);
      });
    });

    it("renders empty library state when no videos exist", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          items: [],
          total: 0,
          limit: 12,
          offset: 0,
        }),
      });

      render(
        <MemoryRouter>
          <ToastProvider>
            <VideoLibraryPage />
          </ToastProvider>
        </MemoryRouter>
      );

      expect(await screen.findByText("No Videos Ingested")).toBeInTheDocument();
      expect(screen.getByText("Import Local Video")).toBeInTheDocument();
    });
  });

  describe("Video Details (/video/:id)", () => {
    it("renders full stream metadata and tabbed navigation", async () => {
      global.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes("/api/v1/videos/vid-1")) {
          return { ok: true, json: async () => mockVideos[0] };
        }
        if (url.includes("/api/v1/jobs")) {
          return {
            ok: true,
            json: async () => ({ items: [mockJobs[1]], total: 1, limit: 20, offset: 0 }),
          };
        }
        if (url.includes("/api/v1/transcripts")) {
          return {
            ok: true,
            json: async () => ({
              id: "tr-1",
              video_id: "vid-1",
              model_name: "base",
              language: "en",
              word_count: 450,
              full_text: "Welcome to Episode 12 of the Tech Podcast...",
            }),
          };
        }
        if (url.includes("/api/v1/highlights")) {
          return { ok: true, json: async () => [] };
        }
        if (url.includes("/api/v1/clips")) {
          return { ok: true, json: async () => ({ items: mockClips, total: 1, limit: 20, offset: 0 }) };
        }
        return { ok: true, json: async () => ({}) };
      });

      render(
        <MemoryRouter initialEntries={["/video/vid-1"]}>
          <ToastProvider>
            <Routes>
              <Route path="/video/:id" element={<VideoDetailPage />} />
            </Routes>
          </ToastProvider>
        </MemoryRouter>
      );

      expect(await screen.findByText("Tech Podcast Episode 12.mp4")).toBeInTheDocument();
      expect(screen.getByText("Stream Characteristics (FFprobe Verified)")).toBeInTheDocument();
      expect(screen.getAllByText("1920x1080").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("h264")).toBeInTheDocument();
      expect(screen.getByText("aac")).toBeInTheDocument();
      expect(screen.getByText("File Verified on SSD")).toBeInTheDocument();

      // Click Transcript tab
      const transcriptTab = screen.getByRole("button", { name: /Transcript/i });
      fireEvent.click(transcriptTab);
      expect(await screen.findByText("Generated Transcript")).toBeInTheDocument();
      expect(screen.getByText(/Welcome to Episode 12/i)).toBeInTheDocument();

      // Click Processing Jobs tab
      const jobsTab = screen.getByRole("button", { name: /Processing Jobs/i });
      fireEvent.click(jobsTab);
      expect(await screen.findByText("Metadata probe complete")).toBeInTheDocument();

      // Click Clips tab
      const clipsTab = screen.getByRole("button", { name: /Clips/i });
      fireEvent.click(clipsTab);
      expect(await screen.findByText("The Future of AI Hardware")).toBeInTheDocument();
    });
  });

  describe("Processing Jobs (/jobs)", () => {
    it("lists active and completed background tasks and allows cancellation", async () => {
      let cancelCalled = false;
      global.fetch = vi.fn().mockImplementation(async (url: string, opts?: RequestInit) => {
        if (opts?.method === "POST" && url.includes("/api/v1/jobs/job-1/cancel")) {
          cancelCalled = true;
          return {
            ok: true,
            json: async () => ({ id: "job-1", status: "CANCELLED", current_step: "Cancelled by user" }),
          };
        }
        if (url.includes("/api/v1/jobs")) {
          return {
            ok: true,
            json: async () => ({
              items: mockJobs,
              total: 2,
              limit: 15,
              offset: 0,
            }),
          };
        }
        return { ok: true, json: async () => ({}) };
      });

      render(
        <MemoryRouter>
          <ToastProvider>
            <JobsPage />
          </ToastProvider>
        </MemoryRouter>
      );

      expect(await screen.findByRole("heading", { name: "Processing Jobs" })).toBeInTheDocument();
      expect(screen.getByText("Transcribing audio segment 3/6")).toBeInTheDocument();

      // Click Cancel on the active job
      const cancelBtn = screen.getByRole("button", { name: /Cancel/i });
      fireEvent.click(cancelBtn);

      // Confirmation modal
      expect(screen.getByText("Cancel Processing Task")).toBeInTheDocument();

      const confirmCancelBtn = screen.getByRole("button", { name: /Cancel Task/i });
      fireEvent.click(confirmCancelBtn);

      await waitFor(() => {
        expect(cancelCalled).toBe(true);
      });
    });
  });

  describe("Clips Library (/clips)", () => {
    it("renders clips list and allows deletion", async () => {
      let deleteClipCalled = false;
      global.fetch = vi.fn().mockImplementation(async (url: string, opts?: RequestInit) => {
        if (opts?.method === "DELETE" && url.includes("/api/v1/clips/clip-1")) {
          deleteClipCalled = true;
          return { ok: true, json: async () => ({ success: true, id: "clip-1" }) };
        }
        if (url.includes("/api/v1/clips")) {
          return {
            ok: true,
            json: async () => ({
              items: mockClips,
              total: 1,
              limit: 12,
              offset: 0,
            }),
          };
        }
        return { ok: true, json: async () => ({}) };
      });

      render(
        <MemoryRouter>
          <ToastProvider>
            <ClipsLibraryPage />
          </ToastProvider>
        </MemoryRouter>
      );

      expect(await screen.findByText("The Future of AI Hardware")).toBeInTheDocument();
      expect(screen.getByText("BLUR_PAD")).toBeInTheDocument();

      const deleteBtn = screen.getByLabelText(/Delete clip The Future of AI Hardware/i);
      fireEvent.click(deleteBtn);

      expect(screen.getByText("Delete Clip Configuration")).toBeInTheDocument();
      const confirmDelete = screen.getByRole("button", { name: /Permanently Delete/i });
      fireEvent.click(confirmDelete);

      await waitFor(() => {
        expect(deleteClipCalled).toBe(true);
      });
    });
  });

  describe("Exports Queue (/exports)", () => {
    it("renders export jobs and handles record deletion", async () => {
      let deleteExportCalled = false;
      global.fetch = vi.fn().mockImplementation(async (url: string, opts?: RequestInit) => {
        if (opts?.method === "DELETE" && url.includes("/api/v1/exports/exp-1")) {
          deleteExportCalled = true;
          return { ok: true, json: async () => ({ success: true, id: "exp-1" }) };
        }
        if (url.includes("/api/v1/exports")) {
          return {
            ok: true,
            json: async () => ({
              items: mockExports,
              total: 1,
              limit: 12,
              offset: 0,
            }),
          };
        }
        return { ok: true, json: async () => ({}) };
      });

      render(
        <MemoryRouter>
          <ToastProvider>
            <ExportsPage />
          </ToastProvider>
        </MemoryRouter>
      );

      expect(await screen.findByText("Future_of_AI_Hardware_9x16.mp4")).toBeInTheDocument();
      expect(screen.getByText("MP4 Saved on SSD")).toBeInTheDocument();
      expect(screen.getByText("h264_nvenc")).toBeInTheDocument();

      const deleteBtn = screen.getByLabelText(/Delete export record Future_of_AI_Hardware_9x16.mp4/i);
      fireEvent.click(deleteBtn);

      expect(screen.getByText("Delete Export Record")).toBeInTheDocument();
      const confirmDelete = screen.getByRole("button", { name: /Permanently Delete/i });
      fireEvent.click(confirmDelete);

      await waitFor(() => {
        expect(deleteExportCalled).toBe(true);
      });
    });
  });
});
