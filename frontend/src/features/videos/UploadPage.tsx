import React, { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  FileVideo,
  HardDrive,
  RefreshCw,
  Sparkles,
  UploadCloud,
  XCircle,
} from "lucide-react";

import { PageContainer } from "../../components/layout/PageContainer";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Progress } from "../../components/ui/progress";
import { useToast } from "../../hooks/useToast";
import { api, ClipslyApiError } from "../../services/api";
import { UploadProgress, Video } from "../../types/api";

const ALLOWED_EXTENSIONS = [".mp4", ".mkv", ".mov", ".webm"];
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024 * 1024; // 10 GB

type UploadStatus = "idle" | "selected" | "uploading" | "finalizing" | "completed" | "failed" | "cancelled";

function formatBytes(bytes: number, decimals = 1): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
}

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [progress, setProgress] = useState<UploadProgress>({
    loaded: 0,
    total: 0,
    percentage: 0,
    speedBytesPerSec: 0,
    remainingSeconds: null,
  });
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [uploadedVideo, setUploadedVideo] = useState<Video | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const validateFile = (file: File): string | null => {
    if (file.size === 0) {
      return "The selected video file is empty (0 bytes).";
    }

    const ext = `.${file.name.split(".").pop()?.toLowerCase()}`;
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return `Unsupported format '${ext}'. Clipsly supports MP4, MKV, MOV, and WebM containers.`;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      return `File size (${formatBytes(file.size)}) exceeds the maximum allowed upload limit of 10 GB.`;
    }

    return null;
  };

  const handleFileSelect = (file: File) => {
    const error = validateFile(file);
    if (error) {
      setErrorMessage(error);
      setStatus("failed");
      setSelectedFile(null);
      toast.error("File Validation Failed", error);
      return;
    }

    setSelectedFile(file);
    setErrorMessage(null);
    setStatus("selected");
    setProgress({
      loaded: 0,
      total: file.size,
      percentage: 0,
      speedBytesPerSec: 0,
      remainingSeconds: null,
    });
  };

  const onFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    if (status === "uploading" || status === "finalizing") {
      return;
    }

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleBrowseClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
      fileInputRef.current.click();
    }
  };

  const handleStartUpload = async () => {
    if (!selectedFile) return;

    setStatus("uploading");
    setErrorMessage(null);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const video = await api.videos.upload(selectedFile, {
        signal: controller.signal,
        onProgress: (p) => {
          setProgress(p);
          if (p.percentage >= 100) {
            setStatus("finalizing");
          }
        },
      });

      setUploadedVideo(video);
      setStatus("completed");
      toast.success("Video Ingestion Complete", `${video.original_filename} is ready for processing.`);
    } catch (err: unknown) {
      if (controller.signal.aborted) {
        setStatus("cancelled");
        toast.info("Upload Cancelled", "File upload was cancelled. Incomplete data removed.");
        return;
      }

      setStatus("failed");
      let msg = "An unexpected error occurred during video upload.";
      if (err instanceof ClipslyApiError) {
        msg = err.detail;
      } else if (err instanceof Error) {
        msg = err.message;
      }
      setErrorMessage(msg);
      toast.error("Upload Failed", msg);
    } finally {
      abortControllerRef.current = null;
    }
  };

  const handleCancelUpload = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setUploadedVideo(null);
    setErrorMessage(null);
    setStatus("idle");
    setProgress({
      loaded: 0,
      total: 0,
      percentage: 0,
      speedBytesPerSec: 0,
      remainingSeconds: null,
    });
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.key === "Enter" || e.key === " ") && (status === "idle" || status === "selected")) {
      e.preventDefault();
      handleBrowseClick();
    }
  };

  return (
    <PageContainer
      title="Upload Video"
      description="Select or drop a local video file to ingest into sovereign local SSD storage."
    >
      <div className="max-w-3xl mx-auto space-y-6">
        <input
          ref={fileInputRef}
          type="file"
          data-testid="video-file-input"
          accept=".mp4,.mkv,.mov,.webm,video/mp4,video/quicktime,video/x-matroska,video/webm"
          className="hidden"
          onChange={onFileInputChange}
          tabIndex={-1}
        />

        {/* 1. IDLE OR SELECTED STATE: DROPZONE */}
        {(status === "idle" || status === "selected") && (
          <div
            tabIndex={0}
            role="button"
            aria-label="Upload video file dropzone"
            onKeyDown={handleKeyDown}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={status === "idle" ? handleBrowseClick : undefined}
            className={`relative rounded-2xl border-2 border-dashed p-8 sm:p-12 text-center transition-all focus:outline-none focus:ring-2 focus:ring-primary ${
              isDragOver
                ? "border-primary bg-primary/10 scale-[1.01]"
                : "border-border bg-card/40 hover:border-primary/50"
            }`}
          >
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary border border-primary/20 mb-4 shadow-sm shadow-primary/10">
              <UploadCloud className="h-8 w-8" />
            </div>

            {status === "idle" ? (
              <>
                <h2 className="text-base font-semibold text-foreground">
                  Drop your local video file here, or click to browse
                </h2>
                <p className="mt-1.5 text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
                  Fast local SSD ingestion directly into{" "}
                  <code className="text-foreground font-mono">storage/uploads/</code>.
                  Supported containers: <span className="text-foreground font-medium">MP4, MOV, MKV, WebM</span>.
                </p>

                <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
                  <Badge variant="subtle" className="text-[11px] font-mono">
                    Max: 10 GB
                  </Badge>
                  <Badge variant="subtle" className="text-[11px] font-mono">
                    Duration: 5 - 120 Min
                  </Badge>
                  <Badge variant="subtle" className="text-[11px] font-mono">
                    FFprobe Verified
                  </Badge>
                  <Badge variant="subtle" className="text-[11px] font-mono">
                    Localhost Only
                  </Badge>
                </div>

                <div className="mt-6">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleBrowseClick();
                    }}
                    className="gap-2"
                  >
                    <FileVideo className="h-4 w-4" />
                    Browse Files
                  </Button>
                </div>
              </>
            ) : (
              selectedFile && (
                <div className="space-y-4">
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-secondary/80 border border-border">
                    <FileVideo className="h-4 w-4 text-primary" />
                    <span className="text-sm font-medium text-foreground truncate max-w-xs sm:max-w-md">
                      {selectedFile.name}
                    </span>
                    <Badge variant="default" className="text-[10px] uppercase font-mono ml-1">
                      {selectedFile.name.split(".").pop()}
                    </Badge>
                  </div>

                  <div className="text-xs text-muted-foreground">
                    Size: <span className="font-mono text-foreground font-medium">{formatBytes(selectedFile.size)}</span>
                  </div>

                  <div className="flex items-center justify-center gap-3 pt-2">
                    <Button
                      type="button"
                      variant="default"
                      size="sm"
                      onClick={handleStartUpload}
                      className="gap-2"
                    >
                      <UploadCloud className="h-4 w-4" />
                      Start Upload
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={handleReset}
                    >
                      Change File
                    </Button>
                  </div>
                </div>
              )
            )}
          </div>
        )}

        {/* 2. UPLOADING OR FINALIZING STATE */}
        {(status === "uploading" || status === "finalizing") && (
          <Card className="border-primary/40 shadow-lg">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-primary/10 text-primary border border-primary/20 animate-pulse">
                    <UploadCloud className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle className="text-sm font-semibold">
                      {status === "uploading" ? "Streaming Video to SSD..." : "Finalizing Video Ingestion..."}
                    </CardTitle>
                    <CardDescription className="text-xs">
                      {selectedFile?.name} ({formatBytes(selectedFile?.size || 0)})
                    </CardDescription>
                  </div>
                </div>
                <Badge variant={status === "uploading" ? "warning" : "info"} className="font-mono text-xs">
                  {status === "uploading" ? `${progress.percentage}%` : "Validating"}
                </Badge>
              </div>
            </CardHeader>

            <CardContent className="space-y-4">
              <Progress value={status === "finalizing" ? 100 : progress.percentage} className="h-2" />

              <div className="flex flex-wrap items-center justify-between text-xs text-muted-foreground font-mono">
                <div>
                  {formatBytes(progress.loaded)} / {formatBytes(progress.total)}
                </div>
                {status === "uploading" && progress.speedBytesPerSec > 0 && (
                  <div className="flex items-center gap-4">
                    <span>{formatBytes(progress.speedBytesPerSec)}/s</span>
                    {progress.remainingSeconds !== null && (
                      <span className="flex items-center gap-1 text-muted-foreground/80">
                        <Clock className="h-3 w-3" />
                        ~{progress.remainingSeconds}s remaining
                      </span>
                    )}
                  </div>
                )}
                {status === "finalizing" && (
                  <div className="flex items-center gap-2 text-primary">
                    <RefreshCw className="h-3 w-3 animate-spin" />
                    <span>Verifying streams with FFprobe...</span>
                  </div>
                )}
              </div>

              <div className="pt-2 flex justify-end">
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  onClick={handleCancelUpload}
                  disabled={status === "finalizing"}
                  className="text-xs"
                >
                  Cancel Upload
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 3. COMPLETED STATE */}
        {status === "completed" && uploadedVideo && (
          <Card className="border-emerald-500/30 bg-emerald-500/5 shadow-md">
            <CardHeader className="pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <CheckCircle2 className="h-6 w-6" />
                </div>
                <div>
                  <CardTitle className="text-base text-foreground font-semibold">
                    Upload & Validation Complete
                  </CardTitle>
                  <CardDescription className="text-xs text-muted-foreground">
                    Video successfully validated by FFprobe and stored safely on local SSD.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>

            <CardContent className="space-y-5">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 rounded-xl bg-card/60 border border-border text-xs">
                <div>
                  <span className="text-muted-foreground block text-[11px]">Filename</span>
                  <span className="font-medium text-foreground truncate block font-mono mt-0.5">
                    {uploadedVideo.original_filename}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">Resolution</span>
                  <span className="font-medium text-foreground font-mono mt-0.5 block">
                    {uploadedVideo.width}x{uploadedVideo.height} ({uploadedVideo.aspect_ratio})
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">Duration</span>
                  <span className="font-medium text-foreground font-mono mt-0.5 block">
                    {formatDuration(uploadedVideo.duration_seconds)} ({uploadedVideo.duration_seconds}s)
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">Codecs</span>
                  <span className="font-medium text-foreground font-mono mt-0.5 block">
                    {uploadedVideo.video_codec} / {uploadedVideo.audio_codec}
                  </span>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3 pt-2">
                <Button
                  type="button"
                  variant="default"
                  size="sm"
                  onClick={() => navigate(`/video/${uploadedVideo.id}`)}
                  className="gap-2"
                >
                  <Sparkles className="h-4 w-4" />
                  Inspect Video Details
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => navigate("/videos")}
                  className="gap-2"
                >
                  <FileVideo className="h-4 w-4" />
                  View in Video Library
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleReset}
                  className="text-xs text-muted-foreground"
                >
                  Upload Another Video
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 4. FAILED STATE */}
        {status === "failed" && (
          <Card className="border-destructive/40 bg-destructive/5 shadow-md">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-destructive/10 text-destructive border border-destructive/20">
                  <XCircle className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold text-destructive">
                    Upload or Validation Failed
                  </CardTitle>
                  <CardDescription className="text-xs text-muted-foreground">
                    The video file could not be ingested. Temporary scratch files were unlinked.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>

            <CardContent className="space-y-4">
              <div className="p-3 rounded-lg bg-card/60 border border-border text-xs text-foreground font-mono leading-relaxed">
                {errorMessage || "An unknown error occurred during video ingestion."}
              </div>

              <div className="flex items-center gap-3">
                {selectedFile && (
                  <Button
                    type="button"
                    variant="default"
                    size="sm"
                    onClick={handleStartUpload}
                    className="gap-2"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    Retry Upload
                  </Button>
                )}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleReset}
                >
                  Select Another File
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 5. CANCELLED STATE */}
        {status === "cancelled" && (
          <Card className="border-amber-500/30 bg-amber-500/5 shadow-sm">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  <AlertCircle className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold text-foreground">
                    Upload Cancelled
                  </CardTitle>
                  <CardDescription className="text-xs text-muted-foreground">
                    The upload process was cancelled by the user. All partial temporary data was cleanly discarded.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleReset}
              >
                Upload Another Video
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Specification Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <FileVideo className="h-4 w-4 text-emerald-400" />
                <CardTitle className="text-xs">Container & Codec Requirements</CardTitle>
              </div>
              <CardDescription className="text-xs leading-relaxed">
                Supports MP4, MOV, MKV, and WebM containers. Video stream must contain valid H.264/HEVC/VP9 and
                speech audio track for transcription.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <HardDrive className="h-4 w-4 text-blue-400" />
                <CardTitle className="text-xs">Local SSD Storage Quota</CardTitle>
              </div>
              <CardDescription className="text-xs leading-relaxed">
                Direct write to <code className="text-foreground">storage/uploads/</code>. Requires at least 10 GB free
                SSD space prior to initiating upload.
              </CardDescription>
            </CardHeader>
          </Card>
        </div>

        {/* Sovereignty Notice Banner */}
        <div className="p-4 rounded-xl bg-secondary/50 border border-border/80 flex items-start gap-3 text-xs text-muted-foreground">
          <AlertCircle className="h-4 w-4 text-primary shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            Zero cloud uploads. All video bytes remain unshared directly on this workstation's local NVMe drive.
          </p>
        </div>
      </div>
    </PageContainer>
  );
};
