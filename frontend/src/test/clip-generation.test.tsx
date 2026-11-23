import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { ToastProvider } from "../components/ui/toast";
import { GenerateClipModal } from "../features/clips/components/GenerateClipModal";
import { HighlightCard } from "../features/highlights/components/HighlightCard";
import { StudioPage } from "../features/clips/StudioPage";
import { api, ClipslyApiError } from "../services/api";
import { Clip, Highlight } from "../types/api";

const mockAcceptedHighlight: Highlight = {
  id: "hl-accepted-1",
  video_id: "vid-101",
  transcript_id: "tr-202",
  start_ms: 10000,
  end_ms: 28000,
  duration_ms: 18000,
  hook_sentence: "The secret to 10x productivity",
  summary: "Discussion about high-leverage habits.",
  hook_score: 92.0,
  composite_score: 88.5,
  rank: 1,
  category: "Strategy",
  status: "ACCEPTED",
};

const mockCandidateHighlight: Highlight = {
  ...mockAcceptedHighlight,
  id: "hl-candidate-2",
  status: "CANDIDATE",
};

const mockCompletedClip: Clip = {
  id: "clip-completed-1",
  video_id: "vid-101",
  video_filename: "source_video.mp4",
  title: "10x Productivity Clip",
  start_ms: 10000,
  end_ms: 28000,
  duration_ms: 18000,
  aspect_ratio_mode: "BLUR_PAD",
  conversion_mode: "BLUR_PAD",
  status: "COMPLETED",
  output_path: "storage/clips/clip-completed-1.mp4",
  output_filename: "10x_Productivity_clip_completed-1.mp4",
  width: 1080,
  height: 1920,
  fps: 30.0,
  video_codec: "h264",
  audio_codec: "aac",
  file_size_bytes: 4194304, // 4 MB
  encoding_backend: "h264_nvenc",
  subtitle_enabled: true,
  subtitle_style_preset: "KARAOKE_AMBER",
  created_at: "2026-11-23T20:00:00Z",
};

const renderWithProviders = (ui: React.ReactElement) => {
  return render(
    <MemoryRouter>
      <ToastProvider>{ui}</ToastProvider>
    </MemoryRouter>
  );
};

