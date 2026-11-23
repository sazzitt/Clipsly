import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  BarChart3,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { EmptyState } from "../../components/common/EmptyState";
import { Button } from "../../components/ui/button";
import { api } from "../../services/api";
import { useToast } from "../../hooks/useToast";
import {
  Highlight,
  HighlightDetectionRequest,
  ProcessingJob,
  Transcript,
  Video,
} from "../../types/api";
import {
  HighlightCard,
  HighlightDetectionPanel,
  HighlightEditDialog,
} from "./components";

export const HighlightsPage: React.FC = () => {
  const { id: videoId } = useParams<{ id: string }>();
  const { toast } = useToast();

  const [video, setVideo] = useState<Video | null>(null);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [highlights, setHighlights] = useState<Highlight[]>([]);
  const [activeJob, setActiveJob] = useState<ProcessingJob | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [editingHighlight, setEditingHighlight] = useState<Highlight | null>(null);
  const [isProcessingAction, setIsProcessingAction] = useState<boolean>(false);

  // Filters and Sorting
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [sortBy, setSortBy] = useState<string>("rank");

  // Fetch initial data
  const fetchData = useCallback(async () => {
    if (!videoId) return;
    try {
      const [videoRes, transcriptRes, highlightsRes, jobsRes] = await Promise.allSettled([
        api.videos.get(videoId),
        api.transcripts.get(videoId),
        api.highlights.list(videoId),
        api.jobs.list({ video_id: videoId, limit: 10 }),
      ]);

      if (videoRes.status === "fulfilled") {
        setVideo(videoRes.value);
      }
      if (transcriptRes.status === "fulfilled") {
        setTranscript(transcriptRes.value);
      }
      if (highlightsRes.status === "fulfilled") {
        setHighlights(highlightsRes.value);
      }
      if (jobsRes.status === "fulfilled") {
        const jobs = jobsRes.value?.items || [];
        const runningHighlightJob = jobs.find(
          (j) =>
            j.job_type === "HIGHLIGHT_DETECTION" &&
            (j.status === "PENDING" || j.status === "PROCESSING")
        );
        setActiveJob(runningHighlightJob || null);
      }
    } catch (err: unknown) {
      toast({
        title: "Failed to load highlights",
        description: err instanceof Error ? err.message : "An error occurred loading highlight data.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }, [videoId, toast]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Polling for active jobs
  useEffect(() => {
    if (!activeJob || (activeJob.status !== "PENDING" && activeJob.status !== "PROCESSING")) {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const job = await api.jobs.get(activeJob.id);
        setActiveJob(job);

        if (job.status === "COMPLETED") {
          toast({
            title: "Highlights Detected",
            description: "AI highlight candidate detection completed successfully.",
          });
          // Refresh highlights
          if (videoId) {
            const updated = await api.highlights.list(videoId);
            setHighlights(updated);
          }
        } else if (job.status === "FAILED") {
          toast({
            title: "Detection Failed",
            description: job.error_message || "Highlight detection failed.",
            variant: "destructive",
          });
        }
      } catch (err) {
        console.warn("Error polling highlight detection job:", err);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activeJob, videoId, toast]);

  // Handler for triggering detection
  const handleDetect = async (config: HighlightDetectionRequest) => {
    if (!videoId) return;
    try {
      const jobResp = await api.highlights.detect(videoId, config);
      toast({
        title: "Detection Queued",
        description: "AI highlight detection job has been scheduled in the worker queue.",
      });
      // Set active job to begin polling
      setActiveJob({
        id: jobResp.job_id,
        video_id: videoId,
        job_type: "HIGHLIGHT_DETECTION",
        status: jobResp.status as ProcessingJob["status"],
        progress_percent: jobResp.progress_percent,
        current_step: jobResp.current_step,
        created_at: jobResp.created_at,
      });
    } catch (err: unknown) {
      toast({
        title: "Detection Request Failed",
        description: err instanceof Error ? err.message : "Failed to submit highlight detection job.",
        variant: "destructive",
      });
      throw err;
    }
  };

  // Handler for cancelling detection
  const handleCancelJob = async (jobId: string) => {
    try {
      await api.jobs.cancel(jobId);
      toast({
        title: "Detection Cancelled",
        description: "Highlight detection job was cancelled.",
      });
      setActiveJob(null);
      await fetchData();
    } catch (err: unknown) {
      toast({
        title: "Failed to Cancel Job",
        description: err instanceof Error ? err.message : "Could not cancel detection job.",
        variant: "destructive",
      });
    }
  };

  // Handler for accepting highlight
  const handleAccept = async (highlightId: string) => {
    try {
      setIsProcessingAction(true);
      const updated = await api.highlights.accept(highlightId);
      setHighlights((prev) => prev.map((h) => (h.id === highlightId ? updated : h)));
      toast({
        title: "Highlight Accepted",
        description: "Candidate marked as ACCEPTED.",
      });
    } catch (err: unknown) {
      toast({
        title: "Failed to Accept Highlight",
        description: err instanceof Error ? err.message : "Error updating highlight status.",
        variant: "destructive",
      });
    } finally {
      setIsProcessingAction(false);
    }
  };

  // Handler for rejecting highlight
  const handleReject = async (highlightId: string) => {
    try {
      setIsProcessingAction(true);
      const updated = await api.highlights.reject(highlightId);
      setHighlights((prev) => prev.map((h) => (h.id === highlightId ? updated : h)));
      toast({
        title: "Highlight Rejected",
        description: "Candidate marked as REJECTED.",
      });
    } catch (err: unknown) {
      toast({
        title: "Failed to Reject Highlight",
        description: err instanceof Error ? err.message : "Error updating highlight status.",
        variant: "destructive",
      });
    } finally {
      setIsProcessingAction(false);
    }
  };

  // Handler for updating highlight
  const handleSaveEdit = async (
    highlightId: string,
    updates: { start_ms: number; end_ms: number; summary: string }
  ) => {
    const updated = await api.highlights.update(highlightId, updates);
    setHighlights((prev) => prev.map((h) => (h.id === highlightId ? updated : h)));
    toast({
      title: "Highlight Updated",
      description: "Boundary timestamps and summary have been saved.",
    });
  };

  // Computed filtered and sorted highlights
  const filteredHighlights = useMemo(() => {
    return highlights
      .filter((h) => {
        if (statusFilter !== "ALL" && h.status?.toUpperCase() !== statusFilter) {
          return false;
        }
        if (categoryFilter !== "ALL" && h.category !== categoryFilter) {
          return false;
        }
        return true;
      })
      .sort((a, b) => {
        if (sortBy === "rank") {
          return (a.rank || 999) - (b.rank || 999);
        }
        if (sortBy === "score") {
          return (b.composite_score || 0) - (a.composite_score || 0);
        }
        if (sortBy === "timestamp") {
          const aStart = a.start_ms ?? (a.start_time ? a.start_time * 1000 : 0);
          const bStart = b.start_ms ?? (b.start_time ? b.start_time * 1000 : 0);
          return aStart - bStart;
        }
        return 0;
      });
  }, [highlights, statusFilter, categoryFilter, sortBy]);

  // Statistics
  const stats = useMemo(() => {
    const total = highlights.length;
    const accepted = highlights.filter((h) => h.status?.toUpperCase() === "ACCEPTED").length;
    const rejected = highlights.filter((h) => h.status?.toUpperCase() === "REJECTED").length;
    const topScore = highlights.reduce(
      (max, h) => Math.max(max, h.composite_score || 0),
      0
    );
    return { total, accepted, rejected, topScore };
  }, [highlights]);

  if (!videoId) {
    return (
      <PageContainer title="AI Highlight Detection" description="Select a video to view highlights.">
        <EmptyState
          icon={<AlertCircle className="h-6 w-6 text-muted-foreground" />}
          title="No Video Specified"
          description="Please navigate to a video from your library to inspect or detect highlights."
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={video ? `AI Highlights: ${video.original_filename || video.filename}` : "AI Highlight Detection"}
      description={`Ranked candidate segments and explainable intelligence for video ${videoId}.`}
      action={
        <Button asChild variant="outline" size="sm" className="gap-2">
          <Link to={`/video/${videoId}`}>
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Video Workstation
          </Link>
        </Button>
      }
    >
      <div className="space-y-6">
        {/* Detection Engine & Filter Panel */}
        <HighlightDetectionPanel
          videoId={videoId}
          hasTranscript={Boolean(transcript && transcript.status === "COMPLETED")}
          activeJob={activeJob}
          onDetectRequested={handleDetect}
          onCancelJob={handleCancelJob}
          statusFilter={statusFilter}
          onStatusFilterChange={setStatusFilter}
          categoryFilter={categoryFilter}
          onCategoryFilterChange={setCategoryFilter}
          sortBy={sortBy}
          onSortByChange={setSortBy}
          stats={stats}
        />

        {/* Highlight Cards Grid */}
        {isLoading ? (
          <div className="flex items-center justify-center p-12">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : filteredHighlights.length === 0 ? (
          <EmptyState
            icon={<BarChart3 className="h-6 w-6 text-muted-foreground" />}
            title={highlights.length === 0 ? "No Highlights Detected" : "No Highlights Match Filter"}
            description={
              highlights.length === 0
                ? "Click 'Detect Highlights' to generate explainable candidate clips from the speech transcript."
                : "Try adjusting your status or category filters above."
            }
          />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {filteredHighlights.map((highlight) => (
              <HighlightCard
                key={highlight.id}
                highlight={highlight}
                onEdit={(h) => setEditingHighlight(h)}
                onAccept={handleAccept}
                onReject={handleReject}
                isProcessingAction={isProcessingAction}
              />
            ))}
          </div>
        )}
      </div>

      {/* Edit Timestamps & Summary Dialog */}
      <HighlightEditDialog
        highlight={editingHighlight}
        isOpen={Boolean(editingHighlight)}
        onClose={() => setEditingHighlight(null)}
        onSave={handleSaveEdit}
        videoDurationSeconds={video?.duration_seconds}
      />
    </PageContainer>
  );
};
