import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import {
  HighlightCard,
  HighlightDetectionPanel,
  HighlightEditDialog,
} from "../features/highlights/components";
import { Highlight, ProcessingJob } from "../types/api";

const sampleHighlight: Highlight = {
  id: "hl-123",
  video_id: "vid-456",
  transcript_id: "trans-789",
  start_ms: 15000,
  end_ms: 45000,
  duration_ms: 30000,
  hook_sentence: "Why does this simple trick blow people's minds?",
  summary: "A breakdown of viral hook structures in video editing.",
  hook_score: 88.0,
  coherence_score: 85.0,
  density_score: 80.0,
  sentiment_score: 75.0,
  composite_score: 83.2,
  rank: 1,
  category: "Insight",
  status: "CANDIDATE",
  explanation: "Opens with an engaging question followed by clean conversational pacing.",
  warnings: ["high_filler_word_ratio"],
};

describe("HighlightCard Component", () => {
  it("renders rank badge, composite score, and category pill", () => {
    render(<HighlightCard highlight={sampleHighlight} />);

    expect(screen.getByText("#1 Top Pick")).toBeInTheDocument();
    expect(screen.getByText("Score: 83.2")).toBeInTheDocument();
    expect(screen.getByText("Insight")).toBeInTheDocument();
  });

  it("formats and displays time range and duration cleanly", () => {
    render(<HighlightCard highlight={sampleHighlight} />);

    // 15000ms = 00:15, 45000ms = 00:45, duration = 30s
    expect(screen.getByText(/00:15 - 00:45 \(30s\)/)).toBeInTheDocument();
  });

  it("quotes hook sentence with emphasized styling", () => {
    render(<HighlightCard highlight={sampleHighlight} />);

    expect(
      screen.getByText('"Why does this simple trick blow people\'s minds?"')
    ).toBeInTheDocument();
  });

  it("renders granular score breakdown bars", () => {
    render(<HighlightCard highlight={sampleHighlight} />);

    expect(screen.getByText("Hook (30%)")).toBeInTheDocument();
    expect(screen.getByText("Flow (30%)")).toBeInTheDocument();
    expect(screen.getByText("Density (25%)")).toBeInTheDocument();
    expect(screen.getByText("Energy (15%)")).toBeInTheDocument();
    expect(screen.getByText("88")).toBeInTheDocument();
    expect(screen.getByText("85")).toBeInTheDocument();
    expect(screen.getByText("80")).toBeInTheDocument();
    expect(screen.getByText("75")).toBeInTheDocument();
  });

  it("displays natural language explanation and warnings", () => {
    render(<HighlightCard highlight={sampleHighlight} />);

    expect(
      screen.getByText("Opens with an engaging question followed by clean conversational pacing.")
    ).toBeInTheDocument();
    expect(screen.getByText("high filler word ratio")).toBeInTheDocument();
  });

  it("triggers onSeek when seek button is clicked", () => {
    const handleSeek = vi.fn();
    render(<HighlightCard highlight={sampleHighlight} onSeek={handleSeek} />);

    const seekBtn = screen.getByRole("button", { name: /Seek/i });
    fireEvent.click(seekBtn);

    expect(handleSeek).toHaveBeenCalledWith(15.0);
  });

  it("triggers onAccept and onReject callbacks", () => {
    const handleAccept = vi.fn();
    const handleReject = vi.fn();

    render(
      <HighlightCard
        highlight={sampleHighlight}
        onAccept={handleAccept}
        onReject={handleReject}
      />
    );

    const acceptBtn = screen.getByRole("button", { name: /Accept/i });
    fireEvent.click(acceptBtn);
    expect(handleAccept).toHaveBeenCalledWith("hl-123");

    const rejectBtn = screen.getByRole("button", { name: /Reject/i });
    fireEvent.click(rejectBtn);
    expect(handleReject).toHaveBeenCalledWith("hl-123");
  });

  it("displays rejection reason when highlight is rejected", () => {
    const rejectedHighlight: Highlight = {
      ...sampleHighlight,
      status: "REJECTED",
      rejection_reason: "Pacing too slow for YouTube Shorts",
    };

    render(<HighlightCard highlight={rejectedHighlight} />);

    expect(screen.getByText("Rejected")).toBeInTheDocument();
    expect(
      screen.getByText(/Pacing too slow for YouTube Shorts/)
    ).toBeInTheDocument();
  });
});

