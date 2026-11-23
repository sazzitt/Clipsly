import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { FileText, ArrowLeft, Loader2, Sparkles } from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { Button } from "../../components/ui/button";
import { api } from "../../services/api";
import { useToast } from "../../hooks/useToast";
import { Transcript, Video, ProcessingJob } from "../../types/api";
import { TranscriptionPanel, TranscriptViewer } from "./components";

export const TranscriptViewerPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { toast } = useToast();

  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [video, setVideo] = useState<Video | null>(null);
  const [activeJob, setActiveJob] = useState<ProcessingJob | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showConfigPanel, setShowConfigPanel] = useState<boolean>(false);

  const fetchTranscriptData = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);

    try {
      // First try to fetch as transcript ID or video ID
      let t: Transcript | null = null;
      try {
        t = await api.transcripts.get(id);
        setTranscript(t);
      } catch {
        // Not found as transcript, maybe it's a video ID with no transcript yet
        t = null;
      }

      // Fetch corresponding video
      const videoId = t?.video_id || id;
      try {
        const v = await api.videos.get(videoId);
        setVideo(v);
      } catch (vErr) {
        console.warn("Could not load associated video record:", vErr);
      }

      // Check for active transcription jobs for this video
      try {
        const jobsRes = await api.jobs.list({ video_id: videoId });
        const runningJob = jobsRes.items.find(
          (j) =>
            j.job_type === "TRANSCRIPTION" &&
            (j.status === "processing" || j.status === "queued" || j.status === "transcribing")
        );
        setActiveJob(runningJob || null);
      } catch {
        // Ignored
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load transcript data.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchTranscriptData();
  }, [fetchTranscriptData]);

  // Poll for active job progress if one is executing
  useEffect(() => {
    if (!activeJob) return;

    const interval = setInterval(async () => {
      try {
        const job = await api.jobs.get(activeJob.id);
        if (job.status === "completed") {
          setActiveJob(null);
          toast({
            title: "Transcription Complete",
            description: "Speech-to-text processing finished successfully.",
            variant: "success",
          });
          fetchTranscriptData();
        } else if (job.status === "failed" || job.status === "cancelled") {
          setActiveJob(null);
          toast({
            title: job.status === "cancelled" ? "Job Cancelled" : "Transcription Failed",
            description: job.error_message || "Transcription job stopped.",
            variant: job.status === "cancelled" ? "info" : "error",
          });
          fetchTranscriptData();
        } else {
          setActiveJob(job);
        }
      } catch {
        // Ignored
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activeJob, fetchTranscriptData, toast]);

  const targetVideoId = video?.id || transcript?.video_id || id || "";

  return (
    <PageContainer
      title="Speech-to-Text Transcript"
      description={`Faster-Whisper local GPU transcription workspace for video ${targetVideoId ? targetVideoId.slice(0, 8) : ""}.`}
      action={
        <div className="flex items-center gap-2">
          {transcript && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowConfigPanel((prev) => !prev)}
              className="gap-1.5 text-xs"
              data-testid="toggle-retranscribe-panel-btn"
            >
              <Sparkles className="h-3.5 w-3.5 text-violet-400" />
              <span>{showConfigPanel ? "Hide Settings" : "Configure Pipeline"}</span>
            </Button>
          )}

          <Button asChild variant="outline" size="sm" className="gap-2">
            <Link to={targetVideoId ? `/video/${targetVideoId}` : "/videos"}>
              <ArrowLeft className="h-3.5 w-3.5" />
              Back to Video
            </Link>
          </Button>
        </div>
      }
    >
      {isLoading ? (
        <div className="p-16 text-center space-y-3" data-testid="transcript-loading">
          <Loader2 className="h-8 w-8 text-primary animate-spin mx-auto" />
          <p className="text-xs text-muted-foreground">Loading speech transcript and model metadata...</p>
        </div>
      ) : error ? (
        <div className="p-8 rounded-xl border border-red-500/30 bg-card/60 text-center space-y-3">
          <FileText className="h-8 w-8 text-red-400 mx-auto" />
          <h3 className="text-sm font-semibold text-foreground">Failed to Load Transcript</h3>
          <p className="text-xs text-muted-foreground">{error}</p>
          <Button variant="outline" size="sm" onClick={fetchTranscriptData}>
            Retry
          </Button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Show Configuration Panel when requested or if no transcript exists */}
          {(!transcript || showConfigPanel) && (
            <TranscriptionPanel
              videoId={targetVideoId}
              hasAudio={video?.has_audio !== false}
              audioAsset={video?.audio_asset}
              activeJob={activeJob}
              hasExistingTranscript={Boolean(transcript)}
              onTranscriptionStarted={(jobId) => {
                setActiveJob({
                  id: jobId,
                  video_id: targetVideoId,
                  job_type: "TRANSCRIPTION",
                  status: "queued",
                  current_step: "Transcription job queued...",
                  progress_percent: 0.0,
                  created_at: new Date().toISOString(),
                });
              }}
              onJobCancelled={() => {
                setActiveJob(null);
                fetchTranscriptData();
              }}
              onExtractAudioRequested={() => {
                if (targetVideoId) {
                  api.videos.extractAudio(targetVideoId).then(() => {
                    toast({
                      title: "Audio Extraction Queued",
                      description: "Extracting 16kHz WAV audio asset...",
                      variant: "info",
                    });
                    fetchTranscriptData();
                  });
                }
              }}
            />
          )}

          {/* Transcript Viewer */}
          {transcript ? (
            <TranscriptViewer
              transcript={transcript}
              onRetranscribeRequested={() => setShowConfigPanel(true)}
            />
          ) : !showConfigPanel ? (
            <div className="p-12 rounded-xl border border-dashed border-border bg-card/40 text-center space-y-3">
              <FileText className="h-8 w-8 text-muted-foreground mx-auto" />
              <h3 className="text-sm font-semibold text-foreground">No Transcript Available</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                No active speech transcript found for this video. You can run Faster-Whisper to transcribe dialogue and extract word timestamps.
              </p>
              <Button
                variant="default"
                size="sm"
                onClick={() => setShowConfigPanel(true)}
                className="bg-violet-600 hover:bg-violet-700 text-white text-xs gap-1.5"
              >
                <Sparkles className="h-3.5 w-3.5" />
                Configure and Start Transcription
              </Button>
            </div>
          ) : null}
        </div>
      )}
    </PageContainer>
  );
};
