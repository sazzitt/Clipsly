import React, { useEffect, useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Film,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Scissors,
  Settings2,
  ArrowRight,
  Cpu,
  StopCircle,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "../../../components/ui/dialog";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Label } from "../../../components/ui/label";
import { Badge } from "../../../components/ui/badge";
import { Progress } from "../../../components/ui/progress";
import { Checkbox } from "../../../components/ui/checkbox";
import { api, ClipslyApiError } from "../../../services/api";
import { useToast } from "../../../hooks/useToast";
import { Clip, ConversionMode, ProcessingJob } from "../../../types/api";

export interface GenerateClipModalProps {
  isOpen: boolean;
  onClose: () => void;
  videoId: string;
  highlightId?: string | null;
  initialTitle?: string;
  initialStartMs?: number;
  initialEndMs?: number;
  videoTitle?: string;
  videoDurationSeconds?: number;
  onClipGenerated?: (clip: Clip) => void;
}

const CONVERSION_MODES: Array<{
  value: ConversionMode;
  label: string;
  description: string;
}> = [
  {
    value: "BLUR_PAD",
    label: "Blurred Background (Default)",
    description: "Preserves full video frame centered over a heavy 9:16 blurred background fill.",
  },
  {
    value: "CROP_CENTER",
    label: "Center Crop",
    description: "Fills the entire 9:16 canvas by cropping the central vertical slice.",
  },
  {
    value: "FIT_LETTERBOX",
    label: "Fit Letterbox",
    description: "Fits the full video within 9:16 with clean solid matte background bars.",
  },
];