describe("Phase 17: GenerateClipModal Component", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("1. renders modal with pre-filled highlight timestamps and calculates duration", () => {
    renderWithProviders(
      <GenerateClipModal
        isOpen={true}
        onClose={vi.fn()}
        videoId="vid-101"
        highlightId="hl-accepted-1"
        initialTitle="My Highlight Clip"
        initialStartMs={10000}
        initialEndMs={28000}
        videoTitle="source_video.mp4"
        videoDurationSeconds={120.0}
      />
    );

    expect(screen.getByText("Generate 9:16 Vertical Clip")).toBeInTheDocument();
    expect(screen.getByDisplayValue("My Highlight Clip")).toBeInTheDocument();
    expect(screen.getByDisplayValue("10")).toBeInTheDocument(); // start seconds
    expect(screen.getByDisplayValue("28")).toBeInTheDocument(); // end seconds
    expect(screen.getByText(/18\.0s \(18000 ms\)/)).toBeInTheDocument();
  });

  it("2. allows selecting vertical conversion modes: BLUR_PAD, CROP_CENTER, and FIT_LETTERBOX", () => {
    renderWithProviders(
      <GenerateClipModal
        isOpen={true}
        onClose={vi.fn()}
        videoId="vid-101"
        initialStartMs={0}
        initialEndMs={15000}
      />
    );

    const blurPadRadio = screen.getByLabelText(/Blurred Background/);
    const cropCenterRadio = screen.getByLabelText(/Center Crop/);
    const fitLetterboxRadio = screen.getByLabelText(/Fit Letterbox/);

    expect(blurPadRadio).toBeChecked();
    expect(cropCenterRadio).not.toBeChecked();

    fireEvent.click(cropCenterRadio);
    expect(cropCenterRadio).toBeChecked();

    fireEvent.click(fitLetterboxRadio);
    expect(fitLetterboxRadio).toBeChecked();
  });

  it("3. validates minimum duration (rejects < 5000 ms) and displays clear validation error", () => {
    renderWithProviders(
      <GenerateClipModal
        isOpen={true}
        onClose={vi.fn()}
        videoId="vid-101"
        initialStartMs={5000}
        initialEndMs={8000} // only 3000ms duration
      />
    );

    expect(
      screen.getByText("Clip duration must be at least 5.0 seconds (5000 ms).")
    ).toBeInTheDocument();

    const submitBtn = screen.getByRole("button", { name: /Generate 9:16 Clip/ });
    expect(submitBtn).toBeDisabled();
  });

  it("4. validates invalid timestamps when end timestamp <= start timestamp", () => {
    renderWithProviders(
      <GenerateClipModal
        isOpen={true}
        onClose={vi.fn()}
        videoId="vid-101"
        initialStartMs={20000}
        initialEndMs={10000}
      />
    );

    expect(
      screen.getByText("End timestamp must be strictly greater than start timestamp.")
    ).toBeInTheDocument();

    const submitBtn = screen.getByRole("button", { name: /Generate 9:16 Clip/ });
    expect(submitBtn).toBeDisabled();
  });

  it("5. successfully submits generation request to real API endpoint", async () => {
    const generateSpy = vi.spyOn(api.clips, "generate").mockResolvedValue({
      job_id: "job-clip-999",
      clip_id: "clip-new-123",
      video_id: "vid-101",
      status: "QUEUED",
      message: "Clip generation job successfully enqueued.",
      clip: mockCompletedClip,
    });

    vi.spyOn(api.jobs, "get").mockResolvedValue({
      id: "job-clip-999",
      video_id: "vid-101",
      job_type: "CLIP_GENERATION",
      status: "PROCESSING",
      progress_percent: 35.0,
      current_step: "Encoding 9:16 clip (h264_nvenc)...",
      created_at: new Date().toISOString(),
    });

    renderWithProviders(
      <GenerateClipModal
        isOpen={true}
        onClose={vi.fn()}
        videoId="vid-101"
        initialTitle="Validated Fast Clip"
        initialStartMs={0}
        initialEndMs={10000}
      />
    );

    const submitBtn = screen.getByRole("button", { name: /Generate 9:16 Clip/ });
    expect(submitBtn).not.toBeDisabled();

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(generateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          video_id: "vid-101",
          title: "Validated Fast Clip",
          start_ms: 0,
          end_ms: 10000,
          conversion_mode: "BLUR_PAD",
          target_width: 1080,
          target_height: 1920,
          target_fps: 30.0,
          force_cpu: false,
        })
      );
    });

    // Should render active job view
    await waitFor(() => {
      expect(screen.getByText(/Job Status:/)).toBeInTheDocument();
    });
  });

  it("6. displays backend error cleanly when generation request fails", async () => {
    vi.spyOn(api.clips, "generate").mockRejectedValue(
      new ClipslyApiError(409, "A processing job is already active for this video.")
    );

    renderWithProviders(
      <GenerateClipModal
        isOpen={true}
        onClose={vi.fn()}
        videoId="vid-101"
        initialStartMs={0}
        initialEndMs={10000}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Generate 9:16 Clip/ }));

    await waitFor(() => {
      expect(
        screen.getByText("A processing job is already active for this video.")
      ).toBeInTheDocument();
    });
  });

  it("7. renders real backend progress percentage and allows cancellation", async () => {
    vi.spyOn(api.clips, "generate").mockResolvedValue({
      job_id: "job-clip-cancel-1",
      clip_id: "clip-cancelling-1",
      video_id: "vid-101",
      status: "QUEUED",
      message: "Enqueued",
      clip: mockCompletedClip,
    });

    vi.spyOn(api.jobs, "get").mockResolvedValue({
      id: "job-clip-cancel-1",
      video_id: "vid-101",
      job_type: "CLIP_GENERATION",
      status: "PROCESSING",
      progress_percent: 62.0,
      current_step: "Encoding frames 62%...",
      created_at: new Date().toISOString(),
    });

    const cancelSpy = vi.spyOn(api.clips, "cancel").mockResolvedValue({
      success: true,
      id: "clip-cancelling-1",
      status: "CANCELLED",
    });

    renderWithProviders(
      <GenerateClipModal
        isOpen={true}
        onClose={vi.fn()}
        videoId="vid-101"
        initialStartMs={0}
        initialEndMs={10000}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Generate 9:16 Clip/ }));

    await waitFor(() => {
      expect(screen.getByText("62%")).toBeInTheDocument();
      expect(screen.getByText("Encoding frames 62%...")).toBeInTheDocument();
    });

    const cancelBtn = screen.getByRole("button", { name: /Cancel Generation/ });
    fireEvent.click(cancelBtn);

    await waitFor(() => {
      expect(cancelSpy).toHaveBeenCalledWith("clip-cancelling-1");
    });
  });
});

