import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { HardDrive } from "lucide-react";
import {
  EmptyVideoLibrary,
  FeatureUnavailable,
  HardwareMetricCard,
  PageToolbar,
  ProcessingStatus,
  SectionHeader,
  StorageUsageBar,
  VideoMetadataRow,
  VideoThumbnail,
} from "../components/workstation";
import { ComponentShowcasePage } from "../features/showcase/ComponentShowcasePage";
import { ToastProvider } from "../components/ui/toast";

describe("Workstation Specific UI Modules", () => {
  describe("VideoThumbnail Component", () => {
    it("renders fallback placeholder and duration badge when no thumbnail image exists", () => {
      render(
        <VideoThumbnail
          durationSeconds={125}
          resolution="1080p"
          aspectRatio="16:9"
        />
      );
      expect(screen.getByText("No Preview")).toBeInTheDocument();
      expect(screen.getByText("02:05")).toBeInTheDocument();
      expect(screen.getByText("1080p")).toBeInTheDocument();
    });

    it("renders 9:16 vertical aspect ratio container", () => {
      const { container } = render(
        <VideoThumbnail aspectRatio="9:16" durationSeconds={45} />
      );
      const thumbnailDiv = container.firstChild as HTMLElement;
      expect(thumbnailDiv).toHaveClass("aspect-[9/16]");
    });
  });

  describe("VideoMetadataRow Component", () => {
    it("renders resolution, duration, fps, codecs, and file size", () => {
      render(
        <VideoMetadataRow
          durationSeconds={75}
          width={1920}
          height={1080}
          fps={30.0}
          videoCodec="h264"
          audioCodec="aac"
          fileSizeBytes={15728640}
        />
      );
      expect(screen.getByText("1m 15s")).toBeInTheDocument();
      expect(screen.getByText("1920x1080")).toBeInTheDocument();
      expect(screen.getByText("30 fps")).toBeInTheDocument();
      expect(screen.getByText("h264")).toBeInTheDocument();
      expect(screen.getByText("15.0 MB")).toBeInTheDocument();
    });
  });

  describe("ProcessingStatus Component", () => {
    it("renders PROCESSING state with step and percentage", () => {
      render(
        <ProcessingStatus
          status="PROCESSING"
          progressPercent={65}
          currentStep="Extracting audio stream..."
          jobType="Ingestion"
        />
      );
      expect(screen.getByText("Processing")).toBeInTheDocument();
      expect(screen.getByText("65%")).toBeInTheDocument();
      expect(screen.getByText("Extracting audio stream...")).toBeInTheDocument();
      expect(screen.getByText(/ingestion/i)).toBeInTheDocument();
    });

    it("renders FAILED state with error message box", () => {
      render(
        <ProcessingStatus
          status="FAILED"
          errorMessage="Subprocess exited with code 1"
        />
      );
      expect(screen.getByText("Failed")).toBeInTheDocument();
      expect(screen.getByText("Subprocess exited with code 1")).toBeInTheDocument();
    });
  });

  describe("StorageUsageBar Component", () => {
    it("renders free and total space", () => {
      render(<StorageUsageBar freeSpaceGb={120.5} totalSpaceGb={512} minSafeFreeSpaceGb={10} />);
      expect(screen.getByText("120.5 GB free")).toBeInTheDocument();
      expect(screen.getByText("/ 512 GB total")).toBeInTheDocument();
    });

    it("renders critical alert when free space is below safety threshold", () => {
      render(<StorageUsageBar freeSpaceGb={6.2} totalSpaceGb={512} minSafeFreeSpaceGb={10} />);
      expect(screen.getByText(/Storage space is critical/i)).toBeInTheDocument();
    });
  });

  describe("HardwareMetricCard Component", () => {
    it("renders title, value, subvalue and percent", () => {
      render(
        <HardwareMetricCard
          title="VRAM Usage"
          value="1.8 / 4.0 GB"
          subValue="RTX 3050"
          percent={45}
          status="safe"
          icon={<HardDrive className="h-4 w-4" />}
        />
      );
      expect(screen.getByText("VRAM Usage")).toBeInTheDocument();
      expect(screen.getByText("1.8 / 4.0 GB")).toBeInTheDocument();
      expect(screen.getByText("RTX 3050")).toBeInTheDocument();
      expect(screen.getByText("45%")).toBeInTheDocument();
    });
  });

  describe("EmptyVideoLibrary Component", () => {
    it("renders empty state and fires onUploadClick", () => {
      const handleUpload = vi.fn();
      render(<EmptyVideoLibrary onUploadClick={handleUpload} />);
      expect(screen.getByText("No Videos Ingested")).toBeInTheDocument();
      const btn = screen.getByRole("button", { name: /import local video/i });
      fireEvent.click(btn);
      expect(handleUpload).toHaveBeenCalledTimes(1);
    });
  });

  describe("FeatureUnavailable Component", () => {
    it("renders feature milestone and technical notes", () => {
      render(
        <FeatureUnavailable
          featureName="NVENC Render Pipeline"
          activationPhase="Phase 16"
          description="Hardware export rendering."
          roadmapNote="Activates in Phase 16."
        />
      );
      expect(screen.getByText("NVENC Render Pipeline")).toBeInTheDocument();
      expect(screen.getByText("Activates in Phase 16")).toBeInTheDocument();
      expect(screen.getByText("Hardware export rendering.")).toBeInTheDocument();
    });
  });

  describe("SectionHeader & PageToolbar", () => {
    it("renders SectionHeader with title and actions", () => {
      render(
        <SectionHeader
          title="Video Library"
          description="Manage long-form videos"
          actions={<button>Action Button</button>}
        />
      );
      expect(screen.getByText("Video Library")).toBeInTheDocument();
      expect(screen.getByText("Manage long-form videos")).toBeInTheDocument();
      expect(screen.getByText("Action Button")).toBeInTheDocument();
    });

    it("renders PageToolbar with slots", () => {
      render(
        <PageToolbar
          searchSlot={<input placeholder="Search..." />}
          actionSlot={<button>Add</button>}
        />
      );
      expect(screen.getByPlaceholderText("Search...")).toBeInTheDocument();
      expect(screen.getByText("Add")).toBeInTheDocument();
    });
  });

  describe("ComponentShowcasePage", () => {
    it("renders the entire design system showcase without throwing", () => {
      render(
        <ToastProvider>
          <BrowserRouter>
            <ComponentShowcasePage />
          </BrowserRouter>
        </ToastProvider>
      );
      expect(screen.getByText("Design System & UI Components")).toBeInTheDocument();
      expect(screen.getByText("Buttons & Actions")).toBeInTheDocument();
    });
  });
});
