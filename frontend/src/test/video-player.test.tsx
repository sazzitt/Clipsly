import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { VideoPlayer } from "../features/videos/components/VideoPlayer";
import { VideoDetailPage } from "../features/videos/VideoDetailPage";
import { VideoLibraryPage } from "../features/videos/VideoLibraryPage";
import { ToastProvider } from "../components/ui/toast";
import { Video } from "../types/api";

const mockVideoWithAudio: Video = {
  id: "vid-preview-1",
  filename: "sample_stream.mp4",
  original_filename: "Sample Stream With Audio.mp4",
  file_path: "storage/uploads/sample_stream.mp4",
  file_size_bytes: 15728640, // 15 MB
  duration_seconds: 125.5,
  width: 1920,
  height: 1080,
  aspect_ratio: "16:9",
  fps: 60.0,
  video_codec: "h264",
  video_codec_profile: "High",
  pixel_format: "yuv420p",
  bit_depth: 8,
  video_bitrate: 4500000,
  rotation: 0,
  orientation: "landscape",
  has_audio: true,
  audio_codec: "aac",
  audio_sample_rate: 48000,
  audio_channels: 2,
  channel_layout: "stereo",
  audio_bitrate: 192000,
  container_format: "mp4",
  bitrate: 4692000,
  status: "READY",
  metadata_status: "COMPLETED",
  metadata_extracted_at: "2026-11-23T12:00:00Z",
  file_exists: true,
  storage_label: "Local SSD Storage",
  processing_jobs_count: 1,
  clips_count: 2,
  transcripts_count: 1,
  highlights_count: 3,
  created_at: "2026-11-23T10:00:00Z",
};

const mockVideoNoAudio: Video = {
  ...mockVideoWithAudio,
  id: "vid-preview-noaudio",
  filename: "silent_video.mp4",
  original_filename: "Silent Video Without Audio.mp4",
  has_audio: false,
  audio_codec: null,
  audio_sample_rate: null,
  audio_channels: null,
  channel_layout: null,
  audio_bitrate: null,
};