export const GenerateClipModal: React.FC<GenerateClipModalProps> = ({
  isOpen,
  onClose,
  videoId,
  highlightId = null,
  initialTitle = "Untitled Clip",
  initialStartMs = 0,
  initialEndMs = 15000,
  videoTitle,
  videoDurationSeconds,
  onClipGenerated,
}) => {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [title, setTitle] = useState<string>(initialTitle);
  const [startSeconds, setStartSeconds] = useState<number>(0);
  const [endSeconds, setEndSeconds] = useState<number>(15);
  const [conversionMode, setConversionMode] = useState<ConversionMode>("BLUR_PAD");
  const [forceCpu, setForceCpu] = useState<boolean>(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Active generation tracking
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [activeClipId, setActiveClipId] = useState<string | null>(null);
  const [activeJob, setActiveJob] = useState<ProcessingJob | null>(null);
  const [completedClip, setCompletedClip] = useState<Clip | null>(null);
  const [isCancelling, setIsCancelling] = useState<boolean>(false);

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Reset form when modal opens with new initials
  useEffect(() => {
    if (isOpen) {
      setTitle(initialTitle || "Untitled Clip");
      const sSec = initialStartMs > 0 ? initialStartMs / 1000 : 0;
      const eSec = initialEndMs > 0 ? initialEndMs / 1000 : sSec + 15;
      setStartSeconds(Number(sSec.toFixed(2)));
      setEndSeconds(Number(eSec.toFixed(2)));
      setConversionMode("BLUR_PAD");
      setForceCpu(false);
      setValidationError(null);
      setIsSubmitting(false);
      setActiveJobId(null);
      setActiveClipId(null);
      setActiveJob(null);
      setCompletedClip(null);
      setIsCancelling(false);
    } else {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    }
  }, [isOpen, initialTitle, initialStartMs, initialEndMs]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const durationSeconds = Math.max(0, endSeconds - startSeconds);
  const durationMs = Math.round(durationSeconds * 1000);

  // Format timecode helper (mm:ss.s)
  const formatTimecode = (sec: number): string => {
    const m = Math.floor(sec / 60);
    const s = (sec % 60).toFixed(1);
    return `${m.toString().padStart(2, "0")}:${s.padStart(4, "0")}`;
  };

  // Validation
  const validateForm = useCallback((): boolean => {
    if (!title.trim()) {
      setValidationError("Clip title cannot be blank.");
      return false;
    }
    if (startSeconds < 0) {
      setValidationError("Start timestamp cannot be negative.");
      return false;
    }
    if (endSeconds <= startSeconds) {
      setValidationError("End timestamp must be strictly greater than start timestamp.");
      return false;
    }
    if (durationMs < 5000) {
      setValidationError("Clip duration must be at least 5.0 seconds (5000 ms).");
      return false;
    }
    if (videoDurationSeconds && endSeconds > videoDurationSeconds + 1.0) {
      setValidationError(
        `End timestamp cannot exceed video duration (${videoDurationSeconds.toFixed(1)}s).`
      );
      return false;
    }
    setValidationError(null);
    return true;
  }, [title, startSeconds, endSeconds, durationMs, videoDurationSeconds]);

  // Run validation whenever inputs change
  useEffect(() => {
    if (isOpen && !activeJobId) {
      validateForm();
    }
  }, [isOpen, activeJobId, validateForm]);

  // Poll for job progress
  const startPolling = useCallback(
    (jobId: string, clipId: string) => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

      const poll = async () => {
        try {
          const job = await api.jobs.get(jobId);
          setActiveJob(job);

          if (job.status === "COMPLETED") {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            try {
              const freshClip = await api.clips.get(clipId);
              setCompletedClip(freshClip);
              onClipGenerated?.(freshClip);
            } catch {
              // fallback if get fails
            }
            toast({
              title: "Clip Generated",
              description: `Vertical 9:16 clip "${title}" is ready.`,
            });
          } else if (job.status === "FAILED") {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            toast({
              title: "Generation Failed",
              description: job.error_message || "Video conversion failed.",
              variant: "destructive",
            });
          } else if (job.status === "CANCELLED") {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            toast({
              title: "Generation Cancelled",
              description: "Clip generation task was cancelled.",
            });
          }
        } catch (err) {
          console.warn("Polling error for clip job:", err);
        }
      };

      poll();
      pollIntervalRef.current = setInterval(poll, 1000);
    },
    [title, toast, onClipGenerated]
  );

  // Submit Generation Request
  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      const payload = {
        video_id: videoId,
        highlight_id: highlightId || undefined,
        title: title.trim(),
        start_ms: Math.round(startSeconds * 1000),
        end_ms: Math.round(endSeconds * 1000),
        conversion_mode: conversionMode,
        aspect_ratio_mode: conversionMode,
        target_width: 1080,
        target_height: 1920,
        target_fps: 30.0,
        force_cpu: forceCpu,
      };

      const resp = await api.clips.generate(payload);

      setActiveJobId(resp.job_id);
      setActiveClipId(resp.clip_id);
      setActiveJob({
        id: resp.job_id,
        video_id: videoId,
        job_type: "CLIP_GENERATION",
        status: "QUEUED",
        progress_percent: 0.0,
        current_step: "Queued for clip generation",
        created_at: new Date().toISOString(),
      });

      startPolling(resp.job_id, resp.clip_id);
    } catch (err: unknown) {
      const msg =
        err instanceof ClipslyApiError
          ? err.detail
          : err instanceof Error
          ? err.message
          : "Failed to enqueue clip generation job.";
      toast({
        title: "Generation Request Failed",
        description: msg,
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Cancel generation
  const handleCancel = async () => {
    if (!activeClipId) return;
    setIsCancelling(true);
    try {
      await api.clips.cancel(activeClipId);
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      setActiveJob((prev) => (prev ? { ...prev, status: "CANCELLED" } : null));
      toast({
        title: "Cancelled",
        description: "Clip generation has been cancelled.",
      });
    } catch (err: unknown) {
      const msg = err instanceof ClipslyApiError ? err.detail : "Failed to cancel clip job.";
      toast({
        title: "Cancellation Error",
        description: msg,
        variant: "destructive",
      });
    } finally {
      setIsCancelling(false);
    }
  };

  const handleOpenStudio = () => {
    if (completedClip || activeClipId) {
      const cId = completedClip?.id || activeClipId;
      onClose();
      navigate(`/studio/${cId}`);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-xl sm:max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Scissors className="h-5 w-5" />
            </div>
            <div>
              <DialogTitle className="text-base font-semibold">
                Generate 9:16 Vertical Clip
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                Convert video segments into short-form vertical MP4 assets.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* State A: In-Progress / Finished Job View */}
        {activeJobId ? (
          <div className="space-y-5 py-3">
            <div className="p-4 rounded-xl border border-border bg-card/60 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground">
                  Job Status:{" "}
                  <span
                    className={
                      activeJob?.status === "COMPLETED"
                        ? "text-emerald-400 font-bold"
                        : activeJob?.status === "FAILED"
                        ? "text-rose-400 font-bold"
                        : activeJob?.status === "CANCELLED"
                        ? "text-amber-400 font-bold"
                        : "text-primary font-bold animate-pulse"
                    }
                  >
                    {activeJob?.status || "QUEUED"}
                  </span>
                </span>
                <Badge variant="outline" className="text-[11px] font-mono">
                  {conversionMode} • 1080x1920
                </Badge>
              </div>

              {/* Progress Bar */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs text-muted-foreground font-mono">
                  <span>{activeJob?.current_step || "Processing..."}</span>
                  <span>{`${Math.round(activeJob?.progress_percent || 0)}%`}</span>
                </div>
                <Progress value={activeJob?.progress_percent || 0} className="h-2" />
              </div>

              {/* Error Box if FAILED */}
              {activeJob?.status === "FAILED" && (
                <div className="p-3 rounded-lg border border-rose-500/30 bg-rose-500/10 text-xs text-rose-300 flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
                  <div>
                    <p className="font-semibold">Generation Failed</p>
                    <p className="text-[11px] opacity-90 mt-0.5">
                      {activeJob.error_message || "An unknown encoding error occurred."}
                    </p>
                  </div>
                </div>
              )}

              {/* Success Info if COMPLETED */}
              {activeJob?.status === "COMPLETED" && (
                <div className="p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-xs text-emerald-300 flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400 mt-0.5" />
                  <div>
                    <p className="font-semibold">9:16 Video Ready</p>
                    <p className="text-[11px] opacity-90 mt-0.5">
                      Encoded to 1080x1920 MP4 with audio preserved. Open Studio to preview and download.
                    </p>
                  </div>
                </div>
              )}
            </div>

            <DialogFooter className="flex items-center justify-between sm:justify-between gap-2 pt-2">
              {activeJob?.status === "QUEUED" || activeJob?.status === "PROCESSING" ? (
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  onClick={handleCancel}
                  disabled={isCancelling}
                  className="gap-1.5 text-xs"
                >
                  {isCancelling ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <StopCircle className="h-3.5 w-3.5" />
                  )}
                  <span>Cancel Generation</span>
                </Button>
              ) : (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={onClose}
                  className="text-xs"
                >
                  Close
                </Button>
              )}

              {activeJob?.status === "COMPLETED" && (
                <Button
                  type="button"
                  size="sm"
                  onClick={handleOpenStudio}
                  className="gap-1.5 text-xs bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  <span>Open Studio</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              )}
            </DialogFooter>
          </div>
        ) : (
          /* State B: Configuration Form */
          <form onSubmit={handleSubmit} className="space-y-4 py-2">
            {/* Clip Title */}
            <div className="space-y-1.5">
              <Label htmlFor="clip-title" className="text-xs font-medium">
                Clip Title
              </Label>
              <Input
                id="clip-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. The Greatest Insight from the Talk"
                className="h-8 text-xs font-medium"
                maxLength={255}
                required
              />
              {videoTitle && (
                <p className="text-[11px] text-muted-foreground truncate">
                  Source Video: <span className="text-foreground">{videoTitle}</span>
                </p>
              )}
            </div>

            {/* Timestamps & Duration Grid */}
            <div className="grid grid-cols-2 gap-3 p-3 rounded-lg border border-border/70 bg-secondary/20">
              <div className="space-y-1">
                <Label htmlFor="clip-start" className="text-[11px] font-mono text-muted-foreground">
                  Start Timestamp (seconds)
                </Label>
                <Input
                  id="clip-start"
                  type="number"
                  step="0.1"
                  min="0"
                  value={startSeconds}
                  onChange={(e) => setStartSeconds(parseFloat(e.target.value) || 0)}
                  className="h-8 text-xs font-mono"
                />
                <span className="text-[10px] text-muted-foreground font-mono">
                  {formatTimecode(startSeconds)}
                </span>
              </div>

              <div className="space-y-1">
                <Label htmlFor="clip-end" className="text-[11px] font-mono text-muted-foreground">
                  End Timestamp (seconds)
                </Label>
                <Input
                  id="clip-end"
                  type="number"
                  step="0.1"
                  min="0"
                  value={endSeconds}
                  onChange={(e) => setEndSeconds(parseFloat(e.target.value) || 0)}
                  className="h-8 text-xs font-mono"
                />
                <span className="text-[10px] text-muted-foreground font-mono">
                  {formatTimecode(endSeconds)}
                </span>
              </div>

              <div className="col-span-2 flex items-center justify-between pt-1 border-t border-border/40 text-xs">
                <span className="text-muted-foreground font-medium">Calculated Duration:</span>
                <span
                  className={`font-mono font-bold ${
                    durationMs < 5000 ? "text-rose-400" : "text-emerald-400"
                  }`}
                >
                  {durationSeconds.toFixed(1)}s ({durationMs} ms)
                </span>
              </div>
            </div>

            {/* Conversion Mode Selection */}
            <div className="space-y-2">
              <Label className="text-xs font-medium flex items-center gap-1.5">
                <Film className="h-3.5 w-3.5 text-primary" />
                <span>Vertical Conversion Mode</span>
              </Label>
              <div className="grid grid-cols-1 gap-2">
                {CONVERSION_MODES.map((mode) => (
                  <label
                    key={mode.value}
                    className={`flex items-start gap-3 p-2.5 rounded-lg border cursor-pointer transition-all ${
                      conversionMode === mode.value
                        ? "border-primary bg-primary/10 ring-1 ring-primary/30"
                        : "border-border bg-card/50 hover:bg-card hover:border-zinc-700"
                    }`}
                  >
                    <input
                      type="radio"
                      name="conversion_mode"
                      value={mode.value}
                      checked={conversionMode === mode.value}
                      onChange={() => setConversionMode(mode.value)}
                      className="mt-1 text-primary focus:ring-primary"
                    />
                    <div className="space-y-0.5 text-xs">
                      <div className="font-semibold text-foreground flex items-center gap-2">
                        {mode.label}
                        {mode.value === "BLUR_PAD" && (
                          <Badge variant="secondary" className="text-[9px] py-0 px-1.5">
                            Recommended
                          </Badge>
                        )}
                      </div>
                      <p className="text-[11px] text-muted-foreground leading-relaxed">
                        {mode.description}
                      </p>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Output Specs & Encoding Settings */}
            <div className="p-3 rounded-lg border border-border bg-card/40 space-y-2.5">
              <div className="flex items-center justify-between text-xs font-medium text-foreground">
                <span className="flex items-center gap-1.5">
                  <Settings2 className="h-3.5 w-3.5 text-muted-foreground" />
                  <span>Output Specifications</span>
                </span>
                <Badge variant="outline" className="text-[10px] font-mono">
                  1080 × 1920 • 30 FPS
                </Badge>
              </div>

              <div className="flex items-center space-x-2 pt-1 border-t border-border/40">
                <Checkbox
                  id="force-cpu"
                  checked={forceCpu}
                  onCheckedChange={(checked) => setForceCpu(Boolean(checked))}
                />
                <label
                  htmlFor="force-cpu"
                  className="text-xs font-medium leading-none text-muted-foreground cursor-pointer flex items-center gap-1.5"
                >
                  <Cpu className="h-3 w-3" />
                  Force CPU encoding (libx264 AVX2) instead of NVIDIA NVENC
                </label>
              </div>
            </div>

            {/* Validation Error Alert */}
            {validationError && (
              <div className="p-2.5 rounded-lg border border-rose-500/30 bg-rose-500/10 text-xs text-rose-300 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
                <span>{validationError}</span>
              </div>
            )}

            <DialogFooter className="flex items-center justify-between sm:justify-between gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onClose}
                disabled={isSubmitting}
                className="text-xs"
              >
                Cancel
              </Button>

              <Button
                type="submit"
                size="sm"
                disabled={Boolean(validationError) || isSubmitting}
                className="gap-1.5 text-xs"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>Submitting...</span>
                  </>
                ) : (
                  <>
                    <Scissors className="h-3.5 w-3.5" />
                    <span>Generate 9:16 Clip</span>
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
};
