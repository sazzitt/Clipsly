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
} from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Skeleton } from "../../components/ui/skeleton";
import { VideoThumbnail } from "../../components/workstation/VideoThumbnail";
import { ProcessingStatus, JobStatus } from "../../components/workstation/ProcessingStatus";
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
  const [error, setError] = useState<string | null>(null);

  // Deletion modal
  const [showDeleteModal, setShowDeleteModal] = useState<boolean>(false);
  const [purgeFiles, setPurgeFiles] = useState<boolean>(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

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
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Skeleton className="aspect-video w-full rounded-xl lg:col-span-1" />
            <Skeleton className="h-64 w-full rounded-xl lg:col-span-2" />
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

      {/* Tab 1: Technical Overview */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-2">
          {/* Thumbnail preview */}
          <div className="space-y-4">
            <VideoThumbnail
              durationSeconds={video.duration_seconds}
              resolution={`${video.width}x${video.height}`}
              aspectRatio="16:9"
              className="w-full shadow-md"
            />

            <div className="p-4 rounded-xl border border-border bg-card/60 space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Status:</span>
                <EntityStatusBadge status={video.status} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">SSD File Status:</span>
                <span className={video.file_exists ? "text-emerald-400 font-medium" : "text-amber-400 font-medium"}>
                  {video.file_exists ? "File Verified on SSD" : "File Missing / Moved"}
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
            </div>
          </div>

          {/* Technical Metadata Cards */}
          <div className="lg:col-span-2 space-y-4">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Layers className="h-4 w-4 text-primary" />
                  Stream Characteristics (FFprobe Verified)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                    <span className="text-muted-foreground block text-[11px]">Duration</span>
                    <span className="text-foreground font-semibold text-sm">
                      {formatDuration(video.duration_seconds)}
                    </span>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                    <span className="text-muted-foreground block text-[11px]">Resolution</span>
                    <span className="text-foreground font-semibold text-sm">
                      {video.width}x{video.height}
                    </span>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                    <span className="text-muted-foreground block text-[11px]">Aspect Ratio</span>
                    <span className="text-foreground font-semibold text-sm">
                      {video.aspect_ratio}
                    </span>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                    <span className="text-muted-foreground block text-[11px]">Frame Rate</span>
                    <span className="text-foreground font-semibold text-sm">
                      {video.fps.toFixed(1)} fps
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono mt-3">
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                    <span className="text-muted-foreground block text-[11px]">Video Codec</span>
                    <span className="text-foreground font-semibold">{video.video_codec}</span>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 space-y-1">
                    <span className="text-muted-foreground block text-[11px]">Audio Codec</span>
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
                      {video.audio_channels === 1 ? "1 (Mono)" : "2 (Stereo)"}
                    </span>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-border/40 text-xs text-muted-foreground space-y-2">
                  <div className="flex items-center justify-between">
                    <span>File Size:</span>
                    <span className="font-mono font-semibold text-foreground">
                      {formatBytes(video.file_size_bytes)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Storage Location:</span>
                    <span className="font-mono text-zinc-300 text-[11px]">
                      {video.storage_label || "Local SSD Storage"}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <HardDrive className="h-4 w-4 text-emerald-400" />
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
                    <span>Model: {transcript.model_name}</span>
                    <span>Language: {transcript.language.toUpperCase()}</span>
                    <span>Words: {transcript.word_count || "--"}</span>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="max-h-96 overflow-y-auto p-4 rounded-xl bg-secondary/30 border border-border text-xs leading-relaxed font-mono whitespace-pre-wrap text-foreground">
                  {transcript.full_text || "No text available."}
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="rounded-xl border border-dashed border-border bg-card/30 p-10 text-center space-y-3">
              <FileText className="h-7 w-7 text-muted-foreground mx-auto" />
              <h3 className="text-sm font-semibold text-foreground">No Transcript Available</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
                This video has not yet been processed with Faster-Whisper. Audio extraction and transcription pipelines will execute in Phase 13.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Highlights */}
      {activeTab === "highlights" && (
        <div className="pt-2">
          {highlights.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {highlights.map((h) => (
                <Card key={h.id} className="p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold font-mono text-amber-400">
                      Score: {h.composite_score.toFixed(1)}/100
                    </span>
                    <span className="text-xs text-muted-foreground font-mono">
                      {formatDuration((h.duration_ms || (h.end_ms && h.start_ms ? h.end_ms - h.start_ms : 0)) / 1000)}
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-foreground">"{h.hook_sentence}"</p>
                  <p className="text-xs text-muted-foreground line-clamp-2">{h.summary}</p>
                </Card>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-border bg-card/30 p-10 text-center space-y-3">
              <Sparkles className="h-7 w-7 text-muted-foreground mx-auto" />
              <h3 className="text-sm font-semibold text-foreground">No Highlights Extracted</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
                AI highlight candidate extraction and composite viral scoring will be performed in Phase 14 after transcript generation.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Clips */}
      {activeTab === "clips" && (
        <div className="pt-2">
          {clips.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {clips.map((clip) => (
                <div key={clip.id} className="p-4 rounded-xl border border-border bg-card space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-foreground truncate">{clip.title}</span>
                    <EntityStatusBadge status={clip.status} />
                  </div>
                  <div className="text-xs font-mono text-muted-foreground flex justify-between">
                    <span>Duration: {formatDuration(clip.duration_ms / 1000)}</span>
                    <span>{clip.aspect_ratio_mode}</span>
                  </div>
                  <Button asChild variant="outline" size="sm" className="w-full text-xs">
                    <Link to={`/studio/${clip.id}`}>Open in Studio</Link>
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-border bg-card/30 p-10 text-center space-y-3">
              <Film className="h-7 w-7 text-muted-foreground mx-auto" />
              <h3 className="text-sm font-semibold text-foreground">No Clips Generated Yet</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
                No customized 9:16 short clips have been drafted from this video yet.
              </p>
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
        consequences="Deleting this video will remove the record and all relational children (transcripts, highlights, draft clips). Rendered MP4 exports will be preserved on disk unless selected below."
        showPurgeFilesOption={true}
        purgeFilesChecked={purgeFiles}
        onPurgeFilesToggle={setPurgeFiles}
        onConfirm={handleDelete}
        isDeleting={isDeleting}
      />
    </PageContainer>
  );
};
