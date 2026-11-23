import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { VideoDetailPage } from "../features/videos/VideoDetailPage";
import { ToastProvider } from "../components/ui/toast";
import { Video, ProcessingJob, AudioAsset } from "../types/api";

const mockVideoWithAudio: Video = {
  id: "vid-test-1",
  filename: "sample_video.mp4",
  original_filename: "Sample Video With Sound.mp4",
  file_path: "storage/uploads/sample_video.mp4",
  file_size_bytes: 10485760,
  duration_seconds: 60.0,
  width: 1920,
  height: 1080,
  aspect_ratio: "16:9",
  fps: 30.0,
  video_codec: "h264",
  has_audio: true,
  audio_codec: "aac",
  audio_sample_rate: 48000,
  audio_channels: 2,
  channel_layout: "stereo",
  status: "READY",
  metadata_status: "COMPLETED",
  file_exists: true,
  storage_label: "Local SSD Storage",
  created_at: "2026-11-23T10:00:00Z",
  audio_asset: null,
  audio_streams: [
    {
      index: 1,
      codec_name: "aac",
      channels: 2,
      sample_rate: 48000,
      channel_layout: "stereo",
      is_default: true,
      language: "eng",
      title: "English Audio",
      bit_rate: 192000,
    },
  ],
};

const mockVideoMultiStream: Video = {
  ...mockVideoWithAudio,
  id: "vid-test-multi",
  audio_streams: [
    {
      index: 1,
      codec_name: "aac",
      channels: 2,
      sample_rate: 48000,
      channel_layout: "stereo",
      is_default: true,
      language: "eng",
      title: "English",
      bit_rate: 192000,
    },
    {
      index: 2,
      codec_name: "mp3",
      channels: 1,
      sample_rate: 44100,
      channel_layout: "mono",
      is_default: false,
      language: "spa",
      title: "Spanish",
      bit_rate: 128000,
    },
  ],
};

const mockVideoNoAudio: Video = {
  ...mockVideoWithAudio,
  id: "vid-test-none",
  has_audio: false,
  audio_codec: null,
  audio_sample_rate: null,
  audio_channels: null,
  channel_layout: null,
  audio_streams: [],
};

const mockCompletedAudioAsset: AudioAsset = {
  id: "asset-123",
  video_id: "vid-test-1",
  filename: "asset-123.wav",
  format: "wav",
  codec: "pcm_s16le",
  sample_rate: 16000,
  channels: 1,
  channel_layout: "mono",
  bit_depth: 16,
  duration_seconds: 60.0,
  file_size_bytes: 1920000,
  source_stream_index: 1,
  status: "COMPLETED",
  created_at: "2026-11-23T10:05:00Z",
};

const mockVideoWithCompletedAudio: Video = {
  ...mockVideoWithAudio,
  audio_asset: mockCompletedAudioAsset,
};