describe("HighlightEditDialog Component", () => {
  it("validates duration boundaries and calls onSave", async () => {
    const handleSave = vi.fn().mockResolvedValue(undefined);
    const handleClose = vi.fn();

    render(
      <HighlightEditDialog
        highlight={sampleHighlight}
        isOpen={true}
        onClose={handleClose}
        onSave={handleSave}
        videoDurationSeconds={120.0}
      />
    );

    expect(screen.getByText("Fine-Tune Highlight")).toBeInTheDocument();

    const startInput = screen.getByLabelText(/Start Time/i);
    const endInput = screen.getByLabelText(/End Time/i);
    const saveBtn = screen.getByRole("button", { name: /Save Changes/i });

    // Set end <= start -> should trigger error
    fireEvent.change(endInput, { target: { value: "10" } });
    fireEvent.click(saveBtn);
    expect(screen.getByText("End time must be strictly greater than start time.")).toBeInTheDocument();
    expect(handleSave).not.toHaveBeenCalled();

    // Set duration < 10s -> should trigger duration error
    fireEvent.change(startInput, { target: { value: "10" } });
    fireEvent.change(endInput, { target: { value: "15" } });
    fireEvent.click(saveBtn);
    expect(screen.getByText("Highlight duration must be at least 10 seconds.")).toBeInTheDocument();
    expect(handleSave).not.toHaveBeenCalled();

    // Valid values: 10s to 35s (duration 25s)
    fireEvent.change(startInput, { target: { value: "10" } });
    fireEvent.change(endInput, { target: { value: "35" } });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(handleSave).toHaveBeenCalledWith("hl-123", {
        start_ms: 10000,
        end_ms: 35000,
        summary: "A breakdown of viral hook structures in video editing.",
      });
      expect(handleClose).toHaveBeenCalled();
    });
  });
});

describe("HighlightDetectionPanel Component", () => {
  it("renders duration presets and triggers detection request", async () => {
    const handleDetect = vi.fn().mockResolvedValue(undefined);

    render(
      <HighlightDetectionPanel
        videoId="vid-456"
        hasTranscript={true}
        onDetectRequested={handleDetect}
        statusFilter="ALL"
        onStatusFilterChange={vi.fn()}
        categoryFilter="ALL"
        onCategoryFilterChange={vi.fn()}
        sortBy="rank"
        onSortByChange={vi.fn()}
        stats={{ total: 0, accepted: 0, rejected: 0, topScore: 0 }}
      />
    );

    expect(screen.getByText("AI Highlight Detection & Scoring")).toBeInTheDocument();

    const detectBtn = screen.getByRole("button", { name: /Detect Highlights/i });
    expect(detectBtn).toBeEnabled();

    fireEvent.click(detectBtn);
    expect(handleDetect).toHaveBeenCalled();
  });

  it("displays live progress and cancel button during active processing job", async () => {
    const handleCancel = vi.fn().mockResolvedValue(undefined);
    const activeJob: ProcessingJob = {
      id: "job-hl-1",
      video_id: "vid-456",
      job_type: "HIGHLIGHT_DETECTION",
      status: "PROCESSING",
      progress_percent: 65.0,
      current_step: "Scoring candidate windows across transcript",
      created_at: new Date().toISOString(),
    };

    render(
      <HighlightDetectionPanel
        videoId="vid-456"
        hasTranscript={true}
        activeJob={activeJob}
        onDetectRequested={vi.fn()}
        onCancelJob={handleCancel}
        statusFilter="ALL"
        onStatusFilterChange={vi.fn()}
        categoryFilter="ALL"
        onCategoryFilterChange={vi.fn()}
        sortBy="rank"
        onSortByChange={vi.fn()}
        stats={{ total: 0, accepted: 0, rejected: 0, topScore: 0 }}
      />
    );

    expect(screen.getByText("Scoring candidate windows across transcript")).toBeInTheDocument();
    expect(screen.getByText("65%")).toBeInTheDocument();

    const cancelBtn = screen.getByRole("button", { name: /Cancel Detection/i });
    fireEvent.click(cancelBtn);
    expect(handleCancel).toHaveBeenCalledWith("job-hl-1");
  });
});
