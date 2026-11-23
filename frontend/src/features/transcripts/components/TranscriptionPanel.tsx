import React, { useEffect, useState } from "react";
import {
  Cpu,
  Zap,
  Activity,
  AlertTriangle,
  FileText,
  Volume2,
  CheckCircle2,
  XCircle,
  Loader2,
  RotateCcw,
} from "lucide-react";
import { Button } from "../../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";
import { api } from "../../../services/api";
import { useToast } from "../../../hooks/useToast";
import {
  AvailableModelsResponse,
  ProcessingJob,
  AudioAsset,
  TranscriptionRequest,
} from "../../../types/api";

interface TranscriptionPanelProps {
  videoId: string;
  hasAudio: boolean;
  audioAsset: AudioAsset | null | undefined;
  activeJob?: ProcessingJob | null;
  onTranscriptionStarted?: (jobId: string) => void;
  onJobCancelled?: () => void;
  onExtractAudioRequested?: () => void;
  hasExistingTranscript?: boolean;
}

export const TranscriptionPanel: React.FC<TranscriptionPanelProps> = ({
  videoId,
  hasAudio,
  audioAsset,
  activeJob,
  onTranscriptionStarted,
  onJobCancelled,
  onExtractAudioRequested,
  hasExistingTranscript = false,
}) => {
  const { toast } = useToast();

  const [modelsData, setModelsData] = useState<AvailableModelsResponse | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>("base");
  const [selectedDevice, setSelectedDevice] = useState<string>("cuda");
  const [selectedComputeType, setSelectedComputeType] = useState<string>("float16");
  const [selectedLanguage, setSelectedLanguage] = useState<string>("");
  const [vadFilter, setVadFilter] = useState<boolean>(true);
  const [wordTimestamps, setWordTimestamps] = useState<boolean>(true);
  const [forceRetranscribe, setForceRetranscribe] = useState<boolean>(false);

  const [isLoadingModels, setIsLoadingModels] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isCancelling, setIsCancelling] = useState<boolean>(false);

  // Fetch available models catalog on mount
  useEffect(() => {
    let isMounted = true;
    const fetchModels = async () => {
      try {
        const data = await api.transcripts.getModels();
        if (isMounted) {
          setModelsData(data);
          if (data.default_model) {
            setSelectedModel(data.default_model);
          }
          if (data.cuda_available) {
            setSelectedDevice("cuda");
            setSelectedComputeType(data.cuda_compute_types[0] || "float16");
          } else {
            setSelectedDevice("cpu");
            setSelectedComputeType(data.cpu_compute_types[0] || "int8");
          }
        }
      } catch (err) {
        console.warn("Failed to query Faster-Whisper models catalog:", err);
      } finally {
        if (isMounted) {
          setIsLoadingModels(false);
        }
      }
    };

    fetchModels();
    return () => {
      isMounted = false;
    };
  }, []);

  const isJobRunning = Boolean(
    activeJob &&
      (activeJob.status === "processing" ||
        activeJob.status === "queued" ||
        activeJob.status === "transcribing" ||
        activeJob.status === "PROCESSING" ||
        activeJob.status === "QUEUED")
  );

  const handleStartTranscription = async () => {
    if (!hasAudio) {
      toast({
        title: "No Audio Track",
        description: "Cannot transcribe a video that contains no audio.",
        variant: "error",
      });
      return;
    }

    if (!audioAsset || audioAsset.status !== "COMPLETED") {
      toast({
        title: "Audio Extraction Required",
        description: "Please extract audio first before running speech-to-text.",
        variant: "warning",
      });
      if (onExtractAudioRequested) {
        onExtractAudioRequested();
      }
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: TranscriptionRequest = {
        model_name: selectedModel,
        device: selectedDevice,
        compute_type: selectedComputeType,
        language: selectedLanguage.trim() ? selectedLanguage.trim() : null,
        vad_filter: vadFilter,
        word_timestamps: wordTimestamps,
        force_retranscribe: forceRetranscribe || hasExistingTranscript,
      };

      const res = await api.videos.transcribe(videoId, payload);
      toast({
        title: "Transcription Queued",
        description: `Job submitted using Faster-Whisper ${selectedModel} model.`,
        variant: "success",
      });
      if (onTranscriptionStarted) {
        onTranscriptionStarted(res.job_id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to queue transcription job.";
      toast({
        title: "Transcription Error",
        description: msg,
        variant: "error",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelJob = async () => {
    if (!activeJob) return;
    setIsCancelling(true);
    try {
      await api.jobs.cancel(activeJob.id);
      toast({
        title: "Cancellation Requested",
        description: "Whisper inference process cancellation signaled.",
        variant: "info",
      });
      if (onJobCancelled) {
        onJobCancelled();
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to cancel job.";
      toast({
        title: "Cancellation Failed",
        description: msg,
        variant: "error",
      });
    } finally {
      setIsCancelling(false);
    }
  };

  const selectedModelMeta = modelsData?.models.find((m) => m.model_name === selectedModel);

  return (
    <Card className="border-border bg-card/70" data-testid="transcription-panel">
      <CardHeader className="pb-3 border-b border-border/50">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="space-y-1">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Zap className="h-4 w-4 text-violet-400" />
              Faster-Whisper Speech-to-Text Pipeline
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              Local GPU-accelerated transcription with Silero VAD and word-level timestamping.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {modelsData?.cuda_available ? (
              <Badge variant="outline" className="text-[11px] border-emerald-500/30 text-emerald-400 bg-emerald-500/10 gap-1 font-mono">
                <CheckCircle2 className="h-3 w-3" />
                {modelsData.detected_gpu || "CUDA GPU Active"}
              </Badge>
            ) : (
              <Badge variant="outline" className="text-[11px] border-amber-500/30 text-amber-400 bg-amber-500/10 gap-1 font-mono">
                <Cpu className="h-3 w-3" />
                CPU Fallback
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-5">
        {/* Prerequisite Check: Audio Extracted */}
        {(!audioAsset || audioAsset.status !== "COMPLETED") && (
          <div
            className="p-3.5 rounded-lg border border-amber-500/30 bg-amber-500/10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs"
            data-testid="audio-missing-warning"
          >
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <span className="font-semibold text-amber-300">16kHz WAV Audio Required</span>
                <p className="text-amber-200/80">
                  Transcribing requires pre-extracted 16kHz mono WAV audio. Extract audio before starting.
                </p>
              </div>
            </div>

            {onExtractAudioRequested && (
              <Button
                variant="outline"
                size="sm"
                onClick={onExtractAudioRequested}
                className="shrink-0 h-7 text-xs border-amber-500/40 text-amber-300 hover:bg-amber-500/20"
                data-testid="extract-audio-prereq-btn"
              >
                <Volume2 className="h-3 w-3 mr-1" />
                Extract Audio
              </Button>
            )}
          </div>
        )}

        {/* Active Transcription Progress */}
        {isJobRunning && activeJob && (
          <div
            className="p-4 rounded-xl border border-violet-500/40 bg-violet-950/20 space-y-3"
            data-testid="transcription-progress"
          >
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-violet-400 animate-spin" />
                <span className="font-medium text-foreground">
                  {activeJob.current_step || "Transcribing speech..."}
                </span>
              </div>
              <span className="font-mono font-semibold text-violet-400">
                {activeJob.progress_percent.toFixed(0)}%
              </span>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-secondary/80 rounded-full h-2 overflow-hidden border border-border">
              <div
                className="bg-violet-600 h-2 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${Math.max(3, activeJob.progress_percent)}%` }}
              />
            </div>

            <div className="flex items-center justify-between pt-1">
              <span className="text-[11px] text-muted-foreground font-mono">
                Job ID: {activeJob.id.slice(0, 8)}...
              </span>

              <Button
                variant="destructive"
                size="sm"
                onClick={handleCancelJob}
                disabled={isCancelling}
                className="h-7 text-xs gap-1"
                data-testid="cancel-transcribe-btn"
              >
                {isCancelling ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <XCircle className="h-3 w-3" />
                )}
                <span>Cancel</span>
              </Button>
            </div>
          </div>
        )}

        {/* Configuration Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Model Size */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground block">
              Whisper Model
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              disabled={isJobRunning || isLoadingModels}
              className="w-full h-9 rounded-md border border-border bg-background px-3 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50 font-mono"
              data-testid="model-select"
            >
              <option value="tiny">tiny (39M params, ~500MB VRAM)</option>
              <option value="base">base (74M params, ~1GB VRAM)</option>
              <option value="small">small (244M params, ~2GB VRAM)</option>
            </select>
            {selectedModelMeta && (
              <span className="text-[10px] text-muted-foreground block line-clamp-1">
                {selectedModelMeta.recommended_for}
              </span>
            )}
          </div>

          {/* Compute Device */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground block">
              Inference Device
            </label>
            <select
              value={selectedDevice}
              onChange={(e) => {
                const dev = e.target.value;
                setSelectedDevice(dev);
                if (dev === "cuda" && modelsData?.cuda_compute_types.length) {
                  setSelectedComputeType(modelsData.cuda_compute_types[0]);
                } else if (dev === "cpu" && modelsData?.cpu_compute_types.length) {
                  setSelectedComputeType(modelsData.cpu_compute_types[0]);
                }
              }}
              disabled={isJobRunning || isLoadingModels}
              className="w-full h-9 rounded-md border border-border bg-background px-3 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50 font-mono"
              data-testid="device-select"
            >
              <option value="cuda" disabled={!modelsData?.cuda_available}>
                CUDA GPU {modelsData?.cuda_available ? "(RTX 3050)" : "(Unavailable)"}
              </option>
              <option value="cpu">CPU (Multi-threaded fallback)</option>
            </select>
            <span className="text-[10px] text-muted-foreground block">
              {selectedDevice === "cuda" ? "Hardware accelerated" : "Standard CPU execution"}
            </span>
          </div>

          {/* Quantization / Compute Type */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground block">
              Precision / Quantization
            </label>
            <select
              value={selectedComputeType}
              onChange={(e) => setSelectedComputeType(e.target.value)}
              disabled={isJobRunning || isLoadingModels}
              className="w-full h-9 rounded-md border border-border bg-background px-3 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50 font-mono"
              data-testid="compute-type-select"
            >
              {selectedDevice === "cuda" ? (
                <>
                  <option value="float16">float16 (Fastest on RTX 3050)</option>
                  <option value="int8_float16">int8_float16 (Reduced VRAM)</option>
                  <option value="int8">int8 (Lowest memory footprint)</option>
                </>
              ) : (
                <>
                  <option value="int8">int8 (Fastest on CPU)</option>
                  <option value="float32">float32 (Full precision)</option>
                </>
              )}
            </select>
            <span className="text-[10px] text-muted-foreground block font-mono">
              CTranslate2 optimized
            </span>
          </div>

          {/* Language Selection */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground block">
              Spoken Language
            </label>
            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              disabled={isJobRunning}
              className="w-full h-9 rounded-md border border-border bg-background px-3 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50 font-mono"
              data-testid="language-select"
            >
              <option value="">Auto-Detect Language</option>
              <option value="en">English (en)</option>
              <option value="es">Spanish (es)</option>
              <option value="fr">French (fr)</option>
              <option value="de">German (de)</option>
              <option value="it">Italian (it)</option>
              <option value="pt">Portuguese (pt)</option>
              <option value="ja">Japanese (ja)</option>
              <option value="zh">Chinese (zh)</option>
              <option value="hi">Hindi (hi)</option>
              <option value="ko">Korean (ko)</option>
              <option value="ru">Russian (ru)</option>
            </select>
            <span className="text-[10px] text-muted-foreground block">
              Auto-detection queries first 30s
            </span>
          </div>
        </div>

        {/* Feature Toggles */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1 border-t border-border/40">
          {/* Silero VAD */}
          <label className="flex items-start gap-2.5 p-3 rounded-lg border border-border/60 bg-secondary/20 cursor-pointer hover:bg-secondary/30 transition-colors">
            <input
              type="checkbox"
              checked={vadFilter}
              onChange={(e) => setVadFilter(e.target.checked)}
              disabled={isJobRunning}
              className="rounded border-border text-primary focus:ring-primary mt-0.5"
              data-testid="vad-toggle"
            />
            <div className="space-y-0.5">
              <span className="text-xs font-medium text-foreground block">
                Silero VAD Speech Filtering
              </span>
              <p className="text-[11px] text-muted-foreground">
                Filters non-speech silence intervals to eliminate hallucinations and speed up processing.
              </p>
            </div>
          </label>

          {/* Word Timestamps */}
          <label className="flex items-start gap-2.5 p-3 rounded-lg border border-border/60 bg-secondary/20 cursor-pointer hover:bg-secondary/30 transition-colors">
            <input
              type="checkbox"
              checked={wordTimestamps}
              onChange={(e) => setWordTimestamps(e.target.checked)}
              disabled={isJobRunning}
              className="rounded border-border text-primary focus:ring-primary mt-0.5"
              data-testid="word-timestamps-toggle"
            />
            <div className="space-y-0.5">
              <span className="text-xs font-medium text-foreground block">
                Word-Level Timestamps
              </span>
              <p className="text-[11px] text-muted-foreground">
                Generates exact millisecond timing for each spoken word, enabling precision subtitle cuts.
              </p>
            </div>
          </label>
        </div>

        {/* Retranscribe Checkbox if existing */}
        {hasExistingTranscript && (
          <div className="flex items-center gap-2 pt-1 text-xs text-muted-foreground">
            <input
              type="checkbox"
              id="forceRetranscribe"
              checked={forceRetranscribe}
              onChange={(e) => setForceRetranscribe(e.target.checked)}
              disabled={isJobRunning}
              className="rounded border-border text-primary focus:ring-primary"
              data-testid="force-retranscribe-toggle"
            />
            <label htmlFor="forceRetranscribe" className="cursor-pointer">
              Force re-transcription (will deactivate current transcript and overwrite)
            </label>
          </div>
        )}

        {/* Action Button */}
        <div className="flex items-center justify-between pt-2 border-t border-border/50">
          <div className="text-[11px] text-muted-foreground flex items-center gap-1.5 font-mono">
            <FileText className="h-3.5 w-3.5 text-zinc-400" />
            <span>Target: Faster-Whisper {selectedModel} ({selectedComputeType})</span>
          </div>

          <Button
            variant="default"
            size="sm"
            onClick={handleStartTranscription}
            disabled={
              isJobRunning ||
              isSubmitting ||
              !hasAudio ||
              !audioAsset ||
              audioAsset.status !== "COMPLETED"
            }
            className="h-8 text-xs gap-1.5 bg-violet-600 hover:bg-violet-700 text-white"
            data-testid="start-transcribe-btn"
          >
            {isSubmitting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : hasExistingTranscript ? (
              <RotateCcw className="h-3.5 w-3.5" />
            ) : (
              <Zap className="h-3.5 w-3.5" />
            )}
            <span>
              {isSubmitting
                ? "Submitting..."
                : isJobRunning
                ? "Transcription Running..."
                : hasExistingTranscript
                ? "Re-Run Transcription"
                : "Start Transcription"}
            </span>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