describe("Phase 14: Audio Extraction & Preprocessing Pipeline (Frontend)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const renderDetailPage = (
    initialVideo: Video,
    initialJobs: ProcessingJob[] = [],
    customFetchHandler?: (url: string, options?: RequestInit) => Promise<Response | null>
  ) => {
    // Mock fetch for all endpoints
    vi.spyOn(global, "fetch").mockImplementation(async (url, options) => {
      const u = url.toString();
      if (customFetchHandler) {
        const customRes = await customFetchHandler(u, options);
        if (customRes) return customRes;
      }
      if (u.match(/\/videos\/[a-zA-Z0-9_-]+$/)) {
        return new Response(JSON.stringify(initialVideo), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (u.includes("/jobs?video_id=")) {
        return new Response(JSON.stringify({ items: initialJobs, total: initialJobs.length, page: 1, limit: 20, pages: 1 }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (u.match(/\/jobs\/[a-zA-Z0-9_-]+$/) && !u.includes("/cancel")) {
        const jobId = u.split("/").pop();
        const found = initialJobs.find((j) => j.id === jobId) || initialJobs[0];
        if (found) {
          return new Response(JSON.stringify(found), { status: 200, headers: { "Content-Type": "application/json" } });
        }
      }
      if (u.includes("/transcripts/")) {
        return new Response(JSON.stringify(null), { status: 404, headers: { "Content-Type": "application/json" } });
      }
      if (u.includes("/highlights/")) {
        return new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (u.includes("/clips?video_id=")) {
        return new Response(JSON.stringify({ items: [], total: 0, page: 1, limit: 20, pages: 1 }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response(JSON.stringify({}), { status: 200, headers: { "Content-Type": "application/json" } });
    });

    return render(
      <MemoryRouter initialEntries={[`/videos/${initialVideo.id}`]}>
        <ToastProvider>
          <Routes>
            <Route path="/videos/:id" element={<VideoDetailPage />} />
          </Routes>
        </ToastProvider>
      </MemoryRouter>
    );
  };

  it("renders the Audio Extraction card on the Video Details overview page", async () => {
    renderDetailPage(mockVideoWithAudio);

    expect(await screen.findByTestId("audio-extraction-card")).toBeInTheDocument();
    expect(screen.getByText(/FFmpeg Audio Preprocessing/i)).toBeInTheDocument();
  });

  it("displays extraction prompt and trigger button when audio is not yet extracted", async () => {
    renderDetailPage(mockVideoWithAudio);

    expect(await screen.findByTestId("audio-extract-prompt")).toBeInTheDocument();
    expect(screen.getByTestId("extract-audio-btn")).toBeInTheDocument();
    expect(screen.getByText(/Extract & Preprocess Audio/i)).toBeInTheDocument();
    expect(screen.getByText(/16,000 Hz, 16-bit mono PCM WAV/i)).toBeInTheDocument();
  });

  it("displays 'No Audio Streams Available' notice when video lacks audio", async () => {
    renderDetailPage(mockVideoNoAudio);

    expect(await screen.findByTestId("no-audio-notice")).toBeInTheDocument();
    expect(screen.getByText(/No Audio Streams Available/i)).toBeInTheDocument();
    expect(screen.queryByTestId("extract-audio-btn")).not.toBeInTheDocument();
  });

  it("renders stream selector when video contains multiple audio streams", async () => {
    renderDetailPage(mockVideoMultiStream);

    expect(await screen.findByTestId("audio-extract-prompt")).toBeInTheDocument();
    expect(screen.getByText(/Select Target Audio Stream:/i)).toBeInTheDocument();
    expect(screen.getByText(/Stream #1: aac/i)).toBeInTheDocument();
    expect(screen.getByText(/Stream #2: mp3/i)).toBeInTheDocument();
  });

  it("triggers audio extraction API call when 'Extract & Preprocess Audio' is clicked", async () => {
    let extractCalled = false;
    renderDetailPage(mockVideoWithAudio, [], async (u) => {
      if (u.includes("/extract-audio")) {
        extractCalled = true;
        return new Response(
          JSON.stringify({
            job_id: "job-extract-999",
            video_id: mockVideoWithAudio.id,
            status: "QUEUED",
            progress_percent: 0.0,
            current_step: "Audio extraction queued...",
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        );
      }
      return null;
    });

    const extractBtn = await screen.findByTestId("extract-audio-btn");
    fireEvent.click(extractBtn);

    await waitFor(() => {
      expect(extractCalled).toBe(true);
    });
  });

  it("displays progress bar, percentage, and current step while job is processing", async () => {
    const activeJob: ProcessingJob = {
      id: "job-audio-proc",
      video_id: mockVideoWithAudio.id,
      job_type: "AUDIO_EXTRACTION",
      status: "PROCESSING",
      progress_percent: 45.0,
      current_step: "Extracting PCM audio (45%)...",
      created_at: "2026-11-23T10:01:00Z",
    };

    renderDetailPage(mockVideoWithAudio, [activeJob]);

    expect(await screen.findByTestId("audio-extraction-progress")).toBeInTheDocument();
    expect(screen.getByText("45%")).toBeInTheDocument();
    expect(screen.getByText(/Extracting PCM audio \(45%\)\.\.\./i)).toBeInTheDocument();
    expect(screen.getByTestId("cancel-audio-btn")).toBeInTheDocument();
  });

  it("triggers cancel API call when 'Cancel Extraction' is clicked", async () => {
    const activeJob: ProcessingJob = {
      id: "job-audio-proc-cancel",
      video_id: mockVideoWithAudio.id,
      job_type: "AUDIO_EXTRACTION",
      status: "PROCESSING",
      progress_percent: 30.0,
      current_step: "Extracting PCM audio...",
      created_at: "2026-11-23T10:01:00Z",
    };

    let cancelCalled = false;
    renderDetailPage(mockVideoWithAudio, [activeJob], async (u) => {
      if (u.includes("/jobs/job-audio-proc-cancel/cancel")) {
        cancelCalled = true;
        return new Response(
          JSON.stringify({ id: activeJob.id, status: "CANCELLED", current_step: "Cancelled by user" }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }
      return null;
    });

    const cancelBtn = await screen.findByTestId("cancel-audio-btn");
    fireEvent.click(cancelBtn);

    await waitFor(() => {
      expect(cancelCalled).toBe(true);
    });
  });

  it("displays validated WAV asset specs when extraction is completed", async () => {
    renderDetailPage(mockVideoWithCompletedAudio);

    expect(await screen.findByTestId("audio-asset-details")).toBeInTheDocument();
    expect(screen.getByTestId("audio-asset-ready-badge")).toBeInTheDocument();
    expect(screen.getByText("WAV (RIFF)")).toBeInTheDocument();
    expect(screen.getByText("pcm_s16le")).toBeInTheDocument();
    expect(screen.getByText("16,000 Hz")).toBeInTheDocument();
    expect(screen.getByText("1 (Mono)")).toBeInTheDocument();
    expect(screen.getByText("16-bit")).toBeInTheDocument();
    expect(screen.getByTestId("reextract-audio-btn")).toBeInTheDocument();
  });

  it("triggers force re-extraction when 'Re-Extract Audio (Force)' is clicked", async () => {
    let reextractPayload: { force_reextract?: boolean } | null = null;
    renderDetailPage(mockVideoWithCompletedAudio, [], async (u, options) => {
      if (u.includes("/extract-audio")) {
        if (options?.body) {
          reextractPayload = JSON.parse(options.body.toString());
        }
        return new Response(
          JSON.stringify({
            job_id: "job-reextract-1",
            video_id: mockVideoWithCompletedAudio.id,
            status: "QUEUED",
            progress_percent: 0.0,
            current_step: "Audio extraction queued...",
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        );
      }
      return null;
    });

    const reextractBtn = await screen.findByTestId("reextract-audio-btn");
    fireEvent.click(reextractBtn);

    await waitFor(() => {
      expect(reextractPayload).not.toBeNull();
      expect(reextractPayload?.force_reextract).toBe(true);
    });
  });

  it("disables extraction button when source video file does not exist on disk", async () => {
    const mockMissingFileVideo: Video = {
      ...mockVideoWithAudio,
      file_exists: false,
    };

    renderDetailPage(mockMissingFileVideo);

    const extractBtn = await screen.findByTestId("extract-audio-btn");
    expect(extractBtn).toBeDisabled();
  });

  it("handles extraction error and keeps UI in a clean state", async () => {
    renderDetailPage(mockVideoWithAudio, [], async (u) => {
      if (u.includes("/extract-audio")) {
        return new Response(
          JSON.stringify({ detail: "Insufficient disk space for audio extraction.", error_code: "INSUFFICIENT_STORAGE" }),
          { status: 507, headers: { "Content-Type": "application/json" } }
        );
      }
      return null;
    });

    const extractBtn = await screen.findByTestId("extract-audio-btn");
    fireEvent.click(extractBtn);

    await waitFor(() => {
      expect(extractBtn).toBeEnabled();
    });
  });
});
