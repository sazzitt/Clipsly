import React, { useState } from "react";
import {
  Sparkles,
  Loader2,
  XCircle,
  Filter,
  SlidersHorizontal,
} from "lucide-react";
import { Button } from "../../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";
import { Progress } from "../../../components/ui/progress";
import { HighlightDetectionRequest, ProcessingJob } from "../../../types/api";

interface HighlightDetectionPanelProps {
  videoId: string;
  hasTranscript: boolean;
  activeJob?: ProcessingJob | null;
  onDetectRequested: (config: HighlightDetectionRequest) => Promise<void>;
  onCancelJob?: (jobId: string) => Promise<void>;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
  categoryFilter: string;
  onCategoryFilterChange: (category: string) => void;
  sortBy: string;
  onSortByChange: (sort: string) => void;
  stats: {
    total: number;
    accepted: number;
    rejected: number;
    topScore: number;
  };
}

export const HighlightDetectionPanel: React.FC<HighlightDetectionPanelProps> = ({
  hasTranscript,
  activeJob,
  onDetectRequested,
  onCancelJob,
  statusFilter,
  onStatusFilterChange,
  categoryFilter,
  onCategoryFilterChange,
  sortBy,
  onSortByChange,
  stats,
}) => {
  const [selectedPresets, setSelectedPresets] = useState<string[]>([
    "15-30",
    "30-60",
    "60-90",
  ]);
  const [minScore, setMinScore] = useState<number>(50);
  const [maxResults, setMaxResults] = useState<number>(10);
  const [forceRedetect, setForceRedetect] = useState<boolean>(false);
  const [showConfig, setShowConfig] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isCancelling, setIsCancelling] = useState<boolean>(false);

  const isJobActive =
    activeJob && (activeJob.status === "PENDING" || activeJob.status === "PROCESSING");

  const handleTogglePreset = (preset: string) => {
    if (selectedPresets.includes(preset)) {
      if (selectedPresets.length > 1) {
        setSelectedPresets(selectedPresets.filter((p) => p !== preset));
      }
    } else {
      setSelectedPresets([...selectedPresets, preset]);
    }
  };

  const handleRunDetection = async () => {
    try {
      setIsSubmitting(true);
      await onDetectRequested({
        target_duration_presets: selectedPresets,
        min_score: minScore,
        max_results: maxResults,
        force_redetect: forceRedetect,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async () => {
    if (!activeJob || !onCancelJob) return;
    try {
      setIsCancelling(true);
      await onCancelJob(activeJob.id);
    } finally {
      setIsCancelling(false);
    }
  };

  return (
    <Card className="border-border bg-card/60 backdrop-blur-sm">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              AI Highlight Detection & Scoring
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              Analyzes speech transcript for engaging hooks, narrative coherence, pacing, and sentiment.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-8 gap-1.5 text-xs"
              onClick={() => setShowConfig(!showConfig)}
            >
              <SlidersHorizontal className="h-3.5 w-3.5 text-muted-foreground" />
              {showConfig ? "Hide Settings" : "Configure Engine"}
            </Button>

            {!isJobActive ? (
              <Button
                size="sm"
                className="h-8 gap-1.5 text-xs"
                disabled={!hasTranscript || isSubmitting}
                onClick={handleRunDetection}
              >
                {isSubmitting ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5" />
                )}
                {stats.total > 0 ? "Re-Detect Highlights" : "Detect Highlights"}
              </Button>
            ) : (
              <Button
                variant="destructive"
                size="sm"
                className="h-8 gap-1.5 text-xs"
                disabled={isCancelling}
                onClick={handleCancel}
              >
                {isCancelling ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <XCircle className="h-3.5 w-3.5" />
                )}
                Cancel Detection
              </Button>
            )}
          </div>
        </div>

        {/* Live Job Progress Display */}
        {isJobActive && (
          <div className="pt-3 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-foreground font-medium">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                {activeJob.current_step || "Processing highlights..."}
              </span>
              <span className="font-mono text-primary font-bold">
                {activeJob.progress_percent?.toFixed(0) || 0}%
              </span>
            </div>
            <Progress value={activeJob.progress_percent || 5} className="h-2" />
          </div>
        )}

        {/* Missing transcript notice */}
        {!hasTranscript && !isJobActive && (
          <div className="mt-2 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs flex items-center justify-between">
            <span>Speech transcript is required before running highlight detection.</span>
            <Badge variant="outline" className="text-[10px] border-amber-500/30 text-amber-300">
              Run Whisper Transcription First
            </Badge>
          </div>
        )}
      </CardHeader>

      <CardContent className="space-y-4 pt-0">
        {/* Expandable Configuration */}
        {showConfig && (
          <div className="p-3.5 rounded-xl border border-border/70 bg-secondary/30 space-y-3 text-xs">
            <div className="space-y-1.5">
              <span className="font-semibold text-foreground">Duration Presets</span>
              <div className="flex flex-wrap gap-2">
                {[
                  { id: "15-30", label: "Short (15-30s)" },
                  { id: "30-60", label: "Medium (30-60s)" },
                  { id: "60-90", label: "Long (60-90s)" },
                ].map((p) => {
                  const isSelected = selectedPresets.includes(p.id);
                  return (
                    <Button
                      key={p.id}
                      variant={isSelected ? "default" : "outline"}
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => handleTogglePreset(p.id)}
                    >
                      {p.label}
                    </Button>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Minimum Composite Score</span>
                  <span className="font-mono font-semibold text-foreground">{minScore}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="90"
                  step="5"
                  value={minScore}
                  onChange={(e) => setMinScore(parseInt(e.target.value, 10))}
                  className="w-full accent-primary"
                />
              </div>

              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Max Highlight Results</span>
                  <span className="font-mono font-semibold text-foreground">{maxResults}</span>
                </div>
                <input
                  type="range"
                  min="3"
                  max="30"
                  step="1"
                  value={maxResults}
                  onChange={(e) => setMaxResults(parseInt(e.target.value, 10))}
                  className="w-full accent-primary"
                />
              </div>
            </div>

            <div className="flex items-center gap-2 pt-1 border-t border-border/40 text-muted-foreground">
              <input
                id="force-redetect-toggle"
                type="checkbox"
                checked={forceRedetect}
                onChange={(e) => setForceRedetect(e.target.checked)}
                className="rounded border-border accent-primary"
              />
              <label htmlFor="force-redetect-toggle" className="cursor-pointer text-xs">
                Force fresh detection (supersedes previous unreviewed candidate highlights)
              </label>
            </div>
          </div>
        )}

        {/* Highlight Metrics & Filter Toolbar */}
        {stats.total > 0 && (
          <div className="space-y-3 pt-1">
            {/* Summary Pills */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div className="p-2.5 rounded-lg border border-border/50 bg-secondary/20 flex items-center justify-between">
                <span className="text-[11px] text-muted-foreground">Total Candidates</span>
                <span className="font-mono font-bold text-foreground text-sm">{stats.total}</span>
              </div>
              <div className="p-2.5 rounded-lg border border-emerald-500/20 bg-emerald-500/5 flex items-center justify-between">
                <span className="text-[11px] text-emerald-400">Accepted</span>
                <span className="font-mono font-bold text-emerald-300 text-sm">{stats.accepted}</span>
              </div>
              <div className="p-2.5 rounded-lg border border-rose-500/20 bg-rose-500/5 flex items-center justify-between">
                <span className="text-[11px] text-rose-400">Rejected</span>
                <span className="font-mono font-bold text-rose-300 text-sm">{stats.rejected}</span>
              </div>
              <div className="p-2.5 rounded-lg border border-amber-500/20 bg-amber-500/5 flex items-center justify-between">
                <span className="text-[11px] text-amber-400">Top Score</span>
                <span className="font-mono font-bold text-amber-300 text-sm">
                  {stats.topScore.toFixed(1)}
                </span>
              </div>
            </div>

            {/* Filter and Sort Controls */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-border/40 text-xs">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-muted-foreground text-[11px] font-medium mr-1 flex items-center gap-1">
                  <Filter className="h-3 w-3" /> Status:
                </span>
                {["ALL", "CANDIDATE", "ACCEPTED", "REJECTED"].map((st) => (
                  <Button
                    key={st}
                    variant={statusFilter === st ? "default" : "outline"}
                    size="sm"
                    className="h-7 text-[11px] px-2.5"
                    onClick={() => onStatusFilterChange(st)}
                  >
                    {st === "ALL" ? "All" : st.charAt(0) + st.slice(1).toLowerCase()}
                  </Button>
                ))}
              </div>

              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <span className="text-muted-foreground text-[11px]">Category:</span>
                  <select
                    value={categoryFilter}
                    onChange={(e) => onCategoryFilterChange(e.target.value)}
                    className="bg-secondary/40 border border-border text-foreground rounded-md text-xs px-2 py-1 focus:outline-none"
                  >
                    <option value="ALL">All Categories</option>
                    <option value="Insight">Insight</option>
                    <option value="Story">Story</option>
                    <option value="Punchline">Punchline</option>
                    <option value="Discussion">Discussion</option>
                    <option value="Question">Question</option>
                  </select>
                </div>

                <div className="flex items-center gap-1.5">
                  <span className="text-muted-foreground text-[11px]">Sort:</span>
                  <select
                    value={sortBy}
                    onChange={(e) => onSortByChange(e.target.value)}
                    className="bg-secondary/40 border border-border text-foreground rounded-md text-xs px-2 py-1 focus:outline-none"
                  >
                    <option value="rank">Rank (#1 First)</option>
                    <option value="score">Highest Score</option>
                    <option value="timestamp">Timeline Order</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