describe("Phase 13: VideoPlayer Component", () => {
  it("renders the video element with the correct stream URL and controls bar", () => {
    render(<VideoPlayer videoId="test-vid-123" title="Test Video" />);

    const container = screen.getByTestId("video-player-container");
    expect(container).toBeInTheDocument();

    const videoEl = screen.getByTestId("html5-video-element") as HTMLVideoElement;
    expect(videoEl).toBeInTheDocument();
    expect(videoEl.src).toContain("/api/v1/videos/test-vid-123/stream");

    // Controls bar elements
    expect(screen.getByTestId("play-pause-button")).toBeInTheDocument();
    expect(screen.getByTestId("seek-slider")).toBeInTheDocument();
    expect(screen.getByTestId("skip-back-button")).toBeInTheDocument();
    expect(screen.getByTestId("skip-forward-button")).toBeInTheDocument();
    expect(screen.getByTestId("mute-button")).toBeInTheDocument();
    expect(screen.getByTestId("volume-slider")).toBeInTheDocument();
    expect(screen.getByTestId("speed-selector-button")).toBeInTheDocument();
    expect(screen.getByTestId("fullscreen-button")).toBeInTheDocument();
    expect(screen.getByTestId("time-display")).toBeInTheDocument();
  });

  it("toggles play/pause when play button and video element are clicked", async () => {
    const playMock = vi.spyOn(window.HTMLMediaElement.prototype, "play").mockImplementation(async () => {});
    const pauseMock = vi.spyOn(window.HTMLMediaElement.prototype, "pause").mockImplementation(() => {});

    render(<VideoPlayer videoId="test-vid-123" />);

    const playBtn = screen.getByTestId("play-pause-button");
    fireEvent.click(playBtn);
    expect(playMock).toHaveBeenCalled();

    playMock.mockRestore();
    pauseMock.mockRestore();
  });

  it("handles seek bar scrubber changes", () => {
    render(<VideoPlayer videoId="test-vid-123" />);

    const seekSlider = screen.getByTestId("seek-slider") as HTMLInputElement;
    fireEvent.change(seekSlider, { target: { value: "45" } });

    expect(seekSlider.value).toBe("45");
  });

  it("adjusts volume and toggles mute", () => {
    render(<VideoPlayer videoId="test-vid-123" />);

    const muteBtn = screen.getByTestId("mute-button");
    const volumeSlider = screen.getByTestId("volume-slider") as HTMLInputElement;

    expect(volumeSlider.value).toBe("1");

    // Click mute
    fireEvent.click(muteBtn);
    expect(volumeSlider.value).toBe("0");

    // Change volume
    fireEvent.change(volumeSlider, { target: { value: "0.7" } });
    expect(volumeSlider.value).toBe("0.7");
  });

  it("opens speed selector menu and changes playback rate", () => {
    render(<VideoPlayer videoId="test-vid-123" />);

    const speedBtn = screen.getByTestId("speed-selector-button");
    expect(speedBtn).toHaveTextContent("1x");

    fireEvent.click(speedBtn);
    expect(screen.getByTestId("speed-dropdown-menu")).toBeInTheDocument();

    const speedOption2 = screen.getByTestId("speed-option-2");
    fireEvent.click(speedOption2);

    expect(speedBtn).toHaveTextContent("2x");
  });

  it("renders stream error overlay and handles retry", () => {
    render(<VideoPlayer videoId="test-vid-123" />);

    const videoEl = screen.getByTestId("html5-video-element");
    // Simulate error event on HTML5 video element
    fireEvent.error(videoEl);

    expect(screen.getByTestId("video-stream-error")).toBeInTheDocument();
    expect(screen.getByText(/Failed to stream video/i)).toBeInTheDocument();

    const retryBtn = screen.getByTestId("video-retry-button");
    fireEvent.click(retryBtn);

    expect(screen.queryByTestId("video-stream-error")).not.toBeInTheDocument();
  });

  it("handles keyboard navigation shortcuts on container", () => {
    const playMock = vi.spyOn(window.HTMLMediaElement.prototype, "play").mockImplementation(async () => {});
    const pauseMock = vi.spyOn(window.HTMLMediaElement.prototype, "pause").mockImplementation(() => {});

    render(<VideoPlayer videoId="test-vid-123" />);
    const container = screen.getByTestId("video-player-container");

    // Space toggles play
    fireEvent.keyDown(container, { key: " " });
    expect(playMock).toHaveBeenCalled();

    // Volume keys
    fireEvent.keyDown(container, { key: "ArrowDown" });
    const volSlider = screen.getByTestId("volume-slider") as HTMLInputElement;
    expect(Number(volSlider.value)).toBeLessThan(1);

    playMock.mockRestore();
    pauseMock.mockRestore();
  });
});

