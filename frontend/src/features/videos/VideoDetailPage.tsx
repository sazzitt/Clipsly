import React, { useCallback, useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  Video as VideoIcon,
  ArrowLeft,
  Activity,
  FileText,
  Sparkles,
  Film,
  HardDrive,
  Trash2,
  AlertCircle,
  Clock,
  Layers,
  RefreshCw,
  Monitor,
  Music,
  VolumeX,
  CheckCircle2,
  AlertTriangle,
  Compass,
  X,
} from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Skeleton } from "../../components/ui/skeleton";
import { ProcessingStatus, JobStatus } from "../../components/workstation/ProcessingStatus";
import { VideoPlayer } from "./components/VideoPlayer";
import { useToast } from "../../hooks/useToast";
import { api, ClipslyApiError } from "../../services/api";
import { Video, ProcessingJob, Transcript, Highlight, Clip } from "../../types/api";
import { DeleteConfirmationDialog, EntityStatusBadge } from "../../components/management";

type ActiveTab = "overview" | "history" | "transcript" | "highlights" | "clips";

function formatBytes(bytes: number): string {
  if (bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

function formatDuration(seconds: number): string {
  if (seconds <= 0) return "0s";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function formatBitrate(bps: number | null | undefined): string {
  if (!bps || bps <= 0) return "N/A";
  if (bps >= 1_000_000) {
    return `${(bps / 1_000_000).toFixed(2)} Mbps`;
  }
  return `${(bps / 1_000).toFixed(0)} kbps`;
}

export const VideoDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();

  const [activeTab, setActiveTab] = useState<ActiveTab>("overview");
  const [video, setVideo] = useState<Video | null>(null);
  const [jobs, setJobs] = useState<ProcessingJob[]>([]);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [highlights, setHighlights] = useState<Highlight[]>([]);
  const [clips, setClips] = useState<Clip[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshingMetadata, setIsRefreshingMetadata] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Deletion modal
  const [showDeleteModal, setShowDeleteModal] = useState<boolean>(false);
  const [purgeFiles, setPurgeFiles] = useState<boolean>(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  // Audio extraction state (Phase 14)
  const [activeAudioJobId, setActiveAudioJobId] = useState<string | null>(null);
  const [audioJob, setAudioJob] = useState<ProcessingJob | null>(null);
  const [selectedStreamIndex, setSelectedStreamIndex] = useState<number | undefined>(undefined);
  const [isExtractingAudio, setIsExtractingAudio] = useState<boolean>(false);
  const [isCancellingAudio, setIsCancellingAudio] = useState<boolean>(false);

  const loadVideoDetails = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);

    try {
      const v = await api.videos.get(id);
      setVideo(v);

      // Concurrently query related jobs, transcript, highlights, and clips
      const [jobsRes, transcriptRes, highlightsRes, clipsRes] = await Promise.allSettled([
        api.jobs.list({ video_id: id }),
        api.transcripts.get(id),
        api.highlights.list(id),
        api.clips.list({ video_id: id }),
      ]);

      if (jobsRes.status === "fulfilled") {
        setJobs(jobsRes.value.items);
        const runningAudio = jobsRes.value.items.find(
          (j) =>
            j.job_type === "AUDIO_EXTRACTION" &&
            (j.status === "QUEUED" ||
              j.status === "PROCESSING" ||
              j.status === "queued" ||
              j.status === "processing")
        );
        if (runningAudio) {
          setActiveAudioJobId(runningAudio.id);
          setAudioJob(runningAudio);
        }
      }
      if (transcriptRes.status === "fulfilled") {
        setTranscript(transcriptRes.value);
      }
      if (highlightsRes.status === "fulfilled") {
        setHighlights(highlightsRes.value);
      }
      if (clipsRes.status === "fulfilled") {
        setClips(clipsRes.value.items);
      }
    } catch (err: unknown) {
      if (err instanceof ClipslyApiError) {
        setError(err.detail);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to load video details.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadVideoDetails();
  }, [loadVideoDetails]);

  // Audio extraction job polling
  useEffect(() => {
    if (!activeAudioJobId) return;

    const interval = setInterval(async () => {
      try {
        const job = await api.jobs.get(activeAudioJobId);
        if (!job || !job.status) return;
        setAudioJob(job);
        const st = job.status.toUpperCase();
        if (st === "COMPLETED") {
          clearInterval(interval);
          setActiveAudioJobId(null);
          setAudioJob(null);
          toast.success("Audio Extraction Complete", "16kHz mono WAV asset generated and validated.");
          loadVideoDetails();
        } else if (st === "FAILED" || st === "CANCELLED") {
          clearInterval(interval);
          setActiveAudioJobId(null);
          setAudioJob(null);
          if (st === "FAILED") {
            toast.error("Audio Extraction Failed", job.error_message || "FFmpeg extraction error.");
          } else {
            toast.info("Audio Extraction Cancelled", "Job was cancelled.");
          }
          loadVideoDetails();
        }
      } catch {
        clearInterval(interval);
        setActiveAudioJobId(null);
        setAudioJob(null);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [activeAudioJobId, loadVideoDetails, toast]);

  const handleExtractAudio = async (force = false) => {
    if (!id || !video) return;
    setIsExtractingAudio(true);
    try {
      const res = await api.videos.extractAudio(id, {
        stream_index: selectedStreamIndex,
        force_reextract: force,
      });

      if (res.status === "COMPLETED" && res.audio_asset) {
        toast.success("Audio Asset Ready", "Using validated 16kHz mono WAV asset.");
        await loadVideoDetails();
      } else {
        setActiveAudioJobId(res.job_id);
        toast.info("Audio Extraction Started", "Extracting 16kHz mono WAV for local transcription...");
      }
    } catch (err: unknown) {
      const msg = err instanceof ClipslyApiError ? err.detail : "Failed to start audio extraction.";
      toast.error("Extraction Error", msg);
    } finally {
      setIsExtractingAudio(false);
    }
  };

  const handleCancelAudioExtraction = async () => {
    const targetJobId = activeAudioJobId || audioJob?.id;
    if (!targetJobId) return;
    setIsCancellingAudio(true);
    try {
      await api.jobs.cancel(targetJobId);
      toast.info("Cancellation Requested", "Terminating FFmpeg extraction process...");
    } catch (err: unknown) {
      const msg = err instanceof ClipslyApiError ? err.detail : "Failed to cancel audio extraction.";
      toast.error("Cancel Failed", msg);
    } finally {
      setIsCancellingAudio(false);
    }
  };

  const handleRefreshMetadata = async () => {
    if (!id) return;
    setIsRefreshingMetadata(true);
    try {
      const updated = await api.videos.refreshMetadata(id);
      setVideo(updated);
      toast.success(
        "Metadata Refreshed",
        "FFprobe re-extracted all video and audio stream parameters."
      );
    } catch (err: unknown) {
      const msg = err instanceof ClipslyApiError ? err.detail : "Failed to refresh metadata.";
      toast.error("Refresh Failed", msg);
    } finally {
      setIsRefreshingMetadata(false);
    }
  };

  const handleDelete = async () => {
    if (!id || !video) return;
    setIsDeleting(true);

    try {
      await api.videos.delete(id, purgeFiles);
      toast.success(
        "Video Removed",
        `${video.original_filename || video.filename} was successfully deleted.`
      );
      navigate("/videos");
    } catch (err: unknown) {
      const msg = err instanceof ClipslyApiError ? err.detail : "Failed to delete video.";
      toast.error("Deletion Failed", msg);
      setIsDeleting(false);
    }
  };

  const normalizeJobStatus = (status: string): JobStatus => {
    const s = status.toUpperCase();
    if (s === "PENDING" || s === "QUEUED") return "QUEUED";
    if (s === "PROCESSING" || s === "RUNNING") return "PROCESSING";
    if (s === "COMPLETED") return "COMPLETED";
    if (s === "FAILED") return "FAILED";
    if (s === "CANCELLED") return "CANCELLED";
    return "QUEUED";
  };

  if (isLoading) {
    return (
      <PageContainer>
        <div className="space-y-6" data-testid="video-detail-loading">
          <div className="flex items-center gap-4">
            <Skeleton className="h-9 w-24" />
            <Skeleton className="h-8 w-64" />
          </div>
          <div className="space-y-6">
            <Skeleton className="aspect-video w-full max-h-[480px] rounded-xl" />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Skeleton className="h-64 w-full rounded-xl" />
              <Skeleton className="h-64 w-full rounded-xl lg:col-span-2" />
            </div>
          </div>
        </div>
      </PageContainer>
    );
  }

  if (error || !video) {
    return (
      <PageContainer>
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-8 text-center space-y-4 max-w-lg mx-auto my-12">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/20 text-destructive mx-auto">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h2 className="text-base font-bold text-foreground">Video Not Found</h2>
          <p className="text-xs text-muted-foreground">{error || "The requested video does not exist in the database."}</p>
          <Button asChild variant="outline" size="sm">
            <Link to="/videos">
              <ArrowLeft className="h-3.5 w-3.5 mr-1.5" />
              Return to Video Library
            </Link>
          </Button>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={video.original_filename || video.filename}
      description={`Source Video UUID: ${video.id}`}
      action={
        <div className="flex items-center gap-2">
          <Button asChild variant="outline" size="sm" className="h-8 text-xs gap-1.5">
            <Link to="/videos">
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Back to Library</span>
            </Link>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefreshMetadata}
            disabled={isRefreshingMetadata}
            className="h-8 text-xs gap-1.5"
            data-testid="header-refresh-metadata-btn"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshingMetadata ? "animate-spin" : ""}`} />
            <span>Refresh Metadata</span>
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setShowDeleteModal(true)}
            className="h-8 text-xs gap-1.5"
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span>Delete Video</span>
          </Button>
        </div>
      }
    >
      {/* Tab Navigation */}
      <div className="flex items-center gap-2 border-b border-border/80 pb-2 overflow-x-auto select-none">
        <Button
          variant={activeTab === "overview" ? "default" : "ghost"}
          size="sm"
          onClick={() => setActiveTab("overview")}
          className="gap-1.5 h-8 text-xs"
        >
          <VideoIcon className="h-3.5 w-3.5" />
          <span>Technical Stream</span>
        </Button>

        <Button
          variant={activeTab === "history" ? "default" : "ghost"}
          size="sm"
          onClick={() => setActiveTab("history")}
          className="gap-1.5 h-8 text-xs"
        >
          <Activity className="h-3.5 w-3.5" />
          <span>Processing Jobs ({jobs.length})</span>
        </Button>

        <Button
          variant={activeTab === "transcript" ? "default" : "ghost"}
          size="sm"
          onClick={() => setActiveTab("transcript")}
          className="gap-1.5 h-8 text-xs"
        >
          <FileText className="h-3.5 w-3.5" />
          <span>Transcript</span>
        </Button>

        <Button
          variant={activeTab === "highlights" ? "default" : "ghost"}
          size="sm"
          onClick={() => setActiveTab("highlights")}
          className="gap-1.5 h-8 text-xs"
        >
          <Sparkles className="h-3.5 w-3.5" />
          <span>Highlights ({highlights.length})</span>
        </Button>

        <Button
          variant={activeTab === "clips" ? "default" : "ghost"}
          size="sm"
          onClick={() => setActiveTab("clips")}
          className="gap-1.5 h-8 text-xs"
        >
          <Film className="h-3.5 w-3.5" />
          <span>Clips ({clips.length})</span>
        </Button>
      </div>

      {/* Tab 1: Technical Overview & Preview */}
      {activeTab === "overview" && (
        <div className="space-y-6 pt-2">
          {/* Section A: Real Workstation Video Player */}
          <section className="space-y-2" aria-label="Video Preview Player">
            {video.file_exists ? (
              <VideoPlayer
                videoId={video.id}
                title={video.original_filename || video.filename}
                className="w-full max-h-[520px]"
              />
            ) : (
              <div className="rounded-xl border border-dashed border-amber-500/40 bg-amber-500/10 p-8 text-center space-y-3">
                <AlertTriangle className="h-8 w-8 text-amber-400 mx-auto" />
                <h3 className="text-sm font-semibold text-foreground">Source Video File Not Found on Disk</h3>
                <p className="text-xs text-muted-foreground max-w-md mx-auto">
                  The database contains metadata for this asset, but the underlying file is missing from local storage.
                </p>
              </div>
            )}
          </section>

          {/* Section E: Metadata Extraction Status & Sync Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl border border-border bg-card/60">
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground font-medium">Metadata Status:</span>
              {video.metadata_status === "COMPLETED" ? (
                <Badge variant="outline" className="gap-1 bg-emerald-500/10 text-emerald-400 border-emerald-500/30 font-mono text-[11px]">
                  <CheckCircle2 className="h-3 w-3" />
                  FFprobe Verified
                </Badge>
              ) : video.metadata_status === "FAILED" ? (
                <Badge variant="outline" className="gap-1 bg-destructive/10 text-destructive border-destructive/30 font-mono text-[11px]">
                  <AlertCircle className="h-3 w-3" />
                  Extraction Failed
                </Badge>
              ) : (
                <Badge variant="outline" className="gap-1 bg-blue-500/10 text-blue-400 border-blue-500/30 animate-pulse font-mono text-[11px]">
                  <RefreshCw className="h-3 w-3 animate-spin" />
                  Analyzing Streams
                </Badge>
              )}

              {video.metadata_extracted_at && (
                <span className="text-[11px] font-mono text-muted-foreground">
                  (Analyzed: {new Date(video.metadata_extracted_at).toLocaleTimeString()})
                </span>
              )}
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={handleRefreshMetadata}
              disabled={isRefreshingMetadata}
              className="h-7 text-xs gap-1.5"
              data-testid="refresh-metadata-btn"
            >
              <RefreshCw className={`h-3 w-3 ${isRefreshingMetadata ? "animate-spin" : ""}`} />
              <span>{isRefreshingMetadata ? "Analyzing..." : "Re-Extract Metadata"}</span>
            </Button>
          </div>

          {/* Section B: Overview & Quick Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
            <div className="p-3 rounded-xl border border-border bg-card/60 space-y-1">
              <span className="text-[11px] text-muted-foreground block">Container</span>
              <span className="text-sm font-bold font-mono text-foreground">
                {(video.container_format || video.filename.split(".").pop() || "N/A").toUpperCase()}
              </span>
            </div>

            <div className="p-3 rounded-xl border border-border bg-card/60 space-y-1">
              <span className="text-[11px] text-muted-foreground block">File Size</span>
              <span className="text-sm font-bold font-mono text-foreground">
                {formatBytes(video.file_size_bytes)}
              </span>
            </div>

            <div className="p-3 rounded-xl border border-border bg-card/60 space-y-1">
              <span className="text-[11px] text-muted-foreground block">Duration</span>
              <span className="text-sm font-bold font-mono text-foreground">
                {formatDuration(video.duration_seconds)}
              </span>
            </div>

            <div className="p-3 rounded-xl border border-border bg-card/60 space-y-1">
              <span className="text-[11px] text-muted-foreground block">Resolution</span>
              <span className="text-sm font-bold font-mono text-foreground">
                {video.width}x{video.height}
              </span>
            </div>

            <div className="p-3 rounded-xl border border-border bg-card/60 space-y-1">
              <span className="text-[11px] text-muted-foreground block">Orientation</span>
              <span className="text-sm font-bold font-mono text-foreground flex items-center gap-1">
                <Compass className="h-3 w-3 text-primary" />
                <span>{video.orientation ? video.orientation.charAt(0).toUpperCase() + video.orientation.slice(1) : "Landscape"}</span>
              </span>
            </div>

            <div className="p-3 rounded-xl border border-border bg-card/60 space-y-1">
              <span className="text-[11px] text-muted-foreground block">Total Bitrate</span>
              <span className="text-sm font-bold font-mono text-foreground">
                {formatBitrate(video.bitrate)}
              </span>
            </div>
          </div>

          {/* Technical Deep Dive: Video & Audio Streams */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Section C: Video Stream Technical Details */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Monitor className="h-4 w-4 text-primary" />
                  Stream Characteristics (FFprobe Verified)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs font-mono">
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                    <span className="text-muted-foreground block text-[11px]">Codec</span>
                    <span className="text-foreground font-semibold">{video.video_codec}</span>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                    <span className="text-muted-foreground block text-[11px]">Profile</span>
                    <span className="text-foreground font-semibold">{video.video_codec_profile || "Main"}</span>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                    <span className="text-muted-foreground block text-[11px]">Frame Rate</span>
                    <span className="text-foreground font-semibold">{video.fps.toFixed(2)} fps</span>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                    <span className="text-muted-foreground block text-[11px]">Pixel Format</span>
                    <span className="text-foreground font-semibold">{video.pixel_format || "yuv420p"}</span>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                    <span className="text-muted-foreground block text-[11px]">Bit Depth</span>
                    <span className="text-foreground font-semibold">{video.bit_depth ? `${video.bit_depth}-bit` : "8-bit"}</span>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                    <span className="text-muted-foreground block text-[11px]">Rotation</span>
                    <span className="text-foreground font-semibold">{video.rotation || 0}°</span>
                  </div>
                </div>

                <div className="pt-2 border-t border-border/40 text-xs text-muted-foreground space-y-2">
                  <div className="flex items-center justify-between">
                    <span>Aspect Ratio:</span>
                    <span className="font-mono font-semibold text-foreground">{video.aspect_ratio}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Video Stream Bitrate:</span>
                    <span className="font-mono font-semibold text-foreground">{formatBitrate(video.video_bitrate)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Section D: Audio Stream Technical Details */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Music className="h-4 w-4 text-emerald-400" />
                  Audio Stream Characteristics
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {video.has_audio !== false && Boolean(video.audio_codec) ? (
                  <>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs font-mono">
                      <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                        <span className="text-muted-foreground block text-[11px]">Codec</span>
                        <span className="text-foreground font-semibold">{video.audio_codec}</span>
                      </div>
                      <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                        <span className="text-muted-foreground block text-[11px]">Sample Rate</span>
                        <span className="text-foreground font-semibold">
                          {video.audio_sample_rate ? `${video.audio_sample_rate} Hz` : "48000 Hz"}
                        </span>
                      </div>
                      <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                        <span className="text-muted-foreground block text-[11px]">Channels</span>
                        <span className="text-foreground font-semibold">
                          {video.audio_channels === 1 ? "1 (Mono)" : `${video.audio_channels ?? 2} (Stereo)`}
                        </span>
                      </div>
                      <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                        <span className="text-muted-foreground block text-[11px]">Channel Layout</span>
                        <span className="text-foreground font-semibold">{video.channel_layout || "stereo"}</span>
                      </div>
                      <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1 sm:col-span-2">
                        <span className="text-muted-foreground block text-[11px]">Audio Bitrate</span>
                        <span className="text-foreground font-semibold">{formatBitrate(video.audio_bitrate)}</span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-border/40 text-xs text-muted-foreground space-y-2">
                      <div className="flex items-center justify-between">
                        <span>Audio Stream Status:</span>
                        <span className="font-mono text-emerald-400 font-medium">Active & Decodable</span>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="p-6 rounded-xl border border-dashed border-border bg-secondary/30 text-center space-y-2">
                    <VolumeX className="h-6 w-6 text-muted-foreground mx-auto" />
                    <h4 className="text-xs font-semibold text-foreground">No Audio Stream Detected</h4>
                    <p className="text-[11px] text-muted-foreground max-w-xs mx-auto">
                      This video does not contain an audio track. Faster-Whisper transcription and speech-based AI highlight analysis will be skipped for this asset.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Section: FFmpeg Audio Preprocessing Pipeline (Phase 14) */}
          <Card className="border-border bg-card/60" data-testid="audio-extraction-card">
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Music className="h-4 w-4 text-emerald-400" />
                FFmpeg Audio Preprocessing (Phase 14: 16kHz Mono WAV)
              </CardTitle>
              {video.audio_asset && video.audio_asset.status === "COMPLETED" && !activeAudioJobId && (
                <Badge variant="outline" className="gap-1 bg-emerald-500/10 text-emerald-400 border-emerald-500/30 font-mono text-[11px]" data-testid="audio-asset-ready-badge">
                  <CheckCircle2 className="h-3 w-3" />
                  Validated WAV Asset
                </Badge>
              )}
            </CardHeader>
            <CardContent className="space-y-4">
              {activeAudioJobId && audioJob ? (
                <div className="space-y-3 p-4 rounded-xl border border-primary/30 bg-primary/5" data-testid="audio-extraction-progress">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <RefreshCw className="h-4 w-4 text-primary animate-spin" />
                      <span className="text-xs font-semibold text-foreground">
                        Extracting 16kHz Mono PCM Audio
                      </span>
                    </div>
                    <span className="text-xs font-mono font-semibold text-primary">
                      {audioJob.progress_percent.toFixed(0)}%
                    </span>
                  </div>

                  <div className="w-full bg-secondary rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-primary h-2 rounded-full transition-all duration-300"
                      style={{ width: `${Math.max(5, audioJob.progress_percent)}%` }}
                    />
                  </div>

                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span className="font-mono text-[11px] truncate max-w-md">
                      {audioJob.current_step || "Processing audio stream..."}
                    </span>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={handleCancelAudioExtraction}
                      disabled={isCancellingAudio}
                      className="h-7 text-xs gap-1"
                      data-testid="cancel-audio-btn"
                    >
                      <X className="h-3 w-3" />
                      <span>{isCancellingAudio ? "Cancelling..." : "Cancel Extraction"}</span>
                    </Button>
                  </div>
                </div>
              ) : video.audio_asset && video.audio_asset.status === "COMPLETED" ? (
                <div className="space-y-4" data-testid="audio-asset-details">
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs font-mono">
                    <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                      <span className="text-muted-foreground block text-[11px]">Format / Container</span>
                      <span className="text-foreground font-semibold">WAV (RIFF)</span>
                    </div>
                    <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                      <span className="text-muted-foreground block text-[11px]">Codec</span>
                      <span className="text-foreground font-semibold">{video.audio_asset.codec}</span>
                    </div>
                    <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                      <span className="text-muted-foreground block text-[11px]">Sample Rate</span>
                      <span className="text-emerald-400 font-semibold">{video.audio_asset.sample_rate.toLocaleString()} Hz</span>
                    </div>
                    <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                      <span className="text-muted-foreground block text-[11px]">Channels</span>
                      <span className="text-emerald-400 font-semibold">1 (Mono)</span>
                    </div>
                    <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                      <span className="text-muted-foreground block text-[11px]">Bit Depth</span>
                      <span className="text-foreground font-semibold">{video.audio_asset.bit_depth}-bit</span>
                    </div>
                    <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                      <span className="text-muted-foreground block text-[11px]">Duration</span>
                      <span className="text-foreground font-semibold">{formatDuration(video.audio_asset.duration_seconds)}</span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-border/40 text-xs">
                    <div className="text-muted-foreground flex items-center gap-2">
                      <HardDrive className="h-3.5 w-3.5 text-zinc-400" />
                      <span>Audio Asset Size: <strong className="text-foreground font-mono">{formatBytes(video.audio_asset.file_size_bytes)}</strong></span>
                      <span className="text-zinc-600">|</span>
                      <span>Filename: <strong className="text-foreground font-mono">{video.audio_asset.filename}</strong></span>
                    </div>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExtractAudio(true)}
                      disabled={isExtractingAudio}
                      className="h-7 text-xs gap-1.5"
                      data-testid="reextract-audio-btn"
                    >
                      <RefreshCw className={`h-3 w-3 ${isExtractingAudio ? "animate-spin" : ""}`} />
                      <span>{isExtractingAudio ? "Extracting..." : "Re-Extract Audio (Force)"}</span>
                    </Button>
                  </div>
                </div>
              ) : video.has_audio === false || !video.audio_codec ? (
                <div className="p-4 rounded-xl border border-dashed border-border bg-secondary/20 text-center space-y-1.5" data-testid="no-audio-notice">
                  <VolumeX className="h-5 w-5 text-muted-foreground mx-auto" />
                  <p className="text-xs font-medium text-foreground">No Audio Streams Available</p>
                  <p className="text-[11px] text-muted-foreground max-w-md mx-auto">
                    This video lacks an audio track. Audio extraction and speech-to-text processing cannot be performed on this asset.
                  </p>
                </div>
              ) : (
                <div className="space-y-4" data-testid="audio-extract-prompt">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Convert this video's audio into the standardized <strong>16,000 Hz, 16-bit mono PCM WAV</strong> format required for high-accuracy local Faster-Whisper transcription.
                  </p>

                  {/* Audio Stream Selection if multiple streams exist */}
                  {video.audio_streams && video.audio_streams.length > 1 && (
                    <div className="p-3 rounded-lg border border-border bg-secondary/30 space-y-2">
                      <span className="text-xs font-medium text-foreground block">Select Target Audio Stream:</span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                        {video.audio_streams.map((stream) => (
                          <label
                            key={stream.index}
                            className={`flex items-center gap-2 p-2 rounded border cursor-pointer transition-colors ${
                              (selectedStreamIndex === undefined && stream.is_default) || selectedStreamIndex === stream.index
                                ? "border-primary bg-primary/10 text-foreground"
                                : "border-border/60 bg-card/60 text-muted-foreground hover:bg-card"
                            }`}
                          >
                            <input
                              type="radio"
                              name="audio_stream"
                              value={stream.index}
                              checked={(selectedStreamIndex === undefined && stream.is_default) || selectedStreamIndex === stream.index}
                              onChange={() => setSelectedStreamIndex(stream.index)}
                              className="sr-only"
                            />
                            <div className="flex-1 font-mono text-[11px]">
                              <span>Stream #{stream.index}: {stream.codec_name} ({stream.channels}ch, {stream.sample_rate}Hz)</span>
                              {stream.language && <span className="text-muted-foreground ml-1">[{stream.language}]</span>}
                              {stream.is_default && <span className="text-primary ml-1 font-semibold">(Default)</span>}
                            </div>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] text-muted-foreground font-mono">Target: 16kHz mono WAV (pcm_s16le)</span>
                    <Button
                      variant="default"
                      size="sm"
                      onClick={() => handleExtractAudio(false)}
                      disabled={isExtractingAudio || !video.file_exists}
                      className="h-8 text-xs gap-1.5"
                      data-testid="extract-audio-btn"
                    >
                      <Music className="h-3.5 w-3.5" />
                      <span>{isExtractingAudio ? "Initializing..." : "Extract & Preprocess Audio"}</span>
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Storage & Local Artifacts Summary */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-1">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <HardDrive className="h-4 w-4 text-zinc-400" />
                  Storage Integrity
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">SSD Status:</span>
                  <span className={video.file_exists ? "text-emerald-400 font-medium" : "text-amber-400 font-medium"}>
                    {video.file_exists ? "File Verified on SSD" : "File Missing / Moved"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Storage Disk:</span>
                  <span className="font-mono text-zinc-300 text-[11px]">
                    {video.storage_label || "Local Workstation NVMe"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Imported:</span>
                  <span className="font-mono text-foreground">
                    {new Date(video.created_at).toLocaleDateString([], {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Layers className="h-4 w-4 text-emerald-400" />
                  Local Artifacts Summary
                </CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3 rounded-lg bg-card/70 border border-border">
                  <span className="text-muted-foreground block">Jobs Executed</span>
                  <span className="text-base font-bold text-foreground font-mono">
                    {video.processing_jobs_count ?? jobs.length}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-card/70 border border-border">
                  <span className="text-muted-foreground block">Transcripts</span>
                  <span className="text-base font-bold text-foreground font-mono">
                    {video.transcripts_count ?? (transcript ? 1 : 0)}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-card/70 border border-border">
                  <span className="text-muted-foreground block">AI Highlights</span>
                  <span className="text-base font-bold text-foreground font-mono">
                    {video.highlights_count ?? highlights.length}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-card/70 border border-border">
                  <span className="text-muted-foreground block">Saved Clips</span>
                  <span className="text-base font-bold text-foreground font-mono">
                    {video.clips_count ?? clips.length}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Tab 2: Processing History */}
      {activeTab === "history" && (
        <div className="space-y-4 pt-2">
          {jobs.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-card/30 p-8 text-center space-y-2">
              <Activity className="h-6 w-6 text-muted-foreground mx-auto" />
              <h3 className="text-sm font-semibold text-foreground">No Processing Jobs Recorded</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                No background tasks have been queued or run for this video. Tasks appear here when audio is extracted, Whisper transcribes audio, or highlights are calculated.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {jobs.map((job) => (
                <div key={job.id} className="p-4 rounded-xl border border-border bg-card space-y-2">
                  <div className="flex items-center justify-between text-xs text-muted-foreground font-mono">
                    <span>Job ID: {job.id}</span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {new Date(job.created_at).toLocaleTimeString()}
                    </span>
                  </div>

                  <ProcessingStatus
                    jobType={job.job_type}
                    status={normalizeJobStatus(job.status)}
                    progressPercent={job.progress_percent}
                    currentStep={job.current_step}
                    errorMessage={job.error_message}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Transcript */}
      {activeTab === "transcript" && (
        <div className="pt-2">
          {transcript ? (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <FileText className="h-4 w-4 text-primary" />
                    Generated Transcript
                  </CardTitle>
                  <div className="flex items-center gap-3 text-xs font-mono text-muted-foreground">
                    <span>Language: {transcript.language || "auto"}</span>
                    <span>Words: {transcript.word_count}</span>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="p-4 rounded-lg bg-secondary/30 border border-border font-sans text-xs leading-relaxed text-foreground max-h-96 overflow-y-auto">
                  {transcript.full_text || "No transcript text available."}
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="rounded-xl border border-dashed border-border bg-card/30 p-8 text-center space-y-2">
              <FileText className="h-6 w-6 text-muted-foreground mx-auto" />
              <h3 className="text-sm font-semibold text-foreground">No Transcript Available</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                {video.has_audio
                  ? "This video has not yet been processed with local Faster-Whisper transcription. Audio transcription will be introduced in Phase 14."
                  : "This video has no audio track, so no transcript can be generated."}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Highlights */}
      {activeTab === "highlights" && (
        <div className="pt-2">
          {highlights.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-card/30 p-8 text-center space-y-2">
              <Sparkles className="h-6 w-6 text-muted-foreground mx-auto" />
              <h3 className="text-sm font-semibold text-foreground">No Highlights Detected</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                AI highlight candidate detection has not been executed on this asset yet.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {highlights.map((h) => {
                const startSec = h.start_time ?? (h.start_ms ? h.start_ms / 1000 : 0);
                const endSec = h.end_time ?? (h.end_ms ? h.end_ms / 1000 : 0);
                return (
                  <div key={h.id} className="p-4 rounded-xl border border-border bg-card space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-foreground truncate">
                        {h.hook_sentence || h.summary || `Highlight #${h.rank || 1}`}
                      </span>
                      <span className="font-mono text-primary font-bold">
                        Score: {(h.composite_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {h.summary || h.explanation || "No description available."}
                    </p>
                    <div className="flex items-center justify-between text-[11px] font-mono text-zinc-400 pt-2 border-t border-border/50">
                      <span>
                        {formatDuration(startSec)} - {formatDuration(endSec)}
                      </span>
                      <span>Duration: {formatDuration(Math.max(0, endSec - startSec))}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Clips */}
      {activeTab === "clips" && (
        <div className="pt-2">
          {clips.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-card/30 p-8 text-center space-y-2">
              <Film className="h-6 w-6 text-muted-foreground mx-auto" />
              <h3 className="text-sm font-semibold text-foreground">No Saved Clips</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                No short-form vertical or horizontal clips have been created from this video yet.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {clips.map((clip) => (
                <div key={clip.id} className="p-4 rounded-xl border border-border bg-card space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-foreground truncate">{clip.title}</span>
                    <EntityStatusBadge status={clip.status} />
                  </div>
                  <div className="text-[11px] font-mono text-muted-foreground flex items-center justify-between">
                    <span>Ratio: {clip.aspect_ratio_mode}</span>
                    <span>
                      {formatDuration(clip.start_ms / 1000)} - {formatDuration(clip.end_ms / 1000)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmationDialog
        isOpen={showDeleteModal}
        onOpenChange={setShowDeleteModal}
        title="Delete Source Video"
        entityName={video.original_filename || video.filename}
        consequences="This will delete the database record and cascade removal of all associated audio transcripts, AI highlights, and draft clips."
        showPurgeFilesOption={true}
        purgeFilesChecked={purgeFiles}
        onPurgeFilesToggle={setPurgeFiles}
        purgeFilesLabel="Also permanently delete source video file from SSD storage"
        onConfirm={handleDelete}
        isDeleting={isDeleting}
      />
    </PageContainer>
  );
};
