import React from "react";
import {
  Play,
  Check,
  X,
  Edit3,
  AlertTriangle,
  Sparkles,
  Clock,
  Quote,
  Flame,
  Award,
  Scissors,
} from "lucide-react";
import { Highlight } from "../../../types/api";
import { Button } from "../../../components/ui/button";
import { Badge } from "../../../components/ui/badge";

interface HighlightCardProps {
  highlight: Highlight;
  onSeek?: (startSeconds: number) => void;
  onEdit?: (highlight: Highlight) => void;
  onAccept?: (highlightId: string) => void;
  onReject?: (highlightId: string) => void;
  onCreateClip?: (highlight: Highlight) => void;
  isProcessingAction?: boolean;
}

export const HighlightCard: React.FC<HighlightCardProps> = ({
  highlight,
  onSeek,
  onEdit,
  onAccept,
  onReject,
  onCreateClip,
  isProcessingAction = false,
}) => {
  const startSec = highlight.start_time ?? (highlight.start_ms ? highlight.start_ms / 1000 : 0);
  const endSec = highlight.end_time ?? (highlight.end_ms ? highlight.end_ms / 1000 : 0);
  const durationSec = Math.max(0, endSec - startSec);

  const formatTimestamp = (totalSeconds: number): string => {
    const m = Math.floor(totalSeconds / 60);
    const s = Math.floor(totalSeconds % 60);
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const getScoreBadgeColor = (score: number) => {
    if (score >= 80) return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
    if (score >= 65) return "bg-amber-500/10 text-amber-400 border-amber-500/30";
    return "bg-blue-500/10 text-blue-400 border-blue-500/30";
  };

  const getRankBadge = (rank?: number) => {
    if (!rank) return null;
    if (rank === 1) {
      return (
        <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm">
          <Award className="h-3 w-3 text-amber-400" /> #{rank} Top Pick
        </span>
      );
    }
    if (rank === 2) {
      return (
        <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-slate-300/20 text-slate-300 border border-slate-400/30">
          #{rank} Runner Up
        </span>
      );
    }
    if (rank === 3) {
      return (
        <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-700/20 text-amber-400 border border-amber-600/30">
          #{rank} Strong
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-secondary text-secondary-foreground border border-border">
        #{rank}
      </span>
    );
  };

  const status = highlight.status?.toUpperCase() || "CANDIDATE";
  const hookScore = highlight.hook_score ?? 0;
  const flowScore = highlight.coherence_score ?? highlight.flow_score ?? 0;
  const densityScore = highlight.density_score ?? 0;
  const sentimentScore = highlight.sentiment_score ?? highlight.energy_score ?? 0;
  const compositeScore = highlight.composite_score ?? 0;

  return (
    <div
      data-testid={`highlight-card-${highlight.id}`}
      className={`rounded-xl border p-4 transition-all duration-150 space-y-3.5 bg-card/70 hover:bg-card hover:border-border/80 ${
        status === "ACCEPTED"
          ? "border-emerald-500/50 bg-emerald-950/10 ring-1 ring-emerald-500/20"
          : status === "REJECTED"
          ? "border-rose-500/30 bg-rose-950/5 opacity-75"
          : "border-border"
      }`}
    >
      {/* Header: Rank, Category, Timing, Score */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {getRankBadge(highlight.rank)}
          {highlight.category && (
            <Badge variant="outline" className="text-[10px] uppercase font-semibold tracking-wider">
              {highlight.category}
            </Badge>
          )}
          <span className="flex items-center gap-1 text-[11px] font-mono text-muted-foreground bg-secondary/40 px-2 py-0.5 rounded-md border border-border/40">
            <Clock className="h-3 w-3 text-muted-foreground" />
            {formatTimestamp(startSec)} - {formatTimestamp(endSec)} ({durationSec.toFixed(0)}s)
          </span>
        </div>

        <div className="flex items-center gap-2">
          {status === "ACCEPTED" && (
            <Badge className="bg-emerald-600 text-white font-medium text-[11px] gap-1">
              <Check className="h-3 w-3" /> Accepted
            </Badge>
          )}
          {status === "REJECTED" && (
            <Badge variant="destructive" className="font-medium text-[11px] gap-1">
              <X className="h-3 w-3" /> Rejected
            </Badge>
          )}
          <div
            className={`flex items-center gap-1 px-2.5 py-1 rounded-lg border font-mono font-bold text-xs ${getScoreBadgeColor(
              compositeScore
            )}`}
          >
            <Flame className="h-3.5 w-3.5" />
            <span>Score: {compositeScore.toFixed(1)}</span>
          </div>
        </div>
      </div>

      {/* Hook Sentence Quote */}
      {highlight.hook_sentence && (
        <div className="p-3 rounded-lg bg-secondary/30 border border-border/50 text-foreground text-xs leading-relaxed relative pl-8">
          <Quote className="h-3.5 w-3.5 text-primary absolute left-2.5 top-3 opacity-80" />
          <span className="font-medium italic">"{highlight.hook_sentence}"</span>
        </div>
      )}

      {/* Summary / Excerpt */}
      {(highlight.summary || highlight.transcript_excerpt) && (
        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
          {highlight.summary || highlight.transcript_excerpt}
        </p>
      )}

      {/* Natural Language Explanation */}
      {highlight.explanation && (
        <div className="text-[11px] text-zinc-400 bg-background/50 p-2.5 rounded-lg border border-border/40 flex items-start gap-2">
          <Sparkles className="h-3.5 w-3.5 text-primary shrink-0 mt-0.5" />
          <span className="leading-snug">{highlight.explanation}</span>
        </div>
      )}

      {/* Granular Scoring Breakdown Bars */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 border-t border-border/40 text-[11px]">
        {/* Hook */}
        <div className="space-y-1">
          <div className="flex justify-between text-muted-foreground">
            <span>Hook (30%)</span>
            <span className="font-mono font-semibold text-foreground">{hookScore.toFixed(0)}</span>
          </div>
          <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(0, hookScore))}%` }}
            />
          </div>
        </div>

        {/* Coherence / Flow */}
        <div className="space-y-1">
          <div className="flex justify-between text-muted-foreground">
            <span>Flow (30%)</span>
            <span className="font-mono font-semibold text-foreground">{flowScore.toFixed(0)}</span>
          </div>
          <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bg-emerald-500 rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(0, flowScore))}%` }}
            />
          </div>
        </div>

        {/* Density */}
        <div className="space-y-1">
          <div className="flex justify-between text-muted-foreground">
            <span>Density (25%)</span>
            <span className="font-mono font-semibold text-foreground">{densityScore.toFixed(0)}</span>
          </div>
          <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bg-amber-500 rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(0, densityScore))}%` }}
            />
          </div>
        </div>

        {/* Sentiment / Energy */}
        <div className="space-y-1">
          <div className="flex justify-between text-muted-foreground">
            <span>Energy (15%)</span>
            <span className="font-mono font-semibold text-foreground">{sentimentScore.toFixed(0)}</span>
          </div>
          <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bg-purple-500 rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(0, sentimentScore))}%` }}
            />
          </div>
        </div>
      </div>

      {/* Warnings Badges */}
      {highlight.warnings && highlight.warnings.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          {highlight.warnings.map((w, idx) => (
            <span
              key={idx}
              className="flex items-center gap-1 text-[10px] font-mono text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded"
            >
              <AlertTriangle className="h-2.5 w-2.5" />
              {w.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}

      {/* Rejection Note */}
      {status === "REJECTED" && highlight.rejection_reason && (
        <div className="text-[11px] text-rose-300 bg-rose-500/10 border border-rose-500/20 p-2 rounded-md">
          <span className="font-semibold">Rejection reason:</span> {highlight.rejection_reason}
        </div>
      )}

      {/* Action Toolbar */}
      <div className="flex items-center justify-between gap-2 pt-2 border-t border-border/40">
        <Button
          variant="secondary"
          size="sm"
          className="h-8 gap-1.5 text-xs text-foreground"
          onClick={() => onSeek?.(startSec)}
        >
          <Play className="h-3.5 w-3.5 text-primary" />
          Seek ({formatTimestamp(startSec)})
        </Button>

        <div className="flex items-center gap-1.5">
          {onEdit && (
            <Button
              variant="outline"
              size="sm"
              className="h-8 gap-1 text-xs"
              onClick={() => onEdit(highlight)}
            >
              <Edit3 className="h-3 w-3" />
              Edit
            </Button>
          )}

          {status === "ACCEPTED" && onCreateClip && (
            <Button
              variant="default"
              size="sm"
              className="h-8 gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-medium"
              onClick={() => onCreateClip(highlight)}
            >
              <Scissors className="h-3.5 w-3.5" />
              Create 9:16 Clip
            </Button>
          )}

          {status !== "ACCEPTED" && onAccept && (
            <Button
              variant="outline"
              size="sm"
              className="h-8 gap-1 text-xs text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/10"
              disabled={isProcessingAction}
              onClick={() => onAccept(highlight.id)}
            >
              <Check className="h-3.5 w-3.5" />
              Accept
            </Button>
          )}

          {status !== "REJECTED" && onReject && (
            <Button
              variant="outline"
              size="sm"
              className="h-8 gap-1 text-xs text-rose-400 border-rose-500/30 hover:bg-rose-500/10"
              disabled={isProcessingAction}
              onClick={() => onReject(highlight.id)}
            >
              <X className="h-3.5 w-3.5" />
              Reject
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