describe("Phase 13: VideoDetailPage Integration", () => {
  beforeEach(() => {
    global.fetch = vi.fn().mockImplementation(async (url: string, opts?: RequestInit) => {
      if (opts?.method === "POST" && url.includes("/metadata/refresh")) {
        return {
          ok: true,
          json: async () => ({
            ...mockVideoWithAudio,
            metadata_status: "COMPLETED",
            metadata_extracted_at: "2026-11-23T14:30:00Z",
          }),
        };
      }
      if (url.includes("/api/v1/videos/vid-preview-1")) {
        return { ok: true, json: async () => mockVideoWithAudio };
      }
      if (url.includes("/api/v1/videos/vid-preview-noaudio")) {
        return { ok: true, json: async () => mockVideoNoAudio };
      }
      if (url.includes("/api/v1/jobs")) {
        return { ok: true, json: async () => ({ items: [], total: 0, limit: 20, offset: 0 }) };
      }
      if (url.includes("/api/v1/transcripts")) {
        return { ok: false, status: 404, json: async () => ({ detail: "Not found" }) };
      }
      if (url.includes("/api/v1/highlights")) {
        return { ok: true, json: async () => [] };
      }
      if (url.includes("/api/v1/clips")) {
        return { ok: true, json: async () => ({ items: [], total: 0, limit: 20, offset: 0 }) };
      }
      return { ok: true, json: async () => ({}) };
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders VideoPlayer, stream characteristics, and metadata refresh button", async () => {
    render(
      <MemoryRouter initialEntries={["/video/vid-preview-1"]}>
        <ToastProvider>
          <Routes>
            <Route path="/video/:id" element={<VideoDetailPage />} />
          </Routes>
        </ToastProvider>
      </MemoryRouter>
    );

    // Verify player is rendered
    expect(await screen.findByTestId("video-player-container")).toBeInTheDocument();
    expect(screen.getByTestId("html5-video-element")).toBeInTheDocument();

    // Verify Section E metadata status & refresh button
    expect(screen.getByText("FFprobe Verified")).toBeInTheDocument();
    const refreshBtn = screen.getByTestId("refresh-metadata-btn");
    expect(refreshBtn).toBeInTheDocument();

    // Verify Section B Quick Stats
    expect(screen.getByText("Landscape")).toBeInTheDocument();
    expect(screen.getByText("MP4")).toBeInTheDocument();
    expect(screen.getByText("4.69 Mbps")).toBeInTheDocument();

    // Verify Section C Video Stream Characteristics
    expect(screen.getByText("Stream Characteristics (FFprobe Verified)")).toBeInTheDocument();
    expect(screen.getByText("High")).toBeInTheDocument();
    expect(screen.getByText("yuv420p")).toBeInTheDocument();
    expect(screen.getByText("8-bit")).toBeInTheDocument();

    // Verify Section D Audio Characteristics
    expect(screen.getByText("Audio Stream Characteristics")).toBeInTheDocument();
    expect(screen.getByText("aac")).toBeInTheDocument();
    expect(screen.getByText("stereo")).toBeInTheDocument();
    expect(screen.getByText("192 kbps")).toBeInTheDocument();
  });

  it("triggers metadata refresh API when button is clicked", async () => {
    render(
      <MemoryRouter initialEntries={["/video/vid-preview-1"]}>
        <ToastProvider>
          <Routes>
            <Route path="/video/:id" element={<VideoDetailPage />} />
          </Routes>
        </ToastProvider>
      </MemoryRouter>
    );

    const refreshBtn = await screen.findByTestId("refresh-metadata-btn");
    fireEvent.click(refreshBtn);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/videos/vid-preview-1/metadata/refresh"),
        expect.objectContaining({ method: "POST" })
      );
    });
  });

  it("renders honest empty state when video has no audio track", async () => {
    render(
      <MemoryRouter initialEntries={["/video/vid-preview-noaudio"]}>
        <ToastProvider>
          <Routes>
            <Route path="/video/:id" element={<VideoDetailPage />} />
          </Routes>
        </ToastProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText("No Audio Stream Detected")).toBeInTheDocument();
    expect(screen.getByText(/Faster-Whisper transcription and speech-based AI highlight analysis will be skipped/i)).toBeInTheDocument();
  });
});

describe("Phase 13: VideoLibraryPage Badges", () => {
  it("renders format, orientation, and resolution badges on video cards", async () => {
    global.fetch = vi.fn().mockImplementation(async (url: string) => {
      if (url.includes("/api/v1/videos")) {
        return {
          ok: true,
          json: async () => ({
            items: [mockVideoWithAudio, mockVideoNoAudio],
            total: 2,
            limit: 12,
            offset: 0,
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    });

    render(
      <MemoryRouter initialEntries={["/videos"]}>
        <ToastProvider>
          <Routes>
            <Route path="/videos" element={<VideoLibraryPage />} />
          </Routes>
        </ToastProvider>
      </MemoryRouter>
    );

    // Format & orientation badges
    expect(await screen.findAllByText("MP4")).toHaveLength(2);
    expect(screen.getAllByText("Landscape")).toHaveLength(2);
    expect(screen.getAllByText("1080p")).toHaveLength(2);
  });
});
