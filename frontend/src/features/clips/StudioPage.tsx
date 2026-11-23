import React, { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Scissors,
  ArrowLeft,
  Type,
  Download,
  RotateCcw,
  AlertCircle,
  Loader2,
  StopCircle,
  FileVideo,
} from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Skeleton } from "../../components/ui/skeleton";
import { Progress } from "../../components/ui/progress";
import { DisabledFeatureBadge } from "../../components/common/DisabledFeatureBadge";
import { EntityStatusBadge } from "../../components/management";
import { api, ClipslyApiError } from "../../services/api";
import { useToast } from "../../hooks/useToast";
import { Clip, ProcessingJob } from "../../types/api";
import { GenerateClipModal } from "./components/GenerateClipModal";

function formatBytes(bytes?: number | null): string {
  if (!bytes || bytes <= 0) return "N/A";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

export const StudioPage: React.FC = () => {
  const { clipId } = useParams<{ clipId: string }>();
  const { toast } = useToast();

  const [clip, setClip] = useState<Clip | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isPlaybackError, setIsPlaybackError] = useState<boolean>(false);
  const [playbackErrorMessage, setPlaybackErrorMessage] = useState<string | null>(null);

  // Active generation tracking
  const [activeJob, setActiveJob] = useState<ProcessingJob | null>(null);
  const [isCancelling, setIsCancelling] = useState<boolean>(false);
  const [showRegenerateModal, setShowRegenerateModal] = useState<boolean>(false);

  const fetchClip = useCallback(async () => {
    if (!clipId) return;
    setIsLoading(true);
    setError(null);
    setIsPlaybackError(false);

    try {
      const data = await api.clips.get(clipId);
      setClip(data);

      // If clip is in progress, find active job
      if (data.status === "QUEUED" || data.status === "PROCESSING") {
        const jobs = await api.jobs.list({ video_id: data.video_id, limit: 10 });
        const matchingJob = jobs.items.find(
          (j) =>
            j.job_type === "CLIP_GENERATION" &&
            (j.status === "QUEUED" || j.status === "PROCESSING")
        );
        if (matchingJob) {
          setActiveJob(matchingJob);
        }
      }
    } catch (err: unknown) {
      const msg =
        err instanceof ClipslyApiError
          ? err.detail
          : err instanceof Error
          ? err.message
          : "Failed to load clip details.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [clipId]);

  useEffect(() => {
    fetchClip();
  }, [fetchClip]);

  // Polling if clip is in active generation
  useEffect(() => {
    if (!clip || (clip.status !== "QUEUED" && clip.status !== "PROCESSING")) {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const updated = await api.clips.get(clip.id);
        setClip(updated);

        if (updated.status === "COMPLETED") {
          toast({
            title: "Clip Generated",
            description: "Vertical 9:16 clip is ready for preview.",
          });
        } else if (updated.status === "FAILED") {
          toast({
            title: "Generation Failed",
            description: updated.error_message || "Video rendering failed.",
            variant: "destructive",
          });
        }

        // Poll associated job for progress %
        const jobs = await api.jobs.list({ video_id: updated.video_id, limit: 5 });
        const runningJob = jobs.items.find((j) => j.job_type === "CLIP_GENERATION");
        if (runningJob) {
          setActiveJob(runningJob);
        }
      } catch (err) {
        console.warn("Polling error in Studio:", err);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [clip, toast]);

  // Cancel generation
  const handleCancelGeneration = async () => {
    if (!clipId) return;
    setIsCancelling(true);
    try {
      await api.clips.cancel(clipId);
      toast({
        title: "Cancelled",
        description: "Clip generation was cancelled.",
      });
      fetchClip();
    } catch (err: unknown) {
      const msg = err instanceof ClipslyApiError ? err.detail : "Failed to cancel clip.";
      toast({
        title: "Cancellation Error",
        description: msg,
        variant: "destructive",
      });
    } finally {
      setIsCancelling(false);
    }
  };

  const streamUrl = clipId ? api.clips.getStreamUrl(clipId) : "";
  const downloadUrl = clipId ? api.clips.getDownloadUrl(clipId) : "";

  return (
    <PageContainer
      title={clip ? `Studio: ${clip.title}` : `Studio: ${clipId || "Draft"}`}
      description="Vertical 9:16 preview player, stream verification, and export downloads."
      action={
        <div className="flex items-center gap-2">
          {clip && clip.status === "COMPLETED" && (
            <Button asChild variant="default" size="sm" className="gap-1.5 h-8 text-xs">
              <a href={downloadUrl} download={clip.output_filename || `${clip.title}.mp4`}>
                <Download className="h-3.5 w-3.5" />
                <span>Download MP4</span>
              </a>
            </Button>
          )}

          <Button asChild variant="outline" size="sm" className="gap-2 h-8 text-xs">
            <Link to="/clips">
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Back to Clips</span>
            </Link>
          </Button>
        </div>
      }
    >
      {isLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <Skeleton className="h-[520px] w-full rounded-xl" />
          </div>
          <div>
            <Skeleton className="h-[520px] w-full rounded-xl" />
          </div>
        </div>
      ) : error ? (
        <Card className="p-8 text-center border-destructive/30 bg-destructive/10 space-y-3">
          <AlertCircle className="h-8 w-8 text-destructive mx-auto" />
          <h3 className="text-sm font-semibold text-destructive">Failed to Load Clip</h3>
          <p className="text-xs text-muted-foreground">{error}</p>
          <Button onClick={fetchClip} variant="outline" size="sm" className="text-xs mt-2">
            <RotateCcw className="h-3 w-3 mr-1.5" />
            Retry
          </Button>
        </Card>
      ) : !clip ? (
        <Card className="p-8 text-center space-y-2">
          <AlertCircle className="h-6 w-6 text-muted-foreground mx-auto" />
          <h3 className="text-sm font-semibold text-foreground">Clip Not Found</h3>
          <p className="text-xs text-muted-foreground">The requested clip ID does not exist.</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: 9:16 Vertical Preview Player */}
          <div className="lg:col-span-2 space-y-4">
            <Card className="p-6 bg-black/60 border-border/80 flex flex-col items-center justify-center min-h-[520px]">
              {clip.status === "COMPLETED" ? (
                <div className="w-full flex flex-col items-center justify-center space-y-3">
                  {/* 9:16 Vertical Aspect Canvas Container */}
                  <div className="relative w-full max-w-[340px] aspect-[9/16] bg-black rounded-xl overflow-hidden shadow-2xl border border-zinc-800 flex items-center justify-center">
                    <video
                      key={streamUrl}
                      controls
                      playsInline
                      preload="metadata"
                      className="w-full h-full object-contain"
                      data-testid="clip-video-player"
                      onError={(e) => {
                        console.error("Clip video playback error:", e);
                        setIsPlaybackError(true);
                        setPlaybackErrorMessage("Failed to decode vertical video stream.");
                      }}
                    >
                      <source src={streamUrl} type="video/mp4" />
                      Your browser does not support HTML5 MP4 video playback.
                    </video>

                    {isPlaybackError && (
                      <div className="absolute inset-0 bg-black/85 flex flex-col items-center justify-center p-4 text-center space-y-2 z-10">
                        <AlertCircle className="h-6 w-6 text-rose-400" />
                        <p className="text-xs font-semibold text-rose-300">Playback Error</p>
                        <p className="text-[11px] text-zinc-400 leading-normal">
                          {playbackErrorMessage || "Unable to stream vertical MP4 from local server."}
                        </p>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center justify-between w-full max-w-[340px] px-1 text-xs text-muted-foreground">
                    <span className="font-mono text-[11px]">9:16 • {clip.width || 1080}x{clip.height || 1920}</span>
                    <Badge variant="outline" className="text-[10px] uppercase font-mono">
                      {clip.conversion_mode || clip.aspect_ratio_mode}
                    </Badge>
                  </div>
                </div>
              ) : clip.status === "QUEUED" || clip.status === "PROCESSING" ? (
                /* In-Progress State */
                <div className="w-full max-w-md p-6 rounded-xl border border-border bg-card/70 text-center space-y-4">
                  <div className="flex justify-center">
                    <div className="p-3 rounded-full bg-primary/10 text-primary">
                      <Loader2 className="h-8 w-8 animate-spin" />
                    </div>
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">
                      Rendering 9:16 Vertical Video...
                    </h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      {activeJob?.current_step || "FFmpeg slicing and aspect ratio conversion in progress."}
                    </p>
                  </div>

                  <div className="space-y-1.5 text-left">
                    <div className="flex justify-between text-xs font-mono text-muted-foreground">
                      <span>Encoding Progress</span>
                      <span>{Math.round(activeJob?.progress_percent || 0)}%</span>
                    </div>
                    <Progress value={activeJob?.progress_percent || 0} className="h-2" />
                  </div>

                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={handleCancelGeneration}
                    disabled={isCancelling}
                    className="gap-1.5 text-xs"
                  >
                    {isCancelling ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <StopCircle className="h-3.5 w-3.5" />
                    )}
                    <span>Cancel Encoding</span>
                  </Button>
                </div>
              ) : clip.status === "FAILED" ? (
                /* Failed State */
                <div className="w-full max-w-md p-6 rounded-xl border border-rose-500/30 bg-rose-500/10 text-center space-y-3">
                  <AlertCircle className="h-8 w-8 text-rose-400 mx-auto" />
                  <h3 className="text-sm font-semibold text-rose-300">Conversion Failed</h3>
                  <p className="text-xs text-zinc-400">
                    {clip.error_message || "The FFmpeg subprocess encountered an error while encoding."}
                  </p>
                  <Button
                    onClick={() => setShowRegenerateModal(true)}
                    variant="outline"
                    size="sm"
                    className="gap-1.5 text-xs mt-2"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    <span>Try Again</span>
                  </Button>
                </div>
              ) : clip.status === "CANCELLED" ? (
                /* Cancelled State */
                <div className="w-full max-w-md p-6 rounded-xl border border-border bg-card/70 text-center space-y-3">
                  <StopCircle className="h-8 w-8 text-amber-400 mx-auto" />
                  <h3 className="text-sm font-semibold text-foreground">Generation Cancelled</h3>
                  <p className="text-xs text-muted-foreground">
                    This clip generation job was stopped by the user.
                  </p>
                  <Button
                    onClick={() => setShowRegenerateModal(true)}
                    variant="outline"
                    size="sm"
                    className="gap-1.5 text-xs mt-2"
                  >
                    <Scissors className="h-3.5 w-3.5" />
                    <span>Re-Generate Clip</span>
                  </Button>
                </div>
              ) : (
                /* Draft / Unrendered State */
                <div className="w-full max-w-md p-8 rounded-xl border border-dashed border-border text-center space-y-3">
                  <Scissors className="h-8 w-8 text-primary mx-auto" />
                  <h3 className="text-sm font-semibold text-foreground">Unrendered Draft Clip</h3>
                  <p className="text-xs text-muted-foreground">
                    This clip configuration has not been rendered into a physical 9:16 video yet.
                  </p>
                  <Button
                    onClick={() => setShowRegenerateModal(true)}
                    size="sm"
                    className="gap-1.5 text-xs mt-2 bg-primary text-primary-foreground"
                  >
                    <Scissors className="h-3.5 w-3.5" />
                    <span>Render 9:16 Video</span>
                  </Button>
                </div>
              )}
            </Card>
          </div>

          {/* Right Column: Metadata & Specifications Panel */}
          <div className="space-y-4">
            {/* Stream & Encoding Specifications Card */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileVideo className="h-4 w-4 text-primary" />
                    <CardTitle className="text-sm">Clip Specifications</CardTitle>
                  </div>
                  <EntityStatusBadge status={clip.status} />
                </div>
                <CardDescription>
                  Verified stream characteristics probed by FFprobe.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                <div className="grid grid-cols-2 gap-2 text-muted-foreground font-mono">
                  <div className="p-2 rounded bg-secondary/30 border border-border/50 space-y-1">
                    <span className="text-[10px] uppercase text-zinc-500">Resolution</span>
                    <p className="text-foreground font-semibold">
                      {clip.width && clip.height ? `${clip.width} × ${clip.height}` : "1080 × 1920"}
                    </p>
                  </div>

                  <div className="p-2 rounded bg-secondary/30 border border-border/50 space-y-1">
                    <span className="text-[10px] uppercase text-zinc-500">Aspect Ratio</span>
                    <p className="text-foreground font-semibold">9:16 Vertical</p>
                  </div>

                  <div className="p-2 rounded bg-secondary/30 border border-border/50 space-y-1">
                    <span className="text-[10px] uppercase text-zinc-500">Frame Rate</span>
                    <p className="text-foreground font-semibold">
                      {clip.fps ? `${clip.fps.toFixed(0)} FPS` : "30 FPS"}
                    </p>
                  </div>

                  <div className="p-2 rounded bg-secondary/30 border border-border/50 space-y-1">
                    <span className="text-[10px] uppercase text-zinc-500">Video Codec</span>
                    <p className="text-foreground font-semibold uppercase">
                      {clip.video_codec || "H.264"}
                    </p>
                  </div>

                  <div className="p-2 rounded bg-secondary/30 border border-border/50 space-y-1">
                    <span className="text-[10px] uppercase text-zinc-500">Audio Codec</span>
                    <p className="text-foreground font-semibold uppercase">
                      {clip.audio_codec || "None"}
                    </p>
                  </div>

                  <div className="p-2 rounded bg-secondary/30 border border-border/50 space-y-1">
                    <span className="text-[10px] uppercase text-zinc-500">File Size</span>
                    <p className="text-foreground font-semibold">
                      {formatBytes(clip.file_size_bytes)}
                    </p>
                  </div>
                </div>

                <div className="pt-2 border-t border-border/50 space-y-1.5 font-mono text-[11px]">
                  <div className="flex justify-between text-muted-foreground">
                    <span>Duration:</span>
                    <span className="text-foreground font-semibold">
                      {(clip.duration_ms / 1000).toFixed(1)}s ({clip.duration_ms} ms)
                    </span>
                  </div>

                  <div className="flex justify-between text-muted-foreground">
                    <span>Conversion Mode:</span>
                    <Badge variant="outline" className="text-[10px]">
                      {clip.conversion_mode || clip.aspect_ratio_mode}
                    </Badge>
                  </div>

                  {clip.encoding_backend && (
                    <div className="flex justify-between text-muted-foreground">
                      <span>Encoder Backend:</span>
                      <Badge variant="secondary" className="text-[10px] font-mono">
                        {clip.encoding_backend}
                      </Badge>
                    </div>
                  )}

                  {clip.output_filename && (
                    <div className="flex justify-between text-muted-foreground truncate">
                      <span>Output File:</span>
                      <span className="text-foreground truncate max-w-[160px]" title={clip.output_filename}>
                        {clip.output_filename}
                      </span>
                    </div>
                  )}
                </div>

                {clip.status === "COMPLETED" && (
                  <div className="pt-2">
                    <Button asChild size="sm" className="w-full gap-2 text-xs">
                      <a href={downloadUrl} download={clip.output_filename || `${clip.title}.mp4`}>
                        <Download className="h-3.5 w-3.5" />
                        <span>Download MP4 Video</span>
                      </a>
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Subtitles Roadmap Notice Card */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <Type className="h-4 w-4 text-amber-400" />
                  <CardTitle className="text-sm">Subtitles & Captions</CardTitle>
                </div>
                <CardDescription>
                  Whisper word-synchronized karaoke captioning.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <DisabledFeatureBadge phase="Phase 18" featureName="Subtitle & Caption Engine" />
                <p className="text-[11px] text-muted-foreground leading-relaxed pt-1">
                  ASS subtitle compilation, font styling presets, and word-level karaoke animations activate in Phase 18.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Re-Generate / Edit Modal */}
      {clip && (
        <GenerateClipModal
          isOpen={showRegenerateModal}
          onClose={() => setShowRegenerateModal(false)}
          videoId={clip.video_id}
          highlightId={clip.highlight_id}
          initialTitle={clip.title}
          initialStartMs={clip.start_ms}
          initialEndMs={clip.end_ms}
          videoTitle={clip.video_filename || undefined}
          onClipGenerated={() => fetchClip()}
        />
      )}
    </PageContainer>
  );
};
