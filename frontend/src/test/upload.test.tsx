import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../components/ui/toast";
import { UploadPage } from "../features/videos/UploadPage";
import { api, ClipslyApiError } from "../services/api";
import { Video } from "../types/api";

const mockVideoResponse: Video = {
  id: "vid-test-123",
  filename: "vid-test-123.mp4",
  original_filename: "My_Tech_Talk.mp4",
  file_size_bytes: 45000000,
  duration_seconds: 620.5,
  width: 1920,
  height: 1080,
  aspect_ratio: "16:9",
  fps: 30.0,
  video_codec: "h264",
  audio_codec: "aac",
  audio_sample_rate: 48000,
  audio_channels: 2,
  status: "READY",
  created_at: "2026-11-22T19:40:00Z",
};

describe("Phase 12: Local Video Upload & Ingestion Pipeline", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const renderUploadPage = () => {
    return render(
      <MemoryRouter>
        <ToastProvider>
          <UploadPage />
        </ToastProvider>
      </MemoryRouter>
    );
  };

  it("renders idle upload dropzone with container specifications and browse button", () => {
    renderUploadPage();

    expect(screen.getByRole("heading", { name: "Upload Video" })).toBeInTheDocument();
    expect(screen.getByText(/Drop your local video file here, or click to browse/i)).toBeInTheDocument();
    expect(screen.getByText("Max: 10 GB")).toBeInTheDocument();
    expect(screen.getByText("Duration: 5 - 120 Min")).toBeInTheDocument();
    expect(screen.getByText("FFprobe Verified")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Browse Files/i })).toBeInTheDocument();
  });

  it("handles valid file selection and displays file details", () => {
    renderUploadPage();

    const file = new File(["dummy video data content"], "podcast_episode.mp4", { type: "video/mp4" });
    const fileInput = screen.getByTestId("video-file-input") as HTMLInputElement;

    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("podcast_episode.mp4")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Start Upload/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Change File/i })).toBeInTheDocument();
  });

  it("rejects unsupported file extension client-side", () => {
    renderUploadPage();

    const invalidFile = new File(["some text"], "document.pdf", { type: "application/pdf" });
    const fileInput = screen.getByTestId("video-file-input") as HTMLInputElement;

    fireEvent.change(fileInput, { target: { files: [invalidFile] } });

    expect(screen.getAllByText(/Unsupported format '\.pdf'/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Upload or Validation Failed")).toBeInTheDocument();
  });

  it("rejects empty file client-side", () => {
    renderUploadPage();

    const emptyFile = new File([], "empty.mp4", { type: "video/mp4" });
    const fileInput = screen.getByTestId("video-file-input") as HTMLInputElement;

    fireEvent.change(fileInput, { target: { files: [emptyFile] } });

    expect(screen.getAllByText(/The selected video file is empty \(0 bytes\)/i).length).toBeGreaterThanOrEqual(1);
  });

  it("rejects oversized files exceeding 10 GB client-side", () => {
    renderUploadPage();

    // Mock file with size > 10GB
    const largeFile = new File(["dummy"], "massive_stream.mp4", { type: "video/mp4" });
    Object.defineProperty(largeFile, "size", { value: 11 * 1024 * 1024 * 1024 });

    const fileInput = screen.getByTestId("video-file-input") as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [largeFile] } });

    expect(screen.getAllByText(/exceeds the maximum allowed upload limit of 10 GB/i).length).toBeGreaterThanOrEqual(1);
  });

  it("executes upload and displays progress and finalizing states", async () => {
    vi.spyOn(api.videos, "upload").mockImplementation(async (_file, options) => {
      // Simulate progress callback
      if (options?.onProgress) {
        options.onProgress({
          loaded: 50000000,
          total: 100000000,
          percentage: 50,
          speedBytesPerSec: 15000000,
          remainingSeconds: 3,
        });
      }
      return mockVideoResponse;
    });

    renderUploadPage();

    const file = new File(["dummy video"], "My_Tech_Talk.mp4", { type: "video/mp4" });
    const fileInput = screen.getByTestId("video-file-input");
    fireEvent.change(fileInput, { target: { files: [file] } });

    const startBtn = screen.getByRole("button", { name: /Start Upload/i });
    fireEvent.click(startBtn);

    // Verify upload was invoked
    await waitFor(() => {
      expect(api.videos.upload).toHaveBeenCalledWith(file, expect.anything());
    });

    // Check completion state
    expect(await screen.findByText("Upload & Validation Complete")).toBeInTheDocument();
    expect(screen.getByText("1920x1080 (16:9)")).toBeInTheDocument();
    expect(screen.getByText("h264 / aac")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Inspect Video Details/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /View in Video Library/i })).toBeInTheDocument();
  });

  it("handles backend validation error during upload", async () => {
    vi.spyOn(api.videos, "upload").mockRejectedValue(
      new ClipslyApiError(400, "FFprobe failed to inspect container: No audio stream detected.", "INVALID_FILE_FORMAT")
    );

    renderUploadPage();

    const file = new File(["dummy video"], "silent_video.mp4", { type: "video/mp4" });
    const fileInput = screen.getByTestId("video-file-input");
    fireEvent.change(fileInput, { target: { files: [file] } });

    const startBtn = screen.getByRole("button", { name: /Start Upload/i });
    fireEvent.click(startBtn);

    expect(await screen.findByText("Upload or Validation Failed")).toBeInTheDocument();
    expect(screen.getAllByText(/No audio stream detected/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("button", { name: /Retry Upload/i })).toBeInTheDocument();
  });

  it("handles upload cancellation cleanly", async () => {
    vi.spyOn(api.videos, "upload").mockImplementation(async (_file, options) => {
      return new Promise((_, reject) => {
        if (options?.signal) {
          options.signal.addEventListener("abort", () => {
            reject(new ClipslyApiError(499, "Upload cancelled by client", "CLIENT_CANCELLED"));
          });
        }
      });
    });

    renderUploadPage();

    const file = new File(["dummy video"], "cancel_me.mp4", { type: "video/mp4" });
    const fileInput = screen.getByTestId("video-file-input");
    fireEvent.change(fileInput, { target: { files: [file] } });

    const startBtn = screen.getByRole("button", { name: /Start Upload/i });
    fireEvent.click(startBtn);

    const cancelBtn = await screen.findByRole("button", { name: /Cancel Upload/i });
    fireEvent.click(cancelBtn);

    expect((await screen.findAllByText("Upload Cancelled")).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/All partial temporary data was cleanly discarded/i)).toBeInTheDocument();
  });

  it("supports keyboard accessible file selection via Enter key", () => {
    renderUploadPage();

    const dropzone = screen.getByRole("button", { name: /Upload video file dropzone/i });
    const fileInput = screen.getByTestId("video-file-input");
    const clickSpy = vi.spyOn(fileInput, "click");

    fireEvent.keyDown(dropzone, { key: "Enter", code: "Enter" });
    expect(clickSpy).toHaveBeenCalled();
  });
});
