import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { TranscriptionPanel, TranscriptViewer } from "../features/transcripts/components";
import { TranscriptViewerPage } from "../features/transcripts/TranscriptViewerPage";
import { ToastProvider } from "../components/ui/toast";
import { api } from "../services/api";
import {
  Transcript,
  AudioAsset,
  ProcessingJob,
  AvailableModelsResponse,
} from "../types/api";

const mockModelsResponse: AvailableModelsResponse = {
  models: [
    {
      model_name: "tiny",
      description: "Ultra-lightweight 39M parameter model.",
      parameters: "39M",
      vram_required_mb: 500,
      recommended_for: "Low-resource environments",
      devices_supported: ["cuda", "cpu"],
    },
    {
      model_name: "base",
      description: "Standard 74M parameter model.",
      parameters: "74M",
      vram_required_mb: 1000,
      recommended_for: "Default candidate for workstation (RTX 3050)",
      devices_supported: ["cuda", "cpu"],
    },
    {
      model_name: "small",
      description: "High-accuracy 244M parameter model.",
      parameters: "244M",
      vram_required_mb: 2000,
      recommended_for: "Complex dialogue",
      devices_supported: ["cuda", "cpu"],
    },
  ],
  default_model: "base",
  cuda_available: true,
  detected_gpu: "NVIDIA GeForce RTX 3050 Laptop GPU",
  cuda_compute_types: ["float16", "int8_float16", "int8"],
  cpu_compute_types: ["int8", "float32"],
};

const mockAudioAsset: AudioAsset = {
  id: "audio-asset-1",
  video_id: "video-123",
  filename: "video-123.wav",
  format: "wav",
  codec: "pcm_s16le",
  sample_rate: 16000,
  channels: 1,
  channel_layout: "mono",
  bit_depth: 16,
  duration_seconds: 45.2,
  file_size_bytes: 1446400,
  source_stream_index: 0,
  status: "COMPLETED",
};

const mockTranscript: Transcript = {
  id: "transcript-456",
  video_id: "video-123",
  model_name: "base",
  compute_type: "float16",
  device: "cuda",
  language: "en",
  language_probability: 0.98,
  status: "COMPLETED",
  full_text: "Welcome to Clipsly. This is local speech recognition.",
  word_count: 8,
  segment_count: 2,
  audio_duration_seconds: 45.2,
  processing_time_seconds: 3.42,
  is_active: true,
  created_at: "2026-11-23T12:00:00Z",
  segments: [
    {
      id: "seg-1",
      transcript_id: "transcript-456",
      segment_index: 0,
      start_ms: 500,
      end_ms: 2200,
      text: "Welcome to Clipsly.",
      avg_confidence: 0.99,
      words: [
        { word: "Welcome", start_ms: 500, end_ms: 1100, probability: 0.99 },
        { word: "to", start_ms: 1150, end_ms: 1300, probability: 0.99 },
        { word: "Clipsly.", start_ms: 1350, end_ms: 2200, probability: 0.98 },
      ],
    },
    {
      id: "seg-2",
      transcript_id: "transcript-456",
      segment_index: 1,
      start_ms: 2400,
      end_ms: 4800,
      text: "This is local speech recognition.",
      avg_confidence: 0.95,
      words: [
        { word: "This", start_ms: 2400, end_ms: 2700, probability: 0.96 },
        { word: "is", start_ms: 2750, end_ms: 2900, probability: 0.98 },
        { word: "local", start_ms: 2950, end_ms: 3400, probability: 0.94 },
        { word: "speech", start_ms: 3450, end_ms: 3900, probability: 0.95 },
        { word: "recognition.", start_ms: 3950, end_ms: 4800, probability: 0.93 },
      ],
    },
  ],
};