describe("Phase 17: HighlightCard Accepted Workflow", () => {
  it("8. renders 'Create 9:16 Clip' button only when highlight is ACCEPTED", () => {
    const createClipSpy = vi.fn();

    const { rerender } = render(
      <HighlightCard
        highlight={mockAcceptedHighlight}
        onCreateClip={createClipSpy}
      />
    );

    const createClipBtn = screen.getByRole("button", { name: /Create 9:16 Clip/ });
    expect(createClipBtn).toBeInTheDocument();

    fireEvent.click(createClipBtn);
    expect(createClipSpy).toHaveBeenCalledWith(mockAcceptedHighlight);

    // Re-render with candidate highlight
    rerender(
      <HighlightCard
        highlight={mockCandidateHighlight}
        onCreateClip={createClipSpy}
      />
    );

    expect(screen.queryByRole("button", { name: /Create 9:16 Clip/ })).not.toBeInTheDocument();
  });
});

describe("Phase 17: StudioPage Interactive Preview & Metadata", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("9. loads completed clip, renders 9:16 video player with streaming URL, and displays verified metadata", async () => {
    vi.spyOn(api.clips, "get").mockResolvedValue(mockCompletedClip);

    render(
      <MemoryRouter initialEntries={["/studio/clip-completed-1"]}>
        <ToastProvider>
          <Routes>
            <Route path="/studio/:clipId" element={<StudioPage />} />
          </Routes>
        </ToastProvider>
      </MemoryRouter>
    );

    // Wait for clip to load
    await waitFor(() => {
      expect(screen.getByText(/Studio: 10x Productivity Clip/)).toBeInTheDocument();
    });

    // Check 9:16 HTML5 video player and stream URL
    const videoElem = screen.getByTestId("clip-video-player") as HTMLVideoElement;
    expect(videoElem).toBeInTheDocument();
    const sourceElem = videoElem.querySelector("source");
    expect(sourceElem?.getAttribute("src")).toBe("/api/v1/clips/clip-completed-1/stream");

    // Verify metadata values
    expect(screen.getByText("1080 × 1920")).toBeInTheDocument();
    expect(screen.getByText("9:16 Vertical")).toBeInTheDocument();
    expect(screen.getByText("30 FPS")).toBeInTheDocument();
    expect(screen.getByText(/^h264$/i)).toBeInTheDocument();
    expect(screen.getByText(/^aac$/i)).toBeInTheDocument();
    expect(screen.getByText("4.0 MB")).toBeInTheDocument();
    expect(screen.getByText("h264_nvenc")).toBeInTheDocument();
    expect(screen.getByText(/18\.0s \(18000 ms\)/)).toBeInTheDocument();

    // Verify download MP4 action link
    const downloadLink = screen.getAllByRole("link", { name: /Download MP4/ })[0];
    expect(downloadLink.getAttribute("href")).toBe("/api/v1/clips/clip-completed-1/download");
  });

  it("10. displays playback error notice honestly when video stream fails to decode", async () => {
    vi.spyOn(api.clips, "get").mockResolvedValue(mockCompletedClip);

    render(
      <MemoryRouter initialEntries={["/studio/clip-completed-1"]}>
        <ToastProvider>
          <Routes>
            <Route path="/studio/:clipId" element={<StudioPage />} />
          </Routes>
        </ToastProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId("clip-video-player")).toBeInTheDocument();
    });

    const videoElem = screen.getByTestId("clip-video-player");
    fireEvent.error(videoElem);

    await waitFor(() => {
      expect(screen.getByText("Playback Error")).toBeInTheDocument();
      expect(screen.getByText("Failed to decode vertical video stream.")).toBeInTheDocument();
    });
  });

  it("11. confirms Phase 18 subtitle roadmap notice is preserved", async () => {
    vi.spyOn(api.clips, "get").mockResolvedValue(mockCompletedClip);

    render(
      <MemoryRouter initialEntries={["/studio/clip-completed-1"]}>
        <ToastProvider>
          <Routes>
            <Route path="/studio/:clipId" element={<StudioPage />} />
          </Routes>
        </ToastProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Subtitle & Caption Engine/)).toBeInTheDocument();
      expect(
        screen.getByText(/ASS subtitle compilation, font styling presets, and word-level karaoke animations activate in Phase 18\./)
      ).toBeInTheDocument();
    });
  });
});