describe("Phase 15: Faster-Whisper Speech-to-Text Pipeline (Frontend)", () => {
  beforeEach(() => {
    vi.spyOn(api.transcripts, "getModels").mockResolvedValue(mockModelsResponse);
    vi.spyOn(api.transcripts, "get").mockResolvedValue(mockTranscript);
    vi.spyOn(api.transcripts, "getSegments").mockResolvedValue({
      transcript_id: mockTranscript.id,
      total: mockTranscript.segments!.length,
      offset: 0,
      limit: 100,
      segments: mockTranscript.segments!,
    });
    vi.spyOn(api.transcripts, "updateSegment").mockResolvedValue({
      ...mockTranscript.segments![0],
      text: "Welcome to Clipsly Workstation.",
    });
    vi.spyOn(api.videos, "transcribe").mockResolvedValue({
      job_id: "job-transcribe-999",
      video_id: "video-123",
      status: "QUEUED",
      progress_percent: 0.0,
      current_step: "Transcription job queued...",
    });
    vi.spyOn(api.jobs, "cancel").mockResolvedValue({
      id: "job-transcribe-999",
      status: "CANCELLED",
      current_step: "Cancelled by user",
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // -------------------------------------------------------------------------
  // 1. TranscriptionPanel Tests
  // -------------------------------------------------------------------------

  it("1. renders TranscriptionPanel with model information and detected GPU", async () => {
    render(
      <ToastProvider>
        <TranscriptionPanel
          videoId="video-123"
          hasAudio={true}
          audioAsset={mockAudioAsset}
        />
      </ToastProvider>
    );

    expect(screen.getByText("Faster-Whisper Speech-to-Text Pipeline")).toBeInTheDocument();
    expect(await screen.findByText(/NVIDIA GeForce RTX 3050/i)).toBeInTheDocument();
    expect(screen.getByTestId("model-select")).toHaveValue("base");
    expect(screen.getByTestId("device-select")).toHaveValue("cuda");
  });

  it("2. shows warning alert when audio asset has not been extracted", () => {
    render(
      <ToastProvider>
        <TranscriptionPanel
          videoId="video-123"
          hasAudio={true}
          audioAsset={null}
        />
      </ToastProvider>
    );

    expect(screen.getByTestId("audio-missing-warning")).toBeInTheDocument();
    expect(screen.getByText(/16kHz WAV Audio Required/i)).toBeInTheDocument();
    expect(screen.getByTestId("start-transcribe-btn")).toBeDisabled();
  });

  it("3. fires onExtractAudioRequested when audio prerequisite button is clicked", () => {
    const handleExtract = vi.fn();
    render(
      <ToastProvider>
        <TranscriptionPanel
          videoId="video-123"
          hasAudio={true}
          audioAsset={null}
          onExtractAudioRequested={handleExtract}
        />
      </ToastProvider>
    );

    const extractBtn = screen.getByTestId("extract-audio-prereq-btn");
    fireEvent.click(extractBtn);
    expect(handleExtract).toHaveBeenCalledTimes(1);
  });

  it("4. changing model size updates the selection", async () => {
    render(
      <ToastProvider>
        <TranscriptionPanel
          videoId="video-123"
          hasAudio={true}
          audioAsset={mockAudioAsset}
        />
      </ToastProvider>
    );

    const modelSelect = await screen.findByTestId("model-select");
    fireEvent.change(modelSelect, { target: { value: "small" } });
    expect(modelSelect).toHaveValue("small");
  });

  it("5. toggling Silero VAD speech filter updates checkbox state", () => {
    render(
      <ToastProvider>
        <TranscriptionPanel
          videoId="video-123"
          hasAudio={true}
          audioAsset={mockAudioAsset}
        />
      </ToastProvider>
    );

    const vadToggle = screen.getByTestId("vad-toggle") as HTMLInputElement;
    expect(vadToggle.checked).toBe(true);
    fireEvent.click(vadToggle);
    expect(vadToggle.checked).toBe(false);
  });

  it("6. toggling Word Timestamps updates checkbox state", () => {
    render(
      <ToastProvider>
        <TranscriptionPanel
          videoId="video-123"
          hasAudio={true}
          audioAsset={mockAudioAsset}
        />
      </ToastProvider>
    );

    const wordToggle = screen.getByTestId("word-timestamps-toggle") as HTMLInputElement;
    expect(wordToggle.checked).toBe(true);
    fireEvent.click(wordToggle);
    expect(wordToggle.checked).toBe(false);
  });

  it("7. shows force-retranscribe option when hasExistingTranscript is true", () => {
    render(
      <ToastProvider>
        <TranscriptionPanel
          videoId="video-123"
          hasAudio={true}
          audioAsset={mockAudioAsset}
          hasExistingTranscript={true}
        />
      </ToastProvider>
    );

    expect(screen.getByTestId("force-retranscribe-toggle")).toBeInTheDocument();
    expect(screen.getByText("Re-Run Transcription")).toBeInTheDocument();
  });

  it("8. clicking Start Transcription calls api.videos.transcribe and triggers callback", async () => {
    const handleStarted = vi.fn();
    render(
      <ToastProvider>
        <TranscriptionPanel
          videoId="video-123"
          hasAudio={true}
          audioAsset={mockAudioAsset}
          onTranscriptionStarted={handleStarted}
        />
      </ToastProvider>
    );

    const startBtn = screen.getByTestId("start-transcribe-btn");
    fireEvent.click(startBtn);

    await waitFor(() => {
      expect(api.videos.transcribe).toHaveBeenCalledWith(
        "video-123",
        expect.objectContaining({
          model_name: "base",
          device: "cuda",
          compute_type: "float16",
          vad_filter: true,
          word_timestamps: true,
        })
      );
    });

    expect(handleStarted).toHaveBeenCalledWith("job-transcribe-999");
  });

  it("9. renders active job progress bar with percentage and step description", () => {
    const activeJob: ProcessingJob = {
      id: "job-transcribe-999",
      video_id: "video-123",
      job_type: "TRANSCRIPTION",
      status: "processing",
      progress_percent: 64.0,
      current_step: "Transcribing audio with Silero VAD...",
      created_at: "2026-11-23T12:00:00Z",
    };

    render(
      <ToastProvider>
        <TranscriptionPanel
          videoId="video-123"
          hasAudio={true}
          audioAsset={mockAudioAsset}
          activeJob={activeJob}
        />
      </ToastProvider>
    );

    expect(screen.getByTestId("transcription-progress")).toBeInTheDocument();
    expect(screen.getByText("Transcribing audio with Silero VAD...")).toBeInTheDocument();
    expect(screen.getByText("64%")).toBeInTheDocument();
    expect(screen.getByTestId("cancel-transcribe-btn")).toBeInTheDocument();
  });

  it("10. clicking Cancel on active job invokes api.jobs.cancel", async () => {
    const handleCancelled = vi.fn();
    const activeJob: ProcessingJob = {
      id: "job-transcribe-999",
      video_id: "video-123",
      job_type: "TRANSCRIPTION",
      status: "processing",
      progress_percent: 45.0,
      current_step: "Inferring speech tokens...",
      created_at: "2026-11-23T12:00:00Z",
    };

    render(
      <ToastProvider>
        <TranscriptionPanel
          videoId="video-123"
          hasAudio={true}
          audioAsset={mockAudioAsset}
          activeJob={activeJob}
          onJobCancelled={handleCancelled}
        />
      </ToastProvider>
    );

    const cancelBtn = screen.getByTestId("cancel-transcribe-btn");
    fireEvent.click(cancelBtn);

    await waitFor(() => {
      expect(api.jobs.cancel).toHaveBeenCalledWith("job-transcribe-999");
    });
    expect(handleCancelled).toHaveBeenCalledTimes(1);
  });

  // -------------------------------------------------------------------------
  // 2. TranscriptViewer Tests
  // -------------------------------------------------------------------------

  it("11. renders TranscriptViewer with model, device, language, and word count cards", () => {
    render(
      <ToastProvider>
        <TranscriptViewer transcript={mockTranscript} />
      </ToastProvider>
    );

    expect(screen.getByTestId("transcript-viewer")).toBeInTheDocument();
    expect(screen.getByText(/base \(float16\)/i)).toBeInTheDocument();
    expect(screen.getByText("CUDA")).toBeInTheDocument();
    expect(screen.getByText("Language")).toBeInTheDocument();
    expect(screen.getByText(/98%/)).toBeInTheDocument();
    expect(screen.getByText(/8 words/i)).toBeInTheDocument();
  });

  it("12. renders ordered sentence segments with timestamps", () => {
    render(
      <ToastProvider>
        <TranscriptViewer transcript={mockTranscript} />
      </ToastProvider>
    );

    expect(screen.getByText("Welcome to Clipsly.")).toBeInTheDocument();
    expect(screen.getByText("This is local speech recognition.")).toBeInTheDocument();
    expect(screen.getByTestId("timestamp-btn-seg-1")).toHaveTextContent("00:00.50");
  });

  it("13. clicking timestamp button invokes onSegmentClick with millisecond offset", () => {
    const handleSeek = vi.fn();
    render(
      <ToastProvider>
        <TranscriptViewer transcript={mockTranscript} onSegmentClick={handleSeek} />
      </ToastProvider>
    );

    const timeBtn = screen.getByTestId("timestamp-btn-seg-1");
    fireEvent.click(timeBtn);
    expect(handleSeek).toHaveBeenCalledWith(500);
  });

  it("14. search input filters segments in real time", () => {
    render(
      <ToastProvider>
        <TranscriptViewer transcript={mockTranscript} />
      </ToastProvider>
    );

    const searchInput = screen.getByTestId("transcript-search-input");
    fireEvent.change(searchInput, { target: { value: "recognition" } });

    expect(screen.queryByText("Welcome to Clipsly.")).not.toBeInTheDocument();
    expect(screen.getByText("This is local speech recognition.")).toBeInTheDocument();
  });

  it("15. toggling Word Timestamps view renders word-level tokens", () => {
    render(
      <ToastProvider>
        <TranscriptViewer transcript={mockTranscript} />
      </ToastProvider>
    );

    const wordModeBtn = screen.getByTestId("view-words-btn");
    fireEvent.click(wordModeBtn);

    expect(screen.getByText("Welcome")).toBeInTheDocument();
    expect(screen.getByText("Clipsly.")).toBeInTheDocument();
    expect(screen.getByText("recognition.")).toBeInTheDocument();
  });

  it("16. clicking edit button allows inline editing and saving calls api.transcripts.updateSegment", async () => {
    render(
      <ToastProvider>
        <TranscriptViewer transcript={mockTranscript} />
      </ToastProvider>
    );

    const editBtn = screen.getByTestId("edit-segment-seg-1");
    fireEvent.click(editBtn);

    const textarea = screen.getByTestId("edit-textarea-seg-1");
    fireEvent.change(textarea, { target: { value: "Welcome to Clipsly Workstation." } });

    const saveBtn = screen.getByTestId("save-edit-seg-1");
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(api.transcripts.updateSegment).toHaveBeenCalledWith(
        "transcript-456",
        "seg-1",
        "Welcome to Clipsly Workstation."
      );
    });

    expect(await screen.findByText("Welcome to Clipsly Workstation.")).toBeInTheDocument();
  });

  it("17. copy transcript button writes full text to clipboard", async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: { writeText: writeTextMock },
    });

    render(
      <ToastProvider>
        <TranscriptViewer transcript={mockTranscript} />
      </ToastProvider>
    );

    const copyBtn = screen.getByTestId("copy-transcript-btn");
    fireEvent.click(copyBtn);

    expect(writeTextMock).toHaveBeenCalledWith(
      "Welcome to Clipsly. This is local speech recognition."
    );
  });

  // -------------------------------------------------------------------------
  // 3. TranscriptViewerPage Integration
  // -------------------------------------------------------------------------

  it("18. TranscriptViewerPage loads transcript and renders viewer and back button", async () => {
    render(
      <ToastProvider>
        <MemoryRouter initialEntries={["/transcripts/video-123"]}>
          <Routes>
            <Route path="/transcripts/:id" element={<TranscriptViewerPage />} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    );

    expect(await screen.findByText("Speech-to-Text Transcript")).toBeInTheDocument();
    expect(screen.getByText("Welcome to Clipsly.")).toBeInTheDocument();
    expect(screen.getByText("Back to Video")).toBeInTheDocument();
  });
});
